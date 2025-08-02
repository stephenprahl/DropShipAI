"""API Key model for user authentication."""
from datetime import datetime, timedelta
from .. import db

class APIKey(db.Model):
    """API Key model for user authentication."""
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    permissions = db.Column(db.String(20), default='read', nullable=False)  # read, read_write, admin
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('api_keys', lazy=True, cascade='all, delete-orphan'))
    
    def __init__(self, **kwargs):
        """Initialize API key with default values."""
        super(APIKey, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
    
    def __repr__(self):
        """String representation of the API key."""
        return f'<APIKey {self.name} ({self.key[:8]}...)>'
    
    def to_dict(self):
        """Convert API key to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key,
            'permissions': self.permissions,
            'is_active': self.is_active,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @property
    def is_expired(self):
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired
    
    def has_permission(self, required_permission):
        """Check if the API key has the required permission."""
        if self.permissions == 'admin':
            return True
        
        if required_permission == 'read':
            return self.permissions in ['read', 'read_write']
        
        if required_permission == 'write':
            return self.permissions == 'read_write'
        
        return False
    
    def update_last_used(self):
        """Update the last used timestamp."""
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def revoke(self):
        """Revoke the API key."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_by_key(cls, key):
        """Get API key by its value."""
        return cls.query.filter_by(key=key, is_active=True).first()
    
    @classmethod
    def get_user_keys(cls, user_id):
        """Get all API keys for a user."""
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def create_for_user(cls, user_id, name, permissions='read', expires_in=None):
        """Create a new API key for a user."""
        from ..utils import generate_api_key
        
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        key = cls(
            user_id=user_id,
            name=name,
            key=generate_api_key(user_id, expires_in=expires_in),
            permissions=permissions,
            expires_at=expires_at
        )
        
        db.session.add(key)
        db.session.commit()
        
        return key
