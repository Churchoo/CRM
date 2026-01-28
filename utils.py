"""
Utility functions for CRM Application
"""

import json
import os
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib


class ConfigManager:
    """Manage application configuration with encryption for sensitive data"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self._cipher = None
    
    def _get_cipher(self):
        """Get or create encryption cipher"""
        if self._cipher is None:
            # Generate key from machine-specific data (simple approach)
            # In production, consider using keyring or other secure storage
            key_material = os.environ.get('COMPUTERNAME', 'default_key')
            key = base64.urlsafe_b64encode(hashlib.sha256(key_material.encode()).digest())
            self._cipher = Fernet(key)
        return self._cipher
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return ""
        cipher = self._get_cipher()
        return cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return ""
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return ""
    
    def load_config(self) -> dict:
        """Load configuration from file"""
        default_config = {
            "email": {
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "password": "",  # Will be encrypted
                "provider": "Gmail"
            },
            "birthday_scheduler": {
                "enabled": True,
                "check_time": "09:00"
            },
            "database": {
                "path": "customers.db",
                "backup_folder": "backups"
            },
            "ui": {
                "theme": "default",
                "window_size": "1000x700"
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to handle new keys
                    return {**default_config, **loaded_config}
            except Exception as e:
                print(f"Error loading config: {e}")
                return default_config
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation
        Example: config.get('email.smtp_server')
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value):
        """
        Set configuration value using dot notation
        Example: config.set('email.smtp_server', 'smtp.gmail.com')
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()


def validate_date(date_string: str, format: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format
    
    Args:
        date_string: Date string to validate
        format: Expected date format (default: YYYY-MM-DD)
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_string, format)
        return True
    except (ValueError, TypeError):
        return False


def format_date(date_string: str, input_format: str = "%Y-%m-%d", 
                output_format: str = "%B %d, %Y") -> str:
    """
    Format date string from one format to another
    
    Args:
        date_string: Input date string
        input_format: Format of input date
        output_format: Desired output format
        
    Returns:
        Formatted date string or original if conversion fails
    """
    try:
        date_obj = datetime.strptime(date_string, input_format)
        return date_obj.strftime(output_format)
    except (ValueError, TypeError):
        return date_string


def validate_phone(phone: str) -> bool:
    """
    Basic phone number validation
    
    Args:
        phone: Phone number string
        
    Returns:
        True if appears valid, False otherwise
    """
    import re
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    # Check if remaining characters are digits and reasonable length
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def ensure_directory(directory: str):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_backup_filename(base_name: str = "customers") -> str:
    """
    Generate timestamped backup filename
    
    Args:
        base_name: Base name for backup file
        
    Returns:
        Filename with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_backup_{timestamp}.db"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# Test function
def test_utils():
    """Test utility functions"""
    print("Testing Utility Functions...")
    
    # Test date validation
    assert validate_date("2024-01-27") == True
    assert validate_date("invalid") == False
    print("✓ Date validation works")
    
    # Test date formatting
    formatted = format_date("2024-01-27", "%Y-%m-%d", "%B %d, %Y")
    print(f"✓ Date formatting: {formatted}")
    
    # Test phone validation
    assert validate_phone("555-123-4567") == True
    assert validate_phone("123") == False
    print("✓ Phone validation works")
    
    # Test text truncation
    truncated = truncate_text("This is a very long text that needs truncation", 20)
    assert len(truncated) <= 20
    print(f"✓ Text truncation: '{truncated}'")
    
    # Test backup filename generation
    backup_name = get_backup_filename()
    assert "backup" in backup_name
    assert ".db" in backup_name
    print(f"✓ Backup filename: {backup_name}")
    
    # Test config manager
    config = ConfigManager("test_config.json")
    config.set("test.value", "hello")
    assert config.get("test.value") == "hello"
    print("✓ Config manager works")
    
    # Test encryption
    encrypted = config.encrypt("secret_password")
    decrypted = config.decrypt(encrypted)
    assert decrypted == "secret_password"
    print("✓ Encryption/decryption works")
    
    # Cleanup
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    
    print("\n✓ All utility tests passed!")


if __name__ == "__main__":
    test_utils()
