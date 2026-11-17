"""
Bot module tests for Telegram Auto Publisher Pro
Tests for BotManager, handlers, keyboards, and messages
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
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
    Subscription,
    RequiredChannel,
    UserStatus,
    AdminRole,
    ContentType,
    GroupType,
    TaskStatus,
    TaskType,
    SubscriptionType,
    SubscriptionStatus,
)
from bot.main import BotManager, create_bot, start_bot, stop_bot, get_bot
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, AccountKeyboard, AdminKeyboard
from bot.handlers.start import StartHandler
from bot.handlers.accounts import AccountsHandler
from bot.handlers.publishing import PublishingHandler
from bot.handlers.content import ContentHandler
from bot.handlers.groups import GroupHandler
from bot.handlers.subscriptions import SubscriptionsHandler
from bot.handlers.admin import AdminHandler
from bot.handlers.reports import ReportHandler


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


# ==================== MESSAGES TESTS ====================


@pytest.mark.asyncio
async def test_messages_english():
    """Test English messages."""
    messages = Messages(Language.ENGLISH)
    
    # Test various message getters
    welcome = messages.get_welcome_message()
    assert "Welcome" in welcome or "welcome" in welcome.lower()
    
    main_menu = messages.get_main_menu_message()
    assert "Main Menu" in main_menu or "menu" in main_menu.lower()
    
    help_msg = messages.get_help_message()
    assert "Help" in help_msg or "help" in help_msg.lower()
    
    account_menu = messages.get_account_menu_message()
    assert "Account" in account_menu or "account" in account_menu.lower()
    
    publishing_menu = messages.get_publishing_menu_message()
    assert "Publishing" in publishing_menu or "publishing" in publishing_menu.lower()
    
    content_menu = messages.get_content_menu_message()
    assert "Content" in content_menu or "content" in content_menu.lower()
    
    group_menu = messages.get_group_menu_message()
    assert "Group" in group_menu or "group" in group_menu.lower()
    
    subscription_menu = messages.get_subscription_menu_message()
    assert "Subscription" in subscription_menu or "subscription" in subscription_menu.lower()
    
    settings = messages.get_settings_message()
    assert "Settings" in settings or "settings" in settings.lower()
    
    permission_denied = messages.get_permission_denied_message()
    assert "Permission" in permission_denied or "permission" in permission_denied.lower() or "access" in permission_denied.lower()


@pytest.mark.asyncio
async def test_messages_arabic():
    """Test Arabic messages."""
    messages = Messages(Language.ARABIC)
    
    # Test various message getters
    welcome = messages.get_welcome_message()
    assert welcome  # Should have some content
    
    main_menu = messages.get_main_menu_message()
    assert main_menu  # Should have some content
    
    help_msg = messages.get_help_message()
    assert help_msg  # Should have some content


@pytest.mark.asyncio
async def test_messages_get_message():
    """Test get_message method."""
    messages_en = Messages(Language.ENGLISH)
    messages_ar = Messages(Language.ARABIC)
    
    # Test with known message keys
    for key in ["welcome", "main_menu", "help", "account_menu"]:
        msg_en = messages_en.get_message(key)
        msg_ar = messages_ar.get_message(key)
        assert msg_en  # Should have some content
        assert msg_ar  # Should have some content


@pytest.mark.asyncio
async def test_messages_channel_subscription():
    """Test channel subscription messages."""
    messages = Messages(Language.ENGLISH)
    
    channels = [
        {"username": "channel1", "channel_id": -1001},
        {"username": "channel2", "channel_id": -1002}
    ]
    
    required_msg = messages.get_channel_subscription_required_message(channels)
    assert "channel1" in required_msg
    assert "channel2" in required_msg
    
    verified_msg = messages.get_channel_subscription_verified_message()
    assert verified_msg
    
    failed_msg = messages.get_channel_subscription_failed_message(channels)
    assert "channel1" in failed_msg
    assert "channel2" in failed_msg


# ==================== KEYBOARDS TESTS ====================


@pytest.mark.asyncio
async def test_main_keyboard():
    """Test MainKeyboard."""
    keyboard = MainKeyboard()
    
    # Test main menu
    main_menu = keyboard.get_main_menu()
    assert main_menu is not None
    assert hasattr(main_menu, 'inline_keyboard')
    
    # Test main menu Arabic
    main_menu_ar = keyboard.get_main_menu_arabic()
    assert main_menu_ar is not None
    assert hasattr(main_menu_ar, 'inline_keyboard')
    
    # Test back button
    back_button = keyboard.get_back_button()
    assert back_button is not None
    assert hasattr(back_button, 'inline_keyboard')
    
    # Test back button Arabic
    back_button_ar = keyboard.get_back_button_arabic()
    assert back_button_ar is not None
    assert hasattr(back_button_ar, 'inline_keyboard')
    
    # Test language selection
    lang_keyboard = keyboard.get_language_selection()
    assert lang_keyboard is not None
    assert hasattr(lang_keyboard, 'inline_keyboard')


@pytest.mark.asyncio
async def test_account_keyboard():
    """Test AccountKeyboard."""
    keyboard = AccountKeyboard(Language.ENGLISH)
    
    # Test account menu
    account_menu = keyboard.get_account_menu()
    assert account_menu is not None
    assert hasattr(account_menu, 'inline_keyboard')
    
    # Test account menu Arabic
    account_menu_ar = keyboard.get_account_menu_arabic()
    assert account_menu_ar is not None
    assert hasattr(account_menu_ar, 'inline_keyboard')
    
    # Test add account keyboard
    add_account = keyboard.get_add_account_keyboard()
    assert add_account is not None
    assert hasattr(add_account, 'inline_keyboard')
    
    # Test account list keyboard
    accounts = [
        {"id": 1, "phone_number": "+123456789", "account_name": "Account 1", "is_connected": True},
        {"id": 2, "phone_number": "+987654321", "account_name": "Account 2", "is_connected": False}
    ]
    account_list = keyboard.get_account_list_keyboard(accounts, page=1, per_page=5)
    assert account_list is not None
    assert hasattr(account_list, 'inline_keyboard')


@pytest.mark.asyncio
async def test_admin_keyboard():
    """Test AdminKeyboard."""
    keyboard = AdminKeyboard(Language.ENGLISH)
    
    # Test admin main menu
    admin_menu = keyboard.get_admin_main_menu()
    assert admin_menu is not None
    assert hasattr(admin_menu, 'inline_keyboard')
    
    # Test admin main menu Arabic
    admin_menu_ar = keyboard.get_admin_main_menu_arabic()
    assert admin_menu_ar is not None
    assert hasattr(admin_menu_ar, 'inline_keyboard')
    
    # Test dashboard keyboard
    dashboard = keyboard.get_dashboard_keyboard()
    assert dashboard is not None
    assert hasattr(dashboard, 'inline_keyboard')
    
    # Test user management keyboard
    user_mgmt = keyboard.get_user_management_keyboard()
    assert user_mgmt is not None
    assert hasattr(user_mgmt, 'inline_keyboard')
    
    # Test channel subscription keyboard
    channels = [
        {"username": "channel1", "channel_id": -1001},
        {"username": "channel2", "channel_id": -1002}
    ]
    channel_sub = keyboard.get_channel_subscription_keyboard(channels)
    assert channel_sub is not None
    assert hasattr(channel_sub, 'inline_keyboard')
    
    # Test channel subscription keyboard Arabic
    channel_sub_ar = keyboard.get_channel_subscription_keyboard_arabic(channels)
    assert channel_sub_ar is not None
    assert hasattr(channel_sub_ar, 'inline_keyboard')


# ==================== START HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_start_handler_initialization():
    """Test StartHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_channel_manager = MagicMock()
    mock_subscription_manager = MagicMock()
    mock_user_manager = MagicMock()
    mock_admin_manager = MagicMock()
    
    start_handler = StartHandler(
        bot=None,
        session_factory=session_factory,
        channel_manager=mock_channel_manager,
        subscription_manager=mock_subscription_manager,
        user_manager=mock_user_manager,
        admin_manager=mock_admin_manager
    )
    
    assert start_handler is not None
    assert start_handler.session_factory == session_factory
    assert start_handler.channel_manager == mock_channel_manager


