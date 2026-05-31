"""
Full verification script for the detection pipeline.
Reads an events.jsonl file and computes all metrics that the API would.
You can then compare these numbers with manual video observation.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

# ---- CONFIGURE THESE ----
EVENTS_FILE = "events_final.jsonl"        # change as needed
STORE_ID    = "STORE_BLR_002"
# Optional: filter by time window, leave as None to analyse the whole file
START_TIME  = None   # e.g. "2026-03-03T10:00:00Z"
END_TIME    = None   # e.g. "2026-03-03T10:01:00Z"
# -------------------------

def parse_ts(ts: str):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

# Load events
with open(EVENTS_FILE) as f:
    all_events = [json.loads(line) for line in f]

# Apply filters
events = []
for e in all_events:
    if e["store_id"] != STORE_ID:
        continue
    if START_TIME and e["timestamp"] < START_TIME:
        continue
    if END_TIME   and e["timestamp"] > END_TIME:
        continue
    events.append(e)

# --- Counts per event type ---
type_counts = Counter(e["event_type"] for e in events)

# --- Unique visitors (exclude staff) ---
visitors = set()
staff_ids = set()
for e in events:
    if e["event_type"] == "ENTRY":
        visitors.add(e["visitor_id"])
        if e["is_staff"]:
            staff_ids.add(e["visitor_id"])
real_visitors = visitors - staff_ids

# --- Converted visitors (BILLING_QUEUE_JOIN) ---
converted = set()
for e in events:
    if e["event_type"] == "BILLING_QUEUE_JOIN" and e["visitor_id"] in real_visitors:
        converted.add(e["visitor_id"])
conversion_rate = (len(converted) / len(real_visitors)) if real_visitors else 0.0

# --- Zone visit frequency & average dwell ---
zone_visits = defaultdict(set)   # zone -> set of visitor_ids
zone_dwells = defaultdict(list)  # zone -> list of dwell_ms

for e in events:
    if e["event_type"] == "ZONE_ENTER" and e["visitor_id"] in real_visitors:
        zone_visits[e["zone_id"]].add(e["visitor_id"])
    if e["event_type"] == "ZONE_DWELL" and e["visitor_id"] in real_visitors:
        zone_dwells[e["zone_id"]].append(e["dwell_ms"])

# --- Queue metrics ---
queue_joins = []
queue_abandons = 0
for e in events:
    if e["event_type"] == "BILLING_QUEUE_JOIN":
        queue_joins.append(e["metadata"].get("queue_depth", 0))
    if e["event_type"] == "BILLING_QUEUE_ABANDON":
        queue_abandons += 1

queue_depth = queue_joins[-1] if queue_joins else 0
total_joined = len(queue_joins)
abandonment_rate = (queue_abandons / total_joined) if total_joined else 0.0

# --- Staff events ---
staff_events = sum(1 for e in events if e["is_staff"])

# ========================================================================
# PRINT SUMMARY
# ========================================================================
print("=" * 60)
print(f"  VERIFICATION REPORT  —  {STORE_ID}")
print(f"  File: {EVENTS_FILE}")
if START_TIME and END_TIME:
    print(f"  Window: {START_TIME} → {END_TIME}")
print("=" * 60)

print(f"\n📊 EVENT COUNTS")
print(f"  Total events: {len(events)}")
for etype, count in sorted(type_counts.items()):
    print(f"    {etype}: {count}")

print(f"\n🧑 UNIQUE VISITORS (excl. staff)")
print(f"  Total entries (incl. staff): {len(visitors)}")
print(f"  Staff visitors:              {len(staff_ids)}")
print(f"  Real visitors:               {len(real_visitors)}")

print(f"\n💰 CONVERSION")
print(f"  Converted visitors: {len(converted)}")
print(f"  Conversion rate:    {conversion_rate:.2%}")

print(f"\n🗺️  ZONE VISIT FREQUENCY")
for zone, vset in sorted(zone_visits.items()):
    print(f"  {zone}: {len(vset)} visits")
print(f"\n⏱️  AVERAGE DWELL PER ZONE")
for zone, dlist in sorted(zone_dwells.items()):
    avg = sum(dlist) / len(dlist)
    print(f"  {zone}: {avg:.0f} ms")

print(f"\n🛒 QUEUE")
print(f"  Current queue depth:     {queue_depth}")
print(f"  Total BILLING_QUEUE_JOIN: {total_joined}")
print(f"  BILLING_QUEUE_ABANDON:   {queue_abandons}")
print(f"  Abandonment rate:        {abandonment_rate:.2%}")

print(f"\n👔 STAFF")
print(f"  Staff events: {staff_events}")

# ========================================================================
# API COMPARISON (optional)
# ========================================================================
try:
    import requests
    resp = requests.get(f"http://localhost:8000/stores/{STORE_ID}/metrics")
    if resp.status_code == 200:
        api = resp.json()
        print(f"\n🔗 API METRICS COMPARISON")
        print(f"  API unique_visitors:     {api['unique_visitors']}  (ours: {len(real_visitors)})")
        print(f"  API conversion_rate:     {api['conversion_rate']:.4f}  (ours: {conversion_rate:.4f})")
        print(f"  API queue_depth:         {api['queue_depth']}  (ours: {queue_depth})")
        print(f"  API abandonment_rate:    {api['abandonment_rate']:.4f}  (ours: {abandonment_rate:.4f})")
        print(f"  API avg_dwell_per_zone:  {api['avg_dwell_per_zone_ms']}")
    else:
        print("\n⚠️  API not reachable or returned error")
except Exception as ex:
    print(f"\n⚠️  API check skipped: {ex}")