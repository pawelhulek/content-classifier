"""Tests for the pure classification logic (written before implementation)."""
import pytest

from app.models import Audience, Query
from app.normalize import (
    audience_from_certification,
    audience_from_duration,
    audience_from_genre_ids,
    merge,
)


class TestGenreIds:
    def test_kids_genre_wins(self):
        assert audience_from_genre_ids([10762]) is Audience.KIDS

    def test_animation_alone_is_family_not_kids(self):
        # Animation is not automatically kids (e.g. adult animation)
        assert audience_from_genre_ids([16]) is Audience.FAMILY

    def test_news_and_talk_are_adult(self):
        assert audience_from_genre_ids([10763]) is Audience.ADULT
        assert audience_from_genre_ids([10767]) is Audience.ADULT

    def test_empty_is_unknown(self):
        assert audience_from_genre_ids([]) is Audience.UNKNOWN

    def test_invalid_input_is_unknown(self):
        assert audience_from_genre_ids(None) is Audience.UNKNOWN
        assert audience_from_genre_ids(["nonsense"]) is Audience.UNKNOWN


class TestCertification:
    @pytest.mark.parametrize("cert", ["TV-Y", "TV-Y7", "G", "0", "6", "7"])
    def test_young_certs_are_kids(self, cert):
        assert audience_from_certification(cert) is Audience.KIDS

    @pytest.mark.parametrize("cert", ["TV-G", "TV-PG", "PG", "12"])
    def test_mid_certs_are_family(self, cert):
        assert audience_from_certification(cert) is Audience.FAMILY

    @pytest.mark.parametrize("cert", ["TV-MA", "R", "NC-17", "18"])
    def test_high_certs_are_adult(self, cert):
        assert audience_from_certification(cert) is Audience.ADULT

    def test_blank_is_unknown(self):
        assert audience_from_certification("") is Audience.UNKNOWN
        assert audience_from_certification(None) is Audience.UNKNOWN


class TestDuration:
    def test_short_is_kids(self):
        assert audience_from_duration(660) is Audience.KIDS      # 11 min

    def test_long_is_unknown_not_adult(self):
        # duration alone must never assert "adult"
        assert audience_from_duration(2332) is Audience.UNKNOWN   # 39 min

    def test_zero_and_none_are_unknown(self):
        assert audience_from_duration(0) is Audience.UNKNOWN
        assert audience_from_duration(None) is Audience.UNKNOWN


class TestMerge:
    def test_certification_beats_duration(self):
        got = merge(Query("X", duration_s=660), cert_audience=Audience.ADULT)
        assert got.audience is Audience.ADULT
        assert got.source == "certification"

    def test_falls_back_to_duration(self):
        got = merge(Query("X", duration_s=660))
        assert got.audience is Audience.KIDS
        assert got.source == "duration"

    def test_unknown_when_nothing_known(self):
        got = merge(Query("X"))
        assert got.audience is Audience.UNKNOWN
        assert got.confidence < 0.5
