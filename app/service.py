"""Classification pipeline: cache -> TMDB -> heuristics. Pure orchestration."""
from __future__ import annotations

import logging

from app.cache import Cache
from app.models import Audience, Classification, Query
from app.normalize import audience_from_certification, audience_from_genre_ids, merge
from app.tmdb import TmdbClient

_LOG = logging.getLogger(__name__)


class Classifier:
    def __init__(self, cache: Cache, tmdb: TmdbClient | None = None) -> None:
        self._cache = cache
        self._tmdb = tmdb

    def classify(self, query: Query, *, use_cache: bool = True) -> Classification:
        if not query.title or not query.title.strip():
            raise ValueError("title must be a non-empty string")

        if use_cache:
            hit = self._cache.get(query.title)
            if hit is not None:
                return hit

        result = self._lookup(query)
        if result.audience is not Audience.UNKNOWN:
            self._cache.put(result)
        return result

    def _lookup(self, query: Query) -> Classification:
        if self._tmdb is None:
            return merge(query)
        try:
            show = self._tmdb.search_tv(query.title)
        except Exception as e:                      # defensive: upstream must not 500 us
            _LOG.warning("TMDB lookup failed for %r: %s", query.title, e)
            return merge(query)
        if show is None:
            return merge(query)

        cert = None
        try:
            cert = self._tmdb.certification(show.tv_id)
        except Exception as e:
            _LOG.warning("TMDB certification failed for %s: %s", show.tv_id, e)

        names = {}
        try:
            names = self._tmdb.genre_names()
        except Exception:
            pass

        return merge(
            query,
            cert_audience=audience_from_certification(cert),
            genre_audience=audience_from_genre_ids(list(show.genre_ids)),
            genres=tuple(names.get(g, str(g)) for g in show.genre_ids),
            certification=cert,
            english_title=show.original_name,
        )
