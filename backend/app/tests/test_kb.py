from app.core.database import SessionLocal
from app.tests.conftest import auth_header, make_user, register


def _new_admin(client, email="kbadmins@acme.io"):
    tok = make_user(client, email, "admin")["access_token"]
    return tok


def test_kb_create_search_delete(client):
    admin_tok = _new_admin(client)
    resp = client.post("/api/v1/kb", headers=auth_header(admin_tok),
                       json={"title": "Reset Office 365 password",
                             "body": "Go to the identity portal, click 'Trouble signing in?', verify yourself and set a new password.",
                             "category": "access"})
    assert resp.status_code == 201
    article_id = resp.json()["id"]

    # embed synchronously so the RAG vector search can find it
    from app.ai.factory import get_ai_provider
    from app.services import kb_service as kb

    db = SessionLocal()
    try:
        kb.embed_article(db, article_id, get_ai_provider())
    finally:
        db.close()

    hits = client.get("/api/v1/kb/search", params={"q": "password reset"},
                      headers=auth_header(admin_tok)).json()
    assert any(h["title"] == "Reset Office 365 password" for h in hits)

    resp = client.delete(f"/api/v1/kb/{article_id}", headers=auth_header(admin_tok))
    assert resp.status_code == 204


def test_only_admin_can_create_kb(client):
    emp_tok = register(client, "quincy@acme.io", "Quincy Q")["access_token"]
    resp = client.post("/api/v1/kb", headers=auth_header(emp_tok),
                       json={"title": "x", "body": "some body text here", "category": "other"})
    assert resp.status_code == 403


def test_kb_search_empty(client):
    emp_tok = register(client, "rose@acme.io", "Rose R")["access_token"]
    resp = client.get("/api/v1/kb/search", params={"q": "zzzzzzzqqqq"}, headers=auth_header(emp_tok))
    assert resp.status_code == 200
    assert resp.json() == []
