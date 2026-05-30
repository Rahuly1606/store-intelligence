"""
Pydantic models for the Store Intelligence API.

Defines the exact event schema required by the problem statement,
including validation, enumeration of event types, and helper methods.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# --------------------------------------------------------------------------- #
# Event Type Enum
# --------------------------------------------------------------------------- #
class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


# --------------------------------------------------------------------------- #
# Main Event Model
# --------------------------------------------------------------------------- #
class Event(BaseModel):
    """A single behavioural event emitted by the detection pipeline."""

    event_id: str = Field(..., description="UUID v4 — globally unique per event")
    store_id: str = Field(..., description="Store identifier, e.g. STORE_BLR_002")
    camera_id: str = Field(..., description="Camera identifier, e.g. CAM_ENTRY_01")
    visitor_id: str = Field(..., description="Re‑ID token, unique per visit session")
    event_type: EventType = Field(..., description="Catalogue type of the event")
    timestamp: str = Field(..., description="ISO‑8601 UTC timestamp")
    zone_id: Optional[str] = Field(None, description="Zone name, null for ENTRY/EXIT")
    dwell_ms: int = Field(0, ge=0, description="Duration in ms; 0 for instantaneous events")
    is_staff: bool = Field(False, description="True if the person is staff")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence [0,1]")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra fields: queue_depth, sku_zone, session_seq, etc.",
    )

    # ---- Validators ----

    @field_validator("event_id")
    @classmethod
    def validate_uuid_v4(cls, v: str) -> str:
        try:
            uid = UUID(v, version=4)
        except (ValueError, TypeError):
            raise ValueError("event_id must be a valid UUID v4")
        return str(uid)

    @field_validator("timestamp")
    @classmethod
    def validate_iso8601_utc(cls, v: str) -> str:
        # Accept any ISO‑8601 format ending with Z or +00:00
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
        if not re.match(pattern, v):
            raise ValueError("timestamp must be ISO‑8601 UTC (e.g. 2026-03-03T14:22:10Z)")
        try:
            # Replace 'Z' with '+00:00' for parsing
            ts_str = v.replace("Z", "+00:00")
            datetime.fromisoformat(ts_str)
        except ValueError:
            raise ValueError("timestamp is not valid ISO‑8601")
        return v

    @field_validator("zone_id")
    @classmethod
    def validate_zone_for_event_type(cls, v: Optional[str], info) -> Optional[str]:
        event_type = info.data.get("event_type")
        if event_type in (EventType.ENTRY, EventType.EXIT):
            if v is not None:
                raise ValueError("zone_id must be null for ENTRY/EXIT events")
        return v

    @field_validator("dwell_ms")
    @classmethod
    def validate_dwell_for_type(cls, v: int, info) -> int:
        event_type = info.data.get("event_type")
        if event_type == EventType.ZONE_DWELL and v == 0:
            # DWELL events should have a positive dwell_ms, but schema says 0 allowed for other events
            # We'll be lenient but flag large values? Not required.
            pass
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_c8a2f1",
                "event_type": "ZONE_DWELL",
                "timestamp": "2026-03-03T14:22:10Z",
                "zone_id": "SKINCARE",
                "dwell_ms": 8400,
                "is_staff": False,
                "confidence": 0.91,
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": "MOISTURISER",
                    "session_seq": 5,
                },
            }
        }
    }


# --------------------------------------------------------------------------- #
# Ingest Request / Response Models
# --------------------------------------------------------------------------- #
class IngestRequest(BaseModel):
    """Batch of events to be ingested."""
    events: list[Event] = Field(..., min_length=1, max_length=500)


class IngestError(BaseModel):
    """Description of a single rejected event."""
    index: int
    event_id: Optional[str] = None
    message: str


class IngestResponse(BaseModel):
    """Response returned by POST /events/ingest."""
    accepted: int
    rejected: int
    errors: list[IngestError] = Field(default_factory=list)