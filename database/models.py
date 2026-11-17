"""
Database models for Telegram Auto Publisher Pro
Defines all SQLAlchemy models and enums for the application
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    Numeric,
    Index,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    declared_attr,
)
from sqlalchemy.dialects.postgresql import JSONB

# Create base class
Base = declarative_base()


# ===========================================
# ENUMS
# ===========================================

class UserStatus(str, Enum):
    """User status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"


class AdminRole(str, Enum):
    """Administrator role enum"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"


class ContentType(str, Enum):
    """Content type enum"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    MEDIA = "media"


class MediaType(str, Enum):
    """Media type enum"""
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"
    STICKER = "sticker"
    GIF = "gif"


class GroupType(str, Enum):
    """Group type enum"""
    CHANNEL = "channel"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    PRIVATE = "private"


class TaskStatus(str, Enum):
    """Publishing task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogType(str, Enum):
    """Log type enum"""
    PUBLISH = "publish"
    SCHEDULE = "schedule"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SubscriptionType(str, Enum):
    """Subscription type enum"""
    FREE = "free"
    PREMIUM = "premium"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"
    TRIAL = "trial"


class SubscriptionStatus(str, Enum):
    """Subscription status enum"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class PermissionStatus(str, Enum):
    """Permission status enum"""
    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING = "pending"
    UNKNOWN = "unknown"


class ChannelVerificationStatus(str, Enum):
    """Channel verification status enum"""
    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    FAILED = "failed"
    SKIPPED = "skipped"


# ===========================================
# MODELS
# ===========================================

