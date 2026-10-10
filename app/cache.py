"""SQLite-backed classification cache. Avoids repeat upstream lookups."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from app.models import Audience, Classification

_SCHEMA = """
CREATE TABLE IF NOT EXISTS classifications (
    key        TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    stored_at  REAL NOT NULL
)
"""


def _key(title: str) -> str:
    """Normalised cache key. Raises on blank input (boundary validation)."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    return title.strip().casefold()


class Cache:
    def __init__(self, path: str | Path, ttl_s: int = 7 * 24 * 3600) -> None:
        if ttl_s < 0:
            raise ValueError("ttl_s must be >= 0")
        self._path = str(path)
        self._ttl = ttl_s
        with self._conn() as c:
            c.execute(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, title: str) -> Classification | None:
        k = _key(title)
        try:
            with self._conn() as c:
                row = c.execute(
                    "SELECT payload, stored_at FROM classifications WHERE key = ?", (k,)
                ).fetchone()
        except sqlite3.Error:
            return None                      # cache must never break a request
        if row is None:
            return None
        if time.time() - row["stored_at"] > self._ttl:
            return None
        try:
            d = json.loads(row["payload"])
            return Classification(
                title=d["title"],
                audience=Audience(d["audience"]),
                source=d["source"],
                confidence=float(d["confidence"]),
                genres=tuple(d.get("genres") or ()),
                certification=d.get("certification"),
                english_title=d.get("english_title"),
            )
        except (ValueError, KeyError, TypeError):
            return None

    def put(self, result: Classification) -> None:
        k = _key(result.title)
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO classifications (key, payload, stored_at) VALUES (?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, "
                    "stored_at=excluded.stored_at",
                    (k, json.dumps(result.as_dict()), time.time()),
                )
        except sqlite3.Error:
            return

    def size(self) -> int:
        try:
            with self._conn() as c:
                return int(c.execute("SELECT COUNT(*) FROM classifications").fetchone()[0])
        except sqlite3.Error:
            return 0
