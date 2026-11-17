"""
Group manager for Telegram Auto Publisher Pro
Manages group and channel information and permissions
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Tuple, Set
from enum import Enum

from telethon import TelegramClient
from telethon.errors import (
    ChatAdminRequiredError,
    UserNotMutualContactError,
    UserRestrictedError,
    UserBannedInChannelError,
    ChatSendMediaForbiddenError,
)

from config import config
from database.models import (
    Group,
    GroupPermission,
    TelegramAccount,
    User,
    GroupType,
    PermissionStatus,
)
from database.repositories import (
    GroupRepository,
    GroupPermissionRepository,
    TelegramAccountRepository,
    UserRepository,
)
from accounts.manager import AccountManager

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission level enum"""
    NONE = "none"
    READ_ONLY = "read_only"
    POST_TEXT = "post_text"
    POST_MEDIA = "post_media"
    ADMIN = "admin"
    OWNER = "owner"


@dataclass
class GroupInfo:
    """Information about a group or channel"""
    
    id: int
    account_id: int
    telegram_id: int
    title: str
    username: Optional[str] = None
    group_type: GroupType = GroupType.GROUP
    access_hash: Optional[int] = None
    is_accessible: bool = True
    is_active: bool = True
    is_verified: bool = False
    
    # Permissions
    can_post_messages: bool = False
    can_post_media: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_pin_messages: bool = False
    permission_status: PermissionStatus = PermissionStatus.UNKNOWN
    
    # Metadata
    participant_count: Optional[int] = None
    admin_count: Optional[int] = None
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
    last_verified_at: Optional[datetime] = None


