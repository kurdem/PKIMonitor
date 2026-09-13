"""Notification channels: SMTP email and Slack/Teams/generic webhooks."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChannelTestResult:
    """Outcome of a single-channel notification test."""

    channel: str      # "email" | "webhook"
    enabled: bool     # is the channel configured/enabled at all?
    success: bool     # did the test message go out?
    detail: str       # human-readable status / error message


# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------
def _deliver_email(subject: str, body: str, recipients: list[str]) -> None:
    """Send an email, raising on any failure (used by both send & test)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_email(subject: str, body: str, to: list[str] | None = None) -> bool:
    if not settings.smtp_enabled:
        logger.debug("SMTP disabled; skipping email '%s'", subject)
        return False

    recipients = to or settings.smtp_to_list
    if not recipients:
        logger.warning("No SMTP recipients configured; skipping email")
        return False

    try:
        _deliver_email(subject, body, recipients)
        logger.info("Sent alert email '%s' to %s", subject, recipients)
        return True
    except Exception:
        logger.exception("Failed to send alert email '%s'", subject)
        return False


# --------------------------------------------------------------------------
# Webhook
# --------------------------------------------------------------------------
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


def _deliver_webhook(title: str, text: str) -> int:
    """POST to the configured webhook, raising on failure. Returns HTTP status."""
    resp = httpx.post(
        settings.webhook_url,
        json=_build_webhook_payload(title, text),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.status_code


def send_webhook(title: str, text: str) -> bool:
    if not settings.webhook_enabled or not settings.webhook_url:
        return False
    try:
        _deliver_webhook(title, text)
        logger.info("Sent webhook alert '%s'", title)
        return True
    except Exception:
        logger.exception("Failed to send webhook alert '%s'", title)
        return False


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Test helpers (feature: notification test button / endpoint)
# --------------------------------------------------------------------------
_TEST_SUBJECT = "[PKIMonitor] Testbenachrichtigung"
_TEST_BODY = (
    "Dies ist eine Testbenachrichtigung von PKIMonitor.\n"
    "Wenn du diese Nachricht erhältst, ist der Versand korrekt konfiguriert."
)


def test_email() -> ChannelTestResult:
    if not settings.smtp_enabled:
        return ChannelTestResult(
            "email", False, False,
            "SMTP ist deaktiviert (SMTP_ENABLED=false).",
        )
    recipients = settings.smtp_to_list
    if not recipients:
        return ChannelTestResult(
            "email", True, False,
            "Keine Empfänger konfiguriert (SMTP_TO ist leer).",
        )
    try:
        _deliver_email(_TEST_SUBJECT, _TEST_BODY, recipients)
        return ChannelTestResult(
            "email", True, True,
            f"Test-E-Mail an {', '.join(recipients)} gesendet.",
        )
    except Exception as exc:
        logger.exception("Test email failed")
        return ChannelTestResult("email", True, False, f"Fehler: {exc}")


def test_webhook() -> ChannelTestResult:
    if not settings.webhook_enabled or not settings.webhook_url:
        return ChannelTestResult(
            "webhook", False, False,
            "Webhook ist deaktiviert (WEBHOOK_ENABLED=false oder WEBHOOK_URL leer).",
        )
    try:
        status_code = _deliver_webhook(_TEST_SUBJECT, _TEST_BODY)
        return ChannelTestResult(
            "webhook", True, True,
            f"Test-Webhook an '{settings.webhook_type}' gesendet (HTTP {status_code}).",
        )
    except Exception as exc:
        logger.exception("Test webhook failed")
        return ChannelTestResult("webhook", True, False, f"Fehler: {exc}")


def test_channels(channel: str | None = None) -> list[ChannelTestResult]:
    """Run a notification test for the requested channel (or all channels)."""
    if channel == "email":
        return [test_email()]
    if channel == "webhook":
        return [test_webhook()]
    return [test_email(), test_webhook()]
