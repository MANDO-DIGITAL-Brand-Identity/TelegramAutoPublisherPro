"""
Admin module tests for Telegram Auto Publisher Pro
Tests for AdminDashboard, UserManager, AdminManager, ChannelManager, 
BroadcastManager, AuditManager, SubscriptionManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from config import config
from database.database import init_db, close_db, get_session_factory
from database.models import (
    User,
    Administrator,
    TelegramAccount,
    Subscription,
    RequiredChannel,
    Broadcast,
    AuditLog,
    UserStatus,
    AdminRole,
    SubscriptionType,
    SubscriptionStatus,
    AuditActionType,
)
from admin.dashboard import AdminDashboard
from admin.user_manager import UserManager
from admin.admin_manager import AdminManager
from admin.channel_manager import ChannelManager
from admin.broadcast_manager import BroadcastManager
from admin.audit_manager import AuditManager
from admin.subscription_manager import SubscriptionManager


@pytest.fixture
def test_db_url():
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
async def setup_test_db(test_db_url):
    await init_db(test_db_url, echo=False)
    yield
    await close_db()


# ==================== USER MANAGER TESTS ====================

@pytest.mark.asyncio
async def test_user_manager_initialization():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    assert user_manager is not None


@pytest.mark.asyncio
async def test_user_manager_create_and_get_user():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    
    async with session_factory() as session:
        await session.execute("DELETE FROM users")
        await session.commit()
        
        user_data = {
            "telegram_id": 123456789,
            "username": "test_user",
            "first_name": "Test",
            "status": UserStatus.ACTIVE,
            "is_bot": False
        }
        result = await user_manager.create_user(user_data)
        assert result is not None
        assert result.telegram_id == 123456789
        
        fetched = await user_manager.get_user(result.id)
        assert fetched is not None
        assert fetched.username == "test_user"
        
        await session.delete(result)
        await session.commit()


@pytest.mark.asyncio
async def test_user_manager_block_unblock():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    
    async with session_factory() as session:
        user = User(telegram_id=123456789, username="test", first_name="Test", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(user)
        await session.flush()
        
        await user_manager.block_user(user.id, admin_id=1)
        blocked = await user_manager.get_user(user.id)
        assert blocked.status == UserStatus.BLOCKED
        
        await user_manager.unblock_user(user.id, admin_id=1)
        unblocked = await user_manager.get_user(user.id)
        assert unblocked.status == UserStatus.ACTIVE
        
        await session.delete(user)
        await session.commit()


# ==================== ADMIN MANAGER TESTS ====================

@pytest.mark.asyncio
async def test_admin_manager_initialization():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    admin_manager = AdminManager(session_factory=session_factory, audit_manager=audit_manager, config=config)
    assert admin_manager is not None


@pytest.mark.asyncio
async def test_admin_manager_add_get_admin():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    admin_manager = AdminManager(session_factory=session_factory, audit_manager=audit_manager, config=config)
    
    async with session_factory() as session:
        user = User(telegram_id=123456789, username="test", first_name="Test", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(user)
        await session.flush()
        
        admin_data = {"user_id": user.id, "role": AdminRole.ADMIN, "is_active": True}
        result = await admin_manager.add_admin(admin_data, super_admin_id=1)
        assert result is not None
        assert result.role == AdminRole.ADMIN
        
        fetched = await admin_manager.get_admin(user.id)
        assert fetched is not None
        
        await session.delete(result)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_admin_manager_check_access():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    admin_manager = AdminManager(session_factory=session_factory, audit_manager=audit_manager, config=config)
    
    async with session_factory() as session:
        user = User(telegram_id=123456789, username="test", first_name="Test", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(user)
        await session.flush()
        
        admin = Administrator(user_id=user.id, role=AdminRole.ADMIN, is_active=True, created_at=datetime.utcnow())
        session.add(admin)
        await session.flush()
        
        assert await admin_manager.check_admin_access(user.id) is True
        
        await session.delete(admin)
        await session.delete(user)
        await session.commit()


# ==================== CHANNEL MANAGER TESTS ====================

@pytest.mark.asyncio
async def test_channel_manager_initialization():
    session_factory = get_session_factory()
    channel_manager = ChannelManager(session_factory=session_factory, config=config)
    assert channel_manager is not None


@pytest.mark.asyncio
async def test_channel_manager_add_get_channel():
    session_factory = get_session_factory()
    channel_manager = ChannelManager(session_factory=session_factory, config=config)
    
    async with session_factory() as session:
        await session.execute("DELETE FROM required_channels")
        await session.commit()
        
        channel_data = {
            "channel_id": -100123456789,
            "channel_username": "test_channel",
            "channel_title": "Test Channel",
            "is_active": True
        }
        result = await channel_manager.add_required_channel(channel_data)
        assert result is not None
        assert result.channel_username == "test_channel"
        
        fetched = await channel_manager.get_required_channel(result.id)
        assert fetched is not None
        
        await session.delete(result)
        await session.commit()


@pytest.mark.asyncio
async def test_channel_manager_get_channels():
    session_factory = get_session_factory()
    channel_manager = ChannelManager(session_factory=session_factory, config=config)
    
    async with session_factory() as session:
        for i in range(3):
            channel = RequiredChannel(
                channel_id=-100123456789-i,
                channel_username=f"channel_{i}",
                channel_title=f"Channel {i}",
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(channel)
        await session.flush()
        
        results = await channel_manager.get_required_channels()
        assert len(results) >= 3
        
        await session.execute("DELETE FROM required_channels")
        await session.commit()


# ==================== SUBSCRIPTION MANAGER TESTS ====================

@pytest.mark.asyncio
async def test_subscription_manager_initialization():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    subscription_manager = SubscriptionManager(
        session_factory=session_factory,
        user_manager=user_manager,
        audit_manager=audit_manager,
        config=config
    )
    assert subscription_manager is not None


@pytest.mark.asyncio
async def test_subscription_manager_create_subscription():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    subscription_manager = SubscriptionManager(
        session_factory=session_factory,
        user_manager=user_manager,
        audit_manager=audit_manager,
        config=config
    )
    
    async with session_factory() as session:
        user = User(telegram_id=123456789, username="test", first_name="Test", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(user)
        await session.flush()
        
        sub_data = {
            "user_id": user.id,
            "subscription_type": SubscriptionType.PREMIUM,
            "status": SubscriptionStatus.ACTIVE,
            "start_date": datetime.utcnow(),
            "end_date": datetime.utcnow() + timedelta(days=30)
        }
        result = await subscription_manager.create_subscription(sub_data)
        assert result is not None
        assert result.subscription_type == SubscriptionType.PREMIUM
        
        await session.delete(result)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_subscription_manager_activate_deactivate():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    subscription_manager = SubscriptionManager(
        session_factory=session_factory,
        user_manager=user_manager,
        audit_manager=audit_manager,
        config=config
    )
    
    async with session_factory() as session:
        user = User(telegram_id=123456789, username="test", first_name="Test", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(user)
        await session.flush()
        
        sub = Subscription(
            user_id=user.id,
            subscription_type=SubscriptionType.PREMIUM,
            status=SubscriptionStatus.INACTIVE,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            created_at=datetime.utcnow()
        )
        session.add(sub)
        await session.flush()
        
        await subscription_manager.activate_subscription(user.id, admin_id=1)
        activated = await subscription_manager.get_subscription(user.id)
        assert activated.status == SubscriptionStatus.ACTIVE
        
        await subscription_manager.deactivate_subscription(user.id, admin_id=1)
        deactivated = await subscription_manager.get_subscription(user.id)
        assert deactivated.status == SubscriptionStatus.INACTIVE
        
        await session.delete(sub)
        await session.delete(user)
        await session.commit()


# ==================== BROADCAST MANAGER TESTS ====================

@pytest.mark.asyncio
async def test_broadcast_manager_initialization():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    broadcast_manager = BroadcastManager(
        session_factory=session_factory,
        notification_manager=MagicMock(),
        audit_manager=audit_manager
    )
    assert broadcast_manager is not None


@pytest.mark.asyncio
async def test_broadcast_manager_create_broadcast():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    broadcast_manager = BroadcastManager(
        session_factory=session_factory,
        notification_manager=MagicMock(),
        audit_manager=audit_manager
    )
    
    async with session_factory() as session:
        admin = User(telegram_id=123456789, username="admin", first_name="Admin", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(admin)
        await session.flush()
        
        broadcast_data = {
            "admin_id": admin.id,
            "title": "Test Broadcast",
            "message": "Test message",
            "message_type": "text",
            "target_audience": "all"
        }
        result = await broadcast_manager.create_broadcast(broadcast_data)
        assert result is not None
        assert result.title == "Test Broadcast"
        
        await session.delete(result)
        await session.delete(admin)
        await session.commit()


@pytest.mark.asyncio
async def test_broadcast_manager_get_broadcasts():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    broadcast_manager = BroadcastManager(
        session_factory=session_factory,
        notification_manager=MagicMock(),
        audit_manager=audit_manager
    )
    
    async with session_factory() as session:
        admin = User(telegram_id=123456789, username="admin", first_name="Admin", status=UserStatus.ACTIVE, created_at=datetime.utcnow())
        session.add(admin)
        await session.flush()
        
        for i in range(3):
            broadcast = Broadcast(
                admin_id=admin.id,
                title=f"Broadcast {i}",
                message=f"Message {i}",
                message_type="text",
                target_audience="all",
                created_at=datetime.utcnow()
            )
            session.add(broadcast)
        await session.flush()
        
        results = await broadcast_manager.get_broadcasts()
        assert len(results) >= 3
        
        await session.execute("DELETE FROM broadcasts")
        await session.delete(admin)
        await session.commit()


# ==================== AUDIT MANAGER TESTS ====================

@pytest.mark.asyncio
async def test_audit_manager_initialization():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    assert audit_manager is not None


@pytest.mark.asyncio
async def test_audit_manager_log_action():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    
    async with session_factory() as session:
        await session.execute("DELETE FROM audit_logs")
        await session.commit()
        
        await audit_manager.log_action(
            admin_id=1,
            action=AuditActionType.USER_BLOCKED,
            target_user_id=123456789,
            target_type="user",
            details={},
            success=True
        )
        
        from database.repositories import AuditLogRepository
        log_repo = AuditLogRepository(session)
        logs = await log_repo.get_recent_logs(limit=1)
        assert len(logs) == 1
        assert logs[0].action == AuditActionType.USER_BLOCKED


@pytest.mark.asyncio
async def test_audit_manager_get_logs():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    
    async with session_factory() as session:
        for i in range(3):
            await audit_manager.log_action(
                admin_id=1,
                action=AuditActionType.USER_BLOCKED,
                target_user_id=123456789+i,
                target_type="user",
                details={},
                success=True
            )
        
        results = await audit_manager.get_audit_logs(limit=10)
        assert len(results) >= 3


# ==================== ADMIN DASHBOARD TESTS ====================

@pytest.mark.asyncio
async def test_admin_dashboard_initialization():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    admin_manager = AdminManager(session_factory=session_factory, audit_manager=audit_manager, config=config)
    subscription_manager = SubscriptionManager(
        session_factory=session_factory,
        user_manager=user_manager,
        audit_manager=audit_manager,
        config=config
    )
    channel_manager = ChannelManager(session_factory=session_factory, config=config)
    
    admin_dashboard = AdminDashboard(
        config=config,
        user_manager=user_manager,
        admin_manager=admin_manager,
        subscription_manager=subscription_manager,
        channel_manager=channel_manager,
        statistics_manager=MagicMock(),
        audit_manager=audit_manager,
        session_factory=session_factory
    )
    assert admin_dashboard is not None


@pytest.mark.asyncio
async def test_admin_dashboard_get_stats():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    admin_manager = AdminManager(session_factory=session_factory, audit_manager=audit_manager, config=config)
    subscription_manager = SubscriptionManager(
        session_factory=session_factory,
        user_manager=user_manager,
        audit_manager=audit_manager,
        config=config
    )
    channel_manager = ChannelManager(session_factory=session_factory, config=config)
    statistics_manager = MagicMock()
    statistics_manager.get_dashboard_stats = AsyncMock(return_value={})
    
    admin_dashboard = AdminDashboard(
        config=config,
        user_manager=user_manager,
        admin_manager=admin_manager,
        subscription_manager=subscription_manager,
        channel_manager=channel_manager,
        statistics_manager=statistics_manager,
        audit_manager=audit_manager,
        session_factory=session_factory
    )
    
    stats = await admin_dashboard.get_dashboard_stats()
    assert stats is not None


# ==================== INTEGRATION TESTS ====================

@pytest.mark.asyncio
async def test_admin_module_integration():
    session_factory = get_session_factory()
    audit_manager = AuditManager(session_factory=session_factory)
    user_manager = UserManager(session_factory=session_factory, audit_manager=audit_manager)
    admin_manager = AdminManager(session_factory=session_factory, audit_manager=audit_manager, config=config)
    subscription_manager = SubscriptionManager(
        session_factory=session_factory,
        user_manager=user_manager,
        audit_manager=audit_manager,
        config=config
    )
    channel_manager = ChannelManager(session_factory=session_factory, config=config)
    broadcast_manager = BroadcastManager(
        session_factory=session_factory,
        notification_manager=MagicMock(),
        audit_manager=audit_manager
    )
    
    admin_dashboard = AdminDashboard(
        config=config,
        user_manager=user_manager,
        admin_manager=admin_manager,
        subscription_manager=subscription_manager,
        channel_manager=channel_manager,
        statistics_manager=MagicMock(),
        audit_manager=audit_manager,
        session_factory=session_factory
    )
    
    assert audit_manager is not None
    assert user_manager is not None
    assert admin_manager is not None
    assert subscription_manager is not None
    assert channel_manager is not None
    assert broadcast_manager is not None
    assert admin_dashboard is not None


__all__ = [
    # User Manager
    'test_user_manager_initialization',
    'test_user_manager_create_and_get_user',
    'test_user_manager_block_unblock',
    
    # Admin Manager
    'test_admin_manager_initialization',
    'test_admin_manager_add_get_admin',
    'test_admin_manager_check_access',
    
    # Channel Manager
    'test_channel_manager_initialization',
    'test_channel_manager_add_get_channel',
    'test_channel_manager_get_channels',
    
    # Subscription Manager
    'test_subscription_manager_initialization',
    'test_subscription_manager_create_subscription',
    'test_subscription_manager_activate_deactivate',
    
    # Broadcast Manager
    'test_broadcast_manager_initialization',
    'test_broadcast_manager_create_broadcast',
    'test_broadcast_manager_get_broadcasts',
    
    # Audit Manager
    'test_audit_manager_initialization',
    'test_audit_manager_log_action',
    'test_audit_manager_get_logs',
    
    # Admin Dashboard
    'test_admin_dashboard_initialization',
    'test_admin_dashboard_get_stats',
    
    # Integration
    'test_admin_module_integration',
]
