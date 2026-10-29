#!/usr/bin/env python3
"""Cron job: fetch upcoming journeys to Vienna and store them in SQLite.

Usage:
    .venv/bin/python scripts/update_journeys.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from transport.db import init_db, upsert_journeys
from transport.scotty import BASE_URL, HEADERS
from transport.utils import fetch_vienna_journeys, make_retrying_session


def main() -> None:
    init_db()

    now = datetime.now()
    search_date = now.strftime("%Y%m%d")
    search_time = now.strftime("%H%M%S")

    journeys = fetch_vienna_journeys(
        make_retrying_session(), BASE_URL, HEADERS, search_date, search_time
    )
    if not journeys:
        print("No journeys fetched", file=sys.stderr)
        sys.exit(1)

    upsert_journeys(
        journeys,
        search_date,
        search_time,
        datetime.now(timezone.utc).isoformat(),
    )
    print(f"Stored {len(journeys)} journeys")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
