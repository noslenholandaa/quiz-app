def test_create_quiz_success(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "New Quiz", "description": "Desc",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Quiz"
    assert data["description"] == "Desc"
    assert len(data["questions"]) == 1


def test_create_quiz_no_title(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_quiz_whitespace_title(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "   ", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_quiz_no_questions(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "Title", "description": "", "questions": [],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_quiz_empty_question_text(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "Title", "description": "",
        "questions": [{"id": 1, "text": "", "type": "text", "required": True}],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_create_quiz_not_enough_options(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "Title", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "single_choice", "required": True,
                       "options": [{"id": 1, "text": "Only one"}]}],
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_list_quizzes_includes_seed(client, auth_headers):
    resp = client.get("/quizzes", headers=auth_headers)
    assert resp.status_code == 200
    quizzes = resp.json()
    assert len(quizzes) >= 2


def test_list_my_quizzes(client, auth_headers, created_quiz):
    resp = client.get("/me/quizzes", headers=auth_headers)
    assert resp.status_code == 200
    quizzes = resp.json()
    assert len(quizzes) == 1
    assert quizzes[0]["id"] == created_quiz["id"]


def test_get_quiz(client, created_quiz):
    resp = client.get(f"/quizzes/{created_quiz['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == created_quiz["title"]


def test_get_quiz_not_found(client):
    resp = client.get("/quizzes/99999")
    assert resp.status_code == 404


def test_update_quiz_own(client, auth_headers, created_quiz):
    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "title": "Updated Title",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_update_quiz_other_admin_forbidden(client, auth_headers, auth_headers_b, created_quiz):
    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "title": "Hacked",
    }, headers=auth_headers_b)
    assert resp.status_code == 403


def test_update_quiz_seed(client, auth_headers):
    resp = client.put("/quizzes/1", json={
        "title": "Hacked",
    }, headers=auth_headers)
    assert resp.status_code == 403


def test_update_quiz_empty_title(client, auth_headers, created_quiz):
    resp = client.put(f"/quizzes/{created_quiz['id']}", json={
        "title": "",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_update_quiz_not_found(client, auth_headers):
    resp = client.put("/quizzes/99999", json={"title": "Nope"}, headers=auth_headers)
    assert resp.status_code == 404


def test_delete_quiz_own(client, auth_headers, created_quiz):
    resp = client.delete(f"/quizzes/{created_quiz['id']}", headers=auth_headers)
    assert resp.status_code == 204
    resp = client.get(f"/quizzes/{created_quiz['id']}")
    assert resp.status_code == 404


def test_delete_quiz_other_admin_forbidden(client, auth_headers, auth_headers_b, created_quiz):
    resp = client.delete(f"/quizzes/{created_quiz['id']}", headers=auth_headers_b)
    assert resp.status_code == 403


def test_delete_quiz_seed(client, auth_headers):
    resp = client.delete("/quizzes/1", headers=auth_headers)
    assert resp.status_code == 403


def test_delete_quiz_not_found(client, auth_headers):
    resp = client.delete("/quizzes/99999", headers=auth_headers)
    assert resp.status_code == 404
