# Key Design Choices

This document explains the reasoning behind three pivotal decisions in the
Store Intelligence system. For each choice we describe the alternatives considered,
what AI suggested, and why we ultimately chose one direction.

---

## 1. Detection Model: YOLOv8 Nano

### Options considered
- **YOLOv8n** (nano) – lightweight, fast, pre‑trained on COCO, rich ecosystem.
- **YOLOv9** – newer, marginally better accuracy but heavier.
- **RT‑DETR** – transformer‑based, strong on occlusion but slower inference.
- **MediaPipe** – good for on‑device, less customisable for fine‑tuning.

### AI input
ChatGPT compared the models on accuracy vs speed for 15 fps CCTV footage.
It noted that YOLOv8n achieves >100 fps on modern GPUs, making it suitable
for real‑time processing even on CPU‑only machines, and recommended it as
the safest starting point.

### Decision
I chose YOLOv8 Nano. The primary requirements for the challenge are correct
person detection at moderate resolution (1080p, 15 fps) and reliable tracking,
not maximum mAP. YOLOv8n runs quickly even on laptop CPUs, handles the
face‑blurred footage adequately, and integrates easily with OpenCV. If
accuracy proved insufficient, the same code can switch to YOLOv8s or YOLOv9
by changing one line.

---

## 2. Event Schema Design

### Options considered
- **Flat JSON** – every field at top level, simple to query but rigid.
- **Nested structure** – e.g., grouping zone information under a sub‑object.
- **Hybrid** – the required schema from the problem statement, with a top‑level
  `metadata` dict for variable fields.

### AI input
I asked Claude to evaluate the supplied schema. It pointed out that the
`metadata` field provides extensibility without breaking downstream
consumers, and that keeping `zone_id` nullable for entry/exit events
is cleaner than using separate event shapes per type.

### Decision
I fully adopted the required schema without modification. It already
balanced simplicity with flexibility: fixed fields for core attributes,
a generic `metadata` dict for event‑specific data (queue depth, session
sequence), and null fields where applicable. This schema validated cleanly
with Pydantic and allowed the API to query across event types efficiently.

---

## 3. API Architecture: Synchronous SQLite with FastAPI

### Options considered
- **Async endpoints with async database driver** (e.g., `aiosqlite`).
- **Synchronous endpoints with SQLite** – simpler, FastAPI handles sync
  dependencies transparently.
- **PostgreSQL** – full production‑grade database.

### AI input
GitHub Copilot suggested using `aiosqlite` for non‑blocking I/O. However,
ChatGPT pointed out that for a single‑process API with low concurrency
(the challenge scenario), synchronous SQLite is simpler to set up, debug,
and test. It also noted that the `check_same_thread=False` flag is safe for
this use case.

### Decision
I used synchronous SQLite. It eliminates the complexity of async database
sessions, works perfectly with the `TestClient` in pytest, and satisfies the
challenge’s requirement for a containerised API that “just works” with
`docker compose up`. The database layer is abstracted behind `get_db`, so
migrating to PostgreSQL later would require changing only `database.py`.