from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, db
import re

auth = Blueprint('auth', __name__)

def is_valid_username(username):
    """Check if username contains only letters, numbers, and underscores."""
    return bool(re.match(r'^\w+$', username))

def is_valid_password(password):
    """Check if password meets complexity requirements."""
    return bool(re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$', password))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
        else:
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                user.update_last_login()
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.dashboard'))
            else:
                flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
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
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists', 'error')
        else:
            try:
                user = User(username=username, email=email, password=password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash('Registration successful!', 'success')
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred. Please try again.', 'error')
                print(f"Error during registration: {e}")
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
