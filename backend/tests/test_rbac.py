def test_user_cannot_access_admin_dashboard(client):
    client.post("/auth/register", json={
        "name": "User", "email": "user@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "user@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    resp = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_user_cannot_list_admin_users(client):
    client.post("/auth/register", json={
        "name": "User", "email": "user2@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "user2@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_can_access_admin_dashboard(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    resp = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_admins" in data
    assert "total_quizzes" in data
    assert "total_submissions" in data
    assert "users" in data


def test_admin_can_list_users(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_promote_user_to_admin(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    client.post("/auth/register", json={
        "name": "User", "email": "promote@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    users_resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    users = users_resp.json()
    target = [u for u in users if u["email"] == "promote@test.com"][0]

    resp = client.put(f"/admin/users/{target['id']}/role", json={"role": "admin"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    updated = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    u = [u for u in updated.json() if u["email"] == "promote@test.com"][0]
    assert u["role"] == "admin"


def test_demote_admin_to_user(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    client.post("/auth/register", json={
        "name": "User", "email": "demote@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    users_resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    users = users_resp.json()
    target = [u for u in users if u["email"] == "demote@test.com"][0]

    client.put(f"/admin/users/{target['id']}/role", json={"role": "admin"},
               headers={"Authorization": f"Bearer {token}"})

    resp = client.put(f"/admin/users/{target['id']}/role", json={"role": "user"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_admin_cannot_self_demote(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    resp = client.put(f"/admin/users/{me['id']}/role", json={"role": "user"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_invalid_role_rejected(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    resp = client.put(f"/admin/users/{me['id']}/role", json={"role": "superadmin"},
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_patch_endpoint_works(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    client.post("/auth/register", json={
        "name": "User", "email": "patch@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    users = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"}).json()
    target = [u for u in users if u["email"] == "patch@test.com"][0]

    resp = client.patch(f"/admin/users/{target['id']}/role", json={"role": "admin"},
                        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
