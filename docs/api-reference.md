# API Reference

Base URL: `http://localhost:8000` (or your deployed origin).
All JSON endpoints return `application/json`. Errors use FastAPI's standard
`{"detail": "..."}` shape.

---

## Auth

### POST `/api/auth/register`

Create an account and receive a JWT immediately.

```json
{
  "email": "user@example.com",
  "password": "strongpass123",
  "full_name": "Ali"
}
```

**201** → `{ "access_token": "...", "token_type": "bearer", "user": {...} }`
**409** → email already registered
**422** → validation error (weak password, bad email)

### POST `/api/auth/login` (OAuth2 form)

`application/x-www-form-urlencoded` with `username` (email) + `password`.

**200** → same token shape.

### POST `/api/auth/login/json`

```json
{ "email": "user@example.com", "password": "strongpass123" }
```

**200** → token shape. **401** → wrong credentials.

### GET `/api/auth/me`

`Authorization: Bearer <token>` → **200** `{ "id", "email", "full_name", "created_at" }`

---

## Heirs

### GET `/api/heirs`

Requires JWT. Returns the 22 supported heir types:

```json
{
  "heirs": [
    { "key": "husband", "label": "Husband", "is_male": false },
    { "key": "wife", "label": "Wife", "is_male": true }
  ]
}
```

Heir keys: `husband, wife, son, daughter, father, mother,
paternal_grandfather, paternal_grandmother, maternal_grandmother,
full_brother, full_sister, paternal_brother, paternal_sister,
maternal_brother, maternal_sister, nephew, paternal_nephew, paternal_uncle,
paternal_uncles_son, son_son, son_daughter, son_sons_son`

---

## Calculation

### POST `/api/calculate`

Requires JWT.

```json
{
  "deceased_gender": "male",
  "estate_value": 1200000,
  "heirs": ["wife", "son", "daughter"],
  "counts": { "wife": 1, "son": 1, "daughter": 1 }
}
```

- `deceased_gender`: `"male" | "female"` (default `male`)
- `estate_value`: `>= 0` (0 = fraction-only)
- `heirs`: 1–30 heir keys (unknown keys → 422)
- `counts`: optional; overrides duplicate counting

**200** →

```json
{
  "mode": "normal",
  "shares_total_n": 1,
  "shares_total_d": 1,
  "adjusted_total_n": 1,
  "adjusted_total_d": 1,
  "excluded": [],
  "notes": [],
  "entries": [
    {
      "key": "son",
      "label": "Son",
      "count": 1,
      "share_numerator": 7,
      "share_denominator": 12,
      "share_decimal": 0.5833333333333334,
      "kind": "asabah",
      "is_male": false,
      "amount": 700000.0,
      "amount_display": "Rs 700,000.00"
    }
  ]
}
```

Each successful calculation is saved to the user's history.

---

## History

### GET `/api/history?limit=20`

Requires JWT. Most recent first. Each record = the calculation response plus
`id`, `user_id`, `deceased_gender`, `estate_value`, `input_heirs` (JSON
string), `created_at`.

### GET `/api/history/{id}`

Requires JWT. Single record, or **404** if not found / not owned.

### DELETE `/api/history/{id}`

Requires JWT. **204** on success, **404** otherwise.

---

## Meta

### GET `/api/health`

No auth. `{ "status": "ok", "app": "...", "version": "1.0.0" }`
