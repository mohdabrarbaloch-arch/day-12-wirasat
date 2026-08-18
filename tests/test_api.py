"""API integration tests using FastAPI TestClient."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_wirasat.db"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _register(email="test@example.com", password="strongpass123"):
    return client.post("/api/auth/register", json={
        "email": email, "password": password, "full_name": "Test User"
    })


def _auth_headers(resp):
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_login():
    r = _register("bob@example.com")
    assert r.status_code == 201
    assert "access_token" in r.json()

    r2 = client.post("/api/auth/login/json", json={
        "email": "bob@example.com", "password": "strongpass123"
    })
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_register_duplicate_email():
    _register("dup@example.com")
    r = _register("dup@example.com")
    assert r.status_code == 409


def test_me_endpoint():
    reg = _register("me@example.com")
    r = client.get("/api/auth/me", headers=_auth_headers(reg))
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_me_requires_auth():
    assert client.get("/api/auth/me").status_code == 401


def test_heir_catalogue():
    r = client.get("/api/heirs")
    assert r.status_code == 200
    heirs = r.json()["heirs"]
    assert len(heirs) >= 20
    keys = {h["key"] for h in heirs}
    assert {"son", "daughter", "wife", "husband", "father", "mother"} <= keys


def test_calculate_requires_auth():
    r = client.post("/api/calculate", json={"heirs": ["son"]})
    assert r.status_code == 401


def test_calculate_son_daughter():
    reg = _register("calc@example.com")
    r = client.post("/api/calculate", headers=_auth_headers(reg), json={
        "deceased_gender": "male",
        "estate_value": 300000,
        "heirs": ["son", "daughter"],
        "counts": {"son": 1, "daughter": 1},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "normal"
    by_key = {e["key"]: e for e in data["entries"]}
    assert by_key["son"]["share_numerator"] == 2
    assert by_key["son"]["share_denominator"] == 3
    assert by_key["daughter"]["share_numerator"] == 1
    assert by_key["daughter"]["share_denominator"] == 3
    assert by_key["son"]["amount"] is not None


def test_calculate_invalid_heir():
    reg = _register("bad@example.com")
    r = client.post("/api/calculate", headers=_auth_headers(reg), json={
        "heirs": ["nonexistent_heir"]
    })
    assert r.status_code == 422


def test_calculate_empty_heirs():
    reg = _register("empty@example.com")
    r = client.post("/api/calculate", headers=_auth_headers(reg), json={"heirs": []})
    assert r.status_code == 422


def test_history_saves_and_lists():
    reg = _register("hist@example.com")
    headers = _auth_headers(reg)
    client.post("/api/calculate", headers=headers, json={
        "heirs": ["wife", "son"], "counts": {"wife": 1, "son": 1}
    })
    r = client.get("/api/history", headers=headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert rows[0]["input_heirs"] is not None


def test_history_requires_auth():
    assert client.get("/api/history").status_code == 401


def test_login_wrong_password():
    _register("wrong@example.com", "strongpass123")
    r = client.post("/api/auth/login/json", json={
        "email": "wrong@example.com", "password": "wrongpass"
    })
    assert r.status_code == 401
