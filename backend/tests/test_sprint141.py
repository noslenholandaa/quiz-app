"""Tests for Sprint 14.1 — performance quick wins."""


def test_submissions_pagination_defaults(client, auth_headers, db_session):
    """GET /me/submissions returns paginated response with defaults."""
    resp = client.get("/me/submissions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "page" in data
    assert "limit" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["limit"] == 20


def test_submissions_pagination_custom(client, auth_headers, db_session):
    """GET /me/submissions?page=1&limit=5 respects custom params."""
    for i in range(3):
        client.post("/quizzes/1/submit", json={
            "answers": [
                {"question_id": 1, "value": 5},
                {"question_id": 2, "value": ["1"]},
                {"question_id": 3, "value": "1"},
                {"question_id": 4, "value": f"Sub {i}"},
            ],
        }, headers=auth_headers)
    resp = client.get("/me/submissions?page=1&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["limit"] == 2
    assert data["total"] >= 3
    assert len(data["items"]) == 2


def test_submissions_pagination_page_out_of_range(client, auth_headers, db_session):
    """Page beyond results returns empty items list."""
    resp = client.get("/me/submissions?page=999", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 0
    assert data["total"] >= 0


def test_submissions_pagination_limit_capped(client, auth_headers, db_session):
    """limit > 100 is capped to 100."""
    resp = client.get("/me/submissions?limit=999", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] <= 100


def test_rate_limiter_no_crash(client):
    """Hitting login endpoint multiple times doesn't crash."""
    for _ in range(5):
        client.post("/auth/login", json={"email": "nonexistent@test.com", "password": "x"})
    resp = client.post("/auth/login", json={"email": "nonexistent@test.com", "password": "x"})
    assert resp.status_code in (200, 401, 422, 429)


def test_selectinload_structure(client, auth_headers):
    """Quiz list endpoints still return correct structure with eager loading."""
    resp = client.get("/quizzes", headers=auth_headers)
    assert resp.status_code == 200
    quizzes = resp.json()
    if quizzes:
        q = quizzes[0]
        assert "id" in q
        assert "title" in q
        assert "category" in q
        assert "tags" in q


def test_selectinload_search(client, auth_headers):
    """Search endpoint works with eager loading."""
    resp = client.get("/quizzes/search?q=quiz", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_selectinload_my_quizzes(client, auth_headers, db_session):
    """Admin's my quizzes endpoint works with eager loading."""
    from database import QuizDB
    existing = db_session.query(QuizDB).filter(
        QuizDB.user_id == 1
    ).first()
    if not existing:
        client.post("/quizzes", json={
            "title": "Eager Load Test",
            "description": "test",
            "questions": [{"id": 1, "text": "Q?", "type": "text", "required": False}],
        }, headers=auth_headers)
    resp = client.get("/me/quizzes", headers=auth_headers)
    assert resp.status_code == 200
    quizzes = resp.json()
    if quizzes:
        assert "category" in quizzes[0]
        assert "tags" in quizzes[0]


def test_get_quiz_eager_loading(client):
    """Single quiz endpoint works with eager loading."""
    resp = client.get("/quizzes/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "category" in data
    assert "tags" in data


def test_rate_limiter_gc_no_side_effect(client, auth_headers):
    """Rate limiter GC function doesn't break normal requests."""
    for _ in range(3):
        resp = client.get("/quizzes", headers=auth_headers)
        assert resp.status_code == 200


def test_migration_indexes_exist():
    """Check that the new indexes are defined in ORM model __table_args__."""
    from database import SubmissionDB, UserDB, RefreshTokenDB, PasswordResetTokenDB

    def _index_names(model_cls):
        args = getattr(model_cls, "__table_args__", None)
        if args is None:
            return set()
        return {idx.name for idx in args if hasattr(idx, "name")}

    sub_idxs = _index_names(SubmissionDB)
    assert "ix_submissions_user_id" in sub_idxs
    assert "ix_submissions_quiz_id" in sub_idxs
    assert "ix_submissions_created_at" in sub_idxs
    assert "ix_submissions_percentage" in sub_idxs

    user_idxs = _index_names(UserDB)
    assert "ix_users_role" in user_idxs

    rt_idxs = _index_names(RefreshTokenDB)
    assert "ix_refresh_tokens_expires_at" in rt_idxs

    prt_idxs = _index_names(PasswordResetTokenDB)
    assert "ix_password_reset_tokens_expires_at" in prt_idxs
