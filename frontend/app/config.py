"""
Configuration Management Module

Follows Single Responsibility Principle - handles only configuration.
Supports multiple environments (development, production, testing).
"""

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Base configuration class with common settings."""
    
    # Application
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = BASE_DIR.parent  # Backend directory
    UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size
    
    # Backend API
    FASTAPI_BASE_URL = os.environ.get('FASTAPI_BASE_URL', 'http://localhost:8000')
    API_TIMEOUT = 30  # seconds
    
    # Pipeline
    PIPELINE_CONFIG = str(PROJECT_ROOT / 'pipeline' / 'config.yaml')
    PIPELINE_SCRIPT = str(PROJECT_ROOT / 'pipeline' / 'detect.py')
    
    # Store Configuration
    DEFAULT_STORE_ID = 'STORE_BLR_002'
    
    # Dashboard
    DASHBOARD_REFRESH_INTERVAL = 5000  # milliseconds
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config."""
        Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in production")


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING = True
    DEBUG = True
    UPLOAD_FOLDER = Path('/tmp/test_uploads')
    FASTAPI_BASE_URL = 'http://localhost:8001'


config: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """Get configuration based on environment."""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
