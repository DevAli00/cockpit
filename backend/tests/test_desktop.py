"""Desktop (standalone) mode: SQLite bootstrap, token hand-off, bundled frontend, host checks."""
from __future__ import annotations

import sqlite3
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings
from app.core.desktop import data_dir, snapshot_database
from app.db.bootstrap import ensure_schema
from app.db.session import make_engine
from app.main import create_app
from app.services.users import ensure_owner

TOKEN = "t" * 43
HOST = "http://127.0.0.1:5000"


@pytest.fixture
def web(tmp_path: Path) -> Path:
    root = tmp_path / "web"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html>COCKPIT-INDEX</html>")
    (root / "assets" / "app.js").write_text("console.log('app')")
    (root / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    return root


@pytest.fixture
async def desk(tmp_path: Path, web: Path) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'cockpit.db'}", secret_key="s" * 48,
        admin_email="local@cockpit.desktop", admin_password="x" * 24,
        desktop_token=TOKEN, static_dir=web, auto_schema=True,
    )
    engine = make_engine(settings.database_url)
    await ensure_schema(engine)
    app = create_app(settings, engine=engine)
    async with app.state.session_factory() as s:
        await ensure_owner(s, settings.admin_email, settings.admin_password)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=HOST) as c:
        yield c
    await engine.dispose()


# --- token hand-off ----------------------------------------------------------------------------
async def test_desktop_token_opens_a_session_without_a_password(desk: AsyncClient) -> None:
    assert (await desk.get("/api/me")).status_code == 401
    assert (await desk.get("/api/auth/desktop?token=wrong")).status_code == 403
    assert (await desk.get("/api/auth/desktop")).status_code == 422
    r = await desk.get(f"/api/auth/desktop?token={TOKEN}")
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert "httponly" in r.headers["set-cookie"].lower()
    me = (await desk.get("/api/me")).json()
    assert me["desktop"] is True


async def test_token_endpoint_does_not_exist_on_the_server_version(anon: AsyncClient) -> None:
    assert (await anon.get(f"/api/auth/desktop?token={TOKEN}")).status_code == 404


async def test_me_reports_not_desktop_on_the_server_version(api: AsyncClient) -> None:
    assert (await api.get("/api/me")).json()["desktop"] is False


async def test_foreign_host_header_is_refused(desk: AsyncClient) -> None:
    """DNS-rebinding defence: a web page pointing its own domain at 127.0.0.1 must not reach the API."""
    r = await desk.get("/api/health", headers={"host": "evil.example"})
    assert r.status_code == 400
    assert (await desk.get("/api/health", headers={"host": "localhost:5000"})).status_code == 200


