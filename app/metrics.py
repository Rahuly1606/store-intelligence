"""
Metrics endpoint for the Store Intelligence API.

GET /stores/{store_id}/metrics — returns aggregated metrics for a store.
"""

import json
from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import EventTable, get_db

router = APIRouter()


@router.get("/stores/{store_id}/metrics")
def get_store_metrics(store_id: str, db: Session = Depends(get_db)) -> Dict:
    """
    Return aggregated metrics for a given store.
    Excludes staff events from all calculations.
    """
    # Get all non-staff events for this store
    events = db.query(EventTable).filter(
        EventTable.store_id == store_id,
        EventTable.is_staff == False
    ).all()

    if not events:
        return {
            "unique_visitors": 0,
            "conversion_rate": 0.0,
            "avg_dwell_per_zone_ms": {},
            "queue_depth": 0,
            "abandonment_rate": 0.0,
        }

    # Unique visitors
    unique_visitors = len(set(e.visitor_id for e in events))

    # Conversion rate: visitors who joined billing queue / total visitors
    visitors_who_joined = set(
        e.visitor_id for e in events if e.event_type == "BILLING_QUEUE_JOIN"
    )
    conversion_rate = round(len(visitors_who_joined) / unique_visitors, 4) if unique_visitors > 0 else 0.0

    # Average dwell time per zone
    zone_dwells = {}
    for e in events:
        if e.event_type == "ZONE_DWELL" and e.zone_id:
            if e.zone_id not in zone_dwells:
                zone_dwells[e.zone_id] = []
            zone_dwells[e.zone_id].append(e.dwell_ms)
    
    avg_dwell_per_zone_ms = {
        zone: int(sum(dwells) / len(dwells))
        for zone, dwells in zone_dwells.items()
    }

    # Queue depth: max queue_depth from metadata
    queue_depth = 0
    for e in events:
        if e.event_type == "BILLING_QUEUE_JOIN" and e.event_metadata:
            try:
                metadata = json.loads(e.event_metadata)
                depth = metadata.get("queue_depth", 0)
                queue_depth = max(queue_depth, depth)
            except (json.JSONDecodeError, TypeError):
                pass

    # Abandonment rate: abandoned / joined (not including abandoned in denominator)
    joined_count = sum(1 for e in events if e.event_type == "BILLING_QUEUE_JOIN")
    abandoned_count = sum(1 for e in events if e.event_type == "BILLING_QUEUE_ABANDON")
    abandonment_rate = round(abandoned_count / joined_count, 4) if joined_count > 0 else 0.0

    return {
        "unique_visitors": unique_visitors,
        "conversion_rate": conversion_rate,
        "avg_dwell_per_zone_ms": avg_dwell_per_zone_ms,
        "queue_depth": queue_depth,
        "abandonment_rate": abandonment_rate,
    }
