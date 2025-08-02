import time
import random
import logging
from typing import Dict, List, Optional
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
class Product:
    title: str
    price: float
    url: str
    asin: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    category: Optional[str] = None
    seller: Optional[str] = None

class AmazonScraper:
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
    
    def search_products(self, query: str, max_results: int = 10) -> List[Product]:
        """Search for products on Amazon."""
        url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        self.driver.get(url)
        
        # Wait for search results to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
        )
        
        # Scroll to load more results
        self._scroll_page()
        
        # Parse the page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        results = []
        
        for item in soup.select("[data-component-type='s-search-result']")[:max_results]:
            try:
                title_elem = item.select_one("h2 a span")
                price_elem = item.select_one(".a-price .a-offscreen")
                
                if not title_elem or not price_elem:
                    continue
                
                # Extract product details
                title = title_elem.text.strip()
                price_str = price_elem.text.strip().replace('$', '').replace(',', '')
                price = float(price_str)
                
                # Get product URL and ASIN
                link = item.select_one("h2 a")
                url = f"https://www.amazon.com{link['href'].split('?')[0]}" if link else None
                asin = link['href'].split('/dp/')[1].split('/')[0] if link and '/dp/' in link['href'] else None
                
                # Get rating and review count if available
                rating_elem = item.select_one(".a-icon-alt")
                rating = float(rating_elem.text.split()[0]) if rating_elem else None
                
                review_count_elem = item.select_one(".a-size-base.s-underline-text")
                review_count = int(review_count_elem.text.replace(',', '')) if review_count_elem else None
                
                product = Product(
                    title=title,
                    price=price,
                    url=url,
                    asin=asin,
                    rating=rating,
                    review_count=review_count
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
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract product details
            title = soup.select_one("#productTitle")
            price = soup.select_one(".a-price .a-offscreen")
            seller = soup.select_one("#merchant-info")
            
            # Extract features from product details table
            features = {}
            for row in soup.select("#productDetails_techSpec_section_1 tr"):
                cols = row.find_all('td')
                if len(cols) == 2:
                    features[cols[0].text.strip()] = cols[1].text.strip()
            
            return {
                'title': title.text.strip() if title else None,
                'price': float(price.text.replace('$', '').replace(',', '')) if price else None,
                'seller': seller.text.strip() if seller else None,
                'features': features
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
    scraper = AmazonScraper()
    try:
        print("Searching for 'wireless earbuds' on Amazon...")
        products = scraper.search_products("wireless earbuds", max_results=5)
        
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.title}")
            print(f"   Price: ${product.price}")
            print(f"   Rating: {product.rating} stars ({product.review_count} reviews)")
            print(f"   URL: {product.url}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        scraper.close()
