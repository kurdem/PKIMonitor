"""Notification channels: SMTP email and Slack/Teams/generic webhooks."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def send_email(subject: str, body: str, to: list[str] | None = None) -> bool:
    if not settings.smtp_enabled:
        logger.debug("SMTP disabled; skipping email '%s'", subject)
        return False

    recipients = to or settings.smtp_to_list
    if not recipients:
        logger.warning("No SMTP recipients configured; skipping email")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Sent alert email '%s' to %s", subject, recipients)
        return True
    except Exception:
        logger.exception("Failed to send alert email '%s'", subject)
        return False


def _build_webhook_payload(title: str, text: str) -> dict:
    wtype = (settings.webhook_type or "generic").lower()
    if wtype == "slack":
        return {"text": f"*{title}*\n{text}"}
    if wtype == "teams":
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": title,
            "themeColor": "D70000",
            "title": title,
            "text": text.replace("\n", "  \n"),
        }
    return {"title": title, "text": text}


def send_webhook(title: str, text: str) -> bool:
    if not settings.webhook_enabled or not settings.webhook_url:
        return False
    try:
        resp = httpx.post(
            settings.webhook_url,
            json=_build_webhook_payload(title, text),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Sent webhook alert '%s'", title)
        return True
    except Exception:
        logger.exception("Failed to send webhook alert '%s'", title)
        return False


def notify(subject: str, body: str) -> list[str]:
    """Dispatch to all enabled channels; return the list that succeeded."""
    channels: list[str] = []
    if send_email(subject, body):
        channels.append("email")
    if send_webhook(subject, body):
        channels.append("webhook")
    if not channels:
        # Always leave a trace even when no channel is configured.
        logger.info("[ALERT] %s\n%s", subject, body)
    return channels
