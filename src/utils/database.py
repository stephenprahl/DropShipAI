import sqlite3
from sqlite3 import Error
from datetime import datetime
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = 'data/arbitrage.db'):
        """Initialize the database connection."""
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _get_connection(self):
        """Get a database connection."""
        try:
            if self.conn is None:
                # Create data directory if it doesn't exist
                Path('data').mkdir(exist_ok=True)
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
            return self.conn
        except Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def _init_db(self):
        """Initialize the database with required tables."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Products table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_platform TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                original_price REAL,
                currency TEXT DEFAULT 'USD',
                url TEXT NOT NULL,
                image_url TEXT,
                category TEXT,
                brand TEXT,
                model TEXT,
                condition TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_platform, source_id)
            )
            ''')
            
            # Sellers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sellers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                name TEXT,
                rating REAL,
                total_ratings INTEGER,
                positive_feedback_percent REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, seller_id)
            )
            ''')
            
            # Product_sellers junction table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_sellers (
                product_id INTEGER,
                seller_id INTEGER,
                price REAL NOT NULL,
                shipping_price REAL DEFAULT 0,
                is_available BOOLEAN DEFAULT 1,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_id, seller_id),
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (seller_id) REFERENCES sellers (id)
            )
            ''')
            
            # Arbitrage_opportunities table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_product_id INTEGER NOT NULL,
                target_platform TEXT NOT NULL,
                estimated_selling_price REAL NOT NULL,
                estimated_fees REAL NOT NULL,
                estimated_profit REAL NOT NULL,
                profit_margin REAL NOT NULL,
                roi REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_product_id) REFERENCES products (id)
            )
            ''')
            
            # Sales_history table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                sale_price REAL NOT NULL,
                quantity INTEGER DEFAULT 1,
                fees REAL NOT NULL,
                shipping_cost REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_platform, source_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_arbitrage_opportunities ON arbitrage_opportunities(is_active, profit_margin)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_history ON sales_history(product_id, sale_date)')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except Error as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def add_or_update_product(self, product_data: dict) -> int:
        """
        Add a new product or update an existing one.
        Returns the product ID.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if product exists
            cursor.execute(
                'SELECT id FROM products WHERE source_platform = ? AND source_id = ?',
                (product_data['source_platform'], product_data['source_id'])
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing product
                product_id = existing['id']
                update_fields = []
                update_values = []
                
                for field in ['title', 'description', 'price', 'original_price', 'url', 
                             'image_url', 'category', 'brand', 'model', 'condition']:
                    if field in product_data and product_data[field] is not None:
                        update_fields.append(f"{field} = ?")
                        update_values.append(product_data[field])
                
                if update_fields:
                    update_query = f"""
                    UPDATE products 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """
                    cursor.execute(update_query, (*update_values, product_id))
            else:
                # Insert new product
                cursor.execute('''
                INSERT INTO products 
                (source_platform, source_id, title, description, price, original_price, 
                 currency, url, image_url, category, brand, model, condition)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_data['source_platform'],
                    product_data['source_id'],
                    product_data.get('title', ''),
                    product_data.get('description'),
                    product_data['price'],
                    product_data.get('original_price', product_data['price']),
                    product_data.get('currency', 'USD'),
                    product_data['url'],
                    product_data.get('image_url'),
                    product_data.get('category'),
                    product_data.get('brand'),
                    product_data.get('model'),
                    product_data.get('condition')
                ))
                product_id = cursor.lastrowid
            
            conn.commit()
            return product_id
            
        except Error as e:
            logger.error(f"Error adding/updating product: {e}")
            conn.rollback()
            raise
    
    def add_seller(self, seller_data: dict) -> int:
        """
        Add a new seller or update an existing one.
        Returns the seller ID.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if seller exists
            cursor.execute(
                'SELECT id FROM sellers WHERE platform = ? AND seller_id = ?',
                (seller_data['platform'], seller_data['seller_id'])
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing seller
                seller_id = existing['id']
                update_fields = []
                update_values = []
                
                for field in ['name', 'rating', 'total_ratings', 'positive_feedback_percent']:
                    if field in seller_data and seller_data[field] is not None:
                        update_fields.append(f"{field} = ?")
                        update_values.append(seller_data[field])
                
                if update_fields:
                    update_query = f"""
                    UPDATE sellers 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """
                    cursor.execute(update_query, (*update_values, seller_id))
            else:
                # Insert new seller
                cursor.execute('''
                INSERT INTO sellers 
                (platform, seller_id, name, rating, total_ratings, positive_feedback_percent)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    seller_data['platform'],
                    seller_data['seller_id'],
                    seller_data.get('name'),
                    seller_data.get('rating'),
                    seller_data.get('total_ratings'),
                    seller_data.get('positive_feedback_percent')
                ))
                seller_id = cursor.lastrowid
            
            conn.commit()
            return seller_id
            
        except Error as e:
            logger.error(f"Error adding/updating seller: {e}")
            conn.rollback()
            raise
    
    def add_product_seller(self, product_id: int, seller_id: int, price: float, shipping_price: float = 0) -> None:
        """Link a product to a seller with a price."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO product_sellers 
            (product_id, seller_id, price, shipping_price, last_checked, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (product_id, seller_id, price, shipping_price))
            
            conn.commit()
            
        except Error as e:
            logger.error(f"Error adding product-seller relationship: {e}")
            conn.rollback()
            raise
    
    def add_arbitrage_opportunity(self, opportunity_data: dict) -> int:
        """
        Add a new arbitrage opportunity.
        Returns the opportunity ID.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO arbitrage_opportunities 
            (source_product_id, target_platform, estimated_selling_price, 
             estimated_fees, estimated_profit, profit_margin, roi, last_checked)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                opportunity_data['source_product_id'],
                opportunity_data['target_platform'],
                opportunity_data['estimated_selling_price'],
                opportunity_data['estimated_fees'],
                opportunity_data['estimated_profit'],
                opportunity_data['profit_margin'],
                opportunity_data['roi']
            ))
            
            opportunity_id = cursor.lastrowid
            conn.commit()
            return opportunity_id
            
        except Error as e:
            logger.error(f"Error adding arbitrage opportunity: {e}")
            conn.rollback()
            raise
    
    def record_sale(self, sale_data: dict) -> int:
        """
        Record a completed sale.
        Returns the sale ID.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO sales_history 
            (product_id, platform, sale_price, quantity, fees, shipping_cost, tax, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sale_data['product_id'],
                sale_data['platform'],
                sale_data['sale_price'],
                sale_data.get('quantity', 1),
                sale_data.get('fees', 0),
                sale_data.get('shipping_cost', 0),
                sale_data.get('tax', 0),
                sale_data.get('notes')
            ))
            
            sale_id = cursor.lastrowid
            conn.commit()
            return sale_id
            
        except Error as e:
            logger.error(f"Error recording sale: {e}")
            conn.rollback()
            raise
    
    def get_arbitrage_opportunities(self, min_profit_margin: float = 20.0, limit: int = 50) -> list:
        """
        Get active arbitrage opportunities with at least the specified profit margin.
        """
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT 
                ao.id,
                p.title,
                p.url as source_url,
                p.price as source_price,
                ao.target_platform,
                ao.estimated_selling_price,
                ao.estimated_fees,
                ao.estimated_profit,
                ao.profit_margin,
                ao.roi,
                ao.created_at,
                ao.last_checked
            FROM 
                arbitrage_opportunities ao
                JOIN products p ON ao.source_product_id = p.id
            WHERE 
                ao.is_active = 1 
                AND ao.profit_margin >= ?
            ORDER BY 
                ao.roi DESC, ao.profit_margin DESC
            LIMIT ?
            ''', (min_profit_margin, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Error as e:
            logger.error(f"Error fetching arbitrage opportunities: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

# Example usage
if __name__ == "__main__":
    # Initialize the database
    db = Database('data/arbitrage.db')
    
    try:
        # Example: Add a product
        product_id = db.add_or_update_product({
            'source_platform': 'amazon',
            'source_id': 'B08N5KWB9H',
            'title': 'Example Product',
            'price': 29.99,
            'url': 'https://www.amazon.com/dp/B08N5KWB9H',
            'category': 'Electronics',
            'brand': 'Example Brand',
            'condition': 'New'
        })
        print(f"Added/updated product with ID: {product_id}")
        
        # Example: Get arbitrage opportunities
        opportunities = db.get_arbitrage_opportunities(min_profit_margin=20.0, limit=5)
        print("\nTop Arbitrage Opportunities:")
        for opp in opportunities:
            print(f"{opp['title']} - {opp['profit_margin']:.1f}% ROI")
            
    finally:
        db.close()
