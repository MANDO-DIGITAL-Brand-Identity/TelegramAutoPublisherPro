"""
Database repositories for Telegram Auto Publisher Pro
Provides data access layer for all database operations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypeVar, Generic, Optional, List, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy import select, update, delete, and_, or_, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .models import (
    Base,
    User,
    Administrator,
    TelegramAccount,
    SessionMetadata,
    AccountSettings,
    Content,
    MediaFile,
    Group,
    GroupPermission,
    PublishingTask,
    PublishingLog,
    PrivateSubscription,
    Subscription,
    RequiredChannel,
    Notification,
    Broadcast,
    BroadcastLog,
    AuditLog,
    ApplicationSettings,
    UserStatus,
    AdminRole,
    ContentType,
    MediaType,
    GroupType,
    TaskStatus,
    LogType,
    SubscriptionType,
    SubscriptionStatus,
    PermissionStatus,
    ChannelVerificationStatus,
)

T = TypeVar('T', bound=Base)


class BaseRepository(ABC, Generic[T]):
    """Base repository class with common CRUD operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.model_class: type = None
    
    @property
    @abstractmethod
    def model_class(self) -> type:
        pass
    
    async def get_by_id(self, id: int) -> Optional[T]:
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model_class).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(stmt)
        return result.scalar()
    
    async def create(self, data: Dict[str, Any]) -> T:
        entity = self.model_class(**data)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        stmt = update(self.model_class).where(self.model_class.id == id).values(**data)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        stmt = delete(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def exists(self, id: int) -> bool:
        stmt = select(self.model_class.id).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class UserRepository(BaseRepository[User]):
    @property
    def model_class(self) -> type:
        return User
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_with_subscription(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id).options(joinedload(User.subscription))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_users(self, limit: int = 100) -> List[User]:
        stmt = select(User).where(User.status == UserStatus.ACTIVE.value).order_by(desc(User.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def search_users(self, query: str, limit: int = 10) -> List[User]:
        stmt = select(User).where(or_(User.username.ilike(f"%{query}%"), User.first_name.ilike(f"%{query}%"), User.last_name.ilike(f"%{query}%"))).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AdministratorRepository(BaseRepository[Administrator]):
    @property
    def model_class(self) -> type:
        return Administrator
    
    async def get_administrator(self, user_id: int) -> Optional[Administrator]:
        stmt = select(Administrator).where(Administrator.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def is_admin(self, user_id: int) -> bool:
        stmt = select(Administrator.id).where(and_(Administrator.user_id == user_id, Administrator.is_active == True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def is_super_admin(self, user_id: int) -> bool:
        stmt = select(Administrator.id).where(and_(Administrator.user_id == user_id, Administrator.role == AdminRole.SUPER_ADMIN.value, Administrator.is_active == True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class TelegramAccountRepository(BaseRepository[TelegramAccount]):
    @property
    def model_class(self) -> type:
        return TelegramAccount
    
    async def get_accounts_by_user(self, user_id: int) -> List[TelegramAccount]:
        stmt = select(TelegramAccount).where(TelegramAccount.user_id == user_id).order_by(desc(TelegramAccount.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_connected_accounts_by_user(self, user_id: int) -> List[TelegramAccount]:
        stmt = select(TelegramAccount).where(and_(TelegramAccount.user_id == user_id, TelegramAccount.is_connected == True)).order_by(desc(TelegramAccount.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SessionRepository(BaseRepository[SessionMetadata]):
    @property
    def model_class(self) -> type:
        return SessionMetadata
    
    async def get_session_by_account(self, account_id: int) -> Optional[SessionMetadata]:
        stmt = select(SessionMetadata).where(SessionMetadata.account_id == account_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AccountSettingsRepository(BaseRepository[AccountSettings]):
    @property
    def model_class(self) -> type:
        return AccountSettings
    
    async def get_settings_by_account(self, account_id: int) -> Optional[AccountSettings]:
        stmt = select(AccountSettings).where(AccountSettings.account_id == account_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ContentRepository(BaseRepository[Content]):
    @property
    def model_class(self) -> type:
        return Content
    
    async def get_contents_by_user(self, user_id: int, limit: int = 100) -> List[Content]:
        stmt = select(Content).where(Content.user_id == user_id).order_by(desc(Content.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_active_contents_by_user(self, user_id: int, limit: int = 100) -> List[Content]:
        stmt = select(Content).where(and_(Content.user_id == user_id, Content.is_active == True)).order_by(desc(Content.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_random_content(self, user_id: int, exclude_id: int = None) -> Optional[Content]:
        if exclude_id:
            stmt = select(Content).where(and_(Content.user_id == user_id, Content.is_active == True, Content.id != exclude_id)).order_by(func.random()).limit(1)
        else:
            stmt = select(Content).where(and_(Content.user_id == user_id, Content.is_active == True)).order_by(func.random()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class MediaFileRepository(BaseRepository[MediaFile]):
    @property
    def model_class(self) -> type:
        return MediaFile
    
    async def get_media_files_by_user(self, user_id: int, limit: int = 100) -> List[MediaFile]:
        stmt = select(MediaFile).where(MediaFile.user_id == user_id).order_by(desc(MediaFile.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class GroupRepository(BaseRepository[Group]):
    @property
    def model_class(self) -> type:
        return Group
    
    async def get_groups_by_account(self, account_id: int) -> List[Group]:
        stmt = select(Group).where(Group.account_id == account_id).order_by(desc(Group.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_active_groups_by_account(self, account_id: int) -> List[Group]:
        stmt = select(Group).where(and_(Group.account_id == account_id, Group.is_active == True)).order_by(desc(Group.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()


class GroupPermissionRepository(BaseRepository[GroupPermission]):
    @property
    def model_class(self) -> type:
        return GroupPermission
    
    async def get_permission(self, group_id: int) -> Optional[GroupPermission]:
        stmt = select(GroupPermission).where(GroupPermission.group_id == group_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def can_post(self, group_id: int) -> bool:
        stmt = select(GroupPermission.can_post_messages).where(and_(GroupPermission.group_id == group_id, GroupPermission.permission_status == PermissionStatus.ALLOWED.value))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() or False


class PublishingTaskRepository(BaseRepository[PublishingTask]):
    @property
    def model_class(self) -> type:
        return PublishingTask
    
    async def get_tasks_by_user(self, user_id: int, limit: int = 100) -> List[PublishingTask]:
        stmt = select(PublishingTask).where(PublishingTask.user_id == user_id).order_by(desc(PublishingTask.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_ready_tasks(self) -> List[PublishingTask]:
        stmt = select(PublishingTask).where(and_(PublishingTask.status == TaskStatus.PENDING.value, PublishingTask.scheduled_at <= datetime.utcnow())).order_by(asc(PublishingTask.priority), asc(PublishingTask.scheduled_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_task_status(self, id: int, status: TaskStatus, error_message: str = None) -> bool:
        values = {"status": status.value, "updated_at": datetime.utcnow()}
        if error_message:
            values["error_message"] = error_message
        stmt = update(PublishingTask).where(PublishingTask.id == id).values(**values)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class PublishingLogRepository(BaseRepository[PublishingLog]):
    @property
    def model_class(self) -> type:
        return PublishingLog
    
    async def get_logs_by_account(self, account_id: int, limit: int = 100) -> List[PublishingLog]:
        stmt = select(PublishingLog).where(PublishingLog.account_id == account_id).order_by(desc(PublishingLog.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_recent_logs(self, account_id: int, limit: int = 10) -> List[PublishingLog]:
        stmt = select(PublishingLog).where(PublishingLog.account_id == account_id).order_by(desc(PublishingLog.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PrivateSubscriptionRepository(BaseRepository[PrivateSubscription]):
    @property
    def model_class(self) -> type:
        return PrivateSubscription
    
    async def get_subscriptions_by_user(self, user_id: int) -> List[PrivateSubscription]:
        stmt = select(PrivateSubscription).where(PrivateSubscription.user_id == user_id).order_by(desc(PrivateSubscription.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def is_subscribed(self, user_id: int, subscriber_id: int) -> bool:
        stmt = select(PrivateSubscription.id).where(and_(PrivateSubscription.user_id == user_id, PrivateSubscription.subscriber_id == subscriber_id, PrivateSubscription.is_active == True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class SubscriptionRepository(BaseRepository[Subscription]):
    @property
    def model_class(self) -> type:
        return Subscription
    
    async def get_subscription_by_user(self, user_id: int) -> Optional[Subscription]:
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def is_premium(self, user_id: int) -> bool:
        stmt = select(Subscription.subscription_type).where(and_(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE.value, Subscription.end_date > datetime.utcnow()))
        result = await self.session.execute(stmt)
        sub_type = result.scalar_one_or_none()
        return sub_type != SubscriptionType.FREE.value if sub_type else False
    
    async def get_subscription_type(self, user_id: int) -> Optional[SubscriptionType]:
        stmt = select(Subscription.subscription_type).where(and_(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE.value, Subscription.end_date > datetime.utcnow()))
        result = await self.session.execute(stmt)
        sub_type = result.scalar_one_or_none()
        return SubscriptionType(sub_type) if sub_type else None


class RequiredChannelRepository(BaseRepository[RequiredChannel]):
    @property
    def model_class(self) -> type:
        return RequiredChannel
    
    async def get_required_channels(self) -> List[RequiredChannel]:
        stmt = select(RequiredChannel).where(RequiredChannel.is_required == True).order_by(asc(RequiredChannel.priority))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def is_required(self, channel_id: int) -> bool:
        stmt = select(RequiredChannel.id).where(and_(RequiredChannel.channel_id == channel_id, RequiredChannel.is_required == True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class NotificationRepository(BaseRepository[Notification]):
    @property
    def model_class(self) -> type:
        return Notification
    
    async def get_notifications_by_user(self, user_id: int, limit: int = 100) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(desc(Notification.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_unread_notifications(self, user_id: int, limit: int = 50) -> List[Notification]:
        stmt = select(Notification).where(and_(Notification.user_id == user_id, Notification.is_read == False)).order_by(desc(Notification.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def mark_read(self, id: int) -> bool:
        stmt = update(Notification).where(Notification.id == id).values(is_read=True, read_at=datetime.utcnow(), updated_at=datetime.utcnow())
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def count_unread(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(Notification).where(and_(Notification.user_id == user_id, Notification.is_read == False))
        result = await self.session.execute(stmt)
        return result.scalar()


class BroadcastRepository(BaseRepository[Broadcast]):
    @property
    def model_class(self) -> type:
        return Broadcast
    
    async def get_broadcasts_by_admin(self, admin_id: int, limit: int = 100) -> List[Broadcast]:
        stmt = select(Broadcast).where(Broadcast.administrator_id == admin_id).order_by(desc(Broadcast.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class BroadcastLogRepository(BaseRepository[BroadcastLog]):
    @property
    def model_class(self) -> type:
        return BroadcastLog
    
    async def get_logs_by_broadcast(self, broadcast_id: int, limit: int = 100) -> List[BroadcastLog]:
        stmt = select(BroadcastLog).where(BroadcastLog.broadcast_id == broadcast_id).order_by(desc(BroadcastLog.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AuditLogRepository(BaseRepository[AuditLog]):
    @property
    def model_class(self) -> type:
        return AuditLog
    
    async def get_recent_logs(self, limit: int = 50) -> List[AuditLog]:
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def log_action(self, administrator_id: int, action: str, action_type: str, target_id: int = None, target_type: str = None, target_name: str = None, details: Dict = None, success: bool = True, error_message: str = None) -> AuditLog:
        log = AuditLog(
            administrator_id=administrator_id,
            action=action,
            action_type=action_type,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            details=details or {},
            old_values={},
            new_values={},
            success=success,
            error_message=error_message,
            created_at=datetime.utcnow()
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log


class ApplicationSettingsRepository(BaseRepository[ApplicationSettings]):
    @property
    def model_class(self) -> type:
        return ApplicationSettings
    
    async def get_settings(self) -> Optional[ApplicationSettings]:
        stmt = select(ApplicationSettings).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def set_settings(self, data: Dict[str, Any]) -> ApplicationSettings:
        settings = await self.get_settings()
        if settings:
            for key, value in data.items():
                setattr(settings, key, value)
            settings.updated_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(settings)
            return settings
        else:
            data["created_at"] = datetime.utcnow()
            data["updated_at"] = datetime.utcnow()
            settings = ApplicationSettings(**data)
            self.session.add(settings)
            await self.session.flush()
            await self.session.refresh(settings)
            return settings


__all__ = [
    'BaseRepository',
    'UserRepository',
    'AdministratorRepository',
    'TelegramAccountRepository',
    'SessionRepository',
    'AccountSettingsRepository',
    'ContentRepository',
    'MediaFileRepository',
    'GroupRepository',
    'GroupPermissionRepository',
    'PublishingTaskRepository',
    'PublishingLogRepository',
    'PrivateSubscriptionRepository',
    'SubscriptionRepository',
    'RequiredChannelRepository',
    'NotificationRepository',
    'BroadcastRepository',
    'BroadcastLogRepository',
    'AuditLogRepository',
    'ApplicationSettingsRepository',
]