@pytest.mark.asyncio
async def test_start_handler_handle_start():
    """Test StartHandler handle_start method."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_channel_manager = MagicMock()
    mock_channel_manager.check_user_subscription = AsyncMock(return_value=True)
    
    start_handler = StartHandler(
        bot=None,
        session_factory=session_factory,
        channel_manager=mock_channel_manager
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User",
        language_code="en"
    )
    mock_message.answer = AsyncMock()
    
    async with session_factory() as session:
        # Clear any existing users
        await session.execute("DELETE FROM users")
        await session.commit()
        
        # Call handler
        await start_handler.handle_start(mock_message)
        
        # Verify message was sent
        mock_message.answer.assert_called_once()
        
        # Verify user was created
        from database.repositories import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_user(123456789)
        assert user is not None
        assert user.username == "test_user"


@pytest.mark.asyncio
async def test_start_handler_handle_help():
    """Test StartHandler handle_help method."""
    session_factory = get_session_factory()
    
    start_handler = StartHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await start_handler.handle_help(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_start_handler_handle_language():
    """Test StartHandler handle_language method."""
    session_factory = get_session_factory()
    
    start_handler = StartHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.answer = AsyncMock()
    
    await start_handler.handle_language(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_start_handler_language_callback():
    """Test StartHandler language callback."""
    session_factory = get_session_factory()
    
    start_handler = StartHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock callback
    mock_callback = MagicMock()
    mock_callback.data = "language_en"
    mock_callback.from_user.id = 123456789
    mock_callback.message = MagicMock()
    mock_callback.message.edit_text = AsyncMock()
    
    await start_handler.handle_language_callback(mock_callback)
    
    # Verify message was edited
    mock_callback.message.edit_text.assert_called_once()


# ==================== ACCOUNTS HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_accounts_handler_initialization():
    """Test AccountsHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_account_manager = MagicMock()
    mock_user_manager = MagicMock()
    mock_notification_manager = MagicMock()
    mock_channel_manager = MagicMock()
    
    accounts_handler = AccountsHandler(
        bot=None,
        session_factory=session_factory,
        account_manager=mock_account_manager,
        user_manager=mock_user_manager,
        notification_manager=mock_notification_manager,
        channel_manager=mock_channel_manager
    )
    
    assert accounts_handler is not None
    assert accounts_handler.session_factory == session_factory
    assert accounts_handler.account_manager == mock_account_manager


