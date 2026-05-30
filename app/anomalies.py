"""
Anomaly detection endpoint for the Store Intelligence API.

GET /stores/{store_id}/anomalies
Returns active anomalies: queue spike, conversion drop, dead zones.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import EventTable, get_db

router = APIRouter()


@router.get("/stores/{store_id}/anomalies")
def store_anomalies(store_id: str, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    anomalies: List[dict] = []

    # ── 1. Queue Spike ─────────────────────────────────────────────
    # Current queue depth from latest BILLING_QUEUE_JOIN
    current_queue = 0
    latest = (
        db.query(EventTable.event_metadata)
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "BILLING_QUEUE_JOIN",
        )
        .order_by(EventTable.timestamp.desc())
        .first()
    )
    if latest:
        try:
            current_queue = json.loads(latest[0]).get("queue_depth", 0)
        except (json.JSONDecodeError, TypeError):
            pass

    # Average queue depth over the past 7 days (excluding today)
    seven_days_ago = today_start - timedelta(days=7)
    past_rows = (
        db.query(EventTable.event_metadata)
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "BILLING_QUEUE_JOIN",
            EventTable.timestamp >= seven_days_ago.isoformat() + "Z",
            EventTable.timestamp < today_start.isoformat() + "Z",
        )
        .all()
    )
    past_depths = []
    for row in past_rows:
        try:
            past_depths.append(json.loads(row[0]).get("queue_depth", 0))
        except (json.JSONDecodeError, TypeError):
            pass

    if past_depths and len(past_depths) >= 3:
        avg_past_queue = sum(past_depths) / len(past_depths)
        if current_queue > avg_past_queue + 5:
            anomalies.append({
                "type": "BILLING_QUEUE_SPIKE",
                "severity": "CRITICAL" if current_queue > avg_past_queue * 2 else "WARN",
                "description": f"Queue depth {current_queue} vs 7‑day avg {avg_past_queue:.1f}",
                "suggested_action": "Open additional checkout counters or redirect staff.",
            })

    # ── 2. Conversion Drop ─────────────────────────────────────────
    # Today's conversion rate
    today_unique = (
        db.query(func.count(func.distinct(EventTable.visitor_id)))
        .filter(
            EventTable.store_id == store_id,
            EventTable.is_staff == False,
            EventTable.timestamp >= today_start.isoformat() + "Z",
        )
        .scalar()
    ) or 0
    today_converted = (
        db.query(func.count(func.distinct(EventTable.visitor_id)))
        .filter(
            EventTable.store_id == store_id,
            EventTable.is_staff == False,
            EventTable.event_type == "BILLING_QUEUE_JOIN",
            EventTable.timestamp >= today_start.isoformat() + "Z",
        )
        .scalar()
    ) or 0
    today_rate = (today_converted / today_unique) if today_unique > 0 else 0.0

    # 7‑day average conversion rate
    past_rates = []
    for i in range(1, 7):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_unique = (
            db.query(func.count(func.distinct(EventTable.visitor_id)))
            .filter(
                EventTable.store_id == store_id,
                EventTable.is_staff == False,
                EventTable.timestamp >= day_start.isoformat() + "Z",
                EventTable.timestamp < day_end.isoformat() + "Z",
            )
            .scalar()
        ) or 0
        day_converted = (
            db.query(func.count(func.distinct(EventTable.visitor_id)))
            .filter(
                EventTable.store_id == store_id,
                EventTable.is_staff == False,
                EventTable.event_type == "BILLING_QUEUE_JOIN",
                EventTable.timestamp >= day_start.isoformat() + "Z",
                EventTable.timestamp < day_end.isoformat() + "Z",
            )
            .scalar()
        ) or 0
        if day_unique > 0:
            past_rates.append(day_converted / day_unique)

    if past_rates:
        avg_past_rate = sum(past_rates) / len(past_rates)
        if avg_past_rate > 0 and today_rate < avg_past_rate * 0.8:
            drop_pct = (avg_past_rate - today_rate) / avg_past_rate * 100
            anomalies.append({
                "type": "CONVERSION_DROP",
                "severity": "CRITICAL" if drop_pct > 50 else "WARN",
                "description": f"Today's conversion {today_rate:.2%} vs 7‑day avg {avg_past_rate:.2%}",
                "suggested_action": "Review staffing, promotions, or queue management.",
            })

    # ── 3. Dead Zone ───────────────────────────────────────────────
    half_hour_ago = now - timedelta(minutes=30)
    active_zones = {
        row[0]
        for row in db.query(EventTable.zone_id)
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "ZONE_ENTER",
            EventTable.is_staff == False,
            EventTable.timestamp >= half_hour_ago.isoformat() + "Z",
        )
        .distinct()
        .all()
        if row[0]
    }
    all_zones = {
        row[0]
        for row in db.query(EventTable.zone_id)
        .filter(
            EventTable.store_id == store_id,
            EventTable.zone_id.isnot(None),
        )
        .distinct()
        .all()
        if row[0]
    }
    for zone in all_zones - active_zones:
        anomalies.append({
            "type": "DEAD_ZONE",
            "severity": "INFO",
            "description": f"Zone '{zone}' has had no visitors in the last 30 minutes.",
            "suggested_action": "Check zone accessibility or refresh product displays.",
        })

    return {
        "store_id": store_id,
        "anomalies": anomalies,
    }