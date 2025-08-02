import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
class APIConfig:
    # Amazon API
    AMAZON_ACCESS_KEY = os.getenv('AMAZON_ACCESS_KEY')
    AMAZON_SECRET_KEY = os.getenv('AMAZON_SECRET_KEY')
    AMAZON_ASSOC_TAG = os.getenv('AMAZON_ASSOC_TAG')
    
    # eBay API
    EBAY_APP_ID = os.getenv('EBAY_APP_ID')
    EBAY_CERT_ID = os.getenv('EBAY_CERT_ID')
    EBAY_DEV_ID = os.getenv('EBAY_DEV_ID')
    
    # AliExpress API
    ALIEXPRESS_API_KEY = os.getenv('ALIEXPRESS_API_KEY')

# Scraping Configuration
class ScrapingConfig:
    REQUEST_DELAY = 2  # seconds between requests
    MAX_RETRIES = 3
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Database Configuration
class DBConfig:
    DB_PATH = 'data/arbitrage.db'

# Arbitrage Settings
class ArbitrageConfig:
    MIN_PROFIT_PERCENTAGE = 20.0  # Minimum profit percentage to consider
    MIN_PROFIT_AMOUNT = 5.00  # Minimum profit amount in USD
    MAX_LISTING_PRICE = 100.00  # Maximum price to consider for a product
    MIN_SALES_RANK = 100000  # Maximum sales rank to consider (lower is better)

# Logging Configuration
class LoggingConfig:
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/arbitrage.log'
