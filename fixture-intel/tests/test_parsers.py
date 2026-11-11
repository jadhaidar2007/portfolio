import datetime as dt
from pathlib import Path

from fixtures.briefing import render, sparkline
from fixtures.ingest import ingest_folder, ingest_messages
from fixtures.parsers import parse_gulfline, parse_harbour, parse_northsea, parser_for

DAY = dt.date(2026, 11, 11)
SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "emails"


def test_northsea_line():
    r = parse_northsea("OCEAN PEARL / 270 / MEG / CHINA / 20-22 NOV / WS 58.5 / UNIPEC / FXD", DAY)
    f = r.fixtures[0]
    assert (f.vessel, f.size_kt, f.load, f.discharge, f.laycan) == ("Ocean Pearl", 270, "MEG", "CHINA", "20-22 Nov")
    assert (f.rate_type, f.rate, f.status) == ("WS", 58.5, "fixed")


def test_northsea_bad_line_is_reported_not_dropped():
    r = parse_northsea("SOMETHING / ODD / HERE", DAY)
    assert r.fixtures == [] and r.unparsed == ["SOMETHING / ODD / HERE"]


def test_gulfline_maps_columns_by_header():
    body = ("| Chrtr | Vessel | Qty | Load | Disch | Laycan | Rate | Status |\n|---|---|---|---|---|---|---|---|\n"
            "| VITOL | Blue Heron | 70kt | USG | UKC | 18-20 Nov | USD 1.85M | SUBS |")
    f = parse_gulfline(body, DAY).fixtures[0]
    assert (f.vessel, f.charterer, f.rate_type, f.rate, f.status) == ("Blue Heron", "VITOL", "LS", 1_850_000, "subs")


def test_harbour_prose():
    body = ("Market is steady. Shell fixed Nordic Star, 130kt WAF/UKC 20-22 Nov at WS 95. "
            "Vitol on subs Blue Heron, 70kt USG/UKC 18-20 Nov at USD 1.85m. More tomorrow.")
    r = parse_harbour(body, DAY)
    assert [f.vessel for f in r.fixtures] == ["Nordic Star", "Blue Heron"]
    assert r.fixtures[1].rate == 1_850_000 and r.fixtures[1].status == "subs"


def test_parser_routing_by_domain():
    assert parser_for("Desk <desk@northsea-brokers.example>") is parse_northsea
    assert parser_for("someone@unknown.example") is None


def test_later_report_wins_on_duplicates():
    early = "BLUE HERON / 70 / USG / UKC / 18-20 NOV / WS 150 / VITOL / SUBS"
    late = "BLUE HERON / 70 / USG / UKC / 18-20 NOV / WS 151 / VITOL / FXD"
    s = "desk@northsea-brokers.example"
    report = ingest_messages([("a", s, DAY - dt.timedelta(days=1), early), ("b", s, DAY, late)])
    assert len(report.fixtures) == 1 and report.duplicates == 1
    assert report.fixtures[0].status == "fixed"


def test_sample_emails_parse_cleanly():
    report = ingest_folder(SAMPLES)
    assert report.emails > 30
    assert report.unparsed == []
    assert report.duplicates > 0
    assert report.skipped_senders == {"newsletter@unknown-broker.example"}
    assert set(report.by_broker) == {"Northsea", "Gulfline", "Harbour & Co"}


def test_briefing_renders_inline_svg():
    report = ingest_folder(SAMPLES)
    html = render(report.fixtures, DAY)
    assert "<svg" in html and "<script" not in html
    assert sparkline([1.0]) == ""
