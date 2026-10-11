"""Pick the best TMDB search hit for a title. Pure logic, no I/O.

TMDB's own result order is relevance-based and puts obscure shows with a
near-identical name ahead of the obvious one: searching 'Euforia' (HBO's Polish
title for Euphoria) returns a Catalan singing contest first. We re-rank on how
well the name matches, then on popularity, then on vote count.
"""
from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

EXACT = 3
PREFIX = 2
PARTIAL = 1
NONE = 0


def fold(value: str | None) -> str:
    """Casefold, strip accents and collapse whitespace.

    So 'Eufòria', 'EUFORIA' and ' euforia ' all compare equal.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.casefold().split())


def match_tier(query: str, *names: str | None) -> int:
    """How closely `query` matches any of `names` - EXACT down to NONE."""
    wanted = fold(query)
    if not wanted:
        return NONE
    best = NONE
    for name in names:
        candidate = fold(name)
        if not candidate:
            continue
        if candidate == wanted:
            return EXACT
        if candidate.startswith(wanted) or wanted.startswith(candidate):
            best = max(best, PREFIX)
        elif wanted in candidate or candidate in wanted:
            best = max(best, PARTIAL)
    return best


def _number(value: Any) -> float:
    """TMDB occasionally omits or mistypes these; never let that raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def _rank_key(result: Mapping[str, Any], query: str) -> tuple[int, float, float]:
    return (
        match_tier(query, result.get("name"), result.get("original_name")),
        _number(result.get("popularity")),
        _number(result.get("vote_count")),
    )


def best_match(results: Iterable[Any] | None, query: str) -> Mapping[str, Any] | None:
    """The best usable result, or None when there is nothing to pick from."""
    if not results:
        return None
    usable = [r for r in results if isinstance(r, Mapping) and "id" in r]
    if not usable:
        return None
    return max(usable, key=lambda r: _rank_key(r, query))
