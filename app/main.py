"""HTTP API. GET /classify?title=...&duration=...  ->  JSON classification."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query as Q

from app.cache import Cache
from app.config import Settings
from app.models import Query
from app.service import Classifier
from app.tmdb import TmdbClient

logging.basicConfig(level=logging.INFO)
_LOG = logging.getLogger("classifier")

settings = Settings.from_env()
_cache = Cache(settings.cache_path, ttl_s=settings.cache_ttl_s)
_tmdb = (
    TmdbClient(settings.tmdb_api_key, settings.language, settings.country)
    if settings.tmdb_api_key
    else None
)
if _tmdb is None:
    _LOG.warning("TMDB_API_KEY not set - running on heuristics only")
_classifier = Classifier(_cache, _tmdb)

app = FastAPI(title="Content Classifier", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "tmdb_configured": _tmdb is not None,
        "cached_titles": _cache.size(),
    }


@app.get("/classify")
def classify(
    title: str = Q(..., min_length=1, max_length=300),
    episode: str | None = Q(None, max_length=300),
    duration: int | None = Q(None, ge=0, le=86400),
    app_name: str | None = Q(None, max_length=120),
    no_cache: bool = Q(False),
) -> dict:
    if not title.strip():
        raise HTTPException(status_code=422, detail="title must not be blank")
    try:
        result = _classifier.classify(
            Query(title=title.strip(), episode=episode, duration_s=duration, app=app_name),
            use_cache=not no_cache,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        _LOG.exception("classification failed for %r", title)
        raise HTTPException(status_code=502, detail="classification failed") from e
    return result.as_dict()
