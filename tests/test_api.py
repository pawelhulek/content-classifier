import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "api.db"))
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    import importlib
    import app.main as m
    importlib.reload(m)
    return TestClient(m.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["tmdb_configured"] is False


def test_classify_short_is_kids(client):
    r = client.get("/classify", params={"title": "Miś znika", "duration": 660})
    assert r.status_code == 200
    assert r.json()["audience"] == "kids"


def test_classify_unknown_without_signals(client):
    r = client.get("/classify", params={"title": "Klara"})
    assert r.json()["audience"] == "unknown"


def test_missing_title_is_422(client):
    assert client.get("/classify").status_code == 422


def test_blank_title_is_422(client):
    assert client.get("/classify", params={"title": "   "}).status_code == 422


def test_negative_duration_rejected(client):
    assert client.get("/classify", params={"title": "X", "duration": -5}).status_code == 422