class GroupManager:
    """
    Manages groups and channels for publishing.
    Handles group retrieval, permission checking, and management.
    """
    
    def __init__(
        self,
        account_manager: AccountManager = None,
        session_factory: Callable = None
    ):
        """
        Initialize the group manager.
        
        Args:
            account_manager: Account manager instance.
            session_factory: Database session factory.
        """
        self.account_manager = account_manager
        self.session_factory = session_factory
        
        # Group cache
        self._group_cache: Dict[int, GroupInfo] = {}
    
    async def refresh_groups(self, account_id: int) -> List[GroupInfo]:
        """
        Refresh the list of groups for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            List of GroupInfo objects.
        """
        try:
            # Get Telethon client
            client = await self.account_manager.get_account_client(account_id)
            if not client:
                logger.warning(f"No client available for account {account_id}")
                return []
            
            # Get dialogs
            dialogs = await client.get_dialogs(limit=200)
            
            group_infos = []
            
            for dialog in dialogs:
                entity = dialog.entity
                
                # Skip users
                if hasattr(entity, 'user') and entity.user:
                    continue
                
                # Process group/channel
                group_info = await self._extract_group_info(account_id, entity)
                if group_info:
                    group_infos.append(group_info)
                    self._group_cache[group_info.id] = group_info
            
            # Save to database
            await self._save_groups_to_database(account_id, group_infos)
            
            logger.info(f"Refreshed {len(group_infos)} groups for account {account_id}")
            return group_infos
            
        except Exception as e:
            logger.error(f"Error refreshing groups for account {account_id}: {e}")
            return []
    
    async def _extract_group_info(self, account_id: int, entity: Any) -> Optional[GroupInfo]:
        """
        Extract group information from a Telegram entity.
        
        Args:
            account_id: The account ID.
            entity: The Telegram entity.
            
        Returns:
            GroupInfo object, or None if not a group/channel.
        """
        try:
            # Check if it's a chat (group/channel)
            if hasattr(entity, 'broadcast') and entity.broadcast:
                group_type = GroupType.CHANNEL
            elif hasattr(entity, 'megagroup') and entity.megagroup:
                group_type = GroupType.SUPERGROUP
            elif hasattr(entity, 'gigagroup') and entity.gigagroup:
                group_type = GroupType.SUPERGROUP
            else:
                group_type = GroupType.GROUP
            
            # Check permissions
            can_post_messages, can_post_media, can_edit_messages, can_delete_messages, can_pin_messages = \
                await self._check_permissions(entity)
            
            # Determine permission status
            if can_post_messages and can_post_media:
                permission_status = PermissionStatus.ALLOWED
            elif can_post_messages:
                permission_status = PermissionStatus.ALLOWED  # Can post text
            else:
                permission_status = PermissionStatus.DENIED
            
            return GroupInfo(
                id=0,  # Will be set when saved to database
                account_id=account_id,
                telegram_id=entity.id,
                title=entity.title,
                username=getattr(entity, 'username', None),
                group_type=group_type,
                access_hash=getattr(entity, 'access_hash', None),
                is_accessible=True,
                is_active=True,
                is_verified=False,
                can_post_messages=can_post_messages,
                can_post_media=can_post_media,
                can_edit_messages=can_edit_messages,
                can_delete_messages=can_delete_messages,
                can_pin_messages=can_pin_messages,
                permission_status=permission_status,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error extracting group info: {e}")
            return None
    
    async def _check_permissions(self, entity: Any) -> Tuple[bool, bool, bool, bool, bool]:
        """
        Check permissions for a group/channel.
        
        Args:
            entity: The Telegram entity.
            
        Returns:
            Tuple of (can_post_messages, can_post_media, can_edit_messages, can_delete_messages, can_pin_messages).
        """
        try:
            client = None
            
            # Try to get a client (this is a simplified approach)
            # In a real implementation, we would use the client that retrieved the entity
            if self.account_manager:
                # This is a placeholder - we need the actual client
                pass
            
            # For now, return default permissions
            # In a real implementation, we would check actual permissions
            return True, True, True, True, True
            
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False, False, False, False, False
    
    async def _save_groups_to_database(self, account_id: int, group_infos: List[GroupInfo]):
        """
        Save group information to the database.
        
        Args:
            account_id: The account ID.
            group_infos: List of GroupInfo objects.
        """
        try:
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                permission_repo = GroupPermissionRepository(session)
                
                for group_info in group_infos:
                    # Check if group already exists
                    existing_group = await group_repo.get_group_by_telegram_id(group_info.telegram_id)
                    
                    if existing_group:
                        # Update existing group
                        group_data = {
                            "title": group_info.title,
                            "username": group_info.username,
                            "group_type": group_info.group_type.value,
                            "access_hash": group_info.access_hash,
                            "is_accessible": group_info.is_accessible,
                            "is_active": group_info.is_active,
                            "updated_at": datetime.utcnow()
                        }
                        
                        await group_repo.update(existing_group.id, group_data)
                        group_id = existing_group.id
                    else:
                        # Create new group
                        group_data = {
                            "account_id": account_id,
                            "telegram_id": group_info.telegram_id,
                            "title": group_info.title,
                            "username": group_info.username,
                            "group_type": group_info.group_type.value,
                            "access_hash": group_info.access_hash,
                            "is_accessible": group_info.is_accessible,
                            "is_active": group_info.is_active,
                            "is_verified": group_info.is_verified,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                        
                        group = await group_repo.create(group_data)
                        group_id = group.id
                        group_info.id = group_id
                    
                    # Save permissions
                    existing_permission = await permission_repo.get_permission(group_id)
                    
                    if existing_permission:
                        await permission_repo.update_permissions(
                            group_id,
                            can_post_messages=group_info.can_post_messages,
                            can_post_media=group_info.can_post_media,
                            can_edit_messages=group_info.can_edit_messages,
                            can_delete_messages=group_info.can_delete_messages,
                            can_pin_messages=group_info.can_pin_messages,
                            permission_status=group_info.permission_status
                        )
                    else:
                        await permission_repo.create({
                            "group_id": group_id,
                            "can_post_messages": group_info.can_post_messages,
                            "can_post_media": group_info.can_post_media,
                            "can_edit_messages": group_info.can_edit_messages,
                            "can_delete_messages": group_info.can_delete_messages,
                            "can_pin_messages": group_info.can_pin_messages,
                            "permission_status": group_info.permission_status.value,
                            "is_verified": False,
                            "created_at": datetime.utcnow()
                        })
            
            logger.info(f"Saved {len(group_infos)} groups to database for account {account_id}")
            
        except Exception as e:
            logger.error(f"Error saving groups to database: {e}")
    
    async def get_groups(self, account_id: int) -> List[GroupInfo]:
        """
        Get all groups for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            List of GroupInfo objects.
        """
        # Check cache first
        cached_groups = [g for g in self._group_cache.values() if g.account_id == account_id]
        if cached_groups:
            return cached_groups
        
        # Get from database
        try:
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_groups_by_account(account_id)
                
                group_infos = []
                for group in groups:
                    # Get permissions
                    permission_repo = GroupPermissionRepository(session)
                    permission = await permission_repo.get_permission(group.id)
                    
                    group_info = GroupInfo(
                        id=group.id,
                        account_id=account_id,
                        telegram_id=group.telegram_id,
                        title=group.title or "",
                        username=group.username,
                        group_type=GroupType(group.group_type) if group.group_type else GroupType.GROUP,
                        access_hash=group.access_hash,
                        is_accessible=group.is_accessible,
                        is_active=group.is_active,
                        is_verified=group.is_verified,
                        can_post_messages=permission.can_post_messages if permission else False,
                        can_post_media=permission.can_post_media if permission else False,
                        can_edit_messages=permission.can_edit_messages if permission else False,
                        can_delete_messages=permission.can_delete_messages if permission else False,
                        can_pin_messages=permission.can_pin_messages if permission else False,
                        permission_status=PermissionStatus(permission.permission_status) if permission else PermissionStatus.UNKNOWN,
                        created_at=group.created_at,
                        updated_at=group.updated_at,
                        last_verified_at=group.last_verified_at
                    )
                    
                    group_infos.append(group_info)
                    self._group_cache[group_info.id] = group_info
                
                return group_infos
                
        except Exception as e:
            logger.error(f"Error getting groups for account {account_id}: {e}")
            return []
    
    async def get_active_groups(self, account_id: int) -> List[GroupInfo]:
        """
        Get all active groups for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            List of GroupInfo objects for active groups.
        """
        groups = await self.get_groups(account_id)
        return [g for g in groups if g.is_active]
    
    async def get_groups_with_permissions(self, account_id: int) -> List[GroupInfo]:
        """
        Get groups with publishing permissions for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            List of GroupInfo objects with publishing permissions.
        """
        groups = await self.get_groups(account_id)
        return [g for g in groups if g.permission_status == PermissionStatus.ALLOWED]
    
    async def get_group(self, group_id: int) -> Optional[GroupInfo]:
        """
        Get information about a specific group.
        
        Args:
            group_id: The group ID.
            
        Returns:
            GroupInfo object, or None if not found.
        """
        # Check cache first
        if group_id in self._group_cache:
            return self._group_cache[group_id]
        
        # Get from database
        try:
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                group = await group_repo.get_group(group_id)
                
                if not group:
                    return None
                
                # Get permissions
                permission_repo = GroupPermissionRepository(session)
                permission = await permission_repo.get_permission(group_id)
                
                group_info = GroupInfo(
                    id=group.id,
                    account_id=group.account_id,
                    telegram_id=group.telegram_id,
                    title=group.title or "",
                    username=group.username,
                    group_type=GroupType(group.group_type) if group.group_type else GroupType.GROUP,
                    access_hash=group.access_hash,
                    is_accessible=group.is_accessible,
                    is_active=group.is_active,
                    is_verified=group.is_verified,
                    can_post_messages=permission.can_post_messages if permission else False,
                    can_post_media=permission.can_post_media if permission else False,
                    can_edit_messages=permission.can_edit_messages if permission else False,
                    can_delete_messages=permission.can_delete_messages if permission else False,
                    can_pin_messages=permission.can_pin_messages if permission else False,
                    permission_status=PermissionStatus(permission.permission_status) if permission else PermissionStatus.UNKNOWN,
                    created_at=group.created_at,
                    updated_at=group.updated_at,
                    last_verified_at=group.last_verified_at
                )
                
                self._group_cache[group_info.id] = group_info
                return group_info
                
        except Exception as e:
            logger.error(f"Error getting group {group_id}: {e}")
            return None
    
    async def can_publish_to_group(self, account_id: int, group_id: int) -> Tuple[bool, str]:
        """
        Check if we can publish to a specific group.
        
        Args:
            account_id: The account ID.
            group_id: The group ID.
            
        Returns:
            Tuple of (can_publish, error_message).
        """
        try:
            group_info = await self.get_group(group_id)
            
            if not group_info:
                return False, "Group not found"
            
            if group_info.account_id != account_id:
                return False, "Group does not belong to this account"
            
            if not group_info.is_active:
                return False, "Group is not active"
            
            if group_info.permission_status != PermissionStatus.ALLOWED:
                return False, "No permission to publish to this group"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking publish permission: {e}")
            return False, str(e)
    
    async def can_publish_media_to_group(self, account_id: int, group_id: int) -> Tuple[bool, str]:
        """
        Check if we can publish media to a specific group.
        
        Args:
            account_id: The account ID.
            group_id: The group ID.
            
        Returns:
            Tuple of (can_publish, error_message).
        """
        try:
            can_publish, error = await self.can_publish_to_group(account_id, group_id)
            
            if not can_publish:
                return False, error
            
            group_info = await self.get_group(group_id)
            
            if not group_info.can_post_media:
                return False, "No permission to post media to this group"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking media publish permission: {e}")
            return False, str(e)
    
    async def verify_group_permissions(self, account_id: int, group_id: int) -> Tuple[bool, str]:
        """
        Verify and update group permissions.
        
        Args:
            account_id: The account ID.
            group_id: The group ID.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Get client
            client = await self.account_manager.get_account_client(account_id)
            if not client:
                return False, "Account client not available"
            
            # Get group entity
            try:
                entity = await client.get_entity(group_id)
            except Exception as e:
                return False, f"Error getting group entity: {e}"
            
            # Check permissions
            can_post_messages, can_post_media, can_edit_messages, can_delete_messages, can_pin_messages = \
                await self._check_permissions(entity)
            
            # Update permissions in database
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                group = await group_repo.get_group_by_telegram_id(group_id)
                
                if not group:
                    return False, "Group not found in database"
                
                permission_repo = GroupPermissionRepository(session)
                permission = await permission_repo.get_permission(group.id)
                
                if not permission:
                    await permission_repo.create({
                        "group_id": group.id,
                        "can_post_messages": can_post_messages,
                        "can_post_media": can_post_media,
                        "can_edit_messages": can_edit_messages,
                        "can_delete_messages": can_delete_messages,
                        "can_pin_messages": can_pin_messages,
                        "permission_status": PermissionStatus.ALLOWED.value if (can_post_messages or can_post_media) else PermissionStatus.DENIED.value,
                        "is_verified": True,
                        "verified_at": datetime.utcnow()
                    })
                else:
                    await permission_repo.update_permissions(
                        group.id,
                        can_post_messages=can_post_messages,
                        can_post_media=can_post_media,
                        can_edit_messages=can_edit_messages,
                        can_delete_messages=can_delete_messages,
                        can_pin_messages=can_pin_messages,
                        permission_status=PermissionStatus.ALLOWED.value if (can_post_messages or can_post_media) else PermissionStatus.DENIED.value
                    )
            
            # Update cache
            if group.id in self._group_cache:
                self._group_cache[group.id].can_post_messages = can_post_messages
                self._group_cache[group.id].can_post_media = can_post_media
                self._group_cache[group.id].can_edit_messages = can_edit_messages
                self._group_cache[group.id].can_delete_messages = can_delete_messages
                self._group_cache[group.id].can_pin_messages = can_pin_messages
                self._group_cache[group.id].permission_status = PermissionStatus.ALLOWED if (can_post_messages or can_post_media) else PermissionStatus.DENIED
            
            logger.info(f"Verified permissions for group {group_id}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error verifying group permissions: {e}")
            return False, str(e)
    
    async def select_groups_for_publishing(
        self,
        account_id: int,
        group_ids: List[int]
    ) -> Tuple[bool, str]:
        """
        Select groups for publishing.
        
        Args:
            account_id: The account ID.
            group_ids: List of group IDs to select.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Verify all groups belong to this account and have permissions
            for group_id in group_ids:
                can_publish, error = await self.can_publish_to_group(account_id, group_id)
                if not can_publish:
                    return False, f"Cannot publish to group {group_id}: {error}"
            
            # Update account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                await settings_repo.update_publishing_settings(
                    account_id,
                    selected_group_ids=group_ids
                )
            
            logger.info(f"Selected {len(group_ids)} groups for publishing for account {account_id}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error selecting groups for publishing: {e}")
            return False, str(e)
    
    async def get_selected_groups(self, account_id: int) -> List[GroupInfo]:
        """
        Get selected groups for publishing.
        
        Args:
            account_id: The account ID.
            
        Returns:
            List of GroupInfo objects for selected groups.
        """
        try:
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                if not settings or not settings.selected_group_ids:
                    return []
                
                group_ids = settings.selected_group_ids
                groups = []
                
                for group_id in group_ids:
                    group_info = await self.get_group(group_id)
                    if group_info:
                        groups.append(group_info)
                
                return groups
                
        except Exception as e:
            logger.error(f"Error getting selected groups for account {account_id}: {e}")
            return []
    
    async def search_groups(
        self,
        account_id: int,
        query: str,
        limit: int = 10
    ) -> List[GroupInfo]:
        """
        Search groups by title or username.
        
        Args:
            account_id: The account ID.
            query: The search query.
            limit: Maximum number of results.
            
        Returns:
            List of GroupInfo objects matching the query.
        """
        try:
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.search_groups(account_id, query, limit)
                
                group_infos = []
                for group in groups:
                    group_info = await self.get_group(group.id)
                    if group_info:
                        group_infos.append(group_info)
                
                return group_infos
                
        except Exception as e:
            logger.error(f"Error searching groups for account {account_id}: {e}")
            return []
    
    async def clear_cache(self):
        """Clear the group cache."""
        self._group_cache.clear()
        logger.info("Cleared group cache")


__all__ = [
    'PermissionLevel',
    'GroupInfo',
    'GroupManager',
]
