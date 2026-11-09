# PyInstaller spec for the Cockpit desktop app (macOS .app and Windows folder build).
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
VERSION = tomllib.loads((ROOT / "backend" / "pyproject.toml").read_text())["project"]["version"]
ASSETS = ROOT / "desktop" / "assets"

a = Analysis(
    [str(ROOT / "desktop" / "main.py")],
    pathex=[str(ROOT / "backend")],
    datas=[(str(ROOT / "frontend" / "dist"), "web")],
    hiddenimports=[
        *collect_submodules("uvicorn"),
        "aiosqlite", "sqlalchemy.dialects.sqlite.aiosqlite", "argon2", "app.db.models",
    ],
    # Server-only pieces the standalone app never uses.
    excludes=["asyncpg", "alembic", "pytest", "tkinter", "PIL"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Cockpit",
    console=False,  # no terminal window
    icon=str(ASSETS / ("cockpit.icns" if sys.platform == "darwin" else "cockpit.ico")),
)
coll = COLLECT(exe, a.binaries, a.datas, name="Cockpit")

if sys.platform == "darwin":
    app = BUNDLE(
        coll, name="Cockpit.app", icon=str(ASSETS / "cockpit.icns"),
        bundle_identifier="app.cockpit.desktop", version=VERSION,
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "NSRequiresAquaSystemAppearance": False,  # follow light/dark mode
        },
    )
