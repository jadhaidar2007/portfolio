"""Aggregations shared by the dashboard API and the morning briefing."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from statistics import mean

from .models import Fixture


def daily_ws_by_route(fixtures: list[Fixture]) -> dict[str, list[tuple[dt.date, float]]]:
    """Average Worldscale rate per route per day (fixed + subs; failed excluded)."""
    buckets: dict[str, dict[dt.date, list[float]]] = defaultdict(lambda: defaultdict(list))
    for f in fixtures:
        if f.rate_type == "WS" and f.status != "failed":
            buckets[f.route][f.reported_on].append(f.rate)
    return {route: sorted((d, round(mean(v), 1)) for d, v in days.items())
            for route, days in buckets.items()}


def summary(fixtures: list[Fixture], today: dt.date) -> dict:
    todays = [f for f in fixtures if f.reported_on == today]
    routes = {}
    for route, series in daily_ws_by_route(fixtures).items():
        latest = series[-1][1]
        prev = series[-2][1] if len(series) > 1 else latest
        routes[route] = {"latest_ws": latest, "change": round(latest - prev, 1),
                         "series": [v for _, v in series]}
    charterers: dict[str, int] = defaultdict(int)
    for f in fixtures:
        if f.status == "fixed":
            charterers[f.charterer] += 1
    return {
        "as_of": today.isoformat(),
        "total": len(fixtures),
        "today": len(todays),
        "failed_today": sum(f.status == "failed" for f in todays),
        "routes": routes,
        "top_charterers": sorted(charterers.items(), key=lambda kv: -kv[1])[:5],
    }
