def test_submit_success(client, auth_headers):
    resp = client.post("/quizzes/1/submit", json={
        "answers": [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": ["1", "3"]},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "Great service!"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["quiz_id"] == 1
    assert data["quiz_title"] == "Pesquisa de Satisfação"
    assert len(data["answers"]) == 4


def test_submit_quiz_not_found(client, auth_headers):
    resp = client.post("/quizzes/99999/submit", json={
        "answers": [],
    }, headers=auth_headers)
    assert resp.status_code == 404


def test_submit_invalid_question(client, auth_headers):
    resp = client.post("/quizzes/1/submit", json={
        "answers": [
            {"question_id": 999, "value": "test"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_submit_multiple_choice_empty(client, auth_headers):
    resp = client.post("/quizzes/1/submit", json={
        "answers": [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": []},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "ok"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200
    ans = resp.json()["answers"]
    mc_answer = [a for a in ans if a["question_id"] == 2][0]["answer"]
    assert mc_answer == []


def test_submit_multiple_choice_selected(client, auth_headers):
    resp = client.post("/quizzes/1/submit", json={
        "answers": [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": ["1", "2"]},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "ok"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200
    ans = resp.json()["answers"]
    mc_answer = [a for a in ans if a["question_id"] == 2][0]["answer"]
    assert mc_answer == ["1", "2"]


def test_list_submissions(client, auth_headers):
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
    assert data["items"][0]["quiz_id"] == 1


def test_submissions_isolation(client, auth_headers, auth_headers_b):
    client.post("/quizzes/1/submit", json={
        "answers": [
            {"question_id": 1, "value": 5},
            {"question_id": 2, "value": ["1"]},
            {"question_id": 3, "value": "1"},
            {"question_id": 4, "value": "User A"},
        ],
    }, headers=auth_headers)
    resp = client.get("/me/submissions", headers=auth_headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