class User(Base):
    """User model representing Telegram users"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True)
    
    # Status and permissions
    status = Column(
        String(20),
        default=UserStatus.ACTIVE.value,
        nullable=False
    )
    is_bot = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    
    # Subscription
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    telegram_accounts = relationship("TelegramAccount", back_populates="user")
    administrator = relationship("Administrator", back_populates="user", uselist=False)
    private_subscriptions = relationship("PrivateSubscription", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    publishing_tasks = relationship("PublishingTask", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_telegram_id', 'telegram_id'),
        Index('idx_user_status', 'status'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Administrator(Base):
    """Administrator model for users with admin privileges"""
    
    __tablename__ = "administrators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False, index=True)
    role = Column(
        String(20),
        default=AdminRole.ADMIN.value,
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Permissions
    can_manage_users = Column(Boolean, default=True, nullable=False)
    can_manage_accounts = Column(Boolean, default=True, nullable=False)
    can_manage_subscriptions = Column(Boolean, default=True, nullable=False)
    can_manage_channels = Column(Boolean, default=True, nullable=False)
    can_manage_broadcasts = Column(Boolean, default=True, nullable=False)
    can_manage_settings = Column(Boolean, default=False, nullable=False)
    can_view_audit_logs = Column(Boolean, default=True, nullable=False)
    can_manage_admins = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="administrator")
    audit_logs = relationship("AuditLog", back_populates="administrator")
    broadcasts = relationship("Broadcast", back_populates="administrator")
    
    # Indexes
    __table_args__ = (
        Index('idx_admin_user_id', 'user_id'),
        Index('idx_admin_role', 'role'),
        Index('idx_admin_is_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Administrator(user_id={self.user_id}, role={self.role})>"


class TelegramAccount(Base):
    """Telegram account model for connected user accounts"""
    
    __tablename__ = "telegram_accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    
    # Account information
    phone_number = Column(String(20), nullable=True)
    account_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Connection status
    is_connected = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    connection_status = Column(String(50), default="disconnected", nullable=False)
    
    # Session information
    session_id = Column(String(255), unique=True, nullable=True)
    session_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_connected_at = Column(DateTime, nullable=True)
    last_disconnected_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="telegram_accounts")
    session_metadata = relationship("SessionMetadata", back_populates="telegram_account", uselist=False)
    account_settings = relationship("AccountSettings", back_populates="telegram_account", uselist=False)
    contents = relationship("Content", back_populates="telegram_account")
    groups = relationship("Group", back_populates="telegram_account")
    publishing_tasks = relationship("PublishingTask", back_populates="telegram_account")
    publishing_logs = relationship("PublishingLog", back_populates="telegram_account")
    
    # Indexes
    __table_args__ = (
        Index('idx_telegram_account_user_id', 'user_id'),
        Index('idx_telegram_account_session_id', 'session_id'),
        Index('idx_telegram_account_is_connected', 'is_connected'),
        Index('idx_telegram_account_phone', 'phone_number'),
    )
    
    def __repr__(self):
        return f"<TelegramAccount(id={self.id}, phone={self.phone_number}, connected={self.is_connected})>"


class SessionMetadata(Base):
    """Session metadata for Telethon sessions"""
    
    __tablename__ = "session_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), unique=True, nullable=False)
    
    # Session file information
    session_file_path = Column(String(512), nullable=True)
    session_file_size = Column(Integer, nullable=True)
    session_file_hash = Column(String(255), nullable=True)
    
    # Session properties
    is_encrypted = Column(Boolean, default=False, nullable=False)
    encryption_key_id = Column(String(255), nullable=True)
    
    # Session state
    is_valid = Column(Boolean, default=True, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    telegram_account = relationship("TelegramAccount", back_populates="session_metadata")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_metadata_account_id', 'account_id'),
        Index('idx_session_metadata_is_valid', 'is_valid'),
    )
    
    def __repr__(self):
        return f"<SessionMetadata(account_id={self.account_id}, valid={self.is_valid})>"


class AccountSettings(Base):
    """Settings for individual Telegram accounts"""
    
    __tablename__ = "account_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), unique=True, nullable=False)
    
    # Publishing settings
    publishing_enabled = Column(Boolean, default=False, nullable=False)
    publishing_interval_minutes = Column(Integer, default=60, nullable=False)
    publishing_mode = Column(String(20), default="random", nullable=False)  # random, sequential, individual
    
    # Content selection
    selected_content_id = Column(Integer, ForeignKey("contents.id"), nullable=True)
    use_random_content = Column(Boolean, default=True, nullable=False)
    prevent_duplicate_content = Column(Boolean, default=True, nullable=False)
    
    # Group selection
    selected_group_ids = Column(JSON, default=[], nullable=False)  # List of group IDs
    
    # Scheduling
    schedule_enabled = Column(Boolean, default=False, nullable=False)
    schedule_cron = Column(String(100), nullable=True)
    schedule_timezone = Column(String(50), default="UTC", nullable=False)
    
    # Notifications
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    notification_on_success = Column(Boolean, default=True, nullable=False)
    notification_on_failure = Column(Boolean, default=True, nullable=False)
    
    # Statistics
    total_published = Column(Integer, default=0, nullable=False)
    successful_published = Column(Integer, default=0, nullable=False)
    failed_published = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    telegram_account = relationship("TelegramAccount", back_populates="account_settings")
    selected_content = relationship("Content", back_populates="account_settings")
    
    # Indexes
    __table_args__ = (
        Index('idx_account_settings_account_id', 'account_id'),
    )
    
    def __repr__(self):
        return f"<AccountSettings(account_id={self.account_id}, publishing_enabled={self.publishing_enabled})>"


class Content(Base):
    """Content model for saved posts and media"""
    
    __tablename__ = "contents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    
    # Content type
    content_type = Column(
        String(20),
        default=ContentType.TEXT.value,
        nullable=False
    )
    
    # Content data
    title = Column(String(500), nullable=True)
    text = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    
    # Media information
    media_type = Column(String(20), nullable=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=True)
    
    # Formatting
    parse_mode = Column(String(20), default="HTML", nullable=False)  # HTML, Markdown, MarkdownV2
    entities = Column(JSON, nullable=True)  # Telegram message entities
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    tags = Column(JSON, default=[], nullable=False)  # List of tags
    category = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    telegram_account = relationship("TelegramAccount", back_populates="contents")
    media_file = relationship("MediaFile", back_populates="contents")
    account_settings = relationship("AccountSettings", back_populates="selected_content")
    publishing_tasks = relationship("PublishingTask", back_populates="content")
    
    # Indexes
    __table_args__ = (
        Index('idx_content_user_id', 'user_id'),
        Index('idx_content_account_id', 'account_id'),
        Index('idx_content_type', 'content_type'),
        Index('idx_content_is_active', 'is_active'),
        Index('idx_content_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Content(id={self.id}, type={self.content_type}, title={self.title})>"


class MediaFile(Base):
    """Media file model for uploaded files"""
    
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    
    # File information
    file_id = Column(String(255), unique=True, nullable=True)  # Telegram file ID
    file_unique_id = Column(String(255), unique=True, nullable=True)  # Telegram file unique ID
    file_name = Column(String(500), nullable=True)
    file_path = Column(String(1024), nullable=True)
    
    # Media type
    media_type = Column(
        String(20),
        default=MediaType.DOCUMENT.value,
        nullable=False
    )
    
    # File metadata
    file_size = Column(BigInteger, nullable=True)  # Size in bytes
    mime_type = Column(String(255), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Thumbnail
    has_thumbnail = Column(Boolean, default=False, nullable=False)
    thumbnail_file_id = Column(String(255), nullable=True)
    
    # Status
    is_uploaded = Column(Boolean, default=False, nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    uploaded_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    contents = relationship("Content", back_populates="media_file")
    
    # Indexes
    __table_args__ = (
        Index('idx_media_file_user_id', 'user_id'),
        Index('idx_media_file_file_id', 'file_id'),
        Index('idx_media_file_media_type', 'media_type'),
        Index('idx_media_file_is_uploaded', 'is_uploaded'),
    )
    
    def __repr__(self):
        return f"<MediaFile(id={self.id}, type={self.media_type}, name={self.file_name})>"


class Group(Base):
    """Group model for managed groups and channels"""
    
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    
    # Group information
    telegram_id = Column(BigInteger, nullable=False, index=True)  # Group/channel ID
    title = Column(String(500), nullable=True)
    username = Column(String(255), nullable=True)
    
    # Group type
    group_type = Column(
        String(20),
        default=GroupType.GROUP.value,
        nullable=False
    )
    
    # Access information
    access_hash = Column(BigInteger, nullable=True)
    is_accessible = Column(Boolean, default=True, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    account = relationship("TelegramAccount", back_populates="groups")
    permissions = relationship("GroupPermission", back_populates="group")
    publishing_tasks = relationship("PublishingTask", back_populates="group")
    
    # Indexes
    __table_args__ = (
        Index('idx_group_account_id', 'account_id'),
        Index('idx_group_telegram_id', 'telegram_id'),
        Index('idx_group_group_type', 'group_type'),
        Index('idx_group_is_active', 'is_active'),
        Index('idx_group_is_verified', 'is_verified'),
    )
    
    def __repr__(self):
        return f"<Group(id={self.id}, title={self.title}, type={self.group_type})>"


class GroupPermission(Base):
    """Group permission model for publishing permissions"""
    
    __tablename__ = "group_permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    
    # Permission status
    can_post_messages = Column(Boolean, default=False, nullable=False)
    can_post_media = Column(Boolean, default=False, nullable=False)
    can_edit_messages = Column(Boolean, default=False, nullable=False)
    can_delete_messages = Column(Boolean, default=False, nullable=False)
    can_pin_messages = Column(Boolean, default=False, nullable=False)
    can_manage_topics = Column(Boolean, default=False, nullable=False)
    
    # Overall permission status
    permission_status = Column(
        String(20),
        default=PermissionStatus.UNKNOWN.value,
        nullable=False
    )
    
    # Verification
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    verification_error = Column(String(1000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    group = relationship("Group", back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_group_permission_group_id', 'group_id'),
        Index('idx_group_permission_status', 'permission_status'),
    )
    
    def __repr__(self):
        return f"<GroupPermission(group_id={self.group_id}, status={self.permission_status})>"


class PublishingTask(Base):
    """Publishing task model for scheduled publishing"""
    
    __tablename__ = "publishing_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True, index=True)
    
    # Task information
    task_name = Column(String(500), nullable=True)
    task_description = Column(Text, nullable=True)
    
    # Task status
    status = Column(
        String(20),
        default=TaskStatus.PENDING.value,
        nullable=False
    )
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    publish_at = Column(DateTime, nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    
    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    retry_delay_seconds = Column(Integer, default=60, nullable=False)
    
    # Priority
    priority = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Result information
    result_message_id = Column(BigInteger, nullable=True)
    result_message_link = Column(String(1024), nullable=True)
    error_message = Column(String(2000), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="publishing_tasks")
    telegram_account = relationship("TelegramAccount", back_populates="publishing_tasks")
    group = relationship("Group", back_populates="publishing_tasks")
    content = relationship("Content", back_populates="publishing_tasks")
    logs = relationship("PublishingLog", back_populates="task")
    
    # Indexes
    __table_args__ = (
        Index('idx_publishing_task_user_id', 'user_id'),
        Index('idx_publishing_task_account_id', 'account_id'),
        Index('idx_publishing_task_status', 'status'),
        Index('idx_publishing_task_scheduled_at', 'scheduled_at'),
        Index('idx_publishing_task_priority', 'priority'),
        Index('idx_publishing_task_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PublishingTask(id={self.id}, status={self.status}, scheduled_at={self.scheduled_at})>"


class PublishingLog(Base):
    """Publishing log model for tracking publishing operations"""
    
    __tablename__ = "publishing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("publishing_tasks.id"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    
    # Log type
    log_type = Column(
        String(20),
        default=LogType.PUBLISH.value,
        nullable=False
    )
    
    # Operation details
    operation = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    
    # Status
    success = Column(Boolean, nullable=True)
    error_code = Column(Integer, nullable=True)
    error_message = Column(String(2000), nullable=True)
    
    # Target information
    target_type = Column(String(50), nullable=True)  # group, channel, user
    target_id = Column(BigInteger, nullable=True)
    target_name = Column(String(500), nullable=True)
    
    # Content information
    content_type = Column(String(50), nullable=True)
    content_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("PublishingTask", back_populates="logs")
    telegram_account = relationship("TelegramAccount", back_populates="publishing_logs")
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_publishing_log_task_id', 'task_id'),
        Index('idx_publishing_log_account_id', 'account_id'),
        Index('idx_publishing_log_user_id', 'user_id'),
        Index('idx_publishing_log_type', 'log_type'),
        Index('idx_publishing_log_success', 'success'),
        Index('idx_publishing_log_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PublishingLog(id={self.id}, type={self.log_type}, success={self.success})>"


class PrivateSubscription(Base):
    """Private subscription model for user subscribers"""
    
    __tablename__ = "private_subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    subscriber_id = Column(BigInteger, nullable=False, index=True)  # Telegram user ID
    
    # Subscription status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Subscriber information
    subscriber_username = Column(String(255), nullable=True)
    subscriber_first_name = Column(String(255), nullable=True)
    subscriber_last_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    subscribed_at = Column(DateTime, nullable=True)
    unsubscribed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="private_subscriptions")
    
    # Indexes
    __table_args__ = (
        Index('idx_private_subscription_user_id', 'user_id'),
        Index('idx_private_subscription_subscriber_id', 'subscriber_id'),
        Index('idx_private_subscription_is_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<PrivateSubscription(id={self.id}, subscriber_id={self.subscriber_id}, active={self.is_active})>"


class Subscription(Base):
    """Subscription model for user subscription plans"""
    
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True, nullable=False, index=True)
    
    # Subscription type
    subscription_type = Column(
        String(20),
        default=SubscriptionType.FREE.value,
        nullable=False
    )
    
    # Subscription status
    status = Column(
        String(20),
        default=SubscriptionStatus.ACTIVE.value,
        nullable=False
    )
    
    # Duration and timing
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    duration_days = Column(Integer, nullable=True)
    
    # Features and limits
    max_accounts = Column(Integer, default=2, nullable=False)
    max_groups = Column(Integer, default=5, nullable=False)
    min_publish_interval = Column(Integer, default=60, nullable=False)  # in minutes
    
    # Payment information (if applicable)
    payment_method = Column(String(50), nullable=True)
    transaction_id = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    
    # Auto-renewal
    auto_renew = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_user_id', 'user_id'),
        Index('idx_subscription_type', 'subscription_type'),
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_end_date', 'end_date'),
    )
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, type={self.subscription_type}, status={self.status})>"


class RequiredChannel(Base):
    """Required channel model for mandatory channel subscriptions"""
    
    __tablename__ = "required_channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Channel information
    channel_id = Column(BigInteger, unique=True, nullable=False, index=True)
    channel_username = Column(String(255), unique=True, nullable=True)
    channel_title = Column(String(500), nullable=True)
    
    # Channel type
    channel_type = Column(
        String(20),
        default=GroupType.CHANNEL.value,
        nullable=False
    )
    
    # Verification settings
    is_required = Column(Boolean, default=True, nullable=False)
    verification_enabled = Column(Boolean, default=True, nullable=False)
    
    # Priority
    priority = Column(Integer, default=0, nullable=False)
    
    # Messages
    join_message = Column(Text, nullable=True)
    success_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_required_channel_channel_id', 'channel_id'),
        Index('idx_required_channel_is_required', 'is_required'),
        Index('idx_required_channel_priority', 'priority'),
    )
    
    def __repr__(self):
        return f"<RequiredChannel(id={self.id}, username={self.channel_username}, required={self.is_required})>"


class Notification(Base):
    """Notification model for user notifications"""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    
    # Notification type
    notification_type = Column(String(50), nullable=True)
    
    # Notification content
    title = Column(String(500), nullable=True)
    message = Column(Text, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    
    # Related data
    related_id = Column(Integer, nullable=True)
    related_type = Column(String(50), nullable=True)
    
    # Action buttons
    action_buttons = Column(JSON, default=[], nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        Index('idx_notification_user_id', 'user_id'),
        Index('idx_notification_is_read', 'is_read'),
        Index('idx_notification_is_sent', 'is_sent'),
        Index('idx_notification_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, read={self.is_read})>"


class Broadcast(Base):
    """Broadcast model for administrative announcements"""
    
    __tablename__ = "broadcasts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    administrator_id = Column(BigInteger, ForeignKey("administrators.user_id"), nullable=False, index=True)
    
    # Broadcast type
    broadcast_type = Column(String(50), default="text", nullable=False)  # text, media, etc.
    
    # Broadcast content
    title = Column(String(500), nullable=True)
    message = Column(Text, nullable=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=True)
    
    # Target audience
    target_all = Column(Boolean, default=True, nullable=False)
    target_user_ids = Column(JSON, default=[], nullable=False)  # List of user IDs
    target_subscription_types = Column(JSON, default=[], nullable=False)  # List of subscription types
    
    # Status
    status = Column(String(20), default="draft", nullable=False)  # draft, scheduled, sent, cancelled
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    
    # Statistics
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    read_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    administrator = relationship("Administrator", back_populates="broadcasts")
    media_file = relationship("MediaFile")
    logs = relationship("BroadcastLog", back_populates="broadcast")
    
    # Indexes
    __table_args__ = (
        Index('idx_broadcast_administrator_id', 'administrator_id'),
        Index('idx_broadcast_status', 'status'),
        Index('idx_broadcast_scheduled_at', 'scheduled_at'),
        Index('idx_broadcast_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Broadcast(id={self.id}, status={self.status}, recipients={self.total_recipients})>"


class BroadcastLog(Base):
    """Broadcast log model for tracking broadcast deliveries"""
    
    __tablename__ = "broadcast_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    
    # Delivery status
    status = Column(String(20), nullable=True)  # sent, delivered, failed, read
    
    # Error information
    error_message = Column(String(2000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    broadcast = relationship("Broadcast", back_populates="logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_broadcast_log_broadcast_id', 'broadcast_id'),
        Index('idx_broadcast_log_user_id', 'user_id'),
        Index('idx_broadcast_log_status', 'status'),
        Index('idx_broadcast_log_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<BroadcastLog(id={self.id}, broadcast_id={self.broadcast_id}, status={self.status})>"


class AuditLog(Base):
    """Audit log model for tracking administrative actions"""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    administrator_id = Column(BigInteger, ForeignKey("administrators.user_id"), nullable=False, index=True)
    
    # Action information
    action = Column(String(255), nullable=False)
    action_type = Column(String(50), nullable=True)  # user, account, subscription, etc.
    
    # Target information
    target_id = Column(BigInteger, nullable=True)
    target_type = Column(String(50), nullable=True)
    target_name = Column(String(500), nullable=True)
    
    # Details
    details = Column(JSON, default={}, nullable=False)
    old_values = Column(JSON, default={}, nullable=False)
    new_values = Column(JSON, default={}, nullable=False)
    
    # Result
    success = Column(Boolean, nullable=True)
    error_message = Column(String(2000), nullable=True)
    
    # IP and device information
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    administrator = relationship("Administrator", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_log_administrator_id', 'administrator_id'),
        Index('idx_audit_log_action', 'action'),
        Index('idx_audit_log_action_type', 'action_type'),
        Index('idx_audit_log_target_id', 'target_id'),
        Index('idx_audit_log_target_type', 'target_type'),
        Index('idx_audit_log_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, success={self.success})>"


class ApplicationSettings(Base):
    """Application settings model for system-wide configuration"""
    
    __tablename__ = "application_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # General settings
    app_name = Column(String(255), default="Telegram Auto Publisher Pro", nullable=False)
    app_version = Column(String(50), default="1.0.0", nullable=False)
    app_description = Column(Text, nullable=True)
    
    # Bot settings
    bot_token = Column(String(255), nullable=True)
    bot_username = Column(String(255), nullable=True)
    
    # Maintenance
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    maintenance_message = Column(Text, nullable=True)
    
    # Default limits
    default_max_accounts = Column(Integer, default=2, nullable=False)
    default_max_groups = Column(Integer, default=5, nullable=False)
    default_publish_interval = Column(Integer, default=60, nullable=False)
    
    # Logging
    log_level = Column(String(10), default="INFO", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_application_settings_id', 'id'),
    )
    
    def __repr__(self):
        return f"<ApplicationSettings(id={self.id}, app_name={self.app_name})>"
