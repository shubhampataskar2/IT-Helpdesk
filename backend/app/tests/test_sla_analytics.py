from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models import Ticket
from app.services.sla_service import check_overdue
from app.tests.conftest import auth_header, make_user, register


def _ticket(client, token, title, desc):
    return client.post("/api/v1/tickets", headers=auth_header(token),
                       json={"title": title, "description": desc}).json()


def test_sla_deadlines_are_set(client):
    token = register(client, "sara@acme.io", "Sara S")["access_token"]
    t = _ticket(client, token, "Critical outage", "All users locked out, production system completely down, urgent")
    assert t["sla_response_due_at"] is not None
    assert t["sla_resolve_due_at"] is not None


def test_check_overdue_flags_tickets():
    db = SessionLocal()
    try:
        # craft an overdue ticket directly
        creator_id = int(db.scalar(text("SELECT id FROM users WHERE email='admin@helpdesk.io'")))
        before = datetime.now(timezone.utc) - timedelta(hours=5)
        ticket = Ticket(
            number="HT-OVERDUE-TEST",
            title="Overdue duck",
            description="This ticket is intentionally past its SLA deadlines for testing purposes.",
            status="new",
            priority="critical",
            category="network",
            creator_id=creator_id,
            created_at=before,
            first_response_at=None,
            sla_response_due_at=before + timedelta(minutes=30),
            sla_resolve_due_at=before + timedelta(minutes=240),
        )
        db.add(ticket)
        db.commit()
        overdue = check_overdue(db)
        ids = [t.id for t in overdue["response"]] + [t.id for t in overdue["resolve"]]
        assert ticket.id in ids
    finally:
        db.close()


def test_analytics_reflects_activity(client):
    support_tok = make_user(client, "toby@acme.io", "support")["access_token"]
    emp_tok = register(client, "uma@acme.io", "Uma U")["access_token"]
    _ticket(client, emp_tok, "Broken keyboard", "The keyboard keys are not registering presses")
    resolved = _ticket(client, emp_tok, "Slow wifi", "Wifi keeps cutting out in the east wing")
    support_id = client.get("/api/v1/auth/me", headers=auth_header(support_tok)).json()["id"]
    client.post(f"/api/v1/tickets/{resolved['id']}/assign",
                headers=auth_header(support_tok), json={"assignee_id": support_id})
    client.patch(f"/api/v1/tickets/{resolved['id']}", headers=auth_header(support_tok),
                 json={"status": "resolved"})

    overview = client.get("/api/v1/analytics/overview", headers=auth_header(support_tok)).json()
    assert overview["total"] >= 2
    assert overview["by_status"]["resolved"] >= 1
    assert overview["avg_resolve_minutes"] is not None

    sla = client.get("/api/v1/analytics/sla", headers=auth_header(support_tok)).json()
    assert set(sla.keys()) == {"low", "medium", "high", "critical"}

    engineers = client.get("/api/v1/analytics/engineers", headers=auth_header(support_tok)).json()
    assert any(e["resolved"] >= 1 for e in engineers)
