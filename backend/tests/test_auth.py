"""Regression tests for the optional API-key auth.

Guards against the bug where an empty `API_KEY` env value ("") was treated as
"auth enabled with an empty key", causing every write request to return 401.
"""

import pytest
from fastapi.testclient import TestClient

import app.config as config
from app.config import Settings
from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize("raw,expected", [("", None), ("   ", None), ("secret", "secret")])
def test_blank_api_key_becomes_none(raw, expected):
    assert Settings(api_key=raw).api_key == expected


def test_writes_allowed_when_key_blank(client, monkeypatch):
    # Empty key => auth disabled => POST succeeds without a header.
    monkeypatch.setattr(config.settings, "api_key", None)
    resp = client.post("/api/certificates", json={"name": "NoAuth"})
    assert resp.status_code == 201


def test_writes_require_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(config.settings, "api_key", "secret")

    # Read endpoints stay open.
    assert client.get("/api/certificates").status_code == 200

    # Missing / wrong key is rejected.
    assert client.post("/api/certificates", json={"name": "x"}).status_code == 401
    assert client.post(
        "/api/certificates", json={"name": "x"}, headers={"X-API-Key": "nope"}
    ).status_code == 401

    # Correct key is accepted.
    assert client.post(
        "/api/certificates", json={"name": "x"}, headers={"X-API-Key": "secret"}
    ).status_code == 201
