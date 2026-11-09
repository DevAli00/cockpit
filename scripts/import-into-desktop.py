"""Loads a Cockpit JSON backup into the desktop app's database and checks the copy is identical.

Usage (desktop app closed):  backend/.venv/bin/python scripts/import-into-desktop.py <backup.json>
Replaces whatever the desktop database holds; an existing database is copied aside first.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy.engine import URL  # noqa: E402

from app.core.desktop import DB_FILE, data_dir, snapshot_database  # noqa: E402
from app.db.bootstrap import ensure_schema  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.schemas_backup import Backup  # noqa: E402
from app.services.backup import export_all, import_all  # noqa: E402


async def main(source: Path) -> int:
    original = json.loads(source.read_text(encoding="utf-8"))
    folder = data_dir(sys.platform, os.environ, Path.home())
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        folder.chmod(0o700)
    db = folder / DB_FILE
    if db.exists():
        kept = snapshot_database(db, folder / "backups" / "before-import", date.today(), keep=5)
        print(f"existing database copied to {kept}" if kept else "existing database already copied today")

    engine = make_engine(URL.create("sqlite+aiosqlite", database=str(db)).render_as_string(hide_password=False))
    try:
        await ensure_schema(engine)
        factory = make_session_factory(engine)
        async with factory() as s:
            await import_all(s, Backup.model_validate(original))
        async with factory() as s:
            copy = json.loads((await export_all(s)).model_dump_json())
    finally:
        await engine.dispose()

    differing = [k for k in original if original[k] != copy.get(k)]
    rows = sum(len(v) for v in copy.values() if isinstance(v, list))
    if differing:
        print(f"MISMATCH in: {', '.join(differing)}")
        return 1
    print(f"imported {rows} rows into {db}: identical to the backup")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(asyncio.run(main(Path(sys.argv[1]))))
