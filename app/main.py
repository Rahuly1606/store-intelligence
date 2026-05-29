"""
Store Intelligence API — Main Application Entry Point

This module creates the FastAPI application, configures CORS (if needed),
sets up structured logging, and defines the health and ingest stubs.
All real logic will be moved to dedicated router modules later.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

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
    """
    Handle startup and shutdown events.
    On startup: initialise database and load models (future).
    On shutdown: clean up resources.
    """
    logger.info("Starting Store Intelligence API")
    # Future: initialise DB pool, pre-load config, etc.
    app.state.start_time = time.time()
    yield
    logger.info("Shutting down Store Intelligence API")
    # Future: close DB connections

# --------------------------------------------------------------------------- #
# FastAPI Application Instance
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="Store Intelligence API",
    version="0.1.0",
    description="Real‑time offline store analytics from CCTV footage",
    lifespan=lifespan,
)

# --------------------------------------------------------------------------- #
# Middleware (structured logging)
# --------------------------------------------------------------------------- #
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log every incoming request with method, path, and latency.
    """
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
# Health Endpoint
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health_check():
    """
    Service health check. Returns overall status and the last event
    timestamp per store (stub — will be implemented in Milestone 3).
    """
    # Placeholder: in the future, query the database for latest timestamps
    last_event_ts_per_store = {}  # e.g., {"STORE_BLR_002": "2026-03-03T14:41:55Z"}

    return {
        "status": "ok",
        "last_event_ts_per_store": last_event_ts_per_store,
        "uptime_seconds": round(time.time() - app.state.start_time, 2),
    }

# --------------------------------------------------------------------------- #
# Ingestion Endpoint (Stub)
# --------------------------------------------------------------------------- #
@app.post("/events/ingest")
async def ingest_events():
    """
    Ingest a batch of events. Stub implementation that returns a static
    success response. Will be replaced with full validation and storage later.
    """
    return {
        "accepted": 0,
        "rejected": 0,
        "errors": [],
    }

# --------------------------------------------------------------------------- #
# Root Redirect
# --------------------------------------------------------------------------- #
@app.get("/")
async def root():
    """Redirect to the API docs."""
    return {"message": "Store Intelligence API — visit /docs for Swagger UI"}