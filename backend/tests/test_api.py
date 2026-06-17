import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    # Fresh schema per test for isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_certificate_crud(client):
    payload = {
        "name": "Test Cert",
        "common_name": "test.example.com",
        "issuer": "Test CA",
        "expiration_date": "2020-01-01T00:00:00Z",
        "environment": "test",
    }
    resp = client.post("/api/certificates", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "expired"  # date is in the past
    cert_id = body["id"]

    resp = client.get("/api/certificates")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.put(f"/api/certificates/{cert_id}", json={"location": "DC1"})
    assert resp.status_code == 200
    assert resp.json()["location"] == "DC1"

    resp = client.delete(f"/api/certificates/{cert_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/certificates/{cert_id}")
    assert resp.status_code == 404


def test_certificate_status_filter(client):
    client.post("/api/certificates", json={
        "name": "Expired", "expiration_date": "2000-01-01T00:00:00Z",
    })
    resp = client.get("/api/certificates", params={"status": "expired"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    resp = client.get("/api/certificates", params={"status": "ok"})
    assert resp.json() == []


def test_dashboard_counts(client):
    client.post("/api/certificates", json={
        "name": "Expired", "expiration_date": "2000-01-01T00:00:00Z",
    })
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["expired"] == 1


def test_monitor_create_parses_host(client):
    resp = client.post("/api/monitors", json={"url": "https://example.com:8443"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["hostname"] == "example.com"
    assert body["port"] == 8443
