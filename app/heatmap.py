"""
Heatmap endpoint for the Store Intelligence API.

GET /stores/{store_id}/heatmap
Returns zone visit frequency and average dwell, normalized 0–100,
with a data_confidence flag if < 20 sessions.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import EventTable, get_db

router = APIRouter()


@router.get("/stores/{store_id}/heatmap")
def store_heatmap(store_id: str, db: Session = Depends(get_db)):
    # ── Total unique visitors (sessions) for data confidence ──────
    total_visitors = (
        db.query(func.count(func.distinct(EventTable.visitor_id)))
        .filter(
            EventTable.store_id == store_id,
            EventTable.is_staff == False,
            EventTable.event_type == "ENTRY",
        )
        .scalar()
    ) or 0

    data_confidence = total_visitors >= 20

    # ── Zone visit frequency (distinct visitors per zone) ─────────
    zone_freq = (
        db.query(
            EventTable.zone_id,
            func.count(func.distinct(EventTable.visitor_id)).label("visits"),
        )
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "ZONE_ENTER",
            EventTable.is_staff == False,
            EventTable.zone_id.isnot(None),
        )
        .group_by(EventTable.zone_id)
        .all()
    )

    # ── Average dwell per zone ─────────────────────────────────────
    zone_dwell = (
        db.query(
            EventTable.zone_id,
            func.avg(EventTable.dwell_ms).label("avg_dwell"),
        )
        .filter(
            EventTable.store_id == store_id,
            EventTable.event_type == "ZONE_DWELL",
            EventTable.is_staff == False,
            EventTable.zone_id.isnot(None),
        )
        .group_by(EventTable.zone_id)
        .all()
    )

    # Convert to dicts
    freq_dict = {zone: visits for zone, visits in zone_freq}
    dwell_dict = {zone: int(avg) for zone, avg in zone_dwell if avg is not None}

    # ── Normalization ──────────────────────────────────────────────
    def normalize(values: dict) -> dict:
        if not values:
            return {}
        vlist = list(values.values())
        vmin, vmax = min(vlist), max(vlist)
        if vmin == vmax:
            return {k: 100.0 for k in values}
        return {
            k: round((v - vmin) / (vmax - vmin) * 100, 2)
            for k, v in values.items()
        }

    return {
        "store_id": store_id,
        "data_confidence": data_confidence,
        "zones": [
            {
                "zone_id": zone,
                "visit_frequency": normalize(freq_dict).get(zone, 0.0),
                "avg_dwell": normalize(dwell_dict).get(zone, 0.0),
                "raw_visits": freq_dict.get(zone, 0),
                "raw_dwell_ms": dwell_dict.get(zone, 0),
            }
            for zone in set(list(freq_dict.keys()) + list(dwell_dict.keys()))
        ],
    }