"""
Authentication module for Telegram Auto Publisher Pro
Handles Telethon-based authentication for user accounts
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Tuple

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.events import NewMessage

from config import config
from security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class AuthenticationState(Enum):
    """Authentication state enum"""
    IDLE = "idle"
    WAITING_FOR_CODE = "waiting_for_code"
    WAITING_FOR_PASSWORD = "waiting_for_password"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class Authenticator:
    """
    Handles authentication for a single Telegram account.
    """
    
    phone_number: str
    api_id: int = field(default_factory=lambda: config.telegram.API_ID)
    api_hash: str = field(default_factory=lambda: config.telegram.API_HASH)
    session_id: Optional[str] = None
    session_path: Optional[Path] = None
    encryption_manager: Optional[EncryptionManager] = None
    
    # State
    client: Optional[TelegramClient] = None
    state: AuthenticationState = AuthenticationState.IDLE
    verification_code: Optional[str] = None
    phone_code_hash: Optional[str] = None
    
    # Callbacks
    on_code_requested: Optional[Callable[[str], None]] = None
    on_authenticated: Optional[Callable[[TelegramClient], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    
    def __post_init__(self):
        """Initialize the authenticator."""
        if self.session_path is None:
            self.session_path = config.telegram.session_path / f"account_{self.phone_number}.session"
        
        if self.encryption_manager is None:
            self.encryption_manager = EncryptionManager(config.security.ENCRYPTION_KEY)
    
    async def initialize_client(self) -> TelegramClient:
        """
        Initialize the Telethon client.
        
        Returns:
            The initialized TelegramClient.
        """
        # Create session string if we have one
        session_string = None
        if self.session_id:
            session_string = self.session_id
        
        # Create client
        if session_string:
            self.client = TelegramClient(
                StringSession(session_string),
                self.api_id,
                self.api_hash
            )
        else:
            self.client = TelegramClient(
                str(self.session_path),
                self.api_id,
                self.api_hash
            )
        
        # Set up event handlers
        self._setup_event_handlers()
        
        return self.client
    
    def _setup_event_handlers(self):
        """Set up event handlers for the client."""
        if not self.client:
            return
        
        @self.client.on(NewMessage(func=lambda m: m.is_code()))
        async def handler(event):
            # Handle verification code messages
            if self.state == AuthenticationState.WAITING_FOR_CODE:
                code = event.message.message
                logger.info(f"Received verification code: {code[:2]}...")
                if self.on_code_requested:
                    self.on_code_requested(code)
        
    async def login(self) -> bool:
        """
        Start the login process.
        
        Returns:
            True if login was successful, False otherwise.
        """
        try:
            if not self.client:
                await self.initialize_client()
            
            # Check if already connected
            if self.client.is_connected():
                self.state = AuthenticationState.AUTHENTICATED
                return True
            
            # Connect to Telegram
            await self.client.connect()
            
            # Check if already authenticated
            if await self.client.is_user_authorized():
                self.state = AuthenticationState.AUTHENTICATED
                if self.on_authenticated:
                    self.on_authenticated(self.client)
                return True
            
            # Request login
            self.state = AuthenticationState.WAITING_FOR_CODE
            await self.client.send_code_request(self.phone_number)
            
            logger.info(f"Login code requested for {self.phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.state = AuthenticationState.ERROR
            if self.on_error:
                self.on_error(e)
            return False
    
    async def verify_code(self, code: str) -> bool:
        """
        Verify the login code.
        
        Args:
            code: The verification code.
            
        Returns:
            True if verification was successful, False otherwise.
        """
        try:
            if not self.client or not self.client.is_connected():
                await self.initialize_client()
                await self.client.connect()
                await self.client.send_code_request(self.phone_number)
            
            # Try to sign in with the code
            try:
                await self.client.sign_in(self.phone_number, code)
                self.state = AuthenticationState.AUTHENTICATED
                
                # Save session
                await self.save_session()
                
                if self.on_authenticated:
                    self.on_authenticated(self.client)
                
                return True
                
            except Exception as e:
                # Check if 2FA is required
                if "password" in str(e).lower():
                    self.state = AuthenticationState.WAITING_FOR_PASSWORD
                    self.verification_code = code
                    logger.info(f"2FA required for {self.phone_number}")
                    return False
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Code verification failed: {e}")
            self.state = AuthenticationState.ERROR
            if self.on_error:
                self.on_error(e)
            return False
    
    async def verify_password(self, password: str) -> bool:
        """
        Verify the 2FA password.
        
        Args:
            password: The 2FA password.
            
        Returns:
            True if verification was successful, False otherwise.
        """
        try:
            if not self.client or not self.client.is_connected():
                return False
            
            if self.state != AuthenticationState.WAITING_FOR_PASSWORD:
                return False
            
            if not self.verification_code:
                return False
            
            # Sign in with code and password
            await self.client.sign_in(password=password)
            self.state = AuthenticationState.AUTHENTICATED
            
            # Save session
            await self.save_session()
            
            if self.on_authenticated:
                self.on_authenticated(self.client)
            
            return True
            
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            self.state = AuthenticationState.ERROR
            if self.on_error:
                self.on_error(e)
            return False
    
    async def save_session(self) -> Optional[str]:
        """
        Save the current session.
        
        Returns:
            The session ID as a string, or None if failed.
        """
        try:
            if not self.client:
                return None
            
            # Get session string
            session_string = self.client.session.save()
            
            # Save to file
            if self.session_path:
                self.session_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.session_path, 'w') as f:
                    f.write(session_string)
            
            # Encrypt and store session ID
            self.session_id = session_string
            
            # If encryption is enabled, encrypt the session string
            if config.security.SESSION_ENCRYPTION_ENABLED and self.encryption_manager:
                encrypted = self.encryption_manager.encrypt(session_string)
                # Store encrypted session
                if self.session_path:
                    encrypted_path = self.session_path.parent / f"{self.session_path.name}.enc"
                    with open(encrypted_path, 'w') as f:
                        f.write(encrypted)
            
            logger.info(f"Session saved for {self.phone_number}")
            return session_string
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return None
    
    async def load_session(self, session_string: str = None) -> bool:
        """
        Load a session.
        
        Args:
            session_string: The session string to load. If None, loads from file.
            
        Returns:
            True if session was loaded successfully, False otherwise.
        """
        try:
            if session_string:
                # Use provided session string
                self.session_id = session_string
                self.client = TelegramClient(
                    StringSession(session_string),
                    self.api_id,
                    self.api_hash
                )
            elif self.session_path and self.session_path.exists():
                # Load from file
                if config.security.SESSION_ENCRYPTION_ENABLED and self.encryption_manager:
                    encrypted_path = self.session_path.parent / f"{self.session_path.name}.enc"
                    if encrypted_path.exists():
                        with open(encrypted_path, 'r') as f:
                            encrypted = f.read()
                        session_string = self.encryption_manager.decrypt(encrypted)
                    else:
                        with open(self.session_path, 'r') as f:
                            session_string = f.read()
                else:
                    with open(self.session_path, 'r') as f:
                        session_string = f.read()
                
                self.session_id = session_string
                self.client = TelegramClient(
                    StringSession(session_string),
                    self.api_id,
                    self.api_hash
                )
            else:
                return False
            
            # Connect and verify
            await self.client.connect()
            if await self.client.is_user_authorized():
                self.state = AuthenticationState.AUTHENTICATED
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect the client."""
        try:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
            self.state = AuthenticationState.IDLE
            logger.info(f"Disconnected from {self.phone_number}")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def close(self) -> None:
        """Close the client and clean up."""
        try:
            if self.client:
                await self.client.disconnect()
                await self.client.session.close()
            self.client = None
            self.state = AuthenticationState.IDLE
            logger.info(f"Closed client for {self.phone_number}")
        except Exception as e:
            logger.error(f"Error closing client: {e}")


