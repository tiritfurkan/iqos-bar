"""Shared icon rendering.

- The heat-stick glyph (also exported to PNG by tools/make_icons.py).
- A tray icon for Windows/Linux with the battery % drawn into it, since a
  system tray shows only an image (no adjacent text like the macOS menu bar).

Pillow is imported lazily so macOS (which uses the pre-rendered template PNG)
does not need it at runtime.
"""

from __future__ import annotations


def _draw_glyph(draw, scale: float, color) -> None:
    s = scale
    x0, y0, x1, y1 = 2 * s, 7.5 * s, 16 * s, 13.5 * s
    r = (y1 - y0) / 2
    lw = max(1, round(1.5 * s))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=color, width=lw)
    draw.rounded_rectangle([13.5 * s, y0, 16 * s, y1], radius=r * 0.6, fill=color)
    draw.ellipse([7.5 * s - 1.2 * s, 3.4 * s - 1.2 * s,
                  7.5 * s + 1.2 * s, 3.4 * s + 1.2 * s], fill=color)
    draw.ellipse([11 * s - 1.0 * s, 1.6 * s - 1.0 * s,
                  11 * s + 1.0 * s, 1.6 * s + 1.0 * s], fill=color[:3] + (210,))


def glyph_image(scale: float = 8, color=(0, 0, 0, 255)):
    """The bare glyph on a transparent canvas (22x16 points * scale)."""
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (int(22 * scale), int(16 * scale)), (0, 0, 0, 0))
    _draw_glyph(ImageDraw.Draw(im), scale, color)
    return im


def tray_image(badge: str | None, size: int = 64, color=(255, 255, 255, 255)):
    """A square tray icon: glyph on top, battery % text below.

    White by default, which reads on the typically dark Windows taskbar and
    most Linux panels.
    """
    from PIL import Image, ImageDraw, ImageFont

    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Glyph centred in the top portion.
    gscale = size / 22 * 0.62
    glyph = glyph_image(gscale, color)
    gx = (size - glyph.width) // 2
    im.alpha_composite(glyph, (gx, int(size * 0.04)))

    if badge:
        try:
            font = ImageFont.truetype("arialbd.ttf", int(size * 0.34))
        except OSError:
            try:
                font = ImageFont.truetype(
                    "DejaVuSans-Bold.ttf", int(size * 0.34))
            except OSError:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), badge, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size - tw) / 2 - bbox[0], size * 0.52 - bbox[1]),
                  badge, font=font, fill=color)
    return im
