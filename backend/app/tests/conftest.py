import os

os.environ["DATABASE_URL"] = "postgresql+psycopg2://helpdesk@localhost:5432/helpdesk_test"
os.environ["ENABLE_RATE_LIMIT"] = "false"
os.environ.setdefault("AI_PROVIDER", "heuristic")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("USE_CELERY", "false")
os.environ.setdefault("DUPLICATE_THRESHOLD", "0.6")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal, init_db
from app.main import app
from app.services.bootstrap import _seed_admin, _seed_kb

init_db()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    yield
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE refresh_tokens, ticket_comments, tickets, kb_articles, audit_logs, users CASCADE"))
        db.commit()
        _seed_admin(db)
        _seed_kb(db)
    finally:
        db.close()


def register(client, email: str, name: str = "Test User", password: str = "password123") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def login(client, email: str, password: str = "password123") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_support(db, email: str = "engineer@acme.io") -> int:
    db.execute(text("UPDATE users SET role='support' WHERE email=:e"), {"e": email})
    db.commit()
    user = db.scalar(text("SELECT id FROM users WHERE email=:e"), {"e": email})
    return int(user)


def make_user(client, email: str, role: str = "employee") -> dict:
    data = register(client, email)
    if role != "employee":
        db = SessionLocal()
        try:
            db.execute(text("UPDATE users SET role=:r WHERE email=:e"), {"r": role, "e": email})
            db.commit()
        finally:
            db.close()
    return data