# Standalone authentication functions

async def login_with_phone(
    phone_number: str,
    api_id: int = None,
    api_hash: str = None,
    session_path: Path = None,
    encryption_manager: EncryptionManager = None
) -> Authenticator:
    """
    Start login process with phone number.
    
    Args:
        phone_number: The phone number to login with.
        api_id: Telegram API ID. If None, uses config.
        api_hash: Telegram API hash. If None, uses config.
        session_path: Path to save the session. If None, uses default.
        encryption_manager: Encryption manager for session encryption.
        
    Returns:
        An Authenticator instance.
    """
    authenticator = Authenticator(
        phone_number=phone_number,
        api_id=api_id or config.telegram.API_ID,
        api_hash=api_hash or config.telegram.API_HASH,
        session_path=session_path,
        encryption_manager=encryption_manager
    )
    
    await authenticator.login()
    return authenticator


async def verify_code(
    authenticator: Authenticator,
    code: str
) -> bool:
    """
    Verify a login code.
    
    Args:
        authenticator: The Authenticator instance.
        code: The verification code.
        
    Returns:
        True if verification was successful, False otherwise.
    """
    return await authenticator.verify_code(code)


async def verify_password(
    authenticator: Authenticator,
    password: str
) -> bool:
    """
    Verify a 2FA password.
    
    Args:
        authenticator: The Authenticator instance.
        password: The 2FA password.
        
    Returns:
        True if verification was successful, False otherwise.
    """
    return await authenticator.verify_password(password)


__all__ = [
    'AuthenticationState',
    'Authenticator',
    'login_with_phone',
    'verify_code',
    'verify_password',
]
