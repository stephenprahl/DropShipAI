"""
Super Arbitrage - A platform for finding and managing online arbitrage opportunities.
"""
from flask import Flask
from flask_cors import CORS
from config import config
from .extensions import (
    db, login_manager, limiter, mail, cache, assets, csrf
)
login_manager.login_message_category = 'info'

def create_app(config_name='default'):
    """
    Application factory function.
    
    Args:
        config_name (str): The configuration to use. Defaults to 'default'.
        
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Apply configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    cache.init_app(app)
    assets.init_app(app)
    csrf.init_app(app)
    CORS(app)
    
    # Configure logging
    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler
        import os
        
        # Ensure log directory exists
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        # File handler for logging
        file_handler = RotatingFileHandler(
            'logs/superarbitrage.log',
            maxBytes=10240,
            backupCount=10
        )
        
        # Format for log messages
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Super Arbitrage startup')
    
    # Register blueprints
    from .auth import auth as auth_blueprint
    from .main import main as main_blueprint
    from .api import api as api_blueprint
    from .admin import admin as admin_blueprint
    
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    
    # Error handlers
    from .errors import not_found_error, internal_error, forbidden_error, ratelimit_error
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)
    app.register_error_handler(403, forbidden_error)
    app.register_error_handler(429, ratelimit_error)
    
    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': User,
            'Product': Product,
            'Marketplace': Marketplace,
            'ArbitrageOpportunity': ArbitrageOpportunity
        }
    
    # CLI commands
    from .commands import register_commands
    register_commands(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
