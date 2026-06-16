from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_FROM,
    SMTP_USE_TLS,
    SMTP_TIMEOUT,
)

logger = logging.getLogger("quizapp.email")

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _build_email(to_email: str, subject: str, html_body: str, text_body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    if not SMTP_HOST:
        logger.warning("SMTP_HOST not configured — skipping email to %s", to_email)
        return False

    msg = _build_email(to_email, subject, html_body, text_body)
    start = time.time()

    try:
        if SMTP_USE_TLS:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                server.starttls()
                if SMTP_USERNAME:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                if SMTP_USERNAME:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)

        elapsed = time.time() - start
        logger.info("Email sent to %s (%.2fs)", to_email, elapsed)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", SMTP_USERNAME)
        return False
    except smtplib.SMTPConnectError:
        logger.error("SMTP connection failed — host=%s port=%s", SMTP_HOST, SMTP_PORT)
        return False
    except smtplib.SMTPSenderRefused:
        logger.error("SMTP sender refused — from=%s", SMTP_FROM)
        return False
    except smtplib.SMTPRecipientsRefused:
        logger.error("SMTP recipient refused — to=%s", to_email)
        return False
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("SMTP error sending to %s: %s", to_email, exc)
        return False


def _load_template(name: str) -> str:
    path = _TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def send_password_reset_email(email: str, reset_url: str) -> bool:
    subject = "Redefinição de senha — Quiz App"
    html_body = _load_template("password_reset.html").replace("{{RESET_URL}}", reset_url)
    text_body = _load_template("password_reset.txt").replace("{{RESET_URL}}", reset_url)
    return send_email(email, subject, html_body, text_body)
