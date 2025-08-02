"""Product and price history models."""
from datetime import datetime
from .. import db

class Product(db.Model):
    """Product model for tracking items across marketplaces."""
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    upc = db.Column(db.String(12), unique=True, index=True)
    ean = db.Column(db.String(13), unique=True, index=True)
    asin = db.Column(db.String(10), unique=True, index=True)
    mpn = db.Column(db.String(100), index=True)
    brand = db.Column(db.String(100))
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(512))
    description = db.Column(db.Text)
    weight = db.Column(db.Float)  # in grams
    dimensions = db.Column(db.String(100))  # format: "LxWxH" in cm
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = db.relationship('ProductPriceHistory', backref='product', lazy='dynamic')
    opportunities = db.relationship('ArbitrageOpportunity', backref='product', lazy='dynamic')
    
    def current_price(self, marketplace_id=None):
        """Get the current price for this product, optionally filtered by marketplace."""
        query = self.prices.order_by(ProductPriceHistory.timestamp.desc())
        if marketplace_id:
            query = query.filter_by(marketplace_id=marketplace_id)
        return query.first()
    
    def price_history(self, days=30, marketplace_id=None):
        """Get price history for this product."""
        cutoff = datetime.utcnow() - datetime.timedelta(days=days)
        query = self.prices.filter(ProductPriceHistory.timestamp >= cutoff)
        if marketplace_id:
            query = query.filter_by(marketplace_id=marketplace_id)
        return query.order_by(ProductPriceHistory.timestamp).all()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'upc': self.upc,
            'brand': self.brand,
            'category': self.category,
            'image_url': self.image_url,
            'current_price': self.current_price().to_dict() if self.current_price() else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Product {self.name}>'


class ProductPriceHistory(db.Model):
    """Historical price data for products."""
    __tablename__ = 'product_price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    marketplace_id = db.Column(db.Integer, db.ForeignKey('marketplace.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    in_stock = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer)
    buy_box_winner = db.Column(db.Boolean, default=False)
    seller_id = db.Column(db.String(100))
    seller_name = db.Column(db.String(255))
    shipping_cost = db.Column(db.Numeric(10, 2))
    condition = db.Column(db.String(50))  # new, used, refurbished, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'marketplace_id': self.marketplace_id,
            'price': float(self.price) if self.price else None,
            'currency': self.currency,
            'in_stock': self.in_stock,
            'stock_quantity': self.stock_quantity,
            'buy_box_winner': self.buy_box_winner,
            'shipping_cost': float(self.shipping_cost) if self.shipping_cost else None,
            'condition': self.condition,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __repr__(self):
        return f'<ProductPriceHistory {self.product_id} @ {self.price} {self.currency}>'
