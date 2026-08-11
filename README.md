# URL Shortener with Analytics Dashboard

A URL shortening service with base62 encoding, Redis caching, rate limiting, and
click analytics (geo-location, device/browser breakdown, referrers).

Built with FastAPI, Redis, and PostgreSQL.

## Architecture

```
                         ┌──────────────┐
                         │   Client     │
                         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              POST /shorten  GET /:code  GET /analytics/:code
                    │           │           │
                    ▼           ▼           ▼
              ┌─────────────────────────────────┐
              │         FastAPI Server          │
              │           :8000                 │
              │                                 │
              │  ┌───────────┐ ┌─────────────┐  │
              │  │   Rate    │ │   Auth      │  │
              │  │  Limiter  │ │ (API Key)   │  │
              │  └─────┬─────┘ └──────┬──────┘  │
              └────────┼──────────────┼─────────┘
                       │              │
            ┌──────────┴──────────────┴──────────┐
            │                                     │
            ▼                                     ▼
     ┌─────────────┐                      ┌─────────────┐
     │    Redis     │                      │ PostgreSQL  │
     │    :6379     │                      │   :5432     │
     │              │                      │             │
     │ • URL cache  │                      │ • urls      │
     │   (code→url) │                      │ • clicks    │
     │ • Rate limit │                      │ • api_keys  │
     │   counters   │                      │             │
     └─────────────┘                      └─────────────┘
                                                │
                                          ┌─────┴─────┐
                                          │  GeoIP    │
                                          │  Lookup   │
                                          │ (MaxMind  │
                                          │  GeoLite2)│
                                          └───────────┘
```

**Redirect flow (`GET /:code`):** check Redis for the code → URL mapping; on a
cache hit, redirect immediately without touching Postgres. On a miss, query
Postgres, populate the cache, then redirect. The click is logged asynchronously
so it never adds latency to the redirect response.

**Shorten flow (`POST /shorten`):** rate limit check → validate URL → (custom
alias uniqueness check, or auto-generate a base62 code from the row's id) →
insert into Postgres → cache the mapping → return the short URL.

## Base62 encoding

Short codes are the row's auto-increment id encoded in base62 (`a-z`, `A-Z`,
`0-9`), not a hash — so there are no collisions to handle, codes are as short
as the id allows, and a code can be decoded straight back to the id for an
O(1) lookup. The `urls_id_seq` sequence starts at `238328` (`62³+62²+62`) so
codes are always at least 4 characters. See [`app/core/base62.py`](app/core/base62.py).

## Quick start

```bash
docker compose up -d
```

This starts the API on `:8000`, Redis on `:6379`, and Postgres on `:5432`.
Tables are created automatically on startup ([`app/db/migrations.py`](app/db/migrations.py)).

Create an API key for testing:

```bash
python scripts/create_api_key.py "My App"
```

This prints a key like `sk_live_...` — use it as the `X-API-Key` header below.

### Shorten a URL

```bash
curl -X POST localhost:8000/shorten \
  -H "X-API-Key: sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'
```

```json
{
  "short_url": "https://xoragain.com/baaa",
  "code": "baaa",
  "original_url": "https://google.com",
  "created_at": "2026-08-12T10:00:00",
  "expires_at": null
}
```

### Custom alias

```bash
curl -X POST localhost:8000/shorten \
  -H "X-API-Key: sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com", "custom_alias": "my-github"}'
```

### Expiring link

```bash
curl -X POST localhost:8000/shorten \
  -H "X-API-Key: sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "expires_in_hours": 1}'
```

### Follow the redirect

Visit `http://localhost:8000/baaa` in a browser, or:

```bash
curl -i localhost:8000/baaa
```

### View analytics

```bash
curl localhost:8000/analytics/baaa -H "X-API-Key: sk_live_..."
curl localhost:8000/analytics/baaa/summary -H "X-API-Key: sk_live_..."
```

### List your URLs

```bash
curl "localhost:8000/urls?limit=20&offset=0" -H "X-API-Key: sk_live_..."
```

### Deactivate a URL

```bash
curl -X DELETE localhost:8000/urls/baaa -H "X-API-Key: sk_live_..."
```

### Site stats / health

```bash
curl localhost:8000/stats
curl localhost:8000/health
```

## GeoIP setup (optional)

Click geo-location needs MaxMind's free GeoLite2-City database. Without it,
`country`/`city` are simply logged as `null` — everything else still works.

1. Create a free account at [MaxMind](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
2. Download `GeoLite2-City.mmdb`
3. Place it at `data/GeoLite2-City.mmdb` (mounted into the container by `docker-compose.yml`)

## API reference

| Method   | Path                     | Auth    | Body/Params                                  | Description                    |
|----------|--------------------------|---------|-----------------------------------------------|---------------------------------|
| `POST`   | `/shorten`               | API Key | `{url, custom_alias?, expires_in_hours?}`     | Create a short URL              |
| `GET`    | `/:code`                 | None    | —                                              | 301 redirect to the original URL |
| `GET`    | `/analytics/:code`       | API Key | `?days=30`                                    | Full click analytics            |
| `GET`    | `/analytics/:code/summary` | API Key | —                                           | Quick summary                   |
| `GET`    | `/urls`                  | API Key | `?limit=20&offset=0`                          | List your URLs                  |
| `DELETE` | `/urls/:code`            | API Key | —                                              | Deactivate a short URL          |
| `GET`    | `/stats`                 | None    | —                                              | Public site stats               |
| `GET`    | `/health`                | None    | —                                              | Health check (Redis + Postgres) |

Authenticate with `X-API-Key: <key>`.

## Running tests

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip on macOS/Linux
.venv/Scripts/python -m pytest tests/ -v
```

The test suite mocks Redis/Postgres at the repository/cache boundary, so it
runs without Docker. It covers:

- `test_base62.py` — encode/decode roundtrip, uniqueness, negative-input rejection
- `test_rate_limiter.py` — token bucket allow/reject at the boundary, per-minute bucket keying
- `test_shorten.py` — URL validation, base62 code generation, custom alias success/conflict/format rejection, expiry
- `test_redirect.py` — cache hit/miss, 404 on unknown code, 410 on expired/deactivated
- `test_analytics.py` — click aggregation across all dimensions, click logging never raising on failure

For a full integration pass against real infra:

```bash
docker compose up -d
python scripts/create_api_key.py "Test"
# then run the curl commands above against the printed key
```

## Project layout

```
url-shortener/
├── app/
│   ├── main.py                # FastAPI app, lifespan, router wiring
│   ├── config.py               # Settings from env vars
│   ├── routers/                # shorten, redirect, analytics, urls
│   ├── services/                # url_service, analytics_service, rate_limiter
│   ├── core/                    # base62, geo (MaxMind), user_agent parsing
│   ├── cache/                   # Redis URL cache
│   ├── db/                      # asyncpg pool, migrations, repository (SQL)
│   ├── models/                  # Pydantic schemas
│   └── middleware/               # API key auth dependency
├── tests/
├── scripts/create_api_key.py    # Seed an API key for local testing
├── data/                        # Mount point for GeoLite2-City.mmdb
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Deploying to xoragain.com

Not required to run locally — only if you want the service live on the
domain. Point DNS at your server, then reverse-proxy with Nginx + Let's
Encrypt:

```nginx
server {
    listen 443 ssl;
    server_name xoragain.com;

    ssl_certificate /etc/letsencrypt/live/xoragain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xoragain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
