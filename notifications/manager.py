"""
Notification manager for Telegram Auto Publisher Pro
Manages user notifications and delivery through the control bot
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User,
    Notification,
    TelegramAccount,
    PublishingTask,
    PublishingLog,
)
from database.repositories import (
    UserRepository,
    NotificationRepository,
    TelegramAccountRepository,
    PublishingTaskRepository,
    PublishingLogRepository,
)

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications"""
    
    # System notifications
    SYSTEM = "system"
    WELCOME = "welcome"
    MAINTENANCE = "maintenance"
    
    # Account notifications
    ACCOUNT_CONNECTED = "account_connected"
    ACCOUNT_DISCONNECTED = "account_disconnected"
    ACCOUNT_ERROR = "account_error"
    ACCOUNT_EXPIRED = "account_expired"
    
    # Publishing notifications
    PUBLISH_STARTED = "publish_started"
    PUBLISH_COMPLETED = "publish_completed"
    PUBLISH_FAILED = "publish_failed"
    PUBLISH_PAUSED = "publish_paused"
    PUBLISH_RESUMED = "publish_resumed"
    SCHEDULE_STARTED = "schedule_started"
    SCHEDULE_STOPPED = "schedule_stopped"
    
    # Task notifications
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    
    # Subscription notifications
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    
    # Channel subscription notifications
    CHANNEL_REQUIRED = "channel_required"
    CHANNEL_VERIFIED = "channel_verified"
    CHANNEL_FAILED = "channel_failed"
    
    # Content notifications
    CONTENT_ADDED = "content_added"
    CONTENT_UPDATED = "content_updated"
    CONTENT_DELETED = "content_deleted"
    
    # Group notifications
    GROUP_ADDED = "group_added"
    GROUP_REMOVED = "group_removed"
    GROUP_PERMISSION_DENIED = "group_permission_denied"
    
    # Admin notifications
    ADMIN_BROADCAST = "admin_broadcast"
    ADMIN_ANNOUNCEMENT = "admin_announcement"
    
    # Error notifications
    ERROR = "error"
    RATE_LIMIT = "rate_limit"
    FLOOD_WAIT = "flood_wait"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationInfo:
    """Information about a notification"""
    
    id: Optional[int] = None
    user_id: int = 0
    notification_type: NotificationType = NotificationType.SYSTEM
    
    # Content
    title: str = ""
    message: str = ""
    
    # Status
    is_read: bool = False
    is_sent: bool = False
    
    # Related data
    related_id: Optional[int] = None
    related_type: Optional[str] = None
    
    # Action buttons
    action_buttons: List[Dict[str, Any]] = field(default_factory=list)
    
    # Priority
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # Delivery info
    delivery_attempts: int = 0
    last_error: Optional[str] = None


@dataclass
class NotificationStats:
    """Notification statistics"""
    
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_read: int = 0
    total_unread: int = 0
    pending_delivery: int = 0


