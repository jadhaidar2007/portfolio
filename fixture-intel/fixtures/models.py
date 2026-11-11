from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Fixture:
    """One reported tanker fixture, normalised across brokers."""

    vessel: str
    size_kt: int            # cargo size in thousand tonnes
    load: str               # load region / port
    discharge: str
    laycan: str             # e.g. "12-14 Nov"
    rate_type: str          # "WS" (Worldscale points) or "LS" (lump sum, USD)
    rate: float
    charterer: str
    status: str             # fixed | failed | subs
    broker: str
    reported_on: dt.date

    @property
    def route(self) -> str:
        return f"{self.load} → {self.discharge}"

    @property
    def key(self) -> tuple:
        """Same fixture is often reported by several brokers; dedupe on this."""
        return (self.vessel.upper(), self.laycan, self.load.upper())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["reported_on"] = self.reported_on.isoformat()
        d["route"] = self.route
        return d
