import hashlib
import os
from datetime import datetime, timezone, timedelta


def test_forgot_password_existing_email(client, db_session):
    client.post("/auth/register", json={
        "name": "Test", "email": "fp@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "enviadas" in data["message"]


def test_forgot_password_nonexistent_email(client):
    resp = client.post("/auth/forgot-password", json={"email": "ghost@nowhere.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "enviadas" in data["message"]


def test_forgot_password_same_message_always(client):
    client.post("/auth/register", json={
        "name": "Test", "email": "same@test.com", "password": "password123",
    })
    resp_existing = client.post("/auth/forgot-password", json={"email": "same@test.com"})
    resp_missing = client.post("/auth/forgot-password", json={"email": "missing@test.com"})
    assert resp_existing.status_code == 200
    assert resp_missing.status_code == 200
    assert resp_existing.json()["message"] == resp_missing.json()["message"]


def test_reset_password_success(client, db_session):
    from database import PasswordResetTokenDB, UserDB

    client.post("/auth/register", json={
        "name": "Test", "email": "reset@test.com", "password": "password123",
    })

    user = db_session.query(UserDB).filter(UserDB.email == "reset@test.com").first()
    raw = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    reset = PasswordResetTokenDB(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(reset)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={
        "token": raw,
        "new_password": "novaSenha123",
    })
    assert resp.status_code == 200

    resp = client.post("/auth/login", json={
        "email": "reset@test.com", "password": "novaSenha123",
    })
    assert resp.status_code == 200


def test_reset_password_expired_token(client, db_session):
    from database import PasswordResetTokenDB, UserDB

    client.post("/auth/register", json={
        "name": "Test", "email": "expired@test.com", "password": "password123",
    })

    user = db_session.query(UserDB).filter(UserDB.email == "expired@test.com").first()
    raw = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    reset = PasswordResetTokenDB(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db_session.add(reset)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={
        "token": raw,
        "new_password": "novaSenha123",
    })
    assert resp.status_code == 400
    assert "expirado" in resp.json()["detail"]


def test_reset_password_reused_token(client, db_session):
    from database import PasswordResetTokenDB, UserDB

    client.post("/auth/register", json={
        "name": "Test", "email": "reuse@test.com", "password": "password123",
    })

    user = db_session.query(UserDB).filter(UserDB.email == "reuse@test.com").first()
    raw = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    reset = PasswordResetTokenDB(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used=True,
    )
    db_session.add(reset)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={
        "token": raw,
        "new_password": "novaSenha123",
    })
    assert resp.status_code == 400


def test_forgot_password_production_returns_token_demo_mode(monkeypatch, client, db_session):
    monkeypatch.setattr("app.services.auth_service.ENVIRONMENT", "production")
    client.post("/auth/register", json={
        "name": "Prod", "email": "fp-prod@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-prod@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert data["reset_url"] is not None
    assert "/static/reset-password.html?token=" in data["reset_url"]


def test_forgot_password_testing_returns_token(monkeypatch, client):
    monkeypatch.setattr("app.services.auth_service.ENVIRONMENT", "testing")
    resp = client.post("/auth/forgot-password", json={"email": "test-skip@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reset_url"] is None


def test_forgot_password_logs_url(monkeypatch, client, db_session):
    logged = []
    monkeypatch.setattr("app.services.auth_service.logger.info", lambda msg, *args: logged.append((msg, args)))
    client.post("/auth/register", json={
        "name": "Dev", "email": "fp-dev@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-dev@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reset_url"] is not None
    assert "token=" in data["reset_url"]
    reset_logs = [(msg, args) for msg, args in logged if "Password reset token generated" in msg]
    assert len(reset_logs) == 1


def test_forgot_password_nonexistent_no_token(monkeypatch, client):
    resp = client.post("/auth/forgot-password", json={"email": "ghost@nowhere.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reset_url"] is None


def test_forgot_password_no_smtp_error(monkeypatch, client, db_session):
    client.post("/auth/register", json={
        "name": "Fail", "email": "fp-fail@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-fail@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "instruções" in data["message"]
    assert data["reset_url"] is not None
    assert "SMTP" not in data["message"]


def test_reset_password_invalid_token(client):
    resp = client.post("/auth/reset-password", json={
        "token": "invalidtoken123",
        "new_password": "novaSenha123",
    })
    assert resp.status_code == 400


def test_reset_password_short_password(client, db_session):
    from database import PasswordResetTokenDB, UserDB

    client.post("/auth/register", json={
        "name": "Test", "email": "short@test.com", "password": "password123",
    })

    user = db_session.query(UserDB).filter(UserDB.email == "short@test.com").first()
    raw = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    reset = PasswordResetTokenDB(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(reset)
    db_session.commit()

    resp = client.post("/auth/reset-password", json={
        "token": raw,
        "new_password": "abc",
    })
    assert resp.status_code == 422
