import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from .config_manager import get_config_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Messenger:
    """Handles sending notifications through various channels."""
    
    def __init__(self):
        self.config = get_config_manager()
    
    def send_notification(
        self,
        subject: str,
        message: str,
        notification_type: str = 'info',
        **kwargs
    ) -> Dict[str, bool]:
        """Send a notification through the appropriate channels."""
        if self._is_quiet_hours() and notification_type != 'error':
            logger.info("Skipping non-critical notification during quiet hours")
            return {}
        
        results = {}
        
        # Send email if enabled and not rate limited
        if self._should_send(notification_type, 'email'):
            results['email'] = self._send_email(subject, message, **kwargs)
        
        # Send SMS if enabled and not rate limited
        if self._should_send(notification_type, 'sms'):
            results['sms'] = self._send_sms(f"{subject}: {message}")
        
        return results
    
    def _should_send(self, notification_type: str, channel: str) -> bool:
        """Check if a notification should be sent."""
        if not self.config.get(f'{channel}.enabled', False):
            return False
        
        # Check notification type preferences
        pref_key = f'preferences.notify_on_{notification_type}'
        if not self.config.get(pref_key, True):
            return False
            
        return True
    
    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        quiet_start, quiet_end = self.config.get('preferences.quiet_hours', ('22:00', '08:00'))
        now = datetime.now()
        
        start_hour, start_minute = map(int, quiet_start.split(':'))
        end_hour, end_minute = map(int, quiet_end.split(':'))
        
        start_time = now.replace(hour=start_hour, minute=start_minute)
        end_time = now.replace(hour=end_hour, minute=end_minute)
        
        if start_time > end_time:
            return now >= start_time or now <= end_time
        return start_time <= now <= end_time
    
    def _send_email(
        self,
        subject: str,
        message: str,
        **kwargs
    ) -> bool:
        """Send an email notification."""
        try:
            email_config = self.config.get_email_config()
            
            if not all([email_config['smtp_server'], email_config['smtp_username']]):
                logger.warning("Email not configured properly")
                return False
            
            recipients = self.config.get_recipients()['email']
            if not recipients:
                logger.warning("No email recipients configured")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{email_config['sender_name']} <{email_config['sender_email']}>"
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject
            
            # Create HTML version
            html = f"""
            <html>
              <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                  <h2>{subject}</h2>
                  <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                    {message.replace('\n', '<br>')}
                  </div>
                </div>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['smtp_username'], email_config['smtp_password'])
                server.send_message(msg)
            
            logger.info(f"Email sent to {', '.join(recipients)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_sms(self, message: str) -> bool:
        """Send an SMS notification."""
        # This is a placeholder - in a real implementation, you would integrate with an SMS gateway
        try:
            sms_config = self.config.get_sms_config()
            if not sms_config['enabled']:
                return False
                
            # Example implementation for Twilio
            if sms_config['provider'] == 'twilio':
                from twilio.rest import Client
                
                client = Client(
                    sms_config['twilio']['account_sid'],
                    sms_config['twilio']['auth_token']
                )
                
                recipients = self.config.get_recipients()['phone']
                for phone in recipients:
                    client.messages.create(
                        to=phone,
                        from_=sms_config['twilio']['from_number'],
                        body=message[:160]  # Truncate to 160 chars
                    )
                
                logger.info(f"SMS sent to {len(recipients)} recipients")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

# Global instance
_messenger = None

def get_messenger() -> Messenger:
    """Get the global messenger instance."""
    global _messenger
    if _messenger is None:
        _messenger = Messenger()
    return _messenger
