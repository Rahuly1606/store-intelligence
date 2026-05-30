# PROMPT:
# Generate pytest tests for GET /stores/{store_id}/funnel.
# Cover: empty store, visitors at various stages (entry only, entry+zone, entry+zone+billing),
# staff exclusion, and re-entry not double-counted.
# Ensure drop-off calculations are correct.

# CHANGES MADE:
# - Added camera_id to all events for DB constraint.
# - Verified purchase count equals billing count (POS correlation not yet implemented).
# - Checked drop-off percentages with expected values.
# - Ensured staff events are excluded.

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


def test_funnel_empty_store(client):
    resp = client.get("/stores/STORE_BLR_002/funnel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["funnel"] == {"entry": 0, "zone_visit": 0, "billing_queue": 0, "purchase": 0}
    assert data["dropoff_pct"] == {"entry_to_zone": 0.0, "zone_to_billing": 0.0, "billing_to_purchase": 0.0}


def test_funnel_entry_only(client):
    events = [
        {"event_id": f"e{i}", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": f"VIS_{i}", "event_type": "ENTRY", "timestamp": "2026-03-03T14:20:00Z", "confidence": 0.9}
        for i in range(3)
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/funnel")
    data = resp.json()
    assert data["funnel"]["entry"] == 3
    assert data["funnel"]["zone_visit"] == 0
    assert data["funnel"]["billing_queue"] == 0
    assert data["funnel"]["purchase"] == 0
    # All dropped off at entry->zone
    assert data["dropoff_pct"]["entry_to_zone"] == 100.0


def test_funnel_full_conversion(client):
    # 2 visitors go through all stages, 1 visitor only entry
    events = [
        # Visitor 1: full path
        {"event_id": "e1", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_1", "event_type": "ENTRY", "timestamp": "2026-03-03T14:20:00Z", "confidence": 0.9},
        {"event_id": "e2", "store_id": "STORE_BLR_002", "camera_id": "CAM_MAINFLOOR_01",
         "visitor_id": "VIS_1", "event_type": "ZONE_ENTER", "timestamp": "2026-03-03T14:22:00Z",
         "zone_id": "SKINCARE", "confidence": 0.9},
        {"event_id": "e3", "store_id": "STORE_BLR_002", "camera_id": "CAM_BILLING_01",
         "visitor_id": "VIS_1", "event_type": "BILLING_QUEUE_JOIN", "timestamp": "2026-03-03T14:25:00Z",
         "confidence": 0.9},
        # Visitor 2: full path
        {"event_id": "e4", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_2", "event_type": "ENTRY", "timestamp": "2026-03-03T14:21:00Z", "confidence": 0.9},
        {"event_id": "e5", "store_id": "STORE_BLR_002", "camera_id": "CAM_MAINFLOOR_01",
         "visitor_id": "VIS_2", "event_type": "ZONE_ENTER", "timestamp": "2026-03-03T14:23:00Z",
         "zone_id": "SKINCARE", "confidence": 0.9},
        {"event_id": "e6", "store_id": "STORE_BLR_002", "camera_id": "CAM_BILLING_01",
         "visitor_id": "VIS_2", "event_type": "BILLING_QUEUE_JOIN", "timestamp": "2026-03-03T14:26:00Z",
         "confidence": 0.9},
        # Visitor 3: only entry
        {"event_id": "e7", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_3", "event_type": "ENTRY", "timestamp": "2026-03-03T14:22:00Z", "confidence": 0.9},
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/funnel")
    data = resp.json()
    assert data["funnel"]["entry"] == 3
    assert data["funnel"]["zone_visit"] == 2
    assert data["funnel"]["billing_queue"] == 2
    assert data["funnel"]["purchase"] == 2
    # Drop-off: entry->zone = (3-2)/3*100 = 33.33
    assert data["dropoff_pct"]["entry_to_zone"] == round((3-2)/3*100, 2)
    # Zone->billing = 0%
    assert data["dropoff_pct"]["zone_to_billing"] == 0.0
    assert data["dropoff_pct"]["billing_to_purchase"] == 0.0


def test_funnel_staff_excluded(client):
    events = [
        {"event_id": "e1", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_STAFF", "event_type": "ENTRY", "timestamp": "2026-03-03T14:20:00Z",
         "confidence": 0.9, "is_staff": True},
        {"event_id": "e2", "store_id": "STORE_BLR_002", "camera_id": "CAM_MAINFLOOR_01",
         "visitor_id": "VIS_STAFF", "event_type": "ZONE_ENTER", "timestamp": "2026-03-03T14:22:00Z",
         "zone_id": "SKINCARE", "confidence": 0.9, "is_staff": True},
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/funnel")
    data = resp.json()
    # Staff excluded: all zeros
    assert data["funnel"]["entry"] == 0
    assert data["funnel"]["zone_visit"] == 0


def test_funnel_no_double_count_reentry(client):
    # Same visitor enters twice: should count only once
    events = [
        {"event_id": "e1", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_1", "event_type": "ENTRY", "timestamp": "2026-03-03T14:20:00Z", "confidence": 0.9},
        {"event_id": "e2", "store_id": "STORE_BLR_002", "camera_id": "CAM_ENTRY_01",
         "visitor_id": "VIS_1", "event_type": "REENTRY", "timestamp": "2026-03-03T15:20:00Z", "confidence": 0.9},
    ]
    insert_events(events)
    resp = client.get("/stores/STORE_BLR_002/funnel")
    data = resp.json()
    # Only one unique visitor counted
    assert data["funnel"]["entry"] == 1