"""
Notification system for SuperArb.

This module provides a unified interface for sending notifications through
multiple channels (email, SMS, webhooks) with rate limiting and error handling.

Example usage:
    from src.notifications import (
        notify_opportunity,
        notify_order_update,
        notify_error
    )
    
    # Notify about a new arbitrage opportunity
    notify_opportunity({
        'title': 'Wireless Earbuds',
        'source_platform': 'amazon',
        'target_platform': 'ebay',
        'source_price': 29.99,
        'target_price': 59.99,
        'estimated_profit': 21.01,
        'profit_margin': 35.0,
        'source_url': 'https://amazon.com/dp/B08N5KWB9H',
        'target_url': 'https://ebay.com/itm/1234567890'
    })
    
    # Notify about an order update
    notify_order_update({
        'order_id': 'ORD-12345',
        'status': 'shipped',
        'product_name': 'Wireless Earbuds',
        'customer_name': 'John Doe',
        'tracking_number': '1Z999AA1234567890',
        'estimated_delivery': '2023-12-25'
    })
    
    # Notify about an error
    try:
        1 / 0
    except Exception as e:
        notify_error(e, context="Error in order processing")
"""

from typing import Dict, Any, Optional
import logging

from .messenger import get_messenger
from .config_manager import get_config_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def notify_opportunity(opportunity: Dict[str, Any]) -> Dict[str, bool]:
    """
    Send a notification about a new arbitrage opportunity.
    
    Args:
        opportunity: Dictionary containing opportunity details with keys:
            - title: Product title
            - source_platform: Source platform name (e.g., 'amazon')
            - target_platform: Target platform name (e.g., 'ebay')
            - source_price: Price on the source platform
            - target_price: Expected selling price on target platform
            - estimated_profit: Estimated profit amount
            - profit_margin: Profit margin as a percentage
            - source_url: URL of the source product
            - target_url: URL of the target listing (if applicable)
    
    Returns:
        Dictionary with notification status for each channel
    """
    config = get_config_manager()
    
    # Check if we should notify about this opportunity
    min_profit = config.get('preferences.min_profit_threshold', 20.0)
    if opportunity.get('estimated_profit', 0) < min_profit:
        logger.info(f"Skipping opportunity notification - profit below threshold (${min_profit})")
        return {}
    
    # Format the message
    subject = f"💰 New Arbitrage Opportunity: {opportunity.get('title', 'Untitled')}"
    
    message = f"""
    🚀 New Arbitrage Opportunity Found!
    
    Product: {title}
    Source: {source_platform} - ${source_price:.2f}
    Target: {target_platform} - ${target_price:.2f}
    
    Estimated Profit: ${estimated_profit:.2f} ({profit_margin:.1f}%)
    
    Source URL: {source_url}
    Target URL: {target_url}
    
    Time: {time}
    """.format(
        title=opportunity.get('title', 'N/A'),
        source_platform=opportunity.get('source_platform', 'N/A').title(),
        target_platform=opportunity.get('target_platform', 'N/A').title(),
        source_price=opportunity.get('source_price', 0),
        target_price=opportunity.get('target_price', 0),
        estimated_profit=opportunity.get('estimated_profit', 0),
        profit_margin=opportunity.get('profit_margin', 0),
        source_url=opportunity.get('source_url', 'N/A'),
        target_url=opportunity.get('target_url', 'N/A'),
        time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Send the notification
    messenger = get_messenger()
    return messenger.send_notification(
        subject=subject,
        message=message.strip(),
        notification_type='arbitrage_opportunity',
        **opportunity
    )

def notify_order_update(order: Dict[str, Any]) -> Dict[str, bool]:
    """
    Send a notification about an order status update.
    
    Args:
        order: Dictionary containing order details with keys:
            - order_id: Order ID
            - status: Order status (e.g., 'placed', 'shipped', 'delivered')
            - product_name: Name of the product
            - quantity: Quantity ordered
            - total: Total order amount
            - customer_name: Customer name
            - shipping_address: Shipping address
            - tracking_number: Tracking number (if available)
            - estimated_delivery: Estimated delivery date (if available)
    
    Returns:
        Dictionary with notification status for each channel
    """
    # Format status for display
    status_display = order.get('status', '').title()
    
    # Format the message
    subject = f"📦 Order {status_display}: {order.get('order_id', '')}"
    
    message = f"""
    📦 Order Status Update
    
    Order ID: {order_id}
    Status: {status_display}
    
    Product: {product_name}
    Quantity: {quantity}
    Total: ${total:.2f}
    
    Customer: {customer_name}
    Shipping: {shipping_address}
    """
    
    # Add tracking info if available
    if order.get('tracking_number'):
        message += f"\nTracking: {order['tracking_number']}"
    
    # Add estimated delivery if available
    if order.get('estimated_delivery'):
        message += f"\nEstimated Delivery: {order['estimated_delivery']}"
    
    # Format the message with order data
    message = message.format(
        order_id=order.get('order_id', 'N/A'),
        status_display=status_display,
        product_name=order.get('product_name', 'N/A'),
        quantity=order.get('quantity', 1),
        total=float(order.get('total', 0)),
        customer_name=order.get('customer_name', 'N/A'),
        shipping_address=order.get('shipping_address', 'N/A')
    )
    
    # Send the notification
    messenger = get_messenger()
    return messenger.send_notification(
        subject=subject,
        message=message.strip(),
        notification_type='order_update',
        **order
    )

def notify_error(
    error: Exception,
    context: Optional[str] = None,
    notify: bool = True
) -> Dict[str, bool]:
    """
    Send a notification about an error.
    
    Args:
        error: The exception that was raised
        context: Additional context about where the error occurred
        notify: Whether to send a notification (or just log the error)
    
    Returns:
        Dictionary with notification status for each channel
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Log the error
    logger.error(
        f"Error: {error_type} - {error_msg}" +
        (f"\nContext: {context}" if context else ""),
        exc_info=True
    )
    
    if not notify:
        return {}
    
    # Format the message
    subject = f"❌ Error: {error_type}"
    
    message = f"""
    ❌ An error occurred in the SuperArb system
    
    Error: {error_type} - {error_msg}
    
    Context: {context}
    
    Time: {time}
    """.format(
        error_type=error_type,
        error_msg=error_msg,
        context=context or 'No additional context',
        time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Send the notification
    messenger = get_messenger()
    return messenger.send_notification(
        subject=subject,
        message=message.strip(),
        notification_type='error'
    )

# Import these at the bottom to avoid circular imports
from datetime import datetime
from .messenger import get_messenger
from .config_manager import get_config_manager
