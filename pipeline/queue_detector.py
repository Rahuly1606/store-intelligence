"""
Queue detection module for billing camera.

Detects when visitors join or leave the billing queue, computes queue depth,
and emits BILLING_QUEUE_JOIN / BILLING_QUEUE_ABANDON events.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("queue")


class QueueDetector:
    """
    Monitors the billing zone and emits queue events.

    Parameters
    ----------
    layout_path : str
        Path to store_layout.json.
    proximity_threshold : float
        Max distance (in pixels) from the counter line to be considered "in queue".
    """

    def __init__(self, layout_path: str, proximity_threshold: float = 50.0) -> None:
        self.proximity_threshold = proximity_threshold

        # Load billing zone polygon from store_layout.json
        import json
        with open(layout_path, "r") as f:
            data = json.load(f)
        self.billing_polygon = None
        self.counter_line = None  # (start_point, end_point) – middle line of billing zone
        for zone in data.get("zones", []):
            if zone.get("name") == "BILLING":
                pts = zone["polygon"]
                self.billing_polygon = np.array(pts, dtype=np.int32)
                # Use the bottom edge as the counter line (assumption)
                # Actually we'll define counter_line explicitly in config for flexibility
                break

        # Per‑track state: track_id -> {in_queue, joined_event_sent}
        self.track_state: Dict[int, Dict[str, Any]] = {}

    def set_counter_line(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> None:
        """Define the counter line (where people queue)."""
        self.counter_line = (np.array(p1), np.array(p2))

    def _distance_to_line(self, point: Tuple[float, float]) -> float:
        """Perpendicular distance from point to the counter line."""
        if self.counter_line is None:
            return float("inf")
        p, q = self.counter_line
        return float(np.linalg.norm(np.cross(q - p, p - np.array(point)))) / np.linalg.norm(q - p)

    def _inside_billing_zone(self, point: Tuple[float, float]) -> bool:
        if self.billing_polygon is None:
            return False
        return cv2.pointPolygonTest(self.billing_polygon, point, False) >= 0

    def _compute_queue_depth(self, all_points: List[Tuple[float, float]]) -> int:
        """Count how many points are within proximity threshold of the counter line."""
        if self.counter_line is None:
            return 0
        count = 0
        for pt in all_points:
            if self._distance_to_line(pt) <= self.proximity_threshold:
                count += 1
        return count

    def update(
        self,
        track_id: int,
        point: Tuple[float, float],
        frame_time: datetime,
        camera_id: str,
        visitor_id: str,
        is_staff: bool,
        confidence: float,
        emitter,  # EventEmitter
        all_centers: List[Tuple[float, float]],  # all track centers in this camera
    ) -> None:
        """
        Process one track for queue events. Call every frame for each active track
        in the billing camera.

        all_centers: list of center points of all current tracks (for queue depth).
        """
        if is_staff:
            return  # Staff don't queue

        in_zone = self._inside_billing_zone(point)
        near_counter = self._distance_to_line(point) <= self.proximity_threshold if in_zone else False

        state = self.track_state.get(track_id)
        if state is None:
            state = {"in_queue": False, "joined_sent": False}
            self.track_state[track_id] = state

        # Compute current queue depth (including this track if it would be in queue)
        all_points_for_depth = list(all_centers)
        if near_counter:
            all_points_for_depth.append(point)
        queue_depth = self._compute_queue_depth(all_points_for_depth)

        # --- Queue JOIN ---
        if near_counter and not state["in_queue"] and queue_depth > 0:
            state["in_queue"] = True
            state["joined_sent"] = True
            emitter.emit(emitter._make_event(
                event_type="BILLING_QUEUE_JOIN",
                camera_id=camera_id,
                visitor_id=visitor_id,
                timestamp=frame_time,
                is_staff=False,
                confidence=confidence,
                metadata={"queue_depth": queue_depth},
            ))

        # --- Queue ABANDON ---
        if not near_counter and state["in_queue"]:
            state["in_queue"] = False
            emitter.emit(emitter._make_event(
                event_type="BILLING_QUEUE_ABANDON",
                camera_id=camera_id,
                visitor_id=visitor_id,
                timestamp=frame_time,
                is_staff=False,
                confidence=confidence,
            ))

        # If the person left the billing zone entirely, clear state
        if not in_zone:
            if state["in_queue"]:
                state["in_queue"] = False
                # Don't emit ABANDON again if we already did
            self.track_state.pop(track_id, None)