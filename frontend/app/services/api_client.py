"""
API Client Service

Handles communication with FastAPI backend.
Follows Single Responsibility Principle - only handles API calls.
"""

import logging
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException, Timeout


logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Custom exception for API client errors."""
    pass


class APIClient:
    """
    Client for FastAPI backend communication.
    
    Implements retry logic and error handling.
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of FastAPI backend
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_metrics(self, store_id: str) -> Dict[str, Any]:
        """
        Get store metrics.
        
        Args:
            store_id: Store identifier
            
        Returns:
            Metrics data dictionary
            
        Raises:
            APIClientError: If request fails
        """
        endpoint = f"/stores/{store_id}/metrics"
        return self._get(endpoint)
    
    def get_funnel(self, store_id: str) -> Dict[str, Any]:
        """
        Get conversion funnel data.
        
        Args:
            store_id: Store identifier
            
        Returns:
            Funnel data dictionary
            
        Raises:
            APIClientError: If request fails
        """
        endpoint = f"/stores/{store_id}/funnel"
        return self._get(endpoint)
    
    def get_heatmap(self, store_id: str) -> Dict[str, Any]:
        """
        Get heatmap data.
        
        Args:
            store_id: Store identifier
            
        Returns:
            Heatmap data dictionary
            
        Raises:
            APIClientError: If request fails
        """
        endpoint = f"/stores/{store_id}/heatmap"
        return self._get(endpoint)
    
    def get_anomalies(self, store_id: str) -> Dict[str, Any]:
        """
        Get anomaly detection results.
        
        Args:
            store_id: Store identifier
            
        Returns:
            Anomalies data dictionary
            
        Raises:
            APIClientError: If request fails
        """
        endpoint = f"/stores/{store_id}/anomalies"
        return self._get(endpoint)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check API health status.
        
        Returns:
            Health status dictionary
            
        Raises:
            APIClientError: If request fails
        """
        return self._get("/health")
    
    def _get(self, endpoint: str) -> Dict[str, Any]:
        """
        Perform GET request.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIClientError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"GET {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except Timeout:
            error_msg = f"Request timeout for {url}"
            logger.error(error_msg)
            raise APIClientError(error_msg)
            
        except RequestException as e:
            error_msg = f"API request failed for {url}: {str(e)}"
            logger.error(error_msg)
            raise APIClientError(error_msg)
    
    def is_available(self) -> bool:
        """
        Check if API is available.
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            self.health_check()
            return True
        except APIClientError:
            return False
    
    def close(self):
        """Close the session."""
        self.session.close()
