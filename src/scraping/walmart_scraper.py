import time
import random
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from config.settings import ScrapingConfig, LoggingConfig

# Set up logging
logging.basicConfig(
    level=getattr(logging, LoggingConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class WalmartProduct:
    title: str
    price: float
    url: str
    item_id: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    in_stock: bool = True
    seller: Optional[str] = "Walmart"

class WalmartScraper:
    def __init__(self, headless: bool = True):
        self.config = ScrapingConfig()
        self.driver = self._init_driver(headless)
        
    def _init_driver(self, headless: bool = True):
        """Initialize Selenium WebDriver with Chrome."""
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.config.USER_AGENT}')
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def search_products(self, query: str, max_results: int = 10) -> List[WalmartProduct]:
        """Search for products on Walmart."""
        url = f"https://www.walmart.com/search?q={query.replace(' ', '+')}"
        self.driver.get(url)
        
        # Wait for search results to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-item-id]"))
        )
        
        # Scroll to load more results
        self._scroll_page()
        
        # Parse the page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        results = []
        
        for item in soup.select("[data-item-id]")[:max_results]:
            try:
                # Get product ID
                item_id = item.get('data-item-id')
                if not item_id:
                    continue
                
                # Get title
                title_elem = item.select_one("[data-automation-id='product-title']")
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                
                # Get price
                price_elem = item.select_one("[data-automation-id='product-price']")
                price = 0.0
                if price_elem:
                    price_str = price_elem.text.strip().replace('$', '').replace(',', '')
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass
                
                # Get URL
                link = item.select_one("a[href]")
                url = f"https://www.walmart.com{link['href']}" if link else None
                
                # Get rating and review count
                rating = None
                review_count = None
                rating_elem = item.select_one(".w_iUH7")
                if rating_elem and 'rating' in rating_elem.get('aria-label', ''):
                    rating_text = rating_elem['aria-label']
                    rating_parts = rating_text.split()
                    if len(rating_parts) > 0:
                        try:
                            rating = float(rating_parts[0])
                        except ValueError:
                            pass
                
                review_count_elem = item.select_one("span.b.w_iUH7")
                if review_count_elem:
                    try:
                        review_count = int(review_count_elem.text.strip('()').replace(',', ''))
                    except ValueError:
                        pass
                
                # Check stock status
                in_stock = bool(item.select_one("[data-automation-id='add-to-cart-button']"))
                
                product = WalmartProduct(
                    title=title,
                    price=price,
                    url=url,
                    item_id=item_id,
                    rating=rating,
                    review_count=review_count,
                    in_stock=in_stock
                )
                
                results.append(product)
                
            except Exception as e:
                logger.error(f"Error parsing product: {e}")
                continue
            
            time.sleep(random.uniform(1, 3))  # Random delay between requests
            
        return results
    
    def get_product_details(self, url: str) -> Optional[Dict]:
        """Get detailed information about a specific product."""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-automation-id='product-title']"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract product details
            title_elem = soup.select_one("[data-automation-id='product-title']")
            price_elem = soup.select_one("[data-automation-id='product-price']")
            
            # Extract specifications
            specs = {}
            for row in soup.select("table.keyFactsTable tr"):
                cols = row.find_all(['th', 'td'])
                if len(cols) == 2:
                    key = cols[0].text.strip()
                    value = cols[1].text.strip()
                    specs[key] = value
            
            # Extract description
            description = ""
            desc_elem = soup.select_one("[data-automation-id='description']")
            if desc_elem:
                description = desc_elem.text.strip()
            
            # Get seller info
            seller = "Walmart"
            seller_elem = soup.select_one("[data-automation-id='seller-name']")
            if seller_elem:
                seller = seller_elem.text.strip()
            
            return {
                'title': title_elem.text.strip() if title_elem else None,
                'price': float(price_elem.text.replace('$', '').replace(',', '')) if price_elem else None,
                'seller': seller,
                'description': description,
                'specifications': specs,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error getting product details: {e}")
            return None
    
    def _scroll_page(self):
        """Scroll the page to load more results."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
                
            last_height = new_height
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()

# Example usage
if __name__ == "__main__":
    scraper = WalmartScraper()
    try:
        print("Searching for 'wireless earbuds' on Walmart...")
        products = scraper.search_products("wireless earbuds", max_results=5)
        
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.title}")
            print(f"   Price: ${product.price:.2f}")
            if product.rating:
                print(f"   Rating: {product.rating} stars ({product.review_count or 0} reviews)")
            print(f"   In Stock: {'Yes' if product.in_stock else 'No'}")
            print(f"   URL: {product.url}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        scraper.close()
