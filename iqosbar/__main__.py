"""Entry point: launch the right UI for this OS.

    python -m iqosbar
"""

from __future__ import annotations

import sys


def main() -> None:
    if sys.platform == "darwin":
        from .ui_mac import main as ui_main
    else:
        from .ui_win import main as ui_main
    ui_main()


if __name__ == "__main__":
    main()
