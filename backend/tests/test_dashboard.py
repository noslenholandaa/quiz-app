def test_dashboard_initial(client, test_user):
    access_token, _ = test_user
    resp = client.get("/me/dashboard", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_quizzes_created"] == 0
    assert data["total_quizzes_responded"] == 0
    assert data["total_submissions"] == 0
    assert data["total_answers_submitted"] == 0
    assert data["recent_quizzes"] == []
    assert data["recent_submissions"] == []


def test_dashboard_after_activity(client, auth_headers, created_quiz):
    client.post(f"/quizzes/{created_quiz['id']}/submit", json={
        "answers": [
            {"question_id": 1, "value": "Answer text"},
            {"question_id": 2, "value": "1"},
        ],
    }, headers=auth_headers)
    resp = client.get("/me/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_quizzes_created"] == 1
    assert data["total_quizzes_responded"] == 1
    assert data["total_submissions"] == 1
    assert data["total_answers_submitted"] == 2
    assert len(data["recent_quizzes"]) == 1
    assert len(data["recent_submissions"]) == 1


def test_stats_initial(client, test_user):
    access_token, _ = test_user
    resp = client.get("/me/stats", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_7_days"]["submissions"] == 0
    assert data["last_7_days"]["quizzes_created"] == 0
    assert data["last_30_days"]["submissions"] == 0
    assert data["last_30_days"]["quizzes_created"] == 0


def test_stats_after_activity(client, auth_headers, created_quiz):
    client.post(f"/quizzes/{created_quiz['id']}/submit", json={
        "answers": [
            {"question_id": 1, "value": "Text"},
            {"question_id": 2, "value": "1"},
        ],
    }, headers=auth_headers)
    resp = client.get("/me/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_7_days"]["submissions"] >= 1
    assert data["last_7_days"]["quizzes_created"] >= 1
    assert data["last_30_days"]["submissions"] >= 1
    assert data["last_30_days"]["quizzes_created"] >= 1


def test_dashboard_requires_auth(client):
    resp = client.get("/me/dashboard")
    assert resp.status_code == 401


def test_stats_requires_auth(client):
    resp = client.get("/me/stats")
    assert resp.status_code == 401
