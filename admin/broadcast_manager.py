"""
Broadcast manager for Telegram Auto Publisher Pro
Manages administrative announcements and broadcasts to users
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
    Administrator,
    Broadcast,
    BroadcastLog,
    SubscriptionType,
    SubscriptionStatus,
)
from database.repositories import (
    UserRepository,
    AdministratorRepository,
    BroadcastRepository,
    BroadcastLogRepository,
    SubscriptionRepository,
    AuditLogRepository,
)
from security.permissions import check_admin_access, check_super_admin_access
from notifications.manager import NotificationManager, NotificationType

logger = logging.getLogger(__name__)


class BroadcastType(str, Enum):
    TEXT = "text"
    MEDIA = "media"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


class BroadcastStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BroadcastDeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


@dataclass
class BroadcastInfo:
    id: Optional[int] = None
    administrator_id: int = 0
    broadcast_type: BroadcastType = BroadcastType.TEXT
    title: Optional[str] = None
    message: Optional[str] = None
    media_file_id: Optional[int] = None
    target_all: bool = True
    target_user_ids: List[int] = field(default_factory=list)
    target_subscription_types: List[str] = field(default_factory=list)
    status: BroadcastStatus = BroadcastStatus.DRAFT
    scheduled_at: Optional[datetime] = None
    timezone: str = "UTC"
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0
    read_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class BroadcastStats:
    total_broadcasts: int = 0
    draft_broadcasts: int = 0
    scheduled_broadcasts: int = 0
    sent_broadcasts: int = 0
    cancelled_broadcasts: int = 0
    total_recipients: int = 0
    total_sent: int = 0
    total_failed: int = 0
    total_read: int = 0
    success_rate: float = 0.0


@dataclass
class BroadcastRecipient:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    subscription_type: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: bool = False
    status: BroadcastDeliveryStatus = BroadcastDeliveryStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BroadcastManager:
    def __init__(
        self,
        session_factory: Callable = None,
        broadcast_repository: BroadcastRepository = None,
        broadcast_log_repository: BroadcastLogRepository = None,
        user_repository: UserRepository = None,
        administrator_repository: AdministratorRepository = None,
        subscription_repository: SubscriptionRepository = None,
        audit_log_repository: AuditLogRepository = None,
        notification_manager: NotificationManager = None,
        config: any = None
    ):
        self.session_factory = session_factory
        self.config = config or config
        if broadcast_repository:
            self.broadcast_repository = broadcast_repository
        else:
            self.broadcast_repository = BroadcastRepository(session_factory)
        if broadcast_log_repository:
            self.broadcast_log_repository = broadcast_log_repository
        else:
            self.broadcast_log_repository = BroadcastLogRepository(session_factory)
        if user_repository:
            self.user_repository = user_repository
        else:
            self.user_repository = UserRepository(session_factory)
        if administrator_repository:
            self.administrator_repository = administrator_repository
        else:
            self.administrator_repository = AdministratorRepository(session_factory)
        if subscription_repository:
            self.subscription_repository = subscription_repository
        else:
            self.subscription_repository = SubscriptionRepository(session_factory)
        if audit_log_repository:
            self.audit_log_repository = audit_log_repository
        else:
            self.audit_log_repository = AuditLogRepository(session_factory)
        self.notification_manager = notification_manager
        self._bot = None
        self._broadcast_rate_limit: Dict[int, datetime] = {}
        self._rate_limit_interval = timedelta(seconds=0.1)
        logger.info("BroadcastManager initialized")

    async def initialize(self) -> None:
        logger.info("BroadcastManager: Initializing...")
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                pending = await self.broadcast_repository.get_all(
                    filters={"status": BroadcastStatus.SCHEDULED.value}
                )
                logger.info(f"BroadcastManager: Found {len(pending)} scheduled broadcasts")
        except Exception as e:
            logger.error(f"BroadcastManager: Error initializing: {e}")
            raise
        logger.info("BroadcastManager: Initialized successfully")

    async def set_bot(self, bot: Any) -> None:
        self._bot = bot
        logger.info("BroadcastManager: Bot instance set")

    async def create_broadcast(
        self,
        administrator_id: int,
        broadcast_type: BroadcastType = BroadcastType.TEXT,
        title: Optional[str] = None,
        message: Optional[str] = None,
        media_file_id: Optional[int] = None,
        target_all: bool = True,
        target_user_ids: Optional[List[int]] = None,
        target_subscription_types: Optional[List[str]] = None,
        scheduled_at: Optional[datetime] = None,
        timezone: str = "UTC"
    ) -> Tuple[bool, Optional[BroadcastInfo]]:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                admin = await self.administrator_repository.get(administrator_id)
                if not admin:
                    logger.warning(f"BroadcastManager: Administrator {administrator_id} not found")
                    return False, None
                status = BroadcastStatus.DRAFT
                if scheduled_at:
                    status = BroadcastStatus.SCHEDULED
                broadcast = Broadcast(
                    administrator_id=administrator_id,
                    broadcast_type=broadcast_type.value,
                    title=title,
                    message=message,
                    media_file_id=media_file_id,
                    target_all=target_all,
                    target_user_ids=target_user_ids or [],
                    target_subscription_types=target_subscription_types or [],
                    status=status.value,
                    scheduled_at=scheduled_at,
                    timezone=timezone,
                    total_recipients=0,
                    sent_count=0,
                    failed_count=0,
                    read_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(broadcast)
                await session.flush()
                await session.refresh(broadcast)
                await session.commit()
                await self.audit_log_repository.log_action(
                    administrator_id=administrator_id,
                    action="Create broadcast",
                    action_type="broadcast_management",
                    target_id=broadcast.id,
                    target_type="broadcast",
                    target_name=title or f"Broadcast {broadcast.id}",
                    details={"broadcast_type": broadcast_type.value, "target_all": target_all},
                    success=True
                )
                broadcast_info = BroadcastInfo(
                    id=broadcast.id,
                    administrator_id=broadcast.administrator_id,
                    broadcast_type=BroadcastType(broadcast.broadcast_type),
                    title=broadcast.title,
                    message=broadcast.message,
                    media_file_id=broadcast.media_file_id,
                    target_all=broadcast.target_all,
                    target_user_ids=broadcast.target_user_ids or [],
                    target_subscription_types=broadcast.target_subscription_types or [],
                    status=BroadcastStatus(broadcast.status),
                    scheduled_at=broadcast.scheduled_at,
                    timezone=broadcast.timezone,
                    total_recipients=broadcast.total_recipients,
                    sent_count=broadcast.sent_count,
                    failed_count=broadcast.failed_count,
                    read_count=broadcast.read_count,
                    created_at=broadcast.created_at,
                    updated_at=broadcast.updated_at,
                    sent_at=broadcast.sent_at,
                    completed_at=broadcast.completed_at
                )
                logger.info(f"BroadcastManager: Created broadcast {broadcast.id}")
                return True, broadcast_info
        except Exception as e:
            logger.error(f"BroadcastManager: Error creating broadcast: {e}")
            return False, None

    async def get_broadcast(self, broadcast_id: int) -> Optional[BroadcastInfo]:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                broadcast = await self.broadcast_repository.get(broadcast_id)
                if not broadcast:
                    return None
                return BroadcastInfo(
                    id=broadcast.id,
                    administrator_id=broadcast.administrator_id,
                    broadcast_type=BroadcastType(broadcast.broadcast_type),
                    title=broadcast.title,
                    message=broadcast.message,
                    media_file_id=broadcast.media_file_id,
                    target_all=broadcast.target_all,
                    target_user_ids=broadcast.target_user_ids or [],
                    target_subscription_types=broadcast.target_subscription_types or [],
                    status=BroadcastStatus(broadcast.status),
                    scheduled_at=broadcast.scheduled_at,
                    timezone=broadcast.timezone,
                    total_recipients=broadcast.total_recipients,
                    sent_count=broadcast.sent_count,
                    failed_count=broadcast.failed_count,
                    read_count=broadcast.read_count,
                    created_at=broadcast.created_at,
                    updated_at=broadcast.updated_at,
                    sent_at=broadcast.sent_at,
                    completed_at=broadcast.completed_at
                )
        except Exception as e:
            logger.error(f"BroadcastManager: Error getting broadcast {broadcast_id}: {e}")
            return None

    async def get_broadcasts(
        self,
        administrator_id: Optional[int] = None,
        status: Optional[BroadcastStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BroadcastInfo]:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                filters = {}
                if administrator_id:
                    filters["administrator_id"] = administrator_id
                if status:
                    filters["status"] = status.value
                broadcasts = await self.broadcast_repository.get_all(
                    filters=filters, limit=limit, offset=offset,
                    order_by="created_at", descending=True
                )
                return [
                    BroadcastInfo(
                        id=b.id, administrator_id=b.administrator_id,
                        broadcast_type=BroadcastType(b.broadcast_type),
                        title=b.title, message=b.message,
                        media_file_id=b.media_file_id,
                        target_all=b.target_all,
                        target_user_ids=b.target_user_ids or [],
                        target_subscription_types=b.target_subscription_types or [],
                        status=BroadcastStatus(b.status),
                        scheduled_at=b.scheduled_at, timezone=b.timezone,
                        total_recipients=b.total_recipients,
                        sent_count=b.sent_count, failed_count=b.failed_count,
                        read_count=b.read_count,
                        created_at=b.created_at, updated_at=b.updated_at,
                        sent_at=b.sent_at, completed_at=b.completed_at
                    )
                    for b in broadcasts
                ]
        except Exception as e:
            logger.error(f"BroadcastManager: Error getting broadcasts: {e}")
            return []

    async def update_broadcast(
        self,
        broadcast_id: int,
        administrator_id: int,
        title: Optional[str] = None,
        message: Optional[str] = None,
        broadcast_type: Optional[BroadcastType] = None,
        media_file_id: Optional[int] = None,
        target_all: Optional[bool] = None,
        target_user_ids: Optional[List[int]] = None,
        target_subscription_types: Optional[List[str]] = None,
        scheduled_at: Optional[datetime] = None,
        timezone: Optional[str] = None
    ) -> Tuple[bool, Optional[BroadcastInfo]]:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                broadcast = await self.broadcast_repository.get(broadcast_id)
                if not broadcast:
                    return False, None
                if broadcast.administrator_id != administrator_id:
                    return False, None
                changes = {}
                if title is not None:
                    broadcast.title = title
                    changes["title"] = title
                if message is not None:
                    broadcast.message = message
                    changes["message"] = message
                if broadcast_type is not None:
                    broadcast.broadcast_type = broadcast_type.value
                    changes["broadcast_type"] = broadcast_type.value
                if media_file_id is not None:
                    broadcast.media_file_id = media_file_id
                    changes["media_file_id"] = media_file_id
                if target_all is not None:
                    broadcast.target_all = target_all
                    changes["target_all"] = target_all
                if target_user_ids is not None:
                    broadcast.target_user_ids = target_user_ids
                    changes["target_user_ids"] = target_user_ids
                if target_subscription_types is not None:
                    broadcast.target_subscription_types = target_subscription_types
                    changes["target_subscription_types"] = target_subscription_types
                if scheduled_at is not None:
                    broadcast.scheduled_at = scheduled_at
                    changes["scheduled_at"] = str(scheduled_at)
                if timezone is not None:
                    broadcast.timezone = timezone
                    changes["timezone"] = timezone
                broadcast.updated_at = datetime.utcnow()
                await session.commit()
                await self.audit_log_repository.log_action(
                    administrator_id=administrator_id,
                    action="Update broadcast",
                    action_type="broadcast_management",
                    target_id=broadcast.id,
                    target_type="broadcast",
                    target_name=broadcast.title or f"Broadcast {broadcast.id}",
                    details={"changes": changes},
                    success=True
                )
                return True, BroadcastInfo(
                    id=broadcast.id, administrator_id=broadcast.administrator_id,
                    broadcast_type=BroadcastType(broadcast.broadcast_type),
                    title=broadcast.title, message=broadcast.message,
                    media_file_id=broadcast.media_file_id,
                    target_all=broadcast.target_all,
                    target_user_ids=broadcast.target_user_ids or [],
                    target_subscription_types=broadcast.target_subscription_types or [],
                    status=BroadcastStatus(broadcast.status),
                    scheduled_at=broadcast.scheduled_at, timezone=broadcast.timezone,
                    total_recipients=broadcast.total_recipients,
                    sent_count=broadcast.sent_count, failed_count=broadcast.failed_count,
                    read_count=broadcast.read_count,
                    created_at=broadcast.created_at, updated_at=broadcast.updated_at,
                    sent_at=broadcast.sent_at, completed_at=broadcast.completed_at
                )
        except Exception as e:
            logger.error(f"BroadcastManager: Error updating broadcast {broadcast_id}: {e}")
            return False, None

    async def delete_broadcast(self, broadcast_id: int, administrator_id: int) -> bool:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                broadcast = await self.broadcast_repository.get(broadcast_id)
                if not broadcast:
                    return False
                is_super_admin = await check_super_admin_access(administrator_id, self.session_factory)
                if broadcast.administrator_id != administrator_id and not is_super_admin:
                    return False
                broadcast_name = broadcast.title or f"Broadcast {broadcast.id}"
                await self.broadcast_repository.delete(broadcast_id)
                await session.commit()
                await self.audit_log_repository.log_action(
                    administrator_id=administrator_id,
                    action="Delete broadcast",
                    action_type="broadcast_management",
                    target_id=broadcast.id,
                    target_type="broadcast",
                    target_name=broadcast_name,
                    success=True
                )
                logger.info(f"BroadcastManager: Deleted broadcast {broadcast_id}")
                return True
        except Exception as e:
            logger.error(f"BroadcastManager: Error deleting broadcast {broadcast_id}: {e}")
            return False

    async def schedule_broadcast(
        self, broadcast_id: int, administrator_id: int, scheduled_at: datetime
    ) -> bool:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                broadcast = await self.broadcast_repository.get(broadcast_id)
                if not broadcast:
                    return False
                if broadcast.administrator_id != administrator_id:
                    return False
                broadcast.scheduled_at = scheduled_at
                broadcast.status = BroadcastStatus.SCHEDULED.value
                broadcast.updated_at = datetime.utcnow()
                await session.commit()
                await self.audit_log_repository.log_action(
                    administrator_id=administrator_id,
                    action="Schedule broadcast",
                    action_type="broadcast_management",
                    target_id=broadcast.id,
                    target_type="broadcast",
                    target_name=broadcast.title or f"Broadcast {broadcast.id}",
                    details={"scheduled_at": str(scheduled_at)},
                    success=True
                )
                logger.info(f"BroadcastManager: Scheduled broadcast {broadcast_id}")
                return True
        except Exception as e:
            logger.error(f"BroadcastManager: Error scheduling broadcast {broadcast_id}: {e}")
            return False

    async def cancel_broadcast(self, broadcast_id: int, administrator_id: int) -> bool:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                broadcast = await self.broadcast_repository.get(broadcast_id)
                if not broadcast:
                    return False
                if broadcast.administrator_id != administrator_id:
                    return False
                if broadcast.status not in [BroadcastStatus.SCHEDULED.value, BroadcastStatus.DRAFT.value]:
                    return False
                broadcast.status = BroadcastStatus.CANCELLED.value
                broadcast.updated_at = datetime.utcnow()
                await session.commit()
                await self.audit_log_repository.log_action(
                    administrator_id=administrator_id,
                    action="Cancel broadcast",
                    action_type="broadcast_management",
                    target_id=broadcast.id,
                    target_type="broadcast",
                    target_name=broadcast.title or f"Broadcast {broadcast.id}",
                    success=True
                )
                logger.info(f"BroadcastManager: Cancelled broadcast {broadcast_id}")
                return True
        except Exception as e:
            logger.error(f"BroadcastManager: Error cancelling broadcast {broadcast_id}: {e}")
            return False

    async def send_broadcast(self, broadcast_id: int, administrator_id: Optional[int] = None) -> Tuple[bool, Dict[str, int]]:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                broadcast = await self.broadcast_repository.get(broadcast_id)
                if not broadcast:
                    return False, {}
                if broadcast.status == BroadcastStatus.SENT.value:
                    return False, {}
                user_ids = await self._get_broadcast_recipients(broadcast)
                broadcast.total_recipients = len(user_ids)
                if not user_ids:
                    broadcast.status = BroadcastStatus.FAILED.value
                    broadcast.failed_count = 1
                    broadcast.updated_at = datetime.utcnow()
                    await session.commit()
                    return False, {"total": 0, "sent": 0, "failed": 1}
                broadcast.status = BroadcastStatus.SENDING.value
                broadcast.sent_at = datetime.utcnow()
                broadcast.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"BroadcastManager: Sending broadcast {broadcast_id} to {len(user_ids)} recipients")
                sent_count = 0
                failed_count = 0
                for user_id in user_ids:
                    try:
                        last_sent = self._broadcast_rate_limit.get(user_id)
                        if last_sent and (datetime.utcnow() - last_sent) < self._rate_limit_interval:
                            await asyncio.sleep(0.1)
                        success = await self._send_broadcast_to_user(broadcast, user_id)
                        if success:
                            sent_count += 1
                            self._broadcast_rate_limit[user_id] = datetime.utcnow()
                            log = BroadcastLog(
                                broadcast_id=broadcast.id, user_id=user_id,
                                status=BroadcastDeliveryStatus.SENT.value,
                                created_at=datetime.utcnow()
                            )
                            session.add(log)
                            await session.flush()
                        else:
                            failed_count += 1
                            log = BroadcastLog(
                                broadcast_id=broadcast.id, user_id=user_id,
                                status=BroadcastDeliveryStatus.FAILED.value,
                                error_message="Failed to send",
                                created_at=datetime.utcnow()
                            )
                            session.add(log)
                            await session.flush()
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"BroadcastManager: Error sending to user {user_id}: {e}")
                        log = BroadcastLog(
                            broadcast_id=broadcast.id, user_id=user_id,
                            status=BroadcastDeliveryStatus.FAILED.value,
                            error_message=str(e),
                            created_at=datetime.utcnow()
                        )
                        session.add(log)
                        await session.flush()
                broadcast.sent_count = sent_count
                broadcast.failed_count = failed_count
                broadcast.status = BroadcastStatus.SENT.value
                broadcast.completed_at = datetime.utcnow()
                broadcast.updated_at = datetime.utcnow()
                await session.commit()
                if administrator_id:
                    await self.audit_log_repository.log_action(
                        administrator_id=administrator_id,
                        action="Send broadcast",
                        action_type="broadcast_management",
                        target_id=broadcast.id,
                        target_type="broadcast",
                        target_name=broadcast.title or f"Broadcast {broadcast.id}",
                        details={"total": broadcast.total_recipients, "sent": sent_count, "failed": failed_count},
                        success=True
                    )
                logger.info(f"BroadcastManager: Sent broadcast {broadcast_id} - {sent_count} sent, {failed_count} failed")
                return True, {"total": broadcast.total_recipients, "sent": sent_count, "failed": failed_count}
        except Exception as e:
            logger.error(f"BroadcastManager: Error sending broadcast {broadcast_id}: {e}")
            return False, {"error": str(e)}

    async def _get_broadcast_recipients(self, broadcast: Broadcast) -> List[int]:
        try:
            async with self.session_factory() as session:
                self.user_repository.session = session
                self.subscription_repository.session = session
                users = await self.user_repository.get_all(filters={"status": "active"})
                user_ids = [u.telegram_id for u in users]
                if not broadcast.target_all:
                    if broadcast.target_user_ids:
                        target_set = set(broadcast.target_user_ids)
                        user_ids = [uid for uid in user_ids if uid in target_set]
                    if broadcast.target_subscription_types:
                        target_subs = set(broadcast.target_subscription_types)
                        filtered_ids = []
                        for user in users:
                            subscription = await self.subscription_repository.get_by_field("user_id", user.telegram_id)
                            if subscription and subscription.subscription_type in target_subs:
                                filtered_ids.append(user.telegram_id)
                        user_ids = filtered_ids
                return list(set(user_ids))
        except Exception as e:
            logger.error(f"BroadcastManager: Error getting recipients: {e}")
            return []

    async def _send_broadcast_to_user(self, broadcast: Broadcast, user_id: int) -> bool:
        if not self._bot:
            logger.warning("BroadcastManager: Bot instance not set")
            return False
        try:
            message_text = broadcast.message or ""
            if broadcast.title:
                message_text = f"<b>{broadcast.title}</b>\n\n{message_text}"
            if broadcast.broadcast_type == BroadcastType.TEXT.value:
                await self._bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
                return True
            elif broadcast.broadcast_type in [BroadcastType.PHOTO.value, BroadcastType.MEDIA.value]:
                if broadcast.media_file_id:
                    await self._bot.send_photo(chat_id=user_id, photo="placeholder", caption=message_text, parse_mode="HTML")
                    return True
                else:
                    await self._bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
                    return True
            else:
                await self._bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
                return True
        except Exception as e:
            logger.error(f"BroadcastManager: Error sending to user {user_id}: {e}")
            return False

    async def get_broadcast_stats(self) -> BroadcastStats:
        try:
            async with self.session_factory() as session:
                self.broadcast_repository.session = session
                from sqlalchemy import select, func
                from database.models import Broadcast, BroadcastLog
                total_broadcasts = await session.scalar(select(func.count()).select_from(Broadcast)) or 0
                draft_count = await session.scalar(select(func.count()).select_from(Broadcast).where(Broadcast.status == BroadcastStatus.DRAFT.value)) or 0
                scheduled_count = await session.scalar(select(func.count()).select_from(Broadcast).where(Broadcast.status == BroadcastStatus.SCHEDULED.value)) or 0
                sent_count = await session.scalar(select(func.count()).select_from(Broadcast).where(Broadcast.status == BroadcastStatus.SENT.value)) or 0
                cancelled_count = await session.scalar(select(func.count()).select_from(Broadcast).where(Broadcast.status == BroadcastStatus.CANCELLED.value)) or 0
                total_recipients = await session.scalar(select(func.sum(Broadcast.total_recipients)).select_from(Broadcast)) or 0
                total_sent = await session.scalar(select(func.sum(Broadcast.sent_count)).select_from(Broadcast)) or 0
                total_failed = await session.scalar(select(func.sum(Broadcast.failed_count)).select_from(Broadcast)) or 0
                total_read = await session.scalar(select(func.count()).select_from(BroadcastLog).where(BroadcastLog.status == BroadcastDeliveryStatus.READ.value)) or 0
                success_rate = (total_sent / (total_sent + total_failed)) * 100 if (total_sent + total_failed) > 0 else 0.0
                return BroadcastStats(
                    total_broadcasts=total_broadcasts, draft_broadcasts=draft_count,
                    scheduled_broadcasts=scheduled_count, sent_broadcasts=sent_count,
                    cancelled_broadcasts=cancelled_count, total_recipients=total_recipients,
                    total_sent=total_sent, total_failed=total_failed, total_read=total_read,
                    success_rate=success_rate
                )
        except Exception as e:
            logger.error(f"BroadcastManager: Error getting stats: {e}")
            return BroadcastStats()

    async def cleanup_old_broadcasts(self, days: int = 90) -> int:
        try:
            async with self.session_factory() as session:
                self.broadcast_log_repository.session = session
                from sqlalchemy import delete
                from database.models import BroadcastLog
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                stmt = delete(BroadcastLog).where(BroadcastLog.created_at < cutoff_date)
                result = await session.execute(stmt)
                count = result.rowcount
                await session.commit()
                logger.info(f"BroadcastManager: Cleaned up {count} old broadcast logs")
                return count
        except Exception as e:
            logger.error(f"BroadcastManager: Error cleaning up: {e}")
            return 0
