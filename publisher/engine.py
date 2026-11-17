"""
Publishing engine for Telegram Auto Publisher Pro
Handles all publishing operations using Telethon
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple, Set
from enum import Enum

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    MessageEmptyError,
    MessageNotModifiedError,
    MessageIdInvalidError,
    PeerFloodError,
    ChatSendMediaForbiddenError,
    ChatAdminRequiredError,
    UserRestrictedError,
    UserBannedInChannelError,
)
from telethon.tl.types import (
    InputPeerUser,
    InputPeerChat,
    InputPeerChannel,
    InputMediaPhoto,
    InputMediaDocument,
    InputMediaUploadedDocument,
)

from config import config
from database.models import (
    TelegramAccount,
    Content,
    MediaFile,
    Group,
    PublishingTask,
    PublishingLog,
    TaskStatus,
    LogType,
    ContentType,
    MediaType,
)
from database.repositories import (
    TelegramAccountRepository,
    ContentRepository,
    MediaFileRepository,
    GroupRepository,
    PublishingTaskRepository,
    PublishingLogRepository,
    AccountSettingsRepository,
)
from accounts.manager import AccountManager
from security.encryption import EncryptionManager

logger = logging.getLogger(__name__)


class PublishResult(Enum):
    """Result of a publishing operation"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLOOD_WAIT = "flood_wait"
    NO_PERMISSION = "no_permission"
    INVALID_CONTENT = "invalid_content"


@dataclass
class PublishConfig:
    """Configuration for a publishing operation"""
    
    account_id: int
    group_id: Optional[int] = None
    content_id: Optional[int] = None
    text: Optional[str] = None
    media_file_id: Optional[int] = None
    caption: Optional[str] = None
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = False
    reply_to_message_id: Optional[int] = None
    
    # Scheduling
    schedule_time: Optional[datetime] = None
    
    # Retry
    max_retries: int = 3
    retry_delay: int = 60


