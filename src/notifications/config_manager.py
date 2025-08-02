import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """Manages loading and accessing notification configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If not provided, looks for
                       'config/notifications.yaml' in the project root.
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            'notifications.yaml'
        )
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from the YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found at {self.config_path}. "
                "Please create one based on the example configuration."
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot notation key.
        
        Args:
            key: Dot notation key (e.g., 'email.smtp_server')
            default: Default value to return if key is not found
            
        Returns:
            The configuration value or default if not found
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration."""
        return {
            'enabled': self.get('email.enabled', False),
            'smtp_server': self.get('email.smtp_server', ''),
            'smtp_port': self.get('email.smtp_port', 587),
            'smtp_username': self.get('email.smtp_username', ''),
            'smtp_password': self.get('email.smtp_password', ''),
            'sender_email': self.get('email.sender_email', ''),
            'sender_name': self.get('email.sender_name', 'SuperArb')
        }
    
    def get_sms_config(self) -> Dict[str, Any]:
        """Get SMS configuration."""
        return {
            'enabled': self.get('sms.enabled', False),
            'provider': self.get('sms.provider', ''),
            'twilio': self.get('sms.twilio', {})
        }
    
    def get_recipients(self, notification_type: str = 'default') -> Dict[str, list]:
        """Get recipients for a specific notification type.
        
        Args:
            notification_type: Type of notification ('default', 'arbitrage_opportunities', 
                             'order_updates', 'error_alerts')
            
        Returns:
            Dictionary with 'email' and 'phone' lists of recipients
        """
        # Get specific recipients for the notification type
        specific = self.get(f'recipients.{notification_type}', {})
        
        # Get default recipients
        default = self.get('recipients.default', {})
        
        # Combine defaults with specific overrides
        if isinstance(specific, list):
            # If specific is a list, use it as-is
            emails = [r.get('email') for r in specific if r.get('email')]
            phones = [r.get('phone') for r in specific if r.get('phone')]
        else:
            # If specific is a dict with email/phone keys
            emails = specific.get('email', [])
            if not isinstance(emails, list):
                emails = [emails] if emails else []
            
            phones = specific.get('phone', [])
            if not isinstance(phones, list):
                phones = [phones] if phones else []
        
        # Add default recipients if not already in the list
        if isinstance(default, list):
            for recipient in default:
                if 'email' in recipient and recipient['email'] not in emails:
                    emails.append(recipient['email'])
                if 'phone' in recipient and recipient['phone'] not in phones:
                    phones.append(recipient['phone'])
        
        return {
            'email': emails,
            'phone': phones
        }
    
    def get_template(self, template_name: str) -> str:
        """Get a message template by name.
        
        Args:
            template_name: Name of the template (e.g., 'arbitrage_opportunity')
            
        Returns:
            The template content as a string
        """
        # First try to get from email templates
        template = self.get(f'email.templates.{template_name}')
        
        # If not found, try SMS templates
        if not template:
            template = self.get(f'sms.templates.{template_name}', '')
        
        return template
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get notification preferences."""
        return {
            'notify_on_opportunity': self.get('preferences.notify_on_opportunity', True),
            'notify_on_order_update': self.get('preferences.notify_on_order_update', True),
            'notify_on_error': self.get('preferences.notify_on_error', True),
            'default_method': self.get('preferences.default_method', 'email'),
            'quiet_hours': (
                self.get('preferences.quiet_hours_start', '22:00'),
                self.get('preferences.quiet_hours_end', '08:00')
            ),
            'min_profit_threshold': float(self.get('preferences.min_profit_threshold', 20.0))
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature: Name of the feature (e.g., 'enable_email', 'enable_sms')
            
        Returns:
            bool: True if the feature is enabled
        """
        return bool(self.get(f'features.{feature}', False))
    
    def reload(self) -> None:
        """Reload the configuration from disk."""
        self._load_config()


# Singleton instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_email_config() -> Dict[str, Any]:
    """Get email configuration."""
    return get_config_manager().get_email_config()


def get_sms_config() -> Dict[str, Any]:
    """Get SMS configuration."""
    return get_config_manager().get_sms_config()


def get_recipients(notification_type: str = 'default') -> Dict[str, list]:
    """Get recipients for a notification type."""
    return get_config_manager().get_recipients(notification_type)


def get_template(template_name: str) -> str:
    """Get a message template by name."""
    return get_config_manager().get_template(template_name)


def reload_config() -> None:
    """Reload the configuration from disk."""
    get_config_manager().reload()
