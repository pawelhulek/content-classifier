"""Configuration from environment. Secrets never hardcoded."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    tmdb_api_key: str | None
    language: str
    country: str
    cache_path: str
    cache_ttl_s: int

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> "Settings":
        e = env if env is not None else dict(os.environ)
        raw_ttl = e.get("CACHE_TTL_S", str(7 * 24 * 3600))
        try:
            ttl = int(raw_ttl)
            if ttl < 0:
                raise ValueError
        except ValueError:
            raise ValueError(f"CACHE_TTL_S must be a non-negative integer, got {raw_ttl!r}")
        key = (e.get("TMDB_API_KEY") or "").strip() or None
        return Settings(
            tmdb_api_key=key,
            language=e.get("TMDB_LANGUAGE", "pl-PL"),
            country=e.get("TMDB_COUNTRY", "PL"),
            cache_path=e.get("CACHE_PATH", "/data/cache.db"),
            cache_ttl_s=ttl,
        )
