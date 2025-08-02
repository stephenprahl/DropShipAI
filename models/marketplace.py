"""Marketplace and credentials models."""
from datetime import datetime
from .. import db

class Marketplace(db.Model):
    """Marketplace model for different e-commerce platforms."""
    __tablename__ = 'marketplace'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., 'Amazon', 'eBay'
    code = db.Column(db.String(50), nullable=False, unique=True)  # e.g., 'amazon', 'ebay'
    base_url = db.Column(db.String(255))
    logo_url = db.Column(db.String(512))
    is_active = db.Column(db.Boolean, default=True)
    requires_api = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credentials = db.relationship('MarketplaceCredentials', backref='marketplace', lazy='dynamic')
    price_history = db.relationship('ProductPriceHistory', backref='marketplace', lazy='dynamic')
    
    def __repr__(self):
        return f'<Marketplace {self.name}>'


class MarketplaceCredentials(db.Model):
    """API credentials for marketplaces."""
    __tablename__ = 'marketplace_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    marketplace_id = db.Column(db.Integer, db.ForeignKey('marketplace.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Common credentials (some fields may be null depending on the marketplace)
    api_key = db.Column(db.String(255))
    api_secret = db.Column(db.String(255))
    access_token = db.Column(db.String(512))
    refresh_token = db.Column(db.String(512))
    seller_id = db.Column(db.String(100))
    marketplace_id_code = db.Column(db.String(100))  # e.g., Amazon's Merchant ID
    
    # Additional metadata as JSON
    metadata = db.Column(db.JSON)
    
    # Status
    is_valid = db.Column(db.Boolean, default=True)
    last_validated = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary, optionally including sensitive data."""
        data = {
            'id': self.id,
            'marketplace_id': self.marketplace_id,
            'marketplace_name': self.marketplace.name if self.marketplace else None,
            'is_valid': self.is_valid,
            'last_validated': self.last_validated.isoformat() if self.last_validated else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_sensitive:
            data.update({
                'api_key': self.api_key,
                'seller_id': self.seller_id,
                'marketplace_id_code': self.marketplace_id_code,
                'metadata': self.metadata
            })
        
        return data
    
    def __repr__(self):
        return f'<MarketplaceCredentials {self.marketplace.name} for User {self.user_id}>'
