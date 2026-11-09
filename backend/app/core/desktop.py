"""Helpers for the standalone desktop app: where data lives, and daily snapshots of it."""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import date
from pathlib import Path

APP_NAME = "Cockpit"
DB_FILE = "cockpit.db"


def data_dir(platform: str, env: Mapping[str, str], home: Path) -> Path:
    """Per-user data folder. COCKPIT_DATA_DIR overrides it (used for testing and portable installs)."""
    if override := env.get("COCKPIT_DATA_DIR"):
        return Path(override)
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if platform == "win32":
        base = env.get("APPDATA")
        return (Path(base) if base else home / "AppData" / "Roaming") / APP_NAME
    base = env.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local" / "share") / APP_NAME.lower()


def snapshot_database(db: Path, backups: Path, today: date, keep: int) -> Path | None:
    """Copy the database once per day into `backups`, keeping the `keep` most recent copies.

    Uses SQLite's backup API, which is safe while the database is in use. Returns the new copy,
    or None when there is nothing to copy or today's copy already exists.
    """
    if not db.is_file():
        return None
    backups.mkdir(parents=True, exist_ok=True)
    target = backups / f"cockpit-{today:%Y%m%d}.db"
    if target.exists():
        return None
    src, dst = sqlite3.connect(db), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    for old in sorted(backups.glob("cockpit-*.db"))[:-keep]:
        old.unlink(missing_ok=True)
    return target
