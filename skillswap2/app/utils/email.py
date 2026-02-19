from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def is_email_enabled() -> bool:
    """Return True when email notifications are configured and enabled."""
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return False
    if not settings.SMTP_SERVER:
        return False
    if not settings.EMAIL_FROM:
        return False
    return True


def send_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """
    Send an email using SMTP settings.

    Returns True on success. Failures are logged and False is returned.
    """
    if not is_email_enabled():
        return False

    smtp_server = settings.SMTP_SERVER
    from_email = settings.EMAIL_FROM
    if not smtp_server or not from_email:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    username = settings.SMTP_USERNAME or from_email
    password = settings.EMAIL_PASSWORD or ""

    try:
        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(
                smtp_server,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
        else:
            server = smtplib.SMTP(
                smtp_server,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )

        with server:
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                server.starttls()
            if password:
                server.login(username, password)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.warning("Email send failed for '%s': %s", to_email, exc)
        return False
