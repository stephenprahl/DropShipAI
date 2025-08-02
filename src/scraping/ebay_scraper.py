import time
import random
import logging
from typing import List, Optional, Dict
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
class EBayProduct:
    title: str
    price: float
    url: str
    item_id: str
    condition: Optional[str] = None
    shipping_price: Optional[float] = None
    free_shipping: bool = False
    buy_it_now: bool = False
    best_offer: bool = False
    time_left: Optional[str] = None
    watchers: Optional[int] = None

class EBayScraper:
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
    
    def search_products(self, query: str, max_results: int = 10) -> List[EBayProduct]:
        """Search for products on eBay."""
        url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}&_sop=12"
        self.driver.get(url)
        
        # Wait for search results to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".srp-results .s-item"))
        )
        
        # Scroll to load more results
        self._scroll_page()
        
        # Parse the page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        results = []
        
        for item in soup.select(".srp-results .s-item")[1:max_results+1]:  # Skip first item (sometimes an ad)
            try:
                # Extract basic info
                title_elem = item.select_one(".s-item__title")
                price_elem = item.select_one(".s-item__price")
                
                if not title_elem or not price_elem:
                    continue
                
                # Get product details
                title = title_elem.text.strip()
                price_str = price_elem.text.strip().replace('$', '').replace(',', '')
                price = float(price_str) if price_str.replace('.', '').isdigit() else 0.0
                
                # Get product URL and ID
                link = item.select_one(".s-item__link")
                url = link['href'].split('?')[0] if link else None
                item_id = url.split('/')[-1].split('?')[0] if url else None
                
                # Get shipping info
                shipping_elem = item.select_one(".s-item__shipping")
                shipping_price = 0.0
                free_shipping = False
                
                if shipping_elem:
                    shipping_text = shipping_elem.text.lower()
                    if 'free' in shipping_text:
                        free_shipping = True
                    elif '$' in shipping_text:
                        try:
                            shipping_price = float(''.join(c for c in shipping_text if c.isdigit() or c == '.'))
                        except (ValueError, TypeError):
                            shipping_price = 0.0
                
                # Get condition
                condition_elem = item.select_one(".s-item__subtitle")
                condition = condition_elem.text.strip() if condition_elem else "Unknown"
                
                # Get auction/buy it now info
                buy_it_now = bool(item.select_one(".s-item__purchase-options"))
                best_offer = "best offer" in item.text.lower()
                
                # Get time left and watchers
                time_left = None
                watchers = None
                
                time_elem = item.select_one(".s-item__time-end")
                if time_elem:
                    time_left = time_elem.text.strip()
                
                watchers_elem = item.select_one(".s-item__hotness")
                if watchers_elem and 'watchers' in watchers_elem.text.lower():
                    try:
                        watchers = int(''.join(c for c in watchers_elem.text if c.isdigit()))
                    except (ValueError, TypeError):
                        pass
                
                product = EBayProduct(
                    title=title,
                    price=price,
                    url=url,
                    item_id=item_id,
                    condition=condition,
                    shipping_price=shipping_price,
                    free_shipping=free_shipping,
                    buy_it_now=buy_it_now,
                    best_offer=best_offer,
                    time_left=time_left,
                    watchers=watchers
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
                EC.presence_of_element_located((By.ID, "itemTitle"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract product details
            title = soup.select_one("#itemTitle")
            price = soup.select_one("#prcIsum")
            condition = soup.select_one("#vi-itm-cond")
            seller_info = soup.select_one("#mbgLink")
            
            # Extract item specifics
            specifics = {}
            for row in soup.select("#viTabs_0_is .ux-layout-section--features"):
                label = row.select_one(".ux-labels-values__labels")
                value = row.select_one(".ux-labels-values__values")
                if label and value:
                    specifics[label.text.strip()] = value.text.strip()
            
            # Get shipping info
            shipping = {}
            shipping_cost = soup.select_one("#shSummary .sh-ds")
            if shipping_cost:
                shipping['cost'] = shipping_cost.text.strip()
                
            shipping_to = soup.select_one("#shSummary .sh-fls-cb")
            if shipping_to:
                shipping['location'] = shipping_to.text.strip()
            
            return {
                'title': title.text.replace('Details about', '').strip() if title else None,
                'price': float(price.text.replace('$', '').replace(',', '')) if price else None,
                'condition': condition.text.strip() if condition else None,
                'seller': seller_info.text.strip() if seller_info else None,
                'specifics': specifics,
                'shipping': shipping
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
    scraper = EBayScraper()
    try:
        print("Searching for 'wireless earbuds' on eBay...")
        products = scraper.search_products("wireless earbuds", max_results=5)
        
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.title}")
            print(f"   Price: ${product.price:.2f}")
            if product.free_shipping:
                print("   Free Shipping")
            elif product.shipping_price:
                print(f"   + ${product.shipping_price:.2f} shipping")
            print(f"   Condition: {product.condition}")
            if product.buy_it_now:
                print("   Buy It Now")
            if product.best_offer:
                print("   Best Offer Available")
            if product.watchers:
                print(f"   {product.watchers} watchers")
            print(f"   URL: {product.url}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        scraper.close()
