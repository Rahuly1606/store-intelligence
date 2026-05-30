"""
Store Intelligence API — Main Application Entry Point

Creates the FastAPI application, configures structured logging,
initialises the database, and includes all endpoint routers.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.database import init_db
from app.ingestion import router as ingestion_router

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
    On startup: initialise database tables.
    On shutdown: clean up resources (if needed).
    """
    logger.info("Starting Store Intelligence API")
    init_db()                          # Create tables if they don't exist
    app.state.start_time = time.time()
    yield
    logger.info("Shutting down Store Intelligence API")

# --------------------------------------------------------------------------- #
# FastAPI Application Instance
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="Store Intelligence API",
    version="0.2.0",
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

# --------------------------------------------------------------------------- #
# Health Endpoint
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health_check():
    """
    Service health check. Returns overall status and the last event
    timestamp per store (stub — will be implemented in Milestone 3).
    """
    return {
        "status": "ok",
        "last_event_ts_per_store": {},
        "uptime_seconds": round(time.time() - app.state.start_time, 2),
    }

# --------------------------------------------------------------------------- #
# Root Redirect
# --------------------------------------------------------------------------- #
@app.get("/")
async def root():
    """Redirect to the API docs."""
    return {"message": "Store Intelligence API — visit /docs for Swagger UI"}