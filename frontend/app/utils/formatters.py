"""
Data Formatting Utilities

Follows Single Responsibility Principle - only formats data.
"""

from datetime import datetime
from typing import Any, Dict


class TimeFormatter:
    """Formats time-related data."""
    
    @staticmethod
    def milliseconds_to_seconds(ms: int) -> float:
        """Convert milliseconds to seconds."""
        return round(ms / 1000, 2)
    
    @staticmethod
    def milliseconds_to_minutes(ms: int) -> float:
        """Convert milliseconds to minutes."""
        return round(ms / 60000, 2)
    
    @staticmethod
    def format_duration(ms: int) -> str:
        """Format duration in human-readable format."""
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60000:
            return f"{TimeFormatter.milliseconds_to_seconds(ms)}s"
        else:
            return f"{TimeFormatter.milliseconds_to_minutes(ms)}m"


class PercentageFormatter:
    """Formats percentage data."""
    
    @staticmethod
    def format(value: float, decimals: int = 1) -> str:
        """Format decimal as percentage string."""
        return f"{round(value * 100, decimals)}%"
    
    @staticmethod
    def to_percentage(value: float, decimals: int = 1) -> float:
        """Convert decimal to percentage number."""
        return round(value * 100, decimals)


class MetricsFormatter:
    """Formats metrics data for display."""
    
    @staticmethod
    def format_dwell_times(dwell_data: Dict[str, int]) -> Dict[str, str]:
        """Format dwell times for display."""
        return {
            zone: TimeFormatter.format_duration(ms)
            for zone, ms in dwell_data.items()
        }
    
    @staticmethod
    def format_metrics_response(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Format complete metrics response for frontend."""
        return {
            'unique_visitors': metrics.get('unique_visitors', 0),
            'conversion_rate': PercentageFormatter.format(
                metrics.get('conversion_rate', 0.0)
            ),
            'queue_depth': metrics.get('queue_depth', 0),
            'abandonment_rate': PercentageFormatter.format(
                metrics.get('abandonment_rate', 0.0)
            ),
            'dwell_times': MetricsFormatter.format_dwell_times(
                metrics.get('avg_dwell_per_zone_ms', {})
            )
        }


class FilenameFormatter:
    """Formats filenames safely."""
    
    @staticmethod
    def sanitize(filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Remove any non-alphanumeric characters except dots, dashes, underscores
        import re
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        
        return filename
    
    @staticmethod
    def add_timestamp(filename: str) -> str:
        """Add timestamp to filename to ensure uniqueness."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        return f"{name}_{timestamp}.{ext}" if ext else f"{name}_{timestamp}"
