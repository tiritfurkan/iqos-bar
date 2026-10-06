"""Draw the app icon (AppIcon.png + AppIcon.icns for macOS, AppIcon.ico for Windows).

Uses the same heat-stick glyph as the menu bar icon, on a dark rounded tile
following the macOS icon grid (824px tile on a 1024px canvas).

    python tools/make_app_icon.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iqosbar.icon import glyph_image  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ACCENT = (255, 122, 69)


def tile(size: int = 1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inset = round(size * 100 / 1024)
    side = size - 2 * inset
    radius = round(side * 0.225)

    # Soft drop shadow, as macOS icons have.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [inset, inset + size * 0.012, inset + side, inset + side + size * 0.012],
        radius=radius, fill=(0, 0, 0, 110))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(size * 0.018)))

    # Vertical charcoal gradient with a warm glow in the top right.
    body = Image.new("RGBA", (side, side))
    px = body.load()
    for y in range(side):
        t = y / side
        base = (int(44 - 22 * t), int(44 - 22 * t), int(52 - 24 * t))
        for x in range(side):
            dx, dy = (x - side * 0.85) / side, (y - side * 0.1) / side
            glow = max(0.0, 1 - (dx * dx + dy * dy) ** 0.5 / 0.75) ** 2 * 0.55
            px[x, y] = tuple(int(b + (a - b) * glow) for a, b in zip(ACCENT, base)) + (255,)
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, side - 1, side - 1], radius=radius, fill=255)
    canvas.paste(body, (inset, inset), mask)

    # Hairline highlight on the tile edge.
    ImageDraw.Draw(canvas).rounded_rectangle(
        [inset, inset, inset + side - 1, inset + side - 1], radius=radius,
        outline=(255, 255, 255, 28), width=max(1, size // 512))

    # Glyph: white stick with the lit tip and smoke dots in orange.
    scale = side * 0.78 / 22
    white = glyph_image(scale, (255, 255, 255, 255))
    orange = glyph_image(scale, ACCENT + (255,))
    # Keep the tip and smoke dots orange, the capsule outline white.
    cut = round(13.2 * scale)
    glyph = white.copy()
    glyph.paste(orange.crop((cut, 0, orange.width, orange.height)), (cut, 0))
    dots = orange.crop((0, 0, cut, round(5.2 * scale)))
    glyph.paste(dots, (0, 0))
    glyph = glyph.crop(glyph.getbbox())  # centre what is visible, not the canvas
    gx = (size - glyph.width) // 2
    gy = (size - glyph.height) // 2
    canvas.alpha_composite(glyph, (gx, gy))
    return canvas


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    big = tile(1024)
    big.save(ASSETS / "AppIcon.png")

    # Windows .ico
    big.save(ASSETS / "AppIcon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                                          (128, 128), (256, 256)])

    # macOS .icns via iconutil (only available on macOS)
    if shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as tmp:
            iconset = Path(tmp) / "AppIcon.iconset"
            iconset.mkdir()
            for pt in (16, 32, 128, 256, 512):
                for mult in (1, 2):
                    px = pt * mult
                    name = f"icon_{pt}x{pt}{'@2x' if mult == 2 else ''}.png"
                    big.resize((px, px), Image.LANCZOS).save(iconset / name)
            subprocess.run(["iconutil", "-c", "icns", str(iconset),
                            "-o", str(ASSETS / "AppIcon.icns")], check=True)
    print("wrote AppIcon.png, AppIcon.ico" + (", AppIcon.icns" if shutil.which("iconutil") else ""))


if __name__ == "__main__":
    main()
