import time
import pytest
from app.cache import Cache
from app.models import Audience, Classification


def cls(title="Klara", audience=Audience.FAMILY):
    return Classification(title=title, audience=audience, source="genre", confidence=0.8)


@pytest.fixture
def cache(tmp_path):
    return Cache(tmp_path / "c.db", ttl_s=3600)


def test_miss_then_hit(cache):
    assert cache.get("Klara") is None
    cache.put(cls())
    got = cache.get("Klara")
    assert got is not None and got.audience is Audience.FAMILY


def test_lookup_is_case_and_space_insensitive(cache):
    cache.put(cls())
    assert cache.get("  klara ") is not None


def test_expired_entry_is_a_miss(tmp_path):
    c = Cache(tmp_path / "c.db", ttl_s=0)
    c.put(cls())
    time.sleep(0.01)
    assert c.get("Klara") is None


def test_put_is_idempotent_and_overwrites(cache):
    cache.put(cls(audience=Audience.FAMILY))
    cache.put(cls(audience=Audience.ADULT))
    assert cache.get("Klara").audience is Audience.ADULT
    assert cache.size() == 1


def test_blank_keys_rejected(cache):
    with pytest.raises(ValueError):
        cache.get("")
    with pytest.raises(ValueError):
        cache.put(cls(title="   "))


def test_survives_reopen(tmp_path):
    p = tmp_path / "c.db"
    Cache(p, ttl_s=3600).put(cls())
    assert Cache(p, ttl_s=3600).get("Klara") is not None
