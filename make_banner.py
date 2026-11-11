"""Builds assets/banner.png from assets/cover_source.jpg (user-provided artwork).

Removes the trademarked marks from the source (game logo, age-rating badge, sponsor, crest and
shorts logo) by normalized-convolution inpainting, then adds this project's own title and fades
the bottom into the UI background.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
SRC = HERE / "assets" / "cover_source.jpg"   # original with marks: local only, not committed
CLEAN = HERE / "assets" / "cover_clean.jpg"  # marks removed: committed
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "assets" / "banner.png")
W, H = 1280, 480
BG = (20, 22, 28)

# Regions to remove, in source pixels (1024x377): (box, is_ellipse)
REMOVE = [
    ((12, 264, 94, 370), False),    # age-rating badge + "PROVISIONAL"
    ((400, 238, 620, 338), False),  # game logo
    ((398, 158, 516, 212), False),  # sponsor text
    ((470, 108, 514, 160), True),   # crest + star
    ((556, 350, 596, 377), True),   # shorts logo
]


def box_blur(a, r):
    """Approximate Gaussian blur of a float array (H, W[, C]) with three separable box passes."""
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0)] * a.ndim
            pad[axis] = (r + 1, r)
            c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
            hi = np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)
            a = (hi - lo) / (2 * r + 1)
    return a


def inpaint(img, mask):
    """Fills mask>0 with values diffused from the surrounding pixels (normalized convolution)."""
    a = np.asarray(img, dtype=np.float32)
    known = (np.asarray(mask) == 0).astype(np.float32)
    out = a.copy()
    for radius in (2, 4, 8, 14, 24, 40):
        num = box_blur(out * known[..., None], radius)
        den = box_blur(known, radius)[..., None]
        fill = num / np.maximum(den, 1e-4)
        newly = (known == 0) & (den[..., 0] > 0.05)
        out[newly] = fill[newly]
        known = np.maximum(known, newly.astype(np.float32))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


if SRC.exists():
    src = Image.open(SRC).convert("RGB")
    mask = Image.new("L", src.size)
    md = ImageDraw.Draw(mask)
    for box, ellipse in REMOVE:
        (md.ellipse if ellipse else md.rectangle)(box, fill=255)
    clean = inpaint(src, mask)
    # Light grain over the filled areas so they don't look flat
    grain = Image.effect_noise(src.size, 10).convert("RGB")
    grainy = Image.blend(clean, Image.composite(grain, clean, Image.new("L", src.size, 40)), 0.15)
    clean = Image.composite(grainy, clean, mask.filter(ImageFilter.GaussianBlur(3)))
    clean.save(CLEAN, quality=95)
clean = Image.open(CLEAN).convert("RGB")

img = clean.resize((W, H), Image.LANCZOS)

# Fade the bottom into the UI background
fade = Image.new("RGB", (W, H), BG)
fmask = Image.new("L", (W, H))
fd = ImageDraw.Draw(fmask)
for y in range(H):
    t = max(0.0, (y - H * 0.7) / (H * 0.3))
    fd.line([(0, y), (W, y)], fill=int(255 * t ** 1.4))
img = Image.composite(fade, img, fmask)

# Our own title where the logo was
font_path = next((p for p in (Path(r"C:\Windows\Fonts\ariblk.ttf"), Path(r"C:\Windows\Fonts\seguibl.ttf"),
                              Path(r"C:\Windows\Fonts\seguisb.ttf")) if p.exists()), None)
if font_path:
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(font_path), 92)
    text = "FIFA 14"
    tw = d.textlength(text, font=font)
    cx = 510 * W / 1024
    x, y = cx - tw / 2, H * 0.62
    d.text((x, y), text, font=font, fill=(14, 14, 18), stroke_width=6, stroke_fill=(255, 255, 255))
    small_path = Path(r"C:\Windows\Fonts\seguisb.ttf")
    if small_path.exists():
        small = ImageFont.truetype(str(small_path), 24)
        sub = "PS4  ·  PC INSTALLER"
        sw = d.textlength(sub, font=small)
        d.text((cx - sw / 2, y + 120), sub, font=small, fill=(62, 196, 109))

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print("banner:", OUT)
