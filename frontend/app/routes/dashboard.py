"""
Dashboard Routes

Handles dashboard display and metrics API endpoints.
Follows Single Responsibility Principle - only handles HTTP layer.
"""

import logging
from flask import Blueprint, request, jsonify, current_app, render_template

from app.models import StoreMetrics, FunnelData, HeatmapData
from app.services import APIClientError


logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def dashboard():
    """Render dashboard page."""
    store_id = request.args.get('store_id', current_app.config['DEFAULT_STORE_ID'])
    return render_template('dashboard.html', store_id=store_id)


@dashboard_bp.route('/api/metrics/<store_id>')
def get_metrics(store_id: str):
    """
    Get store metrics.
    
    Args:
        store_id: Store identifier
        
    Returns:
        JSON response with metrics data
    """
    try:
        api_client = current_app.extensions['api_client']
        
        # Fetch metrics from backend
        metrics_data = api_client.get_metrics(store_id)
        
        # Convert to domain model
        metrics = StoreMetrics.from_api_response(metrics_data)
        
        return jsonify({
            'success': True,
            'data': metrics.to_dict()
        }), 200
        
    except APIClientError as e:
        logger.error(f"Failed to fetch metrics: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch metrics from backend'
        }), 503
        
    except Exception as e:
        logger.exception("Unexpected error fetching metrics")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@dashboard_bp.route('/api/funnel/<store_id>')
def get_funnel(store_id: str):
    """Get conversion funnel data."""
    try:
        api_client = current_app.extensions['api_client']
        funnel_data = api_client.get_funnel(store_id)
        funnel = FunnelData.from_api_response(funnel_data)
        
        return jsonify({
            'success': True,
            'data': funnel.to_dict()
        }), 200
        
    except APIClientError as e:
        logger.error(f"Failed to fetch funnel: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch funnel from backend'
        }), 503


@dashboard_bp.route('/api/heatmap/<store_id>')
def get_heatmap(store_id: str):
    """Get heatmap data."""
    try:
        api_client = current_app.extensions['api_client']
        heatmap_data = api_client.get_heatmap(store_id)
        heatmap = HeatmapData.from_api_response(heatmap_data)
        
        return jsonify({
            'success': True,
            'data': heatmap.to_dict()
        }), 200
        
    except APIClientError as e:
        logger.error(f"Failed to fetch heatmap: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch heatmap from backend'
        }), 503


@dashboard_bp.route('/api/health')
def health_check():
    """Check application and backend health."""
    try:
        api_client = current_app.extensions['api_client']
        backend_health = api_client.health_check()
        backend_available = True
    except APIClientError:
        backend_health = None
        backend_available = False
    
    return jsonify({
        'success': True,
        'data': {
            'frontend': 'ok',
            'backend': 'ok' if backend_available else 'unavailable',
            'backend_details': backend_health
        }
    }), 200


@dashboard_bp.route('/api/dashboard-data/<store_id>')
def get_dashboard_data(store_id: str):
    """Get all dashboard data in single request (optimized)."""
    try:
        api_client = current_app.extensions['api_client']
        
        metrics_data = api_client.get_metrics(store_id)
        funnel_data = api_client.get_funnel(store_id)
        heatmap_data = api_client.get_heatmap(store_id)
        
        metrics = StoreMetrics.from_api_response(metrics_data)
        funnel = FunnelData.from_api_response(funnel_data)
        heatmap = HeatmapData.from_api_response(heatmap_data)
        
        return jsonify({
            'success': True,
            'data': {
                'metrics': metrics.to_dict(),
                'funnel': funnel.to_dict(),
                'heatmap': heatmap.to_dict()
            }
        }), 200
        
    except APIClientError as e:
        logger.error(f"Failed to fetch dashboard data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch data from backend'
        }), 503
