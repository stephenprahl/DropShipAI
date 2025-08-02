"""Base scraper class with common functionality for all platform scrapers."""
import random
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all platform scrapers."""
    
    def __init__(self):
        self.session = self._create_session()
        self.request_delay = (1, 3)  # Random delay between requests in seconds
        self.timeout = 30  # Request timeout in seconds
    
    def _create_session(self):
        """Create a requests session with headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        return session
    
    def _get_random_user_agent(self) -> str:
        """Return a random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        ]
        return random.choice(user_agents)
    
    def _random_delay(self):
        """Random delay between requests to avoid rate limiting."""
        time.sleep(random.uniform(*self.request_delay))
    
    @staticmethod
    def parse_price(price_str: str) -> float:
        """Convert price string to float."""
        if not price_str:
            return 0.0
        # Remove currency symbols and non-numeric characters except decimal point
        price_str = ''.join(c for c in price_str if c.isdigit() or c in '.,')
        # Handle different decimal separators
        if ',' in price_str and '.' in price_str:
            if price_str.find(',') < price_str.find('.'):
                price_str = price_str.replace(',', '')
            else:
                price_str = price_str.replace('.', '').replace(',', '.')
        elif ',' in price_str:
            price_str = price_str.replace(',', '.')
        return float(price_str)
    
    @abstractmethod
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for products on the platform."""
        pass
