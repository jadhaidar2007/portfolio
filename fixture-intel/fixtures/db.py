from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

from .models import Fixture

SCHEMA = """
CREATE TABLE IF NOT EXISTS fixtures (
    vessel TEXT, size_kt INTEGER, load TEXT, discharge TEXT, laycan TEXT,
    rate_type TEXT, rate REAL, charterer TEXT, status TEXT, broker TEXT,
    reported_on TEXT,
    PRIMARY KEY (vessel, laycan, load)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert(conn: sqlite3.Connection, fixtures: list[Fixture]) -> int:
    rows = [(f.vessel.upper(), f.size_kt, f.load.upper(), f.discharge, f.laycan, f.rate_type,
             f.rate, f.charterer, f.status, f.broker, f.reported_on.isoformat()) for f in fixtures]
    conn.executemany(
        """INSERT INTO fixtures VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(vessel, laycan, load) DO UPDATE SET
             rate_type=excluded.rate_type, rate=excluded.rate, status=excluded.status,
             broker=excluded.broker, reported_on=excluded.reported_on
           WHERE excluded.reported_on >= fixtures.reported_on""",
        rows,
    )
    conn.commit()
    return len(rows)


def load_all(conn: sqlite3.Connection) -> list[Fixture]:
    out = []
    for r in conn.execute("SELECT * FROM fixtures ORDER BY reported_on, vessel"):
        out.append(Fixture(r["vessel"].title(), r["size_kt"], r["load"], r["discharge"],
                           r["laycan"], r["rate_type"], r["rate"], r["charterer"], r["status"],
                           r["broker"], dt.date.fromisoformat(r["reported_on"])))
    return out
