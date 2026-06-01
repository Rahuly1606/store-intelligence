"""
Application Factory Module

Implements Factory Pattern for Flask application creation.
Follows Dependency Inversion Principle - depends on abstractions.
"""

import logging
from flask import Flask
from pathlib import Path

from app.config import get_config


def create_app(config_name: str = None) -> Flask:
    """
    Application factory function.
    
    Creates and configures Flask application instance with proper
    dependency injection and service initialization.
    
    Args:
        config_name: Configuration environment name
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Initialize logging
    _configure_logging(app)
    
    # Register blueprints (routes)
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Initialize services (dependency injection)
    _initialize_services(app)
    
    app.logger.info(f"Application started in {config_name or 'development'} mode")
    
    return app


def _configure_logging(app: Flask) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format=app.config['LOG_FORMAT']
    )


def _register_blueprints(app: Flask) -> None:
    """Register application blueprints (route modules)."""
    from app.routes.upload import upload_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(upload_bp)
    app.register_blueprint(dashboard_bp)


def _register_error_handlers(app: Flask) -> None:
    """Register custom error handlers."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal error: {error}')
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        return {'error': 'File size exceeds maximum allowed (500MB)'}, 413


def _initialize_services(app: Flask) -> None:
    """
    Initialize application services with dependency injection.
    Services are stored in app.extensions for access across the app.
    """
    from app.services.api_client import APIClient
    from app.services.storage import StorageService
    from app.services.video_processor import VideoProcessorService
    
    # Initialize services
    api_client = APIClient(
        base_url=app.config['FASTAPI_BASE_URL'],
        timeout=app.config['API_TIMEOUT']
    )
    
    storage_service = StorageService(
        upload_folder=app.config['UPLOAD_FOLDER'],
        allowed_extensions=app.config['ALLOWED_EXTENSIONS']
    )
    
    video_processor = VideoProcessorService(
        pipeline_script=app.config['PIPELINE_SCRIPT'],
        pipeline_config=app.config['PIPELINE_CONFIG'],
        api_client=api_client
    )
    
    # Store in app.extensions for dependency injection
    app.extensions['api_client'] = api_client
    app.extensions['storage_service'] = storage_service
    app.extensions['video_processor'] = video_processor
