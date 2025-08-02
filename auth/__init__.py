"""Authentication blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import db, User, Role, Notification
from ..forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from ..utils import send_email, log_activity
from datetime import datetime
import logging

# Create blueprint
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            log_activity('login_failed', f"Failed login attempt for {form.email.data}")
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account is disabled. Please contact support.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Update user login info
        user.last_login_at = datetime.utcnow()
        user.current_login_at = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        user.current_login_ip = request.remote_addr
        
        # If this is the first login, show welcome message
        if user.login_count == 1:
            Notification.create_welcome_notification(user)
        
        db.session.commit()
        
        login_user(user, remember=form.remember_me.data)
        log_activity('login_success', f"User {user.email} logged in")
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
@login_required
def logout():
    """User logout."""
    log_activity('logout', f"User {current_user.email} logged out")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please use a different email.', 'warning')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken. Please choose a different one.', 'warning')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            email=form.email.data.lower(),
            username=form.username.data,
            password=form.password.data
        )
        
        # Add default role
        default_role = Role.query.filter_by(name='user').first()
        if default_role:
            user.roles.append(default_role)
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email
        try:
            send_email(
                subject='Welcome to Super Arbitrage!',
                recipients=[user.email],
                text_body=render_template('email/welcome.txt', user=user),
                html_body=render_template('email/welcome.html', user=user)
            )
        except Exception as e:
            current_app.logger.error(f'Failed to send welcome email: {str(e)}')
        
        # Create welcome notification
        Notification.create_welcome_notification(user)
        
        # Log the user in
        login_user(user)
        log_activity('registration', f'New user registered: {user.email}')
        
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate password reset token
            from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
            s = Serializer(current_app.config['SECRET_KEY'], expires_in=3600)  # 1 hour expiration
            token = s.dumps({'user_id': user.id}).decode('utf-8')
            
            # Send password reset email
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            try:
                send_email(
                    subject='Reset Your Password',
                    recipients=[user.email],
                    text_body=render_template('email/reset_password.txt',
                                           user=user, reset_url=reset_url),
                    html_body=render_template('email/reset_password.html',
                                           user=user, reset_url=reset_url)
                )
                flash('Check your email for instructions to reset your password', 'info')
            except Exception as e:
                current_app.logger.error(f'Failed to send password reset email: {str(e)}')
                flash('Failed to send password reset email. Please try again later.', 'danger')
        else:
            # Don't reveal that the email doesn't exist
            flash('If your email is registered, you will receive a password reset link.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html',
                         title='Reset Password', form=form)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Verify token
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
    from itsdangerous import SignatureExpired, BadSignature
    s = Serializer(current_app.config['SECRET_KEY'])
    
    try:
        data = s.loads(token)
        user = User.query.get(data.get('user_id'))
        
        if not user:
            flash('Invalid or expired token.', 'danger')
            return redirect(url_for('auth.login'))
        
        form = ResetPasswordForm()
        if form.validate_on_submit():
            # Update password
            user.password = form.password.data
            db.session.commit()
            
            # Log the password reset
            log_activity('password_reset', f'Password reset for user: {user.email}')
            
            flash('Your password has been reset. Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        
        return render_template('auth/reset_password.html', form=form, token=token)
    
    except (SignatureExpired, BadSignature):
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

@auth.route('/confirm-email/<token>')
def confirm_email(token):
    """Confirm email with token."""
    if current_user.is_authenticated and current_user.email_confirmed:
        return redirect(url_for('main.dashboard'))
    
    # Verify token
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
    from itsdangerous import SignatureExpired, BadSignature
    s = Serializer(current_app.config['SECRET_KEY'])
    
    try:
        data = s.loads(token)
        user = User.query.get(data.get('user_id'))
        
        if not user:
            flash('Invalid or expired confirmation link.', 'danger')
            return redirect(url_for('main.index'))
        
        if user.email_confirmed:
            flash('Account already confirmed. Please log in.', 'info')
            return redirect(url_for('auth.login'))
        
        # Confirm email
        user.email_confirmed = True
        user.email_confirmed_on = datetime.utcnow()
        db.session.commit()
        
        # Log the confirmation
        log_activity('email_confirmed', f'Email confirmed for user: {user.email}')
        
        flash('Thank you for confirming your email address!', 'success')
        return redirect(url_for('main.dashboard'))
    
    except (SignatureExpired, BadSignature):
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))

@auth.route('/resend-confirmation')
@login_required
def resend_confirmation():
    """Resend email confirmation."""
    if current_user.email_confirmed:
        flash('Your email is already confirmed.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Generate confirmation token
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
    s = Serializer(current_app.config['SECRET_KEY'], expires_in=86400)  # 24 hours
    token = s.dumps({'user_id': current_user.id}).decode('utf-8')
    
    # Send confirmation email
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    
    try:
        send_email(
            subject='Confirm Your Email',
            recipients=[current_user.email],
            text_body=render_template('email/confirm_email.txt',
                                   user=current_user, confirm_url=confirm_url),
            html_body=render_template('email/confirm_email.html',
                                   user=current_user, confirm_url=confirm_url)
        )
        flash('A new confirmation email has been sent. Please check your inbox.', 'info')
    except Exception as e:
        current_app.logger.error(f'Failed to send confirmation email: {str(e)}')
        flash('Failed to send confirmation email. Please try again later.', 'danger')
    
    return redirect(url_for('main.dashboard'))
