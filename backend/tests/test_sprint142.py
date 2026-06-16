"""Tests for Sprint 14.2 — SQL Aggregation Refactor."""


def submit_quiz(client, token, quiz_id, answers):
    headers = {"Authorization": f"Bearer {token}"}
    return client.post(f"/quizzes/{quiz_id}/submit", json={"answers": answers}, headers=headers)


# ── 1. Admin dashboard continues correct ──

def test_admin_dashboard_aggregation(client):
    resp = client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/quizzes", json={
        "title": "Admin Quiz", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=headers)

    resp = client.get("/admin/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_users"] >= 1
    assert data["total_admins"] >= 1
    assert data["total_quizzes"] >= 1
    assert data["total_submissions"] >= 0
    assert len(data["users"]) >= 1
    user_entry = [u for u in data["users"] if u["email"] == "test@example.com"]
    assert len(user_entry) == 1
    assert user_entry[0]["quizzes_count"] >= 1


# ── 2. Admin users continues correct ──

def test_admin_users_aggregation(client):
    client.post("/auth/register", json={
        "name": "Admin", "email": "test@example.com", "password": "password123",
    })
    client.post("/auth/register", json={
        "name": "User A", "email": "usera@test.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/admin/users", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    emails = [u["email"] for u in data]
    assert "test@example.com" in emails
    assert "usera@test.com" in emails


# ── 3. Dashboard continues returning same metrics ──

def test_dashboard_metrics_after_activity(client):
    resp = client.post("/auth/register", json={
        "name": "Test User", "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    quiz_resp = client.post("/quizzes", json={
        "title": "Metric Quiz", "description": "",
        "questions": [
            {"id": 1, "text": "Q1?", "type": "text", "required": True},
            {"id": 2, "text": "Rating?", "type": "rating", "required": True,
             "options": [{"id": 1, "text": "1"}, {"id": 2, "text": "2"}, {"id": 3, "text": "3"}]},
        ],
    }, headers=headers)
    quiz_id = quiz_resp.json()["id"]

    submit_quiz(client, token, quiz_id, [
        {"question_id": 1, "value": "Answer"},
        {"question_id": 2, "value": 3},
    ])

    resp = client.get("/me/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_quizzes_created"] >= 1
    assert data["total_quizzes_responded"] >= 1
    assert data["total_submissions"] >= 1
    assert data["total_answers_submitted"] >= 2
    assert data["best_percentage"] > 0
    assert data["average_percentage"] > 0


def test_dashboard_initial_state(client):
    resp = client.post("/auth/register", json={
        "name": "Fresh User", "email": "fresh@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/me/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_quizzes_created"] == 0
    assert data["total_quizzes_responded"] == 0
    assert data["total_submissions"] == 0
    assert data["total_answers_submitted"] == 0


# ── 4. Profile continues returning same badges ──

def test_profile_badges_aggregation(client):
    resp = client.post("/auth/register", json={
        "name": "Badge User", "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers).json()
    user_id = me["id"]

    profile = client.get(f"/users/{user_id}/profile")
    assert profile.status_code == 200
    data = profile.json()
    assert data["name"] == "Badge User"
    assert data["submissions"] == 0
    assert len(data["badges"]) == 0

    quiz_resp = client.post("/quizzes", json={
        "title": "Badge Quiz", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=headers)
    quiz_id = quiz_resp.json()["id"]

    submit_quiz(client, token, quiz_id, [{"question_id": 1, "value": "ok"}])

    profile = client.get(f"/users/{user_id}/profile")
    data = profile.json()
    assert data["submissions"] >= 1
    badge_names = [b["name"] for b in data["badges"]]
    assert "Primeiro Quiz Respondido" in badge_names
    assert "Criador" in badge_names
    assert "Perfeccionista" in badge_names


# ── 5. Ranking continues correct ──

def test_ranking_aggregation(client):
    resp_a = client.post("/auth/register", json={
        "name": "User A", "email": "test@example.com", "password": "password123",
    })
    token_a = resp_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    quiz_resp = client.post("/quizzes", json={
        "title": "Rank Quiz", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=headers_a)
    quiz_id = quiz_resp.json()["id"]

    submit_quiz(client, token_a, quiz_id, [{"question_id": 1, "value": "ok"}])

    resp_b = client.post("/auth/register", json={
        "name": "User B", "email": "userb@example.com", "password": "password123",
    })
    token_b = resp_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    submit_quiz(client, token_b, quiz_id, [{"question_id": 1, "value": "yes"}])

    me_a = client.get("/auth/me", headers=headers_a).json()
    profile_a = client.get(f"/users/{me_a['id']}/profile")
    assert profile_a.json()["ranking_position"] == 1

    me_b = client.get("/auth/me", headers=headers_b).json()
    profile_b = client.get(f"/users/{me_b['id']}/profile")
    assert profile_b.json()["ranking_position"] >= 1


# ── 6. Dashboard ranking_position present ──

def test_dashboard_ranking_position(client):
    client.post("/auth/register", json={
        "name": "Rank User", "email": "test@example.com", "password": "password123",
    })
    resp = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/me/dashboard", headers=headers)
    assert resp.status_code == 200
    assert "ranking_position" in resp.json()
