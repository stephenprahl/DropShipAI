"""Command-line interface commands for the application."""
import click
from flask import current_app
from flask.cli import with_appcontext
from .extensions import db
from .models import User, Role, Marketplace
import json
import os
from datetime import datetime


def register_commands(app):
    ""Register Click commands with the Flask application."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(import_marketplaces_command)
    app.cli.add_command(clear_cache_command)
    app.cli.add_command(generate_api_key_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database."""
    try:
        db.create_all()
        click.echo('Initialized the database.')
        
        # Create default roles if they don't exist
        roles = [
            ('admin', 'Administrator with full access'),
            ('user', 'Regular user'),
            ('api', 'API user with limited access')
        ]
        
        for name, description in roles:
            if not Role.query.filter_by(name=name).first():
                role = Role(name=name, description=description)
                db.session.add(role)
        
        db.session.commit()
        click.echo('Created default roles.')
        
    except Exception as e:
        click.echo(f'Error initializing database: {str(e)}', err=True)


@click.command('create-user')
@click.argument('username')
@click.argument('email')
@click.argument('password')
@click.option('--admin', is_flag=True, help='Make the user an admin')
@with_appcontext
def create_user_command(username, email, password, admin):
    """Create a new user."""
    try:
        if User.query.filter_by(email=email).first():
            click.echo(f'User with email {email} already exists.', err=True)
            return
            
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        
        if admin:
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin', description='Administrator with full access')
                db.session.add(admin_role)
            user.roles.append(admin_role)
        
        db.session.commit()
        click.echo(f'Created user: {username} (Admin: {admin})')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating user: {str(e)}', err=True)


@click.command('import-marketplaces')
@click.argument('filename', type=click.Path(exists=True))
@with_appcontext
def import_marketplaces_command(filename):
    """Import marketplaces from a JSON file."""
    try:
        with open(filename, 'r') as f:
            marketplaces = json.load(f)
            
        count = 0
        for data in marketplaces:
            if not Marketplace.query.filter_by(code=data['code']).first():
                marketplace = Marketplace(
                    name=data['name'],
                    code=data['code'],
                    base_url=data.get('base_url', ''),
                    logo_url=data.get('logo_url', ''),
                    is_active=data.get('is_active', True),
                    requires_api=data.get('requires_api', False)
                )
                db.session.add(marketplace)
                count += 1
                
        db.session.commit()
        click.echo(f'Imported {count} marketplaces.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error importing marketplaces: {str(e)}', err=True)


@click.command('clear-cache')
@with_appcontext
def clear_cache_command():
    """Clear the application cache."""
    try:
        cache.clear()
        click.echo('Cache cleared.')
    except Exception as e:
        click.echo(f'Error clearing cache: {str(e)}', err=True)


@click.command('generate-api-key')
@click.argument('user_email')
@with_appcontext
def generate_api_key_command(user_email):
    """Generate a new API key for a user."""
    try:
        user = User.query.filter_by(email=user_email).first()
        if not user:
            click.echo(f'User with email {user_email} not found.', err=True)
            return
            
        # Generate a secure API key
        import secrets
        api_key = secrets.token_urlsafe(32)
        
        # In a real app, you would store the hashed API key
        # For simplicity, we'll just print it here
        click.echo(f'API Key for {user.email}: {api_key}')
        click.echo('IMPORTANT: Store this key securely. It will not be shown again.')
        
    except Exception as e:
        click.echo(f'Error generating API key: {str(e)}', err=True)
