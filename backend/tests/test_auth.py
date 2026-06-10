def test_register_success(client):
    resp = client.post("/auth/register", json={
        "name": "Alice", "email": "alice@example.com", "password": "secret123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "name": "Alice", "email": "dup@example.com", "password": "secret123",
    })
    resp = client.post("/auth/register", json={
        "name": "Bob", "email": "dup@example.com", "password": "secret456",
    })
    assert resp.status_code == 409
    assert "já cadastrado" in resp.json()["detail"]


def test_register_empty_name(client):
    resp = client.post("/auth/register", json={
        "name": "", "email": "a@b.com", "password": "secret123",
    })
    assert resp.status_code == 422


def test_register_whitespace_name(client):
    resp = client.post("/auth/register", json={
        "name": "   ", "email": "b@c.com", "password": "secret123",
    })
    assert resp.status_code == 422


def test_register_empty_password(client):
    resp = client.post("/auth/register", json={
        "name": "Test", "email": "c@d.com", "password": "",
    })
    assert resp.status_code == 422


def test_register_whitespace_password(client):
    resp = client.post("/auth/register", json={
        "name": "Test", "email": "d@e.com", "password": "   ",
    })
    assert resp.status_code == 422


def test_register_short_password_4chars(client):
    resp = client.post("/auth/register", json={
        "name": "Test", "email": "e@f.com", "password": "abcd",
    })
    assert resp.status_code == 422


def test_register_short_password_5chars(client):
    resp = client.post("/auth/register", json={
        "name": "Test", "email": "f@g.com", "password": "abcde",
    })
    assert resp.status_code == 422


def test_login_success(client):
    client.post("/auth/register", json={
        "name": "Test", "email": "login@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "login@test.com", "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid_email(client):
    resp = client.post("/auth/login", json={
        "email": "noone@example.com", "password": "password123",
    })
    assert resp.status_code == 401


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "name": "Test", "email": "wp@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "wp@test.com", "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_me_valid_token(client):
    client.post("/auth/register", json={
        "name": "Test User", "email": "me@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "me@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"
    assert resp.json()["name"] == "Test User"


def test_me_no_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert resp.status_code == 401
