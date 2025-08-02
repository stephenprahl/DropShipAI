"""Background tasks for the Super Arbitrage application."""
import time
import logging
from datetime import datetime, timedelta
from .. import create_app, db
from ..models import Product, Marketplace, ArbitrageOpportunity, Notification, User, ActivityLog
from ..utils import log_activity

# Configure logging
logger = logging.getLogger(__name__)

# Create a Flask application context
app = create_app()

class BackgroundTask:
    """Base class for background tasks."""
    
    def __init__(self):
        self.app = app
        self.name = self.__class__.__name__
    
    def run(self):
        """Run the task."""
        start_time = time.time()
        logger.info(f"Starting {self.name}...")
        
        try:
            with self.app.app_context():
                result = self.execute()
                logger.info(f"Completed {self.name} in {time.time() - start_time:.2f} seconds")
                return result
        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}", exc_info=True)
            log_activity('task_error', {
                'task': self.name,
                'error': str(e),
                'traceback': str(e.__traceback__)
            })
            raise


class PriceScraper(BackgroundTask):
    """Background task for scraping product prices."""
    
    def __init__(self, marketplace_id=None):
        super().__init__()
        self.marketplace_id = marketplace_id
    
    def execute(self):
        """Execute the price scraping task."""
        from .scrapers import get_scraper_for_marketplace
        
        # Get active marketplaces
        query = Marketplace.query.filter_by(is_active=True)
        if self.marketplace_id:
            query = query.filter_by(id=self.marketplace_id)
        
        marketplaces = query.all()
        
        if not marketplaces:
            logger.warning("No active marketplaces found")
            return {"status": "skipped", "reason": "No active marketplaces"}
        
        results = []
        
        for marketplace in marketplaces:
            scraper = get_scraper_for_marketplace(marketplace.code)
            if not scraper:
                logger.warning(f"No scraper available for {marketplace.name}")
                continue
            
            logger.info(f"Scraping prices for {marketplace.name}...")
            
            # Get products that need to be updated
            # Update products that haven't been updated in the last 24 hours
            update_threshold = datetime.utcnow() - timedelta(hours=24)
            
            products = Product.query.join(Product.prices)\
                                 .filter(
                                     Product.marketplace_id == marketplace.id,
                                     Product.is_active == True,
                                     Product.updated_at < update_threshold
                                 )\
                                 .limit(100)\
                                 .all()
            
            if not products:
                logger.info(f"No products to update for {marketplace.name}")
                continue
            
            logger.info(f"Updating {len(products)} products from {marketplace.name}")
            
            updated = 0
            errors = 0
            
            for product in products:
                try:
                    # Get current price from the marketplace
                    price_data = scraper.get_product_price(product.external_id)
                    
                    if price_data and 'price' in price_data:
                        # Update product price
                        old_price = product.current_price
                        new_price = price_data['price']
                        
                        product.price = new_price
                        product.updated_at = datetime.utcnow()
                        
                        # Log price change
                        if old_price != new_price:
                            product.log_price_change(
                                marketplace_id=marketplace.id,
                                old_price=old_price,
                                new_price=new_price,
                                in_stock=price_data.get('in_stock', True),
                                stock_quantity=price_data.get('stock_quantity')
                            )
                        
                        db.session.commit()
                        updated += 1
                        
                        # Check for arbitrage opportunities
                        self.check_arbitrage_opportunities(product)
                        
                except Exception as e:
                    logger.error(f"Error updating product {product.id}: {str(e)}")
                    errors += 1
                    db.session.rollback()
            
            results.append({
                'marketplace': marketplace.name,
                'products_updated': updated,
                'errors': errors
            })
        
        return {
            'status': 'completed',
            'results': results
        }
    
    def check_arbitrage_opportunities(self, product):
        """Check for arbitrage opportunities for a product."""
        from .scrapers import get_scraper_for_marketplace
        
        # Get all other marketplaces
        other_marketplaces = Marketplace.query.filter(
            Marketplace.id != product.marketplace_id,
            Marketplace.is_active == True
        ).all()
        
        if not other_marketplaces:
            return
        
        opportunities = []
        
        for target_marketplace in other_marketplaces:
            try:
                scraper = get_scraper_for_marketplace(target_marketplace.code)
                if not scraper:
                    continue
                
                # Search for the same product on the target marketplace
                search_results = scraper.search_products(
                    query=product.name,
                    brand=product.brand,
                    upc=product.upc,
                    asin=product.asin
                )
                
                if not search_results:
                    continue
                
                # For simplicity, take the first result
                target_product = search_results[0]
                
                # Calculate profit
                source_price = product.price
                target_price = target_product['price']
                
                # Get marketplace fees (this would come from a config or database)
                fees = self.calculate_fees(target_marketplace, target_price)
                
                # Calculate shipping costs (this would be estimated or from a shipping API)
                shipping = self.estimate_shipping_costs(product, target_marketplace)
                
                # Calculate profit
                profit_info = calculate_profit(
                    source_price=source_price,
                    target_price=target_price,
                    fees=fees,
                    shipping=shipping
                )
                
                if profit_info['profit'] > 0 and profit_info['profit_margin'] > 0:
                    # Create or update arbitrage opportunity
                    opportunity = ArbitrageOpportunity.query.filter_by(
                        source_product_id=product.id,
                        target_marketplace_id=target_marketplace.id
                    ).first()
                    
                    if not opportunity:
                        opportunity = ArbitrageOpportunity(
                            user_id=product.owner_id,
                            source_product_id=product.id,
                            source_marketplace_id=product.marketplace_id,
                            target_marketplace_id=target_marketplace.id,
                            status='active',
                            profit=profit_info['profit'],
                            profit_margin=profit_info['profit_margin'],
                            source_price=source_price,
                            target_price=target_price,
                            shipping_cost=shipping,
                            fees=fees,
                            target_url=target_product.get('url')
                        )
                        db.session.add(opportunity)
                    else:
                        opportunity.profit = profit_info['profit']
                        opportunity.profit_margin = profit_info['profit_margin']
                        opportunity.source_price = source_price
                        opportunity.target_price = target_price
                        opportunity.shipping_cost = shipping
                        opportunity.fees = fees
                        opportunity.updated_at = datetime.utcnow()
                        
                        # If the opportunity was previously expired, reactivate it
                        if opportunity.status == 'expired':
                            opportunity.status = 'active'
                    
                    opportunities.append(opportunity)
                    
            except Exception as e:
                logger.error(f"Error checking arbitrage opportunity for product {product.id} on {target_marketplace.name}: {str(e)}")
                continue
        
        if opportunities:
            try:
                db.session.commit()
                self.notify_opportunities(opportunities)
            except Exception as e:
                logger.error(f"Error saving arbitrage opportunities: {str(e)}")
                db.session.rollback()
    
    def calculate_fees(self, marketplace, price):
        """Calculate marketplace fees for a given price."""
        # This is a simplified example. In a real app, you would:
        # 1. Get fee structure from the marketplace model or a config
        # 2. Calculate fees based on the price, category, etc.
        # 3. Consider any special promotions or account levels
        
        # Example: 15% of price + $1.00 per item
        return float(price) * 0.15 + 1.00
    
    def estimate_shipping_costs(self, product, marketplace):
        """Estimate shipping costs for a product to a marketplace."""
        # This is a simplified example. In a real app, you would:
        # 1. Get shipping rates from a shipping API (e.g., Shippo, EasyPost)
        # 2. Consider package dimensions, weight, and destination
        # 3. Apply any shipping discounts or promotions
        
        # Example: Flat rate based on weight
        weight = product.weight or 500  # Default to 500g if not set
        
        if weight < 500:  # Up to 500g
            return 3.99
        elif weight < 1000:  # 500g to 1kg
            return 5.99
        else:  # 1kg and up
            return 7.99 + (weight - 1000) / 1000 * 2.00  # $2 per additional kg
    
    def notify_opportunities(self, opportunities):
        """Send notifications for new or updated arbitrage opportunities."""
        from ..models import Notification
        
        for opportunity in opportunities:
            # Skip if this is just an update to an existing opportunity
            if opportunity.updated_at and (datetime.utcnow() - opportunity.updated_at).total_seconds() < 3600:
                continue
            
            # Create notification for the user
            notification = Notification(
                user_id=opportunity.user_id,
                title="New Arbitrage Opportunity",
                message=f"Found a potential profit of ${opportunity.profit:.2f} ({opportunity.profit_margin:.1f}%) on {opportunity.target_marketplace.name}",
                notification_type='opportunity',
                reference_id=opportunity.id,
                reference_type='arbitrage_opportunity',
                status='unread'
            )
            
            db.session.add(notification)
            
            # Log the activity
            log_activity(
                'opportunity_created',
                {
                    'opportunity_id': opportunity.id,
                    'profit': float(opportunity.profit),
                    'margin': float(opportunity.profit_margin),
                    'source_marketplace': opportunity.source_marketplace.name,
                    'target_marketplace': opportunity.target_marketplace.name
                },
                user_id=opportunity.user_id
            )
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error creating notifications: {str(e)}")
            db.session.rollback()


