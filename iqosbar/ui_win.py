"""Windows / Linux system-tray front-end (pystray).

A tray shows only an image, so the battery % is drawn into the icon
(see icon.tray_image). The dropdown repeats the same info lines as macOS.
"""

from __future__ import annotations

import threading
import time

import pystray
from pystray import Menu, MenuItem

from . import chart
from . import icon as iconmod
from .core import Poller

REFRESH_SECONDS = 20


class TrayApp:
    def __init__(self) -> None:
        self._poller = Poller()
        self._state = None
        self._stop = threading.Event()
        self._icon = pystray.Icon(
            "iqosbar",
            icon=iconmod.tray_image(None),
            title="IQOS Bar",
            menu=Menu(
                MenuItem(lambda i: self._line("device_line"), None, enabled=False),
                MenuItem(lambda i: self._line("today_line"), None, enabled=False),
                MenuItem(lambda i: self._line("spark_line"), None, enabled=False),
                MenuItem(lambda i: self._line("battery_line"), None, enabled=False),
                MenuItem(lambda i: self._line("total_line"), None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("Open chart…", lambda i: chart.open_chart()),
                MenuItem("Refresh now", lambda i: self._refresh()),
                MenuItem("Quit", lambda i: self._quit()),
            ),
        )

    def _line(self, field: str) -> str:
        if self._state is None:
            return "…"
        return getattr(self._state, field) or ""

    def _refresh(self) -> None:
        state = self._poller.poll()
        self._state = state
        self._icon.icon = iconmod.tray_image(state.badge)
        tooltip = "IQOS Bar"
        if state.connected:
            parts = [p for p in (state.battery_line, state.today_line) if p]
            tooltip = "  ·  ".join(parts) or tooltip
        self._icon.title = tooltip
        self._icon.update_menu()

    def _quit(self) -> None:
        self._stop.set()
        self._icon.stop()

    def _loop(self, icon) -> None:
        icon.visible = True
        while not self._stop.is_set():
            try:
                self._refresh()
            except Exception:
                pass
            self._stop.wait(REFRESH_SECONDS)

    def run(self) -> None:
        self._icon.run(setup=self._loop)


def main() -> None:
    TrayApp().run()


if __name__ == "__main__":
    main()
