"""Pure classification logic. No I/O, no globals, fully testable."""
from __future__ import annotations

from app.models import Audience, Classification, Query

# TMDB TV genre ids -> audience signal
KIDS_GENRE_IDS = frozenset({10762})                      # Kids
FAMILY_GENRE_IDS = frozenset({16, 10751})                # Animation, Family
ADULT_GENRE_IDS = frozenset({10763, 10767, 10768, 99})   # News, Talk, War&Politics, Documentary

KIDS_CERTS = frozenset({"TV-Y", "TV-Y7", "G", "0", "6", "7", "AL"})
FAMILY_CERTS = frozenset({"TV-G", "TV-PG", "PG", "PG-13", "12", "9"})
ADULT_CERTS = frozenset({"TV-14", "TV-MA", "R", "NC-17", "16", "18"})

# Kids content is reliably short; long content tells us nothing on its own.
KIDS_MAX_DURATION_S = 15 * 60

_CONFIDENCE = {
    "certification": 0.95,
    "genre": 0.80,
    "duration": 0.55,
    "none": 0.30,
}


def audience_from_genre_ids(genre_ids: object) -> Audience:
    """Map TMDB genre ids to an audience. Unknown on any invalid input."""
    if not isinstance(genre_ids, (list, tuple, set, frozenset)):
        return Audience.UNKNOWN
    ids = {g for g in genre_ids if isinstance(g, int)}
    if not ids:
        return Audience.UNKNOWN
    if ids & KIDS_GENRE_IDS:
        return Audience.KIDS
    if ids & ADULT_GENRE_IDS:
        return Audience.ADULT
    if ids & FAMILY_GENRE_IDS:
        return Audience.FAMILY
    return Audience.UNKNOWN


def audience_from_certification(cert: object) -> Audience:
    """Map an age certification string to an audience."""
    if not isinstance(cert, str) or not cert.strip():
        return Audience.UNKNOWN
    key = cert.strip().upper()
    if key in KIDS_CERTS:
        return Audience.KIDS
    if key in FAMILY_CERTS:
        return Audience.FAMILY
    if key in ADULT_CERTS:
        return Audience.ADULT
    return Audience.UNKNOWN


def audience_from_duration(duration_s: object) -> Audience:
    """Short runtimes suggest kids content. Never concludes 'adult'."""
    if not isinstance(duration_s, int) or duration_s <= 0:
        return Audience.UNKNOWN
    return Audience.KIDS if duration_s <= KIDS_MAX_DURATION_S else Audience.UNKNOWN


def merge(
    query: Query,
    *,
    cert_audience: Audience = Audience.UNKNOWN,
    genre_audience: Audience = Audience.UNKNOWN,
    genres: tuple[str, ...] = (),
    certification: str | None = None,
    english_title: str | None = None,
) -> Classification:
    """Combine signals by trust order: certification > genre > duration."""
    for audience, source in (
        (cert_audience, "certification"),
        (genre_audience, "genre"),
        (audience_from_duration(query.duration_s), "duration"),
    ):
        if audience is not Audience.UNKNOWN:
            return Classification(
                title=query.title,
                audience=audience,
                source=source,
                confidence=_CONFIDENCE[source],
                genres=genres,
                certification=certification,
                english_title=english_title,
            )
    return Classification(
        title=query.title,
        audience=Audience.UNKNOWN,
        source="none",
        confidence=_CONFIDENCE["none"],
        genres=genres,
        certification=certification,
        english_title=english_title,
    )
