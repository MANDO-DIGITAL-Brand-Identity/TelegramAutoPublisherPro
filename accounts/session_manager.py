"""
Session manager for Telegram Auto Publisher Pro
Manages Telethon session creation, persistence, and retrieval
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple

from telethon import TelegramClient
from telethon.sessions import StringSession

from config import config
from database.models import TelegramAccount, SessionMetadata
from database.repositories import TelegramAccountRepository, SessionRepository
from security.encryption import EncryptionManager
from .authentication import Authenticator, AuthenticationState

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Information about a Telethon session."""
    
    account_id: int
    session_id: str
    session_path: Path
    phone_number: str
    is_connected: bool = False
    is_valid: bool = True
    last_used: datetime = None
    created_at: datetime = None
    
    # Telethon client
    client: Optional[TelegramClient] = None


class SessionManager:
    """
    Manages Telethon sessions for multiple accounts.
    Handles session creation, persistence, and retrieval.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        encryption_manager: EncryptionManager = None
    ):
        """
        Initialize the session manager.
        
        Args:
            session_factory: A callable that returns an async database session.
            encryption_manager: Encryption manager for session encryption.
        """
        self.session_factory = session_factory
        self.encryption_manager = encryption_manager or EncryptionManager(config.security.ENCRYPTION_KEY)
        
        # In-memory session cache
        self._sessions: Dict[str, SessionInfo] = {}
        self._clients: Dict[str, TelegramClient] = {}
        
        # Session directory
        self.session_dir = config.telegram.session_path
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_session(
        self,
        account_id: int,
        phone_number: str,
        api_id: int = None,
        api_hash: str = None
    ) -> Optional[SessionInfo]:
        """
        Create a new session for an account.
        
        Args:
            account_id: The account ID.
            phone_number: The phone number for the account.
            api_id: Telegram API ID. If None, uses config.
            api_hash: Telegram API hash. If None, uses config.
            
        Returns:
            SessionInfo if successful, None otherwise.
        """
        try:
            # Create session ID
            session_id = f"account_{account_id}_{phone_number}"
            session_path = self.session_dir / f"{session_id}.session"
            
            # Create authenticator
            authenticator = Authenticator(
                phone_number=phone_number,
                api_id=api_id or config.telegram.API_ID,
                api_hash=api_hash or config.telegram.API_HASH,
                session_id=None,
                session_path=session_path,
                encryption_manager=self.encryption_manager
            )
            
            # Initialize client
            await authenticator.initialize_client()
            
            # Create session info
            session_info = SessionInfo(
                account_id=account_id,
                session_id=session_id,
                session_path=session_path,
                phone_number=phone_number,
                client=authenticator.client
            )
            
            # Store in cache
            self._sessions[session_id] = session_info
            self._clients[session_id] = authenticator.client
            
            # Save to database
            if self.session_factory:
                async with self.session_factory() as session:
                    # Update account with session ID
                    account_repo = TelegramAccountRepository(session)
                    await account_repo.update(account_id, {"session_id": session_id})
                    
                    # Create session metadata
                    session_repo = SessionRepository(session)
                    await session_repo.create({
                        "account_id": account_id,
                        "session_file_path": str(session_path),
                        "session_file_size": 0,
                        "is_encrypted": config.security.SESSION_ENCRYPTION_ENABLED,
                        "is_valid": True,
                        "created_at": datetime.utcnow()
                    })
            
            logger.info(f"Created session for account {account_id} ({phone_number})")
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    async def load_session(
        self,
        account_id: int,
        phone_number: str = None,
        session_id: str = None
    ) -> Optional[SessionInfo]:
        """
        Load an existing session.
        
        Args:
            account_id: The account ID.
            phone_number: The phone number for the account.
            session_id: The session ID. If None, will be generated from account_id.
            
        Returns:
            SessionInfo if successful, None otherwise.
        """
        try:
            # Get session info from database
            if self.session_factory:
                async with self.session_factory() as session:
                    account_repo = TelegramAccountRepository(session)
                    account = await account_repo.get_account(account_id)
                    
                    if not account:
                        logger.warning(f"Account {account_id} not found")
                        return None
                    
                    session_id = account.session_id or session_id
                    phone_number = account.phone_number or phone_number
            
            if not session_id:
                session_id = f"account_{account_id}"
            
            if not phone_number:
                logger.warning(f"Phone number not available for account {account_id}")
                return None
            
            # Check cache first
            if session_id in self._sessions:
                session_info = self._sessions[session_id]
                if session_info.client and session_info.client.is_connected():
                    return session_info
            
            # Load from file
            session_path = self.session_dir / f"{session_id}.session"
            
            if not session_path.exists():
                logger.warning(f"Session file not found: {session_path}")
                return None
            
            # Read session string
            session_string = None
            if config.security.SESSION_ENCRYPTION_ENABLED:
                encrypted_path = self.session_dir / f"{session_id}.session.enc"
                if encrypted_path.exists():
                    with open(encrypted_path, 'r') as f:
                        encrypted = f.read()
                    session_string = self.encryption_manager.decrypt(encrypted)
                else:
                    with open(session_path, 'r') as f:
                        session_string = f.read()
            else:
                with open(session_path, 'r') as f:
                    session_string = f.read()
            
            if not session_string:
                logger.warning(f"Empty session file: {session_path}")
                return None
            
            # Create client
            client = TelegramClient(
                StringSession(session_string),
                config.telegram.API_ID,
                config.telegram.API_HASH
            )
            
            # Connect and verify
            await client.connect()
            if not await client.is_user_authorized():
                logger.warning(f"Session not authorized: {session_id}")
                return None
            
            # Create session info
            session_info = SessionInfo(
                account_id=account_id,
                session_id=session_id,
                session_path=session_path,
                phone_number=phone_number,
                is_connected=True,
                is_valid=True,
                client=client
            )
            
            # Store in cache
            self._sessions[session_id] = session_info
            self._clients[session_id] = client
            
            # Update last used in database
            if self.session_factory:
                async with self.session_factory() as session:
                    session_repo = SessionRepository(session)
                    await session_repo.update(session_info.account_id, {
                        "last_used_at": datetime.utcnow()
                    })
            
            logger.info(f"Loaded session for account {account_id}")
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    async def get_session(self, account_id: int) -> Optional[SessionInfo]:
        """
        Get a session for an account, loading it if necessary.
        
        Args:
            account_id: The account ID.
            
        Returns:
            SessionInfo if successful, None otherwise.
        """
        # Check cache first
        for session_id, session_info in self._sessions.items():
            if session_info.account_id == account_id:
                if session_info.client and session_info.client.is_connected():
                    return session_info
                else:
                    # Try to reconnect
                    await self.reconnect_session(session_id)
                    return self._sessions.get(session_id)
        
        # Load from database
        if self.session_factory:
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get_account(account_id)
                
                if not account:
                    logger.warning(f"Account {account_id} not found")
                    return None
                
                return await self.load_session(
                    account_id=account_id,
                    phone_number=account.phone_number,
                    session_id=account.session_id
                )
        
        return None
    
    async def get_client(self, account_id: int) -> Optional[TelegramClient]:
        """
        Get a Telethon client for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            TelegramClient if successful, None otherwise.
        """
        session_info = await self.get_session(account_id)
        return session_info.client if session_info else None
    
    async def reconnect_session(self, session_id: str) -> bool:
        """
        Reconnect a session.
        
        Args:
            session_id: The session ID to reconnect.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if session_id not in self._sessions:
                return False
            
            session_info = self._sessions[session_id]
            
            if not session_info.client:
                return False
            
            # Disconnect if connected
            if session_info.client.is_connected():
                await session_info.client.disconnect()
            
            # Reconnect
            await session_info.client.connect()
            
            # Check if authorized
            if await session_info.client.is_user_authorized():
                session_info.is_connected = True
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to reconnect session {session_id}: {e}")
            return False
    
    async def disconnect_session(self, session_id: str) -> bool:
        """
        Disconnect a session.
        
        Args:
            session_id: The session ID to disconnect.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if session_id in self._sessions:
                session_info = self._sessions[session_id]
                if session_info.client and session_info.client.is_connected():
                    await session_info.client.disconnect()
                session_info.is_connected = False
            
            if session_id in self._clients:
                client = self._clients[session_id]
                if client and client.is_connected():
                    await client.disconnect()
            
            logger.info(f"Disconnected session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Disconnect first
            await self.disconnect_session(session_id)
            
            # Remove from cache
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._clients:
                del self._clients[session_id]
            
            # Delete session file
            session_path = self.session_dir / f"{session_id}.session"
            if session_path.exists():
                os.remove(session_path)
            
            # Delete encrypted session file
            encrypted_path = self.session_dir / f"{session_id}.session.enc"
            if encrypted_path.exists():
                os.remove(encrypted_path)
            
            # Update database
            if self.session_factory:
                async with self.session_factory() as session:
                    session_repo = SessionRepository(session)
                    # Find session by session_id
                    sessions = await session_repo.get_all()
                    for sess in sessions:
                        if sess.session_file_path and session_id in sess.session_file_path:
                            await session_repo.delete(sess.id)
                            break
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def close_all_sessions(self) -> int:
        """
        Close all active sessions.
        
        Returns:
            Number of sessions closed.
        """
        count = 0
        for session_id in list(self._sessions.keys()):
            if await self.disconnect_session(session_id):
                count += 1
        
        self._sessions.clear()
        self._clients.clear()
        
        logger.info(f"Closed {count} sessions")
        return count
    
    async def list_sessions(self) -> List[SessionInfo]:
        """
        List all active sessions.
        
        Returns:
            List of SessionInfo objects.
        """
        return list(self._sessions.values())
    
    async def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get information about a specific session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            SessionInfo if found, None otherwise.
        """
        return self._sessions.get(session_id)
    
    async def save_session(self, session_id: str) -> bool:
        """
        Save a session to disk.
        
        Args:
            session_id: The session ID to save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if session_id not in self._sessions:
                return False
            
            session_info = self._sessions[session_id]
            
            if not session_info.client:
                return False
            
            # Get session string
            session_string = session_info.client.session.save()
            
            # Save to file
            session_path = self.session_dir / f"{session_id}.session"
            with open(session_path, 'w') as f:
                f.write(session_string)
            
            # Encrypt if enabled
            if config.security.SESSION_ENCRYPTION_ENABLED:
                encrypted = self.encryption_manager.encrypt(session_string)
                encrypted_path = self.session_dir / f"{session_id}.session.enc"
                with open(encrypted_path, 'w') as f:
                    f.write(encrypted)
            
            logger.info(f"Saved session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False


__all__ = [
    'SessionInfo',
    'SessionManager',
]
