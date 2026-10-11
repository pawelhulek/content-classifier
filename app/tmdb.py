"""Minimal TMDB client. Returns None on any failure - never raises to callers."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .ranking import best_match

_LOG = logging.getLogger(__name__)
_BASE = "https://api.themoviedb.org/3"
_TIMEOUT = 10


@dataclass(frozen=True, slots=True)
class TmdbShow:
    tv_id: int
    name: str
    original_name: str | None
    genre_ids: tuple[int, ...]


class TmdbClient:
    def __init__(self, api_key: str, language: str = "pl-PL", country: str = "PL") -> None:
        if not api_key or not api_key.strip():
            raise ValueError("TMDB api_key is required")
        self._key = api_key.strip()
        self._language = language
        self._country = country

    def _get(self, path: str, **params: str) -> dict | None:
        params = {**params, "api_key": self._key}
        url = f"{_BASE}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=_TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            _LOG.warning("TMDB %s -> HTTP %s", path, e.code)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            _LOG.warning("TMDB %s failed: %s", path, e)
        return None

    def search_tv(self, title: str) -> TmdbShow | None:
        if not title or not title.strip():
            return None
        data = self._get("/search/tv", query=title.strip(), language=self._language)
        results = (data or {}).get("results") or []
        # NOT results[0]: TMDB's relevance order puts near-name-matches ahead of
        # the obvious show (query 'Euforia' -> a Catalan contest, not Euphoria).
        top = best_match(results, title.strip())
        if top is None:
            return None
        return TmdbShow(
            tv_id=int(top["id"]),
            name=str(top.get("name") or title),
            original_name=top.get("original_name"),
            genre_ids=tuple(g for g in (top.get("genre_ids") or []) if isinstance(g, int)),
        )

    def certification(self, tv_id: int) -> str | None:
        """Age certification, preferring the configured country then US."""
        data = self._get(f"/tv/{tv_id}/content_ratings")
        results = (data or {}).get("results") or []
        by_country = {
            str(r.get("iso_3166_1")): str(r.get("rating") or "")
            for r in results
            if isinstance(r, dict)
        }
        for cc in (self._country, "US"):
            if by_country.get(cc):
                return by_country[cc]
        return None

    def genre_names(self) -> dict[int, str]:
        data = self._get("/genre/tv/list", language=self._language)
        return {
            int(g["id"]): str(g["name"])
            for g in (data or {}).get("genres") or []
            if isinstance(g, dict) and "id" in g and "name" in g
        }
