"""Admin interface for the Super Arbitrage application."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from ..models import db, User, Role, Marketplace, Product, ArbitrageOpportunity, Notification
from ..forms import ImportProductsForm, MarketplaceCredentialsForm, APIKeyForm
from ..utils import admin_required, log_activity
from werkzeug.utils import secure_filename
import os
import csv
from datetime import datetime

# Create admin blueprint
admin = Blueprint('admin', __name__)

@admin.before_request
@login_required
@admin_required
def before_request():
    """Protect all admin endpoints."""
    pass

@admin.route('/')
def index():
    """Admin dashboard."""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_products': Product.query.count(),
        'total_opportunities': ArbitrageOpportunity.query.count(),
        'active_marketplaces': Marketplace.query.filter_by(is_active=True).count()
    }
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_opportunities = (ArbitrageOpportunity.query
                          .order_by(ArbitrageOpportunity.created_at.desc())
                          .limit(5)
                          .all())
    
    return render_template('admin/index.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_opportunities=recent_opportunities)

@admin.route('/users')
def users():
    """List all users."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    
    query = User.query
    
    # Apply filters
    if 'status' in request.args and request.args['status'] != 'all':
        query = query.filter_by(is_active=(request.args['status'] == 'active'))
    
    if 'role' in request.args and request.args['role'] != 'all':
        role = Role.query.filter_by(name=request.args['role']).first()
        if role:
            query = query.filter(User.roles.any(id=role.id))
    
    if 'search' in request.args:
        search = f"%{request.args['search']}%"
        query = query.filter(
            (User.username.ilike(search)) |
            (User.email.ilike(search))
        )
    
    # Order and paginate
    users = query.order_by(User.created_at.desc())\
                .paginate(page=page, per_page=per_page, error_out=False)
    
    roles = Role.query.all()
    
    return render_template('admin/users.html',
                         users=users,
                         roles=roles)

@admin.route('/user/<int:user_id>')
def view_user(user_id):
    """View user details."""
    user = User.query.get_or_404(user_id)
    
    # Get user statistics
    stats = {
        'products': Product.query.filter_by(owner_id=user.id).count(),
        'opportunities': ArbitrageOpportunity.query.filter_by(user_id=user.id).count(),
        'active_opportunities': ArbitrageOpportunity.query.filter_by(
            user_id=user.id,
            status='active'
        ).count(),
        'total_profit': db.session.query(
            db.func.sum(ArbitrageOpportunity.profit)
        ).filter(
            ArbitrageOpportunity.user_id == user.id,
            ArbitrageOpportunity.status == 'completed'
        ).scalar() or 0
    }
    
    # Get recent activity
    recent_activity = Notification.query\
        .filter_by(user_id=user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(10)\
        .all()
    
    return render_template('admin/view_user.html',
                         user=user,
                         stats=stats,
                         recent_activity=recent_activity)

@admin.route('/marketplaces')
def marketplaces():
    """List all marketplaces."""
    marketplaces = Marketplace.query.order_by(Marketplace.name).all()
    return render_template('admin/marketplaces.html',
                         marketplaces=marketplaces)

@admin.route('/marketplace/<int:marketplace_id>')
def view_marketplace(marketplace_id):
    """View marketplace details."""
    marketplace = Marketplace.query.get_or_404(marketplace_id)
    
    # Get marketplace statistics
    stats = {
        'products': Product.query.join(Product.prices)\
                               .filter_by(marketplace_id=marketplace_id)\
                               .distinct()\
                               .count(),
        'opportunities': ArbitrageOpportunity.query.filter(
            (ArbitrageOpportunity.source_marketplace_id == marketplace_id) |
            (ArbitrageOpportunity.target_marketplace_id == marketplace_id)
        ).count(),
        'active_users': User.query.join(User.products)\
                                .join(Product.prices)\
                                .filter_by(marketplace_id=marketplace_id)\
                                .distinct()\
                                .count()
    }
    
    # Get recent activity
    recent_products = (Product.query.join(Product.prices)
                      .filter_by(marketplace_id=marketplace_id)
                      .order_by(Product.updated_at.desc())
                      .limit(5)
                      .all())
    
    return render_template('admin/view_marketplace.html',
                         marketplace=marketplace,
                         stats=stats,
                         recent_products=recent_products)

@admin.route('/import-products', methods=['GET', 'POST'])
def import_products():
    """Import products from CSV."""
    form = ImportProductsForm()
    
    if form.validate_on_submit():
        marketplace = Marketplace.query.get(form.marketplace_id.data)
        if not marketplace:
            flash('Invalid marketplace selected.', 'danger')
            return redirect(url_for('admin.import_products'))
        
        file = form.import_file.data
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(url_for('admin.import_products'))
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'imports')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}")
        file.save(filepath)
        
        # Process the CSV file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                required_fields = ['name', 'price', 'url']
                
                # Check for required fields
                if not all(field in reader.fieldnames for field in required_fields):
                    flash('CSV file is missing required fields.', 'danger')
                    return redirect(url_for('admin.import_products'))
                
                # Process each row
                imported = 0
                updated = 0
                for row in reader:
                    # Check if product already exists
                    product = Product.query.filter_by(
                        marketplace_id=marketplace.id,
                        external_id=row.get('id', '')
                    ).first()
                    
                    if product and form.update_existing.data:
                        # Update existing product
                        product.name = row['name']
                        product.price = float(row['price'])
                        product.url = row['url']
                        product.updated_at = datetime.utcnow()
                        updated += 1
                    elif not product:
                        # Create new product
                        product = Product(
                            name=row['name'],
                            price=float(row['price']),
                            url=row['url'],
                            marketplace_id=marketplace.id,
                            external_id=row.get('id'),
                            image_url=row.get('image_url'),
                            category=row.get('category'),
                            brand=row.get('brand')
                        )
                        db.session.add(product)
                        imported += 1
                
                db.session.commit()
                
                flash(f'Successfully imported {imported} products and updated {updated} products.', 'success')
                log_activity('import_products', f'Imported {imported} products from {marketplace.name}')
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error importing products: {str(e)}')
            flash('An error occurred while importing products. Please check the file format and try again.', 'danger')
        
        return redirect(url_for('admin.products'))
    
    return render_template('admin/import_products.html', form=form)

