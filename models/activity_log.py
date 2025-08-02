"""Activity Log model for tracking user actions."""
from datetime import datetime
from .. import db
from sqlalchemy.dialects.postgresql import JSONB

class ActivityLog(db.Model):
    """Activity Log model for tracking user actions."""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(JSONB, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('activities', lazy=True))
    
    def __init__(self, **kwargs):
        """Initialize activity log with default values."""
        super(ActivityLog, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    def __repr__(self):
        """String representation of the activity log."""
        return f'<ActivityLog {self.action} by {self.user_id or "system"} at {self.created_at}>'
    
    def to_dict(self):
        """Convert activity log to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def log_activity(cls, user_id, action, details=None, ip_address=None, user_agent=None, commit=True):
        """Log an activity."""
        if isinstance(details, dict):
            details = {k: v for k, v in details.items() if v is not None}
        
        log = cls(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log)
        
        if commit:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # Log the error but don't fail the request
                from .. import app
                app.logger.error(f"Failed to log activity: {str(e)}")
        
        return log
    
    @classmethod
    def get_user_activities(cls, user_id, page=1, per_page=20):
        """Get paginated activities for a user."""
        return cls.query.filter_by(user_id=user_id)\
                       .order_by(cls.created_at.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    
    @classmethod
    def get_recent_activities(cls, limit=50):
        """Get recent activities across all users."""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def search_activities(cls, query, page=1, per_page=20):
        """Search activities by action or details."""
        search = f"%{query}%"
        return cls.query.filter(
            (cls.action.ilike(search)) |
            (cls.details.cast(db.String).ilike(search))
        ).order_by(cls.created_at.desc())\
         .paginate(page=page, per_page=per_page, error_out=False)
    
    @classmethod
    def cleanup_old_logs(cls, days=90):
        """Remove activity logs older than the specified number of days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = cls.query.filter(cls.created_at < cutoff_date).delete()
        db.session.commit()
        return deleted
