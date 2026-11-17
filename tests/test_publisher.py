"""
Publisher module tests for Telegram Auto Publisher Pro
Tests for PublishingEngine, TaskScheduler, ContentManager, GroupManager, TaskManager
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy import select

from config import config
from database.database import init_db, close_db, get_session_factory
from database.models import (
    User,
    TelegramAccount,
    Content,
    Group,
    PublishingTask,
    PublishingLog,
    MediaFile,
    ContentType,
    GroupType,
    TaskStatus,
    TaskType,
    UserStatus,
)
from publisher.engine import PublishingEngine, PublishConfig, PublishResult, PublishResultData
from publisher.scheduler import TaskScheduler, TaskType
from publisher.content_manager import ContentManager, ContentData
from publisher.group_manager import GroupManager, GroupInfo, PermissionLevel
from publisher.task_manager import TaskManager, TaskInfo, TaskState


@pytest.fixture
def test_db_url():
    """Get test database URL."""
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
async def setup_test_db(test_db_url):
    """Setup test database."""
    await init_db(test_db_url, echo=False)
    yield
    await close_db()


# ==================== CONTENT MANAGER TESTS ====================


@pytest.mark.asyncio
async def test_content_manager_initialization():
    """Test ContentManager initialization."""
    session_factory = get_session_factory()
    
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
    )
    
    assert content_manager is not None
    assert content_manager.session_factory == session_factory
    assert content_manager.config == config


@pytest.mark.asyncio
async def test_create_content():
    """Test creating content."""
    session_factory = get_session_factory()
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create content
        content_data = ContentData(
            user_id=user.id,
            title="Test Content",
            content_type=ContentType.TEXT,
            text_content="This is a test content",
            media_file_id=None
        )
        
        result = await content_manager.create_content(content_data)
        
        assert result is not None
        assert result.id is not None
        assert result.title == "Test Content"
        assert result.content_type == ContentType.TEXT
        assert result.text_content == "This is a test content"
        
        # Clean up
        await session.delete(result)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_content():
    """Test getting content by ID."""
    session_factory = get_session_factory()
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create content
        content = Content(
            user_id=user.id,
            title="Test Content",
            content_type=ContentType.TEXT,
            text_content="This is a test content",
            created_at=datetime.utcnow()
        )
        session.add(content)
        await session.flush()
        await session.refresh(content)
        
        # Get content
        result = await content_manager.get_content(content.id)
        
        assert result is not None
        assert result.id == content.id
        assert result.title == "Test Content"
        
        # Clean up
        await session.delete(content)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_contents_by_user():
    """Test getting contents by user ID."""
    session_factory = get_session_factory()
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create multiple contents
        for i in range(3):
            content = Content(
                user_id=user.id,
                title=f"Test Content {i}",
                content_type=ContentType.TEXT,
                text_content=f"This is test content {i}",
                created_at=datetime.utcnow()
            )
            session.add(content)
        
        await session.flush()
        
        # Get contents by user
        results = await content_manager.get_contents_by_user(user.id)
        
        assert len(results) == 3
        
        # Clean up
        await session.execute(
            delete(Content).where(Content.user_id == user.id)
        )
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_update_content():
    """Test updating content."""
    session_factory = get_session_factory()
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create content
        content = Content(
            user_id=user.id,
            title="Test Content",
            content_type=ContentType.TEXT,
            text_content="This is a test content",
            created_at=datetime.utcnow()
        )
        session.add(content)
        await session.flush()
        await session.refresh(content)
        
        # Update content
        content_data = ContentData(
            id=content.id,
            user_id=user.id,
            title="Updated Content",
            content_type=ContentType.TEXT,
            text_content="This is updated content"
        )
        
        result = await content_manager.update_content(content_data)
        
        assert result is not None
        assert result.title == "Updated Content"
        assert result.text_content == "This is updated content"
        
        # Clean up
        await session.delete(content)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_delete_content():
    """Test deleting content."""
    session_factory = get_session_factory()
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create content
        content = Content(
            user_id=user.id,
            title="Test Content",
            content_type=ContentType.TEXT,
            text_content="This is a test content",
            created_at=datetime.utcnow()
        )
        session.add(content)
        await session.flush()
        await session.refresh(content)
        
        # Delete content
        await content_manager.delete_content(content.id)
        
        # Verify deletion
        result = await content_manager.get_content(content.id)
        assert result is None
        
        # Clean up
        await session.delete(user)
        await session.commit()


# ==================== GROUP MANAGER TESTS ====================


@pytest.mark.asyncio
async def test_group_manager_initialization():
    """Test GroupManager initialization."""
    session_factory = get_session_factory()
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    group_manager = GroupManager(
        config=config,
        session_factory=session_factory,
        account_manager=mock_account_manager
    )
    
    assert group_manager is not None
    assert group_manager.session_factory == session_factory
    assert group_manager.config == config


@pytest.mark.asyncio
async def test_create_group():
    """Test creating a group."""
    session_factory = get_session_factory()
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    group_manager = GroupManager(
        config=config,
        session_factory=session_factory,
        account_manager=mock_account_manager
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
        await session.refresh(user)
        
        # Create group
        group_data = {
            "user_id": user.id,
            "telegram_id": -100123456789,
            "title": "Test Group",
            "group_type": GroupType.CHANNEL,
            "username": "test_group",
            "is_active": True
        }
        
        result = await group_manager.create_group(group_data)
        
        assert result is not None
        assert result.id is not None
        assert result.title == "Test Group"
        assert result.group_type == GroupType.CHANNEL
        
        # Clean up
        await session.delete(result)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_group():
    """Test getting a group by ID."""
    session_factory = get_session_factory()
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    group_manager = GroupManager(
        config=config,
        session_factory=session_factory,
        account_manager=mock_account_manager
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
        await session.refresh(user)
        
        # Create group
        group = Group(
            user_id=user.id,
            telegram_id=-100123456789,
            title="Test Group",
            group_type=GroupType.CHANNEL,
            username="test_group",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(group)
        await session.flush()
        await session.refresh(group)
        
        # Get group
        result = await group_manager.get_group(group.id)
        
        assert result is not None
        assert result.id == group.id
        assert result.title == "Test Group"
        
        # Clean up
        await session.delete(group)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_groups_by_user():
    """Test getting groups by user ID."""
    session_factory = get_session_factory()
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    group_manager = GroupManager(
        config=config,
        session_factory=session_factory,
        account_manager=mock_account_manager
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
        await session.refresh(user)
        
        # Create multiple groups
        for i in range(3):
            group = Group(
                user_id=user.id,
                telegram_id=-100123456789 - i,
                title=f"Test Group {i}",
                group_type=GroupType.CHANNEL,
                username=f"test_group_{i}",
                is_active=True,
                created_at=datetime.utcnow()
            )
            session.add(group)
        
        await session.flush()
        
        # Get groups by user
        results = await group_manager.get_groups_by_user(user.id)
        
        assert len(results) == 3
        
        # Clean up
        await session.execute(
            delete(Group).where(Group.user_id == user.id)
        )
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_check_group_permissions():
    """Test checking group permissions."""
    session_factory = get_session_factory()
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    group_manager = GroupManager(
        config=config,
        session_factory=session_factory,
        account_manager=mock_account_manager
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
        await session.refresh(user)
        
        # Create group
        group = Group(
            user_id=user.id,
            telegram_id=-100123456789,
            title="Test Group",
            group_type=GroupType.CHANNEL,
            username="test_group",
            is_active=True,
            can_post_messages=True,
            can_edit_messages=True,
            created_at=datetime.utcnow()
        )
        session.add(group)
        await session.flush()
        await session.refresh(group)
        
        # Check permissions
        result = await group_manager.check_group_permissions(group.id)
        
        assert result == PermissionLevel.FULL
        
        # Clean up
        await session.delete(group)
        await session.delete(user)
        await session.commit()


# ==================== TASK MANAGER TESTS ====================


@pytest.mark.asyncio
async def test_task_manager_initialization():
    """Test TaskManager initialization."""
    session_factory = get_session_factory()
    
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
    )
    
    assert task_manager is not None
    assert task_manager.session_factory == session_factory
    assert task_manager.config == config


@pytest.mark.asyncio
async def test_create_task():
    """Test creating a task."""
    session_factory = get_session_factory()
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create content
        content = Content(
            user_id=user.id,
            title="Test Content",
            content_type=ContentType.TEXT,
            text_content="This is a test content",
            created_at=datetime.utcnow()
        )
        session.add(content)
        await session.flush()
        await session.refresh(content)
        
        # Create task
        task_data = {
            "user_id": user.id,
            "account_id": None,
            "content_id": content.id,
            "task_type": TaskType.PUBLISH,
            "status": TaskStatus.PENDING,
            "scheduled_time": datetime.utcnow() + timedelta(hours=1),
            "interval_minutes": 60
        }
        
        result = await task_manager.create_task(task_data)
        
        assert result is not None
        assert result.id is not None
        assert result.task_type == TaskType.PUBLISH
        assert result.status == TaskStatus.PENDING
        
        # Clean up
        await session.delete(result)
        await session.delete(content)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_task():
    """Test getting a task by ID."""
    session_factory = get_session_factory()
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create task
        task = PublishingTask(
            user_id=user.id,
            task_type=TaskType.PUBLISH,
            status=TaskStatus.PENDING,
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)
        
        # Get task
        result = await task_manager.get_task(task.id)
        
        assert result is not None
        assert result.id == task.id
        assert result.task_type == TaskType.PUBLISH
        
        # Clean up
        await session.delete(task)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_get_tasks_by_user():
    """Test getting tasks by user ID."""
    session_factory = get_session_factory()
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create multiple tasks
        for i in range(3):
            task = PublishingTask(
                user_id=user.id,
                task_type=TaskType.PUBLISH,
                status=TaskStatus.PENDING,
                scheduled_time=datetime.utcnow() + timedelta(hours=i+1),
                created_at=datetime.utcnow()
            )
            session.add(task)
        
        await session.flush()
        
        # Get tasks by user
        results = await task_manager.get_tasks_by_user(user.id)
        
        assert len(results) == 3
        
        # Clean up
        await session.execute(
            delete(PublishingTask).where(PublishingTask.user_id == user.id)
        )
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_update_task_status():
    """Test updating task status."""
    session_factory = get_session_factory()
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create task
        task = PublishingTask(
            user_id=user.id,
            task_type=TaskType.PUBLISH,
            status=TaskStatus.PENDING,
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)
        
        # Update status
        await task_manager.update_task_status(task.id, TaskStatus.RUNNING)
        
        # Verify
        result = await task_manager.get_task(task.id)
        assert result.status == TaskStatus.RUNNING
        
        # Clean up
        await session.delete(task)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_delete_task():
    """Test deleting a task."""
    session_factory = get_session_factory()
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
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
        await session.refresh(user)
        
        # Create task
        task = PublishingTask(
            user_id=user.id,
            task_type=TaskType.PUBLISH,
            status=TaskStatus.PENDING,
            scheduled_time=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)
        
        # Delete task
        await task_manager.delete_task(task.id)
        
        # Verify deletion
        result = await task_manager.get_task(task.id)
        assert result is None
        
        # Clean up
        await session.delete(user)
        await session.commit()


# ==================== PUBLISHING ENGINE TESTS ====================


@pytest.mark.asyncio
async def test_publishing_engine_initialization():
    """Test PublishingEngine initialization."""
    session_factory = get_session_factory()
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    publishing_engine = PublishingEngine(
        config=config,
        account_manager=mock_account_manager,
        session_factory=session_factory
    )
    
    assert publishing_engine is not None
    assert publishing_engine.config == config
    assert publishing_engine.account_manager == mock_account_manager


@pytest.mark.asyncio
async def test_publish_config_creation():
    """Test PublishConfig creation."""
    config_data = {
        "account_id": 1,
        "content_id": 1,
        "group_ids": [1, 2, 3],
        "schedule_time": datetime.utcnow(),
        "interval_minutes": 60
    }
    
    publish_config = PublishConfig(**config_data)
    
    assert publish_config.account_id == 1
    assert publish_config.content_id == 1
    assert publish_config.group_ids == [1, 2, 3]
    assert publish_config.interval_minutes == 60


@pytest.mark.asyncio
async def test_publish_result_creation():
    """Test PublishResult creation."""
    result_data = PublishResultData(
        success_count=5,
        failure_count=2,
        total_count=7,
        errors=["Error 1", "Error 2"]
    )
    
    result = PublishResult(
        success=True,
        data=result_data
    )
    
    assert result.success is True
    assert result.data.success_count == 5
    assert result.data.failure_count == 2
    assert result.data.total_count == 7


# ==================== TASK SCHEDULER TESTS ====================


@pytest.mark.asyncio
async def test_task_scheduler_initialization():
    """Test TaskScheduler initialization."""
    session_factory = get_session_factory()
    
    # Mock publishing engine
    mock_publishing_engine = MagicMock()
    
    task_scheduler = TaskScheduler(
        config=config,
        publishing_engine=mock_publishing_engine,
        session_factory=session_factory
    )
    
    assert task_scheduler is not None
    assert task_scheduler.config == config
    assert task_scheduler.publishing_engine == mock_publishing_engine


@pytest.mark.asyncio
async def test_schedule_task():
    """Test scheduling a task."""
    session_factory = get_session_factory()
    
    # Mock publishing engine
    mock_publishing_engine = MagicMock()
    
    task_scheduler = TaskScheduler(
        config=config,
        publishing_engine=mock_publishing_engine,
        session_factory=session_factory
    )
    
    # Mock the scheduler
    with patch('publisher.scheduler.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        # Schedule a task
        task_id = 1
        run_time = datetime.utcnow() + timedelta(minutes=10)
        
        await task_scheduler.schedule_task(task_id, run_time)
        
        # Verify scheduler was called
        mock_scheduler.add_job.assert_called_once()


@pytest.mark.asyncio
async def test_start_scheduler():
    """Test starting the scheduler."""
    session_factory = get_session_factory()
    
    # Mock publishing engine
    mock_publishing_engine = MagicMock()
    
    task_scheduler = TaskScheduler(
        config=config,
        publishing_engine=mock_publishing_engine,
        session_factory=session_factory
    )
    
    # Mock the scheduler
    with patch('publisher.scheduler.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        await task_scheduler.start()
        
        # Verify scheduler was started
        mock_scheduler.start.assert_called_once()


@pytest.mark.asyncio
async def test_stop_scheduler():
    """Test stopping the scheduler."""
    session_factory = get_session_factory()
    
    # Mock publishing engine
    mock_publishing_engine = MagicMock()
    
    task_scheduler = TaskScheduler(
        config=config,
        publishing_engine=mock_publishing_engine,
        session_factory=session_factory
    )
    
    # Mock the scheduler
    with patch('publisher.scheduler.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        await task_scheduler.start()
        await task_scheduler.stop()
        
        # Verify scheduler was stopped
        mock_scheduler.shutdown.assert_called_once()


# ==================== INTEGRATION TESTS ====================


@pytest.mark.asyncio
async def test_publisher_module_integration():
    """Test integration of publisher module components."""
    session_factory = get_session_factory()
    
    # Create all components
    content_manager = ContentManager(
        config=config,
        session_factory=session_factory
    )
    
    # Mock account manager
    mock_account_manager = MagicMock()
    
    group_manager = GroupManager(
        config=config,
        session_factory=session_factory,
        account_manager=mock_account_manager
    )
    
    task_manager = TaskManager(
        config=config,
        session_factory=session_factory
    )
    
    # Mock publishing engine
    mock_publishing_engine = MagicMock()
    
    task_scheduler = TaskScheduler(
        config=config,
        publishing_engine=mock_publishing_engine,
        session_factory=session_factory
    )
    
    # Verify all components are created
    assert content_manager is not None
    assert group_manager is not None
    assert task_manager is not None
    assert task_scheduler is not None
    
    # Set dependencies
    task_scheduler.set_dependencies(
        account_manager=mock_account_manager,
        notification_manager=None,
        content_manager=content_manager,
        group_manager=group_manager,
        task_manager=task_manager
    )
    
    # Verify dependencies are set
    assert task_scheduler.account_manager == mock_account_manager
    assert task_scheduler.content_manager == content_manager
    assert task_scheduler.group_manager == group_manager
    assert task_scheduler.task_manager == task_manager


__all__ = [
    # Content Manager tests
    'test_content_manager_initialization',
    'test_create_content',
    'test_get_content',
    'test_get_contents_by_user',
    'test_update_content',
    'test_delete_content',
    
    # Group Manager tests
    'test_group_manager_initialization',
    'test_create_group',
    'test_get_group',
    'test_get_groups_by_user',
    'test_check_group_permissions',
    
    # Task Manager tests
    'test_task_manager_initialization',
    'test_create_task',
    'test_get_task',
    'test_get_tasks_by_user',
    'test_update_task_status',
    'test_delete_task',
    
    # Publishing Engine tests
    'test_publishing_engine_initialization',
    'test_publish_config_creation',
    'test_publish_result_creation',
    
    # Task Scheduler tests
    'test_task_scheduler_initialization',
    'test_schedule_task',
    'test_start_scheduler',
    'test_stop_scheduler',
    
    # Integration tests
    'test_publisher_module_integration',
]
