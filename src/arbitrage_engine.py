"""
Arbitrage Engine - Coordinates scraping and profit calculation
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path

from scraping.amazon_scraper import AmazonScraper, Product as AmazonProduct
from scraping.ebay_scraper import EBayScraper, EBayProduct
from analysis.profit_calculator import ProfitCalculator

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Represents a profitable arbitrage opportunity."""
    source_product: Dict
    target_platform: str
    target_price: float
    profit: float
    profit_margin: float
    fees: Dict
    timestamp: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'source_product': self.source_product,
            'target_platform': self.target_platform,
            'target_price': self.target_price,
            'profit': self.profit,
            'profit_margin': self.profit_margin,
            'fees': self.fees,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ArbitrageOpportunity':
        """Create from dictionary."""
        return cls(**data)

class ArbitrageEngine:
    """Main engine for finding and managing arbitrage opportunities."""
    
    def __init__(self, data_dir: str = 'data'):
        """Initialize with data directory for persistence."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize scrapers
        self.amazon_scraper = AmazonScraper()
        self.ebay_scraper = EBayScraper()
        
        # Initialize profit calculator
        self.profit_calculator = ProfitCalculator()
        
        # Cache for storing scraped products
        self.product_cache: Dict[str, Dict] = {}
        
    def search_products(self, query: str, platform: str, max_results: int = 20) -> List[Dict]:
        """Search for products on a specific platform."""
        try:
            if platform.lower() == 'amazon':
                products = self.amazon_scraper.search_products(query, max_results)
                return [self._format_amazon_product(p) for p in products]
            elif platform.lower() == 'ebay':
                products = self.ebay_scraper.search_products(query, max_results)
                return [self._format_ebay_product(p) for p in products]
            else:
                logger.error(f"Unsupported platform: {platform}")
                return []
        except Exception as e:
            logger.error(f"Error searching {platform} for '{query}': {e}")
            return []
    
    def _format_amazon_product(self, product: AmazonProduct) -> Dict:
        """Format Amazon product for our arbitrage system."""
        return {
            'platform': 'amazon',
            'title': product.title,
            'price': product.price,
            'url': product.url,
            'product_id': product.asin,
            'rating': product.rating,
            'review_count': product.review_count,
            'category': product.category,
            'seller': product.seller,
            'scraped_at': datetime.utcnow().isoformat()
        }
    
    def _format_ebay_product(self, product: EBayProduct) -> Dict:
        """Format eBay product for our arbitrage system."""
        return {
            'platform': 'ebay',
            'title': product.title,
            'price': product.price,
            'url': product.url,
            'product_id': product.item_id,
            'condition': product.condition,
            'shipping_price': product.shipping_price,
            'free_shipping': product.free_shipping,
            'buy_it_now': product.buy_it_now,
            'best_offer': product.best_offer,
            'time_left': product.time_left,
            'watchers': product.watchers,
            'scraped_at': datetime.utcnow().isoformat()
        }
    
    def find_opportunities(
        self,
        source_platform: str,
        target_platform: str,
        query: str,
        min_profit: float = 10.0,
        min_margin: float = 20.0,
        max_results: int = 20
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities between two platforms.
        
        Args:
            source_platform: Platform to source products from (e.g., 'amazon')
            target_platform: Platform to sell on (e.g., 'ebay')
            query: Search query for products
            min_profit: Minimum profit in dollars
            min_margin: Minimum profit margin percentage
            max_results: Maximum number of results to return
            
        Returns:
            List of profitable opportunities
        """
        logger.info(f"Searching for opportunities from {source_platform} to {target_platform}...")
        
        # Search for products on source platform
        products = self.search_products(query, source_platform, max_results)
        if not products:
            logger.warning(f"No products found on {source_platform} for query: {query}")
            return []
        
        opportunities = []
        
        # Check each product for arbitrage potential
        for product in products:
            try:
                # Calculate target price (simple 50% markup for demonstration)
                target_price = product['price'] * 1.5
                
                # Calculate profit metrics
                profit_data = self.profit_calculator.calculate_profit(
                    source_price=product['price'],
                    target_price=target_price,
                    source_platform=source_platform,
                    target_platform=target_platform,
                    shipping_cost=product.get('shipping_price', 0.0)
                )
                
                # Check if opportunity meets criteria
                if (profit_data['profit'] >= min_profit and 
                    profit_data['profit_margin'] >= min_margin):
                    
                    opportunity = ArbitrageOpportunity(
                        source_product=product,
                        target_platform=target_platform,
                        target_price=target_price,
                        profit=profit_data['profit'],
                        profit_margin=profit_data['profit_margin'],
                        fees={
                            'source_fees': profit_data['source_fees'],
                            'target_fees': profit_data['target_fees'],
                            'total_fees': profit_data['source_fees'] + profit_data['target_fees']
                        },
                        timestamp=datetime.utcnow().isoformat()
                    )
                    
                    opportunities.append(opportunity)
                    
                    logger.info(
                        f"Found opportunity: {product['title'][:50]}... | "
                        f"Profit: ${profit_data['profit']:.2f} ({profit_data['profit_margin']:.1f}%)"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing product {product.get('title', 'unknown')}: {e}")
                continue
        
        return opportunities
    
    def save_opportunities(self, opportunities: List[ArbitrageOpportunity], filename: str = None):
        """Save opportunities to a JSON file."""
        if not filename:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"opportunities_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump([opp.to_dict() for opp in opportunities], f, indent=2)
            logger.info(f"Saved {len(opportunities)} opportunities to {filepath}")
        except Exception as e:
            logger.error(f"Error saving opportunities: {e}")
    
    def load_opportunities(self, filename: str) -> List[ArbitrageOpportunity]:
        """Load opportunities from a JSON file."""
        filepath = self.data_dir / filename
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return [ArbitrageOpportunity.from_dict(item) for item in data]
        except Exception as e:
            logger.error(f"Error loading opportunities from {filepath}: {e}")
            return []

def main():
    """Example usage of the arbitrage engine."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize the engine
    engine = ArbitrageEngine()
    
    # Search for opportunities from Amazon to eBay
    opportunities = engine.find_opportunities(
        source_platform='amazon',
        target_platform='ebay',
        query='wireless earbuds',
        min_profit=10.0,
        min_margin=20.0,
        max_results=10
    )
    
    # Save the opportunities
    if opportunities:
        engine.save_opportunities(opportunities)
        print(f"\nFound {len(opportunities)} opportunities:")
        for opp in opportunities[:5]:  # Show first 5
            print(f"\n{opp.source_product['title'][:60]}...")
            print(f"Source: ${opp.source_product['price']:.2f} ({opp.source_product['platform']})")
            print(f"Target: ${opp.target_price:.2f} ({opp.target_platform})")
            print(f"Profit: ${opp.profit:.2f} ({opp.profit_margin:.1f}% margin)")
    else:
        print("No profitable opportunities found.")

if __name__ == "__main__":
    main()
