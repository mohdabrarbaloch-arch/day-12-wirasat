# Wirasat — Architecture

## Overview

Wirasat is a zero-friction Faraid (Islamic inheritance) calculator. A user
selects the deceased's heirs, optionally enters an estate value, and receives
an exact, scholar-grade distribution: fractional shares with awl, radd,
asabah and hajb rules applied automatically.

## System diagram

```
┌──────────────────────────┐         ┌─────────────────────────────────────┐
│      Browser (SPA)       │  HTTP   │            FastAPI app              │
│                          │────────▶│  /api/auth/*     JWT + bcrypt      │
│  static/index.html       │◀────────│  /api/heirs      heir catalogue    │
│  static/css/style.css    │  JSON   │  /api/calculate  Faraid engine     │
│  static/js/app.js        │         │  /api/history    saved calcs       │
└──────────────────────────┘         └──────────────┬──────────────────────┘
                                                    │ SQLAlchemy 2.0
                                                    ▼
                              ┌───────────────────────────────────────────┐
                              │  SQLite (dev / Vercel /tmp)  or  Postgres 16│
                              │  users, calculations                      │
                              └───────────────────────────────────────────┘
```

## Tech stack

| Layer        | Choice                                            |
|--------------|---------------------------------------------------|
| Backend      | Python 3.11, FastAPI 0.115, Pydantic v2           |
| ORM          | SQLAlchemy 2.0 (declarative, typed `Mapped`)      |
| Database     | SQLite (dev, /tmp on Vercel) / PostgreSQL 16      |
| Auth         | JWT (HS256, 24h) + bcrypt (12 rounds)             |
| Security     | CORS allow-list, slowapi rate limits, input validation |
| Frontend     | Vanilla JS SPA (no build step), mobile-first     |
| Deploy       | Docker / docker-compose, Vercel serverless        |

## Faraid engine (`app/core/faraid.py`)

Pure, dependency-free logic operating on `fractions.Fraction` — no floating
point anywhere in the share math.

1. **Heir catalogue** — 22 heir types with labels and gender.
2. **Hajb (exclusion)** — `_apply_exclusions()`: children block siblings &
   grandparents, father blocks grandfather, mother blocks grandmothers,
   sons block grandsons, etc.
3. **Quranic fixed shares** — `_quranic_shares()`: spouse, parents,
   grandparents, daughters, sisters, maternal siblings. Includes the
   umariyyatan rule (mother takes 1/3 of the remainder when spouse+father).
4. **Asabah (residuary)** — ordered male tiers (`son → grandson → father →
   grandfather → brothers → nephews → uncles`) with 2:1 male:female split
   within a tier; father/grandfather stack their residue on top of a fixed
   share; female siblings become tier-2 asabah when daughters are present.
5. **Awl** — shares totalling >1 are reduced proportionally.
6. **Radd** — surplus returned proportionally to sharers when no asabah
   exists (majority view; noted in the result notes).

The engine exposes `calculate_distribution(deceased_gender, heirs, counts)`
returning a `CalculationResult` with exact fractions.

## Data flow

1. SPA loads `/api/heirs` → renders the picker grid.
2. User selects heirs (+ counts) and optional estate value.
3. `POST /api/calculate` (JWT required) → Pydantic validates → engine runs →
   result saved to `calculations` table → response returned with fractions
   and (when estate given) PKR amounts.
4. `GET /api/history` lists the user's saved calculations.

## Auth & security

- Passwords hashed with bcrypt (12 rounds); never stored in plaintext.
- JWT signed with `SECRET_KEY` (env); 24h expiry; `sub` = user id.
- `get_current_user` dependency guards every non-auth route.
- Rate limiting via slowapi: login 10/min, general 120/min (env-tunable).
- CORS restricted to configured origins.
- Input validation on every request (Pydantic: email format, heir keys,
  estate bounds, heir count limits).

## Scaling notes

- **Compute** is trivial (pure math) — the bottleneck is never CPU.
- **DB**: SQLite is fine to ~10k calculations; switch `DATABASE_URL` to
  Postgres for multi-user production (docker-compose included).
- **Deploy**: FastAPI is stateless; horizontal scaling is a matter of adding
  workers behind a load balancer. On Vercel, `/tmp` SQLite is ephemeral per
  instance — use a managed Postgres (Neon/Supabase) for persistence.
- **Observability**: add structured logging + Sentry for production.

## Project layout

```
app/
  main.py             FastAPI app, middleware, static mount
  models.py           User, Calculation ORM models
  core/
    config.py         pydantic-settings
    database.py       engine, session, Base
    security.py       JWT create/decode
    faraid.py         the inheritance engine (pure logic)
  routers/
    deps.py           get_current_user
    auth.py           register / login / login-json / me
    calc.py           /api/heirs, /api/calculate
    history.py        /api/history CRUD
  schemas/
    schemas.py        Pydantic request/response models
static/
  index.html          SPA shell
  css/style.css       mobile-first Islamic theme
  js/app.js           auth, picker, results, history, print
tests/
  test_faraid.py      17 engine unit tests
  test_api.py         14 API integration tests
docs/
  setup.md            local + Docker + Vercel setup
  usage.md            user guide
  api-reference.md    endpoint reference
```