class NotificationManager:
    """
    Manages user notifications and delivery through the control bot.
    Provides functionality for creating, sending, tracking, and managing notifications.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        user_repository: UserRepository = None,
        notification_repository: NotificationRepository = None,
        telegram_account_repository: TelegramAccountRepository = None,
        publishing_task_repository: PublishingTaskRepository = None,
        publishing_log_repository: PublishingLogRepository = None,
        config: any = None
    ):
        """
        Initialize the notification manager.
        
        Args:
            session_factory: Database session factory.
            user_repository: User repository instance.
            notification_repository: Notification repository instance.
            telegram_account_repository: Telegram account repository instance.
            publishing_task_repository: Publishing task repository instance.
            publishing_log_repository: Publishing log repository instance.
            config: Application configuration.
        """
        self.session_factory = session_factory
        self.config = config or config
        
        # Initialize repositories if not provided
        if user_repository:
            self.user_repository = user_repository
        else:
            self.user_repository = UserRepository(session_factory)
            
        if notification_repository:
            self.notification_repository = notification_repository
        else:
            self.notification_repository = NotificationRepository(session_factory)
            
        if telegram_account_repository:
            self.telegram_account_repository = telegram_account_repository
        else:
            self.telegram_account_repository = TelegramAccountRepository(session_factory)
            
        if publishing_task_repository:
            self.publishing_task_repository = publishing_task_repository
        else:
            self.publishing_task_repository = PublishingTaskRepository(session_factory)
            
        if publishing_log_repository:
            self.publishing_log_repository = publishing_log_repository
        else:
            self.publishing_log_repository = PublishingLogRepository(session_factory)
        
        # Notification callbacks for bot integration
        self._notification_callbacks: List[Callable] = []
        
        # Rate limiting
        self._notification_rate_limit: Dict[int, datetime] = {}
        self._rate_limit_interval = timedelta(seconds=1)  # Minimum 1 second between notifications per user
        
        logger.info("NotificationManager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the notification manager.
        """
        logger.info("NotificationManager: Initializing...")
        
        # Load any pending notifications
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                pending = await self.notification_repository.get_all(
                    filters={"is_sent": False, "is_read": False}
                )
                logger.info(f"NotificationManager: Found {len(pending)} pending notifications")
        except Exception as e:
            logger.error(f"NotificationManager: Error initializing: {e}")
            raise
        
        logger.info("NotificationManager: Initialized successfully")
    
    async def close(self) -> None:
        """
        Close the notification manager.
        """
        logger.info("NotificationManager: Closing...")
        self._notification_callbacks.clear()
        self._notification_rate_limit.clear()
        logger.info("NotificationManager: Closed")
    
    def register_callback(self, callback: Callable) -> None:
        """
        Register a callback for notification delivery.
        
        Args:
            callback: Async callback function that receives NotificationInfo.
        """
        if callback not in self._notification_callbacks:
            self._notification_callbacks.append(callback)
            logger.debug(f"NotificationManager: Registered callback {callback.__name__}")
    
    def unregister_callback(self, callback: Callable) -> bool:
        """
        Unregister a notification callback.
        
        Args:
            callback: The callback to remove.
            
        Returns:
            True if the callback was removed, False otherwise.
        """
        if callback in self._notification_callbacks:
            self._notification_callbacks.remove(callback)
            logger.debug(f"NotificationManager: Unregistered callback {callback.__name__}")
            return True
        return False
    
    async def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_id: Optional[int] = None,
        related_type: Optional[str] = None,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        save_to_db: bool = True
    ) -> NotificationInfo:
        """
        Create a new notification.
        
        Args:
            user_id: The Telegram user ID.
            notification_type: The type of notification.
            title: The notification title.
            message: The notification message.
            related_id: Optional related entity ID.
            related_type: Optional related entity type.
            action_buttons: Optional list of action buttons.
            priority: The notification priority.
            save_to_db: Whether to save to database.
            
        Returns:
            NotificationInfo object.
        """
        now = datetime.utcnow()
        
        notification_info = NotificationInfo(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=related_id,
            related_type=related_type,
            action_buttons=action_buttons or [],
            priority=priority,
            created_at=now,
            updated_at=now
        )
        
        if save_to_db:
            try:
                async with self.session_factory() as session:
                    self.notification_repository.session = session
                    
                    notification = Notification(
                        user_id=user_id,
                        notification_type=notification_type.value,
                        title=title,
                        message=message,
                        related_id=related_id,
                        related_type=related_type,
                        action_buttons=action_buttons or [],
                        created_at=now,
                        updated_at=now
                    )
                    
                    session.add(notification)
                    await session.flush()
                    await session.refresh(notification)
                    
                    notification_info.id = notification.id
                    logger.debug(f"NotificationManager: Created notification {notification.id} for user {user_id}")
                    
                    await session.commit()
            except Exception as e:
                logger.error(f"NotificationManager: Error saving notification to DB: {e}")
                await session.rollback()
                raise
        
        return notification_info
    
    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_id: Optional[int] = None,
        related_type: Optional[str] = None,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        force: bool = False
    ) -> bool:
        """
        Send a notification to a user.
        
        Args:
            user_id: The Telegram user ID.
            notification_type: The type of notification.
            title: The notification title.
            message: The notification message.
            related_id: Optional related entity ID.
            related_type: Optional related entity type.
            action_buttons: Optional list of action buttons.
            priority: The notification priority.
            force: Whether to bypass rate limiting.
            
        Returns:
            True if the notification was sent successfully.
        """
        # Check rate limiting
        if not force:
            last_sent = self._notification_rate_limit.get(user_id)
            if last_sent and (datetime.utcnow() - last_sent) < self._rate_limit_interval:
                logger.debug(f"NotificationManager: Rate limited for user {user_id}")
                return False
        
        try:
            # Create the notification
            notification_info = await self.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                related_id=related_id,
                related_type=related_type,
                action_buttons=action_buttons,
                priority=priority,
                save_to_db=True
            )
            
            # Update rate limit
            self._notification_rate_limit[user_id] = datetime.utcnow()
            
            # Trigger callbacks
            for callback in self._notification_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(notification_info)
                    else:
                        callback(notification_info)
                except Exception as e:
                    logger.error(f"NotificationManager: Error in callback {callback.__name__}: {e}")
            
            # Mark as sent in database
            if notification_info.id:
                async with self.session_factory() as session:
                    self.notification_repository.session = session
                    await self.notification_repository.mark_sent(notification_info.id)
                    await session.commit()
            
            logger.info(f"NotificationManager: Sent notification {notification_info.id} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"NotificationManager: Error sending notification to user {user_id}: {e}")
            return False
    
    async def send_account_notification(
        self,
        user_id: int,
        account_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send an account-related notification.
        
        Args:
            user_id: The Telegram user ID.
            account_id: The account ID.
            notification_type: The type of notification.
            title: The notification title.
            message: The notification message.
            action_buttons: Optional list of action buttons.
            
        Returns:
            True if the notification was sent successfully.
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=account_id,
            related_type="telegram_account",
            action_buttons=action_buttons
        )
    
    async def send_publishing_notification(
        self,
        user_id: int,
        task_id: Optional[int] = None,
        notification_type: NotificationType = NotificationType.PUBLISH_COMPLETED,
        title: str = "Publishing Update",
        message: str = "",
        action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send a publishing-related notification.
        
        Args:
            user_id: The Telegram user ID.
            task_id: Optional task ID.
            notification_type: The type of notification.
            title: The notification title.
            message: The notification message.
            action_buttons: Optional list of action buttons.
            
        Returns:
            True if the notification was sent successfully.
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=task_id,
            related_type="publishing_task",
            action_buttons=action_buttons
        )
    
    async def send_subscription_notification(
        self,
        user_id: int,
        subscription_id: Optional[int] = None,
        notification_type: NotificationType = NotificationType.SUBSCRIPTION_ACTIVATED,
        title: str = "Subscription Update",
        message: str = "",
        action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send a subscription-related notification.
        
        Args:
            user_id: The Telegram user ID.
            subscription_id: Optional subscription ID.
            notification_type: The type of notification.
            title: The notification title.
            message: The notification message.
            action_buttons: Optional list of action buttons.
            
        Returns:
            True if the notification was sent successfully.
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=subscription_id,
            related_type="subscription",
            action_buttons=action_buttons
        )
    
    async def send_error_notification(
        self,
        user_id: int,
        error_message: str,
        error_type: str = "Error",
        related_id: Optional[int] = None,
        related_type: Optional[str] = None
    ) -> bool:
        """
        Send an error notification.
        
        Args:
            user_id: The Telegram user ID.
            error_message: The error message.
            error_type: The error type.
            related_id: Optional related entity ID.
            related_type: Optional related entity type.
            
        Returns:
            True if the notification was sent successfully.
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ERROR,
            title=f"{error_type}",
            message=error_message,
            related_id=related_id,
            related_type=related_type,
            priority=NotificationPriority.URGENT
        )
    
    async def send_broadcast_notification(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.ADMIN_BROADCAST,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        exclude_users: Optional[List[int]] = None
    ) -> Dict[str, int]:
        """
        Send a broadcast notification to multiple users.
        
        Args:
            user_ids: List of user IDs to notify.
            title: The notification title.
            message: The notification message.
            notification_type: The type of notification.
            action_buttons: Optional list of action buttons.
            exclude_users: Optional list of user IDs to exclude.
            
        Returns:
            Dictionary with statistics (sent, failed, skipped).
        """
        exclude_set = set(exclude_users or [])
        results = {"sent": 0, "failed": 0, "skipped": 0}
        
        for user_id in user_ids:
            if user_id in exclude_set:
                results["skipped"] += 1
                continue
                
            try:
                success = await self.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    action_buttons=action_buttons,
                    force=False
                )
                
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"NotificationManager: Error sending broadcast to user {user_id}: {e}")
                results["failed"] += 1
        
        logger.info(f"NotificationManager: Broadcast completed - {results}")
        return results
    
    async def get_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False
    ) -> List[NotificationInfo]:
        """
        Get notifications for a user.
        
        Args:
            user_id: The Telegram user ID.
            limit: Maximum number of notifications to return.
            offset: Offset for pagination.
            unread_only: Whether to return only unread notifications.
            
        Returns:
            List of NotificationInfo objects.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                
                if unread_only:
                    notifications = await self.notification_repository.get_unread_notifications(
                        user_id, limit
                    )
                else:
                    notifications = await self.notification_repository.get_notifications_by_user(
                        user_id, limit
                    )
                
                return [
                    NotificationInfo(
                        id=n.id,
                        user_id=n.user_id,
                        notification_type=NotificationType(n.notification_type) if n.notification_type else NotificationType.SYSTEM,
                        title=n.title or "",
                        message=n.message or "",
                        is_read=n.is_read,
                        is_sent=n.is_sent,
                        related_id=n.related_id,
                        related_type=n.related_type,
                        action_buttons=n.action_buttons or [],
                        created_at=n.created_at,
                        updated_at=n.updated_at,
                        sent_at=n.sent_at,
                        read_at=n.read_at
                    )
                    for n in notifications
                ]
                
        except Exception as e:
            logger.error(f"NotificationManager: Error getting notifications for user {user_id}: {e}")
            return []
    
    async def get_unread_count(self, user_id: int) -> int:
        """
        Get the count of unread notifications for a user.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            Count of unread notifications.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                return await self.notification_repository.count_unread(user_id)
        except Exception as e:
            logger.error(f"NotificationManager: Error getting unread count for user {user_id}: {e}")
            return 0
    
    async def mark_read(self, notification_id: int, user_id: Optional[int] = None) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: The notification ID.
            user_id: Optional user ID for validation.
            
        Returns:
            True if the notification was marked as read.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                
                # Validate user ownership if user_id is provided
                if user_id:
                    notification = await self.notification_repository.get(notification_id)
                    if not notification or notification.user_id != user_id:
                        logger.warning(f"NotificationManager: User {user_id} tried to mark notification {notification_id} as read but doesn't own it")
                        return False
                
                result = await self.notification_repository.mark_read(notification_id)
                await session.commit()
                
                if result:
                    logger.debug(f"NotificationManager: Marked notification {notification_id} as read")
                
                return result
                
        except Exception as e:
            logger.error(f"NotificationManager: Error marking notification {notification_id} as read: {e}")
            return False
    
    async def mark_all_read(self, user_id: int) -> int:
        """
        Mark all notifications for a user as read.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            Number of notifications marked as read.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                
                from sqlalchemy import update, and_
                from sqlalchemy.future import select
                from database.models import Notification
                
                stmt = (
                    update(Notification)
                    .where(and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False
                    ))
                    .values(is_read=True, read_at=datetime.utcnow(), updated_at=datetime.utcnow())
                )
                
                result = await session.execute(stmt)
                count = result.rowcount
                await session.commit()
                
                logger.info(f"NotificationManager: Marked {count} notifications as read for user {user_id}")
                return count
                
        except Exception as e:
            logger.error(f"NotificationManager: Error marking all notifications as read for user {user_id}: {e}")
            return 0
    
    async def delete_notification(self, notification_id: int, user_id: Optional[int] = None) -> bool:
        """
        Delete a notification.
        
        Args:
            notification_id: The notification ID.
            user_id: Optional user ID for validation.
            
        Returns:
            True if the notification was deleted.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                
                # Validate user ownership if user_id is provided
                if user_id:
                    notification = await self.notification_repository.get(notification_id)
                    if not notification or notification.user_id != user_id:
                        logger.warning(f"NotificationManager: User {user_id} tried to delete notification {notification_id} but doesn't own it")
                        return False
                
                result = await self.notification_repository.delete(notification_id)
                await session.commit()
                
                if result:
                    logger.debug(f"NotificationManager: Deleted notification {notification_id}")
                
                return result
                
        except Exception as e:
            logger.error(f"NotificationManager: Error deleting notification {notification_id}: {e}")
            return False
    
    async def get_statistics(self) -> NotificationStats:
        """
        Get notification statistics.
        
        Returns:
            NotificationStats object.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                
                from sqlalchemy import select, func, and_, or_
                from database.models import Notification
                
                # Total sent
                total_sent = await session.scalar(
                    select(func.count()).select_from(Notification).where(Notification.is_sent == True)
                )
                
                # Total delivered (sent and not failed)
                total_delivered = await session.scalar(
                    select(func.count()).select_from(Notification).where(
                        and_(
                            Notification.is_sent == True,
                            or_(
                                Notification.last_error == None,
                                Notification.last_error == ""
                            )
                        )
                    )
                )
                
                # Total failed
                total_failed = await session.scalar(
                    select(func.count()).select_from(Notification).where(
                        and_(
                            Notification.is_sent == True,
                            Notification.last_error != None,
                            Notification.last_error != ""
                        )
                    )
                )
                
                # Total read
                total_read = await session.scalar(
                    select(func.count()).select_from(Notification).where(Notification.is_read == True)
                )
                
                # Total unread
                total_unread = await session.scalar(
                    select(func.count()).select_from(Notification).where(
                        and_(
                            Notification.is_read == False,
                            Notification.is_sent == True
                        )
                    )
                )
                
                # Pending delivery
                pending_delivery = await session.scalar(
                    select(func.count()).select_from(Notification).where(
                        and_(
                            Notification.is_sent == False,
                            Notification.is_read == False
                        )
                    )
                )
                
                return NotificationStats(
                    total_sent=total_sent or 0,
                    total_delivered=total_delivered or 0,
                    total_failed=total_failed or 0,
                    total_read=total_read or 0,
                    total_unread=total_unread or 0,
                    pending_delivery=pending_delivery or 0
                )
                
        except Exception as e:
            logger.error(f"NotificationManager: Error getting statistics: {e}")
            return NotificationStats()
    
    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """
        Clean up old notifications.
        
        Args:
            days: Number of days to keep notifications.
            
        Returns:
            Number of notifications deleted.
        """
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                
                from sqlalchemy import delete, and_
                from database.models import Notification
                
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Delete read notifications older than cutoff
                stmt = delete(Notification).where(
                    and_(
                        Notification.is_read == True,
                        Notification.created_at < cutoff_date
                    )
                )
                
                result = await session.execute(stmt)
                count = result.rowcount
                await session.commit()
                
                logger.info(f"NotificationManager: Cleaned up {count} old notifications")
                return count
                
        except Exception as e:
            logger.error(f"NotificationManager: Error cleaning up old notifications: {e}")
            return 0
    
    # ===========================================
    # Convenience Methods for Common Notifications
    # ===========================================
    
    async def notify_account_connected(self, user_id: int, account_name: str, phone: str) -> bool:
        """Notify user that an account was connected."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT_CONNECTED,
            title="Account Connected",
            message=f"Account '{account_name}' ({phone}) has been successfully connected.",
            action_buttons=[
                {"text": "View Accounts", "callback": "view_accounts"}
            ]
        )
    
    async def notify_account_disconnected(self, user_id: int, account_name: str) -> bool:
        """Notify user that an account was disconnected."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT_DISCONNECTED,
            title="Account Disconnected",
            message=f"Account '{account_name}' has been disconnected.",
            action_buttons=[
                {"text": "Reconnect", "callback": "reconnect_account"},
                {"text": "View Accounts", "callback": "view_accounts"}
            ]
        )
    
    async def notify_account_error(self, user_id: int, account_name: str, error: str) -> bool:
        """Notify user of an account error."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT_ERROR,
            title="Account Error",
            message=f"Account '{account_name}' encountered an error: {error}",
            priority=NotificationPriority.HIGH,
            action_buttons=[
                {"text": "View Details", "callback": "view_account_error"},
                {"text": "Reconnect", "callback": "reconnect_account"}
            ]
        )
    
    async def notify_publish_started(self, user_id: int, task_id: int, account_name: str, group_count: int) -> bool:
        """Notify user that publishing has started."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.PUBLISH_STARTED,
            title="Publishing Started",
            message=f"Publishing has started for account '{account_name}' to {group_count} groups.",
            related_id=task_id,
            related_type="publishing_task",
            action_buttons=[
                {"text": "View Progress", "callback": f"view_task_{task_id}"},
                {"text": "Pause", "callback": f"pause_task_{task_id}"}
            ]
        )
    
    async def notify_publish_completed(
        self,
        user_id: int,
        task_id: int,
        account_name: str,
        success_count: int,
        failed_count: int
    ) -> bool:
        """Notify user that publishing has completed."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.PUBLISH_COMPLETED,
            title="Publishing Completed",
            message=f"Publishing completed for account '{account_name}'. Success: {success_count}, Failed: {failed_count}",
            related_id=task_id,
            related_type="publishing_task",
            action_buttons=[
                {"text": "View Report", "callback": f"view_report_{task_id}"},
                {"text": "Start Again", "callback": "start_publishing"}
            ]
        )
    
    async def notify_publish_failed(
        self,
        user_id: int,
        task_id: int,
        account_name: str,
        error: str
    ) -> bool:
        """Notify user that publishing has failed."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.PUBLISH_FAILED,
            title="Publishing Failed",
            message=f"Publishing failed for account '{account_name}': {error}",
            related_id=task_id,
            related_type="publishing_task",
            priority=NotificationPriority.HIGH,
            action_buttons=[
                {"text": "Retry", "callback": f"retry_task_{task_id}"},
                {"text": "View Details", "callback": f"view_task_{task_id}"}
            ]
        )
    
    async def notify_subscription_expiring(self, user_id: int, days_remaining: int) -> bool:
        """Notify user that their subscription is expiring."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
            title="Subscription Expiring",
            message=f"Your subscription will expire in {days_remaining} days. Please renew to avoid service interruption.",
            priority=NotificationPriority.HIGH,
            action_buttons=[
                {"text": "Renew Subscription", "callback": "renew_subscription"},
                {"text": "View Plans", "callback": "view_plans"}
            ]
        )
    
    async def notify_subscription_expired(self, user_id: int) -> bool:
        """Notify user that their subscription has expired."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_EXPIRED,
            title="Subscription Expired",
            message="Your subscription has expired. Please renew to continue using the service.",
            priority=NotificationPriority.URGENT,
            action_buttons=[
                {"text": "Renew Now", "callback": "renew_subscription"},
                {"text": "View Plans", "callback": "view_plans"}
            ]
        )
    
    async def notify_subscription_activated(self, user_id: int, subscription_type: str) -> bool:
        """Notify user that their subscription has been activated."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SUBSCRIPTION_ACTIVATED,
            title="Subscription Activated",
            message=f"Your {subscription_type} subscription has been activated. Thank you!",
            action_buttons=[
                {"text": "View Subscription", "callback": "view_subscription"},
                {"text": "Start Publishing", "callback": "start_publishing"}
            ]
        )
    
    async def notify_channel_required(self, user_id: int, channel_name: str, channel_url: str) -> bool:
        """Notify user that they need to join a required channel."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.CHANNEL_REQUIRED,
            title="Channel Required",
            message=f"Please join the required channel '{channel_name}' to access all features.",
            priority=NotificationPriority.HIGH,
            action_buttons=[
                {"text": "Join Channel", "url": channel_url},
                {"text": "Verify", "callback": "verify_subscription"}
            ]
        )
    
    async def notify_channel_verified(self, user_id: int, channel_name: str) -> bool:
        """Notify user that their channel subscription has been verified."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.CHANNEL_VERIFIED,
            title="Channel Verified",
            message=f"Your subscription to '{channel_name}' has been verified. Thank you!",
            action_buttons=[
                {"text": "Continue", "callback": "main_menu"}
            ]
        )
    
    async def notify_rate_limit(self, user_id: int, wait_time: int) -> bool:
        """Notify user that they are rate limited."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.RATE_LIMIT,
            title="Rate Limit Reached",
            message=f"You have reached the rate limit. Please wait {wait_time} seconds before trying again.",
            priority=NotificationPriority.HIGH
        )
    
    async def notify_flood_wait(self, user_id: int, wait_time: int) -> bool:
        """Notify user about FloodWait."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.FLOOD_WAIT,
            title="Flood Wait",
            message=f"Telegram has requested a wait time of {wait_time} seconds. Please wait before continuing.",
            priority=NotificationPriority.URGENT
        )