class OpportunityChecker(BackgroundTask):
    """Background task for checking and updating arbitrage opportunities."""
    
    def __init__(self, opportunity_id=None):
        super().__init__()
        self.opportunity_id = opportunity_id
    
    def execute(self):
        """Execute the opportunity checking task."""
        from .scrapers import get_scraper_for_marketplace
        
        # Get opportunities to check
        query = ArbitrageOpportunity.query.filter_by(status='active')
        
        if self.opportunity_id:
            query = query.filter_by(id=self.opportunity_id)
        else:
            # Only check opportunities that haven't been updated in the last hour
            last_hour = datetime.utcnow() - timedelta(hours=1)
            query = query.filter(ArbitrageOpportunity.updated_at < last_hour)
        
        opportunities = query.limit(100).all()
        
        if not opportunities:
            logger.info("No opportunities to check")
            return {"status": "skipped", "reason": "No opportunities to check"}
        
        results = []
        
        for opportunity in opportunities:
            try:
                # Get source product
                product = Product.query.get(opportunity.source_product_id)
                if not product or not product.is_active:
                    opportunity.status = 'expired'
                    opportunity.updated_at = datetime.utcnow()
                    continue
                
                # Get target marketplace scraper
                scraper = get_scraper_for_marketplace(opportunity.target_marketplace.code)
                if not scraper:
                    logger.warning(f"No scraper available for {opportunity.target_marketplace.name}")
                    continue
                
                # Get current price on target marketplace
                price_data = scraper.get_product_price(opportunity.target_product_id or "")
                if not price_data or 'price' not in price_data:
                    # Product no longer available on target marketplace
                    opportunity.status = 'expired'
                    opportunity.updated_at = datetime.utcnow()
                    continue
                
                # Update opportunity with new price
                old_price = opportunity.target_price
                new_price = price_data['price']
                
                if old_price != new_price:
                    # Recalculate profit
                    fees = self.calculate_fees(opportunity.target_marketplace, new_price)
                    shipping = opportunity.shipping_cost  # Could also be updated
                    
                    profit_info = calculate_profit(
                        source_price=opportunity.source_price,
                        target_price=new_price,
                        fees=fees,
                        shipping=shipping
                    )
                    
                    # Update opportunity
                    opportunity.target_price = new_price
                    opportunity.profit = profit_info['profit']
                    opportunity.profit_margin = profit_info['profit_margin']
                    opportunity.fees = fees
                    opportunity.updated_at = datetime.utcnow()
                    
                    # If profit is too low, mark as expired
                    if profit_info['profit'] < 1.00 or profit_info['profit_margin'] < 5.0:
                        opportunity.status = 'expired'
                    
                    # Log the price change
                    log_activity(
                        'opportunity_updated',
                        {
                            'opportunity_id': opportunity.id,
                            'old_price': float(old_price),
                            'new_price': float(new_price),
                            'profit': float(profit_info['profit']),
                            'margin': float(profit_info['profit_margin'])
                        },
                        user_id=opportunity.user_id
                    )
                
                results.append({
                    'opportunity_id': opportunity.id,
                    'status': opportunity.status,
                    'profit': float(opportunity.profit),
                    'margin': float(opportunity.profit_margin)
                })
                
            except Exception as e:
                logger.error(f"Error checking opportunity {opportunity.id}: {str(e)}")
                results.append({
                    'opportunity_id': opportunity.id,
                    'status': 'error',
                    'error': str(e)
                })
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error saving opportunity updates: {str(e)}")
            db.session.rollback()
        
        return {
            'status': 'completed',
            'checked': len(opportunities),
            'results': results
        }
    
    def calculate_fees(self, marketplace, price):
        """Calculate marketplace fees for a given price."""
        # Same as in PriceScraper, could be refactored to a shared method
        return float(price) * 0.15 + 1.00


def calculate_profit(source_price, target_price, fees=0, shipping=0, quantity=1):
    """Calculate profit and profit margin."""
    try:
        source_price = float(source_price or 0)
        target_price = float(target_price or 0)
        fees = float(fees or 0)
        shipping = float(shipping or 0)
        quantity = int(quantity or 1)
        
        total_cost = (source_price + shipping) * quantity + fees
        total_revenue = target_price * quantity
        profit = total_revenue - total_cost
        profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            'profit': round(profit, 2),
            'profit_margin': round(profit_margin, 2),
            'total_cost': round(total_cost, 2),
            'total_revenue': round(total_revenue, 2)
        }
    except (ValueError, TypeError) as e:
        logger.error(f"Error calculating profit: {str(e)}")
        return {
            'profit': 0,
            'profit_margin': 0,
            'total_cost': 0,
            'total_revenue': 0
        }
