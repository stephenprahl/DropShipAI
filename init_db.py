import os
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)
os.makedirs('data/opportunities', exist_ok=True)

# Connect to SQLite database (creates it if it doesn't exist)
conn = sqlite3.connect('data/arbitrage.db')
cursor = conn.cursor()

# Enable foreign key support
cursor.execute('PRAGMA foreign_keys = ON')

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0
)
''')

# Create products table
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT UNIQUE,
    price DECIMAL(10, 2),
    source_marketplace TEXT,
    source_id TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_marketplace, source_id)
)
''')

# Create arbitrage_opportunities table
cursor.execute('''
CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_product_id INTEGER,
    target_marketplace TEXT NOT NULL,
    target_url TEXT,
    target_price DECIMAL(10, 2),
    target_fees DECIMAL(10, 2),
    estimated_profit DECIMAL(10, 2),
    profit_margin DECIMAL(5, 2),
    status TEXT DEFAULT 'potential',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_product_id) REFERENCES products (id) ON DELETE CASCADE,
    CHECK (status IN ('potential', 'active', 'sold', 'unavailable'))
)
''')

# Create price_history table
try:
    cursor.execute('''
    CREATE TABLE price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
    )
    ''')
    print("Created price_history table")
except sqlite3.OperationalError:
    print("price_history table already exists")

# Create an admin user (change the password in production!)
admin_username = 'admin'
admin_email = 'admin@example.com'
admin_password = 'Admin@123'  # Change this in production!
admin_password_hash = generate_password_hash(admin_password)

try:
    cursor.execute(
        'INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)',
        (admin_username, admin_email, admin_password_hash, 1)
    )
    print(f"Created admin user: {admin_username}")
    print(f"Password: {admin_password} (change this immediately!)")
except sqlite3.IntegrityError:
    print("Admin user already exists")

# Create triggers for updated_at timestamps
cursor.execute('''
CREATE TRIGGER IF NOT EXISTS update_products_timestamp
AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS update_opportunities_timestamp
AFTER UPDATE ON arbitrage_opportunities
BEGIN
    UPDATE arbitrage_opportunities SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
''')

# Create indexes for better query performance
cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_marketplace, source_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_opportunities_status ON arbitrage_opportunities(status)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_opportunities_profit ON arbitrage_opportunities(estimated_profit)')

# Commit changes and close connection
conn.commit()
conn.close()

print("Database initialized successfully at data/arbitrage.db")
print("Database schema includes tables: users, products, arbitrage_opportunities, price_history")
