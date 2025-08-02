import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import random

# Set up logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PriceDataPoint:
  price: float
  timestamp: datetime
  source: str

@dataclass
class ProductAnalysis:
  product_id: str
  source_platform: str
  current_price: float
  avg_price: float
  price_std: float
  price_trend: float  # Price trend over time (slope of linear regression)
  sales_velocity: float  # Estimated sales per day
  competition_level: float  # 0-1 scale, 1 being highly competitive
  demand_score: float  # 0-1 scale, 1 being high demand
  seasonality_factor: float  # 1.0 is normal, >1.0 is high season
  last_updated: datetime

class ArbitrageAnalyzer:
  def __init__(self, db_path: str = 'data/arbitrage.db'):
    """Initialize the arbitrage analyzer with a database connection."""
    self.db_path = db_path
    
  def analyze_product(self, product_data: dict, price_history: List[dict], 
             competition_data: dict = None) -> dict:
    """
    Analyze a product for arbitrage potential.
    
    Args:
      product_data: Dictionary containing product information
      price_history: List of historical price points
      competition_data: Optional data about competitors
      
    Returns:
      Dictionary with analysis results
    """
    try:
      # Convert price history to PriceDataPoint objects
      price_points = [
        PriceDataPoint(
          price=p['price'],
          timestamp=datetime.fromisoformat(p['timestamp']) if isinstance(p['timestamp'], str) else p['timestamp'],
          source=p.get('source', 'unknown')
        ) for p in price_history
      ]
      
      # Sort by timestamp
      price_points.sort(key=lambda x: x.timestamp)
      
      # Basic price statistics
      prices = [p.price for p in price_points]
      current_price = prices[-1] if prices else 0
      avg_price = np.mean(prices) if prices else 0
      price_std = np.std(prices) if len(prices) > 1 else 0
      
      # Price trend (simple linear regression)
      price_trend = self._calculate_price_trend(price_points)
      
      # Estimate sales velocity (this would be more accurate with actual sales data)
      sales_velocity = self._estimate_sales_velocity(product_data, price_points)
      
      # Analyze competition
      competition_level = self._analyze_competition(competition_data) if competition_data else 0.5
      
      # Calculate demand score (simplified)
      demand_score = self._calculate_demand_score(
        product_data, 
        price_points, 
        competition_level
      )
      
      # Calculate seasonality factor
      seasonality_factor = self._get_seasonality_factor(product_data)
      
      # Calculate profit potential
      profit_potential = self._calculate_profit_potential(
        current_price,
        avg_price,
        demand_score,
        competition_level,
        seasonality_factor
      )
      
      # Create analysis result
      analysis = {
        'product_id': product_data.get('id'),
        'source_platform': product_data.get('source_platform', 'unknown'),
        'current_price': current_price,
        'avg_price': avg_price,
        'price_std': price_std,
        'price_trend': price_trend,
        'sales_velocity': sales_velocity,
        'competition_level': competition_level,
        'demand_score': demand_score,
        'seasonality_factor': seasonality_factor,
        'profit_potential': profit_potential,
        'last_updated': datetime.utcnow().isoformat(),
        'recommendation': self._generate_recommendation(
          profit_potential,
          demand_score,
          competition_level
        )
      }
      
      return analysis
      
    except Exception as e:
      logger.error(f"Error analyzing product: {e}", exc_info=True)
      raise
  
  def _calculate_price_trend(self, price_points: List[PriceDataPoint]) -> float:
    """Calculate the price trend using linear regression."""
    if len(price_points) < 2:
      return 0.0
      
    try:
      # Convert timestamps to numerical values (days since first point)
      first_timestamp = min(p.timestamp for p in price_points)
      x = np.array([(p.timestamp - first_timestamp).total_seconds() / 86400 
             for p in price_points])
      y = np.array([p.price for p in price_points])
      
      # Simple linear regression
      z = np.polyfit(x, y, 1)
      return float(z[0])  # Return the slope
      
    except Exception as e:
      logger.warning(f"Error calculating price trend: {e}")
      return 0.0
  
  def _estimate_sales_velocity(self, product_data: dict, 
                 price_points: List[PriceDataPoint]) -> float:
    """Estimate sales velocity based on available data."""
    # This is a simplified estimation
    # In a real system, you'd use actual sales data or marketplace APIs
    
    # Base velocity on price position relative to historical prices
    if not price_points:
      return 0.5  # Default to medium velocity
      
    current_price = price_points[-1].price
    prices = [p.price for p in price_points]
    min_price, max_price = min(prices), max(prices)
    price_range = max_price - min_price
    
    if price_range == 0:
      return 0.5  # No price variation
      
    # Normalize price position (0 = min price, 1 = max price)
    price_position = (current_price - min_price) / price_range
    
    # Lower prices typically lead to higher sales velocity
    # This is a simple inverse relationship, but could be more sophisticated
    return max(0.1, 1.0 - price_position * 0.8)  # Between 0.2 and 1.0
  
  def _analyze_competition(self, competition_data: dict) -> float:
    """Analyze competition level based on available data."""
    # This is a simplified analysis
    # In a real system, you'd analyze actual competitor data
    
    # Competition data might include:
    # - Number of sellers
    # - Price distribution
    # - Seller ratings
    # - Inventory levels
    
    # For now, return a random value between 0.2 and 0.8
    return random.uniform(0.2, 0.8)
  
  def _calculate_demand_score(self, product_data: dict, 
                price_points: List[PriceDataPoint],
                competition_level: float) -> float:
    """Calculate a demand score for the product."""
    # This is a simplified calculation
    # In a real system, you'd use actual sales data, search volume, etc.
    
    # Factors that might influence demand:
    # - Price trend (increasing prices might indicate increasing demand)
    # - Sales velocity
    # - Seasonality
    # - Competition level
    
    # For now, return a value between 0.3 and 0.9
    return random.uniform(0.3, 0.9)
  
  def _get_seasonality_factor(self, product_data: dict) -> float:
    """Calculate a seasonality factor for the product."""
    # This is a placeholder that would be replaced with actual seasonality analysis
    # based on product category, historical sales data, etc.
    
    # For now, return a value between 0.8 and 1.2
    return random.uniform(0.8, 1.2)
  
  def _calculate_profit_potential(self, current_price: float, 
                  avg_price: float,
                  demand_score: float,
                  competition_level: float,
                  seasonality_factor: float) -> float:
    """Calculate a profit potential score."""
    # This is a simplified calculation
    # In a real system, you'd consider:
    # - Current price vs. historical prices
    # - Demand and competition
    # - Seasonality
    # - Fees and shipping costs
    # - Marketplace dynamics
    
    # Simple formula (all values between 0 and 1)
    price_ratio = avg_price / current_price if current_price > 0 else 1.0
    profit_potential = (
      (0.4 * price_ratio) + 
      (0.3 * demand_score) + 
      (0.2 * (1 - competition_level)) + 
      (0.1 * seasonality_factor)
    )
    
    # Ensure the result is between 0 and 1
    return max(0.0, min(1.0, profit_potential))
  
  def _generate_recommendation(self, profit_potential: float,
                 demand_score: float,
                 competition_level: float) -> str:
    """Generate a human-readable recommendation."""
    if profit_potential > 0.7 and demand_score > 0.6 and competition_level < 0.6:
      return "Strong buy - High profit potential with good demand and manageable competition"
    elif profit_potential > 0.5 and demand_score > 0.5 and competition_level < 0.7:
      return "Buy - Good profit potential with reasonable demand"
    elif profit_potential > 0.4 and demand_score > 0.4 and competition_level < 0.8:
      return "Consider - Some profit potential, but evaluate carefully"
    elif profit_potential <= 0.3 or competition_level > 0.8:
      return "Avoid - Low profit potential or too much competition"
    else:
      return "Neutral - Insufficient data or mixed signals"
  
  def find_arbitrage_opportunities(self, source_platform: str, 
                   target_platform: str,
                   min_profit_margin: float = 20.0,
                   min_demand_score: float = 0.5) -> List[dict]:
    """
    Find arbitrage opportunities between two platforms.
    
    Args:
      source_platform: Platform to source products from (e.g., 'amazon')
      target_platform: Platform to sell on (e.g., 'ebay')
      min_profit_margin: Minimum required profit margin (percentage)
      min_demand_score: Minimum required demand score (0-1)
      
    Returns:
      List of arbitrage opportunities
    """
    # In a real implementation, this would:
    # 1. Query products from the source platform
    # 2. Check prices on the target platform
    # 3. Calculate fees and shipping costs
    # 4. Apply the analysis
    # 5. Return the best opportunities
    
    # This is a placeholder that returns mock data
    # In a real system, you'd implement the above logic
    
    mock_products = [
      {
        'id': f"{source_platform}_12345",
        'title': 'Wireless Earbuds',
        'price': 29.99,
        'url': f'https://{source_platform}.com/product/12345',
        'category': 'Electronics',
        'source_platform': source_platform,
        'target_platform': target_platform
      },
      {
        'id': f"{source_platform}_67890",
        'title': 'Smart Watch',
        'price': 89.99,
        'url': f'https://{source_platform}.com/product/67890',
        'category': 'Electronics',
        'source_platform': source_platform,
        'target_platform': target_platform
      }
    ]
    
    opportunities = []
    for product in mock_products:
      # Generate mock price history (30 days)
      price_history = []
      base_price = product['price']
      for i in range(30):
        price = base_price * random.uniform(0.9, 1.1)  # ±10% variation
        price_history.append({
          'price': round(price, 2),
          'timestamp': (datetime.utcnow() - timedelta(days=29-i)).isoformat(),
          'source': source_platform
        })
      
      # Analyze the product
      analysis = self.analyze_product(product, price_history)
      
      # Calculate potential selling price (add a markup)
      markup = random.uniform(1.2, 2.0)  # 20-100% markup
      selling_price = round(product['price'] * markup, 2)
      
      # Calculate fees (simplified)
      fees = selling_price * 0.15  # 15% fee estimate
      
      # Calculate profit
      profit = selling_price - product['price'] - fees
      profit_margin = (profit / selling_price) * 100
      
      # Only include if it meets our criteria
      if profit_margin >= min_profit_margin and analysis['demand_score'] >= min_demand_score:
        opportunities.append({
          'product': product,
          'analysis': analysis,
          'selling_price': selling_price,
          'fees': fees,
          'profit': profit,
          'profit_margin': profit_margin,
          'roi': (profit / product['price']) * 100 if product['price'] > 0 else 0,
          'source_platform': source_platform,
          'target_platform': target_platform
        })
    
    # Sort by profit margin (highest first)
    opportunities.sort(key=lambda x: x['profit_margin'], reverse=True)
    return opportunities

