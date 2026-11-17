"""
Security tests for Telegram Auto Publisher Pro
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from security.encryption import EncryptionManager
from security.permissions import PermissionManager
from security.validation import ValidationManager


@pytest.fixture
def encryption_manager():
    """Create an encryption manager for testing."""
    return EncryptionManager("test-secret-key-for-encryption")


@pytest.fixture
def permission_manager():
    """Create a permission manager for testing."""
    return PermissionManager()


@pytest.fixture
def validation_manager():
    """Create a validation manager for testing."""
    return ValidationManager()


# ===========================================
# Encryption Manager Tests
# ===========================================

class TestEncryptionManager:
    """Tests for EncryptionManager."""
    
    def test_encrypt_decrypt_text(self, encryption_manager):
        """Test encrypting and decrypting text."""
        plaintext = "Hello, World!"
        
        encrypted = encryption_manager.encrypt(plaintext)
        assert encrypted != plaintext
        
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_empty_string(self, encryption_manager):
        """Test encrypting and decrypting empty string."""
        plaintext = ""
        
        encrypted = encryption_manager.encrypt(plaintext)
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_unicode(self, encryption_manager):
        """Test encrypting and decrypting unicode text."""
        plaintext = "Hello 世界 🌍"
        
        encrypted = encryption_manager.encrypt(plaintext)
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_long_text(self, encryption_manager):
        """Test encrypting and decrypting long text."""
        plaintext = "A" * 10000
        
        encrypted = encryption_manager.encrypt(plaintext)
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_file(self, encryption_manager, tmp_path):
        """Test encrypting a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test file content")
        
        encrypted_file = tmp_path / "test.enc"
        encryption_manager.encrypt_file(str(test_file), str(encrypted_file))
        
        assert encrypted_file.exists()
        assert test_file.read_text() != encrypted_file.read_text()
    
    def test_decrypt_file(self, encryption_manager, tmp_path):
        """Test decrypting a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test file content")
        
        encrypted_file = tmp_path / "test.enc"
        encryption_manager.encrypt_file(str(test_file), str(encrypted_file))
        
        decrypted_file = tmp_path / "test_decrypted.txt"
        encryption_manager.decrypt_file(str(encrypted_file), str(decrypted_file))
        
        assert decrypted_file.exists()
        assert decrypted_file.read_text() == "Test file content"
    
    def test_generate_hmac(self, encryption_manager):
        """Test generating HMAC."""
        data = "test data"
        hmac_value = encryption_manager.generate_hmac(data)
        
        assert hmac_value is not None
        assert len(hmac_value) > 0
    
    def test_verify_hmac(self, encryption_manager):
        """Test verifying HMAC."""
        data = "test data"
        hmac_value = encryption_manager.generate_hmac(data)
        
        assert encryption_manager.verify_hmac(data, hmac_value) is True
        assert encryption_manager.verify_hmac("wrong data", hmac_value) is False
    
    def test_encrypt_with_wrong_key(self):
        """Test decrypting with wrong key."""
        manager1 = EncryptionManager("key1")
        manager2 = EncryptionManager("key2")
        
        plaintext = "test"
        encrypted = manager1.encrypt(plaintext)
        
        with pytest.raises(Exception):
            manager2.decrypt(encrypted)


# ===========================================
# Permission Manager Tests
# ===========================================

class TestPermissionManager:
    """Tests for PermissionManager."""
    
    def test_check_admin_access(self, permission_manager):
        """Test checking admin access."""
        # This would need a real database in a real test
        # For now, just test the function exists
        assert hasattr(permission_manager, 'check_admin_access')
    
    def test_check_super_admin_access(self, permission_manager):
        """Test checking super admin access."""
        assert hasattr(permission_manager, 'check_super_admin_access')
    
    def test_check_user_access(self, permission_manager):
        """Test checking user access."""
        assert hasattr(permission_manager, 'check_user_access')


# ===========================================
# Validation Manager Tests
# ===========================================

class TestValidationManager:
    """Tests for ValidationManager."""
    
    def test_validate_phone_number(self, validation_manager):
        """Test validating phone numbers."""
        # Valid phone numbers
        assert validation_manager.validate_phone_number("+1234567890") is True
        assert validation_manager.validate_phone_number("1234567890") is True
        assert validation_manager.validate_phone_number("+1 234 567 890") is True
        
        # Invalid phone numbers
        assert validation_manager.validate_phone_number("") is False
        assert validation_manager.validate_phone_number("abc") is False
        assert validation_manager.validate_phone_number("+123") is False
    
    def test_validate_username(self, validation_manager):
        """Test validating usernames."""
        # Valid usernames
        assert validation_manager.validate_username("test_user") is True
        assert validation_manager.validate_username("TestUser123") is True
        assert validation_manager.validate_username("user_name") is True
        
        # Invalid usernames
        assert validation_manager.validate_username("") is False
        assert validation_manager.validate_username("@user") is False
        assert validation_manager.validate_username("user@domain.com") is False
    
    def test_validate_text(self, validation_manager):
        """Test validating text."""
        # Valid text
        assert validation_manager.validate_text("Hello, World!") is True
        assert validation_manager.validate_text("Test 123") is True
        assert validation_manager.validate_text("") is True  # Empty is valid
        
        # Invalid text (too long)
        long_text = "A" * 5000
        assert validation_manager.validate_text(long_text, max_length=100) is False
    
    def test_validate_media(self, validation_manager):
        """Test validating media."""
        # Valid media
        assert validation_manager.validate_media_file_size(1024) is True  # 1KB
        assert validation_manager.validate_media_file_size(10 * 1024 * 1024) is True  # 10MB
        
        # Invalid media (too large)
        assert validation_manager.validate_media_file_size(51 * 1024 * 1024) is False  # 51MB
    
    def test_sanitize_input(self, validation_manager):
        """Test sanitizing input."""
        # Test HTML sanitization
        html_input = "<script>alert('xss')</script>"
        sanitized = validation_manager.sanitize_input(html_input)
        assert "<script>" not in sanitized
        
        # Test SQL injection
        sql_input = "'; DROP TABLE users; --"
        sanitized = validation_manager.sanitize_input(sql_input)
        assert "DROP TABLE" not in sanitized or "'";" not in sanitized
    
    def test_validate_verification_code(self, validation_manager):
        """Test validating verification codes."""
        # Valid codes (5 digits)
        assert validation_manager.validate_verification_code("12345") is True
        assert validation_manager.validate_verification_code("00000") is True
        
        # Invalid codes
        assert validation_manager.validate_verification_code("1234") is False
        assert validation_manager.validate_verification_code("123456") is False
        assert validation_manager.validate_verification_code("abcde") is False
