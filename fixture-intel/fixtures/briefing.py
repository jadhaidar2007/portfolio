"""Morning briefing email: one glance at overnight fixtures and rate moves.

Email clients don't run JavaScript and many strip external images, so the
sparklines are inline SVG and all styles are inline.
"""
from __future__ import annotations

import datetime as dt
from html import escape

from .analytics import summary
from .models import Fixture


def sparkline(values: list[float], width: int = 120, height: int = 28) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = width / (len(values) - 1)
    pts = " ".join(f"{i * step:.1f},{height - 2 - (v - lo) / span * (height - 4):.1f}"
                   for i, v in enumerate(values))
    color = "#22c55e" if values[-1] >= values[0] else "#ef4444"
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg"><polyline fill="none" stroke="{color}" '
            f'stroke-width="2" points="{pts}"/></svg>')


def render(fixtures: list[Fixture], today: dt.date) -> str:
    s = summary(fixtures, today)
    cell = "padding:6px 10px;border-bottom:1px solid #1f2937"
    td = f'style="{cell}"'
    route_rows = "".join(
        f"<tr><td {td}>{escape(route)}</td><td {td}><b>WS {r['latest_ws']}</b></td>"
        f"<td style=\"{cell};color:{'#22c55e' if r['change'] >= 0 else '#ef4444'}\">"
        f"{r['change']:+}</td><td {td}>{sparkline(r['series'])}</td></tr>"
        for route, r in sorted(s["routes"].items())
    )
    todays = [f for f in fixtures if f.reported_on == today]
    fx_rows = "".join(
        f"<tr><td {td}>{escape(f.vessel)}</td><td {td}>{f.size_kt}kt</td>"
        f"<td {td}>{escape(f.route)}</td><td {td}>{escape(f.laycan)}</td>"
        f"<td {td}>{'WS %g' % f.rate if f.rate_type == 'WS' else '$%.2fm' % (f.rate / 1e6)}</td>"
        f"<td {td}>{escape(f.charterer)}</td><td {td}>{f.status}</td></tr>"
        for f in todays
    )
    return f"""<html><body style="margin:0;background:#0b1220;color:#e5e7eb;font-family:Arial,sans-serif">
<div style="max-width:720px;margin:0 auto;padding:24px">
<h2 style="margin:0 0 4px">Tanker fixtures — morning briefing</h2>
<div style="color:#9ca3af;margin-bottom:18px">{today:%A %d %B %Y} · {s['today']} new reports · {s['failed_today']} failed · demo data</div>
<h3 style="margin:18px 0 6px">Rates by route</h3>
<table style="border-collapse:collapse;width:100%">{route_rows}</table>
<h3 style="margin:18px 0 6px">Reported today</h3>
<table style="border-collapse:collapse;width:100%;font-size:13px">{fx_rows or '<tr><td>No fixtures reported today.</td></tr>'}</table>
</div></body></html>"""
