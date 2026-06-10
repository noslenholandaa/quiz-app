def test_refresh_success(client, test_user):
    _, refresh_token = test_user
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token


def test_refresh_revokes_old_token(client, test_user):
    _, refresh_token = test_user
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_refresh_invalid_token(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "invalidtoken123"})
    assert resp.status_code == 401


def test_logout_success(client, test_user):
    _, refresh_token = test_user
    resp = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 204


def test_logout_revokes_token(client, test_user):
    _, refresh_token = test_user
    client.post("/auth/logout", json={"refresh_token": refresh_token})
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_list_sessions(client, test_user):
    access_token, _ = test_user
    resp = client.get("/auth/sessions", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1


def test_revoke_session(client, test_user):
    access_token, _ = test_user
    resp = client.get("/auth/sessions", headers={"Authorization": f"Bearer {access_token}"})
    sessions = resp.json()
    session_id = sessions[0]["id"]
    resp = client.delete(f"/auth/sessions/{session_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 204
    resp = client.get("/auth/sessions", headers={"Authorization": f"Bearer {access_token}"})
    assert len(resp.json()) == 0


def test_revoke_nonexistent_session(client, test_user):
    access_token, _ = test_user
    resp = client.delete("/auth/sessions/99999", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 404
