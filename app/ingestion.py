"""
Ingestion endpoint for the Store Intelligence API.

POST /events/ingest  — accepts a batch of events, validates them,
deduplicates by event_id, and returns a structured response.
"""

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import EventTable, get_db
from app.models import Event, IngestError, IngestRequest, IngestResponse

logger = logging.getLogger("ingestion")

router = APIRouter()


@router.post("/events/ingest", response_model=IngestResponse)
def ingest_events(
    body: Dict[str, List[Dict[str, Any]]],
    db: Session = Depends(get_db),
) -> IngestResponse:
    """
    Ingest a batch of up to 500 events.
    Validates each event, skips duplicates (idempotent), and returns a
    summary with per‑error details for malformed events.
    """
    accepted = 0
    rejected = 0
    errors: List[IngestError] = []

    # Validate the batch structure
    if "events" not in body:
        raise HTTPException(status_code=422, detail="Missing 'events' field")
    
    events_list = body["events"]
    
    if not isinstance(events_list, list):
        raise HTTPException(status_code=422, detail="'events' must be a list")
    
    if len(events_list) == 0:
        raise HTTPException(status_code=422, detail="'events' list cannot be empty")
    
    if len(events_list) > 500:
        raise HTTPException(status_code=422, detail="'events' list cannot exceed 500 items")

    for idx, event_dict in enumerate(events_list):
        # Validate each event individually
        try:
            event_data = Event(**event_dict)
        except ValidationError as e:
            # Extract a readable error message
            error_msg = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            errors.append(
                IngestError(
                    index=idx,
                    event_id=event_dict.get("event_id"),
                    message=f"Validation error: {error_msg}",
                )
            )
            rejected += 1
            continue
        except Exception as e:
            errors.append(
                IngestError(
                    index=idx,
                    event_id=event_dict.get("event_id"),
                    message=f"Unexpected validation error: {str(e)}",
                )
            )
            rejected += 1
            continue

        # Serialize metadata to JSON string for storage
        try:
            metadata_json = json.dumps(event_data.metadata)
        except (TypeError, ValueError) as e:
            errors.append(
                IngestError(
                    index=idx,
                    event_id=event_data.event_id,
                    message=f"Metadata serialization failed: {e}",
                )
            )
            rejected += 1
            continue

        # Build the database row
        db_event = EventTable(
            event_id=event_data.event_id,
            store_id=event_data.store_id,
            camera_id=event_data.camera_id,
            visitor_id=event_data.visitor_id,
            event_type=event_data.event_type.value,
            timestamp=event_data.timestamp,
            zone_id=event_data.zone_id,
            dwell_ms=event_data.dwell_ms,
            is_staff=event_data.is_staff,
            confidence=event_data.confidence,
            event_metadata=metadata_json,
        )

        try:
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            accepted += 1
        except IntegrityError:
            db.rollback()
            # Duplicate event_id — idempotent, count as accepted but don't re-add
            accepted += 1
            continue
        except Exception as e:
            db.rollback()
            logger.exception("Unexpected error storing event %s", event_data.event_id)
            errors.append(
                IngestError(
                    index=idx,
                    event_id=event_data.event_id,
                    message=f"Database error: {e}",
                )
            )
            rejected += 1

    return IngestResponse(
        accepted=accepted,
        rejected=rejected,
        errors=errors,
    )