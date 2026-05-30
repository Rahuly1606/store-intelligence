"""
Database setup and session management.

Uses SQLAlchemy to connect to SQLite (or another database via DATABASE_URL).
Provides a `get_db` dependency for FastAPI endpoints and an `init_db` utility.
"""

import os
from typing import Generator

from sqlalchemy import Column, String, Float, Integer, Boolean, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# --------------------------------------------------------------------------- #
# Engine & Session Factory
# --------------------------------------------------------------------------- #
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app/store.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# --------------------------------------------------------------------------- #
# Base & Table
# --------------------------------------------------------------------------- #
class Base(DeclarativeBase):
    pass


class EventTable(Base):
    """SQLAlchemy table mirroring the event schema."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    camera_id = Column(String, nullable=False)
    visitor_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    zone_id = Column(String, nullable=True)
    dwell_ms = Column(Integer, nullable=False, default=0)
    is_staff = Column(Boolean, nullable=False, default=False)
    confidence = Column(Float, nullable=False)
    # Renamed from 'metadata' to avoid conflict with SQLAlchemy's internal attribute
    event_metadata = Column(Text, nullable=True, default="{}")

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_event_id"),
    )


# --------------------------------------------------------------------------- #
# Session Dependency
# --------------------------------------------------------------------------- #
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Initialisation
# --------------------------------------------------------------------------- #
def init_db():
    """Create all tables. Called at application startup."""
    Base.metadata.create_all(bind=engine)