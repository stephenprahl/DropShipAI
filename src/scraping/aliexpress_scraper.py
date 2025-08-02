import time
import random
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

from config.settings import ScrapingConfig, LoggingConfig

# Set up logging
logging.basicConfig(
    level=getattr(logging, LoggingConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AliExpressProduct:
    title: str
    price: float
    original_price: float
    url: str
    product_id: str
    store_name: str
    store_rating: Optional[float] = None
    orders_count: Optional[int] = None
    free_shipping: bool = False
    min_order_quantity: int = 1
    variants: Optional[Dict] = None

class AliExpressScraper:
    def __init__(self, headless: bool = True):
        self.config = ScrapingConfig()
        self.driver = self._init_driver(headless)
        self.base_url = "https://www.aliexpress.com"
        
    def _init_driver(self, headless: bool = True):
        """Initialize Selenium WebDriver with Chrome."""
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.config.USER_AGENT}')
        
        # Add arguments to handle AliExpress anti-bot measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Mask the WebDriver instance
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def search_products(self, query: str, max_results: int = 10) -> List[AliExpressProduct]:
        """Search for products on AliExpress."""
        url = f"{self.base_url}/wholesale?SearchText={query.replace(' ', '+')}"
        self.driver.get(url)
        
        # Handle cookie consent if it appears
        self._handle_cookie_consent()
        
        # Wait for search results to load
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ae_object_type='product']"))
        )
        
        # Scroll to load more results
        self._scroll_page()
        
        # Parse the page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        results = []
        
        for item in soup.select("[data-ae_object_type='product']")[:max_results]:
            try:
                # Get product ID
                product_link = item.select_one("a[href*='item/']")
                if not product_link:
                    continue
                    
                href = product_link.get('href', '')
                product_id = self._extract_product_id(href)
                if not product_id:
                    continue
                
                # Get title
                title_elem = item.select_one("[class*='title--']")
                title = title_elem.text.strip() if title_elem else ""
                
                # Get price
                price_elem = item.select_one("[class*='price--']")
                price_str = price_elem.text.strip() if price_elem else ""
                price = self._parse_price(price_str)
                
                # Get original price if on sale
                original_price = price
                original_price_elem = item.select_one("[class*='sale-price--']")
                if original_price_elem:
                    original_price = self._parse_price(original_price_elem.text.strip())
                
                # Get store name
                store_elem = item.select_one("[class*='store--']")
                store_name = store_elem.text.strip() if store_elem else ""
                
                # Get store rating
                store_rating = None
                rating_elem = item.select_one("[class*='evaluation--'] [class*='score--']")
                if rating_elem:
                    try:
                        store_rating = float(rating_elem.text.strip())
                    except (ValueError, AttributeError):
                        pass
                
                # Get order count
                orders_count = None
                orders_elem = item.select_one("[class*='sale--']")
                if orders_elem:
                    try:
                        orders_text = orders_elem.text.strip().lower()
                        if 'sold' in orders_text:
                            orders_num = re.search(r'(\d+[,\d]*)', orders_text)
                            if orders_num:
                                orders_count = int(orders_num.group(1).replace(',', ''))
                    except (ValueError, AttributeError):
                        pass
                
                # Check for free shipping
                free_shipping = bool(item.select_one(":-soup-contains('Free Shipping')"))
                
                # Get URL
                url = href if href.startswith('http') else f"{self.base_url}{href}"
                
                product = AliExpressProduct(
                    title=title,
                    price=price,
                    original_price=original_price,
                    url=url,
                    product_id=product_id,
                    store_name=store_name,
                    store_rating=store_rating,
                    orders_count=orders_count,
                    free_shipping=free_shipping
                )
                
                results.append(product)
                
            except Exception as e:
                logger.error(f"Error parsing product: {e}")
                continue
            
            time.sleep(random.uniform(2, 5))  # Random delay between requests
            
        return results
    
    def get_product_details(self, url: str) -> Optional[Dict]:
        """Get detailed information about a specific product."""
        try:
            self.driver.get(url)
            
            # Handle cookie consent if it appears
            self._handle_cookie_consent()
            
            # Wait for product details to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='Product_Name']"))
            )
            
            # Scroll to load all sections
            self._scroll_page()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract product details
            title_elem = soup.select_one("[class*='Product_Name']")
            price_elem = soup.select_one("[class*='Product_Price']")
            store_elem = soup.select_one("[class*='Store_Name']")
            
            # Extract description
            description = ""
            desc_elem = soup.select_one("div[class*='Product_Description']")
            if desc_elem:
                description = desc_elem.text.strip()
            
            # Extract specifications
            specs = {}
            spec_rows = soup.select("div[class*='Specification'] tr")
            for row in spec_rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) == 2:
                    key = cols[0].text.strip()
                    value = cols[1].text.strip()
                    specs[key] = value
            
            # Extract variants if available
            variants = {}
            variant_elems = soup.select("[class*='Sku_Item']")
            for variant in variant_elems:
                name = variant.get('title', '').strip()
                if name:
                    variants[name] = variant.get('data-sku-prop', '')
            
            # Extract shipping info
            shipping_info = {}
            shipping_elems = soup.select("[class*='ShippingInfo']")
            for elem in shipping_elems:
                text = elem.text.strip()
                if 'to' in text and 'in' in text:
                    parts = text.split('in')
                    if len(parts) == 2:
                        shipping_info['delivery_time'] = parts[1].strip()
                elif 'shipping' in text.lower():
                    shipping_info['method'] = text
            
            return {
                'title': title_elem.text.strip() if title_elem else None,
                'price': self._parse_price(price_elem.text) if price_elem else None,
                'store': store_elem.text.strip() if store_elem else None,
                'description': description,
                'specifications': specs,
                'variants': variants if variants else None,
                'shipping_info': shipping_info,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error getting product details: {e}")
            return None
    
    def _extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from URL."""
        match = re.search(r'/item/(\d+)\.html', url)
        return match.group(1) if match else None
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string into float."""
        if not price_str:
            return 0.0
            
        # Extract numbers and decimal point
        price_match = re.search(r'[\d.,]+', price_str)
        if not price_match:
            return 0.0
            
        price_num = price_match.group(0).replace(',', '.')
        try:
            return float(price_num)
        except ValueError:
            return 0.0
    
    def _handle_cookie_consent(self):
        """Handle cookie consent popup if it appears."""
        try:
            # Try to find and click the cookie consent button
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='agree-btn']"))
            )
            cookie_btn.click()
            time.sleep(1)
        except:
            pass  # No cookie consent popup found or couldn't click it
    
    def _scroll_page(self, scroll_pause_time: float = 0.5):
        """Scroll the page to load more content."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait to load content
            time.sleep(scroll_pause_time)
            
            # Calculate new scroll height and compare with last scroll height
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
    scraper = AliExpressScraper()
    try:
        print("Searching for 'wireless earbuds' on AliExpress...")
        products = scraper.search_products("wireless earbuds", max_results=5)
        
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.title}")
            print(f"   Price: ${product.price:.2f}")
            if product.original_price > product.price:
                print(f"   Original: ${product.original_price:.2f} (Save {((product.original_price - product.price)/product.original_price*100):.0f}%)")
            if product.store_rating:
                print(f"   Store: {product.store_name} ({product.store_rating}/5.0)")
            if product.orders_count:
                print(f"   Orders: {product.orders_count:,}")
            if product.free_shipping:
                print("   Free Shipping")
            print(f"   URL: {product.url}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        scraper.close()
