"""Generate the macOS menu bar template PNGs from the shared glyph.

Run after changing the glyph:  python tools/make_icons.py
Requires Pillow (build-time only; macOS runtime uses the PNGs).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iqosbar.icon import glyph_image  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "assets"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    glyph_image(1).save(OUT / "menubar.png")
    glyph_image(2).save(OUT / "menubar@2x.png")
    glyph_image(8).save(OUT / "icon-glyph.png")
    print("wrote menubar.png, menubar@2x.png, icon-glyph.png")


if __name__ == "__main__":
    main()
