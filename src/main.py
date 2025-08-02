import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories if they don't exist."""
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

def main():
    """Main entry point for the Super Arbitrage application."""
    parser = argparse.ArgumentParser(description='AI-Powered Dropshipping Arbitrage Tool')
    parser.add_argument('--query', type=str, help='Search query for products')
    parser.add_argument('--max-results', type=int, default=5, help='Maximum number of results to return')
    args = parser.parse_args()
    
    logger.info("Starting Super Arbitrage...")
    setup_directories()
    
    if args.query:
        from src.scraping.amazon_scraper import AmazonScraper
        
        logger.info(f"Searching for: {args.query}")
        scraper = AmazonScraper()
        
        try:
            products = scraper.search_products(args.query, max_results=args.max_results)
            
            print("\nSearch Results:")
            print("-" * 80)
            for i, product in enumerate(products, 1):
                print(f"{i}. {product.title[:80]}...")
                print(f"   Price: ${product.price:.2f}")
                if product.rating:
                    print(f"   Rating: {product.rating} stars ({product.review_count or 0} reviews)")
                print(f"   URL: {product.url}")
                print()
                
        except Exception as e:
            logger.error(f"Error during search: {e}")
        finally:
            scraper.close()
    else:
        logger.info("No search query provided. Use --query to search for products.")

if __name__ == "__main__":
    main()
