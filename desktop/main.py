"""Cockpit desktop launcher.

Starts the API on a random local port, serves the bundled web app from it, and shows it in a native
window. Data lives in one SQLite file in the user's application-data folder.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import uvicorn
from sqlalchemy.engine import URL

from app.core.config import Settings
from app.core.desktop import (
    APP_NAME, DB_FILE, data_dir, snapshot_database, start_watchdog, timed_out_report,
)
from app.main import create_app

log = logging.getLogger("cockpit.desktop")

SNAPSHOTS_KEPT = 14
STARTUP_TIMEOUT_S = 30.0
BROWSER_IDLE_EXIT_S = 12 * 3600  # browser-fallback mode has no window to close: stop when unused
WINDOW_SIZE = (1280, 860)
WINDOW_MIN_SIZE = (900, 600)
SELFTEST_PAGE_TIMEOUT_S = 40.0
# Hard limit for a whole self-test run. A web view that never answers blocks run_js for good, and
# a build machine would then wait for hours: past this limit the app reports and quits by force.
SELFTEST_TIMEOUT_S = 90.0
SELFTEST_TIMEOUT_EXIT = 3

SELFTEST_PATH = "/__selftest__"
# Runs inside the page (no eval: the app's Content-Security-Policy forbids it) and posts what it
# sees to SELFTEST_PATH, which only exists while self-testing.
SELFTEST_JS = """
(function tick() {
  if (window.__cockpitSelftest) return;
  var brand = document.querySelector('.brand');
  if (!brand) { setTimeout(tick, 250); return; }
  window.__cockpitSelftest = true;
  function call(method, path, body) {
    var x = new XMLHttpRequest();
    x.open(method, path, false);
    x.setRequestHeader('Content-Type', 'application/json');
    x.send(body ? JSON.stringify(body) : null);
    return { status: x.status, body: x.responseText };
  }
  var me = call('GET', '/api/me');
  var created = call('POST', '/api/tasks', { title: 'selftest task' });
  var tasks = call('GET', '/api/tasks');
  var backup = call('POST', '/api/desktop/backup-file');
  call('POST', '%s', {
    ready: true,
    brand: brand.textContent,
    heading: (document.querySelector('h1') || {}).textContent || '',
    signOutShown: Array.prototype.some.call(document.querySelectorAll('button'), function (b) { return b.textContent === 'Sign out'; }),
    me: me, taskCreated: created.status, tasks: JSON.parse(tasks.body).length, backup: backup,
    userAgent: navigator.userAgent
  });
})()
""" % SELFTEST_PATH


def web_dir() -> Path:
    """The built web app: bundled by PyInstaller, or frontend/dist when run from source."""
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled) / "web" if bundled else Path(__file__).resolve().parent.parent / "frontend" / "dist"


def setup_logging(folder: Path) -> None:
    handler = RotatingFileHandler(folder / "cockpit.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


class ActivityTracker:
    """ASGI wrapper that remembers when the last request arrived."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.last_seen = time.monotonic()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            self.last_seen = time.monotonic()
        await self.app(scope, receive, send)


class LocalServer:
    """uvicorn on 127.0.0.1 with an OS-assigned port, running in a background thread."""

    def __init__(self, app: Any) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))  # loopback only; the OS picks a free port
        self.port: int = self._sock.getsockname()[1]
        config = uvicorn.Config(app, log_config=None, access_log=False, lifespan="on")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, kwargs={"sockets": [self._sock]}, daemon=True)

    def start(self) -> bool:
        """True once the server accepts requests; False if startup failed or timed out."""
        self._thread.start()
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        while time.monotonic() < deadline:
            if self._server.started:
                return True
            if not self._thread.is_alive():
                return False
            time.sleep(0.05)
        return False

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)


class WindowBridge:
    """Native dialogs for the server (see app.api.desktop). The page itself gets no native API."""

    def __init__(self) -> None:
        self.window: Any = None

    def save_text(self, suggested_name: str, content: str) -> bool:
        import webview

        if self.window is None:
            return False
        chosen = self.window.create_file_dialog(
            webview.FileDialog.SAVE, save_filename=Path(suggested_name).name, file_types=("JSON file (*.json)",)
        )
        if not chosen:
            return False
        target = Path(chosen if isinstance(chosen, str) else chosen[0])
        target.write_text(content, encoding="utf-8")
        log.info("saved %s", target)
        return True


class SelftestBridge(WindowBridge):
    """Saves without asking, so the self-test never blocks on a dialog."""

    def __init__(self, folder: Path) -> None:
        super().__init__()
        self._folder = folder

    def save_text(self, suggested_name: str, content: str) -> bool:
        (self._folder / Path(suggested_name).name).write_text(content, encoding="utf-8")
        return True


