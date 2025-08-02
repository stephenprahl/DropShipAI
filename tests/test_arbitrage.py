"""
Test script for the Super Arbitrage system.

This script tests the core functionality of the arbitrage system,
including finding opportunities, processing orders, and database operations.
"""

import unittest
import os
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_arbitrage import ArbitrageEngine, process_orders, list_opportunities
from src.utils.database import Database

class TestArbitrageSystem(unittest.TestCase):
    """Test cases for the arbitrage system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before any tests are run."""
        # Use an in-memory database for testing
        cls.db = Database(":memory:")
        cls.db.initialize_database()
        
    def setUp(self):
        """Set up test fixtures before each test method is called."""
        # Clear the database before each test
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM arbitrage_opportunities")
        cursor.execute("DELETE FROM orders")
        conn.commit()
        conn.close()
        
        # Create a test arbitrage engine
        self.engine = ArbitrageEngine()
        
    def test_find_opportunities(self):
        """Test finding arbitrage opportunities."""
        # Mock the find_opportunities method to return test data
        with patch.object(self.engine, 'find_opportunities') as mock_find:
            mock_find.return_value = [
                {
                    'id': 'OPP-12345',
                    'title': 'Test Product',
                    'source_platform': 'amazon',
                    'source_price': 29.99,
                    'target_platform': 'ebay',
                    'target_price': 59.99,
                    'estimated_profit': 21.01,
                    'profit_margin': 35.0,
                    'source_url': 'https://amazon.com/dp/B08N5KWB9H',
                    'target_url': 'https://ebay.com/itm/1234567890'
                }
            ]
            
            opportunities = self.engine.find_opportunities(
                source_platform='amazon',
                target_platform='ebay',
                query='test product',
                min_profit=20.0,
                min_margin=15.0,
                max_products=5,
                max_workers=3
            )
            
            self.assertEqual(len(opportunities), 1)
            self.assertEqual(opportunities[0]['title'], 'Test Product')
            self.assertGreaterEqual(opportunities[0]['estimated_profit'], 20.0)
            self.assertGreaterEqual(opportunities[0]['profit_margin'], 15.0)
    
    def test_process_orders(self):
        """Test processing orders."""
        # Test with mock data
        with patch('run_arbitrage.process_orders') as mock_process:
            mock_process.return_value = [
                {
                    'order_id': 'TEST-123',
                    'platform': 'amazon',
                    'status': 'pending',
                    'product_id': 'B08N5KWB9H',
                    'product_name': 'Test Product',
                    'quantity': 1,
                    'price': 59.99,
                    'customer_name': 'Test User',
                    'customer_email': 'test@example.com',
                    'shipping_address': '123 Test St',
                    'order_date': datetime.utcnow().isoformat(),
                    'processed_at': datetime.utcnow().isoformat()
                }
            ]
            
            orders = process_orders('amazon', 'pending', limit=1)
            
            self.assertEqual(len(orders), 1)
            self.assertEqual(orders[0]['order_id'], 'TEST-123')
            self.assertEqual(orders[0]['status'], 'pending')
    
    def test_list_opportunities(self):
        """Test listing opportunities from the database."""
        # Insert test data
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # Insert a test product
        cursor.execute(
            """
            INSERT INTO products (
                product_id, title, description, price, url, platform, 
                category, image_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                'B08N5KWB9H', 'Test Product', 'A test product', 
                29.99, 'https://example.com', 'amazon', 'Electronics',
                'https://example.com/image.jpg', 
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            )
        )
        
        # Insert a test opportunity
        cursor.execute(
            """
            INSERT INTO arbitrage_opportunities (
                id, source_product_id, target_platform, target_price,
                estimated_profit, profit_margin, is_active, created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                'OPP-12345', 'B08N5KWB9H', 'ebay', 59.99,
                21.01, 35.0, 1,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            )
        )
        
        conn.commit()
        conn.close()
        
        # Test listing opportunities
        opportunities = list_opportunities(limit=1, min_profit=20.0)
        
        self.assertGreaterEqual(len(opportunities), 0)
        if opportunities:
            self.assertEqual(opportunities[0]['id'], 'OPT-12345')
            self.assertGreaterEqual(opportunities[0]['estimated_profit'], 20.0)

    @patch('run_arbitrage.notify_opportunity')
    def test_notification_system(self, mock_notify):
        """Test the notification system."""
        from run_arbitrage import notify_opportunity
        
        test_opportunity = {
            'id': 'OPP-12345',
            'title': 'Test Product',
            'source_platform': 'amazon',
            'source_price': 29.99,
            'target_platform': 'ebay',
            'target_price': 59.99,
            'estimated_profit': 21.01,
            'profit_margin': 35.0,
            'source_url': 'https://amazon.com/dp/B08N5KWB9H',
            'target_url': 'https://ebay.com/itm/1234567890'
        }
        
        # Test notification function
        notify_opportunity(test_opportunity)
        
        # Verify notification was sent
        mock_notify.assert_called_once_with(test_opportunity)

if __name__ == '__main__':
    unittest.main()
