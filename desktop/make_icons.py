"""Draws the app icon and writes desktop/assets/cockpit.{png,icns,ico}. Run with Pillow installed."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
MARGIN = 100  # macOS icons keep a transparent margin around the tile
BLUE = (47, 111, 222, 255)
WHITE = (255, 255, 255, 255)
# The favicon's line on a 32-unit grid.
POINTS = [(8, 21), (13, 15), (17, 18), (24, 9)]
STROKE = 2.6

out = Path(__file__).resolve().parent / "assets"
out.mkdir(exist_ok=True)

tile = SIZE - 2 * MARGIN
scale = tile / 32
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle((MARGIN, MARGIN, SIZE - MARGIN, SIZE - MARGIN), radius=int(tile * 0.225), fill=BLUE)
pts = [(MARGIN + x * scale, MARGIN + y * scale) for x, y in POINTS]
width = int(STROKE * scale)
draw.line(pts, fill=WHITE, width=width, joint="curve")
for x, y in pts:  # round caps and joins
    r = width / 2
    draw.ellipse((x - r, y - r, x + r, y + r), fill=WHITE)

img.save(out / "cockpit.png")
img.save(out / "cockpit.icns")
img.save(out / "cockpit.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icons written to", out)
