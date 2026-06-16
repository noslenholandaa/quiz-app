"""Tests for Sprint 14.5 — Production Readiness & Observability."""


def test_request_id_header_present(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) == 36


def test_request_id_unique_per_request(client):
    resp1 = client.get("/health")
    resp2 = client.get("/health")
    assert resp1.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]


def test_request_id_on_error(client):
    resp = client.get("/quizzes/99999")
    assert resp.status_code == 404
    assert "X-Request-ID" in resp.headers


def test_request_id_on_auth_error(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert "X-Request-ID" in resp.headers


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "uptime_seconds" in data
    assert "total_users" in data
    assert "total_quizzes" in data
    assert "total_submissions" in data
    assert "database" in data
    assert "version" in data
    assert data["uptime_seconds"] >= 0
    assert data["total_users"] >= 0
    assert data["total_quizzes"] >= 0
    assert data["total_submissions"] >= 0
    assert data["database"] in ("sqlite", "postgresql")
    assert isinstance(data["version"], str)


def test_metrics_after_activity(client):
    resp = client.post("/auth/register", json={
        "name": "Metrics User", "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/quizzes", json={
        "title": "Metrics Quiz", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=headers)

    client.post("/quizzes/1/submit", json={
        "answers": [{"question_id": 1, "value": "test"}],
    }, headers=headers)

    resp = client.get("/metrics")
    data = resp.json()
    assert data["total_users"] >= 1
    assert data["total_quizzes"] >= 1
    assert data["total_submissions"] >= 1


def test_health_expanded(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "database_type" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert "environment" in data
    assert "timestamp" in data
    assert data["uptime_seconds"] >= 0


def test_health_backwards_compatible(client):
    resp = client.get("/health")
    data = resp.json()
    assert "status" in data
    assert "environment" in data
    assert "timestamp" in data


def test_health_database_still_works(client):
    resp = client.get("/health/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"


def test_middleware_does_not_break_quizzes(client):
    resp = client.post("/auth/register", json={
        "name": "Middleware Test", "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/quizzes", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_middleware_does_not_break_submit(client):
    resp = client.post("/auth/register", json={
        "name": "Submit Test", "email": "test@example.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/quizzes", json={
        "title": "Submit Middleware Quiz", "description": "",
        "questions": [{"id": 1, "text": "Q?", "type": "text", "required": True}],
    }, headers=headers)

    resp = client.post("/quizzes/1/submit", json={
        "answers": [{"question_id": 1, "value": "ok"}],
    }, headers=headers)
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
