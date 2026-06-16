def test_search_by_title(client, auth_headers):
    client.post("/quizzes", json={
        "title": "Python Basics Quiz", "description": "Learn Python",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)

    resp = client.get("/quizzes/search?q=Python", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    titles = [i["title"] for i in data["items"]]
    assert any("Python" in t for t in titles)


def test_search_by_description(client, auth_headers):
    client.post("/quizzes", json={
        "title": "Math Quiz", "description": "Advanced mathematics concepts",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)

    resp = client.get("/quizzes/search?q=mathematics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_search_no_results(client, auth_headers):
    resp = client.get("/quizzes/search?q=ThisDoesNotExist12345", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_search_case_insensitive(client, auth_headers):
    client.post("/quizzes", json={
        "title": "Case Test Quiz", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)

    resp = client.get("/quizzes/search?q=case test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    resp = client.get("/quizzes/search?q=CASE TEST", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_search_pagination(client, auth_headers):
    for i in range(5):
        client.post("/quizzes", json={
            "title": f"Search Paging Quiz {i}", "description": "",
            "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
        }, headers=auth_headers)

    resp = client.get("/quizzes/search?q=Search+Paging&page=1&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 2


def test_search_empty_query(client, auth_headers):
    resp = client.get("/quizzes/search?q=", headers=auth_headers)
    assert resp.status_code == 200


def test_search_requires_auth(client):
    resp = client.get("/quizzes/search?q=test")
    assert resp.status_code == 401



def test_profile_public_contains_views_and_ranking(client, auth_headers, test_user_id):
    resp = client.get(f"/users/{test_user_id}/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_views" in data
    assert "ranking_position" in data
    assert "quizzes" in data



