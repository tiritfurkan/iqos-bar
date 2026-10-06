"""Per-device history of lifetime counters, and derived per-day consumption.

The device reports only *lifetime* totals, so to chart "sticks per day" we
record each reading (timestamp + totals) locally and difference between days.
History is keyed by device serial, so multiple devices stay separate. All
data stays on this machine, in ~/.iqosbar/history.jsonl.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

HISTORY_DIR = Path.home() / ".iqosbar"
HISTORY_FILE = HISTORY_DIR / "history.jsonl"

UNKNOWN_SERIAL = "unknown"


def record(serial: str | None, model: str | None,
           total_sticks: int | None, total_puffs: int | None,
           name: str | None = None) -> None:
    """Append a reading for a device. No-op if both counters are missing."""
    if total_sticks is None and total_puffs is None:
        return
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "serial": serial or UNKNOWN_SERIAL,
        "model": model,
        "name": name,
        "sticks": total_sticks,
        "puffs": total_puffs,
    }
    with HISTORY_FILE.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _load() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    rows = []
    for line in HISTORY_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _rows_for(serial: str) -> list[dict]:
    return [r for r in _load() if r.get("serial", UNKNOWN_SERIAL) == serial]


def devices() -> list[dict]:
    """One summary row per known device, most-recently-seen first."""
    latest: dict[str, dict] = {}
    for row in _load():
        serial = row.get("serial", UNKNOWN_SERIAL)
        prev = latest.get(serial)
        if prev is None or row["ts"] >= prev["ts"]:
            latest[serial] = row
    out = [
        {
            "serial": serial,
            "model": row.get("model"),
            "name": row.get("name"),
            "sticks": row.get("sticks"),
            "puffs": row.get("puffs"),
            "last_seen": row["ts"],
        }
        for serial, row in latest.items()
    ]
    out.sort(key=lambda d: d["last_seen"], reverse=True)
    return out


def _last_per_day(rows: list[dict], field: str) -> dict[date, int]:
    by_day: dict[date, int] = {}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        day = datetime.fromisoformat(row["ts"]).date()
        by_day[day] = max(by_day.get(day, value), value)
    return by_day


def daily_series(serial: str, field: str = "sticks",
                 days: int = 14) -> list[tuple[date, int | None]]:
    """Per-day consumption for a device over the last `days` days."""
    by_day = _last_per_day(_rows_for(serial), field)
    today = date.today()
    if not by_day:
        return [(today - timedelta(days=i), None) for i in range(days - 1, -1, -1)]

    consumption: dict[date, int] = {}
    prev_day = None
    for day in sorted(by_day):
        if prev_day is not None:
            delta = by_day[day] - by_day[prev_day]
            if delta >= 0:
                consumption[day] = delta
        prev_day = day

    return [
        (today - timedelta(days=i), consumption.get(today - timedelta(days=i)))
        for i in range(days - 1, -1, -1)
    ]


def today_count(serial: str, field: str = "sticks") -> int | None:
    by_day = _last_per_day(_rows_for(serial), field)
    today = date.today()
    if today not in by_day:
        return None
    earlier = [d for d in by_day if d < today]
    if not earlier:
        return None
    return max(0, by_day[today] - by_day[max(earlier)])


def daily_average(serial: str, field: str = "sticks", days: int = 14) -> float | None:
    known = [v for _, v in daily_series(serial, field, days) if v is not None]
    if not known:
        return None
    return round(sum(known) / len(known), 1)
