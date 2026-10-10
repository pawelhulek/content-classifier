"""Immutable domain types for content classification."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class Audience(str, Enum):
    KIDS = "kids"
    FAMILY = "family"
    ADULT = "adult"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Query:
    """A classification request. Frozen: never mutated, only replaced."""
    title: str
    episode: str | None = None
    duration_s: int | None = None
    app: str | None = None

    def with_title(self, title: str) -> "Query":
        return replace(self, title=title)


@dataclass(frozen=True, slots=True)
class Classification:
    """Result of classifying one title."""
    title: str
    audience: Audience
    source: str
    confidence: float
    genres: tuple[str, ...] = ()
    certification: str | None = None
    english_title: str | None = None

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "audience": self.audience.value,
            "source": self.source,
            "confidence": round(self.confidence, 2),
            "genres": list(self.genres),
            "certification": self.certification,
            "english_title": self.english_title,
        }
