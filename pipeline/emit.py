"""
Event emitter for the detection pipeline.

Creates structured events conforming to the required schema and writes them
to a JSONL file.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("emit")


class EventEmitter:
    """Handles creation and line‑by‑line writing of structured events."""

    def __init__(self, output_path: Path, store_id: str) -> None:
        self.output_path = output_path
        self.store_id = store_id
        self.file = open(output_path, "a", encoding="utf-8")

    def _make_event(
        self,
        event_type: str,
        camera_id: str,
        visitor_id: str,
        timestamp: datetime,
        zone_id: Optional[str] = None,
        dwell_ms: int = 0,
        is_staff: bool = False,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a complete event dictionary."""
        event = {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": round(confidence, 4),
            "metadata": metadata or {},
        }
        return event

    def emit(self, event: Dict[str, Any]) -> None:
        """Write a single event as a JSON line and flush immediately."""
        self.file.write(json.dumps(event) + "\n")
        self.file.flush()

    def close(self) -> None:
        """Close the output file."""
        self.file.close()