# --- bundled frontend --------------------------------------------------------------------------
async def test_frontend_is_served_with_spa_fallback(desk: AsyncClient) -> None:
    assert "COCKPIT-INDEX" in (await desk.get("/")).text
    assert "COCKPIT-INDEX" in (await desk.get("/projects/123")).text  # client-side route
    js = await desk.get("/assets/app.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert (await desk.get("/favicon.svg")).status_code == 200
    assert "content-security-policy" in (await desk.get("/")).headers


async def test_unknown_api_route_is_a_json_404_not_the_app_shell(desk: AsyncClient) -> None:
    r = await desk.get("/api/does-not-exist")
    assert r.status_code == 404 and "COCKPIT-INDEX" not in r.text


@pytest.mark.parametrize("path", ["/%2e%2e/secret.txt", "/assets/%2e%2e/%2e%2e/secret.txt", "/..%2fsecret.txt"])
async def test_static_files_cannot_escape_their_folder(desk: AsyncClient, path: str) -> None:
    assert "TOP-SECRET" not in (await desk.get(path)).text


# --- sqlite behaviour --------------------------------------------------------------------------
async def test_sqlite_enforces_foreign_keys(desk: AsyncClient) -> None:
    await desk.get(f"/api/auth/desktop?token={TOKEN}")
    c = (await desk.post("/api/clients", json={"name": "Acme", "color": "#112233"})).json()
    p = (await desk.post("/api/projects", json={"name": "Site", "client_id": c["id"]})).json()
    assert (await desk.delete(f"/api/clients/{c['id']}")).status_code == 204
    assert (await desk.get(f"/api/projects/{p['id']}")).json()["client_id"] is None
    ghost = "00000000-0000-0000-0000-000000000000"
    assert (await desk.post("/api/tasks", json={"title": "x", "client_id": ghost})).status_code == 422


async def test_income_shares_adding_up_to_exactly_100_are_accepted(desk: AsyncClient) -> None:
    """SQLite stores decimals as floats: the 100% check must not be thrown off by float sums."""
    await desk.get(f"/api/auth/desktop?token={TOKEN}")
    for name, pct in (("A", "33.3"), ("B", "33.3"), ("C", "33.4")):
        r = await desk.post("/api/funds", json={"name": name, "kind": "other", "target": "100", "income_pct": pct})
        assert r.status_code == 201, r.text
    r = await desk.post("/api/funds", json={"name": "D", "kind": "other", "target": "100", "income_pct": "0.1"})
    assert r.status_code == 422


# --- schema bootstrap / upgrade ----------------------------------------------------------------
async def test_ensure_schema_creates_everything_on_an_empty_file(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite+aiosqlite:///{tmp_path / 'new.db'}")
    changes = await ensure_schema(engine)
    assert any("funds" in c for c in changes)
    assert await ensure_schema(engine) == []  # idempotent
    await engine.dispose()


async def test_ensure_schema_adds_columns_missing_from_an_older_database(tmp_path: Path) -> None:
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE funds (id CHAR(32) PRIMARY KEY, name VARCHAR(200) NOT NULL, kind VARCHAR(12) NOT NULL,"
        " target NUMERIC(12,2) NOT NULL, deadline DATE, trip_id CHAR(32), notes TEXT NOT NULL, created_at DATETIME NOT NULL)"
    )
    con.execute("INSERT INTO funds VALUES ('0123456789abcdef0123456789abcdef','Old fund','travel',100,NULL,NULL,'','2026-01-01 00:00:00')")
    con.commit(); con.close()

    engine = make_engine(f"sqlite+aiosqlite:///{db}")
    changes = await ensure_schema(engine)
    assert any("funds.monthly_day" in c for c in changes) and any("funds.income_pct" in c for c in changes)
    async with engine.connect() as conn:
        row = (await conn.execute(text("select name, monthly_day, monthly_amount, auto_start from funds"))).one()
    assert row == ("Old fund", 1, None, None)  # data kept, new NOT NULL column got its default
    assert list(tmp_path.glob("old.db.before-upgrade-*")), "a copy is kept before altering an existing database"
    assert await ensure_schema(engine) == []
    await engine.dispose()


# --- paths and snapshots -----------------------------------------------------------------------
def test_data_dir_per_platform(tmp_path: Path) -> None:
    home = Path("/home/u")
    assert data_dir("darwin", {}, home) == home / "Library" / "Application Support" / "Cockpit"
    assert data_dir("win32", {"APPDATA": r"C:\Users\u\AppData\Roaming"}, home) == Path(r"C:\Users\u\AppData\Roaming") / "Cockpit"
    assert data_dir("win32", {}, home) == home / "AppData" / "Roaming" / "Cockpit"
    assert data_dir("linux", {"XDG_DATA_HOME": "/x"}, home) == Path("/x") / "cockpit"
    assert data_dir("linux", {}, home) == home / ".local" / "share" / "cockpit"
    assert data_dir("darwin", {"COCKPIT_DATA_DIR": str(tmp_path)}, home) == tmp_path  # explicit override wins


def test_snapshot_database_once_a_day_and_prunes(tmp_path: Path) -> None:
    db = tmp_path / "cockpit.db"
    con = sqlite3.connect(db); con.execute("create table t (v)"); con.execute("insert into t values (42)"); con.commit(); con.close()
    backups = tmp_path / "backups"
    for day in range(1, 6):
        assert snapshot_database(db, backups, date(2026, 11, day), keep=3) is not None
    assert sorted(p.name for p in backups.iterdir()) == ["cockpit-20261103.db", "cockpit-20261104.db", "cockpit-20261105.db"]
    assert snapshot_database(db, backups, date(2026, 11, 5), keep=3) is None  # already done today
    assert sqlite3.connect(backups / "cockpit-20261105.db").execute("select v from t").fetchone() == (42,)
    assert snapshot_database(tmp_path / "missing.db", backups, date(2026, 11, 6), keep=3) is None  # first launch


# --- native save dialog through the server (no JS bridge) --------------------------------------
class FakeBridge:
    def __init__(self, accept: bool) -> None:
        self.accept = accept
        self.calls: list[tuple[str, str]] = []

    def save_text(self, suggested_name: str, content: str) -> bool:
        self.calls.append((suggested_name, content))
        return self.accept


async def _desk_with_bridge(tmp_path: Path, web: Path, bridge: FakeBridge | None) -> tuple[AsyncClient, object]:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'b.db'}", secret_key="s" * 48,
        admin_email="local@cockpit.desktop", admin_password="x" * 24,
        desktop_token=TOKEN, static_dir=web, auto_schema=True,
    )
    engine = make_engine(settings.database_url)
    await ensure_schema(engine)
    app = create_app(settings, engine=engine, desktop_bridge=bridge)
    async with app.state.session_factory() as s:
        await ensure_owner(s, settings.admin_email, settings.admin_password)
    return AsyncClient(transport=ASGITransport(app=app), base_url=HOST), engine


async def test_backup_is_saved_through_the_native_dialog(tmp_path: Path, web: Path) -> None:
    import json

    bridge = FakeBridge(accept=True)
    client, engine = await _desk_with_bridge(tmp_path, web, bridge)
    async with client:
        assert (await client.post("/api/desktop/backup-file")).status_code == 401  # needs the session
        await client.get(f"/api/auth/desktop?token={TOKEN}")
        await client.post("/api/clients", json={"name": "Acme", "color": "#112233"})
        r = await client.post("/api/desktop/backup-file")
        assert r.status_code == 200 and r.json() == {"saved": True}
    name, content = bridge.calls[0]
    assert name.startswith("cockpit-backup-") and name.endswith(".json")
    data = json.loads(content)
    assert data["version"] == 1 and data["clients"][0]["name"] == "Acme"
    await engine.dispose()  # type: ignore[attr-defined]


async def test_cancelled_dialog_is_reported(tmp_path: Path, web: Path) -> None:
    client, engine = await _desk_with_bridge(tmp_path, web, FakeBridge(accept=False))
    async with client:
        await client.get(f"/api/auth/desktop?token={TOKEN}")
        assert (await client.post("/api/desktop/backup-file")).json() == {"saved": False}
    await engine.dispose()  # type: ignore[attr-defined]


async def test_no_native_dialog_on_the_server_version(api: AsyncClient) -> None:
    assert (await api.post("/api/desktop/backup-file")).status_code == 404