@pytest.mark.asyncio
async def test_accounts_handler_handle_accounts():
    """Test AccountsHandler handle_accounts method."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_account_manager = MagicMock()
    mock_account_manager.get_accounts_by_user = AsyncMock(return_value=[])
    
    accounts_handler = AccountsHandler(
        bot=None,
        session_factory=session_factory,
        account_manager=mock_account_manager
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await accounts_handler.handle_accounts(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_accounts_handler_show_account_menu():
    """Test AccountsHandler show_account_menu method."""
    session_factory = get_session_factory()
    
    accounts_handler = AccountsHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    await accounts_handler.show_account_menu(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== PUBLISHING HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_publishing_handler_initialization():
    """Test PublishingHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_account_manager = MagicMock()
    mock_publishing_engine = MagicMock()
    mock_task_scheduler = MagicMock()
    mock_content_manager = MagicMock()
    mock_group_manager = MagicMock()
    mock_task_manager = MagicMock()
    mock_notification_manager = MagicMock()
    
    publishing_handler = PublishingHandler(
        bot=None,
        session_factory=session_factory,
        account_manager=mock_account_manager,
        publishing_engine=mock_publishing_engine,
        task_scheduler=mock_task_scheduler,
        content_manager=mock_content_manager,
        group_manager=mock_group_manager,
        task_manager=mock_task_manager,
        notification_manager=mock_notification_manager
    )
    
    assert publishing_handler is not None
    assert publishing_handler.session_factory == session_factory
    assert publishing_handler.publishing_engine == mock_publishing_engine


