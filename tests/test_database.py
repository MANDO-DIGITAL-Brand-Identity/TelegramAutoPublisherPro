"""
Database tests for Telegram Auto Publisher Pro
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, delete

from database.database import init_db, close_db, get_session_factory
from database.models import (
    User,
    Administrator,
    TelegramAccount,
    Content,
    Group,
    PublishingTask,
    PublishingLog,
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
    GroupType,
    TaskStatus,
    SubscriptionType,
    SubscriptionStatus,
)


@pytest.fixture
def test_db_url():
    """Get test database URL."""
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
async def setup_test_db(test_db_url):
    """Setup test database."""
    # Initialize database
    await init_db(test_db_url, echo=False)
    yield
    # Clean up
    await close_db()


@pytest.mark.asyncio
async def test_user_model():
    """Test User model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Verify
        assert user.id is not None
        assert user.telegram_id == 123456789
        assert user.username == "test_user"
        assert user.status == UserStatus.ACTIVE
        
        # Query
        result = await session.execute(
            select(User).where(User.telegram_id == 123456789)
        )
        fetched_user = result.scalars().first()
        assert fetched_user is not None
        assert fetched_user.telegram_id == 123456789
        
        # Clean up
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_telegram_account_model():
    """Test TelegramAccount model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user first
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create account
        account = TelegramAccount(
            user_id=user.telegram_id,
            account_name="Test Account",
            phone_number="+1234567890",
            is_connected=True,
            is_bot=False,
            session_id="test_session",
            created_at=datetime.utcnow()
        )
        session.add(account)
        await session.flush()
        await session.refresh(account)
        
        # Verify
        assert account.id is not None
        assert account.user_id == user.telegram_id
        assert account.account_name == "Test Account"
        assert account.is_connected is True
        
        # Clean up
        await session.delete(account)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_content_model():
    """Test Content model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user first
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create content
        content = Content(
            user_id=user.telegram_id,
            title="Test Content",
            content="This is test content",
            content_type=ContentType.TEXT,
            created_at=datetime.utcnow()
        )
        session.add(content)
        await session.flush()
        await session.refresh(content)
        
        # Verify
        assert content.id is not None
        assert content.user_id == user.telegram_id
        assert content.title == "Test Content"
        assert content.content_type == ContentType.TEXT
        
        # Clean up
        await session.delete(content)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_group_model():
    """Test Group model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user first
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create account
        account = TelegramAccount(
            user_id=user.telegram_id,
            account_name="Test Account",
            phone_number="+1234567890",
            is_connected=True,
            is_bot=False,
            session_id="test_session",
            created_at=datetime.utcnow()
        )
        session.add(account)
        await session.flush()
        await session.refresh(account)
        
        # Create group
        group = Group(
            user_id=user.telegram_id,
            telegram_account_id=account.id,
            group_id=-1001234567890,
            group_name="Test Group",
            group_username="test_group",
            group_type=GroupType.CHANNEL,
            is_selected=True,
            can_send_messages=True,
            created_at=datetime.utcnow()
        )
        session.add(group)
        await session.flush()
        await session.refresh(group)
        
        # Verify
        assert group.id is not None
        assert group.group_id == -1001234567890
        assert group.group_name == "Test Group"
        assert group.group_type == GroupType.CHANNEL
        
        # Clean up
        await session.delete(group)
        await session.delete(account)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_publishing_task_model():
    """Test PublishingTask model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user first
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create account
        account = TelegramAccount(
            user_id=user.telegram_id,
            account_name="Test Account",
            phone_number="+1234567890",
            is_connected=True,
            is_bot=False,
            session_id="test_session",
            created_at=datetime.utcnow()
        )
        session.add(account)
        await session.flush()
        await session.refresh(account)
        
        # Create content
        content = Content(
            user_id=user.telegram_id,
            title="Test Content",
            content="This is test content",
            content_type=ContentType.TEXT,
            created_at=datetime.utcnow()
        )
        session.add(content)
        await session.flush()
        await session.refresh(content)
        
        # Create group
        group = Group(
            user_id=user.telegram_id,
            telegram_account_id=account.id,
            group_id=-1001234567890,
            group_name="Test Group",
            group_username="test_group",
            group_type=GroupType.CHANNEL,
            is_selected=True,
            can_send_messages=True,
            created_at=datetime.utcnow()
        )
        session.add(group)
        await session.flush()
        await session.refresh(group)
        
        # Create task
        task = PublishingTask(
            user_id=user.telegram_id,
            name="Test Task",
            telegram_account_id=account.id,
            content_id=content.id,
            group_id=group.id,
            group_ids=[group.id],
            status=TaskStatus.PENDING,
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            interval_minutes=60,
            created_at=datetime.utcnow()
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)
        
        # Verify
        assert task.id is not None
        assert task.user_id == user.telegram_id
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING
        
        # Clean up
        await session.delete(task)
        await session.delete(group)
        await session.delete(content)
        await session.delete(account)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_subscription_model():
    """Test Subscription model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user first
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create subscription
        subscription = Subscription(
            user_id=user.telegram_id,
            subscription_type=SubscriptionType.FREE,
            status=SubscriptionStatus.ACTIVE,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            auto_renew=False,
            max_accounts=2,
            max_groups=5,
            min_publish_interval=60,
            created_at=datetime.utcnow()
        )
        session.add(subscription)
        await session.flush()
        await session.refresh(subscription)
        
        # Verify
        assert subscription.id is not None
        assert subscription.user_id == user.telegram_id
        assert subscription.subscription_type == SubscriptionType.FREE
        assert subscription.status == SubscriptionStatus.ACTIVE
        
        # Clean up
        await session.delete(subscription)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_required_channel_model():
    """Test RequiredChannel model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create channel
        channel = RequiredChannel(
            channel_id=-1001234567890,
            channel_username="test_channel",
            channel_title="Test Channel",
            channel_type=GroupType.CHANNEL,
            is_required=True,
            verification_enabled=True,
            priority=0,
            join_message="Please join this channel",
            success_message="Thank you for joining!",
            created_at=datetime.utcnow()
        )
        session.add(channel)
        await session.flush()
        await session.refresh(channel)
        
        # Verify
        assert channel.id is not None
        assert channel.channel_id == -1001234567890
        assert channel.channel_username == "test_channel"
        assert channel.is_required is True
        
        # Clean up
        await session.delete(channel)
        await session.commit()


