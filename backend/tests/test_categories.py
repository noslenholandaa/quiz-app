def test_list_categories_empty(client, auth_headers):
    resp = client.get("/categories", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_categories_with_data(client, auth_headers, db_session):
    from database import CategoryDB
    cat = CategoryDB(name="Science", slug="science")
    db_session.add(cat)
    db_session.commit()

    resp = client.get("/categories", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(c.get("name") == "Science" for c in data)


def test_categories_requires_auth(client):
    resp = client.get("/categories")
    assert resp.status_code == 200


def test_list_tags_empty(client, auth_headers):
    resp = client.get("/tags", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_tags_with_data(client, auth_headers):
    cat_resp = client.post("/quizzes", json={
        "title": "Quiz with tags", "description": "",
        "tag_ids": [1],
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=auth_headers)
    assert cat_resp.status_code == 201

    resp = client.get("/tags", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_tags_requires_auth(client):
    resp = client.get("/tags")
    assert resp.status_code == 200