@admin.route('/settings', methods=['GET', 'POST'])
def settings():
    """Admin settings."""
    form = MarketplaceCredentialsForm()
    
    if form.validate_on_submit():
        # Save marketplace credentials
        credentials = {
            'api_key': form.api_key.data,
            'api_secret': form.api_secret.data,
            'seller_id': form.seller_id.data,
            'is_active': form.is_active.data,
            'updated_at': datetime.utcnow()
        }
        
        # In a real app, you would encrypt sensitive data before saving
        marketplace = Marketplace.query.get(form.marketplace_id.data)
        if marketplace:
            marketplace.credentials = credentials
            db.session.commit()
            flash(f'Credentials for {marketplace.name} have been updated.', 'success')
            log_activity('update_credentials', f'Updated credentials for {marketplace.name}')
        else:
            flash('Invalid marketplace selected.', 'danger')
        
        return redirect(url_for('admin.settings'))
    
    # Load existing credentials for the first marketplace by default
    marketplace = Marketplace.query.first()
    if marketplace and marketplace.credentials:
        form.api_key.data = marketplace.credentials.get('api_key', '')
        form.seller_id.data = marketplace.credentials.get('seller_id', '')
        form.is_active.data = marketplace.credentials.get('is_active', False)
    
    return render_template('admin/settings.html', form=form)

@admin.route('/api/keys', methods=['GET', 'POST'])
def api_keys():
    """Manage API keys."""
    form = APIKeyForm()
    
    if form.validate_on_submit():
        # Generate a new API key
        from ..utils import generate_api_key
        
        expires_in = int(form.expires_in.data) if form.expires_in.data != '0' else None
        api_key = generate_api_key(current_user.id, expires_in=expires_in)
        
        # Save the API key to the database
        from ..models import APIKey
        
        key = APIKey(
            user_id=current_user.id,
            name=form.name.data,
            key=api_key,
            permissions=form.permissions.data,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
        )
        
        db.session.add(key)
        db.session.commit()
        
        flash('API key generated successfully!', 'success')
        log_activity('generate_api_key', 'Generated new API key')
        
        # Show the API key to the user (only once)
        return render_template('admin/api_key_generated.html', api_key=api_key)
    
    # List existing API keys
    api_keys = current_user.api_keys.order_by(APIKey.created_at.desc()).all()
    
    return render_template('admin/api_keys.html',
                         form=form,
                         api_keys=api_keys)

@admin.route('/api/keys/<int:key_id>/revoke', methods=['POST'])
def revoke_api_key(key_id):
    """Revoke an API key."""
    from ..models import APIKey
    
    key = APIKey.query.get_or_404(key_id)
    
    # Ensure the user owns the key or is an admin
    if key.user_id != current_user.id and not current_user.has_role('admin'):
        flash('You do not have permission to revoke this key.', 'danger')
        return redirect(url_for('admin.api_keys'))
    
    db.session.delete(key)
    db.session.commit()
    
    flash('API key has been revoked.', 'success')
    log_activity('revoke_api_key', f'Revoked API key: {key.name}')
    
    return redirect(url_for('admin.api_keys'))

@admin.route('/system/logs')
def system_logs():
    """View system logs."""
    log_file = os.path.join(current_app.instance_path, 'logs', 'superarbitrage.log')
    
    try:
        with open(log_file, 'r') as f:
            logs = f.read().split('\n')
        logs = [log for log in logs if log.strip()][-1000:]  # Show last 1000 lines
    except FileNotFoundError:
        logs = ["No log file found."]
    
    return render_template('admin/system_logs.html', logs=logs)

@admin.route('/system/status')
def system_status():
    """View system status."""
    import psutil
    import platform
    from datetime import datetime
    
    # System information
    system_info = {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'uptime': str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())),
        'process_uptime': str(datetime.now() - datetime.fromtimestamp(psutil.Process().create_time()))
    }
    
    # Database status
    try:
        db_status = 'Connected'
        db_version = db.session.execute('SELECT version()').scalar()
    except Exception as e:
        db_status = f'Error: {str(e)}'
        db_version = 'Unknown'
    
    # Background tasks status
    # This would depend on your task queue implementation (Celery, RQ, etc.)
    tasks_status = {
        'queue': 'Not implemented',
        'workers': 'Not implemented',
        'scheduled': 'Not implemented'
    }
    
    return render_template('admin/system_status.html',
                         system_info=system_info,
                         db_status=db_status,
                         db_version=db_version,
                         tasks_status=tasks_status)
