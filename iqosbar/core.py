"""Shared state logic used by every platform UI.

A UI calls `Poller.poll()` on a timer and renders the returned `UiState`.
All device reading, history logging and string formatting live here, so the
macOS and Windows/Linux front-ends stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import history
from .reader import IqosReader

MINI_DAYS = 7
MINI_BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int | None]) -> str:
    known = [v for v in values if v is not None]
    hi = max(known) if known else 0
    out = []
    for v in values:
        if v is None:
            out.append("·")
        elif hi == 0:
            out.append(MINI_BLOCKS[0])
        else:
            out.append(MINI_BLOCKS[round((v / hi) * (len(MINI_BLOCKS) - 1))])
    return "".join(out)


def _display_name(product: str | None, model: str | None) -> str:
    if product:
        name = product.strip()
        return name[5:] if name.upper().startswith("IQOS ") else name
    return model or "IQOS"


def _short(serial: str) -> str:
    return serial[-6:] if serial != history.UNKNOWN_SERIAL else "unknown"


@dataclass
class UiState:
    connected: bool
    # Short text for the menu bar / tray icon badge, e.g. "92%" or None.
    badge: str | None
    battery_percent: int | None
    today_line: str
    spark_line: str
    battery_line: str
    total_line: str
    device_line: str
    # Structured values for richer UIs (the macOS panel). When the device is
    # unplugged these describe the last device we saw.
    today: int | None = None
    series: list[int | None] = field(default_factory=list)
    device_name: str = ""
    serial_short: str = ""
    sticks: int | None = None
    puffs: int | None = None


class Poller:
    """Reads the device, logs history, and formats display state."""

    def __init__(self) -> None:
        self._reader = IqosReader()

    def poll(self) -> UiState:
        snap = self._reader.read()

        if not snap.connected:
            return self._last_known()

        name = _display_name(snap.product, snap.model_code)
        history.record(snap.serial, snap.model_code,
                       snap.total_sticks, snap.total_puffs, name=name)

        serial = snap.serial or history.UNKNOWN_SERIAL
        today = history.today_count(serial, "sticks")
        series = [v for _, v in history.daily_series(serial, "sticks", MINI_DAYS)]

        badge = f"{snap.battery_percent}%" if snap.battery_percent is not None else None

        if today is not None:
            today_line = f"Today: {today} sticks"
        else:
            today_line = "Today: collecting data…"

        if snap.battery_percent is not None:
            battery_line = f"Battery: {snap.battery_percent}%"
        elif snap.voltage_mv is not None:
            battery_line = f"Battery: {snap.voltage_mv} mV"
        else:
            battery_line = "Battery: —"

        if snap.total_sticks is not None:
            total_line = (
                f"Lifetime: {snap.total_sticks} sticks, {snap.total_puffs} puffs"
            )
        else:
            total_line = ""

        return UiState(
            connected=True, badge=badge, battery_percent=snap.battery_percent,
            today_line=today_line,
            spark_line=f"Last {MINI_DAYS}d: {sparkline(series)}",
            battery_line=battery_line, total_line=total_line,
            device_line=f"{name} · #{_short(serial)}",
            today=today, series=series, device_name=name,
            serial_short=_short(serial),
            sticks=snap.total_sticks, puffs=snap.total_puffs,
        )

    def _last_known(self) -> UiState:
        """Not connected: still show today's numbers for the last device seen."""
        state = UiState(
            connected=False, badge=None, battery_percent=None,
            today_line="Device not connected", spark_line="",
            battery_line="", total_line="", device_line="",
        )
        devices = history.devices()
        if not devices:
            return state
        dev = devices[0]
        serial = dev["serial"]
        state.today = history.today_count(serial, "sticks")
        state.series = [v for _, v in history.daily_series(serial, "sticks", MINI_DAYS)]
        state.device_name = dev.get("name") or dev.get("model") or "IQOS"
        state.serial_short = _short(serial)
        state.sticks = dev.get("sticks")
        state.puffs = dev.get("puffs")
        return state
