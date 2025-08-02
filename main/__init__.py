"""Main application blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ..models import db, ArbitrageOpportunity, Product, Notification
from ..utils import admin_required

# Create blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')

@main.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    # Get recent opportunities
    recent_opportunities = (ArbitrageOpportunity.query
                          .filter_by(user_id=current_user.id)
                          .order_by(ArbitrageOpportunity.created_at.desc())
                          .limit(5)
                          .all())
    
    # Get recent notifications
    recent_notifications = (Notification.query
                          .filter_by(user_id=current_user.id)
                          .order_by(Notification.created_at.desc())
                          .limit(5)
                          .all())
    
    # Get product count
    product_count = Product.query.filter_by(owner_id=current_user.id).count()
    
    # Get active opportunity count
    opportunity_count = ArbitrageOpportunity.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).count()
    
    # Calculate 7-day profit
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_profits = (db.session.query(db.func.sum(ArbitrageOpportunity.profit))
                     .filter(
                         ArbitrageOpportunity.user_id == current_user.id,
                         ArbitrageOpportunity.status == 'completed',
                         ArbitrageOpportunity.updated_at >= week_ago
                     )
                     .scalar() or 0)
    
    return render_template('dashboard.html',
                         recent_opportunities=recent_opportunities,
                         recent_notifications=recent_notifications,
                         product_count=product_count,
                         opportunity_count=opportunity_count,
                         recent_profits=recent_profits)

@main.route('/find')
@login_required
def find():
    """Find arbitrage opportunities."""
    return render_template('find.html')

@main.route('/opportunities')
@login_required
def opportunities():
    """View all arbitrage opportunities."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    min_profit = request.args.get('min_profit', 0, type=float)
    min_margin = request.args.get('min_margin', 0, type=float)
    
    # Base query
    query = ArbitrageOpportunity.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if status != 'all':
        query = query.filter_by(status=status)
    
    if min_profit > 0:
        query = query.filter(ArbitrageOpportunity.profit >= min_profit)
    
    if min_margin > 0:
        query = query.filter(ArbitrageOpportunity.profit_margin >= min_margin)
    
    # Order and paginate
    opportunities = (query.order_by(ArbitrageOpportunity.created_at.desc())
                    .paginate(page=page, per_page=per_page, error_out=False))
    
    return render_template('opportunities.html',
                         opportunities=opportunities,
                         status=status,
                         min_profit=min_profit,
                         min_margin=min_margin)

@main.route('/opportunity/<int:opportunity_id>')
@login_required
def view_opportunity(opportunity_id):
    """View details of a specific opportunity."""
    opportunity = ArbitrageOpportunity.query.get_or_404(opportunity_id)
    
    # Ensure the user owns this opportunity
    if opportunity.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this opportunity.', 'danger')
        return redirect(url_for('main.opportunities'))
    
    # Mark notification as read if accessed from notification
    notification_id = request.args.get('notification_id')
    if notification_id:
        notification = Notification.query.get(notification_id)
        if notification and notification.user_id == current_user.id:
            notification.mark_as_read()
    
    return render_template('view_opportunity.html', opportunity=opportunity)

@main.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html')

@main.route('/settings')
@login_required
def settings():
    """User settings page."""
    return render_template('settings.html')

@main.route('/notifications')
@login_required
def notifications():
    """User notifications page."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    
    # Get filter parameters
    status = request.args.get('status', 'unread')
    
    # Base query
    query = Notification.query.filter_by(user_id=current_user.id)
    
    # Apply status filter
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Order and paginate
    notifications = (query.order_by(Notification.created_at.desc())
                    .paginate(page=page, per_page=per_page, error_out=False))
    
    # Mark all as read if requested
    if request.args.get('mark_read') == 'all':
        for notification in notifications.items:
            if notification.status != 'read':
                notification.mark_as_read(commit=False)
        db.session.commit()
        flash('All notifications marked as read.', 'success')
    
    return render_template('notifications.html',
                         notifications=notifications,
                         status=status)

@main.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    Notification.query.filter_by(user_id=current_user.id, status='unread')\
        .update({'status': 'read', 'read_at': datetime.utcnow()})
    db.session.commit()
    
    if request.is_json:
        return jsonify({'status': 'success'})
    
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    # Ensure the notification belongs to the current user
    if notification.user_id != current_user.id:
        if request.is_json:
            return jsonify({'error': 'Unauthorized'}), 403
        flash('You do not have permission to modify this notification.', 'danger')
        return redirect(url_for('main.notifications'))
    
    notification.mark_as_read()
    
    if request.is_json:
        return jsonify({'status': 'success'})
    
    return redirect(notification.action_url or url_for('main.notifications'))
