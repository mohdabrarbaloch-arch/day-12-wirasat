# 🕌 Wirasat — وراثت · Faraid Inheritance Calculator

> Divide the estate the way Allah ﷻ prescribed — exactly.

Wirasat is a production-ready **Islamic inheritance (Faraid) calculator**. You
pick the heirs, optionally enter an estate value, and get back an **exact
fractional distribution** — with the full classical rule-set applied: fixed
Quranic shares, **hajb** exclusions, **awl**, **radd** and **asabah**
(residuary) distribution, including the 2:1 male:female split and the
umariyyatan case.

No floating-point rounding in the share math — the engine works in exact
fractions (`fractions.Fraction`), so every paisa of the estate is accounted
for.

![Wirasat login](https://static.teamily.ai/sites/a2ed58ed-8717-4660-9349-35beace0433c/documents/wirasat_login/wirasat_login.png)
![Wirasat results](https://static.teamily.ai/sites/a2ed58ed-8717-4660-9349-35beace0433c/documents/wirasat_results/wirasat_results.png)

## ✨ Features

- **22 heir types** — spouse, children, parents, grandparents, siblings,
  nephews, uncles, grandchildren — with a friendly tap-to-select picker
- **Exact Quranic shares** — never rounded until you ask for money amounts
- **All classical rules** — hajb exclusion, awl (proportional reduction),
  radd (surplus return), asabah ordering, 2:1 male:female split, umariyyatan
- **Estate value support** — enter an amount (Rs) and see each heir's exact
  share in rupees
- **Share certificate view** — print/save a clean distribution sheet
- **Accounts & history** — JWT auth, saved calculations per user
- **Mobile-first SPA** — no build step, works great on a phone
- **Security-first** — bcrypt password hashing, JWT sessions, rate limiting,
  CORS allow-list, input validation on every endpoint
- **Deploy-ready** — Docker + docker-compose (Postgres 16), Vercel serverless

## 🧠 How the math works

```
Fixed shares (Quranic)  →  Hajb exclusions  →  Asabah (residue)  →  Awl / Radd
        ↓                        ↓                    ↓                   ↓
   spouse, parents,      closer heirs          ordered male        if shares > 1
   daughters, sisters    block distant         tiers, 2:1          reduce; if no
   (exact fractions)     ones                  male:female         asabah, return
                                                                   surplus
```

All computation happens in `app/core/faraid.py` using Python's exact
`Fraction` type — verified against classical rulings in 17 unit tests.

## 🚀 Live demo

> ⚠️ **Not yet deployed.** This build was verified locally (tests, lint,
> live HTTP smoke test). To deploy:

### Option A — Docker (recommended for full functionality)

```bash
docker compose up --build
# → http://localhost:8000
```

### Option B — Vercel (serverless)

The repo ships `vercel.json` + `api/index.py` (uses a writable `/tmp`
SQLite — fine for a demo; use a managed Postgres for persistence).

```bash
npm i -g vercel
vercel --prod --yes
```

## 📦 Installation (local dev)

```bash
# 1. Clone
git clone https://github.com/mohdabrarbaloch-arch/day-12-wirasat.git
cd day-12-wirasat

# 2. Environment
cp .env.example .env        # then edit SECRET_KEY

# 3. Python 3.11+ venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Run
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
```

## 🧪 Tests & lint

```bash
pip install -r requirements.txt pytest ruff
pytest -q          # 31 tests
ruff check app tests
```

## 🔌 API at a glance

| Method | Endpoint              | Auth | Description                    |
|--------|-----------------------|------|--------------------------------|
| POST   | `/api/auth/register`  | —    | Create account, get JWT        |
| POST   | `/api/auth/login`     | —    | OAuth2 form login              |
| POST   | `/api/auth/login/json`| —    | JSON login (SPA)               |
| GET    | `/api/auth/me`        | JWT  | Current user                   |
| GET    | `/api/heirs`          | JWT  | Heir catalogue                 |
| POST   | `/api/calculate`      | JWT  | Compute distribution           |
| GET    | `/api/history`        | JWT  | Saved calculations             |
| DELETE | `/api/history/{id}`   | JWT  | Delete a calculation           |

Full reference: [docs/api-reference.md](docs/api-reference.md)

## 📚 Docs

- [Setup guide](docs/setup.md)
- [Usage guide](docs/usage.md)
- [API reference](docs/api-reference.md)
- [Architecture](ARCHITECTURE.md)

## ⚖️ Disclaimer

This tool implements the classical Sunni (Hanafi-method) Faraid rules and is
verified against standard inheritance problems, but **inheritance is a
sensitive matter** — for a real estate distribution, always confirm the
calculation with a qualified scholar or the local court.

## 📄 License

[MIT](LICENSE) © 2026 ABraz Baloch

---

Built on Day 12 of the **Autonomous AI Software Engineer — 30 Day Challenge**.
