import io
import json
import urllib.error
import pytest

from app.tmdb import TmdbClient


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _mock_urlopen(monkeypatch, payloads):
    """payloads: list of dicts (or Exceptions) returned in call order."""
    calls = {"urls": []}
    seq = list(payloads)

    def fake(url, timeout=None):
        calls["urls"].append(url)
        nxt = seq.pop(0) if seq else {}
        if isinstance(nxt, Exception):
            raise nxt
        return _Resp(json.dumps(nxt).encode())

    monkeypatch.setattr("app.tmdb.urllib.request.urlopen", fake)
    return calls


def test_requires_api_key():
    with pytest.raises(ValueError):
        TmdbClient("")
    with pytest.raises(ValueError):
        TmdbClient("   ")


def test_search_tv_parses_top_result(monkeypatch):
    calls = _mock_urlopen(monkeypatch, [{"results": [
        {"id": 42, "name": "Jaś Fasola", "original_name": "Mr. Bean", "genre_ids": [10762, 16]}]}])
    show = TmdbClient("k").search_tv("Jaś Fasola")
    assert show.tv_id == 42 and show.original_name == "Mr. Bean"
    assert show.genre_ids == (10762, 16)
    assert "language=pl-PL" in calls["urls"][0]
    assert "api_key=k" in calls["urls"][0]


def test_search_tv_blank_title_returns_none(monkeypatch):
    _mock_urlopen(monkeypatch, [])
    assert TmdbClient("k").search_tv("  ") is None


def test_search_tv_no_results(monkeypatch):
    _mock_urlopen(monkeypatch, [{"results": []}])
    assert TmdbClient("k").search_tv("Nieznane") is None


def test_search_tv_malformed_result(monkeypatch):
    _mock_urlopen(monkeypatch, [{"results": [{"no_id": True}]}])
    assert TmdbClient("k").search_tv("X") is None


def test_http_error_returns_none(monkeypatch):
    _mock_urlopen(monkeypatch, [urllib.error.HTTPError("u", 401, "no", {}, None)])
    assert TmdbClient("k").search_tv("X") is None


def test_network_error_returns_none(monkeypatch):
    _mock_urlopen(monkeypatch, [urllib.error.URLError("down")])
    assert TmdbClient("k").search_tv("X") is None


def test_certification_prefers_configured_country(monkeypatch):
    _mock_urlopen(monkeypatch, [{"results": [
        {"iso_3166_1": "US", "rating": "TV-MA"},
        {"iso_3166_1": "PL", "rating": "7"}]}])
    assert TmdbClient("k", country="PL").certification(1) == "7"


def test_certification_falls_back_to_us(monkeypatch):
    _mock_urlopen(monkeypatch, [{"results": [{"iso_3166_1": "US", "rating": "TV-Y"}]}])
    assert TmdbClient("k", country="PL").certification(1) == "TV-Y"


def test_certification_none_when_absent(monkeypatch):
    _mock_urlopen(monkeypatch, [{"results": []}])
    assert TmdbClient("k").certification(1) is None


def test_genre_names_maps_ids(monkeypatch):
    _mock_urlopen(monkeypatch, [{"genres": [
        {"id": 10762, "name": "Dla dzieci"}, {"id": 16, "name": "Animacja"}, {"bad": 1}]}])
    assert TmdbClient("k").genre_names() == {10762: "Dla dzieci", 16: "Animacja"}


def test_genre_names_empty_on_failure(monkeypatch):
    _mock_urlopen(monkeypatch, [urllib.error.URLError("x")])
    assert TmdbClient("k").genre_names() == {}
