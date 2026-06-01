"""Routes package - HTTP layer."""

from app.routes.upload import upload_bp
from app.routes.dashboard import dashboard_bp

__all__ = ['upload_bp', 'dashboard_bp']
