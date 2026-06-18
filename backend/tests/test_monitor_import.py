"""Tests for immediate-check on create and the bulk monitor import."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.routers.monitors as monitors_router
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Certificate


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _fake_check(expiry_days=40):
    """Build a fake run_monitor_check that simulates a successful TLS check."""
    def _impl(monitor, db):
        cert = monitor.certificate
        if cert is None:
            cert = Certificate(name=monitor.hostname, common_name=monitor.hostname, source="url")
            db.add(cert)
            db.flush()
            monitor.certificate_id = cert.id
        cert.common_name = monitor.hostname
        cert.expiration_date = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        monitor.last_checked = datetime.now(timezone.utc)
        monitor.last_success = True
        monitor.last_error = None
        db.commit()
        db.refresh(monitor)
    return _impl


def test_create_without_check(client):
    resp = client.post("/api/monitors?check=false", json={"url": "https://h.example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["hostname"] == "h.example.com"
    assert body["last_checked"] is None  # no immediate check ran


def test_create_with_check_populates_certificate(client, monkeypatch):
    monkeypatch.setattr(monitors_router, "run_monitor_check", _fake_check())
    resp = client.post("/api/monitors", json={"url": "https://h.example.com", "environment": "prod"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["certificate_id"] is not None
    assert body["last_success"] is True

    # The discovered certificate now carries an expiry date and our environment.
    certs = client.get("/api/certificates").json()
    assert len(certs) == 1
    assert certs[0]["environment"] == "prod"
    assert certs[0]["expiration_date"] is not None
    assert certs[0]["days_remaining"] >= 38


def test_bulk_import_idempotent(client):
    payload = {"urls": ["https://a.example.com", "b.example.com:8443"], "check": False}
    r1 = client.post("/api/monitors/import", json=payload)
    assert r1.status_code == 200
    data = r1.json()
    assert data["total"] == 2
    assert data["created"] == 2
    assert data["reused"] == 0

    # Re-running the same import reuses the existing monitors.
    r2 = client.post("/api/monitors/import", json=payload)
    data2 = r2.json()
    assert data2["created"] == 0
    assert data2["reused"] == 2

    assert len(client.get("/api/monitors").json()) == 2


def test_bulk_import_with_check_reports_expiry(client, monkeypatch):
    monkeypatch.setattr(monitors_router, "run_monitor_check", _fake_check(expiry_days=25))
    payload = {
        "monitors": [{"url": "https://a.example.com", "environment": "test"}],
        "check": True,
    }
    resp = client.post("/api/monitors/import", json=payload)
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["created"] is True
    assert item["checked"] is True
    assert item["success"] is True
    assert item["expiration_date"] is not None
    assert item["days_remaining"] <= 25

    # Environment from the item was applied to the discovered certificate.
    cert = client.get("/api/certificates").json()[0]
    assert cert["environment"] == "test"
    assert cert["status"] == "critical"  # < 30 days
