"""
Zone detection module.

Loads store_layout.json and provides a ZoneMapper class that determines
which zone a point belongs to, tracks per-person zone state, and emits
ZONE_ENTER, ZONE_EXIT, ZONE_DWELL events.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("zones")


class ZoneMapper:
    """
    Maps 2D points to store zones and manages dwell logic.

    Parameters
    ----------
    layout_path : str
        Path to store_layout.json.
    dwell_interval_sec : float
        Seconds between successive ZONE_DWELL events for the same person.
    """

    def __init__(self, layout_path: str, dwell_interval_sec: float = 30.0) -> None:
        self.dwell_interval_sec = dwell_interval_sec
        # Load zones
        import json
        with open(layout_path, "r") as f:
            data = json.load(f)
        self.zones = data.get("zones", [])
        # Pre-compute polygons per camera for quick lookup
        self._cam_zones: Dict[str, Dict[str, np.ndarray]] = {}
        for zone in self.zones:
            name = zone["name"]
            poly = np.array(zone["polygon"], dtype=np.int32)
            for cam in zone.get("cameras", []):
                self._cam_zones.setdefault(cam, {})[name] = poly

        # Per‑track state: track_id -> {current_zone, enter_time, last_dwell}
        self.track_state: Dict[int, Dict[str, Any]] = {}

    def get_zone(self, point: Tuple[float, float], camera_id: str) -> Optional[str]:
        """Return the zone name the point falls into, or None."""
        if camera_id not in self._cam_zones:
            return None
        for name, poly in self._cam_zones[camera_id].items():
            if cv2.pointPolygonTest(poly, point, False) >= 0:
                return name
        return None

    def update(
        self,
        track_id: int,
        point: Tuple[float, float],
        camera_id: str,
        frame_time: datetime,
        visitor_id: str,
        is_staff: bool,
        confidence: float,
        emitter,  # EventEmitter instance
    ) -> None:
        """
        Process one track for zone transitions and dwell.
        Call this for every active track in every frame.

        emitter must have an `emit(event_dict)` method.
        """
        zone = self.get_zone(point, camera_id)
        state = self.track_state.get(track_id)
        if state is None:
            state = {
                "zone": None,
                "enter_time": None,
                "last_dwell": None,
            }
            self.track_state[track_id] = state

        old_zone = state["zone"]

        # --- Zone change ---
        if zone != old_zone:
            # Exit old zone
            if old_zone:
                emitter.emit(emitter._make_event(
                    event_type="ZONE_EXIT",
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    timestamp=frame_time,
                    zone_id=old_zone,
                    is_staff=is_staff,
                    confidence=confidence,
                ))
            # Enter new zone
            if zone:
                state["enter_time"] = frame_time
                state["last_dwell"] = None  # reset dwell timer on entry
                emitter.emit(emitter._make_event(
                    event_type="ZONE_ENTER",
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    timestamp=frame_time,
                    zone_id=zone,
                    is_staff=is_staff,
                    confidence=confidence,
                ))
            state["zone"] = zone

        # --- Dwell logic ---
        if zone and state["enter_time"]:
            dwell_sec = (frame_time - state["enter_time"]).total_seconds()
            last_dwell = state.get("last_dwell")
            # Emit DWELL every dwell_interval_sec
            if dwell_sec >= self.dwell_interval_sec:
                if (last_dwell is None or
                    (frame_time - last_dwell).total_seconds() >= self.dwell_interval_sec):
                    emitter.emit(emitter._make_event(
                        event_type="ZONE_DWELL",
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        timestamp=frame_time,
                        zone_id=zone,
                        dwell_ms=int(dwell_sec * 1000),
                        is_staff=is_staff,
                        confidence=confidence,
                    ))
                    state["last_dwell"] = frame_time