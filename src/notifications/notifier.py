import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Union
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Notifier:
    """Handles sending notifications via email and SMS."""
    
    def __init__(self):
        """Initialize the notifier with configuration from environment variables."""
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.sender_email = os.getenv('SENDER_EMAIL', self.smtp_username)
        
        # SMS configuration (using email-to-SMS gateway)
        self.sms_gateway = os.getenv('SMS_GATEWAY')
        
        # Notification preferences
        self.notify_email = os.getenv('NOTIFY_EMAIL', '').lower() == 'true'
        self.notify_sms = os.getenv('NOTIFY_SMS', '').lower() == 'true'
        self.notification_recipients = os.getenv('NOTIFICATION_RECIPIENTS', '').split(',')
    
    def send_notification(self, 
                        subject: str, 
                        message: str, 
                        notification_type: str = 'info') -> bool:
        """
        Send a notification via email and/or SMS based on preferences.
        
        Args:
            subject: Notification subject
            message: Notification message content
            notification_type: Type of notification ('info', 'warning', 'error', 'success')
            
        Returns:
            bool: True if all notifications were sent successfully, False otherwise
        """
        success = True
        
        if not self.notification_recipients:
            logger.warning("No notification recipients configured")
            return False
        
        # Send email notification if enabled
        if self.notify_email and self.smtp_username and self.smtp_password:
            try:
                self._send_email(subject, message, notification_type)
                logger.info("Email notification sent successfully")
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
                success = False
        
        # Send SMS notification if enabled
        if self.notify_sms and self.sms_gateway:
            try:
                self._send_sms(subject + " " + message[:140])
                logger.info("SMS notification sent successfully")
            except Exception as e:
                logger.error(f"Failed to send SMS notification: {e}")
                success = False
        
        return success
    
    def _send_email(self, subject: str, message: str, notification_type: str) -> None:
        """Send an email notification."""
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(self.notification_recipients)
        msg['Subject'] = f"[SuperArb] {subject}"
        
        # Create HTML version of message
        html = f"""
        <html>
          <head></head>
          <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
              <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h2 style="color: #333;">{subject}</h2>
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 15px;">
                  <p style="color: #555; line-height: 1.6;">
                    {message.replace('\n', '<br>')}
                  </p>
                </div>
                <div style="margin-top: 20px; font-size: 12px; color: #777; text-align: center;">
                  This is an automated message from SuperArb. Please do not reply to this email.
                </div>
              </div>
            </div>
          </body>
        </html>
        """
        
        # Attach HTML version
        msg.attach(MIMEText(html, 'html'))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
    
    def _send_sms(self, message: str) -> None:
        """Send an SMS notification using email-to-SMS gateway."""
        if not self.sms_gateway:
            raise ValueError("SMS gateway not configured")
        
        # Create a simple text email for SMS
        msg = MIMEText(message)
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(f"{recipient}@{self.sms_gateway}" for recipient in self.notification_recipients)
        msg['Subject'] = ""  # Some gateways require empty subject for SMS
        
        # Connect to SMTP server and send SMS
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
    
    def notify_arbitrage_opportunity(self, opportunity: Dict) -> bool:
        """Send a notification about a new arbitrage opportunity."""
        subject = f"💰 New Arbitrage Opportunity: {opportunity.get('title', 'Untitled')}"
        
        message = f"""
        🚀 New Arbitrage Opportunity Found!
        
        Product: {opportunity.get('title', 'N/A')}
        Source: {opportunity.get('source_platform', 'N/A').title()}
        Target: {opportunity.get('target_platform', 'N/A').title()}
        
        Source Price: ${opportunity.get('source_price', 0):.2f}
        Target Price: ${opportunity.get('target_price', 0):.2f}
        Estimated Profit: ${opportunity.get('profit', 0):.2f} ({opportunity.get('margin', 0):.1f}%)
        
        Source URL: {opportunity.get('source_url', 'N/A')}
        Target URL: {opportunity.get('target_url', 'N/A')}
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_notification(subject, message.strip(), 'success')
    
    def notify_order_update(self, order: Dict) -> bool:
        """Send a notification about an order status update."""
        subject = f"📦 Order Update: {order.get('status', 'Status Update')} - {order.get('order_id', '')}"
        
        message = f"""
        📦 Order Status Update
        
        Order ID: {order.get('order_id', 'N/A')}
        Status: {order.get('status', 'N/A')}
        
        Product: {order.get('product_name', 'N/A')}
        Quantity: {order.get('quantity', 1)}
        Total: ${order.get('total', 0):.2f}
        
        Customer: {order.get('customer_name', 'N/A')}
        Shipping: {order.get('shipping_address', 'N/A')}
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_notification(subject, message.strip(), 'info')
    
    def notify_error(self, error_message: str, context: str = "") -> bool:
        """Send an error notification."""
        subject = "❌ Error in SuperArb Application"
        
        message = f"""
        ❌ An error occurred in the SuperArb application
        
        Error: {error_message}
        
        Context: {context or 'No additional context provided'}
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_notification(subject, message.strip(), 'error')

# Example usage
if __name__ == "__main__":
    # Example configuration (in production, use environment variables)
    import os
    os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
    os.environ['SMTP_PORT'] = '587'
    os.environ['SMTP_USERNAME'] = 'your-email@gmail.com'
    os.environ['SMTP_PASSWORD'] = 'your-app-password'
    os.environ['NOTIFICATION_RECIPIENTS'] = 'recipient@example.com,1234567890'
    os.environ['SMS_GATEWAY'] = 'vtext.com'  # For Verizon, other carriers have different domains
    
    notifier = Notifier()
    
    # Test notification
    notifier.send_notification(
        "Test Notification",
        "This is a test notification from SuperArb.\n\n"
        "If you're receiving this, the notification system is working correctly!",
        'info'
    )
    
    # Test arbitrage opportunity notification
    notifier.notify_arbitrage_opportunity({
        'title': 'Wireless Earbuds',
        'source_platform': 'amazon',
        'target_platform': 'ebay',
        'source_price': 29.99,
        'target_price': 59.99,
        'profit': 21.01,
        'margin': 35.0,
        'source_url': 'https://amazon.com/dp/B08N5KWB9H',
        'target_url': 'https://ebay.com/itm/1234567890'
    })
    
    # Test order update notification
    notifier.notify_order_update({
        'order_id': 'ORD-12345',
        'status': 'Shipped',
        'product_name': 'Wireless Earbuds',
        'quantity': 2,
        'total': 59.98,
        'customer_name': 'John Doe',
        'shipping_address': '123 Main St, Anytown, USA 12345'
    })
    
    # Test error notification
    notifier.notify_error(
        "Failed to process order ORD-12345",
        "Payment processing failed due to insufficient funds"
    )
