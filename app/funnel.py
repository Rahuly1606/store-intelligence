"""
Funnel endpoint for the Store Intelligence API.

GET /stores/{store_id}/funnel
Returns the conversion funnel with counts and drop‑off percentages
(Entry → Zone Visit → Billing Queue → Purchase).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import EventTable, get_db

router = APIRouter()


@router.get("/stores/{store_id}/funnel")
def store_funnel(store_id: str, db: Session = Depends(get_db)):
    # ── Entry stage: unique visitors with at least one ENTRY ──────
    entry_count = (
        db.query(func.count(func.distinct(EventTable.visitor_id)))
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "ENTRY",
            EventTable.is_staff == False,
        )
        .scalar()
    ) or 0

    # ── Zone Visit stage: visitors with at least one ZONE_ENTER ──
    zone_visit_count = (
        db.query(func.count(func.distinct(EventTable.visitor_id)))
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "ZONE_ENTER",
            EventTable.is_staff == False,
        )
        .scalar()
    ) or 0

    # ── Billing Queue stage: visitors with BILLING_QUEUE_JOIN ──
    billing_count = (
        db.query(func.count(func.distinct(EventTable.visitor_id)))
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "BILLING_QUEUE_JOIN",
            EventTable.is_staff == False,
        )
        .scalar()
    ) or 0

    # ── Purchase stage: same as billing for now ──────────────────
    # (Will be refined once POS correlation marks conversions)
    purchase_count = billing_count

    # ── Drop‑off percentages ─────────────────────────────────────
    def dropoff(prev, curr):
        if prev == 0:
            return 0.0
        return round(((prev - curr) / prev) * 100, 2)

    return {
        "store_id": store_id,
        "funnel": {
            "entry": entry_count,
            "zone_visit": zone_visit_count,
            "billing_queue": billing_count,
            "purchase": purchase_count,
        },
        "dropoff_pct": {
            "entry_to_zone": dropoff(entry_count, zone_visit_count),
            "zone_to_billing": dropoff(zone_visit_count, billing_count),
            "billing_to_purchase": dropoff(billing_count, purchase_count),
        },
    }