# Example usage
if __name__ == "__main__":
  analyzer = ArbitrageAnalyzer()
  
  # Example product data
  product = {
    'id': 'B08N5KWB9H',
    'title': 'Wireless Earbuds',
    'price': 29.99,
    'url': 'https://example.com/product/B08N5KWB9H',
    'category': 'Electronics',
    'source_platform': 'amazon'
  }
  
  # Generate some mock price history (30 days)
  import random
  from datetime import datetime, timedelta
  
  price_history = []
  base_price = 29.99
  for i in range(30):
    price = base_price * random.uniform(0.9, 1.1)  # ±10% variation
    price_history.append({
      'price': round(price, 2),
      'timestamp': (datetime.utcnow() - timedelta(days=29-i)).isoformat(),
      'source': 'amazon'
    })
  
  # Analyze the product
  analysis = analyzer.analyze_product(product, price_history)
  
  print("Product Analysis:")
  print(f"Title: {product['title']}")
  print(f"Current Price: ${product['price']:.2f}")
  print(f"Average Price: ${analysis['avg_price']:.2f}")
  print(f"Price Trend: {'↑' if analysis['price_trend'] > 0 else '↓'} {abs(analysis['price_trend']):.2f} per day")
  print(f"Demand Score: {analysis['demand_score']:.2f}/1.0")
  print(f"Competition Level: {analysis['competition_level']:.2f}/1.0")
  print(f"Profit Potential: {analysis['profit_potential']*100:.1f}%")
  print(f"Recommendation: {analysis['recommendation']}")
  
  # Find arbitrage opportunities
  print("\nFinding arbitrage opportunities...")
  opportunities = analyzer.find_arbitrage_opportunities(
    source_platform='amazon',
    target_platform='ebay',
    min_profit_margin=20.0
  )
  
  print(f"\nFound {len(opportunities)} opportunities:")
  for i, opp in enumerate(opportunities, 1):
    print(f"\n{i}. {opp['product']['title']}")
    print(f"   Source: {opp['source_platform'].title()} (${opp['product']['price']:.2f})")
    print(f"   Target: {opp['target_platform'].title()} (${opp['selling_price']:.2f})")
    print(f"   Profit: ${opp['profit']:.2f} ({opp['profit_margin']:.1f}% margin, {opp['roi']:.1f}% ROI)")
    print(f"   Demand: {opp['analysis']['demand_score']:.2f}/1.0")
    print(f"   Competition: {opp['analysis']['competition_level']:.2f}/1.0")
