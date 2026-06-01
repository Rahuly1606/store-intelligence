"""
Video Domain Model

Represents video entity with business logic.
Follows Single Responsibility Principle.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class CameraType(Enum):
    """Camera type enumeration."""
    ENTRY = "CAM_ENTRY_01"
    MAINFLOOR = "CAM_MAINFLOOR_01"
    BILLING = "CAM_BILLING_01"
    
    @classmethod
    def from_string(cls, value: str) -> 'CameraType':
        """Create CameraType from string value."""
        mapping = {
            'entry': cls.ENTRY,
            'mainfloor': cls.MAINFLOOR,
            'billing': cls.BILLING
        }
        return mapping.get(value.lower(), cls.ENTRY)


class ProcessingStatus(Enum):
    """Video processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Video:
    """
    Video domain model.
    
    Represents a video file with its metadata and processing state.
    Immutable after creation (use methods to create new instances).
    """
    
    filename: str
    camera_type: CameraType
    store_id: str
    file_path: Path
    uploaded_at: datetime
    status: ProcessingStatus = ProcessingStatus.PENDING
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def camera_id(self) -> str:
        """Get camera ID string."""
        return self.camera_type.value
    
    @property
    def is_processed(self) -> bool:
        """Check if video has been processed."""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def has_failed(self) -> bool:
        """Check if processing failed."""
        return self.status == ProcessingStatus.FAILED
    
    @property
    def is_processing(self) -> bool:
        """Check if video is currently being processed."""
        return self.status == ProcessingStatus.PROCESSING
    
    def mark_processing(self) -> 'Video':
        """Create new Video instance marked as processing."""
        return Video(
            filename=self.filename,
            camera_type=self.camera_type,
            store_id=self.store_id,
            file_path=self.file_path,
            uploaded_at=self.uploaded_at,
            status=ProcessingStatus.PROCESSING,
            processed_at=None,
            error_message=None
        )
    
    def mark_completed(self) -> 'Video':
        """Create new Video instance marked as completed."""
        return Video(
            filename=self.filename,
            camera_type=self.camera_type,
            store_id=self.store_id,
            file_path=self.file_path,
            uploaded_at=self.uploaded_at,
            status=ProcessingStatus.COMPLETED,
            processed_at=datetime.utcnow(),
            error_message=None
        )
    
    def mark_failed(self, error: str) -> 'Video':
        """Create new Video instance marked as failed."""
        return Video(
            filename=self.filename,
            camera_type=self.camera_type,
            store_id=self.store_id,
            file_path=self.file_path,
            uploaded_at=self.uploaded_at,
            status=ProcessingStatus.FAILED,
            processed_at=datetime.utcnow(),
            error_message=error
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'filename': self.filename,
            'camera_type': self.camera_type.name,
            'camera_id': self.camera_id,
            'store_id': self.store_id,
            'status': self.status.value,
            'uploaded_at': self.uploaded_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'error_message': self.error_message
        }
