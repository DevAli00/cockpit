# PyInstaller spec for the Cockpit desktop app (macOS .app and Windows folder build).
import sys
import sysconfig
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
VERSION = tomllib.loads((ROOT / "backend" / "pyproject.toml").read_text())["project"]["version"]
ASSETS = ROOT / "desktop" / "assets"


def min_macos() -> str:
    """The oldest macOS this build can run on: the bundled Python's own target (never below 11)."""
    major, _, minor = str(sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET") or "11.0").partition(".")
    version = max((int(major), int(minor or 0)), (11, 0))
    return f"{version[0]}.{version[1]}"


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
# Windows file properties (Details tab): product name and version, also required for code signing.
version_file = None
if sys.platform == "win32":
    nums = tuple(int(n) for n in VERSION.split(".")) + (0,)
    strings = {
        "CompanyName": "Cockpit", "ProductName": "Cockpit", "ProductVersion": VERSION,
        "FileDescription": "Cockpit", "FileVersion": VERSION, "InternalName": "Cockpit",
        "OriginalFilename": "Cockpit.exe", "LegalCopyright": "MIT License",
    }
    table = ", ".join(f"StringStruct({k!r}, {v!r})" for k, v in strings.items())
    version_file = Path(workpath) / "version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={nums}, prodvers={nums}), kids=["
        f"StringFileInfo([StringTable('040904B0', [{table}])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n",
        encoding="utf-8",
    )

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Cockpit",
    console=False,  # no terminal window
    icon=str(ASSETS / ("cockpit.icns" if sys.platform == "darwin" else "cockpit.ico")),
    version=str(version_file) if version_file else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Cockpit")

if sys.platform == "darwin":
    app = BUNDLE(
        coll, name="Cockpit.app", icon=str(ASSETS / "cockpit.icns"),
        bundle_identifier="app.cockpit.desktop", version=VERSION,
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": min_macos(),
            "NSRequiresAquaSystemAppearance": False,  # follow light/dark mode
        },
    )
