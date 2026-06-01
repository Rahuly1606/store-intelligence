"""
Metrics Domain Model

Represents store metrics data structure.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StoreMetrics:
    """Store metrics domain model."""
    
    unique_visitors: int
    conversion_rate: float
    avg_dwell_per_zone_ms: Dict[str, int]
    queue_depth: int
    abandonment_rate: float
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'StoreMetrics':
        """Create from API response."""
        return cls(
            unique_visitors=data.get('unique_visitors', 0),
            conversion_rate=data.get('conversion_rate', 0.0),
            avg_dwell_per_zone_ms=data.get('avg_dwell_per_zone_ms', {}),
            queue_depth=data.get('queue_depth', 0),
            abandonment_rate=data.get('abandonment_rate', 0.0)
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        # Format dwell times from ms to readable format
        dwell_times = {}
        for zone, ms in self.avg_dwell_per_zone_ms.items():
            seconds = ms / 1000
            if seconds < 60:
                dwell_times[zone] = f"{seconds:.1f}s"
            else:
                minutes = seconds / 60
                dwell_times[zone] = f"{minutes:.1f}m"
        
        return {
            'unique_visitors': self.unique_visitors,
            'conversion_rate': round(self.conversion_rate * 100, 2),  # Convert to percentage
            'dwell_times': dwell_times,  # Formatted dwell times
            'avg_dwell_per_zone_ms': self.avg_dwell_per_zone_ms,  # Raw data
            'queue_depth': self.queue_depth,
            'abandonment_rate': round(self.abandonment_rate * 100, 2)  # Convert to percentage
        }


@dataclass
class FunnelData:
    """Conversion funnel domain model."""
    
    entry: int
    zone_visit: int
    billing_queue: int
    conversion: int
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'FunnelData':
        """Create from API response."""
        return cls(
            entry=data.get('entry', 0),
            zone_visit=data.get('zone_visit', 0),
            billing_queue=data.get('billing_queue', 0),
            conversion=data.get('conversion', 0)
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary with percentages."""
        total = self.entry if self.entry > 0 else 1
        return {
            'entry': self.entry,
            'zone_visit': self.zone_visit,
            'billing_queue': self.billing_queue,
            'conversion': self.conversion,
            'entry_pct': 100.0,
            'zone_visit_pct': round((self.zone_visit / total) * 100, 1),
            'billing_queue_pct': round((self.billing_queue / total) * 100, 1),
            'conversion_pct': round((self.conversion / total) * 100, 1)
        }


@dataclass
class HeatmapData:
    """Heatmap domain model."""
    
    zone_visits: Dict[str, int]
    zone_dwell_avg_ms: Dict[str, int]
    normalized_intensity: Dict[str, float]
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'HeatmapData':
        """Create from API response."""
        return cls(
            zone_visits=data.get('zone_visits', {}),
            zone_dwell_avg_ms=data.get('zone_dwell_avg_ms', {}),
            normalized_intensity=data.get('normalized_intensity', {})
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'zone_visits': self.zone_visits,
            'zone_dwell_avg_ms': self.zone_dwell_avg_ms,
            'normalized_intensity': self.normalized_intensity
        }
