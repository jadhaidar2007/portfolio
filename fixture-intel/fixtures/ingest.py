"""Turn a folder of broker emails (.eml) into deduplicated fixtures."""
from __future__ import annotations

import datetime as dt
import email
from dataclasses import dataclass, field
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

from .models import Fixture
from .parsers import parser_for


@dataclass
class IngestReport:
    fixtures: list[Fixture] = field(default_factory=list)
    emails: int = 0
    skipped_senders: set[str] = field(default_factory=set)
    unparsed: list[tuple[str, str]] = field(default_factory=list)  # (file, line)
    duplicates: int = 0
    by_broker: dict[str, int] = field(default_factory=dict)  # parsed, before dedupe


def read_email(raw: bytes) -> tuple[str, dt.date, str]:
    msg = email.message_from_bytes(raw, policy=policy.default)
    body = msg.get_body(preferencelist=("plain",))
    sent = parsedate_to_datetime(msg["Date"]).date()
    return msg["From"], sent, body.get_content() if body else ""


def ingest_messages(messages: list[tuple[str, str, dt.date, str]]) -> IngestReport:
    """messages: (source_id, sender, date, body). Shared by .eml and Graph ingestion."""
    report = IngestReport()
    seen: dict[tuple, Fixture] = {}
    for source_id, sender, sent, body in messages:
        report.emails += 1
        parse = parser_for(sender)
        if parse is None:
            report.skipped_senders.add(sender)
            continue
        result = parse(body, sent)
        report.unparsed += [(source_id, line) for line in result.unparsed]
        for fx in result.fixtures:
            report.by_broker[fx.broker] = report.by_broker.get(fx.broker, 0) + 1
            if fx.key in seen:
                report.duplicates += 1
                # A later report wins: subs often turn into fixed/failed the next day.
                if fx.reported_on >= seen[fx.key].reported_on:
                    seen[fx.key] = fx
            else:
                seen[fx.key] = fx
    report.fixtures = sorted(seen.values(), key=lambda f: (f.reported_on, f.vessel))
    return report


def ingest_folder(folder: Path) -> IngestReport:
    messages = []
    for path in sorted(Path(folder).glob("*.eml")):
        sender, sent, body = read_email(path.read_bytes())
        messages.append((path.name, sender, sent, body))
    return ingest_messages(messages)
