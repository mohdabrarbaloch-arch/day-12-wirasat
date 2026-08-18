# Setup Guide

## Prerequisites

- Python 3.11+
- (Optional) Docker + Docker Compose for the Postgres path
- (Optional) Node.js for the Vercel CLI

## 1. Local development (SQLite)

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-12-wirasat.git
cd day-12-wirasat

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit SECRET_KEY — use:  python -c "import secrets; print(secrets.token_hex(32))"

uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 — the SPA is served from the same origin.

## 2. Docker (PostgreSQL 16)

```bash
docker compose up --build
```

- API: http://localhost:8000
- Postgres: `postgresql+psycopg://wirasat:wirasat@db:5432/wirasat`
- Tables are created automatically on startup (`Base.metadata.create_all`).

## 3. Vercel (serverless)

The repo is Vercel-ready:

- `vercel.json` routes `/api/*` to the FastAPI app and static assets to the
  SPA.
- `api/index.py` sets `DATABASE_URL=sqlite:////tmp/wirasat.db` — writable but
  ephemeral per instance. For real persistence, set the `DATABASE_URL`
  environment variable in Vercel to a managed Postgres (Neon / Supabase).

```bash
npm i -g vercel
vercel --prod --yes
```

## 4. Environment variables

| Variable              | Default                  | Description                          |
|-----------------------|--------------------------|--------------------------------------|
| `SECRET_KEY`          | `dev-secret-change-me`   | JWT signing key — set a long random value! |
| `DATABASE_URL`        | `sqlite:///./wirasat.db` | SQLAlchemy database URL              |
| `CORS_ORIGINS`        | `*`                      | Comma-separated allowed origins      |
| `RATE_LIMIT_LOGIN`    | `10/minute`              | Login/register rate limit            |
| `RATE_LIMIT_GENERAL`  | `120/minute`             | General API rate limit               |
| `ENABLE_ADMIN_WIPE`   | `false`                  | Danger switch (keep false)           |

## 5. Tests & lint

```bash
pip install pytest ruff
pytest -q
ruff check app tests
```