@pytest.mark.asyncio
async def test_notification_model():
    """Test Notification model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create user first
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            language_code="en",
            status=UserStatus.ACTIVE,
            is_bot=False,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create notification
        notification = Notification(
            user_id=user.telegram_id,
            notification_type="system",
            title="Test Notification",
            message="This is a test notification",
            is_read=False,
            is_sent=True,
            related_id=1,
            related_type="test",
            action_buttons=[],
            created_at=datetime.utcnow()
        )
        session.add(notification)
        await session.flush()
        await session.refresh(notification)
        
        # Verify
        assert notification.id is not None
        assert notification.user_id == user.telegram_id
        assert notification.title == "Test Notification"
        assert notification.is_read is False
        
        # Clean up
        await session.delete(notification)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_broadcast_model():
    """Test Broadcast model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create admin first
        admin = Administrator(
            user_id=123456789,
            username="admin_user",
            first_name="Admin",
            last_name="User",
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(admin)
        await session.flush()
        await session.refresh(admin)
        
        # Create broadcast
        broadcast = Broadcast(
            administrator_id=admin.user_id,
            broadcast_type="text",
            title="Test Broadcast",
            message="This is a test broadcast",
            target_all=True,
            target_user_ids=[],
            target_subscription_types=[],
            status="draft",
            scheduled_at=None,
            timezone="UTC",
            total_recipients=0,
            sent_count=0,
            failed_count=0,
            read_count=0,
            created_at=datetime.utcnow()
        )
        session.add(broadcast)
        await session.flush()
        await session.refresh(broadcast)
        
        # Verify
        assert broadcast.id is not None
        assert broadcast.administrator_id == admin.user_id
        assert broadcast.title == "Test Broadcast"
        assert broadcast.status == "draft"
        
        # Clean up
        await session.delete(broadcast)
        await session.delete(admin)
        await session.commit()


@pytest.mark.asyncio
async def test_audit_log_model():
    """Test AuditLog model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create admin first
        admin = Administrator(
            user_id=123456789,
            username="admin_user",
            first_name="Admin",
            last_name="User",
            role=AdminRole.SUPER_ADMIN,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(admin)
        await session.flush()
        await session.refresh(admin)
        
        # Create audit log
        audit_log = AuditLog(
            administrator_id=admin.user_id,
            action="test_action",
            action_type="test",
            target_id=1,
            target_type="test",
            target_name="Test Target",
            details={"key": "value"},
            old_values={},
            new_values={},
            success=True,
            error_message=None,
            ip_address="127.0.0.1",
            user_agent="Test Agent",
            created_at=datetime.utcnow()
        )
        session.add(audit_log)
        await session.flush()
        await session.refresh(audit_log)
        
        # Verify
        assert audit_log.id is not None
        assert audit_log.administrator_id == admin.user_id
        assert audit_log.action == "test_action"
        assert audit_log.success is True
        
        # Clean up
        await session.delete(audit_log)
        await session.delete(admin)
        await session.commit()


@pytest.mark.asyncio
async def test_application_settings_model():
    """Test ApplicationSettings model."""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Create settings
        settings = ApplicationSettings(
            app_name="Telegram Auto Publisher Pro",
            app_version="1.0.0",
            app_description="Test description",
            maintenance_mode=False,
            maintenance_message="",
            default_max_accounts=2,
            default_max_groups=5,
            default_publish_interval=60,
            log_level="INFO",
            created_at=datetime.utcnow()
        )
        session.add(settings)
        await session.flush()
        await session.refresh(settings)
        
        # Verify
        assert settings.id is not None
        assert settings.app_name == "Telegram Auto Publisher Pro"
        assert settings.app_version == "1.0.0"
        assert settings.maintenance_mode is False
        
        # Clean up
        await session.delete(settings)
        await session.commit()
