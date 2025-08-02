"""Arbitrage opportunity and alert models."""
from datetime import datetime
from decimal import Decimal
from .. import db

class ArbitrageOpportunity(db.Model):
    """Arbitrage opportunity between two marketplaces."""
    __tablename__ = 'arbitrage_opportunity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    # Source and target marketplaces
    source_marketplace_id = db.Column(db.Integer, db.ForeignKey('marketplace.id'), nullable=False)
    target_marketplace_id = db.Column(db.Integer, db.ForeignKey('marketplace.id'), nullable=False)
    
    # Price information
    source_price = db.Column(db.Numeric(10, 2), nullable=False)
    target_price = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    fees = db.Column(db.Numeric(10, 2), default=0)
    profit = db.Column(db.Numeric(10, 2), nullable=False)
    profit_margin = db.Column(db.Numeric(5, 2), nullable=False)  # percentage
    
    # Status and metadata
    status = db.Column(db.String(50), default='active', index=True)  # active, expired, executed, cancelled
    is_auto_trade = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    
    # Timestamps
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source_marketplace = db.relationship('Marketplace', foreign_keys=[source_marketplace_id])
    target_marketplace = db.relationship('Marketplace', foreign_keys=[target_marketplace_id])
    
    def calculate_profitability(self):
        """Calculate and update profit and profit margin."""
        total_cost = self.source_price + (self.shipping_cost or 0) + (self.fees or 0)
        self.profit = self.target_price - total_cost
        self.profit_margin = (float(self.profit) / float(self.target_price)) * 100 if self.target_price > 0 else 0
        return self.profit, self.profit_margin
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'source_marketplace': self.source_marketplace.name if self.source_marketplace else None,
            'target_marketplace': self.target_marketplace.name if self.target_marketplace else None,
            'source_price': float(self.source_price) if self.source_price else None,
            'target_price': float(self.target_price) if self.target_price else None,
            'shipping_cost': float(self.shipping_cost) if self.shipping_cost else None,
            'fees': float(self.fees) if self.fees else None,
            'profit': float(self.profit) if self.profit is not None else None,
            'profit_margin': float(self.profit_margin) if self.profit_margin is not None else None,
            'status': self.status,
            'is_auto_trade': self.is_auto_trade,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ArbitrageOpportunity {self.id}: {self.profit_margin:.2f}% margin>'


class OpportunityAlert(db.Model):
    """Alerts for arbitrage opportunities."""
    __tablename__ = 'opportunity_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('arbitrage_opportunity.id'), nullable=False)
    
    # Alert criteria
    min_profit = db.Column(db.Numeric(10, 2))
    min_margin = db.Column(db.Numeric(5, 2))  # percentage
    max_price = db.Column(db.Numeric(10, 2))
    
    # Alert status
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_triggered = db.Column(db.DateTime)
    trigger_count = db.Column(db.Integer, default=0)
    
    # Notification preferences
    notify_email = db.Column(db.Boolean, default=True)
    notify_push = db.Column(db.Boolean, default=False)
    notify_webhook = db.Column(db.Boolean, default=False)
    webhook_url = db.Column(db.String(512))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunity = db.relationship('ArbitrageOpportunity', backref='alerts')
    
    def should_trigger(self, opportunity):
        """Check if the alert should trigger for the given opportunity."""
        if not self.is_active:
            return False
            
        conditions = []
        if self.min_profit is not None:
            conditions.append(opportunity.profit >= self.min_profit)
        if self.min_margin is not None:
            conditions.append(opportunity.profit_margin >= self.min_margin)
        if self.max_price is not None:
            conditions.append(opportunity.source_price <= self.max_price)
            
        return all(conditions)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'opportunity_id': self.opportunity_id,
            'min_profit': float(self.min_profit) if self.min_profit is not None else None,
            'min_margin': float(self.min_margin) if self.min_margin is not None else None,
            'max_price': float(self.max_price) if self.max_price is not None else None,
            'is_active': self.is_active,
            'notify_email': self.notify_email,
            'notify_push': self.notify_push,
            'notify_webhook': self.notify_webhook,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'trigger_count': self.trigger_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<OpportunityAlert {self.id} for Opportunity {self.opportunity_id}>'
