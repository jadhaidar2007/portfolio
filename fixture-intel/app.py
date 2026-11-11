"""Dashboard server. Run `python run_pipeline.py` first, then `python app.py`."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from fixtures import db
from fixtures.analytics import summary

ROOT = Path(__file__).resolve().parent
TODAY = dt.date(2026, 11, 11)  # demo data ends here
app = Flask(__name__, static_folder=str(ROOT / "static"))


def _fixtures():
    return db.load_all(db.connect(ROOT / "fixtures.db"))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/fixtures")
def fixtures():
    rows = [f.to_dict() for f in _fixtures()]
    for key in ("status", "broker", "load"):
        if value := request.args.get(key):
            rows = [r for r in rows if r[key].lower() == value.lower()]
    return jsonify(sorted(rows, key=lambda r: r["reported_on"], reverse=True))


@app.get("/api/summary")
def api_summary():
    return jsonify(summary(_fixtures(), TODAY))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
