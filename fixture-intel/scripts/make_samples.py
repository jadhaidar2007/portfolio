"""Generate two weeks of synthetic broker emails in three different formats.

All vessels, brokers, charterers and rates are invented. Rates follow a
random walk per route so the dashboard and sparklines have something to show.
Run: python scripts/make_samples.py
"""
from __future__ import annotations

import datetime as dt
import random
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "samples" / "emails"
END = dt.date(2026, 11, 11)
DAYS = 14

ROUTES = {  # (load, discharge, size_kt, start WS)
    "VLCC": ("MEG", "CHINA", 270, 58.0),
    "SUEZMAX": ("WAF", "UKC", 130, 95.0),
    "AFRAMAX": ("USG", "UKC", 70, 150.0),
}
VESSELS = ["Ocean Pearl", "Nordic Star", "Blue Heron", "Silver Fjord", "Cape Aurora", "Sea Lantern",
           "Polar Wind", "Amber Tide", "Iron Gull", "Coral Dawn", "Atlas Spirit", "Harbor Light",
           "Kestrel", "Desert Rose", "Morning Calm", "Grey Petrel", "Red Kite", "Saga Venture"]
CHARTERERS = ["UNIPEC", "SHELL", "VITOL", "TRAFIGURA", "TOTAL", "BP", "RELIANCE", "EQUINOR"]


def walk(rng: random.Random) -> dict[str, list[float]]:
    rates = {}
    for cls, (_, _, _, start) in ROUTES.items():
        v, series = start, []
        for _ in range(DAYS):
            v = max(30, v + rng.gauss(0.6, start * 0.03))
            series.append(round(v, 1))
        rates[cls] = series
    return rates


def deals_for_day(rng, day, ws):
    deals = []
    pool = rng.sample(VESSELS, len(VESSELS))  # a vessel is fixed at most once per day
    for cls, (load, dis, size, _) in ROUTES.items():
        for _ in range(rng.randint(1, 3)):
            lay_start = (day + dt.timedelta(days=rng.randint(7, 20)))
            lay_end = lay_start + dt.timedelta(days=2)
            laycan = f"{lay_start.day}-{lay_end.day} {lay_end:%b}"
            status = rng.choices(["FXD", "SUBS", "FLD"], [0.75, 0.17, 0.08])[0]
            deals.append(dict(vessel=pool.pop(), size=size, load=load, dis=dis,
                              laycan=laycan, ws=round(ws[cls] + rng.uniform(-2.5, 2.5), 1),
                              chrtr=rng.choice(CHARTERERS), status=status))
    return deals


def northsea(deals):
    lines = ["Good morning, please find our latest fixtures below:", ""]
    lines += [f"{d['vessel'].upper()} / {d['size']} / {d['load']} / {d['dis']} / "
              f"{d['laycan'].upper()} / WS {d['ws']} / {d['chrtr']} / {d['status']}" for d in deals]
    lines += ["", "Rgds, Northsea Desk"]
    return "\n".join(lines)


def gulfline(deals):
    rows = ["| Vessel | Qty | Load | Disch | Laycan | Rate | Chrtr | Status |",
            "|---|---|---|---|---|---|---|---|"]
    rows += [f"| {d['vessel']} | {d['size']}kt | {d['load']} | {d['dis']} | {d['laycan']} | "
             f"WS {d['ws']} | {d['chrtr']} | {d['status']} |" for d in deals]
    return "Dirty tanker fixtures today:\n\n" + "\n".join(rows) + "\n\nGulfline Tankers"


def harbour(deals):
    word = {"FXD": "fixed", "SUBS": "on subs", "FLD": "failed"}
    s = [f"{d['chrtr'].title()} {word[d['status']]} {d['vessel']}, {d['size']}kt "
         f"{d['load']}/{d['dis']} {d['laycan']} at WS {d['ws']}." for d in deals]
    return "Market is steady. " + " ".join(s) + " More tomorrow."


BROKERS = [("desk@northsea-brokers.example", northsea),
           ("fixtures@gulfline.example", gulfline),
           ("research@harbourco.example", harbour)]


def main():
    rng = random.Random(7)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.eml"):
        old.unlink()
    rates = walk(rng)
    for i in range(DAYS):
        day = END - dt.timedelta(days=DAYS - 1 - i)
        ws = {cls: series[i] for cls, series in rates.items()}
        deals = deals_for_day(rng, day, ws)
        for sender, fmt in BROKERS:
            picked = [d for d in deals if rng.random() < 0.7]  # brokers overlap -> duplicates
            if not picked:
                continue
            msg = EmailMessage()
            msg["From"], msg["To"] = sender, "chartering@demo-trader.example"
            msg["Subject"] = f"Tanker fixtures {day:%d %b}"
            msg["Date"] = format_datetime(dt.datetime.combine(day, dt.time(7, 30)))
            msg.set_content(fmt(picked))
            (OUT / f"{day:%Y%m%d}_{sender.split('@')[1].split('.')[0]}.eml").write_bytes(bytes(msg))
    # one email from an unknown sender, to show it is skipped, not mis-parsed
    msg = EmailMessage()
    msg["From"], msg["Subject"] = "newsletter@unknown-broker.example", "Weekly market wrap"
    msg["Date"] = format_datetime(dt.datetime.combine(END, dt.time(8, 0)))
    msg.set_content("Freight markets were mixed this week.")
    (OUT / f"{END:%Y%m%d}_unknown.eml").write_bytes(bytes(msg))
    print(f"wrote {len(list(OUT.glob('*.eml')))} emails to {OUT}")


if __name__ == "__main__":
    main()
