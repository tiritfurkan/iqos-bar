"""Backwards-compatible entry point.

Prefer `python -m iqosbar`. This keeps `python -m iqosbar.app` working by
delegating to the platform-appropriate UI.
"""

from __future__ import annotations

from .__main__ import main

if __name__ == "__main__":
    main()
