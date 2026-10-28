import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.getenv(
    "OEBB_SCOTTY_PROXY_DB",
    str(PROJECT_ROOT / "var" / "db" / "journeys.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS journeys (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL,
    search_date TEXT NOT NULL,
    search_time TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the database file and schema if they do not exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(SCHEMA)


def upsert_journeys(data: list, search_date: str, search_time: str, fetched_at: str) -> None:
    """Store the latest journeys snapshot, replacing any previous one."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO journeys (id, data, search_date, search_time, fetched_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                search_date = excluded.search_date,
                search_time = excluded.search_time,
                fetched_at = excluded.fetched_at
            """,
            (json.dumps(data), search_date, search_time, fetched_at),
        )


def get_journeys() -> dict[str, Any] | None:
    """Return the stored journeys snapshot, or None if not yet synced."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT data, search_date, search_time, fetched_at FROM journeys WHERE id = 1"
        ).fetchone()

    if row is None:
        return None

    return {
        "data": json.loads(row["data"]),
        "search_date": row["search_date"],
        "search_time": row["search_time"],
        "fetched_at": row["fetched_at"],
    }
