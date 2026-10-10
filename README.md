# content-classifier

A tiny HTTP service that answers one question: **is this TV show for kids, family, or adults?**

Built for [Home Assistant](https://www.home-assistant.io/) media players (Apple TV, Chromecast,
Android TV) that report a show title but no age rating. Give it a title — in any language — and it
returns a normalised audience classification backed by real TMDB age certifications.

```bash
curl "http://localhost:8077/classify?title=Jaś%20Fasola:%20Serial%20animowany"
```

```json
{
  "title": "Jaś Fasola: Serial animowany",
  "audience": "kids",
  "source": "certification",
  "confidence": 0.95,
  "genres": ["Kids", "Animacja", "Komedia", "Familijny"],
  "certification": "7",
  "english_title": "Mr. Bean: The Animated Series"
}
```

## Why

Media players expose `media_title` and sometimes `media_artist`, but **no content rating**. There's
no way to tell a children's cartoon from a late-night talk show, which makes per-audience screen-time
reporting impossible. Online databases keyed on English titles don't help when your TV reports
localised ones.

This service resolves localised titles through TMDB (`language=xx-XX`), reads the real age
certification for your country, and normalises it to `kids` / `family` / `adult` / `unknown`.

## How it classifies

Signals are applied in order of trust. The first confident signal wins:

| Order | Signal | Confidence | Notes |
|-------|--------|-----------|-------|
| 1 | TMDB age certification | 0.95 | `TV-Y`, `7`, `16`, `TV-MA`… for your country, falling back to US |
| 2 | TMDB genre | 0.80 | Kids / News / Talk / Documentary are decisive |
| 3 | Runtime heuristic | 0.55 | `<= 15 min` suggests kids content |
| — | nothing conclusive | 0.30 | returns `unknown` |

Two deliberate choices:

- **Runtime never concludes `adult`.** A long runtime tells you nothing, so it yields `unknown`
  rather than guessing.
- **Animation alone is `family`, not `kids`.** Adult animation exists.

`unknown` results are **not cached**, so adding an API key later doesn't leave stale answers behind.

## Run it

```yaml
# docker-compose.yml
services:
  content-classifier:
    image: ghcr.io/pawelhulek/content-classifier:latest
    restart: unless-stopped
    ports: ["8077:8077"]
    volumes: ["./data:/data"]
    environment:
      TMDB_API_KEY: "your_key"   # free, non-commercial: themoviedb.org
      TMDB_LANGUAGE: "pl-PL"
      TMDB_COUNTRY: "PL"
```

It **runs without an API key**, falling back to the runtime heuristic. Add a key to get real
certifications.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `TMDB_API_KEY` | *(unset)* | TMDB v3 key. Without it, heuristics only. |
| `TMDB_LANGUAGE` | `pl-PL` | Language for title search and genre names. |
| `TMDB_COUNTRY` | `PL` | Which country's certification to prefer (falls back to `US`). |
| `CACHE_PATH` | `/data/cache.db` | SQLite cache location. |
| `CACHE_TTL_S` | `604800` | Cache lifetime (7 days). |

## API

### `GET /classify`

| Param | Required | Notes |
|-------|----------|-------|
| `title` | yes | 1–300 chars, non-blank |
| `episode` | no | Episode name, for context |
| `duration` | no | Seconds, 0–86400 — enables the runtime heuristic |
| `app_name` | no | Source app, e.g. `Netflix` |
| `no_cache` | no | `true` to bypass the cache |

Returns `422` on invalid input, `502` if classification fails outright.

### `GET /health`

```json
{"status": "ok", "tmdb_configured": true, "cached_titles": 42}
```

## Home Assistant

```yaml
rest_command:
  classify_content:
    url: >-
      http://content-classifier:8077/classify?title={{ title | urlencode }}&duration={{ duration | default(0) }}
    method: GET
```

## Design notes

- **Degrades, never fails.** TMDB errors, timeouts and malformed payloads return `None` internally;
  the request still gets an answer from whatever signals remain.
- **Cache failures are non-fatal.** A broken SQLite file can't break a lookup.
- **Immutable domain types.** Frozen dataclasses throughout; nothing is mutated in place.
- **No secrets in code.** Configuration is environment-only.

## Development

```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt pytest pytest-cov httpx
./.venv/bin/python -m pytest tests/ --cov=app
```

57 tests, ~91% coverage. The classification logic in `app/normalize.py` is pure and has no I/O.

## Attribution

This product uses the TMDB API but is not endorsed or certified by
[TMDB](https://www.themoviedb.org/). TMDB's API is free for non-commercial use and requires
attribution of TMDB as the data source.

## Licence

MIT — see [LICENSE](LICENSE).