class SelftestCapture(ActivityTracker):
    """Self-test only: receives the page's report on SELFTEST_PATH."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.reported = threading.Event()
        self.report: dict[str, Any] = {"ready": False, "error": "no report from the page"}
        self.stage = "starting"  # what the run was doing, for the report of a stuck run

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] != SELFTEST_PATH:
            await super().__call__(scope, receive, send)
            return
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        self.report = json.loads(body)
        self.reported.set()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


def _selftest(window: Any, capture: SelftestCapture, out: Path) -> None:
    """Drive the real window once and write what it saw (used to verify packaged builds)."""
    deadline = time.monotonic() + SELFTEST_PAGE_TIMEOUT_S
    while time.monotonic() < deadline and not capture.reported.is_set():
        capture.stage = "running a script in the page (the web view did not answer)"
        try:
            window.run_js(SELFTEST_JS)  # re-injected until the app page (not the redirect) has it
        except Exception as exc:
            log.exception("self-test: could not run the script in the page")
            capture.report = {"ready": False, "error": repr(exc)}
        capture.stage = "waiting for the page to report"
        capture.reported.wait(2)
    out.write_text(json.dumps(capture.report, indent=2), encoding="utf-8")
    log.info("self-test: reported=%s", capture.reported.is_set())
    capture.stage = "closing the window"
    window.destroy()


def _abort_selftest(out: Path, capture: SelftestCapture) -> None:
    """Watchdog: the self-test is stuck. Write what is known and quit without waiting for the GUI."""
    if capture.reported.is_set():  # the page did its part; only the shutdown hung
        report: dict[str, Any] = {**capture.report, "forcedExit": True}
    else:
        report = timed_out_report(capture.report, capture.stage, SELFTEST_TIMEOUT_S)
    log.error("self-test: forced exit while %s", capture.stage)
    try:
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        logging.shutdown()
        os._exit(SELFTEST_TIMEOUT_EXIT)  # the GUI loop may be what is stuck: sys.exit would wait for it


def _fail_selftest(out: Path, error: str) -> None:
    """The self-test could not even show a window: say why instead of leaving no report."""
    out.write_text(json.dumps({"ready": False, "error": error}, indent=2), encoding="utf-8")


def _error_page(log_file: Path) -> str:
    return (
        "<body style='font-family:system-ui;padding:2rem'><h2>Cockpit could not start</h2>"
        f"<p>Details are in:<br><code>{log_file}</code></p></body>"
    )


def _serve_in_browser(url: str, tracker: ActivityTracker) -> None:
    """Fallback when no native web view is available: use the default browser."""
    webbrowser.open(url)
    while time.monotonic() - tracker.last_seen < BROWSER_IDLE_EXIT_S:
        time.sleep(30)


def main() -> int:
    folder = data_dir(sys.platform, os.environ, Path.home())
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        folder.chmod(0o700)  # personal finances: this user only
    setup_logging(folder)
    db = folder / DB_FILE
    try:
        snapshot_database(db, folder / "backups", date.today(), SNAPSHOTS_KEPT)
    except Exception:
        log.exception("daily snapshot failed (continuing)")

    token = secrets.token_urlsafe(32)
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]  # never pick up a stray .env
        database_url=URL.create("sqlite+aiosqlite", database=str(db)).render_as_string(hide_password=False),
        secret_key=secrets.token_urlsafe(48),  # sessions do not outlive the process
        admin_email="local@cockpit.desktop",
        admin_password=secrets.token_urlsafe(32),  # unused: the window signs in with the token
        desktop_token=token, static_dir=web_dir(), auto_schema=True,
    )
    selftest = os.environ.get("COCKPIT_SELFTEST")
    # COCKPIT_SELFTEST_DIALOG=1 keeps the real save dialog in a self-test (someone must answer it).
    real_dialog = bool(os.environ.get("COCKPIT_SELFTEST_DIALOG"))
    bridge = SelftestBridge(folder) if selftest and not real_dialog else WindowBridge()
    app = create_app(settings, desktop_bridge=bridge)
    tracker = SelftestCapture(app) if selftest else ActivityTracker(app)
    capture = tracker if isinstance(tracker, SelftestCapture) else None
    report_to = Path(selftest) if selftest else None
    if capture is not None and report_to is not None:
        start_watchdog(SELFTEST_TIMEOUT_S, lambda: _abort_selftest(report_to, capture))
        capture.stage = "starting the local server"
    server = LocalServer(tracker)
    started = server.start()
    url = f"http://127.0.0.1:{server.port}/api/auth/desktop?token={token}"
    log.info("started=%s port=%s data=%s", started, server.port, folder)

    try:
        import webview
    except Exception as exc:
        log.exception("native web view unavailable")
        if report_to is not None:  # a self-test must end, not wait in the browser fallback
            _fail_selftest(report_to, f"native web view unavailable: {exc!r}")
            server.stop()
            return 1
        if started:
            _serve_in_browser(url, tracker)
        server.stop()
        return 0 if started else 1

    try:
        if started:
            window = webview.create_window(
                APP_NAME, url, width=WINDOW_SIZE[0], height=WINDOW_SIZE[1], min_size=WINDOW_MIN_SIZE
            )
        else:
            window = webview.create_window(APP_NAME, html=_error_page(folder / "cockpit.log"), width=640, height=320)
        bridge.window = window
        kwargs: dict[str, Any] = {"gui": "edgechromium"} if sys.platform == "win32" else {}
        if capture is not None and report_to is not None:
            if not started:
                _fail_selftest(report_to, "the local server did not start")
                return 1
            capture.stage = "opening the window"
            webview.start(_selftest, (window, capture, report_to), **kwargs)
        else:
            webview.start(**kwargs)
    except Exception as exc:
        log.exception("window failed")
        if report_to is not None:
            _fail_selftest(report_to, f"window failed: {exc!r}")
            return 1
        if started:
            _serve_in_browser(url, tracker)
    finally:
        server.stop()
    return 0 if started else 1


if __name__ == "__main__":
    sys.exit(main())
