"""Broker-specific parsers.

Every broker formats their fixture report differently, and formats drift. A
single "smart" regex breaks silently; one small parser per broker, chosen by
sender domain, fails loudly and is easy to fix when one broker changes layout.
Lines a parser can't read are returned as `unparsed` so they can be reviewed
instead of disappearing.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Callable

from .models import Fixture

STATUS_WORDS = {"FXD": "fixed", "FIXED": "fixed", "FLD": "failed", "FAILED": "failed",
                "SUBS": "subs", "ON SUBS": "subs"}


def _rate(text: str) -> tuple[str, float]:
    text = text.strip().upper().replace(",", "")
    if m := re.match(r"WS\s*([\d.]+)", text):
        return "WS", float(m.group(1))
    if m := re.match(r"(?:USD|\$)\s*([\d.]+)\s*(M)?", text):
        value = float(m.group(1)) * (1_000_000 if m.group(2) else 1)
        return "LS", value
    raise ValueError(f"unknown rate format: {text!r}")


@dataclass
class ParseResult:
    fixtures: list[Fixture] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- Northsea
# One fixture per line, slash separated:
#   OCEAN PEARL / 270 / MEG / CHINA / 12-14 NOV / WS 58 / UNIPEC / FXD
NORTHSEA_RE = re.compile(
    r"^(?P<vessel>[A-Z][A-Z .'-]+?)\s*/\s*(?P<size>\d+)\s*/\s*(?P<load>[A-Z .]+?)\s*/\s*"
    r"(?P<dis>[A-Z .]+?)\s*/\s*(?P<laycan>[\d-]+\s*[A-Z]{3})\s*/\s*(?P<rate>[^/]+?)\s*/\s*"
    r"(?P<chrtr>[A-Z0-9 .&-]+?)\s*/\s*(?P<status>FXD|FLD|SUBS)\s*$"
)


def parse_northsea(body: str, reported_on: dt.date) -> ParseResult:
    out = ParseResult()
    for line in body.splitlines():
        line = line.strip()
        if "/" not in line:
            continue
        m = NORTHSEA_RE.match(line.upper())
        if not m:
            out.unparsed.append(line)
            continue
        rate_type, rate = _rate(m["rate"])
        out.fixtures.append(Fixture(
            m["vessel"].title(), int(m["size"]), m["load"].strip(), m["dis"].strip(),
            m["laycan"].title(), rate_type, rate, m["chrtr"].strip(),
            STATUS_WORDS[m["status"]], "Northsea", reported_on))
    return out


# ---------------------------------------------------------------- Gulfline
# Pipe table with a header row; column order can change, so map by header name.
#   | Vessel | Qty | Load | Disch | Laycan | Rate | Chrtr | Status |
def parse_gulfline(body: str, reported_on: dt.date) -> ParseResult:
    out = ParseResult()
    header: list[str] | None = None
    for line in body.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        row = dict(zip(header, cells))
        try:
            rate_type, rate = _rate(row["rate"])
            out.fixtures.append(Fixture(
                row["vessel"].title(), int(row["qty"].lower().rstrip("kt")),
                row["load"].upper(), row["disch"].upper(), row["laycan"].title(),
                rate_type, rate, row["chrtr"].upper(),
                STATUS_WORDS[row["status"].upper()], "Gulfline", reported_on))
        except (KeyError, ValueError):
            out.unparsed.append(line.strip())
    return out


# ---------------------------------------------------------------- Harbour & Co
# Prose, one sentence per fixture:
#   "Shell fixed Nordic Star, 130kt WAF/UKC 20-22 Nov at WS 95."
#   "Vitol on subs Blue Heron 80kt USG/UKC 18-19 Nov at USD 1.85m."
HARBOUR_RE = re.compile(
    r"(?P<chrtr>[A-Z][\w&.-]*(?: [A-Z][\w&.-]*)*?) (?P<status>fixed|on subs|failed) "
    r"(?P<vessel>[A-Z][\w' -]+?),? (?P<size>\d+)kt (?P<load>[A-Z]+)/(?P<dis>[A-Z]+) "
    r"(?P<laycan>\d+-\d+ [A-Z][a-z]{2}) at (?P<rate>[^.]+(?:\.\d+[^.]*)?)\.",
)


def parse_harbour(body: str, reported_on: dt.date) -> ParseResult:
    out = ParseResult()
    for sentence in re.split(r"(?<=\.)\s+(?=[A-Z])", body):
        sentence = sentence.strip()
        if not re.search(r"\bfixed\b|\bon subs\b|\bfailed\b", sentence):
            continue
        m = HARBOUR_RE.search(sentence)
        if not m:
            out.unparsed.append(sentence)
            continue
        rate_type, rate = _rate(m["rate"])
        out.fixtures.append(Fixture(
            m["vessel"].strip(), int(m["size"]), m["load"], m["dis"], m["laycan"],
            rate_type, rate, m["chrtr"].upper(),
            STATUS_WORDS[m["status"].upper()], "Harbour & Co", reported_on))
    return out


# Sender domain -> parser. Adding a broker = one function + one line here.
PARSERS: dict[str, Callable[[str, dt.date], ParseResult]] = {
    "northsea-brokers.example": parse_northsea,
    "gulfline.example": parse_gulfline,
    "harbourco.example": parse_harbour,
}


def parser_for(sender: str) -> Callable[[str, dt.date], ParseResult] | None:
    domain = sender.rsplit("@", 1)[-1].strip(" >").lower()
    return PARSERS.get(domain)
