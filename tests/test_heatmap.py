# PROMPT:
# Write pytest tests for GET /stores/{store_id}/heatmap.
# Include tests for: empty store, store with zone visits and dwell,
# normalization (0-100), data_confidence flag (false if <20 visitors).

# CHANGES MADE:
# - Used temporary DB with direct event insertion.
# - Verified normalization logic and data_confidence threshold.

import os
import tempfile

temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"

import pytest
from fastapi.testclient import TestClient

from app.database import engine, Base, SessionLocal, EventTable
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield c


def insert_events(events):
    db = SessionLocal()
    for ev in events:
        db.add(EventTable(**ev))
    db.commit()
    db.close()


def test_heatmap_empty_store(client):
    resp = client.get("/stores/STORE_BLR_002/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_confidence"] is False
    assert data["zones"] == []


def test_heatmap_with_data(client):
    # 10 visitors (under 20, so data_confidence=False)
    events = []
    for i in range(10):
        ev = {
            "event_id": f"e{i}",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": f"VIS_{i}",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:20:00Z",
            "confidence": 0.9,
        }
        events.append(ev)
        # half of them enter zone A
        if i % 2 == 0:
            events.append({
                "event_id": f"ez{i}",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_MAINFLOOR_01",
                "visitor_id": f"VIS_{i}",
                "event_type": "ZONE_ENTER",
                "timestamp": "2026-03-03T14:22:00Z",
                "zone_id": "ZONE_A",
                "confidence": 0.9,
            })
        # quarter enter zone B
        if i % 4 == 0:
            events.append({
                "event_id": f"ezb{i}",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_MAINFLOOR_01",
                "visitor_id": f"VIS_{i}",
                "event_type": "ZONE_ENTER",
                "timestamp": "2026-03-03T14:23:00Z",
                "zone_id": "ZONE_B",
                "confidence": 0.9,
            })

    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/heatmap")
    data = resp.json()
    assert data["data_confidence"] is False
    assert len(data["zones"]) == 2

    zone_a = next(z for z in data["zones"] if z["zone_id"] == "ZONE_A")
    zone_b = next(z for z in data["zones"] if z["zone_id"] == "ZONE_B")
    # Zone A has 5 visits, Zone B has 3
    assert zone_a["raw_visits"] == 5
    assert zone_b["raw_visits"] == 3
    # Normalized: A max -> 100, B -> 0
    assert zone_a["visit_frequency"] == 100.0
    assert zone_b["visit_frequency"] == 0.0


def test_heatmap_data_confidence_true(client):
    # Create 25 visitors (>=20)
    events = []
    for i in range(25):
        events.append({
            "event_id": f"e{i}",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": f"VIS_{i}",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:20:00Z",
            "confidence": 0.9,
        })
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/heatmap")
    data = resp.json()
    assert data["data_confidence"] is True