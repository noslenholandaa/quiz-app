def submit_quiz(client, token, quiz_id, answers):
    headers = {"Authorization": f"Bearer {token}"}
    return client.post(f"/quizzes/{quiz_id}/submit", json={"answers": answers}, headers=headers)


def test_leaderboard_empty(client, auth_headers):
    resp = client.get("/leaderboard", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_leaderboard_ordered(client, test_user, user_b):
    token_a, _ = test_user
    token_b, _ = user_b
    quiz1_answers = [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ]
    quiz2_answers = [
        {"question_id": 1, "value": "Brasília"},
        {"question_id": 2, "value": ["1", "2"]},
        {"question_id": 3, "value": "1969"},
    ]
    submit_quiz(client, token_a, 1, quiz1_answers)
    submit_quiz(client, token_a, 2, quiz2_answers)
    submit_quiz(client, token_b, 1, quiz1_answers)

    resp = client.get("/leaderboard", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["total_score"] >= data[1]["total_score"]


def test_leaderboard_pagination(client, test_user):
    token, _ = test_user
    for _ in range(3):
        submit_quiz(client, token, 1, [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": ["1"]},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "ok"},
        ])
    resp = client.get("/leaderboard?page=1&limit=1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp2 = client.get("/leaderboard?page=1&limit=100", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200


def test_leaderboard_limit_max(client, test_user):
    token, _ = test_user
    resp = client.get("/leaderboard?limit=200", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


def test_quiz_leaderboard(client, test_user):
    token, _ = test_user
    submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ])
    resp = client.get("/quizzes/1/leaderboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["score"] == 4
    assert data[0]["max_score"] == 4
    assert data[0]["percentage"] == 100


def test_quiz_leaderboard_not_found(client, test_user):
    token, _ = test_user
    resp = client.get("/quizzes/99999/leaderboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_quiz_leaderboard_multiple_users(client, test_user, user_b):
    token_a, _ = test_user
    token_b, _ = user_b
    answers = [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ]
    submit_quiz(client, token_a, 1, answers)
    submit_quiz(client, token_b, 1, answers)
    resp = client.get("/quizzes/1/leaderboard", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_quiz_leaderboard_limit(client, test_user):
    token, _ = test_user
    for _ in range(5):
        submit_quiz(client, token, 1, [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": ["1"]},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "ok"},
        ])
    resp = client.get("/quizzes/1/leaderboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) <= 20


def test_public_profile(client, test_user):
    token, _ = test_user
    submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ])
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    resp = client.get(f"/users/{me['id']}/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test User"
    assert data["role"] == "admin"
    assert data["quizzes_created"] >= 0
    assert data["submissions"] >= 1
    assert data["average_score"] > 0
    assert data["best_score"] == 100


def test_public_profile_not_found(client):
    resp = client.get("/users/99999/profile")
    assert resp.status_code == 404


def test_public_profile_no_email(client, test_user):
    token, _ = test_user
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    resp = client.get(f"/users/{me['id']}/profile")
    data = resp.json()
    assert "email" not in data
    assert "password_hash" not in str(data)


def test_badges_first_quiz(client, test_user):
    token, _ = test_user
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    resp = client.get(f"/users/{me['id']}/profile").json()
    initial_badges = len(resp["badges"])

    submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ])
    resp2 = client.get(f"/users/{me['id']}/profile").json()
    names = [b["name"] for b in resp2["badges"]]
    assert "Primeiro Quiz Respondido" in names
    assert len(resp2["badges"]) > initial_badges


def test_badges_perfectionist(client, test_user):
    token, _ = test_user
    submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ])
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    resp = client.get(f"/users/{me['id']}/profile").json()
    names = [b["name"] for b in resp["badges"]]
    assert "Perfeccionista" in names


def test_score_calculated(client, test_user):
    token, _ = test_user
    resp = submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ])
    data = resp.json()
    assert data["score"] == 4
    assert data["max_score"] == 4
    assert data["percentage"] == 100


def test_score_100_percent(client, test_user):
    token, _ = test_user
    resp = submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "otimo"},
    ])
    data = resp.json()
    assert data["score"] == 4
    assert data["percentage"] == 100


def test_dashboard_ranking_position(client, test_user):
    token, _ = test_user
    submit_quiz(client, token, 1, [
        {"question_id": 1, "value": 5},
        {"question_id": 2, "value": ["1"]},
        {"question_id": 3, "value": "1"},
        {"question_id": 4, "value": "ok"},
    ])
    resp = client.get("/me/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["best_percentage"] == 100
    assert data["average_percentage"] == 100.0
    assert data["ranking_position"] == 1


def test_list_submissions_includes_score(client, auth_headers):
    client.post("/quizzes/1/submit", json={
        "answers": [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": ["1"]},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "Nice"},
        ],
    }, headers=auth_headers)
    resp = client.get("/me/submissions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert "score" in data["items"][0]
    assert "max_score" in data["items"][0]
    assert "percentage" in data["items"][0]
