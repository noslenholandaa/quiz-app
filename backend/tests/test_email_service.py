from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _patch_config(monkeypatch):
    monkeypatch.setattr("services.email_service.SMTP_HOST", "smtp.test.com")
    monkeypatch.setattr("services.email_service.SMTP_PORT", 587)
    monkeypatch.setattr("services.email_service.SMTP_USERNAME", "")
    monkeypatch.setattr("services.email_service.SMTP_PASSWORD", "")
    monkeypatch.setattr("services.email_service.SMTP_FROM", "noreply@quizapp.com")
    monkeypatch.setattr("services.email_service.SMTP_USE_TLS", True)
    monkeypatch.setattr("services.email_service.SMTP_TIMEOUT", 30)


def test_send_email_success(monkeypatch):
    from services.email_service import send_email

    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = server

        result = send_email("user@test.com", "Subject", "<p>HTML</p>", "Text body")

        assert result is True
        mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=30)
        server.starttls.assert_called_once()
        server.send_message.assert_called_once()


def test_send_email_no_tls(monkeypatch):
    monkeypatch.setattr("services.email_service.SMTP_USE_TLS", False)

    from services.email_service import send_email

    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = server

        result = send_email("user@test.com", "Subject", "<p>HTML</p>", "Text body")

        assert result is True
        server.starttls.assert_not_called()


def test_send_email_smtp_failure(monkeypatch):
    import smtplib
    from services.email_service import send_email

    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value.send_message.side_effect = smtplib.SMTPException("Connection refused")

        result = send_email("user@test.com", "Subject", "<p>HTML</p>", "Text body")

        assert result is False


def test_send_email_no_host(monkeypatch):
    monkeypatch.setattr("services.email_service.SMTP_HOST", "")

    from services.email_service import send_email

    result = send_email("user@test.com", "Subject", "<p>HTML</p>", "Text body")
    assert result is False


def test_send_email_with_login(monkeypatch):
    monkeypatch.setattr("services.email_service.SMTP_USERNAME", "user")
    monkeypatch.setattr("services.email_service.SMTP_PASSWORD", "pass")
    monkeypatch.setattr("services.email_service.SMTP_USE_TLS", False)

    from services.email_service import send_email

    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = server

        result = send_email("user@test.com", "Subject", "<p>HTML</p>", "Text body")

        assert result is True
        server.login.assert_called_once_with("user", "pass")


def test_send_password_reset_email(monkeypatch):
    from services.email_service import send_password_reset_email

    with patch("services.email_service.send_email", return_value=True) as mock_send:
        result = send_password_reset_email("user@test.com", "http://localhost/reset?token=abc123")

        assert result is True
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == "user@test.com"
        assert args[1] == "Redefinição de senha — Quiz App"
        assert "abc123" in args[2]
        assert "abc123" in args[3]


def test_html_template_contains_reset_url():
    from services.email_service import _load_template

    html = _load_template("password_reset.html")
    assert "{{RESET_URL}}" in html
    assert "Redefinição de senha" in html
    assert "1 hora" in html


def test_text_template_contains_reset_url():
    from services.email_service import _load_template

    text = _load_template("password_reset.txt")
    assert "{{RESET_URL}}" in text
    assert "REDEFINIÇÃO DE SENHA" in text
    assert "1 hora" in text


def test_email_message_structure(monkeypatch):
    from services.email_service import send_email

    with patch("services.email_service.smtplib.SMTP") as mock_smtp:
        server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = server

        send_email("user@test.com", "Subject", "<p>HTML</p>", "Text body")

        msg = server.send_message.call_args[0][0]
        assert msg["Subject"] == "Subject"
        assert msg["To"] == "user@test.com"
        assert msg["From"] == "noreply@quizapp.com"
        # Multipart: first part is text/plain
        assert msg.is_multipart()
        parts = list(msg.walk())
        text_part = [p for p in parts if p.get_content_type() == "text/plain"][0]
        assert text_part.get_content().strip() == "Text body"
        html_part = [p for p in parts if p.get_content_type() == "text/html"][0]
        assert "<p>HTML</p>" in html_part.get_content()
