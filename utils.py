"""Utility functions for the Super Arbitrage application."""
import os
import logging
from functools import wraps
from flask import current_app, request, jsonify, redirect, url_for, flash
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import json
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.has_role('admin'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(action, details, user_id=None, ip_address=None, user_agent=None):
    """Log user activity to the database."""
    from .models import ActivityLog, db
    
    try:
        log = ActivityLog(
            user_id=user_id or (current_user.id if current_user.is_authenticated else None),
            action=action,
            details=details,
            ip_address=ip_address or request.remote_addr if request else None,
            user_agent=user_agent or (request.user_agent.string if request else None)
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log activity: {str(e)}")
        db.session.rollback()

def send_email(subject, recipients, text_body, html_body=None, sender=None):
    """Send an email using the configured email service."""
    if not sender:
        sender = current_app.config['MAIL_DEFAULT_SENDER']
    
    # In production, you would use a real email service like SendGrid or AWS SES
    if current_app.config.get('MAIL_SUPPRESS_SEND', False):
        # Just log the email in development
        logger.info(f"Email not sent (suppressed): {subject} to {recipients}")
        return
    
    # Example using SendGrid (uncomment and configure as needed)
    """
    import sendgrid
    from sendgrid.helpers.mail import Mail, Content, To
    
    sg = sendgrid.SendGridAPIClient(api_key=current_app.config['SENDGRID_API_KEY'])
    
    message = Mail(
        from_email=sender,
        to_emails=recipients,
        subject=subject,
        plain_text_content=text_body,
        html_content=html_body
    )
    
    try:
        response = sg.send(message)
        logger.info(f"Email sent: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise
    """
    
    # Fallback to console output
    logger.info(f"Email would be sent to {recipients} with subject: {subject}")

def generate_api_key(user_id, expires_in=3600):
    """Generate a JWT token for API authentication."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in)
    }
    return jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

def verify_api_key(token):
    """Verify a JWT token and return the user if valid."""
    from .models import User
    
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            return None
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def format_currency(amount, currency='USD'):
    """Format a number as a currency string."""
    try:
        return "${:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return str(amount)

def parse_currency(currency_str):
    """Parse a currency string into a float."""
    if not currency_str:
        return 0.0
    try:
        # Remove any non-numeric characters except decimal point
        clean_str = ''.join(c for c in str(currency_str) if c.isdigit() or c in '.,')
        # Replace comma with dot if it's used as decimal separator
        if ',' in clean_str and '.' in clean_str:
            if clean_str.find(',') > clean_str.find('.'):
                clean_str = clean_str.replace('.', '').replace(',', '.')
            else:
                clean_str = clean_str.replace(',', '')
        elif ',' in clean_str:
            clean_str = clean_str.replace(',', '.')
        return float(clean_str)
    except (ValueError, AttributeError):
        return 0.0

def calculate_profit(source_price, target_price, fees=0, shipping=0, quantity=1):
    """Calculate profit and profit margin."""
    try:
        source_price = float(source_price or 0)
        target_price = float(target_price or 0)
        fees = float(fees or 0)
        shipping = float(shipping or 0)
        quantity = int(quantity or 1)
        
        total_cost = (source_price + shipping) * quantity + fees
        total_revenue = target_price * quantity
        profit = total_revenue - total_cost
        profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            'profit': round(profit, 2),
            'profit_margin': round(profit_margin, 2),
            'total_cost': round(total_cost, 2),
            'total_revenue': round(total_revenue, 2)
        }
    except (ValueError, TypeError):
        return {
            'profit': 0,
            'profit_margin': 0,
            'total_cost': 0,
            'total_revenue': 0
        }

def get_marketplace_connector(marketplace_code):
    """Get a connector for the specified marketplace."""
    # This would return an instance of a marketplace-specific connector class
    # For now, we'll just return a dictionary with the marketplace code
    return {
        'code': marketplace_code,
        'name': marketplace_code.capitalize(),
        'authenticated': False
    }

def validate_url(url):
    """Validate a URL."""
    import re
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?'  # domain...
        r'|localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url)

def sanitize_input(input_str):
    """Sanitize user input to prevent XSS and other attacks."""
    if not input_str:
        return ''
    import bleach
    from markdown import markdown
    
    # Convert markdown to HTML
    html = markdown(input_str)
    
    # Allowed HTML tags and attributes
    allowed_tags = [
        'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li',
        'ol', 'strong', 'ul', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    ]
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'abbr': ['title'],
        'acronym': ['title']
    }
    
    # Clean the HTML
    clean_html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    # Add rel="nofollow" to external links
    clean_html = bleach.linkify(clean_html, callbacks=[
        bleach.callbacks.nofollow,
        bleach.callbacks.target_blank
    ])
    
    return clean_html

def get_pagination_info(pagination, endpoint, **kwargs):
    """Generate pagination metadata for API responses."""
    return {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num,
        'links': {
            'self': url_for(endpoint, page=pagination.page, **kwargs, _external=True),
            'first': url_for(endpoint, page=1, **kwargs, _external=True),
            'last': url_for(endpoint, page=pagination.pages, **kwargs, _external=True) if pagination.pages > 0 else None,
            'prev': url_for(endpoint, page=pagination.prev_num, **kwargs, _external=True) if pagination.has_prev else None,
            'next': url_for(endpoint, page=pagination.next_num, **kwargs, _external=True) if pagination.has_next else None
        }
    }
