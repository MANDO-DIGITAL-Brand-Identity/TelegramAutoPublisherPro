"""
Reports module tests for Telegram Auto Publisher Pro
Tests for StatisticsManager and ReportGenerator
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
    Content,
    Group,
    PublishingTask,
    PublishingLog,
    Subscription,
    AuditLog,
    UserStatus,
    AdminRole,
    ContentType,
    GroupType,
    TaskStatus,
    TaskType,
    SubscriptionType,
    SubscriptionStatus,
    AuditActionType,
)
from reports.statistics import (
    StatisticsManager,
    DashboardStats,
    UserStats,
    AccountStats,
    PublishingStats,
    SubscriptionStats,
    ContentStats,
    GroupStats,
    SystemStats
)
from reports.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    ReportData,
    ReportConfig
)


@pytest.fixture
def test_db_url():
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
async def setup_test_db(test_db_url):
    await init_db(test_db_url, echo=False)
    yield
    await close_db()


# ==================== STATISTICS MANAGER TESTS ====================


@pytest.mark.asyncio
async def test_statistics_manager_initialization():
    """Test StatisticsManager initialization."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    assert statistics_manager is not None
    assert statistics_manager.session_factory == session_factory


@pytest.mark.asyncio
async def test_statistics_manager_get_dashboard_stats():
    """Test getting dashboard statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create test data
        for i in range(5):
            user = User(
                telegram_id=123456789 + i,
                username=f"user_{i}",
                first_name=f"User {i}",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            session.add(user)
        
        for i in range(3):
            account = TelegramAccount(
                user_id=123456789 + i,
                phone_number=f"+123456789{i}",
                account_name=f"Account {i}",
                is_connected=True,
                created_at=datetime.utcnow()
            )
            session.add(account)
        
        for i in range(2):
            content = Content(
                user_id=123456789 + i,
                title=f"Content {i}",
                content_type=ContentType.TEXT,
                text_content=f"Content text {i}",
                created_at=datetime.utcnow()
            )
            session.add(content)
        
        for i in range(4):
            task = PublishingTask(
                user_id=123456789 + i,
                task_type=TaskType.PUBLISH,
                status=TaskStatus.COMPLETED if i % 2 == 0 else TaskStatus.FAILED,
                scheduled_time=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            session.add(task)
        
        for i in range(2):
            sub = Subscription(
                user_id=123456789 + i,
                subscription_type=SubscriptionType.PREMIUM,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow()
            )
            session.add(sub)
        
        await session.flush()
        
        # Get dashboard stats
        stats = await statistics_manager.get_dashboard_stats()
        
        assert stats is not None
        assert stats.total_users >= 5
        assert stats.total_accounts >= 3
        assert stats.total_content >= 2
        assert stats.total_tasks >= 4
        assert stats.completed_tasks >= 2
        assert stats.failed_tasks >= 2
        assert stats.total_subscriptions >= 2
        
        # Clean up
        await session.execute("DELETE FROM subscriptions")
        await session.execute("DELETE FROM publishing_tasks")
        await session.execute("DELETE FROM contents")
        await session.execute("DELETE FROM telegram_accounts")
        await session.execute("DELETE FROM users")
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_user_stats():
    """Test getting user statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create user
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create accounts for user
        for i in range(3):
            account = TelegramAccount(
                user_id=user.id,
                phone_number=f"+123456789{i}",
                account_name=f"Account {i}",
                is_connected=True,
                created_at=datetime.utcnow()
            )
            session.add(account)
        
        # Create content for user
        for i in range(2):
            content = Content(
                user_id=user.id,
                title=f"Content {i}",
                content_type=ContentType.TEXT,
                text_content=f"Content text {i}",
                created_at=datetime.utcnow()
            )
            session.add(content)
        
        # Create tasks for user
        for i in range(4):
            task = PublishingTask(
                user_id=user.id,
                task_type=TaskType.PUBLISH,
                status=TaskStatus.COMPLETED if i % 2 == 0 else TaskStatus.FAILED,
                scheduled_time=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            session.add(task)
        
        await session.flush()
        
        # Get user stats
        stats = await statistics_manager.get_user_stats(user.id)
        
        assert stats is not None
        assert stats.total_accounts >= 3
        assert stats.total_content >= 2
        assert stats.total_tasks >= 4
        
        # Clean up
        await session.execute(f"DELETE FROM publishing_tasks WHERE user_id = {user.id}")
        await session.execute(f"DELETE FROM contents WHERE user_id = {user.id}")
        await session.execute(f"DELETE FROM telegram_accounts WHERE user_id = {user.id}")
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_account_stats():
    """Test getting account statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create user
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        
        # Create account
        account = TelegramAccount(
            user_id=user.id,
            phone_number="+1234567890",
            account_name="Test Account",
            is_connected=True,
            created_at=datetime.utcnow()
        )
        session.add(account)
        await session.flush()
        await session.refresh(account)
        
        # Create tasks for account
        for i in range(3):
            task = PublishingTask(
                user_id=user.id,
                account_id=account.id,
                task_type=TaskType.PUBLISH,
                status=TaskStatus.COMPLETED,
                scheduled_time=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            session.add(task)
        
        await session.flush()
        
        # Get account stats
        stats = await statistics_manager.get_account_stats(account.id)
        
        assert stats is not None
        assert stats.total_tasks >= 3
        
        # Clean up
        await session.execute(f"DELETE FROM publishing_tasks WHERE account_id = {account.id}")
        await session.delete(account)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_publishing_stats():
    """Test getting publishing statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create tasks with different statuses
        for i in range(10):
            status = [
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.PAUSED
            ][i % 5]
            
            task = PublishingTask(
                user_id=123456789 + i,
                task_type=TaskType.PUBLISH,
                status=status,
                scheduled_time=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            session.add(task)
        
        await session.flush()
        
        # Get publishing stats
        stats = await statistics_manager.get_publishing_stats()
        
        assert stats is not None
        assert stats.total_tasks >= 10
        assert stats.pending_tasks >= 2
        assert stats.running_tasks >= 2
        assert stats.completed_tasks >= 2
        assert stats.failed_tasks >= 2
        assert stats.paused_tasks >= 2
        
        # Clean up
        await session.execute("DELETE FROM publishing_tasks")
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_subscription_stats():
    """Test getting subscription statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create users
        for i in range(5):
            user = User(
                telegram_id=123456789 + i,
                username=f"user_{i}",
                first_name=f"User {i}",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            session.add(user)
        
        await session.flush()
        
        # Create subscriptions with different types and statuses
        for i in range(5):
            sub_type = [SubscriptionType.FREE, SubscriptionType.PREMIUM][i % 2]
            status = [SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED, SubscriptionStatus.INACTIVE][i % 3]
            
            sub = Subscription(
                user_id=123456789 + i,
                subscription_type=sub_type,
                status=status,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow()
            )
            session.add(sub)
        
        await session.flush()
        
        # Get subscription stats
        stats = await statistics_manager.get_subscription_stats()
        
        assert stats is not None
        assert stats.total_subscriptions >= 5
        assert stats.active_subscriptions >= 2
        assert stats.premium_subscriptions >= 3
        
        # Clean up
        await session.execute("DELETE FROM subscriptions")
        await session.execute("DELETE FROM users")
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_content_stats():
    """Test getting content statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create users
        for i in range(3):
            user = User(
                telegram_id=123456789 + i,
                username=f"user_{i}",
                first_name=f"User {i}",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            session.add(user)
        
        await session.flush()
        
        # Create content with different types
        for i in range(10):
            content_type = [
                ContentType.TEXT,
                ContentType.IMAGE,
                ContentType.VIDEO,
                ContentType.DOCUMENT
            ][i % 4]
            
            content = Content(
                user_id=123456789 + (i % 3),
                title=f"Content {i}",
                content_type=content_type,
                text_content=f"Content text {i}",
                created_at=datetime.utcnow()
            )
            session.add(content)
        
        await session.flush()
        
        # Get content stats
        stats = await statistics_manager.get_content_stats()
        
        assert stats is not None
        assert stats.total_content >= 10
        assert stats.text_content >= 3
        assert stats.image_content >= 2
        
        # Clean up
        await session.execute("DELETE FROM contents")
        await session.execute("DELETE FROM users")
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_group_stats():
    """Test getting group statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create users
        for i in range(3):
            user = User(
                telegram_id=123456789 + i,
                username=f"user_{i}",
                first_name=f"User {i}",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            session.add(user)
        
        await session.flush()
        
        # Create groups with different types
        for i in range(10):
            group_type = [GroupType.GROUP, GroupType.CHANNEL, GroupType.SUPERGROUP][i % 3]
            
            group = Group(
                user_id=123456789 + (i % 3),
                telegram_id=-100123456789 - i,
                title=f"Group {i}",
                group_type=group_type,
                username=f"group_{i}",
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(group)
        
        await session.flush()
        
        # Get group stats
        stats = await statistics_manager.get_group_stats()
        
        assert stats is not None
        assert stats.total_groups >= 10
        assert stats.active_groups >= 10
        
        # Clean up
        await session.execute("DELETE FROM groups")
        await session.execute("DELETE FROM users")
        await session.commit()


@pytest.mark.asyncio
async def test_statistics_manager_get_system_stats():
    """Test getting system statistics."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    async with session_factory() as session:
        # Create various entities
        for i in range(3):
            user = User(
                telegram_id=123456789 + i,
                username=f"user_{i}",
                first_name=f"User {i}",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            session.add(user)
        
        for i in range(2):
            admin = Administrator(
                user_id=123456789 + i,
                role=AdminRole.ADMIN,
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(admin)
        
        await session.flush()
        
        # Get system stats
        stats = await statistics_manager.get_system_stats()
        
        assert stats is not None
        assert stats.total_users >= 3
        assert stats.total_admins >= 2
        
        # Clean up
        await session.execute("DELETE FROM administrators")
        await session.execute("DELETE FROM users")
        await session.commit()


# ==================== REPORT GENERATOR TESTS ====================


@pytest.mark.asyncio
async def test_report_generator_initialization():
    """Test ReportGenerator initialization."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    assert report_generator is not None
    assert report_generator.session_factory == session_factory
    assert report_generator.statistics_manager == statistics_manager


@pytest.mark.asyncio
async def test_report_generator_generate_text_report():
    """Test generating a text report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    # Generate text report
    report_data = ReportData(
        report_type=ReportType.PUBLISHING,
        user_id=123456789,
        data={"test": "data"}
    )
    
    report_config = ReportConfig(
        report_type=ReportType.PUBLISHING,
        report_format=ReportFormat.TEXT,
        user_id=123456789
    )
    
    result = await report_generator.generate_report(report_data, report_config)
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_report_generator_generate_json_report():
    """Test generating a JSON report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    # Generate JSON report
    report_data = ReportData(
        report_type=ReportType.PUBLISHING,
        user_id=123456789,
        data={"test": "data"}
    )
    
    report_config = ReportConfig(
        report_type=ReportType.PUBLISHING,
        report_format=ReportFormat.JSON,
        user_id=123456789
    )
    
    result = await report_generator.generate_report(report_data, report_config)
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_report_generator_generate_csv_report():
    """Test generating a CSV report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    # Generate CSV report
    report_data = ReportData(
        report_type=ReportType.PUBLISHING,
        user_id=123456789,
        data={"test": "data"}
    )
    
    report_config = ReportConfig(
        report_type=ReportType.PUBLISHING,
        report_format=ReportFormat.CSV,
        user_id=123456789
    )
    
    result = await report_generator.generate_report(report_data, report_config)
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_report_generator_generate_publishing_report():
    """Test generating a publishing report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    async with session_factory() as session:
        # Create test data
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        
        for i in range(5):
            task = PublishingTask(
                user_id=user.id,
                task_type=TaskType.PUBLISH,
                status=TaskStatus.COMPLETED if i % 2 == 0 else TaskStatus.FAILED,
                scheduled_time=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            session.add(task)
        
        await session.flush()
        
        # Generate publishing report
        report_config = ReportConfig(
            report_type=ReportType.PUBLISHING,
            report_format=ReportFormat.TEXT,
            user_id=user.id
        )
        
        result = await report_generator.generate_publishing_report(report_config)
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Clean up
        await session.execute(f"DELETE FROM publishing_tasks WHERE user_id = {user.id}")
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_report_generator_generate_statistics_report():
    """Test generating a statistics report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    # Generate statistics report
    report_config = ReportConfig(
        report_type=ReportType.STATISTICS,
        report_format=ReportFormat.TEXT,
        user_id=123456789
    )
    
    result = await report_generator.generate_statistics_report(report_config)
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_report_generator_generate_user_activity_report():
    """Test generating a user activity report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    async with session_factory() as session:
        # Create user
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.flush()
        
        # Generate user activity report
        report_config = ReportConfig(
            report_type=ReportType.USER_ACTIVITY,
            report_format=ReportFormat.TEXT,
            user_id=user.id
        )
        
        result = await report_generator.generate_user_activity_report(report_config)
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Clean up
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_report_generator_export_report():
    """Test exporting a report."""
    session_factory = get_session_factory()
    statistics_manager = StatisticsManager(session_factory=session_factory)
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    # Generate and export report
    report_data = ReportData(
        report_type=ReportType.PUBLISHING,
        user_id=123456789,
        data={"test": "data"}
    )
    
    report_config = ReportConfig(
        report_type=ReportType.PUBLISHING,
        report_format=ReportFormat.TEXT,
        user_id=123456789
    )
    
    result = await report_generator.export_report(report_data, report_config, "test_report")
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


# ==================== REPORT TYPES AND FORMATS TESTS ====================


@pytest.mark.asyncio
async def test_report_type_enum():
    """Test ReportType enum."""
    assert ReportType.PUBLISHING.value == "publishing"
    assert ReportType.STATISTICS.value == "statistics"
    assert ReportType.USER_ACTIVITY.value == "user_activity"
    assert ReportType.SYSTEM.value == "system"


@pytest.mark.asyncio
async def test_report_format_enum():
    """Test ReportFormat enum."""
    assert ReportFormat.TEXT.value == "text"
    assert ReportFormat.JSON.value == "json"
    assert ReportFormat.CSV.value == "csv"


@pytest.mark.asyncio
async def test_report_data_creation():
    """Test ReportData creation."""
    report_data = ReportData(
        report_type=ReportType.PUBLISHING,
        user_id=123456789,
        data={"test": "data"}
    )
    
    assert report_data.report_type == ReportType.PUBLISHING
    assert report_data.user_id == 123456789
    assert report_data.data == {"test": "data"}


@pytest.mark.asyncio
async def test_report_config_creation():
    """Test ReportConfig creation."""
    report_config = ReportConfig(
        report_type=ReportType.PUBLISHING,
        report_format=ReportFormat.TEXT,
        user_id=123456789
    )
    
    assert report_config.report_type == ReportType.PUBLISHING
    assert report_config.report_format == ReportFormat.TEXT
    assert report_config.user_id == 123456789


# ==================== INTEGRATION TESTS ====================


@pytest.mark.asyncio
async def test_reports_module_integration():
    """Test integration of reports module components."""
    session_factory = get_session_factory()
    
    # Create statistics manager
    statistics_manager = StatisticsManager(session_factory=session_factory)
    
    # Create report generator
    report_generator = ReportGenerator(
        session_factory=session_factory,
        statistics_manager=statistics_manager
    )
    
    # Verify both are created
    assert statistics_manager is not None
    assert report_generator is not None
    
    # Verify dependencies
    assert report_generator.statistics_manager == statistics_manager
    
    # Test basic functionality
    stats = await statistics_manager.get_dashboard_stats()
    assert stats is not None
    
    report_config = ReportConfig(
        report_type=ReportType.STATISTICS,
        report_format=ReportFormat.TEXT,
        user_id=123456789
    )
    report = await report_generator.generate_statistics_report(report_config)
    assert report is not None
    assert isinstance(report, str)


__all__ = [
    # Statistics Manager tests
    'test_statistics_manager_initialization',
    'test_statistics_manager_get_dashboard_stats',
    'test_statistics_manager_get_user_stats',
    'test_statistics_manager_get_account_stats',
    'test_statistics_manager_get_publishing_stats',
    'test_statistics_manager_get_subscription_stats',
    'test_statistics_manager_get_content_stats',
    'test_statistics_manager_get_group_stats',
    'test_statistics_manager_get_system_stats',
    
    # Report Generator tests
    'test_report_generator_initialization',
    'test_report_generator_generate_text_report',
    'test_report_generator_generate_json_report',
    'test_report_generator_generate_csv_report',
    'test_report_generator_generate_publishing_report',
    'test_report_generator_generate_statistics_report',
    'test_report_generator_generate_user_activity_report',
    'test_report_generator_export_report',
    
    # Report Types and Formats tests
    'test_report_type_enum',
    'test_report_format_enum',
    'test_report_data_creation',
    'test_report_config_creation',
    
    # Integration tests
    'test_reports_module_integration',
]
