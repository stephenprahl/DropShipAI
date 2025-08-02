"""
Configuration module for Super Arbitrage.
Handles loading configuration from YAML files and environment variables.
"""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-super-arbitrage')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # File upload settings
    UPLOAD_FOLDER = 'data/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @classmethod
    def load_yaml_config(cls, config_path):
        """Load configuration from YAML file."""
        if not Path(config_path).exists():
            return {}
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///data/development.db')
    
    # Enable detailed logging
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/superarb')
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging
    LOG_LEVEL = 'INFO'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Load additional configurations
dashboard_config = Config.load_yaml_config(Path(__file__).parent / 'dashboard.yaml')
logging_config = Config.load_yaml_config(Path(__file__).parent / 'logging.yaml')
notifications_config = Config.load_yaml_config(Path(__file__).parent / 'notifications.yaml')

# Select configuration based on environment
env = os.environ.get('FLASK_ENV', 'development')
if env == 'production':
    config = ProductionConfig()
elif env == 'testing':
    config = TestingConfig()
else:
    config = DevelopmentConfig()

# Update config with YAML settings
for key, value in {**dashboard_config, **logging_config, **notifications_config}.items():
    setattr(config, key, value)