@dataclass
class PublishResultData:
    """Result data from a publishing operation"""
    
    result: PublishResult
    message_id: Optional[int] = None
    message_link: Optional[str] = None
    error_message: Optional[str] = None
    flood_wait_seconds: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PublishingEngine:
    """
    Main publishing engine for Telegram Auto Publisher Pro.
    Handles all publishing operations using Telethon clients.
    """
    
    def __init__(
        self,
        config: any = None,
        account_manager: AccountManager = None,
        session_factory: Callable = None
    ):
        """
        Initialize the publishing engine.
        
        Args:
            config: Application configuration.
            account_manager: Account manager instance.
            session_factory: Database session factory.
        """
        self.config = config or config
        self.account_manager = account_manager
        self.session_factory = session_factory
        
        # Notification and statistics managers
        self.notification_manager = None
        self.statistics_manager = None
        
        # Active publishing tasks
        self._active_tasks: Dict[int, asyncio.Task] = {}
        
        # Rate limiting
        self._rate_limited_accounts: Dict[int, datetime] = {}
        self._rate_limit_delay = 1  # seconds between publishes for same account
        
        # Flood wait tracking
        self._flood_wait_accounts: Dict[int, datetime] = {}
        
        # Lock for concurrent operations
        self._publish_lock = asyncio.Lock()
    
    def set_dependencies(
        self,
        notification_manager: Any = None,
        statistics_manager: Any = None
    ):
        """
        Set optional dependencies.
        
        Args:
            notification_manager: Notification manager instance.
            statistics_manager: Statistics manager instance.
        """
        self.notification_manager = notification_manager
        self.statistics_manager = statistics_manager
    
    async def publish(
        self,
        config: PublishConfig
    ) -> PublishResultData:
        """
        Publish content to a group or channel.
        
        Args:
            config: Publishing configuration.
            
        Returns:
            PublishResultData with the result of the operation.
        """
        async with self._publish_lock:
            # Check rate limiting
            if await self._check_rate_limit(config.account_id):
                return PublishResultData(
                    result=PublishResult.FLOOD_WAIT,
                    error_message="Rate limited",
                    flood_wait_seconds=self._rate_limit_delay
                )
            
            # Check flood wait
            if await self._check_flood_wait(config.account_id):
                return PublishResultData(
                    result=PublishResult.FLOOD_WAIT,
                    error_message="Flood wait",
                    flood_wait_seconds=self.config.telegram.FLOOD_SLEEP_THRESHOLD
                )
            
            try:
                # Get client
                client = await self.account_manager.get_account_client(config.account_id)
                if not client:
                    return PublishResultData(
                        result=PublishResult.FAILED,
                        error_message="Account client not available"
                    )
                
                # Get target entity
                target_entity = await self._get_target_entity(client, config.group_id)
                if not target_entity:
                    return PublishResultData(
                        result=PublishResult.FAILED,
                        error_message="Target group not found"
                    )
                
                # Prepare content
                media, text, parse_mode = await self._prepare_content(config)
                
                # Publish
                if media:
                    result = await self._publish_media(
                        client,
                        target_entity,
                        media,
                        text,
                        parse_mode,
                        config
                    )
                else:
                    result = await self._publish_text(
                        client,
                        target_entity,
                        text,
                        parse_mode,
                        config
                    )
                
                # Update statistics
                if self.statistics_manager:
                    if result.result == PublishResult.SUCCESS:
                        await self.statistics_manager.increment_successful(config.account_id)
                    else:
                        await self.statistics_manager.increment_failed(config.account_id)
                
                # Send notification if configured
                if self.notification_manager:
                    if result.result == PublishResult.SUCCESS:
                        await self.notification_manager.notify_publish_success(
                            config.account_id,
                            result.message_id
                        )
                    else:
                        await self.notification_manager.notify_publish_failure(
                            config.account_id,
                            result.error_message
                        )
                
                return result
                
            except FloodWaitError as e:
                logger.warning(f"FloodWait for account {config.account_id}: {e.seconds}s")
                self._flood_wait_accounts[config.account_id] = datetime.utcnow() + e.seconds
                return PublishResultData(
                    result=PublishResult.FLOOD_WAIT,
                    error_message="FloodWait",
                    flood_wait_seconds=e.seconds
                )
            except ChatAdminRequiredError:
                logger.warning(f"Admin rights required for account {config.account_id}")
                return PublishResultData(
                    result=PublishResult.NO_PERMISSION,
                    error_message="Admin rights required"
                )
            except ChatSendMediaForbiddenError:
                logger.warning(f"Media sending forbidden for account {config.account_id}")
                return PublishResultData(
                    result=PublishResult.NO_PERMISSION,
                    error_message="Media sending forbidden"
                )
            except UserBannedInChannelError:
                logger.warning(f"User banned in channel for account {config.account_id}")
                return PublishResultData(
                    result=PublishResult.NO_PERMISSION,
                    error_message="User banned in channel"
                )
            except UserRestrictedError:
                logger.warning(f"User restricted for account {config.account_id}")
                return PublishResultData(
                    result=PublishResult.NO_PERMISSION,
                    error_message="User restricted"
                )
            except Exception as e:
                logger.error(f"Publishing failed for account {config.account_id}: {e}")
                return PublishResultData(
                    result=PublishResult.FAILED,
                    error_message=str(e)
                )
    
    async def _check_rate_limit(self, account_id: int) -> bool:
        """
        Check if account is rate limited.
        
        Args:
            account_id: The account ID.
            
        Returns:
            True if rate limited, False otherwise.
        """
        if account_id in self._rate_limited_accounts:
            if datetime.utcnow() < self._rate_limited_accounts[account_id]:
                return True
            else:
                del self._rate_limited_accounts[account_id]
        
        # Apply rate limit
        self._rate_limited_accounts[account_id] = datetime.utcnow() + self._rate_limit_delay
        return False
    
    async def _check_flood_wait(self, account_id: int) -> bool:
        """
        Check if account is in flood wait.
        
        Args:
            account_id: The account ID.
            
        Returns:
            True if in flood wait, False otherwise.
        """
        if account_id in self._flood_wait_accounts:
            if datetime.utcnow() < self._flood_wait_accounts[account_id]:
                return True
            else:
                del self._flood_wait_accounts[account_id]
        
        return False
    
    async def _get_target_entity(self, client: TelegramClient, group_id: Optional[int]) -> Optional[Any]:
        """
        Get the target entity (group, channel, or user) for publishing.
        
        Args:
            client: Telegram client.
            group_id: The group ID.
            
        Returns:
            The target entity, or None if not found.
        """
        if not group_id:
            return None
        
        try:
            # Try to get the entity
            entity = await client.get_entity(group_id)
            return entity
        except Exception as e:
            logger.error(f"Error getting entity {group_id}: {e}")
            return None
    
    async def _prepare_content(self, config: PublishConfig) -> Tuple[Optional[Any], str, str]:
        """
        Prepare content for publishing.
        
        Args:
            config: Publishing configuration.
            
        Returns:
            Tuple of (media, text, parse_mode).
        """
        media = None
        text = config.text or ""
        parse_mode = config.parse_mode
        
        # If we have a content_id, load the content
        if config.content_id:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                content = await content_repo.get_content_with_media(config.content_id)
                
                if content:
                    text = content.text or text
                    parse_mode = content.parse_mode or parse_mode
                    
                    # Load media if available
                    if content.media_file_id:
                        media_file_repo = MediaFileRepository(session)
                        media_file = await media_file_repo.get_media_file(content.media_file_id)
                        
                        if media_file:
                            media = await self._load_media(media_file)
        
        # If we have a media_file_id directly
        elif config.media_file_id:
            async with self.session_factory() as session:
                media_file_repo = MediaFileRepository(session)
                media_file = await media_file_repo.get_media_file(config.media_file_id)
                
                if media_file:
                    media = await self._load_media(media_file)
        
        # Use caption if provided and no text
        if not text and config.caption:
            text = config.caption
        
        return media, text, parse_mode
    
    async def _load_media(self, media_file: MediaFile) -> Optional[Any]:
        """
        Load media from a MediaFile object.
        
        Args:
            media_file: The MediaFile object.
            
        Returns:
            Telethon media object, or None if failed.
        """
        try:
            # Check if we have a file_id (already uploaded to Telegram)
            if media_file.file_id:
                # We can't directly use file_id without a client
                # This would need to be handled differently
                return None
            
            # If we have a file_path, load from disk
            if media_file.file_path and Path(media_file.file_path).exists():
                file_path = Path(media_file.file_path)
                
                # Determine media type
                if media_file.media_type == MediaType.PHOTO.value:
                    return InputMediaUploadedPhoto(file_path)
                elif media_file.media_type == MediaType.VIDEO.value:
                    return InputMediaUploadedDocument(file_path)
                elif media_file.media_type == MediaType.DOCUMENT.value:
                    return InputMediaUploadedDocument(file_path)
                elif media_file.media_type == MediaType.AUDIO.value:
                    return InputMediaUploadedDocument(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading media: {e}")
            return None
    
    async def _publish_text(
        self,
        client: TelegramClient,
        entity: Any,
        text: str,
        parse_mode: str,
        config: PublishConfig
    ) -> PublishResultData:
        """
        Publish text message.
        
        Args:
            client: Telegram client.
            entity: Target entity.
            text: Text to publish.
            parse_mode: Parse mode for the text.
            config: Publishing configuration.
            
        Returns:
            PublishResultData with the result.
        """
        try:
            # Convert parse_mode
            telethon_parse_mode = self._convert_parse_mode(parse_mode)
            
            message = await client.send_message(
                entity,
                text,
                parse_mode=telethon_parse_mode,
                disable_web_page_preview=config.disable_web_page_preview,
                reply_to=config.reply_to_message_id
            )
            
            return PublishResultData(
                result=PublishResult.SUCCESS,
                message_id=message.id,
                message_link=f"https://t.me/c/{entity.id}/{message.id}" if hasattr(entity, 'id') else None
            )
            
        except Exception as e:
            logger.error(f"Error publishing text: {e}")
            return PublishResultData(
                result=PublishResult.FAILED,
                error_message=str(e)
            )
    
    async def _publish_media(
        self,
        client: TelegramClient,
        entity: Any,
        media: Any,
        caption: str,
        parse_mode: str,
        config: PublishConfig
    ) -> PublishResultData:
        """
        Publish media message.
        
        Args:
            client: Telegram client.
            entity: Target entity.
            media: Media to publish.
            caption: Caption for the media.
            parse_mode: Parse mode for the caption.
            config: Publishing configuration.
            
        Returns:
            PublishResultData with the result.
        """
        try:
            # Convert parse_mode
            telethon_parse_mode = self._convert_parse_mode(parse_mode)
            
            # Check if media is a list (album)
            if isinstance(media, list):
                # Send as album
                result = await client.send_media_group(
                    entity,
                    media,
                    caption=caption,
                    parse_mode=telethon_parse_mode
                )
                
                # Get first message ID
                first_message = result[0] if result else None
                return PublishResultData(
                    result=PublishResult.SUCCESS,
                    message_id=first_message.id if first_message else None,
                    message_link=f"https://t.me/c/{entity.id}/{first_message.id}" if first_message and hasattr(entity, 'id') else None
                )
            else:
                # Send single media
                message = await client.send_file(
                    entity,
                    media,
                    caption=caption,
                    parse_mode=telethon_parse_mode,
                    reply_to=config.reply_to_message_id
                )
                
                return PublishResultData(
                    result=PublishResult.SUCCESS,
                    message_id=message.id,
                    message_link=f"https://t.me/c/{entity.id}/{message.id}" if hasattr(entity, 'id') else None
                )
                
        except Exception as e:
            logger.error(f"Error publishing media: {e}")
            return PublishResultData(
                result=PublishResult.FAILED,
                error_message=str(e)
            )
    
    def _convert_parse_mode(self, parse_mode: str) -> Optional[str]:
        """
        Convert parse mode string to Telethon format.
        
        Args:
            parse_mode: The parse mode string.
            
        Returns:
            Telethon parse mode, or None.
        """
        parse_modes = {
            "HTML": "html",
            "Markdown": "md",
            "MarkdownV2": "md2",
            "text": None,
            "": None
        }
        
        return parse_modes.get(parse_mode.upper(), None)
    
    async def publish_to_all_groups(
        self,
        account_id: int,
        content_id: Optional[int] = None,
        text: Optional[str] = None,
        group_ids: Optional[List[int]] = None
    ) -> Dict[int, PublishResultData]:
        """
        Publish content to all selected groups for an account.
        
        Args:
            account_id: The account ID.
            content_id: The content ID to publish.
            text: Text to publish.
            group_ids: List of group IDs to publish to. If None, uses all groups for the account.
            
        Returns:
            Dictionary mapping group IDs to PublishResultData.
        """
        results = {}
        
        try:
            # Get account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                if not settings:
                    return results
                
                # Get groups to publish to
                if group_ids is None:
                    group_ids = settings.selected_group_ids or []
            
            # Publish to each group
            for group_id in group_ids:
                config = PublishConfig(
                    account_id=account_id,
                    group_id=group_id,
                    content_id=content_id,
                    text=text
                )
                
                result = await self.publish(config)
                results[group_id] = result
                
                # Add delay between publishes to avoid rate limiting
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error publishing to all groups: {e}")
        
        return results
    
    async def start_publishing(self, account_id: int) -> bool:
        """
        Start automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            True if started successfully, False otherwise.
        """
        try:
            # Update account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                await settings_repo.update_publishing_settings(
                    account_id,
                    publishing_enabled=True
                )
            
            # Start the publishing task
            task = asyncio.create_task(self._publishing_loop(account_id))
            self._active_tasks[account_id] = task
            
            logger.info(f"Started publishing for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting publishing for account {account_id}: {e}")
            return False
    
    async def stop_publishing(self, account_id: int) -> bool:
        """
        Stop automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            True if stopped successfully, False otherwise.
        """
        try:
            # Cancel the publishing task
            if account_id in self._active_tasks:
                self._active_tasks[account_id].cancel()
                del self._active_tasks[account_id]
            
            # Update account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                await settings_repo.update_publishing_settings(
                    account_id,
                    publishing_enabled=False
                )
            
            logger.info(f"Stopped publishing for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping publishing for account {account_id}: {e}")
            return False
    
    async def pause_publishing(self, account_id: int) -> bool:
        """
        Pause automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            True if paused successfully, False otherwise.
        """
        try:
            # Update account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                if settings:
                    # Store current state
                    await settings_repo.update(account_id, {
                        "publishing_enabled": False,
                        "paused": True
                    })
            
            logger.info(f"Paused publishing for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error pausing publishing for account {account_id}: {e}")
            return False
    
    async def resume_publishing(self, account_id: int) -> bool:
        """
        Resume paused publishing for an account.
        
        Args:
            account_id: The account ID.
            
        Returns:
            True if resumed successfully, False otherwise.
        """
        try:
            # Update account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                if settings and getattr(settings, 'paused', False):
                    await settings_repo.update(account_id, {
                        "publishing_enabled": True,
                        "paused": False
                    })
            
            logger.info(f"Resumed publishing for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resuming publishing for account {account_id}: {e}")
            return False
    
    async def _publishing_loop(self, account_id: int):
        """
        Main publishing loop for an account.
        
        Args:
            account_id: The account ID.
        """
        try:
            while True:
                # Check if publishing is enabled
                async with self.session_factory() as session:
                    settings_repo = AccountSettingsRepository(session)
                    settings = await settings_repo.get_settings_by_account(account_id)
                    
                    if not settings or not settings.publishing_enabled:
                        break
                    
                    # Get publishing interval
                    interval_minutes = settings.publishing_interval_minutes or 60
                
                # Wait for the interval
                await asyncio.sleep(interval_minutes * 60)
                
                # Check if we should continue
                async with self.session_factory() as session:
                    settings_repo = AccountSettingsRepository(session)
                    settings = await settings_repo.get_settings_by_account(account_id)
                    
                    if not settings or not settings.publishing_enabled:
                        break
                
                # Publish to all selected groups
                async with self.session_factory() as session:
                    settings_repo = AccountSettingsRepository(session)
                    settings = await settings_repo.get_settings_by_account(account_id)
                    
                    if settings:
                        # Select content
                        content_id = None
                        if settings.use_random_content:
                            # Get random content
                            content_repo = ContentRepository(session)
                            content = await content_repo.get_random_content(
                                user_id=None,  # Will be set from account
                                exclude_id=None
                            )
                            if content:
                                content_id = content.id
                        elif settings.selected_content_id:
                            content_id = settings.selected_content_id
                        
                        # Publish
                        results = await self.publish_to_all_groups(
                            account_id,
                            content_id=content_id,
                            group_ids=settings.selected_group_ids
                        )
                        
                        logger.info(f"Published to {len(results)} groups for account {account_id}")
                
        except asyncio.CancelledError:
            logger.info(f"Publishing loop cancelled for account {account_id}")
        except Exception as e:
            logger.error(f"Error in publishing loop for account {account_id}: {e}")
    
    async def stop_all(self) -> int:
        """
        Stop all active publishing tasks.
        
        Returns:
            Number of tasks stopped.
        """
        count = 0
        
        for account_id in list(self._active_tasks.keys()):
            if await self.stop_publishing(account_id):
                count += 1
        
        return count


__all__ = [
    'PublishResult',
    'PublishConfig',
    'PublishResultData',
    'PublishingEngine',
]
