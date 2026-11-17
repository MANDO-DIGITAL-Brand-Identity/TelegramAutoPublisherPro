"""
Encryption utilities for Telegram Auto Publisher Pro
Provides encryption for sensitive data at rest
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data.
    Uses Fernet symmetric encryption with a key derived from the provided encryption key.
    """
    
    def __init__(self, key: str = None):
        """
        Initialize the encryption manager.
        
        Args:
            key: The encryption key. If None, a random key will be generated.
        """
        self.key = key or os.getenv("ENCRYPTION_KEY", "")
        
        if not self.key:
            logger.warning("No encryption key provided. Generating a temporary key.")
            self.key = self.generate_key()
        
        # Derive a Fernet key from the provided key
        self.fernet_key = self._derive_fernet_key(self.key)
        self.cipher_suite = Fernet(self.fernet_key)
    
    @staticmethod
    def generate_key(length: int = 32) -> str:
        """
        Generate a random encryption key.
        
        Args:
            length: The length of the key in bytes.
            
        Returns:
            A base64-encoded random key.
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8')
    
    @staticmethod
    def _derive_fernet_key(password: str, salt: bytes = None, iterations: int = 100000) -> bytes:
        """
        Derive a Fernet key from a password using PBKDF2.
        
        Args:
            password: The password to derive the key from.
            salt: Optional salt. If None, a random salt will be generated.
            iterations: The number of iterations for PBKDF2.
            
        Returns:
            A Fernet-compatible key.
        """
        if salt is None:
            salt = b'telegram_auto_publisher_salt'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: The string to encrypt.
            
        Returns:
            The encrypted string (base64-encoded).
        """
        if not data:
            return ""
        
        try:
            encrypted = self.cipher_suite.encrypt(data.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted_data: The encrypted string to decrypt.
            
        Returns:
            The decrypted string.
            
        Raises:
            ValueError: If the data cannot be decrypted.
        """
        if not encrypted_data:
            return ""
        
        try:
            decrypted = self.cipher_suite.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Encrypt bytes.
        
        Args:
            data: The bytes to encrypt.
            
        Returns:
            The encrypted bytes.
        """
        if not data:
            return b""
        
        try:
            return self.cipher_suite.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt bytes.
        
        Args:
            encrypted_data: The encrypted bytes to decrypt.
            
        Returns:
            The decrypted bytes.
            
        Raises:
            ValueError: If the data cannot be decrypted.
        """
        if not encrypted_data:
            return b""
        
        try:
            return self.cipher_suite.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_file(self, file_path: Path, output_path: Path = None) -> Path:
        """
        Encrypt a file.
        
        Args:
            file_path: The path to the file to encrypt.
            output_path: The path to save the encrypted file. If None, appends .enc to the original path.
            
        Returns:
            The path to the encrypted file.
        """
        if output_path is None:
            output_path = file_path.parent / f"{file_path.name}.enc"
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.encrypt_bytes(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            return output_path
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise
    
    def decrypt_file(self, file_path: Path, output_path: Path = None) -> Path:
        """
        Decrypt a file.
        
        Args:
            file_path: The path to the encrypted file.
            output_path: The path to save the decrypted file. If None, removes .enc from the original path.
            
        Returns:
            The path to the decrypted file.
        """
        if output_path is None:
            if file_path.name.endswith('.enc'):
                output_path = file_path.parent / file_path.name[:-4]
            else:
                output_path = file_path.parent / f"{file_path.name}.decrypted"
        
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.decrypt_bytes(encrypted_data)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return output_path
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise
    
    def hash_data(self, data: str, algorithm: str = 'sha256') -> str:
        """
        Hash data using the specified algorithm.
        
        Args:
            data: The data to hash.
            algorithm: The hash algorithm to use (sha256, sha512, etc.).
            
        Returns:
            The hex-encoded hash.
        """
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def generate_hmac(self, data: str, key: str = None) -> Tuple[str, str]:
        """
        Generate an HMAC signature for data.
        
        Args:
            data: The data to sign.
            key: The key to use for signing. If None, uses the encryption key.
            
        Returns:
            A tuple of (signature, key) where key is the key used for signing.
        """
        if key is None:
            key = self.key
        
        signature = hmac.new(
            key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, key
    
    def verify_hmac(self, data: str, signature: str, key: str = None) -> bool:
        """
        Verify an HMAC signature.
        
        Args:
            data: The original data.
            signature: The signature to verify.
            key: The key used for signing. If None, uses the encryption key.
            
        Returns:
            True if the signature is valid, False otherwise.
        """
        if key is None:
            key = self.key
        
        expected_signature, _ = self.generate_hmac(data, key)
        return hmac.compare_digest(expected_signature, signature)
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: The length of the token in bytes.
            
        Returns:
            A hex-encoded random token.
        """
        return secrets.token_hex(length)
    
    def generate_secure_password(self, length: int = 16) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: The length of the password.
            
        Returns:
            A random password containing letters, digits, and special characters.
        """
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
        return ''.join(secrets.choice(alphabet) for _ in range(length))


# Create a default encryption manager instance
encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager(key: str = None) -> EncryptionManager:
    """
    Get or create the default encryption manager.
    
    Args:
        key: The encryption key. If None, uses the environment variable or creates a new key.
        
    Returns:
        The encryption manager instance.
    """
    global encryption_manager
    
    if encryption_manager is None:
        encryption_manager = EncryptionManager(key)
    
    return encryption_manager


__all__ = [
    'EncryptionManager',
    'get_encryption_manager',
    'encryption_manager',
]
