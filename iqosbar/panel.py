"""HTML for the macOS popover panel.

The popover itself draws the background and arrow, so the page is transparent
and follows the system light/dark appearance. Buttons talk back to Python via
`window.webkit.messageHandlers.iqos.postMessage(...)`.
"""

from __future__ import annotations

from html import escape

from .chart import ICONS
from .core import UiState


def _icon(name: str) -> str:
    return f'<svg viewBox="0 0 24 24" class="ic">{ICONS[name]}</svg>'


def _bars(series: list[int | None]) -> str:
    known = [v for v in series if v is not None]
    hi = max(known) if known else 0
    out = []
    for v in series:
        if v is None or hi == 0:
            out.append('<i class="bar none"></i>')
        else:
            pct = max(14, round(100 * v / hi))
            out.append(f'<i class="bar" style="height:{pct}%" title="{v}"></i>')
    return "".join(out)


def _fmt(n: int | None) -> str:
    return "—" if n is None else f"{n:,}"


def render(state: UiState) -> str:
    has_device = bool(state.device_name)

    if has_device:
        head = f"{escape(state.device_name)} · #{escape(state.serial_short)}"
    else:
        head = "IQOS Bar"

    if state.today is not None:
        today = f'Today: {state.today} sticks'
    elif has_device:
        today = 'Today: <span class="soft">collecting data…</span>'
    else:
        today = 'No device yet'

    rows = [f'<div class="row head">{head}</div>']
    rows.append(f'<div class="row strong">{_icon("today")}<span>{today}</span></div>')

    if has_device:
        rows.append(
            f'<div class="row"><span class="muted">Last 7d</span>'
            f'<span class="bars">{_bars(state.series)}</span></div>'
        )

    rows.append('<div class="sep"></div>')

    if state.connected:
        battery = (f"Battery: {state.battery_percent}%"
                   if state.battery_percent is not None else "Battery: —")
        rows.append(f'<div class="row">{_icon("battery")}<span>{battery}</span></div>')
    else:
        rows.append(f'<div class="row">{_icon("battery")}'
                    f'<span class="muted">Plug in over USB to read battery</span></div>')

    if state.sticks is not None:
        rows.append(
            f'<div class="row indent"><span class="muted">Lifetime: '
            f'{_fmt(state.sticks)} sticks, {_fmt(state.puffs)} puffs</span></div>'
        )

    rows.append('<div class="sep"></div>')
    rows.append('<button class="row act" data-a="chart">Open chart…</button>')
    rows.append('<button class="row act" data-a="refresh">Refresh now</button>')
    rows.append('<button class="row act" data-a="quit">Quit</button>')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  :root {{
    --ink:#1d1d22; --muted:#5f5f69; --soft:#8c8c96;
    --accent:#e8622c; --sep:rgba(0,0,0,.09); --hover:rgba(0,0,0,.06);
    --bar-none:rgba(0,0,0,.10);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --ink:#f2f2f5; --muted:#c3c3cc; --soft:#8f8f99;
      --accent:#ff7a45; --sep:rgba(255,255,255,.08); --hover:rgba(255,255,255,.07);
      --bar-none:rgba(255,255,255,.12);
    }}
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  html, body {{ background:transparent; }}
  body {{
    font:13px/1.35 -apple-system,BlinkMacSystemFont,sans-serif;
    color:var(--ink); padding:8px; width:300px;
    -webkit-user-select:none; cursor:default;
    -webkit-font-smoothing:antialiased;
  }}
  .row {{ display:flex; align-items:center; gap:10px; padding:7px 9px;
    border-radius:8px; min-height:30px; }}
  .row.head {{ color:var(--soft); font-size:11.5px; letter-spacing:.02em;
    min-height:24px; padding-top:4px; }}
  .row.strong {{ font-size:14px; font-weight:650; }}
  .row.indent {{ padding-left:36px; }}
  .ic {{ width:17px; height:17px; color:var(--accent); flex:none; }}
  .muted {{ color:var(--muted); }}
  .soft {{ color:var(--soft); font-weight:500; }}
  .bars {{ display:flex; align-items:flex-end; gap:3px; height:18px; }}
  .bar {{ display:block; width:11px; background:var(--accent);
    border-radius:2px; }}
  .bar.none {{ height:3px; background:var(--bar-none); }}
  .sep {{ height:1px; background:var(--sep); margin:5px 8px; }}
  button.act {{ all:unset; display:flex; align-items:center; width:100%;
    box-sizing:border-box; padding:6px 9px; min-height:28px;
    border-radius:7px; color:var(--muted); }}
  button.act:hover {{ background:var(--hover); color:var(--ink); }}
</style></head>
<body>
{"".join(rows)}
<script>
  const post = (m) => {{
    try {{ window.webkit.messageHandlers.iqos.postMessage(m); }} catch (e) {{}}
  }};
  document.querySelectorAll("button.act").forEach((b) =>
    b.addEventListener("click", () => post(b.dataset.a)));
  document.addEventListener("contextmenu", (e) => e.preventDefault());
  addEventListener("load", () => post("h:" + document.body.scrollHeight));
</script>
</body></html>"""
