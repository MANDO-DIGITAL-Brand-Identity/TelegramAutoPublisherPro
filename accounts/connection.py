"""
Connection manager for Telegram Auto Publisher Pro
Handles Telethon client connections and connection monitoring
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Set

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    AuthKeyError,
    SessionPasswordNeededError,
    TimeoutError,
)

from config import config
from database.models import TelegramAccount
from database.repositories import TelegramAccountRepository
from .session_manager import SessionManager, SessionInfo

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStatus:
    """Connection status for an account."""
    
    account_id: int
    phone_number: str
    is_connected: bool = False
    is_authorized: bool = False
    last_connection_time: Optional[datetime] = None
    last_disconnection_time: Optional[datetime] = None
    connection_attempts: int = 0
    error_message: Optional[str] = None


class ConnectionManager:
    """
    Manages connections for multiple Telegram accounts.
    Handles connection monitoring, reconnection, and error handling.
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        session_factory: Callable = None
    ):
        """
        Initialize the connection manager.
        
        Args:
            session_manager: The session manager for managing sessions.
            session_factory: A callable that returns an async database session.
        """
        self.session_manager = session_manager
        self.session_factory = session_factory
        
        # Connection status tracking
        self._connection_status: Dict[int, ConnectionStatus] = {}
        
        # Active connections
        self._active_connections: Set[int] = set()
        
        # Reconnection tasks
        self._reconnection_tasks: Dict[int, asyncio.Task] = {}
        
        # Connection lock
        self._connection_lock = asyncio.Lock()
    
    async def connect_account(self, account_id: int) -> bool:
        """
        Connect to a Telegram account.
        
        Args:
            account_id: The account ID to connect.
            
        Returns:
            True if connection was successful, False otherwise.
        """
        async with self._connection_lock:
            try:
                # Check if already connected
                if account_id in self._active_connections:
                    logger.info(f"Account {account_id} is already connected")
                    return True
                
                # Get session
                session_info = await self.session_manager.get_session(account_id)
                if not session_info or not session_info.client:
                    logger.warning(f"No session available for account {account_id}")
                    return False
                
                client = session_info.client
                
                # Connect
                try:
                    await client.connect()
                except FloodWaitError as e:
                    logger.warning(f"FloodWait for account {account_id}: {e}")
                    await self._handle_flood_wait(account_id, e.seconds)
                    return False
                except ConnectionError as e:
                    logger.error(f"Connection error for account {account_id}: {e}")
                    return False
                except Exception as e:
                    logger.error(f"Unexpected error connecting account {account_id}: {e}")
                    return False
                
                # Check if authorized
                is_authorized = await client.is_user_authorized()
                
                if not is_authorized:
                    logger.warning(f"Account {account_id} is not authorized")
                    await client.disconnect()
                    return False
                
                # Update connection status
                self._connection_status[account_id] = ConnectionStatus(
                    account_id=account_id,
                    phone_number=session_info.phone_number,
                    is_connected=True,
                    is_authorized=True,
                    last_connection_time=datetime.utcnow()
                )
                
                self._active_connections.add(account_id)
                
                # Update database
                if self.session_factory:
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        await account_repo.update_connection_status(
                            account_id,
                            "connected",
                            is_connected=True
                        )
                
                logger.info(f"Connected to account {account_id} ({session_info.phone_number})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect account {account_id}: {e}")
                return False
    
    async def connect_all_accounts(self) -> Dict[int, bool]:
        """
        Connect to all accounts.
        
        Returns:
            Dictionary mapping account IDs to connection success status.
        """
        results = {}
        
        if self.session_factory:
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_all()
                
                for account in accounts:
                    results[account.id] = await self.connect_account(account.id)
        
        return results
    
    async def disconnect_account(self, account_id: int) -> bool:
        """
        Disconnect from a Telegram account.
        
        Args:
            account_id: The account ID to disconnect.
            
        Returns:
            True if disconnection was successful, False otherwise.
        """
        async with self._connection_lock:
            try:
                # Cancel any pending reconnection tasks
                if account_id in self._reconnection_tasks:
                    self._reconnection_tasks[account_id].cancel()
                    del self._reconnection_tasks[account_id]
                
                # Disconnect session
                await self.session_manager.disconnect_session(f"account_{account_id}")
                
                # Update connection status
                if account_id in self._connection_status:
                    status = self._connection_status[account_id]
                    status.is_connected = False
                    status.is_authorized = False
                    status.last_disconnection_time = datetime.utcnow()
                
                self._active_connections.discard(account_id)
                
                # Update database
                if self.session_factory:
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        await account_repo.update_connection_status(
                            account_id,
                            "disconnected",
                            is_connected=False
                        )
                
                logger.info(f"Disconnected from account {account_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to disconnect account {account_id}: {e}")
                return False
    
    async def disconnect_all_accounts(self) -> int:
        """
        Disconnect from all accounts.
        
        Returns:
            Number of accounts disconnected.
        """
        count = 0
        
        for account_id in list(self._active_connections):
            if await self.disconnect_account(account_id):
                count += 1
        
        logger.info(f"Disconnected {count} accounts")
        return count
    
    async def reconnect_account(self, account_id: int) -> bool:
        """
        Reconnect to a Telegram account.
        
        Args:
            account_id: The account ID to reconnect.
            
        Returns:
            True if reconnection was successful, False otherwise.
        """
        # Disconnect first
        await self.disconnect_account(account_id)
        
        # Wait a bit before reconnecting
        await asyncio.sleep(1)
        
        # Reconnect
        return await self.connect_account(account_id)
    
    async def check_connection(self, account_id: int) -> bool:
        """
        Check if an account is connected.
        
        Args:
            account_id: The account ID to check.
            
        Returns:
            True if connected, False otherwise.
        """
        if account_id in self._active_connections:
            # Verify the connection is still active
            session_info = await self.session_manager.get_session(account_id)
            if session_info and session_info.client:
                try:
                    # Ping the connection
                    await session_info.client.get_me()
                    return True
                except Exception:
                    # Connection is not active
                    self._active_connections.discard(account_id)
                    return False
        
        return False
    
    async def check_all_connections(self) -> Dict[int, bool]:
        """
        Check all connections.
        
        Returns:
            Dictionary mapping account IDs to connection status.
        """
        results = {}
        
        for account_id in list(self._active_connections):
            results[account_id] = await self.check_connection(account_id)
        
        return results
    
    async def _handle_flood_wait(self, account_id: int, seconds: int) -> None:
        """
        Handle FloodWait error by scheduling reconnection.
        
        Args:
            account_id: The account ID that received FloodWait.
            seconds: Number of seconds to wait.
        """
        logger.warning(f"FloodWait for account {account_id}: {seconds} seconds")
        
        # Cancel any existing reconnection task
        if account_id in self._reconnection_tasks:
            self._reconnection_tasks[account_id].cancel()
            del self._reconnection_tasks[account_id]
        
        # Schedule reconnection
        async def reconnect_later():
            await asyncio.sleep(seconds)
            await self.connect_account(account_id)
        
        task = asyncio.create_task(reconnect_later())
        self._reconnection_tasks[account_id] = task
        
        # Update connection status
        if account_id in self._connection_status:
            status = self._connection_status[account_id]
            status.is_connected = False
            status.error_message = f"FloodWait: {seconds} seconds"
    
    async def monitor_connections(self) -> None:
        """
        Monitor all connections and reconnect if necessary.
        This should be called periodically.
        """
        logger.info("Monitoring connections...")
        
        # Check all active connections
        for account_id in list(self._active_connections):
            if not await self.check_connection(account_id):
                logger.warning(f"Connection lost for account {account_id}, reconnecting...")
                await self.reconnect_account(account_id)
        
        # Check if there are accounts that should be connected but aren't
        if self.session_factory:
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                connected_accounts = await account_repo.get_connected_accounts()
                
                for account in connected_accounts:
                    if account.id not in self._active_connections:
                        logger.info(f"Found connected account {account.id} not in active connections, connecting...")
                        await self.connect_account(account.id)
    
    async def get_connection_status(self, account_id: int) -> Optional[ConnectionStatus]:
        """
        Get the connection status for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            ConnectionStatus if found, None otherwise.
        """
        return self._connection_status.get(account_id)
    
    async def get_all_connection_statuses(self) -> Dict[int, ConnectionStatus]:
        """
        Get connection status for all accounts.
        
        Returns:
            Dictionary mapping account IDs to ConnectionStatus.
        """
        return self._connection_status.copy()
    
    async def get_active_connections(self) -> Set[int]:
        """
        Get set of currently active connection IDs.
        
        Returns:
            Set of account IDs that are currently connected.
        """
        return self._active_connections.copy()
    
    async def wait_for_connection(self, account_id: int, timeout: int = 30) -> bool:
        """
        Wait for an account to connect.
        
        Args:
            account_id: The account ID to wait for.
            timeout: Maximum time to wait in seconds.
            
        Returns:
            True if connection was established, False if timeout.
        """
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            if await self.check_connection(account_id):
                return True
            await asyncio.sleep(1)
        
        return False


__all__ = [
    'ConnectionStatus',
    'ConnectionManager',
]
