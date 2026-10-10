import pytest
from app.cache import Cache
from app.models import Audience, Query
from app.service import Classifier
from app.tmdb import TmdbShow


class FakeTmdb:
    def __init__(self, show=None, cert=None, boom=False):
        self._show, self._cert, self._boom = show, cert, boom
        self.search_calls = 0

    def search_tv(self, title):
        self.search_calls += 1
        if self._boom:
            raise RuntimeError("upstream down")
        return self._show

    def certification(self, tv_id):
        return self._cert

    def genre_names(self):
        return {10762: "Kids", 10763: "News"}


@pytest.fixture
def cache(tmp_path):
    return Cache(tmp_path / "c.db", ttl_s=3600)


def test_blank_title_rejected(cache):
    with pytest.raises(ValueError):
        Classifier(cache).classify(Query("  "))


def test_no_tmdb_falls_back_to_duration(cache):
    got = Classifier(cache).classify(Query("Miś znika", duration_s=660))
    assert got.audience is Audience.KIDS and got.source == "duration"


def test_tmdb_genre_used(cache):
    show = TmdbShow(1, "Jaś Fasola", "Mr. Bean", (10762,))
    got = Classifier(cache, FakeTmdb(show)).classify(Query("Jaś Fasola"))
    assert got.audience is Audience.KIDS
    assert "Kids" in got.genres
    assert got.english_title == "Mr. Bean"


def test_certification_overrides_genre(cache):
    show = TmdbShow(2, "X", "X", (10762,))
    got = Classifier(cache, FakeTmdb(show, cert="TV-MA")).classify(Query("X"))
    assert got.audience is Audience.ADULT and got.source == "certification"


def test_upstream_failure_degrades_gracefully(cache):
    got = Classifier(cache, FakeTmdb(boom=True)).classify(Query("X", duration_s=660))
    assert got.audience is Audience.KIDS          # fell back, did not raise


def test_cache_prevents_second_upstream_call(cache):
    show = TmdbShow(3, "Klara", "Klara", (10762,))
    fake = FakeTmdb(show)
    c = Classifier(cache, fake)
    c.classify(Query("Klara"))
    c.classify(Query("Klara"))
    assert fake.search_calls == 1


def test_unknown_results_are_not_cached(cache):
    c = Classifier(cache, FakeTmdb(None))
    c.classify(Query("Nieznane"))
    assert cache.size() == 0
