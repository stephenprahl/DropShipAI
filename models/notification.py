"""Notification model for user alerts and messages."""
from datetime import datetime
from enum import Enum
from .. import db

class NotificationType(Enum):
    """Types of notifications."""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    OPPORTUNITY = 'opportunity'
    ALERT = 'alert'
    SYSTEM = 'system'

class NotificationStatus(Enum):
    """Status of a notification."""
    UNREAD = 'unread'
    READ = 'read'
    ARCHIVED = 'archived'
    DELETED = 'deleted'

class Notification(db.Model):
    """User notification model."""
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Notification content
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.Enum(NotificationType), default=NotificationType.INFO, nullable=False)
    
    # Action/Reference
    action_url = db.Column(db.String(512))
    reference_type = db.Column(db.String(50))  # e.g., 'opportunity', 'alert', 'system'
    reference_id = db.Column(db.Integer)  # ID of the referenced item
    
    # Status
    status = db.Column(db.Enum(NotificationStatus), default=NotificationStatus.UNREAD, index=True)
    is_dismissible = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', back_populates='notifications')
    
    def mark_as_read(self, commit=True):
        """Mark notification as read."""
        if self.status != NotificationStatus.READ:
            self.status = NotificationStatus.READ
            self.read_at = datetime.utcnow()
            if commit and db.session:
                db.session.commit()
    
    def mark_as_unread(self, commit=True):
        """Mark notification as unread."""
        self.status = NotificationStatus.UNREAD
        self.read_at = None
        if commit and db.session:
            db.session.commit()
    
    def archive(self, commit=True):
        """Archive the notification."""
        self.status = NotificationStatus.ARCHIVED
        if commit and db.session:
            db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.notification_type.value,
            'status': self.status.value,
            'is_dismissible': self.is_dismissible,
            'action_url': self.action_url,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def create_opportunity_notification(cls, user_id, opportunity, message=None, title=None):
        """Create a notification for a new arbitrage opportunity."""
        if not message:
            message = f"New arbitrage opportunity found with {opportunity.profit_margin:.2f}% margin"
        if not title:
            title = "New Arbitrage Opportunity"
            
        return cls(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.OPPORTUNITY,
            reference_type='opportunity',
            reference_id=opportunity.id,
            action_url=f"/opportunities/{opportunity.id}"
        )
    
    @classmethod
    def create_alert_triggered_notification(cls, user_id, alert, opportunity, message=None, title=None):
        """Create a notification for a triggered alert."""
        if not message:
            message = (f"Alert triggered! Opportunity with {opportunity.profit_margin:.2f}% margin "
                     f"(min: {alert.min_margin or 0}%)")
        if not title:
            title = "Alert Triggered"
            
        return cls(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=NotificationType.ALERT,
            reference_type='alert',
            reference_id=alert.id,
            action_url=f"/alerts/{alert.id}"
        )
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
