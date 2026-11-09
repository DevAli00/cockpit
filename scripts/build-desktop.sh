#!/usr/bin/env bash
# Builds the macOS app and .dmg into dist-desktop/. Run on the Mac architecture you want to target.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-backend/.venv/bin/python}"
VERSION=$("$PY" -c "import tomllib;print(tomllib.load(open('backend/pyproject.toml','rb'))['project']['version'])")
ARCH=$(uname -m)   # arm64 = Apple Silicon, x86_64 = Intel
WORK=build/desktop

echo "== web app"
(cd frontend && { [ -d node_modules ] || npm ci; } && npm run build)

echo "== icons"
[ -f desktop/assets/cockpit.icns ] || "$PY" desktop/make_icons.py

echo "== app bundle"
rm -rf "$WORK"
"$PY" -m PyInstaller desktop/cockpit.spec --noconfirm --distpath "$WORK/dist" --workpath "$WORK/work"

echo "== minimum macOS"
APP="$WORK/dist/Cockpit.app"
MIN=$(/usr/libexec/PlistBuddy -c "Print :LSMinimumSystemVersion" "$APP/Contents/Info.plist")
NEEDED=$(find "$APP" -type f -exec vtool -show-build {} \; 2>/dev/null | awk '/minos/{print $2}' | sort -t. -k1,1n -k2,2n | tail -1)
echo "declared: macOS $MIN   highest required by a bundled file: macOS ${NEEDED:-unknown}"
"$PY" - "$MIN" "${NEEDED:-0}" <<'PYEOF'
import sys
as_tuple = lambda v: tuple(int(p) for p in v.split(".")[:2])
if as_tuple(sys.argv[2]) > as_tuple(sys.argv[1]):
    sys.exit(f"error: a bundled file needs macOS {sys.argv[2]} but the app declares {sys.argv[1]}")
PYEOF

echo "== disk image"
STAGE="$WORK/dmg"
mkdir -p "$STAGE" dist-desktop
cp -R "$WORK/dist/Cockpit.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp desktop/assets/READ-ME-FIRST.txt "$STAGE/"
OUT="dist-desktop/Cockpit-$VERSION-mac-$ARCH.dmg"
rm -f "$OUT"
hdiutil create -volname "Cockpit" -srcfolder "$STAGE" -ov -format UDZO "$OUT" >/dev/null
echo "$MIN" > "dist-desktop/Cockpit-$VERSION-mac-$ARCH.min-macos.txt"
echo "built $OUT (macOS $MIN or newer)"
