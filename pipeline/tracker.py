"""
Self‑contained IoU‑based multi‑object tracker.

Replaces ByteTrack/boxmot to avoid heavy dependencies.
Maintains persistent visitor IDs and handles entry/exit line crossing.
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class Tracker:
    """
    Simple IoU tracker with visitor ID assignment and entry/exit detection.

    Parameters
    ----------
    entry_line : tuple ((x1,y1), (x2,y2))
    track_thresh : float
        Confidence threshold for creating new tracks.
    track_buffer : int
        Max frames a track can survive without a detection.
    match_thresh : float
        IoU threshold for matching detections to tracks.
    """

    def __init__(
        self,
        entry_line: Tuple[Tuple[int, int], Tuple[int, int]],
        track_thresh: float = 0.3,
        track_buffer: int = 30,
        match_thresh: float = 0.3,
    ) -> None:
        self.entry_line = entry_line
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.next_id = 0
        self.tracks: Dict[int, Dict[str, Any]] = {}  # track_id -> state

    def _iou(self, boxA: np.ndarray, boxB: np.ndarray) -> float:
        """Intersection over Union of two boxes [x1,y1,x2,y2]."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        return interArea / (boxAArea + boxBArea - interArea + 1e-6)

    def _side_of_line(self, point: Tuple[float, float]) -> int:
        p1, p2 = self.entry_line
        cross = (p2[0] - p1[0]) * (point[1] - p1[1]) - (p2[1] - p1[1]) * (point[0] - p1[0])
        return 1 if cross > 0 else -1

    def update(
        self,
        detections: np.ndarray,   # (N, 5) [x1,y1,x2,y2,conf]
        frame_time: Any,
        camera_id: str,
    ) -> List[Dict[str, Any]]:
        events = []
        unmatched_dets = list(range(len(detections))) if detections.size > 0 else []

        # Predict new locations for existing tracks (simple: keep last box)
        for tid, state in self.tracks.items():
            state["unmatched"] = True

        # Match detections to tracks based on IoU
        if detections.size > 0:
            for tid, state in self.tracks.items():
                best_iou = self.match_thresh
                best_idx = -1
                for i, det in enumerate(detections):
                    if i not in unmatched_dets:
                        continue
                    iou = self._iou(state["box"], det[:4])
                    if iou > best_iou:
                        best_iou = iou
                        best_idx = i
                if best_idx >= 0:
                    det = detections[best_idx]
                    state["box"] = det[:4]
                    state["confidence"] = det[4]
                    state["age"] = 0
                    state["unmatched"] = False
                    unmatched_dets.remove(best_idx)

        # Create new tracks for unmatched detections
        for i in unmatched_dets:
            det = detections[i]
            if det[4] >= self.track_thresh:
                new_id = self.next_id
                self.next_id += 1
                center = ((det[0] + det[2]) / 2, (det[1] + det[3]) / 2)
                visitor_id = f"VIS_{uuid.uuid4().hex[:7]}"
                self.tracks[new_id] = {
                    "box": det[:4],
                    "confidence": det[4],
                    "visitor_id": visitor_id,
                    "prev_center": center,
                    "crossed_in": False,
                    "age": 0,
                    "unmatched": False,
                    "is_staff": False,
                }

        # Update existing tracks: detect crossing, increase age
        to_delete = []
        for tid, state in self.tracks.items():
            if state["unmatched"]:
                state["age"] += 1
                if state["age"] > self.track_buffer:
                    to_delete.append(tid)
                continue

            center = ((state["box"][0] + state["box"][2]) / 2,
                      (state["box"][1] + state["box"][3]) / 2)
            prev_side = self._side_of_line(state["prev_center"])
            curr_side = self._side_of_line(center)

            if prev_side != curr_side:
                if curr_side == 1 and not state["crossed_in"]:
                    events.append({
                        "event_type": "ENTRY",
                        "visitor_id": state["visitor_id"],
                        "camera_id": camera_id,
                        "timestamp": frame_time,
                        "confidence": float(state["confidence"]),
                        "is_staff": state["is_staff"],
                    })
                    state["crossed_in"] = True
                elif curr_side == -1 and state["crossed_in"]:
                    events.append({
                        "event_type": "EXIT",
                        "visitor_id": state["visitor_id"],
                        "camera_id": camera_id,
                        "timestamp": frame_time,
                        "confidence": float(state["confidence"]),
                        "is_staff": state["is_staff"],
                    })
                    state["crossed_in"] = False

            state["prev_center"] = center

        for tid in to_delete:
            del self.tracks[tid]

        return events