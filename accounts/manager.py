"""
Account manager for Telegram Auto Publisher Pro
Main interface for managing Telegram user accounts
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple, Set

from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    AuthKeyError,
    SessionPasswordNeededError,
)

from config import config
from database.models import (
    TelegramAccount,
    SessionMetadata,
    AccountSettings,
    User,
    Group,
    Content,
    UserStatus,
)
from database.repositories import (
    TelegramAccountRepository,
    SessionRepository,
    AccountSettingsRepository,
    UserRepository,
    GroupRepository,
    ContentRepository,
)
from security.encryption import EncryptionManager
from security.validation import ValidationManager
from .authentication import Authenticator, AuthenticationState
from .session_manager import SessionManager, SessionInfo
from .connection import ConnectionManager, ConnectionStatus

logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Information about a Telegram account."""
    
    id: int
    user_id: int
    phone_number: str
    account_name: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Connection status
    is_connected: bool = False
    connection_status: str = "disconnected"
    
    # Publishing status
    is_publishing: bool = False
    publishing_interval: int = 60
    
    # Statistics
    total_published: int = 0
    successful_published: int = 0
    failed_published: int = 0
    
    # Timestamps
    created_at: datetime = None
    last_connected_at: Optional[datetime] = None
    last_published_at: Optional[datetime] = None


