import os
import sqlite3
from werkzeug.security import generate_password_hash

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

# Connect to SQLite database (creates it if it doesn't exist)
conn = sqlite3.connect('data/arbitrage.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
)
''')

# Create other necessary tables (you can add more as needed)
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT,
    price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Create an admin user (change the password in production!)
admin_username = 'admin'
admin_email = 'admin@example.com'
admin_password = 'Admin@123'  # Change this in production!
admin_password_hash = generate_password_hash(admin_password)

try:
    cursor.execute(
        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
        (admin_username, admin_email, admin_password_hash)
    )
    print(f"Created admin user: {admin_username}")
    print(f"Password: {admin_password} (change this immediately!)")
except sqlite3.IntegrityError:
    print("Admin user already exists")

# Commit changes and close connection
conn.commit()
conn.close()

print("Database initialized successfully at data/arbitrage.db")
