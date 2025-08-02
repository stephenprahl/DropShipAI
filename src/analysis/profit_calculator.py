"""
Profit calculator for arbitrage opportunities.
Handles fee calculations, profit margins, and opportunity evaluation.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlatformFees:
    """Fee structure for different e-commerce platforms."""
    referral_fee: float  # Percentage of sale price
    payment_processing_fee: float  # Percentage of sale price
    fixed_fee: float  # Fixed fee per transaction
    monthly_fee: float = 0.0  # Monthly subscription fee if any
    
    def calculate_fees(self, price: float) -> float:
        """Calculate total fees for a given price."""
        return (price * (self.referral_fee + self.payment_processing_fee) / 100) + self.fixed_fee

class ProfitCalculator:
    """Calculates profit and fees for arbitrage opportunities."""
    
    # Platform fee structures (as percentages of sale price unless specified otherwise)
    PLATFORM_FEES = {
        'amazon': PlatformFees(
            referral_fee=15.0,  # 15% referral fee
            payment_processing_fee=2.9,  # 2.9% + $0.30
            fixed_fee=0.30,
            monthly_fee=39.99  # Professional selling plan
        ),
        'ebay': PlatformFees(
            referral_fee=12.55,  # 12.55% final value fee
            payment_processing_fee=2.9,  # 2.9% + $0.30
            fixed_fee=0.30,
            monthly_fee=0.0  # No monthly fee for basic store
        ),
        'walmart': PlatformFees(
            referral_fee=15.0,  # 15% referral fee
            payment_processing_fee=2.9,  # 2.9% + $0.30
            fixed_fee=0.30,
            monthly_fee=0.0
        ),
        'etsy': PlatformFees(
            referral_fee=6.5,  # 6.5% transaction fee + 5% payment processing
            payment_processing_fee=5.0,
            fixed_fee=0.25,  # $0.25 listing fee
            monthly_fee=0.0
        )
    }
    
    @staticmethod
    def calculate_profit(
        source_price: float,
        target_price: float,
        source_platform: str,
        target_platform: str,
        shipping_cost: float = 0.0,
        quantity: int = 1
    ) -> Dict[str, float]:
        """
        Calculate profit for an arbitrage opportunity.
        
        Args:
            source_price: Price on the source platform
            target_price: Price on the target platform
            source_platform: Name of the source platform (e.g., 'amazon')
            target_platform: Name of the target platform (e.g., 'ebay')
            shipping_cost: Shipping cost to customer (if not free)
            quantity: Number of items
            
        Returns:
            Dictionary with profit metrics
        """
        # Get fee structures for both platforms
        source_fees = ProfitCalculator.PLATFORM_FEES.get(
            source_platform.lower(),
            PlatformFees(referral_fee=10.0, payment_processing_fee=2.9, fixed_fee=0.30)
        )
        
        target_fees = ProfitCalculator.PLATFORM_FEES.get(
            target_platform.lower(),
            PlatformFees(referral_fee=10.0, payment_processing_fee=2.9, fixed_fee=0.30)
        )
        
        # Calculate costs and fees
        source_total = source_price * quantity
        target_total = (target_price + shipping_cost) * quantity
        
        # Calculate fees
        source_fee_amount = source_fees.calculate_fees(source_total)
        target_fee_amount = target_fees.calculate_fees(target_total)
        
        # Calculate profit
        total_cost = source_total + source_fee_amount + target_fee_amount + shipping_cost
        profit = target_total - total_cost
        
        # Calculate profit margin
        profit_margin = (profit / target_total) * 100 if target_total > 0 else 0
        
        return {
            'source_price': source_price,
            'target_price': target_price,
            'shipping_cost': shipping_cost,
            'source_fees': source_fee_amount,
            'target_fees': target_fee_amount,
            'total_cost': total_cost,
            'profit': profit,
            'profit_margin': profit_margin,
            'profit_per_unit': profit / quantity if quantity > 0 else 0,
            'roi': (profit / total_cost) * 100 if total_cost > 0 else 0
        }
    
    @staticmethod
    def evaluate_opportunity(
        source_product: Dict,
        target_platform: str,
        min_profit: float = 10.0,
        min_margin: float = 20.0
    ) -> Optional[Dict]:
        """
        Evaluate if an arbitrage opportunity meets the criteria.
        
        Args:
            source_product: Dictionary containing source product info
            target_platform: Target platform to sell on
            min_profit: Minimum profit in dollars
            min_margin: Minimum profit margin percentage
            
        Returns:
            Dictionary with opportunity details if profitable, None otherwise
        """
        try:
            # Get target price (could be from historical data or pricing strategy)
            target_price = source_product.get('suggested_price', source_product['price'] * 1.5)
            
            # Calculate profit metrics
            profit_data = ProfitCalculator.calculate_profit(
                source_price=source_product['price'],
                target_price=target_price,
                source_platform=source_product['platform'],
                target_platform=target_platform,
                shipping_cost=source_product.get('shipping_cost', 0.0)
            )
            
            # Check if opportunity meets criteria
            if (profit_data['profit'] >= min_profit and 
                profit_data['profit_margin'] >= min_margin):
                return {
                    **profit_data,
                    'source_url': source_product.get('url', ''),
                    'target_platform': target_platform,
                    'product_title': source_product.get('title', '')
                }
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating opportunity: {e}")
            return None