class AccountManager:
    """
    Main manager for Telegram user accounts.
    Provides a unified interface for account management, authentication, and operations.
    """
    
    def __init__(
        self,
        config: any = None,
        encryption_manager: EncryptionManager = None,
        session_factory: Callable = None
    ):
        """
        Initialize the account manager.
        
        Args:
            config: Application configuration.
            encryption_manager: Encryption manager for session encryption.
            session_factory: A callable that returns an async database session.
        """
        self.config = config or config
        self.encryption_manager = encryption_manager or EncryptionManager(self.config.security.ENCRYPTION_KEY)
        self.session_factory = session_factory
        
        # Initialize sub-managers
        self.session_manager = SessionManager(
            session_factory=session_factory,
            encryption_manager=self.encryption_manager
        )
        self.connection_manager = ConnectionManager(
            session_manager=self.session_manager,
            session_factory=session_factory
        )
        
        # Validation manager
        self.validation_manager = ValidationManager()
        
        # Account cache
        self._account_cache: Dict[int, AccountInfo] = {}
        
        # Event callbacks
        self._on_account_added: Optional[Callable[[AccountInfo], None]] = None
        self._on_account_removed: Optional[Callable[[int], None]] = None
        self._on_account_connected: Optional[Callable[[AccountInfo], None]] = None
        self._on_account_disconnected: Optional[Callable[[AccountInfo], None]] = None
    
    # ===========================================
    # ACCOUNT CREATION AND DELETION
    # ===========================================
    
    async def add_account(
        self,
        user_id: int,
        phone_number: str,
        account_name: str = None
    ) -> Tuple[bool, Optional[AccountInfo], str]:
        """
        Add a new Telegram account.
        
        Args:
            user_id: The user ID who owns this account.
            phone_number: The phone number for the account.
            account_name: Optional name for the account.
            
        Returns:
            Tuple of (success, account_info, error_message).
        """
        try:
            # Validate phone number
            is_valid, cleaned_phone = self.validation_manager.validate_phone_number(phone_number)
            if not is_valid:
                return False, None, cleaned_phone
            
            phone_number = cleaned_phone
            
            # Check if account already exists
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                existing = await account_repo.get_account_by_session_id(f"account_{user_id}_{phone_number}")
                
                if existing:
                    return False, None, "Account already exists"
                
                # Create account record
                account_data = {
                    "user_id": user_id,
                    "phone_number": phone_number,
                    "account_name": account_name or f"Account {phone_number}",
                    "is_connected": False,
                    "is_active": True,
                    "connection_status": "disconnected",
                    "created_at": datetime.utcnow()
                }
                
                account = await account_repo.create(account_data)
                
                # Create session
                session_info = await self.session_manager.create_session(
                    account.id,
                    phone_number
                )
                
                if not session_info:
                    # Clean up account if session creation failed
                    await account_repo.delete(account.id)
                    return False, None, "Failed to create session"
                
                # Create default settings
                settings_repo = AccountSettingsRepository(session)
                await settings_repo.create({
                    "account_id": account.id,
                    "publishing_enabled": False,
                    "publishing_interval_minutes": 60,
                    "publishing_mode": "random",
                    "use_random_content": True,
                    "prevent_duplicate_content": True,
                    "selected_group_ids": [],
                    "schedule_enabled": False,
                    "notifications_enabled": True,
                    "notification_on_success": True,
                    "notification_on_failure": True,
                    "total_published": 0,
                    "successful_published": 0,
                    "failed_published": 0
                })
                
                # Create account info
                account_info = AccountInfo(
                    id=account.id,
                    user_id=user_id,
                    phone_number=phone_number,
                    account_name=account_name,
                    is_connected=False,
                    connection_status="disconnected",
                    created_at=datetime.utcnow()
                )
                
                # Update cache
                self._account_cache[account.id] = account_info
                
                logger.info(f"Added account {account.id} for user {user_id}: {phone_number}")
                
                # Notify
                if self._on_account_added:
                    self._on_account_added(account_info)
                
                return True, account_info, ""
                
        except Exception as e:
            logger.error(f"Failed to add account: {e}")
            return False, None, str(e)
    
    async def remove_account(self, account_id: int, user_id: int = None) -> Tuple[bool, str]:
        """
        Remove a Telegram account.
        
        Args:
            account_id: The account ID to remove.
            user_id: Optional user ID for verification.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get_account(account_id)
                
                if not account:
                    return False, "Account not found"
                
                # Verify user ownership if user_id is provided
                if user_id and account.user_id != user_id:
                    return False, "Account does not belong to user"
                
                # Disconnect first
                await self.connection_manager.disconnect_account(account_id)
                
                # Delete session
                await self.session_manager.delete_session(f"account_{account_id}")
                
                # Delete account
                await account_repo.delete(account_id)
                
                # Delete settings
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                if settings:
                    await settings_repo.delete(settings.id)
                
                # Delete session metadata
                session_repo = SessionRepository(session)
                session_meta = await session_repo.get_session_by_account(account_id)
                if session_meta:
                    await session_repo.delete(session_meta.id)
                
                # Remove from cache
                if account_id in self._account_cache:
                    del self._account_cache[account_id]
                
                logger.info(f"Removed account {account_id}")
                
                # Notify
                if self._on_account_removed:
                    self._on_account_removed(account_id)
                
                return True, ""
                
        except Exception as e:
            logger.error(f"Failed to remove account {account_id}: {e}")
            return False, str(e)
    
    # ===========================================
    # ACCOUNT AUTHENTICATION
    # ===========================================
    
    async def login_account(
        self,
        account_id: int,
        phone_number: str = None
    ) -> Tuple[bool, AuthenticationState, str]:
        """
        Start login process for an account.
        
        Args:
            account_id: The account ID to login.
            phone_number: Optional phone number (if different from stored).
            
        Returns:
            Tuple of (success, state, error_message).
        """
        try:
            # Get account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get_account(account_id)
                
                if not account:
                    return False, AuthenticationState.ERROR, "Account not found"
                
                # Use provided phone number or stored one
                phone = phone_number or account.phone_number
                if not phone:
                    return False, AuthenticationState.ERROR, "Phone number is required"
            
            # Create authenticator
            authenticator = Authenticator(
                phone_number=phone,
                session_id=account.session_id
            )
            
            # Initialize and login
            await authenticator.initialize_client()
            success = await authenticator.login()
            
            if success:
                state = authenticator.state
                return True, state, ""
            else:
                return False, authenticator.state, "Login failed"
                
        except PhoneNumberInvalidError:
            return False, AuthenticationState.ERROR, "Invalid phone number"
        except Exception as e:
            logger.error(f"Login failed for account {account_id}: {e}")
            return False, AuthenticationState.ERROR, str(e)
    
    async def verify_login_code(
        self,
        account_id: int,
        code: str
    ) -> Tuple[bool, AuthenticationState, str]:
        """
        Verify login code for an account.
        
        Args:
            account_id: The account ID.
            code: The verification code.
            
        Returns:
            Tuple of (success, state, error_message).
        """
        try:
            # Get account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get_account(account_id)
                
                if not account:
                    return False, AuthenticationState.ERROR, "Account not found"
            
            # Create authenticator
            authenticator = Authenticator(
                phone_number=account.phone_number,
                session_id=account.session_id
            )
            
            # Initialize client
            await authenticator.initialize_client()
            
            # Verify code
            success = await authenticator.verify_code(code)
            
            if success:
                # Save session
                session_string = await authenticator.save_session()
                
                # Update account with session ID
                if session_string:
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        await account_repo.update(account_id, {
                            "session_id": session_string,
                            "is_connected": True,
                            "connection_status": "connected",
                            "last_connected_at": datetime.utcnow()
                        })
                
                # Connect
                await self.connection_manager.connect_account(account_id)
                
                state = authenticator.state
                return True, state, ""
            else:
                return False, authenticator.state, "Invalid code"
                
        except PhoneCodeInvalidError:
            return False, AuthenticationState.ERROR, "Invalid verification code"
        except SessionPasswordNeededError:
            return False, AuthenticationState.WAITING_FOR_PASSWORD, "2FA required"
        except Exception as e:
            logger.error(f"Code verification failed for account {account_id}: {e}")
            return False, AuthenticationState.ERROR, str(e)
    
    async def verify_2fa_password(
        self,
        account_id: int,
        password: str
    ) -> Tuple[bool, AuthenticationState, str]:
        """
        Verify 2FA password for an account.
        
        Args:
            account_id: The account ID.
            password: The 2FA password.
            
        Returns:
            Tuple of (success, state, error_message).
        """
        try:
            # Get account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get_account(account_id)
                
                if not account:
                    return False, AuthenticationState.ERROR, "Account not found"
            
            # Create authenticator
            authenticator = Authenticator(
                phone_number=account.phone_number,
                session_id=account.session_id
            )
            
            # Initialize client
            await authenticator.initialize_client()
            
            # We need to set the state to WAITING_FOR_PASSWORD and the verification code
            # This is a simplified approach - in production, we'd need to track the code
            authenticator.state = AuthenticationState.WAITING_FOR_PASSWORD
            
            # Verify password
            success = await authenticator.verify_password(password)
            
            if success:
                # Save session
                session_string = await authenticator.save_session()
                
                # Update account
                if session_string:
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        await account_repo.update(account_id, {
                            "session_id": session_string,
                            "is_connected": True,
                            "connection_status": "connected",
                            "last_connected_at": datetime.utcnow()
                        })
                
                # Connect
                await self.connection_manager.connect_account(account_id)
                
                state = authenticator.state
                return True, state, ""
            else:
                return False, authenticator.state, "Invalid password"
                
        except PasswordHashInvalidError:
            return False, AuthenticationState.ERROR, "Invalid 2FA password"
        except Exception as e:
            logger.error(f"2FA verification failed for account {account_id}: {e}")
            return False, AuthenticationState.ERROR, str(e)
    
    # ===========================================
    # ACCOUNT CONNECTION MANAGEMENT
    # ===========================================
    
    async def connect_account(self, account_id: int) -> bool:
        """
        Connect to a Telegram account.
        
        Args:
            account_id: The account ID to connect.
            
        Returns:
            True if connection was successful, False otherwise.
        """
        success = await self.connection_manager.connect_account(account_id)
        
        if success:
            # Update account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                await account_repo.update_connection_status(
                    account_id,
                    "connected",
                    is_connected=True
                )
            
            # Update cache
            if account_id in self._account_cache:
                self._account_cache[account_id].is_connected = True
                self._account_cache[account_id].connection_status = "connected"
            
            # Notify
            if self._on_account_connected:
                account_info = await self.get_account_info(account_id)
                if account_info:
                    self._on_account_connected(account_info)
        
        return success
    
    async def disconnect_account(self, account_id: int) -> bool:
        """
        Disconnect from a Telegram account.
        
        Args:
            account_id: The account ID to disconnect.
            
        Returns:
            True if disconnection was successful, False otherwise.
        """
        success = await self.connection_manager.disconnect_account(account_id)
        
        if success:
            # Update account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                await account_repo.update_connection_status(
                    account_id,
                    "disconnected",
                    is_connected=False
                )
            
            # Update cache
            if account_id in self._account_cache:
                self._account_cache[account_id].is_connected = False
                self._account_cache[account_id].connection_status = "disconnected"
            
            # Notify
            if self._on_account_disconnected:
                account_info = await self.get_account_info(account_id)
                if account_info:
                    self._on_account_disconnected(account_info)
        
        return success
    
    async def reconnect_account(self, account_id: int) -> bool:
        """
        Reconnect to a Telegram account.
        
        Args:
            account_id: The account ID to reconnect.
            
        Returns:
            True if reconnection was successful, False otherwise.
        """
        success = await self.connection_manager.reconnect_account(account_id)
        
        if success:
            # Update account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                await account_repo.update_connection_status(
                    account_id,
                    "connected",
                    is_connected=True
                )
            
            # Update cache
            if account_id in self._account_cache:
                self._account_cache[account_id].is_connected = True
                self._account_cache[account_id].connection_status = "connected"
        
        return success
    
    # ===========================================
    # ACCOUNT INFORMATION
    # ===========================================
    
    async def get_account_info(self, account_id: int) -> Optional[AccountInfo]:
        """
        Get information about an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            AccountInfo if found, None otherwise.
        """
        # Check cache first
        if account_id in self._account_cache:
            return self._account_cache[account_id]
        
        # Get from database
        async with self.session_factory() as session:
            account_repo = TelegramAccountRepository(session)
            account = await account_repo.get_account(account_id)
            
            if not account:
                return None
            
            # Get settings
            settings_repo = AccountSettingsRepository(session)
            settings = await settings_repo.get_settings_by_account(account_id)
            
            # Create account info
            account_info = AccountInfo(
                id=account.id,
                user_id=account.user_id,
                phone_number=account.phone_number or "",
                account_name=account.account_name,
                username=account.username,
                first_name=account.first_name,
                last_name=account.last_name,
                is_connected=account.is_connected,
                connection_status=account.connection_status,
                is_publishing=settings.publishing_enabled if settings else False,
                publishing_interval=settings.publishing_interval_minutes if settings else 60,
                total_published=settings.total_published if settings else 0,
                successful_published=settings.successful_published if settings else 0,
                failed_published=settings.failed_published if settings else 0,
                created_at=account.created_at,
                last_connected_at=account.last_connected_at,
                last_published_at=None  # Will be set from publishing logs if needed
            )
            
            # Update cache
            self._account_cache[account_id] = account_info
            
            return account_info
    
    async def get_accounts_by_user(self, user_id: int) -> List[AccountInfo]:
        """
        Get all accounts for a user.
        
        Args:
            user_id: The user ID.
            
        Returns:
            List of AccountInfo objects.
        """
        async with self.session_factory() as session:
            account_repo = TelegramAccountRepository(session)
            accounts = await account_repo.get_accounts_by_user(user_id)
            
            account_infos = []
            for account in accounts:
                account_info = await self.get_account_info(account.id)
                if account_info:
                    account_infos.append(account_info)
            
            return account_infos
    
    async def get_connected_accounts_by_user(self, user_id: int) -> List[AccountInfo]:
        """
        Get all connected accounts for a user.
        
        Args:
            user_id: The user ID.
            
        Returns:
            List of AccountInfo objects for connected accounts.
        """
        async with self.session_factory() as session:
            account_repo = TelegramAccountRepository(session)
            accounts = await account_repo.get_connected_accounts_by_user(user_id)
            
            account_infos = []
            for account in accounts:
                account_info = await self.get_account_info(account.id)
                if account_info and account_info.is_connected:
                    account_infos.append(account_info)
            
            return account_infos
    
    # ===========================================
    # ACCOUNT OPERATIONS
    # ===========================================
    
    async def get_account_client(self, account_id: int) -> Optional[TelegramClient]:
        """
        Get a Telethon client for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            TelegramClient if available, None otherwise.
        """
        return await self.session_manager.get_client(account_id)
    
    async def get_me(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the current user info from Telegram for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            Dictionary with user info, or None if failed.
        """
        client = await self.get_account_client(account_id)
        
        if not client:
            return None
        
        try:
            me = await client.get_me()
            return {
                "id": me.id,
                "phone": me.phone,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "is_bot": me.bot,
                "is_verified": me.verified,
                "is_restricted": me.restricted
            }
        except Exception as e:
            logger.error(f"Failed to get me for account {account_id}: {e}")
            return None
    
    async def get_dialogs(self, account_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get dialogs for an account.
        
        Args:
            account_id: The account ID.
            limit: Maximum number of dialogs to return.
            
        Returns:
            List of dialog dictionaries.
        """
        client = await self.get_account_client(account_id)
        
        if not client:
            return []
        
        try:
            dialogs = await client.get_dialogs(limit=limit)
            return [
                {
                    "id": dialog.id,
                    "name": dialog.name,
                    "entity_id": dialog.entity.id if hasattr(dialog.entity, 'id') else None,
                    "entity_type": type(dialog.entity).__name__
                }
                for dialog in dialogs
            ]
        except Exception as e:
            logger.error(f"Failed to get dialogs for account {account_id}: {e}")
            return []
    
    async def get_groups(self, account_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get groups and channels for an account.
        
        Args:
            account_id: The account ID.
            limit: Maximum number of groups to return.
            
        Returns:
            List of group/channel dictionaries.
        """
        client = await self.get_account_client(account_id)
        
        if not client:
            return []
        
        try:
            dialogs = await client.get_dialogs(limit=limit)
            groups = []
            
            for dialog in dialogs:
                entity = dialog.entity
                if hasattr(entity, 'broadcast') and entity.broadcast:
                    # Channel
                    groups.append({
                        "id": entity.id,
                        "title": entity.title,
                        "username": getattr(entity, 'username', None),
                        "type": "channel",
                        "is_broadcast": True
                    })
                elif hasattr(entity, 'megagroup') and entity.megagroup:
                    # Supergroup
                    groups.append({
                        "id": entity.id,
                        "title": entity.title,
                        "username": getattr(entity, 'username', None),
                        "type": "supergroup",
                        "is_broadcast": False
                    })
                elif not hasattr(entity, 'user'):
                    # Regular group
                    groups.append({
                        "id": entity.id,
                        "title": entity.title,
                        "username": getattr(entity, 'username', None),
                        "type": "group",
                        "is_broadcast": False
                    })
            
            return groups
        except Exception as e:
            logger.error(f"Failed to get groups for account {account_id}: {e}")
            return []
    
    async def check_group_permissions(self, account_id: int, group_id: int) -> Dict[str, bool]:
        """
        Check permissions for a group.
        
        Args:
            account_id: The account ID.
            group_id: The group ID to check.
            
        Returns:
            Dictionary with permission flags.
        """
        client = await self.get_account_client(account_id)
        
        if not client:
            return {"can_post": False, "can_edit": False, "can_delete": False}
        
        try:
            # Try to get the participant
            participant = await client.get_participant(group_id, request_user_id='me')
            
            # Check permissions
            permissions = {
                "can_post": False,
                "can_edit": False,
                "can_delete": False,
                "can_pin": False,
                "is_admin": False,
                "is_owner": False
            }
            
            if participant:
                if hasattr(participant, 'admin_rights'):
                    permissions["is_admin"] = True
                    permissions["can_post"] = True
                    permissions["can_edit"] = True
                    permissions["can_delete"] = True
                    permissions["can_pin"] = True
                    
                    if hasattr(participant.admin_rights, 'other'):
                        permissions["is_owner"] = True
                elif hasattr(participant, 'rights'):
                    # Regular participant
                    rights = participant.rights
                    permissions["can_post"] = getattr(rights, 'send_messages', False)
                    permissions["can_edit"] = getattr(rights, 'edit_messages', False)
                    permissions["can_delete"] = getattr(rights, 'delete_messages', False)
                    permissions["can_pin"] = getattr(rights, 'pin_messages', False)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to check permissions for account {account_id} in group {group_id}: {e}")
            return {"can_post": False, "can_edit": False, "can_delete": False}
    
    # ===========================================
    # ACCOUNT SETTINGS
    # ===========================================
    
    async def get_account_settings(self, account_id: int) -> Optional[Dict[str, Any]]:
        """
        Get settings for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            Dictionary with account settings, or None if not found.
        """
        async with self.session_factory() as session:
            settings_repo = AccountSettingsRepository(session)
            settings = await settings_repo.get_settings_by_account(account_id)
            
            if not settings:
                return None
            
            return {
                "publishing_enabled": settings.publishing_enabled,
                "publishing_interval_minutes": settings.publishing_interval_minutes,
                "publishing_mode": settings.publishing_mode,
                "selected_content_id": settings.selected_content_id,
                "use_random_content": settings.use_random_content,
                "prevent_duplicate_content": settings.prevent_duplicate_content,
                "selected_group_ids": settings.selected_group_ids or [],
                "schedule_enabled": settings.schedule_enabled,
                "schedule_cron": settings.schedule_cron,
                "schedule_timezone": settings.schedule_timezone,
                "notifications_enabled": settings.notifications_enabled,
                "notification_on_success": settings.notification_on_success,
                "notification_on_failure": settings.notification_on_failure,
                "total_published": settings.total_published,
                "successful_published": settings.successful_published,
                "failed_published": settings.failed_published
            }
    
    async def update_account_settings(
        self,
        account_id: int,
        settings: Dict[str, Any]
    ) -> bool:
        """
        Update settings for an account.
        
        Args:
            account_id: The account ID.
            settings: Dictionary with settings to update.
            
        Returns:
            True if update was successful, False otherwise.
        """
        try:
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                
                # Get current settings
                current_settings = await settings_repo.get_settings_by_account(account_id)
                
                if not current_settings:
                    # Create default settings first
                    await settings_repo.create({
                        "account_id": account_id,
                        "publishing_enabled": False,
                        "publishing_interval_minutes": 60,
                        "publishing_mode": "random",
                        "use_random_content": True,
                        "prevent_duplicate_content": True,
                        "selected_group_ids": [],
                        "schedule_enabled": False,
                        "notifications_enabled": True,
                        "notification_on_success": True,
                        "notification_on_failure": True,
                        "total_published": 0,
                        "successful_published": 0,
                        "failed_published": 0
                    })
                    current_settings = await settings_repo.get_settings_by_account(account_id)
                
                # Update settings
                await settings_repo.update(current_settings.id, settings)
                
                # Update cache
                if account_id in self._account_cache:
                    for key, value in settings.items():
                        if hasattr(self._account_cache[account_id], key):
                            setattr(self._account_cache[account_id], key, value)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update settings for account {account_id}: {e}")
            return False
    
    # ===========================================
    # ACCOUNT STATISTICS
    # ===========================================
    
    async def get_account_statistics(self, account_id: int) -> Dict[str, Any]:
        """
        Get statistics for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            Dictionary with account statistics.
        """
        async with self.session_factory() as session:
            settings_repo = AccountSettingsRepository(session)
            settings = await settings_repo.get_settings_by_account(account_id)
            
            if not settings:
                return {
                    "total_published": 0,
                    "successful_published": 0,
                    "failed_published": 0,
                    "success_rate": 0.0
                }
            
            total = settings.total_published
            successful = settings.successful_published
            failed = settings.failed_published
            
            success_rate = 0.0
            if total > 0:
                success_rate = (successful / total) * 100
            
            return {
                "total_published": total,
                "successful_published": successful,
                "failed_published": failed,
                "success_rate": round(success_rate, 2)
            }
    
    # ===========================================
    # CLEANUP AND MANAGEMENT
    # ===========================================
    
    async def close_all_clients(self) -> int:
        """
        Close all Telethon clients.
        
        Returns:
            Number of clients closed.
        """
        count = await self.session_manager.close_all_sessions()
        self._account_cache.clear()
        return count
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up.
        """
        count = 0
        
        if self.session_factory:
            async with self.session_factory() as session:
                session_repo = SessionRepository(session)
                expired_sessions = await session_repo.get_all()
                
                for session_meta in expired_sessions:
                    if session_meta.is_expired or session_meta.is_revoked or not session_meta.is_valid:
                        # Delete the session
                        session_id = f"account_{session_meta.account_id}"
                        await self.session_manager.delete_session(session_id)
                        count += 1
        
        return count
    
    # ===========================================
    # EVENT CALLBACKS
    # ===========================================
    
    def on_account_added(self, callback: Callable[[AccountInfo], None]) -> None:
        """Set callback for when an account is added."""
        self._on_account_added = callback
    
    def on_account_removed(self, callback: Callable[[int], None]) -> None:
        """Set callback for when an account is removed."""
        self._on_account_removed = callback
    
    def on_account_connected(self, callback: Callable[[AccountInfo], None]) -> None:
        """Set callback for when an account is connected."""
        self._on_account_connected = callback
    
    def on_account_disconnected(self, callback: Callable[[AccountInfo], None]) -> None:
        """Set callback for when an account is disconnected."""
        self._on_account_disconnected = callback


__all__ = [
    'AccountInfo',
    'AccountManager',
]
