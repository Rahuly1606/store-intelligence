#!/usr/bin/env python3
"""
Detection Pipeline — Full Integration with Zone, Staff, and Queue Detection

Reads a CCTV clip, runs YOLOv8 person detection, tracks individuals,
detects entry/exit line crossing, maps positions to store zones,
classifies staff, detects billing queue, and writes structured events.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

from pipeline.emit import EventEmitter
from pipeline.tracker import Tracker
from pipeline.zones import ZoneMapper
from pipeline.staff import StaffClassifier
from pipeline.queue_detector import QueueDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("detect")


def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def process_video(
    video_path: Path,
    camera_id: str,
    store_id: str,
    config: dict,
    emitter: EventEmitter,
    start_time: datetime,
) -> None:
    model = YOLO(config.get("model_weights", "yolov8n.pt"))
    confidence = config.get("confidence_threshold", 0.3)

    entry_line = (
        (config["entry_line"]["x1"], config["entry_line"]["y1"]),
        (config["entry_line"]["x2"], config["entry_line"]["y2"]),
    )
    tracker = Tracker(
        entry_line=entry_line,
        track_thresh=config.get("track_thresh", 0.3),
        track_buffer=config.get("track_buffer", 30),
        match_thresh=config.get("match_thresh", 0.3),
    )

    staff_cfg = config.get("staff_detection", {})
    staff_classifier = StaffClassifier(
        color_lower=staff_cfg.get("color_lower", [100, 50, 50]),
        color_upper=staff_cfg.get("color_upper", [130, 255, 255]),
        threshold=0.3,
    )

    zone_mapper = None
    layout_path = config.get("store_layout_path", "data/store_layout.json")
    try:
        zone_mapper = ZoneMapper(
            layout_path=layout_path,
            dwell_interval_sec=config.get("dwell_interval_sec", 30),
        )
        logger.info("Zone detection active (layout: %s)", layout_path)
    except Exception as e:
        logger.warning("Zone detection disabled: %s", e)

    # Queue detector for billing camera
    queue_detector = None
    if camera_id == "CAM_BILLING_01" and config.get("queue_detection", {}).get("enabled", False):
        try:
            queue_detector = QueueDetector(
                layout_path=layout_path,
                proximity_threshold=config["queue_detection"]["proximity_threshold"],
            )
            # Set counter line from layout (or config fallback)
            if queue_detector.billing_polygon is not None:
                # Extract counter line from store_layout.json
                with open(layout_path) as f:
                    import json
                    layout = json.load(f)
                for zone in layout["zones"]:
                    if zone["name"] == "BILLING" and "counter_line" in zone:
                        cl = zone["counter_line"]
                        queue_detector.set_counter_line(
                            (cl["x1"], cl["y1"]), (cl["x2"], cl["y2"])
                        )
                        break
            logger.info("Queue detection enabled")
        except Exception as e:
            logger.warning("Queue detection disabled: %s", e)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info("Processing %s (%d frames @ %.2f fps)", video_path.name, total_frames, fps)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_time = start_time + timedelta(seconds=frame_idx / fps)

        results = model(frame, verbose=False)
        detections = []
        for box in results[0].boxes:
            if box.cls == 0 and box.conf >= confidence:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append([x1, y1, x2, y2, float(box.conf)])

        detections_np = np.array(detections, dtype=np.float32) if detections else np.empty((0, 5))
        track_events = tracker.update(detections_np, frame_time, camera_id)

        for ev in track_events:
            full_event = emitter._make_event(
                event_type=ev["event_type"],
                camera_id=ev["camera_id"],
                visitor_id=ev["visitor_id"],
                timestamp=ev["timestamp"],
                is_staff=ev.get("is_staff", False),
                confidence=ev["confidence"],
            )
            emitter.emit(full_event)

        # Collect all current track centers for queue depth
        all_centers: List[Tuple[float, float]] = []
        for tid, state in tracker.tracks.items():
            box = state.get("box")
            if box is not None:
                center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                all_centers.append(center)

        # Process each track: zones, staff, queue
        for tid, state in tracker.tracks.items():
            box = state.get("box")
            if box is None:
                continue

            center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

            # Staff classification (once)
            if not state.get("staff_classified", False):
                bbox = [int(v) for v in box]
                state["is_staff"] = staff_classifier.is_staff(frame, bbox)
                state["staff_classified"] = True

            # Zone detection
            if zone_mapper:
                zone_mapper.update(
                    track_id=tid,
                    point=center,
                    camera_id=camera_id,
                    frame_time=frame_time,
                    visitor_id=state["visitor_id"],
                    is_staff=state.get("is_staff", False),
                    confidence=float(state.get("confidence", 0.0)),
                    emitter=emitter,
                )

            # Queue detection
            if queue_detector:
                queue_detector.update(
                    track_id=tid,
                    point=center,
                    frame_time=frame_time,
                    camera_id=camera_id,
                    visitor_id=state["visitor_id"],
                    is_staff=state.get("is_staff", False),
                    confidence=float(state.get("confidence", 0.0)),
                    emitter=emitter,
                    all_centers=all_centers,
                )

        frame_idx += 1
        if frame_idx % 500 == 0:
            logger.info("Progress: %d / %d frames", frame_idx, total_frames)

    cap.release()
    logger.info("Finished %s (%d frames)", video_path.name, frame_idx)


def main():
    parser = argparse.ArgumentParser(description="Full Detection Pipeline")
    parser.add_argument("--config", default="pipeline/config.yaml", help="Path to YAML config")
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument("--camera", required=True, help="Camera ID")
    parser.add_argument("--store", required=True, help="Store ID")
    parser.add_argument("--output", default=None, help="Output JSONL file")
    args = parser.parse_args()

    config = load_config(args.config)
    video_path = Path(args.video)
    if not video_path.exists():
        logger.error("Video file not found: %s", video_path)
        sys.exit(1)

    output_path = Path(args.output) if args.output else Path(config.get("output_path", "events.jsonl"))
    emitter = EventEmitter(output_path, args.store)
    start_time = datetime(2026, 3, 3, 10, 0, 0, tzinfo=timezone.utc)

    try:
        process_video(
            video_path=video_path,
            camera_id=args.camera,
            store_id=args.store,
            config=config,
            emitter=emitter,
            start_time=start_time,
        )
    finally:
        emitter.close()

    logger.info("Events written to %s", emitter.output_path)


if __name__ == "__main__":
    main()