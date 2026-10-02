from app.core.database import SessionLocal
from app.services.ticket_service import run_ticket_analysis
from app.tests.conftest import auth_header, make_user, register


def _ticket(client, token, title="Printer not working", desc="The shared printer on floor 4 is offline and my jobs fail."):
    return client.post("/api/v1/tickets", headers=auth_header(token),
                       json={"title": title, "description": desc})


def test_create_ticket_and_ai_quick_analysis(client):
    token = register(client, "frank@acme.io", "Frank F")["access_token"]
    resp = _ticket(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"].startswith("HT-")
    assert data["creator_name"] == "Frank F"
    assert data["priority"] in ("low", "medium", "high", "critical")
    assert data["category"] in ("hardware", "software", "network", "access", "other")
    assert data["sla_resolve_due_at"] is not None


def test_ticket_refinement_pipeline(client):
    token = register(client, "grace@acme.io", "Grace G")["access_token"]
    ticket = _ticket(client, token, title="Laptop replacement needed",
                     desc="My laptop is three years old and the battery barely lasts an hour now.").json()

    db = SessionLocal()
    try:
        run_ticket_analysis(db, ticket["id"])
    finally:
        db.close()

    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth_header(token)).json()
    assert detail["ai_refined"] is True
    assert detail["ai_confidence"] is not None
    assert "Knowledge base" in (detail["ai_suggested_fix"] or "")


def test_employees_only_see_own_tickets(client):
    a_token = register(client, "hank@acme.io", "Hank H")["access_token"]
    b_token = register(client, "iris@acme.io", "Iris I")["access_token"]
    _ticket(client, a_token)
    b_ticket = _ticket(client, b_token, title="Second printer issue").json()

    resp = client.get("/api/v1/tickets", headers=auth_header(a_token))
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()["items"]]
    assert b_ticket["id"] not in ids


def test_support_can_see_all_tickets(client):
    a_token = register(client, "kevin@acme.io", "Kevin K")["access_token"]
    b_token = register(client, "leo@acme.io", "Leo L")["access_token"]
    t_a = _ticket(client, a_token).json()
    t_b = _ticket(client, b_token, title="Network switch issue").json()
    support_token = make_user(client, "support3@acme.io", "support")["access_token"]
    resp = client.get("/api/v1/tickets", headers=auth_header(support_token))
    ids = [t["id"] for t in resp.json()["items"]]
    assert t_a["id"] in ids and t_b["id"] in ids


def test_ticket_workflow_and_comments(client):
    token = register(client, "judy@acme.io", "Judy J")["access_token"]
    ticket = _ticket(client, token).json()

    # employee tries to resolve -> forbidden
    resp = client.patch(f"/api/v1/tickets/{ticket['id']}", headers=auth_header(token),
                        json={"status": "resolved"})
    assert resp.status_code == 403

    # support engineer resolves
    support_token = make_user(client, "support1@acme.io", "support")["access_token"]
    resp = client.patch(f"/api/v1/tickets/{ticket['id']}", headers=auth_header(support_token),
                        json={"status": "in_progress"})
    assert resp.status_code == 200
    resp = client.patch(f"/api/v1/tickets/{ticket['id']}", headers=auth_header(support_token),
                        json={"status": "resolved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["resolved_at"] is not None

    # comment
    resp = client.post(f"/api/v1/tickets/{ticket['id']}/comments",
                       headers=auth_header(support_token), json={"body": "Replaced the drum, done."})
    assert resp.status_code == 201

    # employee reopens
    resp = client.post(f"/api/v1/tickets/{ticket['id']}/reopen", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


def test_duplicate_ticket_detection(client):
    token = register(client, "kim@acme.io", "Kim K")["access_token"]
    _ticket(client, token, title="VPN disconnects all the time",
            desc="My VPN connection keeps dropping every few minutes and I cannot connect to the internal network.")
    t2 = _ticket(client, token, title="VPN keeps dropping connection",
                 desc="My VPN connection keeps dropping every few minutes again, I cannot connect to the internal network.").json()

    db = SessionLocal()
    try:
        run_ticket_analysis(db, t2["id"])
    finally:
        db.close()

    detail = client.get(f"/api/v1/tickets/{t2['id']}", headers=auth_header(token)).json()
    assert detail["duplicate_of"] is not None
