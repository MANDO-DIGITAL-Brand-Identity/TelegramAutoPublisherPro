"""
Input validation for Telegram Auto Publisher Pro
Provides validation for user inputs and data sanitization
"""

import logging
import re
from pathlib import Path
from typing import Optional, List, Tuple

from config import config

logger = logging.getLogger(__name__)


class ValidationManager:
    """
    Manages input validation and data sanitization.
    """
    
    def __init__(self):
        """Initialize the validation manager."""
        pass
    
    def validate_phone_number(self, phone_number: str) -> Tuple[bool, str]:
        """
        Validate a phone number.
        
        Args:
            phone_number: The phone number to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not phone_number:
            return False, "Phone number is required"
        
        # Remove spaces and special characters
        cleaned = re.sub(r'[^0-9+]', '', phone_number)
        
        if not cleaned:
            return False, "Phone number must contain digits"
        
        # Check if it's a valid international phone number format
        # Should start with + followed by country code and number
        if cleaned.startswith('+'):
            if len(cleaned) < 8:  # + + country code (1-3) + number (at least 4)
                return False, "Phone number is too short"
        else:
            # Local format - should be at least 7 digits
            if len(cleaned) < 7:
                return False, "Phone number is too short"
        
        return True, cleaned
    
    def validate_username(self, username: str, min_length: int = 3, max_length: int = 32) -> Tuple[bool, str]:
        """
        Validate a username.
        
        Args:
            username: The username to validate.
            min_length: Minimum length of the username.
            max_length: Maximum length of the username.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not username:
            return False, "Username is required"
        
        if len(username) < min_length:
            return False, f"Username must be at least {min_length} characters"
        
        if len(username) > max_length:
            return False, f"Username must be at most {max_length} characters"
        
        # Check if username contains only allowed characters
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, username
    
    def validate_text_content(self, text: str, max_length: int = 4096) -> Tuple[bool, str]:
        """
        Validate text content.
        
        Args:
            text: The text to validate.
            max_length: Maximum length of the text.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not text:
            return False, "Text is required"
        
        if len(text) > max_length:
            return False, f"Text must be at most {max_length} characters"
        
        return True, text
    
    def validate_media_file(self, file_path: Path, allowed_extensions: List[str] = None) -> Tuple[bool, str]:
        """
        Validate a media file.
        
        Args:
            file_path: The path to the file.
            allowed_extensions: List of allowed file extensions.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not file_path.exists():
            return False, "File does not exist"
        
        if not file_path.is_file():
            return False, "Path is not a file"
        
        # Check file size
        max_size = config.security.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_path.stat().st_size > max_size:
            return False, f"File size exceeds maximum of {config.security.MAX_FILE_SIZE_MB}MB"
        
        # Check file extension
        if allowed_extensions is None:
            allowed_extensions = config.security.ALLOWED_EXTENSIONS
        
        file_extension = file_path.suffix.lower()
        if file_extension not in allowed_extensions:
            return False, f"File extension {file_extension} is not allowed"
        
        return True, str(file_path)
    
    def validate_integer(self, value: str, min_value: int = None, max_value: int = None) -> Tuple[bool, int]:
        """
        Validate an integer value.
        
        Args:
            value: The string to validate.
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.
            
        Returns:
            A tuple of (is_valid, integer_value).
        """
        if not value:
            return False, 0
        
        try:
            int_value = int(value)
        except ValueError:
            return False, 0
        
        if min_value is not None and int_value < min_value:
            return False, 0
        
        if max_value is not None and int_value > max_value:
            return False, 0
        
        return True, int_value
    
    def validate_float(self, value: str, min_value: float = None, max_value: float = None) -> Tuple[bool, float]:
        """
        Validate a float value.
        
        Args:
            value: The string to validate.
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.
            
        Returns:
            A tuple of (is_valid, float_value).
        """
        if not value:
            return False, 0.0
        
        try:
            float_value = float(value)
        except ValueError:
            return False, 0.0
        
        if min_value is not None and float_value < min_value:
            return False, 0.0
        
        if max_value is not None and float_value > max_value:
            return False, 0.0
        
        return True, float_value
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """
        Validate an email address.
        
        Args:
            email: The email address to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not email:
            return False, "Email is required"
        
        # Simple email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        return True, email
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate a URL.
        
        Args:
            url: The URL to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not url:
            return False, "URL is required"
        
        # Simple URL validation
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/[a-zA-Z0-9._-]*)*/?$'
        if not re.match(pattern, url):
            return False, "Invalid URL format"
        
        return True, url
    
    def sanitize_text(self, text: str, max_length: int = 4096) -> str:
        """
        Sanitize text content by removing potentially harmful characters.
        
        Args:
            text: The text to sanitize.
            max_length: Maximum length of the sanitized text.
            
        Returns:
            The sanitized text.
        """
        if not text:
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename by removing potentially harmful characters.
        
        Args:
            filename: The filename to sanitize.
            
        Returns:
            The sanitized filename.
        """
        if not filename:
            return ""
        
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        
        # Remove characters that might be problematic on various filesystems
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Trim whitespace
        filename = filename.strip()
        
        return filename
    
    def validate_cron_expression(self, cron: str) -> Tuple[bool, str]:
        """
        Validate a cron expression.
        
        Args:
            cron: The cron expression to validate.
            
        Returns:
            A tuple of (is_valid, error_message).
        """
        if not cron:
            return False, "Cron expression is required"
        
        # Simple cron validation (5 fields: minute, hour, day, month, weekday)
        parts = cron.split()
        if len(parts) != 5:
            return False, "Cron expression must have 5 fields"
        
        # Validate each part
        for i, part in enumerate(parts):
            # Check for valid characters
            if not re.match(r'^[0-9,*/-]+$', part):
                return False, f"Invalid characters in cron field {i+1}"
        
        return True, cron


# Standalone validation functions

def validate_phone_number(phone_number: str) -> Tuple[bool, str]:
    """Validate a phone number."""
    manager = ValidationManager()
    return manager.validate_phone_number(phone_number)


def validate_username(username: str, min_length: int = 3, max_length: int = 32) -> Tuple[bool, str]:
    """Validate a username."""
    manager = ValidationManager()
    return manager.validate_username(username, min_length, max_length)


def validate_text_content(text: str, max_length: int = 4096) -> Tuple[bool, str]:
    """Validate text content."""
    manager = ValidationManager()
    return manager.validate_text_content(text, max_length)


def validate_media_file(file_path: Path, allowed_extensions: List[str] = None) -> Tuple[bool, str]:
    """Validate a media file."""
    manager = ValidationManager()
    return manager.validate_media_file(file_path, allowed_extensions)


def sanitize_text(text: str, max_length: int = 4096) -> str:
    """Sanitize text content."""
    manager = ValidationManager()
    return manager.sanitize_text(text, max_length)


__all__ = [
    'ValidationManager',
    'validate_phone_number',
    'validate_username',
    'validate_text_content',
    'validate_media_file',
    'sanitize_text',
]
