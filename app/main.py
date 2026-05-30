"""
Store Intelligence API — Main Application Entry Point

Creates the FastAPI application, initialises the database,
includes all endpoint routers, and provides the health endpoint.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request
from sqlalchemy import func

from app.database import init_db, SessionLocal, EventTable
from app.ingestion import router as ingestion_router
from app.metrics import router as metrics_router
from app.funnel import router as funnel_router
from app.heatmap import router as heatmap_router
from app.anomalies import router as anomalies_router

# --------------------------------------------------------------------------- #
# Logging Configuration
# --------------------------------------------------------------------------- #
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api")

# --------------------------------------------------------------------------- #
# Application Lifespan (startup / shutdown)
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Store Intelligence API")
    init_db()
    app.state.start_time = time.time()
    yield
    logger.info("Shutting down Store Intelligence API")

# --------------------------------------------------------------------------- #
# FastAPI Application Instance
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="Store Intelligence API",
    version="0.5.0",
    description="Real‑time offline store analytics from CCTV footage",
    lifespan=lifespan,
)

# --------------------------------------------------------------------------- #
# Middleware (structured request logging)
# --------------------------------------------------------------------------- #
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Request %s %s → %d [%.2fms]",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

# --------------------------------------------------------------------------- #
# Routers
# --------------------------------------------------------------------------- #
app.include_router(ingestion_router)
app.include_router(metrics_router)
app.include_router(funnel_router)
app.include_router(heatmap_router)
app.include_router(anomalies_router)

# --------------------------------------------------------------------------- #
# Health Endpoint
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health_check():
    db = SessionLocal()
    try:
        last_events = (
            db.query(
                EventTable.store_id,
                func.max(EventTable.timestamp).label("latest"),
            )
            .group_by(EventTable.store_id)
            .all()
        )
        last_event_ts_per_store = {
            store: ts for store, ts in last_events
        }

        now = datetime.now(timezone.utc)
        stale_stores = []
        for store, ts_str in last_event_ts_per_store.items():
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if (now - ts) > timedelta(minutes=10):
                    stale_stores.append(store)
            except Exception:
                pass

        return {
            "status": "ok",
            "last_event_ts_per_store": last_event_ts_per_store,
            "uptime_seconds": round(time.time() - app.state.start_time, 2),
            "stale_feeds": stale_stores if stale_stores else None,
        }
    finally:
        db.close()

# --------------------------------------------------------------------------- #
# Root Redirect
# --------------------------------------------------------------------------- #
@app.get("/")
async def root():
    return {"message": "Store Intelligence API — visit /docs for Swagger UI"}