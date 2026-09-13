"""Tests for the notification test endpoint (issue #5)."""

import pytest
from fastapi.testclient import TestClient

import app.services.notifications as notifications
from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def test_test_endpoint_reports_disabled_channels(client, monkeypatch):
    # Both channels disabled -> endpoint still returns a structured result.
    monkeypatch.setattr(notifications.settings, "smtp_enabled", False)
    monkeypatch.setattr(notifications.settings, "webhook_enabled", False)

    resp = client.post("/api/notifications/test")
    assert resp.status_code == 200
    results = {r["channel"]: r for r in resp.json()}
    assert results["email"]["enabled"] is False
    assert results["email"]["success"] is False
    assert results["webhook"]["enabled"] is False


def test_test_endpoint_single_channel(client, monkeypatch):
    monkeypatch.setattr(notifications.settings, "smtp_enabled", False)
    resp = client.post("/api/notifications/test", params={"channel": "email"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["channel"] == "email"


def test_test_endpoint_email_success(client, monkeypatch):
    sent = {}

    def fake_deliver(subject, body, recipients):
        sent["subject"] = subject
        sent["recipients"] = recipients

    monkeypatch.setattr(notifications.settings, "smtp_enabled", True)
    monkeypatch.setattr(notifications.settings, "smtp_to", "ops@example.com")
    monkeypatch.setattr(notifications, "_deliver_email", fake_deliver)

    resp = client.post("/api/notifications/test", params={"channel": "email"})
    assert resp.status_code == 200
    result = resp.json()[0]
    assert result["success"] is True
    assert result["enabled"] is True
    assert sent["recipients"] == ["ops@example.com"]


def test_test_endpoint_email_failure_reports_error(client, monkeypatch):
    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(notifications.settings, "smtp_enabled", True)
    monkeypatch.setattr(notifications.settings, "smtp_to", "ops@example.com")
    monkeypatch.setattr(notifications, "_deliver_email", boom)

    resp = client.post("/api/notifications/test", params={"channel": "email"})
    result = resp.json()[0]
    assert result["success"] is False
    assert "connection refused" in result["detail"]
