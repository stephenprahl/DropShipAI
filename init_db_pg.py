import os
from werkzeug.security import generate_password_hash
from app import create_app, db
from models import User, Product

def init_db():
    """Initialize the database with required tables and admin user."""
    app = create_app('development')
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                password='Admin@123'  # Change this in production!
            )
            db.session.add(admin)
            db.session.commit()
            print("Created admin user")
            print(f"Username: admin")
            print(f"Password: Admin@123")  # Change this in production!
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    init_db()
