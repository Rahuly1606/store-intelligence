# System Architecture – Store Intelligence API

## Overview
The Store Intelligence system transforms raw CCTV footage into real‑time retail analytics.
It consists of two primary components:

1. **Detection Pipeline** – offline batch processor (or simulated real‑time) that reads video clips,
   runs YOLOv8 person detection, tracks individuals with an IoU‑based tracker, maps positions to
   store zones, classifies staff, and emits structured behavioural events as JSONL.

2. **Intelligence API** – a FastAPI web service that ingests events, persists them in SQLite,
   and exposes endpoints for metrics, funnel, heatmap, and anomaly detection.

The two parts are connected via a shared JSONL file that the pipeline writes and the API ingests
through `POST /events/ingest`. In a production deployment the pipeline would stream events
directly to the API, but the file‑based approach satisfies the challenge requirements while
keeping the architecture decoupled and testable.

## Pipeline Design

### Frame processing
Video files are read frame‑by‑frame with OpenCV to avoid loading entire clips into memory.
Each frame is passed through YOLOv8n (nano) for person detection. Detections are filtered
by a configurable confidence threshold (default 0.3).

### Tracking
A custom IoU‑based multi‑object tracker assigns persistent `visitor_id` tokens. We chose
a self‑contained tracker rather than ByteTrack/boxmot to avoid heavy dependency chains
and to have full control over the association logic. The tracker maintains a small state
dict per active track, including the last bounding box, centre point, and crossing flags.

### Entry / Exit detection
For entry cameras, a configurable line crossing algorithm determines when a visitor enters
or exits the store. The crossing direction is computed from the sign of the cross product.
This provides accurate unique visitor counts.

### Zone mapping
Store zones are defined as polygons in `store_layout.json`. A point‑in‑polygon test
determines which zone a visitor occupies. Dwell timers fire `ZONE_DWELL` events every 30s
of continuous presence in a zone.

### Staff classification
A colour heuristic inspects the upper third of a person’s bounding box in HSV space.
If a sufficient fraction of pixels matches a configured colour range, the person is flagged
as staff. This simple approach works well for uniformed employees and avoids the cost of a VLM.

### Queue detection
In the billing camera, visitors within a proximity threshold of a defined counter line are
considered to be in the queue. Queue depth is the count of such visitors, and
`BILLING_QUEUE_JOIN` / `BILLING_QUEUE_ABANDON` events are emitted accordingly.

## API Design
The API is built with FastAPI and follows a router‑based structure. Each domain
(ingestion, metrics, funnel, heatmap, anomalies) has its own module, keeping the codebase
modular and testable.

- **POST /events/ingest** – idempotent, validates with Pydantic, stores in SQLite.
- **GET /stores/{id}/metrics** – live aggregation of unique visitors, conversion rate, dwell, queue depth, abandonment.
- **GET /stores/{id}/funnel** – session‑based conversion funnel (Entry → Zone → Billing → Purchase).
- **GET /stores/{id}/heatmap** – normalized zone visit frequency and dwell, with data confidence flag.
- **GET /stores/{id}/anomalies** – queue spike, conversion drop, and dead zone detection.
- **GET /health** – service status plus per‑store last event timestamp and stale feed warning.

## Production Considerations
- Containerised with Docker and docker‑compose.
- Structured JSON logging with request latency.
- Idempotent ingestion protects against duplicate events.
- Graceful degradation: DB errors return 503 with structured body, not stack traces.
- Tests cover >70% statement coverage, including empty store, zero purchases, staff exclusion, and re‑entry.

## AI-Assisted Decisions

### 1. Model Selection (YOLOv8n)
I used ChatGPT to compare YOLOv8, YOLOv9, and RT‑DETR for this CCTV use case.
It provided speed vs accuracy trade‑offs and recommended YOLOv8n as a good starting point
for 15 fps footage. I agreed and chose it because it runs efficiently on CPU or GPU and
is well‑supported by the ultralytics library.

### 2. Tracking Approach
I asked Claude to suggest a tracker that would work without complex dependencies.
It proposed a simple IoU‑based tracker with a buffer, which I implemented. This avoided
the boxmot dependency issues we encountered during development and is perfectly adequate
for the challenge.

### 3. Staff Detection
I consulted ChatGPT about using a VLM versus a colour heuristic. It suggested trying a
VLM for a few frames to determine the staff uniform colour, then hard‑coding that range.
I used a VLM on a sample frame to identify the staff colour bounds and then implemented
the fast HSV‑based heuristic.