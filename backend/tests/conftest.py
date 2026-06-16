import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient


_test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _test_dir)

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'quiz_app_test.db')}"
os.environ["RATE_LIMIT_REGISTER_PER_HOUR"] = "1000"
os.environ["RATE_LIMIT_LOGIN_PER_MINUTE"] = "1000"
os.environ["ADMIN_EMAILS"] = "test@example.com,userb@example.com"
os.environ["ENVIRONMENT"] = "testing"

from database import Base, engine # noqa: E402
from main import app              # noqa: E402


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(_clean_db):
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(_clean_db):
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(client):
    resp = client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200, f"register failed: {resp.text}"
    data = resp.json()
    return data["access_token"], data["refresh_token"]

@pytest.fixture
def test_user_id(client, test_user):
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {test_user[0]}"})
    return me.json()["id"] if me.status_code == 200 else None

@pytest.fixture
def user_b(client):
    resp = client.post("/auth/register", json={
        "name": "User B",
        "email": "userb@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200, f"register user_b failed: {resp.text}"
    data = resp.json()
    return data["access_token"], data["refresh_token"]


@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user[0]}"}


@pytest.fixture
def auth_headers_b(user_b):
    return {"Authorization": f"Bearer {user_b[0]}"}


@pytest.fixture
def created_quiz(client, auth_headers):
    resp = client.post("/quizzes", json={
        "title": "Test Quiz",
        "description": "A test quiz",
        "questions": [
            {"id": 1, "text": "Q1?", "type": "text", "required": True},
            {"id": 2, "text": "Choose:", "type": "single_choice", "required": True,
             "options": [{"id": 1, "text": "A"}, {"id": 2, "text": "B"}]},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201, f"create quiz failed: {resp.text}"
    return resp.json()
