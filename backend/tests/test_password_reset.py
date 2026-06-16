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


def test_forgot_password_production_attempts_email(monkeypatch, client, db_session):
    monkeypatch.setattr("auth.ENVIRONMENT", "production")
    import auth
    assert auth.ENVIRONMENT == "production"
    sent = {"called": False}

    def fake_send(email, url):
        sent["called"] = True
        assert email == "fp-prod@test.com"
        assert "/static/reset-password.html?token=" in url
        return True

    monkeypatch.setattr("auth.send_password_reset_email", fake_send)
    client.post("/auth/register", json={
        "name": "Prod", "email": "fp-prod@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-prod@test.com"})
    assert resp.status_code == 200
    assert sent["called"] is True


def test_forgot_password_testing_skips_email(monkeypatch, client):
    monkeypatch.setattr("auth.ENVIRONMENT", "testing")
    called = False

    def fake_send(email, url):
        nonlocal called
        called = True

    monkeypatch.setattr("auth.send_password_reset_email", fake_send)
    resp = client.post("/auth/forgot-password", json={"email": "test-skip@test.com"})
    assert resp.status_code == 200
    assert called is False


def test_forgot_password_development_logs_url(monkeypatch, client, db_session):
    logged = []
    monkeypatch.setattr("auth.logger.info", lambda msg, *args: logged.append((msg, args)))
    monkeypatch.setattr("auth.ENVIRONMENT", "development")
    client.post("/auth/register", json={
        "name": "Dev", "email": "fp-dev@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-dev@test.com"})
    assert resp.status_code == 200
    dev_calls = [(msg, args) for msg, args in logged if "[DEV] Reset URL" in msg]
    assert len(dev_calls) == 1
    assert "fp-dev@test.com" in dev_calls[0][1][0]


def test_forgot_password_nonexistent_no_email_sent(monkeypatch, client):
    called = False

    def fake_send(email, url):
        nonlocal called
        called = True

    monkeypatch.setattr("auth.send_password_reset_email", fake_send)
    resp = client.post("/auth/forgot-password", json={"email": "ghost@nowhere.com"})
    assert resp.status_code == 200
    assert called is False


def test_forgot_password_smtp_failure_no_leak(monkeypatch, client, db_session):
    logged = []
    monkeypatch.setattr("auth.logger.error", lambda msg, *args: logged.append((msg, args)))
    monkeypatch.setattr("auth.ENVIRONMENT", "production")

    def failing_send(email, url):
        raise RuntimeError("SMTP interno explodiu")

    monkeypatch.setattr("auth.send_password_reset_email", failing_send)
    client.post("/auth/register", json={
        "name": "Fail", "email": "fp-fail@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-fail@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "instruções" in data["message"]
    assert "token" not in data
    assert "SMTP" not in data["message"]
    error_calls = [(msg, args) for msg, args in logged if "Failed to send password reset email" in msg]
    assert len(error_calls) == 1


def test_forgot_password_token_not_in_logs(monkeypatch, client, db_session, caplog):
    import logging
    caplog.set_level(logging.INFO)
    monkeypatch.setattr("auth.ENVIRONMENT", "production")
    monkeypatch.setattr("auth.send_password_reset_email", lambda e, u: True)
    client.post("/auth/register", json={
        "name": "NoLeak", "email": "fp-noleak@test.com", "password": "password123",
    })
    resp = client.post("/auth/forgot-password", json={"email": "fp-noleak@test.com"})
    assert resp.status_code == 200
    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "token=" not in log_text
    assert "/reset-password.html?token=" not in log_text


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
