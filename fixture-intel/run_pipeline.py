"""Daily job: ingest emails -> SQLite -> morning briefing HTML.

In production this ran from Windows Task Scheduler each morning, pulling mail
via Microsoft Graph (see fixtures/graph.py). The demo reads samples/emails/.

    python run_pipeline.py                 # demo, offline
    python run_pipeline.py --graph --since-hours 24
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from fixtures import db
from fixtures.briefing import render
from fixtures.ingest import ingest_folder, ingest_messages

ROOT = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", action="store_true", help="read the live mailbox via Microsoft Graph")
    ap.add_argument("--since-hours", type=int, default=24)
    ap.add_argument("--db", type=Path, default=ROOT / "fixtures.db")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.date(2026, 11, 11))
    args = ap.parse_args()

    if args.graph:
        from fixtures.graph import fetch_messages
        since = dt.datetime.utcnow() - dt.timedelta(hours=args.since_hours)
        report = ingest_messages(fetch_messages(since))
    else:
        report = ingest_folder(ROOT / "samples" / "emails")

    conn = db.connect(args.db)
    db.upsert(conn, report.fixtures)
    fixtures = db.load_all(conn)

    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    (out / "briefing.html").write_text(render(fixtures, args.today), encoding="utf-8")

    print(f"emails read:        {report.emails}")
    print(f"fixtures parsed:    {len(report.fixtures)} (after removing {report.duplicates} duplicates)")
    print(f"parsed per broker:  {report.by_broker}")
    print(f"unknown senders:    {', '.join(sorted(report.skipped_senders)) or 'none'}")
    print(f"unparsed lines:     {len(report.unparsed)}")
    print(f"database rows:      {len(fixtures)}")
    print(f"briefing written:   out/briefing.html")


if __name__ == "__main__":
    main()
