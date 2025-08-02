import logging
from typing import Dict, List
from datetime import datetime
import time
import random

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrderProcessor:
    def __init__(self):
        self.processed_orders = 0
        
    def process_order(self, order_data: Dict) -> Dict:
        """Process a single order."""
        logger.info(f"Processing order {order_data.get('id')}")
        time.sleep(0.5)  # Simulate processing time
        
        # Simulate success/failure
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            self.processed_orders += 1
            return {
                'order_id': order_data.get('id'),
                'status': 'processed',
                'tracking_number': f"1Z{random.randint(100, 999)}R{random.randint(100000000, 999999999)}",
                'processed_at': datetime.utcnow().isoformat()
            }
        else:
            return {
                'order_id': order_data.get('id'),
                'status': 'failed',
                'error': 'Processing error',
                'processed_at': datetime.utcnow().isoformat()
            }

class ListingManager:
    def create_listing(self, product: Dict, platform: str) -> Dict:
        """Create a new product listing."""
        logger.info(f"Creating {platform} listing for {product.get('title')}")
        time.sleep(1)  # Simulate API call
        
        return {
            'listing_id': f"LST{random.randint(100000000, 999999999)}",
            'platform': platform,
            'product_id': product.get('id'),
            'status': 'active',
            'url': f"https://{platform}.com/listings/{random.randint(1000000, 9999999)}"
        }
    
    def update_inventory(self, product_id: str, quantity: int) -> bool:
        """Update inventory for a product."""
        logger.info(f"Updating inventory for {product_id} to {quantity}")
        time.sleep(0.5)
        return True

# Example usage
if __name__ == "__main__":
    # Test OrderProcessor
    processor = OrderProcessor()
    order = {'id': 'ORD123', 'product_id': 'PROD456', 'quantity': 1}
    result = processor.process_order(order)
    print(f"Order processing result: {result}")
    
    # Test ListingManager
    manager = ListingManager()
    product = {'id': 'PROD456', 'title': 'Test Product', 'price': 29.99}
    listing = manager.create_listing(product, 'ebay')
    print(f"Created listing: {listing}")
