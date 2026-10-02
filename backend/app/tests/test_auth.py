from app.tests.conftest import auth_header, login, register


def test_register_login_me(client):
    tokens = register(client, "alice@acme.io", "Alice A")
    assert tokens["access_token"] and tokens["refresh_token"]

    login_resp = login(client, "alice@acme.io")
    me = client.get("/api/v1/auth/me", headers=auth_header(login_resp["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@acme.io"
    assert me.json()["role"] == "employee"


def test_refresh_rotates_tokens(client):
    tokens = register(client, "bob@acme.io", "Bob B")
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new = resp.json()
    assert new["access_token"] != tokens["access_token"]
    # old refresh token is now revoked
    resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp2.status_code == 401


def test_login_wrong_password(client):
    register(client, "carol@acme.io", "Carol C")
    resp = client.post("/api/v1/auth/login", json={"email": "carol@acme.io", "password": "wrongpass1"})
    assert resp.status_code == 401


def test_register_duplicate_email(client):
    register(client, "dave@acme.io", "Dave D")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dave@acme.io", "full_name": "Imposter", "password": "password123"},
    )
    assert resp.status_code == 409


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_bad_token_rejected(client):
    resp = client.get("/api/v1/auth/me", headers=auth_header("not-a-jwt"))
    assert resp.status_code == 401


def test_registration_is_employee_role(client):
    tokens = register(client, "erin@acme.io", "Erin E")
    me = client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"])).json()
    assert me["role"] == "employee"
