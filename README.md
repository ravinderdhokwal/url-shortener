# WalUrl

Production-oriented URL shortener built with FastAPI, SQLAlchemy (async), and PostgreSQL.

WalUrl accepts a long URL, persists a unique base62 short code, and redirects clients to the original destination. Short codes are generated with a cryptographically secure RNG; uniqueness is enforced by a database unique constraint plus a bounded retry loop in the service layer.

---

## Features

- Create a shortened URL (`POST /api/v1/url`)
- List stored URLs (`GET /api/v1/url`)
- HTTP 302 redirect from `/{short_code}` to the original URL
- Idempotent create: an existing original URL returns **409 Conflict** with the stored short-code payload
- Inactive and expired links return **410 Gone**
- Database-backed `/health` check
- Alembic migrations against PostgreSQL
- Environment-driven configuration (`pydantic-settings`)
- Structured application errors (`AppException` hierarchy)

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Runtime | Python 3.14+ |
| Package / runner | [uv](https://docs.astral.sh/uv/) |
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x (asyncio) |
| Database | PostgreSQL 16 via `asyncpg` |
| Migrations | Alembic |
| Config | pydantic-settings, `.env` |

---

## Architecture

```
HTTP  →  API (FastAPI routers)
           →  Service (business rules, collision retry)
                 →  Repository (SQLAlchemy queries)
                       →  PostgreSQL
```

| Layer | Responsibility |
| --- | --- |
| `api/` | HTTP contracts, status codes, dependency injection |
| `services/` | Short-code generation retries, uniqueness, expiry/active checks |
| `repos/` | Persistence only; does not generate codes or catch unique-constraint errors |
| `models/` | SQLAlchemy models |
| `schemas/` | Pydantic request/response models |
| `core/` | Settings and application exceptions |
| `db/` | Async engine, session, unit of work (`commit` / `rollback`) |

Short codes are **not** guaranteed unique at generation time. The `urls.short_code` unique index is the source of truth. On `IntegrityError`, the service rolls back and retries up to `MAX_SHORT_CODE_GENERATION_ATTEMPTS` (default: 3).

---

## Prerequisites

- Python **3.14+** (see `.python-version`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for local PostgreSQL) **or** a reachable Postgres instance
- Alembic CLI (installed with the project)

---

## Quick start

### 1. Clone and install

```bash
git clone <repository-url>
cd url_shortener

uv sync
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

This starts Postgres 16 as `walurl-postgres-db`:

| Setting | Value |
| --- | --- |
| User | `myuser` |
| Password | `mypassword` |
| Database | `walurl` |
| Port | `5432` |

Change these in `docker-compose.yml` and `.env` together. Do not use the compose defaults in production.

### 3. Configure environment

```bash
cp .env.example .env
```

Set `DATABASE_URL` to match the running database. For the compose stack:

```env
PORT=7007
DATABASE_URL=postgresql+asyncpg://myuser:mypassword@localhost:5432/walurl
ENVIRONMENT=DEV
```

`ENVIRONMENT` values `dev`, `development`, and `local` enable Uvicorn auto-reload and SQL echo. Any other value is treated as production (generic 500 responses, no reload).

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Start the API

```bash
uv run start-server
```

The process binds `0.0.0.0:${PORT}` (default **7007**).

| Resource | URL |
| --- | --- |
| OpenAPI | http://localhost:7007/docs |
| ReDoc | http://localhost:7007/redoc |
| Health | http://localhost:7007/health |

---

## Configuration

Settings are loaded from the environment and `.env` (`src/url_shortener/core/config.py`).

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | — | SQLAlchemy URL; must use the `postgresql+asyncpg://` driver |
| `PORT` | no | `7007` | HTTP listen port |
| `ENVIRONMENT` | no | `prod` | `DEV` / `development` / `local` vs production |
| `APPLICATION_NAME` | no | `WalUrl` | FastAPI title / logger name |
| `API_VERSION` | no | `1` | Version used in `/api/v{n}` |
| `DEFAULT_SHORT_CODE_LENGTH` | no | `7` | Base62 code length (`62^7` ≈ 3.5×10¹² codes) |
| `MAX_SHORT_CODE_GENERATION_ATTEMPTS` | no | `3` | Collision retries before 500 |

---

## API

Base path for versioned JSON APIs: `/api/v1`.

Redirects are **not** versioned; they live at the site root so short links stay short.

### Health

```http
GET /health
```

**200**

```json
{ "status": "ok", "database": "connected" }
```

**503**

```json
{ "status": "error", "database": "unreachable" }
```

### Create short URL

```http
POST /api/v1/url
Content-Type: application/json
```

```json
{ "original_url": "https://example.com/very/long/path" }
```

`original_url` must be at least 10 characters.

**201 Created**

```json
{
  "short_code": "aB3xY9k",
  "original_url": "https://example.com/very/long/path",
  "is_active": true
}
```

**409 Conflict** — the original URL already has a short code. Body includes the existing record under `data`.

```json
{
  "success": false,
  "message": "Short URL already exists for the entered url.",
  "error": "ConflictError",
  "data": {
    "short_code": "aB3xY9k",
    "original_url": "https://example.com/very/long/path",
    "is_active": true
  }
}
```

**500** — unique short code could not be allocated after all retries.

### List URLs

```http
GET /api/v1/url
```

**200** — array of URL rows (SQLAlchemy models serialized by FastAPI).

**404** — no rows in `urls`.

### Redirect

```http
GET /{short_code}
```

**302 Found** — `Location` set to `original_url`.

**404** — unknown short code.

**410 Gone** — `is_active` is false, or `expires_at` is in the past (UTC).

Example:

```bash
curl -i http://localhost:7007/aB3xY9k
```

---

## Error model

Application errors subclass `AppException` and are returned as JSON:

```json
{
  "success": false,
  "message": "<human-readable message>",
  "error": "<ExceptionClassName>",
  "data": null
}
```

| Exception | HTTP | When |
| --- | --- | --- |
| `NotFoundError` | 404 | Missing short code or empty table |
| `ConflictError` | 409 | Original URL already shortened |
| `ResourceInactiveError` | 410 | Inactive or expired link |
| `InternalServerError` | 500 | Exhausted short-code retries |
| Unhandled `Exception` | 500 | Unexpected failure (message redacted unless `ENVIRONMENT` is a dev variant) |

---

## Data model

Table: `urls`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `VARCHAR(36)` | UUID string primary key |
| `short_code` | `VARCHAR(10)` | Unique, indexed |
| `original_url` | `TEXT` | Unique |
| `is_active` | `BOOLEAN` | Default `true` |
| `expires_at` | `TIMESTAMPTZ` | Optional; `NULL` means no expiry |
| `created_at` | `TIMESTAMPTZ` | Server default `now()` |
| `updated_at` | `TIMESTAMPTZ` | Updated on change |

Migrations live under `alembic/versions/`. Typical workflow:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
uv run alembic downgrade -1
```

---

## Project layout

```
url_shortener/
├── alembic/                    # Migration env and revisions
├── alembic.ini
├── docker-compose.yml          # Local PostgreSQL only
├── pyproject.toml
├── src/url_shortener/
│   ├── main.py                 # Uvicorn entry (`start-server`)
│   ├── app.py                  # FastAPI factory, health, exception handlers
│   ├── api/                    # Routers and HTTP deps
│   ├── core/                   # Settings, exceptions
│   ├── db/                     # Engine and session
│   ├── models/
│   ├── repos/
│   ├── schemas/
│   ├── services/
│   └── utils/                  # Base62 generator, messages
└── .env.example
```

---

## Production notes

- **Secrets:** never commit `.env`. Rotate the compose credentials before any shared or public deployment.
- **`DATABASE_URL`:** use a dedicated user with least privilege; require TLS to Postgres in real environments (`ssl=require` / equivalent).
- **`ENVIRONMENT`:** must not be `dev` / `development` / `local` in production (SQL echo, reload, and exception detail leakage).
- **Process model:** `start-server` runs a single Uvicorn worker. For production, put Uvicorn behind a reverse proxy and scale with multiple workers or replicas; do not rely on the in-process reload flag.
- **Bind address:** the app listens on `0.0.0.0`. Restrict exposure with a load balancer / firewall; do not publish the DB port (`5432`) beyond the private network.
- **Health:** use `GET /health` for liveness/readiness. Treat 503 as not ready (database unreachable).
- **Redirects:** responses are **302**. That is correct for mutable mappings (inactive/expiry). Use 301 only if you intentionally want caches and browsers to pin the destination forever.
- **Listing endpoint:** `GET /api/v1/url` returns the full table with no pagination or auth. Do not expose it publicly without access control.
- **Collision space:** 7-character base62 is large; uniqueness still depends on the unique index and retries. Raising `DEFAULT_SHORT_CODE_LENGTH` requires a matching column width and a migration.
- **This repository** ships compose for **Postgres only**. Containerizing the API, adding CI, rate limiting, and authentication are deployment concerns not included in the current tree.

---

## License

No license file is included in this repository. All rights reserved unless the author states otherwise.
