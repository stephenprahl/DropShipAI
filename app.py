"""
Super Arbitrage Web Interface

A Flask-based web application for the Super Arbitrage platform.
"""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from pathlib import Path

# Import our arbitrage engine
from src.arbitrage_engine import ArbitrageEngine, ArbitrageOpportunity

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-key-for-super-arbitrage'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuration
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / 'users.json'

# Initialize arbitrage engine
arbitrage_engine = ArbitrageEngine(data_dir=DATA_DIR)

# User class for authentication
class User:
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash
        self.is_authenticated = False
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.username

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Load users from JSON file
def load_users():
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_user(username, password):
    users = load_users()
    users[username] = generate_password_hash(password)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

@login_manager.user_loader
def load_user(username):
    users = load_users()
    if username not in users:
        return None
    user = User(username, users[username])
    user.is_authenticated = True
    return user

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_users()
        if username in users and check_password_hash(users[username], password):
            user = User(username, users[username])
            user.is_authenticated = True
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        users = load_users()
        if username in users:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        save_user(username, password)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Load recent opportunities
    opportunities_dir = DATA_DIR / 'opportunities'
    opportunities = []
    
    if opportunities_dir.exists():
        for file in sorted(opportunities_dir.glob('*.json'), key=os.path.getmtime, reverse=True)[:5]:
            with open(file, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        opportunities.extend(data[:3])  # Show top 3 from each file
                except json.JSONDecodeError:
                    continue
    
    return render_template('dashboard.html', opportunities=opportunities[:10])

@app.route('/find', methods=['GET', 'POST'])
@login_required
def find():
    if request.method == 'POST':
        source = request.form.get('source')
        target = request.form.get('target')
        query = request.form.get('query')
        min_profit = float(request.form.get('min_profit', 10.0))
        min_margin = float(request.form.get('min_margin', 20.0))
        max_results = int(request.form.get('max_results', 20))
        
        # Run the arbitrage search
        opportunities = arbitrage_engine.find_opportunities(
            source_platform=source,
            target_platform=target,
            query=query,
            min_profit=min_profit,
            min_margin=min_margin,
            max_results=max_results
        )
        
        # Save the results
        if opportunities:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"opportunities_{timestamp}.json"
            arbitrage_engine.save_opportunities(opportunities, filename)
            flash(f'Found {len(opportunities)} opportunities!', 'success')
        else:
            flash('No opportunities found with the current criteria.', 'warning')
        
        return render_template('results.html', 
                             opportunities=opportunities,
                             source=source,
                             target=target,
                             query=query)
    
    return render_template('find.html')

@app.route('/opportunities')
@login_required
def opportunities():
    # List all saved opportunities
    opportunities_dir = DATA_DIR / 'opportunities'
    opportunity_files = []
    
    if opportunities_dir.exists():
        opportunity_files = sorted(
            opportunities_dir.glob('*.json'),
            key=os.path.getmtime,
            reverse=True
        )
    
    return render_template('opportunities.html', opportunity_files=opportunity_files)

@app.route('/opportunity/<filename>')
@login_required
def view_opportunity(filename):
    filepath = DATA_DIR / 'opportunities' / filename
    if not filepath.exists() or '..' in filename or not filepath.is_file():
        flash('Opportunity not found', 'danger')
        return redirect(url_for('opportunities'))
    
    with open(filepath, 'r') as f:
        opportunities = json.load(f)
    
    return render_template('view_opportunity.html', 
                         opportunities=opportunities,
                         filename=filename)

# API Endpoints
@app.route('/api/opportunities', methods=['GET'])
@login_required
def api_opportunities():
    source = request.args.get('source')
    target = request.args.get('target')
    query = request.args.get('query')
    min_profit = float(request.args.get('min_profit', 10.0))
    min_margin = float(request.args.get('min_margin', 20.0))
    max_results = int(request.args.get('max_results', 20))
    
    opportunities = arbitrage_engine.find_opportunities(
        source_platform=source,
        target_platform=target,
        query=query,
        min_profit=min_profit,
        min_margin=min_margin,
        max_results=max_results
    )
    
    # Convert opportunities to dict for JSON serialization
    opportunities_data = [
        {
            'title': opp.source_product.get('title', 'No title'),
            'source_price': f"${opp.source_product.get('price', 0):.2f}",
            'target_price': f"${opp.target_price:.2f}",
            'profit': f"${opp.profit:.2f}",
            'profit_margin': f"{opp.profit_margin:.1f}%",
            'source_url': opp.source_product.get('url', '#')
        }
        for opp in opportunities
    ]
    
    return jsonify({
        'success': True,
        'count': len(opportunities_data),
        'opportunities': opportunities_data
    })

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    # Generate a unique error ID for support reference
    error_id = str(uuid.uuid4())
    return render_template('errors/500.html', error_id=error_id), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(429)
def ratelimit_error(error):
    return render_template('errors/429.html'), 429


if __name__ == '__main__':
    # Create necessary directories
    (DATA_DIR / 'opportunities').mkdir(exist_ok=True, parents=True)
    
    # Run the app
    app.run(debug=True)
