from app.tests.conftest import auth_header, make_user, register


def _ticket(client, token, title, desc):
    return client.post("/api/v1/tickets", headers=auth_header(token),
                       json={"title": title, "description": desc}).json()


def test_employee_blocked_from_analytics(client):
    token = register(client, "mia@acme.io", "Mia M")["access_token"]
    resp = client.get("/api/v1/analytics/overview", headers=auth_header(token))
    assert resp.status_code == 403
    resp = client.get("/api/v1/users", headers=auth_header(token))
    assert resp.status_code == 403
    resp = client.get("/api/v1/admin/audit-logs", headers=auth_header(token))
    assert resp.status_code == 403


def test_support_can_access_analytics_not_admin(client):
    support_token = make_user(client, "nova@acme.io", "support")["access_token"]
    assert client.get("/api/v1/analytics/overview", headers=auth_header(support_token)).status_code == 200
    assert client.get("/api/v1/analytics/sla", headers=auth_header(support_token)).status_code == 200
    assert client.get("/api/v1/analytics/engineers", headers=auth_header(support_token)).status_code == 200
    # support cannot promote users or read audit logs
    assert client.get("/api/v1/admin/audit-logs", headers=auth_header(support_token)).status_code == 403


def test_admin_can_manage_roles_and_audit(client):
    admin_tokens = make_user(client, "admin@acme.io", "admin")["access_token"]
    make_user(client, "oscar@acme.io", "employee")

    me = client.get("/api/v1/auth/me", headers=auth_header(admin_tokens)).json()
    users = client.get("/api/v1/users", headers=auth_header(admin_tokens)).json()
    target = next(u for u in users if u["email"] == "oscar@acme.io")

    resp = client.patch(f"/api/v1/users/{target['id']}/role", headers=auth_header(admin_tokens),
                        json={"role": "support"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "support"

    # deactivate the employee
    resp = client.patch(f"/api/v1/users/{target['id']}/active", headers=auth_header(admin_tokens),
                        json={"is_active": False})
    assert resp.status_code == 200

    # admin can see audit entries from their actions
    logs = client.get("/api/v1/admin/audit-logs", headers=auth_header(admin_tokens)).json()
    assert logs["total"] > 0
    assert any(item["action"] == "user.role_update" for item in logs["items"])

    # admin must not demote themselves below admin
    resp = client.patch(f"/api/v1/users/{me['id']}/role", headers=auth_header(admin_tokens),
                        json={"role": "employee"})
    assert resp.status_code == 400


def test_assignment_requires_support(client):
    employee_token = register(client, "pam@acme.io", "Pam P")["access_token"]
    ticket = _ticket(client, employee_token, "Printer", "Floor 4 printer offline")
    resp = client.post(f"/api/v1/tickets/{ticket['id']}/assign",
                       headers=auth_header(employee_token), json={"assignee_id": None})
    assert resp.status_code == 403
