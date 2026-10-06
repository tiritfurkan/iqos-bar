"""Render the per-device daily-use dashboard as a self-contained HTML file."""

from __future__ import annotations

import os
import subprocess
import sys

from . import history

CHART_FILE = history.HISTORY_DIR / "chart.html"

# Minimal line icons (inherit currentColor), 24x24 viewBox.
ICONS = {
    "stick": '<path d="M4 15h13a3 3 0 0 1 0 6H4zM17 15h3v6h-3z" '
             'fill="none" stroke="currentColor" stroke-width="1.6" '
             'stroke-linejoin="round"/>',
    "puff": '<path d="M7 16c-2 0-3-1.3-3-3 0-1.6 1.2-2.8 2.8-2.9C7.2 7.7 9.3 6 '
            '12 6c2.5 0 4.6 1.6 5.1 3.9H18a3 3 0 0 1 0 6z" fill="none" '
            'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    "battery": '<rect x="3" y="8" width="16" height="9" rx="2.2" fill="none" '
               'stroke="currentColor" stroke-width="1.6"/>'
               '<rect x="20" y="11" width="2.2" height="3" rx="1" '
               'fill="currentColor"/>',
    "today": '<rect x="4" y="5" width="16" height="15" rx="2.4" fill="none" '
             'stroke="currentColor" stroke-width="1.6"/>'
             '<path d="M4 9h16M8 3v3M16 3v3" stroke="currentColor" '
             'stroke-width="1.6" stroke-linecap="round"/>',
    "avg": '<path d="M4 18l5-6 4 3 7-8" fill="none" stroke="currentColor" '
           'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
}


def _icon(name: str) -> str:
    return f'<svg viewBox="0 0 24 24" class="ic">{ICONS[name]}</svg>'


def _short(serial: str) -> str:
    if serial == history.UNKNOWN_SERIAL:
        return "Unknown device"
    return serial[-6:]


def _stat(icon: str, value, label: str) -> str:
    v = "—" if value is None else value
    return (
        f'<div class="stat">{_icon(icon)}<div><div class="big">{v}</div>'
        f'<div class="k">{label}</div></div></div>'
    )


def _bars_svg(series, accent: str) -> str:
    width, height = 680, 170
    pad_l, pad_b, pad_t = 30, 34, 18
    n = len(series)
    values = [v for _, v in series if v is not None]
    vmax = max(values + [1])
    plot_w, plot_h = width - pad_l - 14, height - pad_b - pad_t
    slot = plot_w / n
    bar_w = slot * 0.58

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for frac in (0, 0.5, 1):
        y = pad_t + plot_h * (1 - frac)
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width-14}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l-7}" y="{y+4:.1f}" class="ylab">{round(vmax*frac)}</text>')
    for i, (day, value) in enumerate(series):
        x = pad_l + slot * i + (slot - bar_w) / 2
        if value is None:
            parts.append(f'<rect x="{x:.1f}" y="{pad_t+plot_h-3:.1f}" width="{bar_w:.1f}" height="3" rx="1.5" class="nodata"/>')
        else:
            h = plot_h * (value / vmax)
            y = pad_t + plot_h - h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{accent}"><title>{day.isoformat()}: {value}</title></rect>')
            if value:
                parts.append(f'<text x="{x+bar_w/2:.1f}" y="{y-4:.1f}" class="vlab">{value}</text>')
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{height-pad_b+16}" class="xlab">{day.day}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _device_section(dev: dict, days: int) -> str:
    serial = dev["serial"]
    sticks_series = history.daily_series(serial, "sticks", days)
    puffs_series = history.daily_series(serial, "puffs", days)
    model = dev.get("name") or dev.get("model") or "IQOS"
    ppS = (round(dev["puffs"] / dev["sticks"], 1)
           if dev.get("sticks") and dev.get("puffs") else None)
    return f"""
    <section class="device">
      <div class="dhead">
        <div class="dot"></div>
        <h2>{model}</h2><span class="serial">#{_short(serial)}</span>
      </div>
      <div class="stats">
        {_stat("today", history.today_count(serial, "sticks"), "today (sticks)")}
        {_stat("avg", history.daily_average(serial, "sticks", days), "daily avg")}
        {_stat("stick", dev.get("sticks"), "lifetime sticks")}
        {_stat("puff", dev.get("puffs"), "lifetime puffs")}
        {_stat("battery", ppS, "puffs / stick")}
      </div>
      <div class="chart"><h3>STICKS PER DAY</h3>{_bars_svg(sticks_series, "var(--accent)")}</div>
      <div class="chart"><h3>PUFFS PER DAY</h3>{_bars_svg(puffs_series, "var(--accent)")}</div>
    </section>"""


