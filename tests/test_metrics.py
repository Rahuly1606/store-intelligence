# PROMPT:
# Generate pytest cases for GET /stores/{store_id}/metrics.
# Cover: empty store, store with visitors but no conversions,
# store with conversion, dwell times, queue depth, abandonment rate,
# and staff exclusion.
# Use a fresh temporary database per test and insert events directly.

# CHANGES MADE:
# - Added camera_id to all test events (required by DB schema).
# - Changed conversion rate check to round(1/3, 4) to match API rounding.
# - Fixed staff exclusion test event to include camera_id.

import os
import tempfile
import json

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


def test_metrics_empty_store(client):
    resp = client.get("/stores/STORE_BLR_002/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["avg_dwell_per_zone_ms"] == {}
    assert data["queue_depth"] == 0
    assert data["abandonment_rate"] == 0.0


def test_metrics_no_purchase(client):
    events = [
        {
            "event_id": f"a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b{i:03d}",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": f"VIS_{i:03d}",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:22:10Z",
            "confidence": 0.9,
        }
        for i in range(5)
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/metrics")
    data = resp.json()
    assert data["unique_visitors"] == 5
    assert data["conversion_rate"] == 0.0


def test_metrics_with_conversion_and_dwell(client):
    events = [
        # Visitor 1: entry, dwell, billing join
        {"event_id": "e1", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_1", "event_type": "ENTRY", "timestamp": "2026-03-03T14:20:00Z", "confidence": 0.9},
        {"event_id": "e2", "store_id": "STORE_BLR_002", "camera_id": "CAM_MAINFLOOR_01",
         "visitor_id": "VIS_1", "event_type": "ZONE_DWELL", "timestamp": "2026-03-03T14:22:00Z",
         "zone_id": "SKINCARE", "dwell_ms": 120000, "confidence": 0.9},
        {"event_id": "e3", "store_id": "STORE_BLR_002", "camera_id": "CAM_BILLING_01",
         "visitor_id": "VIS_1", "event_type": "BILLING_QUEUE_JOIN", "timestamp": "2026-03-03T14:25:00Z",
         "confidence": 0.9, "event_metadata": json.dumps({"queue_depth": 3})},
        # Visitor 2: entry, abandon
        {"event_id": "e4", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_2", "event_type": "ENTRY", "timestamp": "2026-03-03T14:21:00Z", "confidence": 0.9},
        {"event_id": "e5", "store_id": "STORE_BLR_002", "camera_id": "CAM_BILLING_01",
         "visitor_id": "VIS_2", "event_type": "BILLING_QUEUE_ABANDON", "timestamp": "2026-03-03T14:26:00Z",
         "confidence": 0.9},
        # Visitor 3: entry only
        {"event_id": "e6", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_3", "event_type": "ENTRY", "timestamp": "2026-03-03T14:22:00Z", "confidence": 0.9},
        # Visitor 4: staff (excluded)
        {"event_id": "e7", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_STAFF", "event_type": "ENTRY", "timestamp": "2026-03-03T14:23:00Z", "confidence": 0.9,
         "is_staff": True},
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/metrics")
    data = resp.json()
    assert data["unique_visitors"] == 3  # VIS_1, VIS_2, VIS_3
    # Conversion rate: 1 converted (VIS_1) out of 3 => 0.3333
    assert data["conversion_rate"] == round(1/3, 4)
    assert data["avg_dwell_per_zone_ms"] == {"SKINCARE": 120000}
    assert data["queue_depth"] == 3
    # Abandonment: joined=1, abandoned=1 -> rate=1.0
    assert data["abandonment_rate"] == 1.0


def test_metrics_staff_exclusion(client):
    events = [
        {"event_id": "s1", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_STAFF", "event_type": "ENTRY", "timestamp": "2026-03-03T14:22:10Z",
         "confidence": 0.9, "is_staff": True},
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/metrics")
    data = resp.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0