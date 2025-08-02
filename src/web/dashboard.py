from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
import sqlite3
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Calculate the paths relative to this file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR,
            static_url_path='/static')
CORS(app)
app.secret_key = os.urandom(24)  # Required for session management

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username=None, email=None):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user is None:
        return None
    return User(id=user['id'], username=user['username'], email=user['email'])

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def is_valid_username(username):
    """Check if username contains only letters, numbers, and underscores."""
    return bool(re.match(r'^\w+$', username))

def is_valid_password(password):
    """Check if password meets complexity requirements."""
    return bool(re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$', password))

def user_exists(username, email):
    """Check if a user with the given username or email already exists."""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT id FROM users WHERE username = ? OR email = ?', 
        (username, email)
    ).fetchone()
    conn.close()
    return user is not None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validate input
        if not all([username, email, password]):
            flash('All fields are required', 'error')
        elif not is_valid_username(username):
            flash('Username can only contain letters, numbers, and underscores', 'error')
        elif not is_valid_password(password):
            flash('Password must be at least 8 characters long and include uppercase, lowercase, and numbers', 'error')
        elif user_exists(username, email):
            flash('Username or email already exists', 'error')
        else:
            # Hash the password
            password_hash = generate_password_hash(password)
            
            # Save to database
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                    (username, email, password_hash)
                )
                user_id = cursor.lastrowid
                conn.commit()
                
                # Log the user in
                user = User(id=user_id, username=username, email=email)
                login_user(user)
                flash('Registration successful!', 'success')
                return redirect(url_for('dashboard'))
                
            except sqlite3.IntegrityError as e:
                flash('An error occurred. Please try again.', 'error')
                print(f"Database error: {e}")
            finally:
                conn.close()
    
    return render_template('register.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
        else:
            # Get user from database
            user_data = get_user_by_username(username)
            
            # Check if user exists and password is correct
            if user_data and check_password_hash(user_data['password_hash'], password):
                user = User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email']
                )
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
    
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Configuration
DATABASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'arbitrage.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/opportunities')
def get_opportunities():
    min_profit = request.args.get('min_profit', 20, type=float)
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ao.*, p.title, p.url as source_url, p.price as source_price
        FROM arbitrage_opportunities ao
        JOIN products p ON ao.source_product_id = p.id
        WHERE ao.is_active = 1 AND ao.profit_margin >= ?
        ORDER BY ao.roi DESC, ao.profit_margin DESC
        LIMIT ?
    ''', (min_profit, limit))
    
    opportunities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(opportunities)

@app.route('/api/orders')
def get_orders():
    limit = request.args.get('limit', 10, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT o.*, p.title as product_title
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        ORDER BY o.created_at DESC
        LIMIT ?
    ''', (limit,))
    
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(orders)

@app.route('/api/metrics')
def get_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as active_listings FROM listings WHERE status = 'active'")
    active_listings = cursor.fetchone()['active_listings']
    
    cursor.execute('''
        SELECT COALESCE(SUM(sale_price - (SELECT price FROM products WHERE id = product_id) - fees), 0) as total_profit
        FROM sales_history
        WHERE strftime('%Y-%m', sale_date) = strftime('%Y-%m', 'now')
    ''')
    monthly_profit = cursor.fetchone()['total_profit']
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'active_listings': active_listings,
        'monthly_profit': monthly_profit
    })

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    
    # Create simple HTML template
    with open('templates/index.html', 'w') as f:
        f.write('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SuperArb Dashboard</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100">
            <div class="container mx-auto p-4">
                <h1 class="text-2xl font-bold mb-4">SuperArb Dashboard</h1>
                <div id="metrics" class="grid grid-cols-2 gap-4 mb-6">
                    <!-- Metrics will be loaded here -->
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div class="bg-white p-4 rounded shadow">
                        <h2 class="text-xl font-semibold mb-2">Top Opportunities</h2>
                        <div id="opportunities">Loading...</div>
                    </div>
                    <div class="bg-white p-4 rounded shadow">
                        <h2 class="text-xl font-semibold mb-2">Recent Orders</h2>
                        <div id="orders">Loading...</div>
                    </div>
                </div>
            </div>
            <script>
                // Load data when page loads
                Promise.all([
                    fetch('/api/metrics').then(r => r.json()),
                    fetch('/api/opportunities?limit=5').then(r => r.json()),
                    fetch('/api/orders?limit=5').then(r => r.json())
                ]).then(([metrics, opportunities, orders]) => {
                    // Update metrics
                    document.getElementById('metrics').innerHTML = `
                        <div class="bg-white p-4 rounded shadow">
                            <div class="text-gray-500">Active Listings</div>
                            <div class="text-2xl font-bold">${metrics.active_listings}</div>
                        </div>
                        <div class="bg-white p-4 rounded shadow">
                            <div class="text-gray-500">Monthly Profit</div>
                            <div class="text-2xl font-bold">$${metrics.monthly_profit.toFixed(2)}</div>
                        </div>
                    `;
                    
                    // Update opportunities
                    document.getElementById('opportunities').innerHTML = 
                        opportunities.map(o => `
                            <div class="border-b py-2">
                                <div class="font-medium">${o.title}</div>
                                <div class="text-sm text-gray-600">
                                    Profit: $${o.estimated_profit.toFixed(2)} (${o.profit_margin.toFixed(1)}%)
                                </div>
                            </div>
                        `).join('') || 'No opportunities found';
                    
                    // Update orders
                    document.getElementById('orders').innerHTML = 
                        orders.map(o => `
                            <div class="border-b py-2">
                                <div class="font-medium">${o.product_title || 'Order ID: ' + o.id}</div>
                                <div class="text-sm text-gray-600">
                                    $${o.total_amount?.toFixed(2) || '0.00'} • ${o.status}
                                </div>
                            </div>
                        `).join('') || 'No orders found';
                });
            </script>
        </body>
        </html>
        ''')
    
    app.run(debug=True, port=5000)