def build(days: int = 14) -> "history.Path":
    devs = history.devices()
    if not devs:
        sections = '<p class="empty">Plug in a device to start tracking.</p>'
    else:
        sections = "".join(_device_section(d, days) for d in devs)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>IQOS daily use</title>
<style>
  :root {{
    --bg:#f5f5f7; --card:#fff; --ink:#15151a; --sub:#73737c;
    --grid:#ececf1; --accent:#e8622c; --accent2:#d3d6dd; --line:#ececf1;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg:#0f0f13; --card:#1a1a20; --ink:#f3f3f6; --sub:#9a9aa4;
      --grid:#26262d; --accent:#ff7a45; --accent2:#34343c; --line:#26262d;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg:#0f0f13; --card:#1a1a20; --ink:#f3f3f6; --sub:#9a9aa4;
    --grid:#26262d; --accent:#ff7a45; --accent2:#34343c; --line:#26262d;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); padding:28px 16px 40px;
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:760px; margin:0 auto; }}
  .title {{ display:flex; align-items:center; gap:10px; margin:0 0 4px; }}
  .title svg {{ width:26px; height:26px; color:var(--accent); }}
  h1 {{ font-size:19px; margin:0; letter-spacing:-.01em; }}
  .lead {{ color:var(--sub); font-size:13px; margin:0 0 24px; }}
  .device {{ background:var(--card); border-radius:18px; padding:20px;
    margin-bottom:18px; border:1px solid var(--line); }}
  .dhead {{ display:flex; align-items:center; gap:9px; margin-bottom:16px; }}
  .dhead h2 {{ font-size:16px; margin:0; }}
  .dot {{ width:9px; height:9px; border-radius:50%; background:var(--accent); }}
  .serial {{ color:var(--sub); font-size:12px; font-variant-numeric:tabular-nums;
    margin-left:auto; letter-spacing:.03em; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(118px,1fr));
    gap:10px; margin-bottom:20px; }}
  .stat {{ display:flex; gap:9px; align-items:center; background:var(--bg);
    border-radius:13px; padding:12px 13px; }}
  .stat .ic {{ width:22px; height:22px; color:var(--accent); flex:none; }}
  .big {{ font-size:23px; font-weight:650; line-height:1.1; letter-spacing:-.02em;
    font-variant-numeric:tabular-nums; }}
  .k {{ color:var(--sub); font-size:11px; text-transform:uppercase;
    letter-spacing:.04em; margin-top:1px; }}
  .chart {{ margin-top:14px; }}
  .chart h3 {{ font-size:11px; color:var(--sub); margin:0 0 4px 4px;
    font-weight:650; letter-spacing:.06em; }}
  .grid {{ stroke:var(--grid); stroke-width:1; }}
  .ylab {{ fill:var(--sub); font-size:10px; text-anchor:end; }}
  .xlab {{ fill:var(--sub); font-size:10px; text-anchor:middle; }}
  .vlab {{ fill:var(--ink); font-size:10px; text-anchor:middle; font-weight:650; }}
  .nodata {{ fill:var(--accent2); }}
  .empty {{ color:var(--sub); text-align:center; padding:40px; }}
  footer {{ color:var(--sub); font-size:11px; margin-top:12px; text-align:center; }}
</style></head>
<body><div class="wrap">
  <div class="title"><svg viewBox="0 0 24 24">{ICONS['stick']}</svg><h1>IQOS daily use</h1></div>
  <p class="lead">Per-device, derived from lifetime counters logged on each plug-in.
     Faint marks are days without enough data yet — the chart fills in as you use it.</p>
  {sections}
  <footer>IQOS Bar · all data stays on this Mac</footer>
</div></body></html>
"""
    history.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    CHART_FILE.write_text(html)
    return CHART_FILE


def open_chart(days: int = 14) -> None:
    path = str(build(days))
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", path], check=False)


if __name__ == "__main__":
    open_chart()
