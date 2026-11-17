"""
Channel manager for Telegram Auto Publisher Pro
Manages mandatory channel subscriptions and verification
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User,
    RequiredChannel,
    GroupType,
)
from database.repositories import (
    UserRepository,
    RequiredChannelRepository,
    AuditLogRepository,
)
from security.permissions import check_admin_access, check_super_admin_access
from notifications.manager import NotificationManager, NotificationType

logger = logging.getLogger(__name__)


@dataclass
class ChannelInfo:
    """Information about a required channel"""
    
    id: Optional[int] = None
    channel_id: int = 0
    channel_username: Optional[str] = None
    channel_title: Optional[str] = None
    channel_type: str = GroupType.CHANNEL.value
    
    # Verification settings
    is_required: bool = True
    verification_enabled: bool = True
    
    # Priority
    priority: int = 0
    
    # Messages
    join_message: Optional[str] = None
    success_message: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ChannelVerificationResult:
    """Result of channel membership verification"""
    
    channel_id: int
    channel_username: Optional[str]
    channel_title: Optional[str]
    
    is_member: bool = False
    is_admin: bool = False
    can_send_messages: bool = False
    
    verification_success: bool = False
    error_message: Optional[str] = None
    
    verified_at: Optional[datetime] = None


@dataclass
class UserChannelStatus:
    """Status of user's channel subscriptions"""
    
    user_id: int
    required_channels: List[ChannelInfo] = field(default_factory=list)
    joined_channels: List[int] = field(default_factory=list)
    missing_channels: List[ChannelInfo] = field(default_factory=list)
    
    all_joined: bool = False
    verification_required: bool = False
    
    last_verified: Optional[datetime] = None