@pytest.mark.asyncio
async def test_publishing_handler_handle_publishing():
    """Test PublishingHandler handle_publishing method."""
    session_factory = get_session_factory()
    
    publishing_handler = PublishingHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await publishing_handler.handle_publishing(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_publishing_handler_show_publishing_menu():
    """Test PublishingHandler show_publishing_menu method."""
    session_factory = get_session_factory()
    
    publishing_handler = PublishingHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    await publishing_handler.show_publishing_menu(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== CONTENT HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_content_handler_initialization():
    """Test ContentHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_content_manager = MagicMock()
    mock_user_manager = MagicMock()
    mock_notification_manager = MagicMock()
    
    content_handler = ContentHandler(
        bot=None,
        session_factory=session_factory,
        content_manager=mock_content_manager,
        user_manager=mock_user_manager,
        notification_manager=mock_notification_manager
    )
    
    assert content_handler is not None
    assert content_handler.session_factory == session_factory
    assert content_handler.content_manager == mock_content_manager


@pytest.mark.asyncio
async def test_content_handler_handle_content():
    """Test ContentHandler handle_content method."""
    session_factory = get_session_factory()
    
    content_handler = ContentHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await content_handler.handle_content(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_content_handler_show_content_menu():
    """Test ContentHandler show_content_menu method."""
    session_factory = get_session_factory()
    
    content_handler = ContentHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    await content_handler.show_content_menu(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== GROUPS HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_groups_handler_initialization():
    """Test GroupHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_account_manager = MagicMock()
    mock_group_manager = MagicMock()
    mock_notification_manager = MagicMock()
    
    groups_handler = GroupHandler(
        bot=None,
        session_factory=session_factory,
        account_manager=mock_account_manager,
        group_manager=mock_group_manager,
        notification_manager=mock_notification_manager
    )
    
    assert groups_handler is not None
    assert groups_handler.session_factory == session_factory
    assert groups_handler.group_manager == mock_group_manager


@pytest.mark.asyncio
async def test_groups_handler_handle_groups():
    """Test GroupHandler handle_groups method."""
    session_factory = get_session_factory()
    
    groups_handler = GroupHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await groups_handler.handle_groups(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_groups_handler_show_groups_menu():
    """Test GroupHandler show_groups_menu method."""
    session_factory = get_session_factory()
    
    groups_handler = GroupHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    await groups_handler.show_groups_menu(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== SUBSCRIPTIONS HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_subscriptions_handler_initialization():
    """Test SubscriptionsHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_subscription_manager = MagicMock()
    mock_user_manager = MagicMock()
    mock_notification_manager = MagicMock()
    
    subscriptions_handler = SubscriptionsHandler(
        bot=None,
        session_factory=session_factory,
        subscription_manager=mock_subscription_manager,
        user_manager=mock_user_manager,
        notification_manager=mock_notification_manager
    )
    
    assert subscriptions_handler is not None
    assert subscriptions_handler.session_factory == session_factory
    assert subscriptions_handler.subscription_manager == mock_subscription_manager


@pytest.mark.asyncio
async def test_subscriptions_handler_handle_subscriptions():
    """Test SubscriptionsHandler handle_subscriptions method."""
    session_factory = get_session_factory()
    
    subscriptions_handler = SubscriptionsHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await subscriptions_handler.handle_subscriptions(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_subscriptions_handler_show_subscriptions_menu():
    """Test SubscriptionsHandler show_subscriptions_menu method."""
    session_factory = get_session_factory()
    
    subscriptions_handler = SubscriptionsHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    await subscriptions_handler.show_subscriptions_menu(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== ADMIN HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_admin_handler_initialization():
    """Test AdminHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_admin_dashboard = MagicMock()
    mock_user_manager = MagicMock()
    mock_admin_manager = MagicMock()
    mock_channel_manager = MagicMock()
    mock_subscription_manager = MagicMock()
    mock_broadcast_manager = MagicMock()
    mock_statistics_manager = MagicMock()
    mock_audit_manager = MagicMock()
    mock_notification_manager = MagicMock()
    
    admin_handler = AdminHandler(
        bot=None,
        session_factory=session_factory,
        admin_dashboard=mock_admin_dashboard,
        user_manager=mock_user_manager,
        admin_manager=mock_admin_manager,
        channel_manager=mock_channel_manager,
        subscription_manager=mock_subscription_manager,
        broadcast_manager=mock_broadcast_manager,
        statistics_manager=mock_statistics_manager,
        audit_manager=mock_audit_manager,
        notification_manager=mock_notification_manager
    )
    
    assert admin_handler is not None
    assert admin_handler.session_factory == session_factory
    assert admin_handler.admin_dashboard == mock_admin_dashboard


@pytest.mark.asyncio
async def test_admin_handler_handle_admin():
    """Test AdminHandler handle_admin method."""
    session_factory = get_session_factory()
    
    admin_handler = AdminHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await admin_handler.handle_admin(mock_message)
    
    # Verify message was sent (should show permission denied for non-admin)
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_admin_handler_show_admin_dashboard():
    """Test AdminHandler show_admin_dashboard method."""
    session_factory = get_session_factory()
    
    # Mock admin dashboard
    mock_admin_dashboard = MagicMock()
    mock_admin_dashboard.get_dashboard_stats = AsyncMock(return_value={})
    
    admin_handler = AdminHandler(
        bot=None,
        session_factory=session_factory,
        admin_dashboard=mock_admin_dashboard
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    # Mock check_admin_access to return True
    with patch('bot.handlers.admin.check_admin_access', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        await admin_handler.show_admin_dashboard(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== REPORTS HANDLER TESTS ====================


@pytest.mark.asyncio
async def test_reports_handler_initialization():
    """Test ReportHandler initialization."""
    session_factory = get_session_factory()
    
    # Mock dependencies
    mock_report_generator = MagicMock()
    mock_statistics_manager = MagicMock()
    mock_user_manager = MagicMock()
    mock_notification_manager = MagicMock()
    
    reports_handler = ReportHandler(
        bot=None,
        session_factory=session_factory,
        report_generator=mock_report_generator,
        statistics_manager=mock_statistics_manager,
        user_manager=mock_user_manager,
        notification_manager=mock_notification_manager
    )
    
    assert reports_handler is not None
    assert reports_handler.session_factory == session_factory
    assert reports_handler.report_generator == mock_report_generator


@pytest.mark.asyncio
async def test_reports_handler_handle_reports():
    """Test ReportHandler handle_reports method."""
    session_factory = get_session_factory()
    
    reports_handler = ReportHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.from_user = User(
        id=123456789,
        username="test_user",
        first_name="Test"
    )
    mock_message.answer = AsyncMock()
    
    await reports_handler.handle_reports(mock_message)
    
    # Verify message was sent
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_reports_handler_show_reports_menu():
    """Test ReportHandler show_reports_menu method."""
    session_factory = get_session_factory()
    
    reports_handler = ReportHandler(
        bot=None,
        session_factory=session_factory
    )
    
    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    
    await reports_handler.show_reports_menu(mock_message, 123456789)
    
    # Verify message was edited
    mock_message.edit_text.assert_called_once()


# ==================== BOT MANAGER TESTS ====================


@pytest.mark.asyncio
async def test_bot_manager_initialization():
    """Test BotManager initialization."""
    session_factory = get_session_factory()
    
    # Mock all dependencies
    mock_config = MagicMock()
    mock_config.telegram.BOT_TOKEN = "test_token"
    
    bot_manager = BotManager(
        config=mock_config,
        session_factory=session_factory
    )
    
    assert bot_manager is not None
    assert bot_manager.config == mock_config
    assert bot_manager.session_factory == session_factory
    assert bot_manager.bot is not None
    assert bot_manager.dispatcher is not None


@pytest.mark.asyncio
async def test_create_bot():
    """Test create_bot function."""
    session_factory = get_session_factory()
    
    # Mock config
    mock_config = MagicMock()
    mock_config.telegram.BOT_TOKEN = "test_token"
    
    bot_manager = await create_bot(
        config=mock_config,
        session_factory=session_factory
    )
    
    assert bot_manager is not None
    assert bot_manager.bot is not None


@pytest.mark.asyncio
async def test_get_bot():
    """Test get_bot function."""
    # Initially should be None
    bot = get_bot()
    assert bot is None
    
    # Create a bot
    session_factory = get_session_factory()
    mock_config = MagicMock()
    mock_config.telegram.BOT_TOKEN = "test_token"
    
    await create_bot(
        config=mock_config,
        session_factory=session_factory
    )
    
    # Now should have a bot
    bot = get_bot()
    assert bot is not None


# ==================== INTEGRATION TESTS ====================


@pytest.mark.asyncio
async def test_bot_module_integration():
    """Test integration of bot module components."""
    session_factory = get_session_factory()
    
    # Create all handlers
    start_handler = StartHandler(session_factory=session_factory)
    accounts_handler = AccountsHandler(session_factory=session_factory)
    publishing_handler = PublishingHandler(session_factory=session_factory)
    content_handler = ContentHandler(session_factory=session_factory)
    groups_handler = GroupHandler(session_factory=session_factory)
    subscriptions_handler = SubscriptionsHandler(session_factory=session_factory)
    admin_handler = AdminHandler(session_factory=session_factory)
    reports_handler = ReportHandler(session_factory=session_factory)
    
    # Verify all handlers are created
    assert start_handler is not None
    assert accounts_handler is not None
    assert publishing_handler is not None
    assert content_handler is not None
    assert groups_handler is not None
    assert subscriptions_handler is not None
    assert admin_handler is not None
    assert reports_handler is not None
    
    # Create bot manager
    mock_config = MagicMock()
    mock_config.telegram.BOT_TOKEN = "test_token"
    
    bot_manager = BotManager(
        config=mock_config,
        session_factory=session_factory
    )
    
    # Verify bot manager has all handlers
    assert bot_manager.start_handler is not None
    assert bot_manager.accounts_handler is not None
    assert bot_manager.publishing_handler is not None
    assert bot_manager.content_handler is not None
    assert bot_manager.groups_handler is not None
    assert bot_manager.subscriptions_handler is not None
    assert bot_manager.admin_handler is not None
    assert bot_manager.reports_handler is not None


__all__ = [
    # Messages tests
    'test_messages_english',
    'test_messages_arabic',
    'test_messages_get_message',
    'test_messages_channel_subscription',
    
    # Keyboards tests
    'test_main_keyboard',
    'test_account_keyboard',
    'test_admin_keyboard',
    
    # Start Handler tests
    'test_start_handler_initialization',
    'test_start_handler_handle_start',
    'test_start_handler_handle_help',
    'test_start_handler_handle_language',
    'test_start_handler_language_callback',
    
    # Accounts Handler tests
    'test_accounts_handler_initialization',
    'test_accounts_handler_handle_accounts',
    'test_accounts_handler_show_account_menu',
    
    # Publishing Handler tests
    'test_publishing_handler_initialization',
    'test_publishing_handler_handle_publishing',
    'test_publishing_handler_show_publishing_menu',
    
    # Content Handler tests
    'test_content_handler_initialization',
    'test_content_handler_handle_content',
    'test_content_handler_show_content_menu',
    
    # Groups Handler tests
    'test_groups_handler_initialization',
    'test_groups_handler_handle_groups',
    'test_groups_handler_show_groups_menu',
    
    # Subscriptions Handler tests
    'test_subscriptions_handler_initialization',
    'test_subscriptions_handler_handle_subscriptions',
    'test_subscriptions_handler_show_subscriptions_menu',
    
    # Admin Handler tests
    'test_admin_handler_initialization',
    'test_admin_handler_handle_admin',
    'test_admin_handler_show_admin_dashboard',
    
    # Reports Handler tests
    'test_reports_handler_initialization',
    'test_reports_handler_handle_reports',
    'test_reports_handler_show_reports_menu',
    
    # Bot Manager tests
    'test_bot_manager_initialization',
    'test_create_bot',
    'test_get_bot',
    
    # Integration tests
    'test_bot_module_integration',
]
