"""API endpoints for Super Arbitrage."""
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from functools import wraps
from ..models import db, User, Product, ArbitrageOpportunity, Marketplace, Notification
from ..utils import admin_required, log_activity
from datetime import datetime, timedelta
import json

# Create blueprint
api = Blueprint('api', __name__)

def api_login_required(f):
    """Decorator for API endpoints that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required',
                'code': 401
            }), 401
        return f(*args, **kwargs)
    return decorated_function

@api.route('/status')
def status():
    """API status endpoint."""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })

@api.route('/auth/status')
@api_login_required
def auth_status():
    """Check authentication status."""
    return jsonify({
        'status': 'authenticated',
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'username': current_user.username,
            'is_admin': current_user.has_role('admin')
        }
    })

@api.route('/products', methods=['GET'])
@api_login_required
def get_products():
    """Get a list of products."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = Product.query.filter_by(owner_id=current_user.id)
    
    # Apply filters
    if 'search' in request.args:
        search = f"%{request.args['search']}%"
        query = query.filter(Product.name.ilike(search))
    
    if 'marketplace_id' in request.args:
        query = query.join(ProductPriceHistory)\
                    .filter(ProductPriceHistory.marketplace_id == request.args['marketplace_id'])
    
    # Order and paginate
    products = query.order_by(Product.created_at.desc())\
                   .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'status': 'success',
        'data': {
            'items': [p.to_dict() for p in products.items],
            'page': products.page,
            'per_page': products.per_page,
            'total': products.total,
            'pages': products.pages
        }
    })

@api.route('/products/<int:product_id>', methods=['GET'])
@api_login_required
def get_product(product_id):
    """Get a single product by ID."""
    product = Product.query.get_or_404(product_id)
    
    # Check ownership
    if product.owner_id != current_user.id and not current_user.has_role('admin'):
        return jsonify({
            'status': 'error',
            'message': 'Not authorized to access this resource',
            'code': 403
        }), 403
    
    return jsonify({
        'status': 'success',
        'data': product.to_dict(detailed=True)
    })

@api.route('/opportunities', methods=['GET'])
@api_login_required
def get_opportunities():
    """Get a list of arbitrage opportunities."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    query = ArbitrageOpportunity.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if 'status' in request.args and request.args['status'] != 'all':
        query = query.filter_by(status=request.args['status'])
    
    if 'min_profit' in request.args:
        query = query.filter(ArbitrageOpportunity.profit >= float(request.args['min_profit']))
    
    if 'min_margin' in request.args:
        query = query.filter(ArbitrageOpportunity.profit_margin >= float(request.args['min_margin']))
    
    if 'source_marketplace_id' in request.args:
        query = query.filter_by(source_marketplace_id=request.args['source_marketplace_id'])
    
    if 'target_marketplace_id' in request.args:
        query = query.filter_by(target_marketplace_id=request.args['target_marketplace_id'])
    
    # Order and paginate
    opportunities = query.order_by(ArbitrageOpportunity.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'status': 'success',
        'data': {
            'items': [o.to_dict() for o in opportunities.items],
            'page': opportunities.page,
            'per_page': opportunities.per_page,
            'total': opportunities.total,
            'pages': opportunities.pages
        }
    })

@api.route('/marketplaces', methods=['GET'])
@api_login_required
def get_marketplaces():
    """Get a list of available marketplaces."""
    marketplaces = Marketplace.query.filter_by(is_active=True).all()
    return jsonify({
        'status': 'success',
        'data': [m.to_dict() for m in marketplaces]
    })

@api.route('/notifications', methods=['GET'])
@api_login_required
def get_notifications():
    """Get user notifications."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    status = request.args.get('status', 'unread')
    
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    notifications = query.order_by(Notification.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'status': 'success',
        'data': {
            'items': [n.to_dict() for n in notifications.items],
            'page': notifications.page,
            'per_page': notifications.per_page,
            'total': notifications.total,
            'pages': notifications.pages
        }
    })

@api.route('/notifications/read-all', methods=['POST'])
@api_login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    updated = Notification.query.filter_by(
        user_id=current_user.id,
        status='unread'
    ).update({
        'status': 'read',
        'read_at': datetime.utcnow()
    })
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'data': {
            'marked_read': updated
        }
    })

@api.route('/notifications/<int:notification_id>/read', methods=['POST'])
@api_login_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        return jsonify({
            'status': 'error',
            'message': 'Not authorized to modify this notification',
            'code': 403
        }), 403
    
    notification.mark_as_read()
    
    return jsonify({
        'status': 'success',
        'data': notification.to_dict()
    })

@api.route('/profile', methods=['GET', 'PUT'])
@api_login_required
def profile():
    """Get or update user profile."""
    if request.method == 'GET':
        return jsonify({
            'status': 'success',
            'data': {
                'id': current_user.id,
                'email': current_user.email,
                'username': current_user.username,
                'created_at': current_user.created_at.isoformat(),
                'last_login_at': current_user.last_login_at.isoformat() if current_user.last_login_at else None,
                'is_active': current_user.is_active,
                'roles': [role.name for role in current_user.roles]
            }
        })
    
    # Handle PUT request
    data = request.get_json() or {}
    
    # Update user profile
    if 'username' in data and data['username'] != current_user.username:
        # Check if username is taken
        if User.query.filter(User.id != current_user.id, User.username == data['username']).first():
            return jsonify({
                'status': 'error',
                'message': 'Username already in use',
                'code': 400
            }), 400
        current_user.username = data['username']
    
    # Update password if provided
    if 'current_password' in data and 'new_password' in data:
        if not current_user.check_password(data['current_password']):
            return jsonify({
                'status': 'error',
                'message': 'Current password is incorrect',
                'code': 400
            }), 400
        current_user.password = data['new_password']
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Profile updated successfully'
    })

@api.route('/activity', methods=['GET'])
@api_login_required
def get_activity():
    """Get user activity log."""
    # In a real application, you would query an activity log table
    # For now, we'll return a placeholder
    return jsonify({
        'status': 'success',
        'data': {
            'items': [],
            'page': 1,
            'per_page': 10,
            'total': 0,
            'pages': 0
        }
    })
