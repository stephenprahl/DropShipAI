import logging
import sys
import traceback
from typing import Optional, Type, Dict, Any
from datetime import datetime, timedelta

from src.notifications.messenger import get_messenger

class ErrorHandler:
    """Handles application errors and sends notifications for critical ones."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_notification: Dict[str, datetime] = {}
        self.messenger = get_messenger()
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        notify: bool = True,
        raise_error: bool = True
    ) -> None:
        """Handle an error with logging and optional notification.
        
        Args:
            error: The exception that was raised
            context: Additional context about where the error occurred
            notify: Whether to send a notification for this error
            raise_error: Whether to re-raise the error after handling
        """
        error_type = type(error).__name__
        error_msg = str(error)
        error_key = f"{error_type}:{error_msg}"
        
        # Log the error
        logging.error(
            f"Error: {error_type} - {error_msg}" +
            (f"\nContext: {context}" if context else "") +
            f"\n{traceback.format_exc()}"
        )
        
        # Check if we should notify about this error
        if notify and self._should_notify(error_key):
            self._send_error_notification(error, context)
        
        # Re-raise the error if requested
        if raise_error:
            raise error
    
    def _should_notify(self, error_key: str) -> bool:
        """Determine if we should send a notification for this error."""
        now = datetime.now()
        
        # Increment error count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Get the last time we notified for this error
        last_notified = self.last_notification.get(error_key, datetime.min)
        
        # Check if we've exceeded the error threshold and cooldown period
        error_threshold = 3  # Notify after 3 occurrences
        cooldown_minutes = 60  # 1 hour cooldown between notifications for the same error
        
        if (self.error_counts[error_key] >= error_threshold and 
                (now - last_notified) > timedelta(minutes=cooldown_minutes)):
            self.last_notification[error_key] = now
            self.error_counts[error_key] = 0  # Reset counter after notification
            return True
            
        return False
    
    def _send_error_notification(
        self,
        error: Exception,
        context: Optional[str] = None
    ) -> None:
        """Send a notification about an error."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        subject = f"[ERROR] {error_type}"
        message = (
            f"An error occurred in the SuperArb system:\n\n"
            f"Error: {error_type} - {error_msg}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        
        if context:
            message += f"\nContext: {context}\n"
        
        # Include the traceback
        message += f"\nTraceback:\n{traceback.format_exc()}"
        
        # Send the notification
        self.messenger.send_notification(
            subject=subject,
            message=message,
            notification_type='error'
        )
        
        logging.info(f"Sent error notification for {error_type}")

# Global error handler instance
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def handle_error(
    error: Exception,
    context: Optional[str] = None,
    notify: bool = True,
    raise_error: bool = True
) -> None:
    """Handle an error using the global error handler."""
    get_error_handler().handle_error(error, context, notify, raise_error)
