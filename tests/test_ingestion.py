# PROMPT:
# Generate a suite of pytest tests for the POST /events/ingest endpoint.
# Include tests for: valid single event, idempotency (duplicate event_id),
# partial success, invalid UUID, missing fields, batch limits, empty batch.
# Use fastapi.testclient.TestClient, override the DATABASE_URL with a temporary
# file‑based SQLite database, and ensure tables are created via lifespan.

# CHANGES MADE:
# - Used a temporary file for SQLite instead of :memory: to avoid connection
#   isolation issues (tables created in lifespan are visible to session).
# - Recreate tables before each test to ensure isolation.
# - Fixed the client fixture to properly trigger lifespan and table creation.

import os
import tempfile

# ---- Use a temporary file‑based SQLite database ----
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"

import pytest
from fastapi.testclient import TestClient

from app.database import engine, Base
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client with fresh database tables per test."""
    # Use the app in a lifespan context, which calls init_db()
    with TestClient(app) as c:
        # Ensure a clean slate for this test
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield c


VALID_EVENT = {
    "event_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "store_id": "STORE_BLR_002",
    "camera_id": "CAM_ENTRY_01",
    "visitor_id": "VIS_test1",
    "event_type": "ENTRY",
    "timestamp": "2026-03-03T14:22:10Z",
    "confidence": 0.95,
}


def test_ingest_single_valid_event(client):
    payload = {"events": [VALID_EVENT]}
    resp = client.post("/events/ingest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 0


def test_ingest_idempotency(client):
    payload = {"events": [VALID_EVENT]}
    r1 = client.post("/events/ingest", json=payload)
    assert r1.json()["accepted"] == 1
    r2 = client.post("/events/ingest", json=payload)
    assert r2.json()["accepted"] == 1


def test_ingest_partial_success(client):
    bad = VALID_EVENT.copy()
    del bad["event_id"]
    payload = {"events": [VALID_EVENT, bad]}
    resp = client.post("/events/ingest", json=payload)
    data = resp.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 1
    assert data["errors"][0]["index"] == 1


def test_ingest_invalid_uuid(client):
    bad = VALID_EVENT.copy()
    bad["event_id"] = "not-a-uuid"
    resp = client.post("/events/ingest", json={"events": [bad]})
    data = resp.json()
    assert data["accepted"] == 0
    assert "event_id" in data["errors"][0]["message"].lower()


def test_ingest_missing_required_field(client):
    bad = VALID_EVENT.copy()
    del bad["store_id"]
    resp = client.post("/events/ingest", json={"events": [bad]})
    assert resp.json()["accepted"] == 0


def test_ingest_batch_too_large(client):
    events = [VALID_EVENT.copy() for _ in range(501)]
    for i, ev in enumerate(events):
        ev["event_id"] = f"a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b{i:05d}"
    resp = client.post("/events/ingest", json={"events": events})
    assert resp.status_code == 422


def test_ingest_empty_batch(client):
    resp = client.post("/events/ingest", json={"events": []})
    assert resp.status_code == 422