class ChannelManager:
    """
    Manages mandatory channel subscriptions and verification.
    Provides functionality for adding, removing, and verifying required channels.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        required_channel_repository: RequiredChannelRepository = None,
        user_repository: UserRepository = None,
        audit_log_repository: AuditLogRepository = None,
        notification_manager: NotificationManager = None,
        config: any = None
    ):
        """
        Initialize the channel manager.
        
        Args:
            session_factory: Database session factory.
            required_channel_repository: Required channel repository instance.
            user_repository: User repository instance.
            audit_log_repository: Audit log repository instance.
            notification_manager: Notification manager instance.
            config: Application configuration.
        """
        self.session_factory = session_factory
        self.config = config or config
        
        # Initialize repositories
        if required_channel_repository:
            self.required_channel_repository = required_channel_repository
        else:
            self.required_channel_repository = RequiredChannelRepository(session_factory)
            
        if user_repository:
            self.user_repository = user_repository
        else:
            self.user_repository = UserRepository(session_factory)
            
        if audit_log_repository:
            self.audit_log_repository = audit_log_repository
        else:
            self.audit_log_repository = AuditLogRepository(session_factory)
        
        self.notification_manager = notification_manager
        
        # Bot reference for verification
        self._bot = None
        
        # Cache for required channels
        self._required_channels_cache: Optional[List[RequiredChannel]] = None
        self._cache_last_updated: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        
        logger.info("ChannelManager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the channel manager.
        """
        logger.info("ChannelManager: Initializing...")
        
        # Load required channels
        await self._load_required_channels()
        
        logger.info("ChannelManager: Initialized successfully")
    
    async def set_bot(self, bot: Any) -> None:
        """
        Set the bot instance for verification.
        
        Args:
            bot: The aiogram Bot instance.
        """
        self._bot = bot
        logger.info("ChannelManager: Bot instance set")
    
    async def _load_required_channels(self, force: bool = False) -> List[RequiredChannel]:
        """
        Load required channels from database with caching.
        
        Args:
            force: Whether to force refresh the cache.
            
        Returns:
            List of RequiredChannel objects.
        """
        if not force and self._required_channels_cache:
            if self._cache_last_updated and (datetime.utcnow() - self._cache_last_updated) < self._cache_ttl:
                return self._required_channels_cache
        
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                channels = await self.required_channel_repository.get_required_channels()
                self._required_channels_cache = channels
                self._cache_last_updated = datetime.utcnow()
                logger.debug(f"ChannelManager: Loaded {len(channels)} required channels")
                return channels
        except Exception as e:
            logger.error(f"ChannelManager: Error loading required channels: {e}")
            return []
    
    async def get_required_channels(self, force: bool = False) -> List[ChannelInfo]:
        """
        Get all required channels.
        
        Args:
            force: Whether to force refresh the cache.
            
        Returns:
            List of ChannelInfo objects.
        """
        channels = await self._load_required_channels(force)
        
        return [
            ChannelInfo(
                id=c.id,
                channel_id=c.channel_id,
                channel_username=c.channel_username,
                channel_title=c.channel_title,
                channel_type=c.channel_type,
                is_required=c.is_required,
                verification_enabled=c.verification_enabled,
                priority=c.priority,
                join_message=c.join_message,
                success_message=c.success_message,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in channels
        ]
    
    async def get_channel(self, channel_id: int) -> Optional[ChannelInfo]:
        """
        Get a specific required channel by ID.
        
        Args:
            channel_id: The channel ID.
            
        Returns:
            ChannelInfo object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                channel = await self.required_channel_repository.get_by_field("channel_id", channel_id)
                
                if channel:
                    return ChannelInfo(
                        id=channel.id,
                        channel_id=channel.channel_id,
                        channel_username=channel.channel_username,
                        channel_title=channel.channel_title,
                        channel_type=channel.channel_type,
                        is_required=channel.is_required,
                        verification_enabled=channel.verification_enabled,
                        priority=channel.priority,
                        join_message=channel.join_message,
                        success_message=channel.success_message,
                        created_at=channel.created_at,
                        updated_at=channel.updated_at
                    )
                return None
        except Exception as e:
            logger.error(f"ChannelManager: Error getting channel {channel_id}: {e}")
            return None
    
    async def get_channel_by_username(self, username: str) -> Optional[ChannelInfo]:
        """
        Get a specific required channel by username.
        
        Args:
            username: The channel username.
            
        Returns:
            ChannelInfo object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                channel = await self.required_channel_repository.get_by_field("channel_username", username)
                
                if channel:
                    return ChannelInfo(
                        id=channel.id,
                        channel_id=channel.channel_id,
                        channel_username=channel.channel_username,
                        channel_title=channel.channel_title,
                        channel_type=channel.channel_type,
                        is_required=channel.is_required,
                        verification_enabled=channel.verification_enabled,
                        priority=channel.priority,
                        join_message=channel.join_message,
                        success_message=channel.success_message,
                        created_at=channel.created_at,
                        updated_at=channel.updated_at
                    )
                return None
        except Exception as e:
            logger.error(f"ChannelManager: Error getting channel by username {username}: {e}")
            return None
    
    async def add_channel(
        self,
        channel_id: int,
        channel_username: Optional[str] = None,
        channel_title: Optional[str] = None,
        channel_type: str = GroupType.CHANNEL.value,
        is_required: bool = True,
        verification_enabled: bool = True,
        priority: int = 0,
        join_message: Optional[str] = None,
        success_message: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Tuple[bool, Optional[ChannelInfo]]:
        """
        Add a new required channel.
        
        Args:
            channel_id: The Telegram channel ID.
            channel_username: The channel username.
            channel_title: The channel title.
            channel_type: The channel type.
            is_required: Whether the channel is required.
            verification_enabled: Whether verification is enabled.
            priority: The channel priority.
            join_message: The join message to display.
            success_message: The success message to display.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            Tuple of (success, ChannelInfo or error message).
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                
                # Check if channel already exists
                existing = await self.required_channel_repository.get_by_field("channel_id", channel_id)
                if existing:
                    logger.warning(f"ChannelManager: Channel {channel_id} already exists")
                    return False, None
                
                channel = RequiredChannel(
                    channel_id=channel_id,
                    channel_username=channel_username,
                    channel_title=channel_title,
                    channel_type=channel_type,
                    is_required=is_required,
                    verification_enabled=verification_enabled,
                    priority=priority,
                    join_message=join_message,
                    success_message=success_message,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(channel)
                await session.flush()
                await session.refresh(channel)
                await session.commit()
                
                # Invalidate cache
                self._required_channels_cache = None
                
                # Log audit
                if admin_id:
                    await self.audit_log_repository.log_action(
                        administrator_id=admin_id,
                        action=f"Add required channel",
                        action_type="channel_management",
                        target_id=channel.id,
                        target_type="required_channel",
                        target_name=channel_title or channel_username or str(channel_id),
                        details={"channel_id": channel_id, "is_required": is_required},
                        success=True
                    )
                
                channel_info = ChannelInfo(
                    id=channel.id,
                    channel_id=channel.channel_id,
                    channel_username=channel.channel_username,
                    channel_title=channel.channel_title,
                    channel_type=channel.channel_type,
                    is_required=channel.is_required,
                    verification_enabled=channel.verification_enabled,
                    priority=channel.priority,
                    join_message=channel.join_message,
                    success_message=channel.success_message,
                    created_at=channel.created_at,
                    updated_at=channel.updated_at
                )
                
                logger.info(f"ChannelManager: Added required channel {channel_id}")
                return True, channel_info
                
        except Exception as e:
            logger.error(f"ChannelManager: Error adding channel {channel_id}: {e}")
            return False, None
    
    async def update_channel(
        self,
        channel_id: int,
        channel_username: Optional[str] = None,
        channel_title: Optional[str] = None,
        is_required: Optional[bool] = None,
        verification_enabled: Optional[bool] = None,
        priority: Optional[int] = None,
        join_message: Optional[str] = None,
        success_message: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Tuple[bool, Optional[ChannelInfo]]:
        """
        Update a required channel.
        
        Args:
            channel_id: The channel ID to update.
            channel_username: The channel username.
            channel_title: The channel title.
            is_required: Whether the channel is required.
            verification_enabled: Whether verification is enabled.
            priority: The channel priority.
            join_message: The join message to display.
            success_message: The success message to display.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            Tuple of (success, ChannelInfo or None).
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                
                channel = await self.required_channel_repository.get_by_field("channel_id", channel_id)
                if not channel:
                    logger.warning(f"ChannelManager: Channel {channel_id} not found")
                    return False, None
                
                # Update fields
                if channel_username is not None:
                    channel.channel_username = channel_username
                if channel_title is not None:
                    channel.channel_title = channel_title
                if is_required is not None:
                    channel.is_required = is_required
                if verification_enabled is not None:
                    channel.verification_enabled = verification_enabled
                if priority is not None:
                    channel.priority = priority
                if join_message is not None:
                    channel.join_message = join_message
                if success_message is not None:
                    channel.success_message = success_message
                
                channel.updated_at = datetime.utcnow()
                await session.commit()
                
                # Invalidate cache
                self._required_channels_cache = None
                
                # Log audit
                if admin_id:
                    changes = {}
                    if channel_username is not None:
                        changes["channel_username"] = channel_username
                    if channel_title is not None:
                        changes["channel_title"] = channel_title
                    if is_required is not None:
                        changes["is_required"] = is_required
                    
                    await self.audit_log_repository.log_action(
                        administrator_id=admin_id,
                        action=f"Update required channel",
                        action_type="channel_management",
                        target_id=channel.id,
                        target_type="required_channel",
                        target_name=channel.channel_title or channel.channel_username or str(channel.channel_id),
                        details={"channel_id": channel_id, "changes": changes},
                        success=True
                    )
                
                channel_info = ChannelInfo(
                    id=channel.id,
                    channel_id=channel.channel_id,
                    channel_username=channel.channel_username,
                    channel_title=channel.channel_title,
                    channel_type=channel.channel_type,
                    is_required=channel.is_required,
                    verification_enabled=channel.verification_enabled,
                    priority=channel.priority,
                    join_message=channel.join_message,
                    success_message=channel.success_message,
                    created_at=channel.created_at,
                    updated_at=channel.updated_at
                )
                
                logger.info(f"ChannelManager: Updated required channel {channel_id}")
                return True, channel_info
                
        except Exception as e:
            logger.error(f"ChannelManager: Error updating channel {channel_id}: {e}")
            return False, None
    
    async def remove_channel(self, channel_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Remove a required channel.
        
        Args:
            channel_id: The channel ID to remove.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if the channel was removed.
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                
                channel = await self.required_channel_repository.get_by_field("channel_id", channel_id)
                if not channel:
                    logger.warning(f"ChannelManager: Channel {channel_id} not found")
                    return False
                
                channel_name = channel.channel_title or channel.channel_username or str(channel.channel_id)
                
                await self.required_channel_repository.delete(channel.id)
                await session.commit()
                
                # Invalidate cache
                self._required_channels_cache = None
                
                # Log audit
                if admin_id:
                    await self.audit_log_repository.log_action(
                        administrator_id=admin_id,
                        action=f"Remove required channel",
                        action_type="channel_management",
                        target_id=channel.id,
                        target_type="required_channel",
                        target_name=channel_name,
                        details={"channel_id": channel_id},
                        success=True
                    )
                
                logger.info(f"ChannelManager: Removed required channel {channel_id}")
                return True
                
        except Exception as e:
            logger.error(f"ChannelManager: Error removing channel {channel_id}: {e}")
            return False
    
    async def reorder_channels(self, channel_ids: List[int], admin_id: Optional[int] = None) -> bool:
        """
        Reorder required channels by updating their priorities.
        
        Args:
            channel_ids: List of channel IDs in the new order.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if the channels were reordered.
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                
                for index, channel_id in enumerate(channel_ids):
                    channel = await self.required_channel_repository.get_by_field("channel_id", channel_id)
                    if channel:
                        channel.priority = index
                        channel.updated_at = datetime.utcnow()
                
                await session.commit()
                
                # Invalidate cache
                self._required_channels_cache = None
                
                # Log audit
                if admin_id:
                    await self.audit_log_repository.log_action(
                        administrator_id=admin_id,
                        action="Reorder required channels",
                        action_type="channel_management",
                        target_type="required_channel",
                        details={"new_order": channel_ids},
                        success=True
                    )
                
                logger.info(f"ChannelManager: Reordered {len(channel_ids)} channels")
                return True
                
        except Exception as e:
            logger.error(f"ChannelManager: Error reordering channels: {e}")
            return False
    
    async def verify_user_channels(self, user_id: int, user: Optional[Any] = None) -> UserChannelStatus:
        """
        Verify if a user has joined all required channels.
        
        Args:
            user_id: The Telegram user ID.
            user: Optional user object from callback.
            
        Returns:
            UserChannelStatus with verification results.
        """
        required_channels = await self.get_required_channels()
        
        if not required_channels:
            # No required channels, user has access
            return UserChannelStatus(
                user_id=user_id,
                required_channels=required_channels,
                all_joined=True,
                verification_required=False,
                last_verified=datetime.utcnow()
            )
        
        # Check each channel
        joined_channels = []
        missing_channels = []
        verification_results = []
        
        for channel in required_channels:
            if not channel.verification_enabled:
                # Skip verification for this channel
                joined_channels.append(channel.channel_id)
                continue
            
            result = await self._verify_channel_membership(user_id, channel, user)
            verification_results.append(result)
            
            if result.is_member and result.verification_success:
                joined_channels.append(channel.channel_id)
            else:
                missing_channels.append(channel)
        
        all_joined = len(missing_channels) == 0
        
        status = UserChannelStatus(
            user_id=user_id,
            required_channels=required_channels,
            joined_channels=joined_channels,
            missing_channels=missing_channels,
            all_joined=all_joined,
            verification_required=not all_joined,
            last_verified=datetime.utcnow()
        )
        
        logger.debug(f"ChannelManager: Verification for user {user_id} - all_joined={all_joined}")
        return status
    
    async def _verify_channel_membership(
        self,
        user_id: int,
        channel: ChannelInfo,
        user: Optional[Any] = None
    ) -> ChannelVerificationResult:
        """
        Verify if a user is a member of a specific channel.
        
        Args:
            user_id: The Telegram user ID.
            channel: The channel to verify.
            user: Optional user object from callback.
            
        Returns:
            ChannelVerificationResult.
        """
        result = ChannelVerificationResult(
            channel_id=channel.channel_id,
            channel_username=channel.channel_username,
            channel_title=channel.channel_title,
            verification_success=False,
            error_message="Verification not available"
        )
        
        # Try to use the bot API for verification
        if self._bot:
            try:
                # Check if user is member of channel
                # Note: This requires the bot to be an admin in the channel
                from aiogram.types import ChatMemberUpdated
                from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
                
                try:
                    # Try to get chat member
                    chat_member = await self._bot.get_chat_member(
                        chat_id=channel.channel_id,
                        user_id=user_id
                    )
                    
                    # Check membership status
                    if hasattr(chat_member, 'status'):
                        result.is_member = chat_member.status in ['member', 'administrator', 'creator']
                        result.is_admin = chat_member.status in ['administrator', 'creator']
                        result.can_send_messages = chat_member.status != 'restricted'
                        result.verification_success = True
                        result.verified_at = datetime.utcnow()
                        
                except TelegramForbiddenError:
                    result.error_message = "Bot does not have permission to check membership"
                    result.verification_success = False
                    
                except TelegramBadRequest as e:
                    result.error_message = f"Invalid channel or user: {e}"
                    result.verification_success = False
                    
                except Exception as e:
                    result.error_message = f"Verification error: {e}"
                    result.verification_success = False
                    
            except Exception as e:
                logger.error(f"ChannelManager: Error verifying membership for user {user_id} in channel {channel.channel_id}: {e}")
                result.error_message = f"Verification error: {e}"
        
        return result
    
    async def check_user_access(self, user_id: int, user: Optional[Any] = None) -> bool:
        """
        Check if a user has access to the bot (has joined all required channels).
        
        Args:
            user_id: The Telegram user ID.
            user: Optional user object from callback.
            
        Returns:
            True if the user has access, False otherwise.
        """
        status = await self.verify_user_channels(user_id, user)
        return status.all_joined
    
    async def get_missing_channels(self, user_id: int, user: Optional[Any] = None) -> List[ChannelInfo]:
        """
        Get the list of channels that a user still needs to join.
        
        Args:
            user_id: The Telegram user ID.
            user: Optional user object from callback.
            
        Returns:
            List of ChannelInfo objects for channels the user hasn't joined.
        """
        status = await self.verify_user_channels(user_id, user)
        return status.missing_channels
    
    async def get_join_urls(self, user_id: int, user: Optional[Any] = None) -> List[Dict[str, str]]:
        """
        Get the join URLs for channels that a user still needs to join.
        
        Args:
            user_id: The Telegram user ID.
            user: Optional user object from callback.
            
        Returns:
            List of dictionaries with channel info and join URLs.
        """
        missing_channels = await self.get_missing_channels(user_id, user)
        
        urls = []
        for channel in missing_channels:
            if channel.channel_username:
                url = f"https://t.me/{channel.channel_username}"
            else:
                # Use invite link format for private channels
                url = f"https://t.me/joinchat/{channel.channel_id}"
            
            urls.append({
                "channel_id": channel.channel_id,
                "channel_username": channel.channel_username,
                "channel_title": channel.channel_title,
                "join_url": url,
                "join_message": channel.join_message or f"Please join {channel.channel_title}"
            })
        
        return urls
    
    async def enable_verification(self, channel_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Enable verification for a channel.
        
        Args:
            channel_id: The channel ID.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if verification was enabled.
        """
        return await self._update_channel_field(
            channel_id, "verification_enabled", True, admin_id
        )
    
    async def disable_verification(self, channel_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Disable verification for a channel.
        
        Args:
            channel_id: The channel ID.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if verification was disabled.
        """
        return await self._update_channel_field(
            channel_id, "verification_enabled", False, admin_id
        )
    
    async def enable_channel(self, channel_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Enable a required channel.
        
        Args:
            channel_id: The channel ID.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if the channel was enabled.
        """
        return await self._update_channel_field(
            channel_id, "is_required", True, admin_id
        )
    
    async def disable_channel(self, channel_id: int, admin_id: Optional[int] = None) -> bool:
        """
        Disable a required channel.
        
        Args:
            channel_id: The channel ID.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if the channel was disabled.
        """
        return await self._update_channel_field(
            channel_id, "is_required", False, admin_id
        )
    
    async def _update_channel_field(
        self,
        channel_id: int,
        field_name: str,
        value: Any,
        admin_id: Optional[int] = None
    ) -> bool:
        """
        Update a specific field of a channel.
        
        Args:
            channel_id: The channel ID.
            field_name: The field name to update.
            value: The value to set.
            admin_id: The administrator ID for audit logging.
            
        Returns:
            True if the field was updated.
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                
                channel = await self.required_channel_repository.get_by_field("channel_id", channel_id)
                if not channel:
                    return False
                
                setattr(channel, field_name, value)
                channel.updated_at = datetime.utcnow()
                await session.commit()
                
                # Invalidate cache
                self._required_channels_cache = None
                
                # Log audit
                if admin_id:
                    await self.audit_log_repository.log_action(
                        administrator_id=admin_id,
                        action=f"Update channel {field_name}",
                        action_type="channel_management",
                        target_id=channel.id,
                        target_type="required_channel",
                        target_name=channel.channel_title or channel.channel_username or str(channel.channel_id),
                        details={"channel_id": channel_id, "field": field_name, "value": value},
                        success=True
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"ChannelManager: Error updating field {field_name} for channel {channel_id}: {e}")
            return False
    
    async def get_channel_count(self) -> int:
        """
        Get the total number of required channels.
        
        Returns:
            Count of required channels.
        """
        channels = await self.get_required_channels()
        return len(channels)
    
    async def is_channel_required(self, channel_id: int) -> bool:
        """
        Check if a channel is required.
        
        Args:
            channel_id: The channel ID.
            
        Returns:
            True if the channel is required.
        """
        try:
            async with self.session_factory() as session:
                self.required_channel_repository.session = session
                return await self.required_channel_repository.is_required(channel_id)
        except Exception as e:
            logger.error(f"ChannelManager: Error checking if channel {channel_id} is required: {e}")
            return False
    
    async def refresh_cache(self) -> None:
        """
        Force refresh the required channels cache.
        """
        await self._load_required_channels(force=True)
        logger.info("ChannelManager: Cache refreshed")
