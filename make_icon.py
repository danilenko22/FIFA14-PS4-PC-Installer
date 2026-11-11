"""Generates assets/app.ico: a football on a pitch-green tile (original artwork, no logos)."""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "assets" / "app.ico")
size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, size - 8, size - 8], radius=48, fill=(30, 120, 56, 255))
for i in range(6):  # mowing stripes
    if i % 2:
        y0 = 8 + i * (size - 16) / 6
        d.rectangle([8, y0, size - 8, y0 + (size - 16) / 6], fill=(38, 138, 64, 255))
d.rounded_rectangle([8, 8, size - 8, size - 8], radius=48, outline=(20, 22, 28, 255), width=6)
cx, cy, r = size // 2, size // 2, 84
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 246, 246, 255), outline=(20, 22, 28, 255), width=6)
dark = (24, 24, 30, 255)
d.regular_polygon((cx, cy, 30), 5, rotation=0, fill=dark)
for k in range(5):
    a = -math.pi / 2 + k * math.tau / 5
    px, py = cx + math.cos(a) * 66, cy + math.sin(a) * 66
    d.regular_polygon((px, py, 20), 5, rotation=36, fill=dark)
    d.line([(cx + math.cos(a) * 30, cy + math.sin(a) * 30), (px, py)], fill=dark, width=5)
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
print("icon:", out)
