"""
Main bot file for Telegram Auto Publisher Pro
Initializes and runs the aiogram control bot
Integrates all handler modules
"""

import asyncio
import logging
from typing import Optional, Callable, Any, Dict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, User
from aiogram.enums import ParseMode

from config import config
from database.repositories import (
    UserRepository,
    AdministratorRepository,
    TelegramAccountRepository,
    SubscriptionRepository,
    RequiredChannelRepository,
)
from security.permissions import check_admin_access, check_user_access
from .messages import Messages, Language
from .keyboards import MainKeyboard, AccountKeyboard, AdminKeyboard

# Import all handlers
from .handlers.start import StartHandler
from .handlers.accounts import AccountsHandler
from .handlers.publishing import PublishingHandler
from .handlers.content import ContentHandler
from .handlers.groups import GroupsHandler
from .handlers.subscriptions import SubscriptionsHandler
from .handlers.admin import AdminHandler
from .handlers.reports import ReportsHandler

logger = logging.getLogger(__name__)


# Global bot instance
_bot: Optional[Bot] = None
_dispatcher: Optional[Dispatcher] = None


class BotManager:
    """
    Manages the aiogram bot instance and handlers.
    Integrates all specialized handler modules.
    """
    
    def __init__(
        self,
        config: any = None,
        account_manager: Any = None,
        publishing_engine: Any = None,
        task_scheduler: Any = None,
        notification_manager: Any = None,
        admin_dashboard: Any = None,
        channel_manager: Any = None,
        subscription_manager: Any = None,
        broadcast_manager: Any = None,
        user_manager: Any = None,
        admin_manager: Any = None,
        statistics_manager: Any = None,
        audit_manager: Any = None,
        encryption_manager: Any = None,
        content_manager: Any = None,
        group_manager: Any = None,
        task_manager: Any = None,
        report_generator: Any = None,
        session_factory: Callable = None
    ):
        """
        Initialize the bot manager.
        
        Args:
            config: Application configuration.
            account_manager: Account manager instance.
            publishing_engine: Publishing engine instance.
            task_scheduler: Task scheduler instance.
            notification_manager: Notification manager instance.
            admin_dashboard: Admin dashboard instance.
            channel_manager: Channel manager instance.
            subscription_manager: Subscription manager instance.
            broadcast_manager: Broadcast manager instance.
            user_manager: User manager instance.
            admin_manager: Admin manager instance.
            statistics_manager: Statistics manager instance.
            audit_manager: Audit manager instance.
            encryption_manager: Encryption manager instance.
            content_manager: Content manager instance.
            group_manager: Group manager instance.
            task_manager: Task manager instance.
            report_generator: Report generator instance.
            session_factory: Database session factory.
        """
        self.config = config or config
        self.account_manager = account_manager
        self.publishing_engine = publishing_engine
        self.task_scheduler = task_scheduler
        self.notification_manager = notification_manager
        self.admin_dashboard = admin_dashboard
        self.channel_manager = channel_manager
        self.subscription_manager = subscription_manager
        self.broadcast_manager = broadcast_manager
        self.user_manager = user_manager
        self.admin_manager = admin_manager
        self.statistics_manager = statistics_manager
        self.audit_manager = audit_manager
        self.encryption_manager = encryption_manager
        self.content_manager = content_manager
        self.group_manager = group_manager
        self.task_manager = task_manager
        self.report_generator = report_generator
        self.session_factory = session_factory
        
        # User language preferences
        self.user_languages: Dict[int, Language] = {}
        
        # Initialize bot and dispatcher
        self.bot = Bot(token=self.config.telegram.BOT_TOKEN)
        self.dispatcher = Dispatcher()
        
        # Initialize all handlers
        self._initialize_handlers()
        
        # Set up all handler registrations
        self._setup_handlers()
    
    def _initialize_handlers(self):
        """Initialize all handler instances."""
        # Start handler
        self.start_handler = StartHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            channel_manager=self.channel_manager,
            subscription_manager=self.subscription_manager,
            user_manager=self.user_manager,
            admin_manager=self.admin_manager
        )
        
        # Accounts handler
        self.accounts_handler = AccountsHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            account_manager=self.account_manager,
            user_manager=self.user_manager,
            notification_manager=self.notification_manager,
            channel_manager=self.channel_manager
        )
        
        # Publishing handler
        self.publishing_handler = PublishingHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            account_manager=self.account_manager,
            publishing_engine=self.publishing_engine,
            task_scheduler=self.task_scheduler,
            content_manager=self.content_manager,
            group_manager=self.group_manager,
            task_manager=self.task_manager,
            notification_manager=self.notification_manager
        )
        
        # Content handler
        self.content_handler = ContentHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            content_manager=self.content_manager,
            user_manager=self.user_manager,
            notification_manager=self.notification_manager
        )
        
        # Groups handler
        self.groups_handler = GroupsHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            account_manager=self.account_manager,
            group_manager=self.group_manager,
            notification_manager=self.notification_manager
        )
        
        # Subscriptions handler
        self.subscriptions_handler = SubscriptionsHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            subscription_manager=self.subscription_manager,
            user_manager=self.user_manager,
            notification_manager=self.notification_manager
        )
        
        # Admin handler
        self.admin_handler = AdminHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            admin_dashboard=self.admin_dashboard,
            user_manager=self.user_manager,
            admin_manager=self.admin_manager,
            channel_manager=self.channel_manager,
            subscription_manager=self.subscription_manager,
            broadcast_manager=self.broadcast_manager,
            statistics_manager=self.statistics_manager,
            audit_manager=self.audit_manager,
            notification_manager=self.notification_manager
        )
        
        # Reports handler
        self.reports_handler = ReportsHandler(
            bot=self.bot,
            session_factory=self.session_factory,
            report_generator=self.report_generator,
            statistics_manager=self.statistics_manager,
            user_manager=self.user_manager,
            notification_manager=self.notification_manager
        )
    
    def _setup_handlers(self):
        """Set up all bot handler registrations."""
        # ==================== COMMAND HANDLERS ====================
        
        # Start command
        self.dispatcher.message.register(
            self.start_handler.handle_start,
            CommandStart()
        )
        
        # Help command
        self.dispatcher.message.register(
            self.start_handler.handle_help,
            Command("help")
        )
        
        # Main menu command
        self.dispatcher.message.register(
            self.start_handler.handle_main_menu,
            Command("menu", "main")
        )
        
        # Language command
        self.dispatcher.message.register(
            self.start_handler.handle_language,
            Command("language", "lang")
        )
        
        # Accounts command
        self.dispatcher.message.register(
            self.accounts_handler.handle_accounts,
            Command("accounts")
        )
        
        # Publishing command
        self.dispatcher.message.register(
            self.publishing_handler.handle_publishing,
            Command("publishing", "publish")
        )
        
        # Content command
        self.dispatcher.message.register(
            self.content_handler.handle_content,
            Command("content")
        )
        
        # Groups command
        self.dispatcher.message.register(
            self.groups_handler.handle_groups,
            Command("groups")
        )
        
        # Subscriptions command
        self.dispatcher.message.register(
            self.subscriptions_handler.handle_subscriptions,
            Command("subscriptions", "sub")
        )
        
        # Admin command
        self.dispatcher.message.register(
            self.admin_handler.handle_admin,
            Command("admin")
        )
        
        # Reports command
        self.dispatcher.message.register(
            self.reports_handler.handle_reports,
            Command("reports")
        )
        
        # ==================== CALLBACK HANDLERS ====================
        
        # Start handler callbacks
        self.dispatcher.callback_query.register(
            self.start_handler.handle_language_callback,
            F.data.startswith("language_")
        )
        self.dispatcher.callback_query.register(
            self.start_handler.handle_back_callback,
            F.data == "back_to_main"
        )
        
        # Accounts handler callbacks
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_account_menu,
            F.data == "account_management"
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_add_account,
            F.data == "add_account"
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_my_accounts,
            F.data == "my_accounts"
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_phone_number,
            F.data == "phone_number"
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_verify_code,
            F.data.startswith("verify_code_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_verify_password,
            F.data.startswith("verify_password_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_account_list,
            F.data == "account_list"
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_select_account,
            F.data.startswith("select_account_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_account_settings,
            F.data.startswith("account_settings_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_connect_account,
            F.data.startswith("connect_account_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_disconnect_account,
            F.data.startswith("disconnect_account_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_confirm_disconnect,
            F.data.startswith("confirm_disconnect_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_delete_account,
            F.data.startswith("delete_account_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_confirm_delete,
            F.data.startswith("confirm_delete_")
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_back_to_accounts,
            F.data == "back_to_accounts"
        )
        self.dispatcher.callback_query.register(
            self.accounts_handler.handle_account_page,
            F.data.startswith("account_page_")
        )
        
        # Publishing handler callbacks
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_publishing_menu,
            F.data == "publishing_management"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_create_task,
            F.data == "create_task"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_select_account_for_task,
            F.data == "select_account_for_task"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_account_selected_for_task,
            F.data.startswith("account_selected_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_select_content_for_task,
            F.data == "select_content_for_task"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_content_selected_for_task,
            F.data.startswith("content_selected_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_select_groups_for_task,
            F.data == "select_groups_for_task"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_groups_selected_for_task,
            F.data.startswith("groups_selected_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_set_schedule_for_task,
            F.data == "set_schedule_for_task"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_schedule_now,
            F.data == "schedule_now"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_schedule_later,
            F.data == "schedule_later"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_my_tasks,
            F.data == "my_tasks"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_task_details,
            F.data.startswith("task_details_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_start_task,
            F.data.startswith("start_task_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_stop_task,
            F.data.startswith("stop_task_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_confirm_stop,
            F.data.startswith("confirm_stop_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_pause_task,
            F.data.startswith("pause_task_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_resume_task,
            F.data.startswith("resume_task_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_delete_task,
            F.data.startswith("delete_task_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_confirm_delete_task,
            F.data.startswith("confirm_delete_task_")
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_back_to_publishing,
            F.data == "back_to_publishing"
        )
        self.dispatcher.callback_query.register(
            self.publishing_handler.handle_task_page,
            F.data.startswith("task_page_")
        )
        
        # Content handler callbacks
        self.dispatcher.callback_query.register(
            self.content_handler.handle_content_menu,
            F.data == "content_management"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_add_content,
            F.data == "add_content"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_content_type,
            F.data == "content_type"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_content_type_selected,
            F.data.startswith("content_type_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_content_title,
            F.data == "content_title"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_text_content,
            F.data == "text_content"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_media_content,
            F.data == "media_content"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_my_content,
            F.data == "my_content"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_content_details,
            F.data.startswith("content_details_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_edit_content,
            F.data.startswith("edit_content_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_new_title,
            F.data.startswith("new_title_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_new_text_content,
            F.data.startswith("new_text_content_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_delete_content,
            F.data.startswith("delete_content_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_confirm_delete_content,
            F.data.startswith("confirm_delete_content_")
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_back_to_content,
            F.data == "back_to_content"
        )
        self.dispatcher.callback_query.register(
            self.content_handler.handle_content_page,
            F.data.startswith("content_page_")
        )
        
        # Groups handler callbacks
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_groups_menu,
            F.data == "group_management"
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_refresh_groups,
            F.data == "refresh_groups"
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_my_groups,
            F.data == "my_groups"
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_group_details,
            F.data.startswith("group_details_")
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_select_all_groups,
            F.data == "select_all_groups"
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_deselect_all_groups,
            F.data == "deselect_all_groups"
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_toggle_group,
            F.data.startswith("toggle_group_")
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_back_to_groups,
            F.data == "back_to_groups"
        )
        self.dispatcher.callback_query.register(
            self.groups_handler.handle_groups_page,
            F.data.startswith("groups_page_")
        )
        
        # Subscriptions handler callbacks
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_subscriptions_menu,
            F.data == "subscription_management"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_my_subscription,
            F.data == "my_subscription"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_subscription_plans,
            F.data == "subscription_plans"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_select_plan,
            F.data.startswith("select_plan_")
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_activate_plan,
            F.data.startswith("activate_plan_")
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_payment_method,
            F.data == "payment_method"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_renew_subscription,
            F.data == "renew_subscription"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_cancel_subscription,
            F.data == "cancel_subscription"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_confirm_cancel,
            F.data == "confirm_cancel_subscription"
        )
        self.dispatcher.callback_query.register(
            self.subscriptions_handler.handle_back_to_subscriptions,
            F.data == "back_to_subscriptions"
        )
        
        # Admin handler callbacks
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_admin_dashboard,
            F.data == "admin_dashboard"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_dashboard,
            F.data == "dashboard"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_user_management,
            F.data == "user_management"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_view_users,
            F.data == "view_users"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_search_users,
            F.data == "search_users"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_user_details,
            F.data.startswith("user_details_")
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_block_user,
            F.data.startswith("block_user_")
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_confirm_block,
            F.data.startswith("confirm_block_")
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_unblock_user,
            F.data.startswith("unblock_user_")
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_confirm_unblock,
            F.data.startswith("confirm_unblock_")
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_channel_management,
            F.data == "channel_management"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_broadcast_management,
            F.data == "broadcast_management"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_settings,
            F.data == "settings"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_audit_logs,
            F.data == "audit_logs"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_back_to_admin,
            F.data == "back_to_admin"
        )
        self.dispatcher.callback_query.register(
            self.admin_handler.handle_user_page,
            F.data.startswith("user_page_")
        )
        
        # Reports handler callbacks
        self.dispatcher.callback_query.register(
            self.reports_handler.handle_reports_menu,
            F.data == "reports"
        )
        self.dispatcher.callback_query.register(
            self.reports_handler.handle_publishing_report,
            F.data == "publishing_report"
        )
        self.dispatcher.callback_query.register(
            self.reports_handler.handle_task_history,
            F.data == "task_history"
        )
        self.dispatcher.callback_query.register(
            self.reports_handler.handle_statistics,
            F.data == "statistics"
        )
        self.dispatcher.callback_query.register(
            self.reports_handler.handle_export_report,
            F.data.startswith("export_report_")
        )
        self.dispatcher.callback_query.register(
            self.reports_handler.handle_back_to_reports,
            F.data == "back_to_reports"
        )
        
        # Main menu and navigation callbacks
        self.dispatcher.callback_query.register(
            self._handle_main_menu_callback,
            F.data == "main_menu"
        )
        self.dispatcher.callback_query.register(
            self._handle_publishing_management_callback,
            F.data == "publishing_management"
        )
        self.dispatcher.callback_query.register(
            self._handle_content_management_callback,
            F.data == "content_management"
        )
        self.dispatcher.callback_query.register(
            self._handle_group_management_callback,
            F.data == "group_management"
        )
        self.dispatcher.callback_query.register(
            self._handle_private_messaging_callback,
            F.data == "private_messaging"
        )
        self.dispatcher.callback_query.register(
            self._handle_application_settings_callback,
            F.data == "application_settings"
        )
        self.dispatcher.callback_query.register(
            self._handle_help_support_callback,
            F.data == "help_support"
        )
        
        # Generic back button handler
        self.dispatcher.callback_query.register(
            self._handle_back_callback,
            F.data == "back"
        )
        
        # Channel subscription verification
        self.dispatcher.callback_query.register(
            self._handle_verify_subscription,
            F.data == "verify_subscription"
        )
        
        # Handle all other messages
        self.dispatcher.message.register(
            self._handle_message
        )
    
    # ==================== MAIN MENU AND NAVIGATION ====================
    
    async def _handle_main_menu_callback(self, callback: CallbackQuery):
        """Handle main menu callback."""
        try:
            user_id = callback.from_user.id
            await self._show_main_menu(callback.message, user_id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling main menu callback: {e}")
    
    async def _handle_publishing_management_callback(self, callback: CallbackQuery):
        """Handle publishing management callback."""
        try:
            user_id = callback.from_user.id
            await self.publishing_handler.show_publishing_menu(callback.message, user_id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling publishing management callback: {e}")
    
    async def _handle_content_management_callback(self, callback: CallbackQuery):
        """Handle content management callback."""
        try:
            user_id = callback.from_user.id
            await self.content_handler.show_content_menu(callback.message, user_id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling content management callback: {e}")
    
    async def _handle_group_management_callback(self, callback: CallbackQuery):
        """Handle group management callback."""
        try:
            user_id = callback.from_user.id
            await self.groups_handler.show_groups_menu(callback.message, user_id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling group management callback: {e}")
    
    async def _handle_private_messaging_callback(self, callback: CallbackQuery):
        """Handle private messaging callback."""
        try:
            user_id = callback.from_user.id
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            await callback.message.edit_text(
                messages.get_private_messaging_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_back_keyboard(user_id)
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling private messaging callback: {e}")
    
    async def _handle_application_settings_callback(self, callback: CallbackQuery):
        """Handle application settings callback."""
        try:
            user_id = callback.from_user.id
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            await callback.message.edit_text(
                messages.get_settings_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_back_keyboard(user_id)
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling application settings callback: {e}")
    
    async def _handle_help_support_callback(self, callback: CallbackQuery):
        """Handle help and support callback."""
        try:
            user_id = callback.from_user.id
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            await callback.message.edit_text(
                messages.get_help_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_back_keyboard(user_id)
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling help support callback: {e}")
    
    async def _handle_back_callback(self, callback: CallbackQuery):
        """Handle back button callback."""
        try:
            user_id = callback.from_user.id
            await self._show_main_menu(callback.message, user_id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling back callback: {e}")
    
    async def _handle_verify_subscription(self, callback: CallbackQuery):
        """Handle verify subscription callback."""
        try:
            user_id = callback.from_user.id
            await self._verify_channel_subscription(callback.message, user_id)
            await callback.answer()
        except Exception as e:
            logger.error(f"Error handling verify subscription: {e}")
    
    async def _handle_message(self, message: Message):
        """Handle all other messages."""
        # For now, just ignore or provide help
        pass
    
    # ==================== CHANNEL SUBSCRIPTION ====================
    
    async def _check_channel_subscription(self, message: Message, user_id: int) -> bool:
        """Check if user has subscribed to required channels."""
        try:
            if not self.channel_manager:
                return True
            
            async with self.session_factory() as session:
                channel_repo = RequiredChannelRepository(session)
                required_channels = await channel_repo.get_active_required_channels()
            
            if not required_channels:
                return True
            
            # Check if all channels are joined
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            # Get user info for verification
            user = message.from_user
            
            # Check subscription status
            is_subscribed = await self.channel_manager.check_user_subscription(user_id, user)
            
            if is_subscribed:
                return True
            
            # Show subscription message
            channel_list = [
                {"username": ch.channel_username, "channel_id": ch.channel_id}
                for ch in required_channels
            ]
            
            await message.answer(
                messages.get_channel_subscription_required_message(channel_list),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_channel_subscription_keyboard(required_channels, user_id)
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking channel subscription: {e}")
            return True  # Allow access on error
    
    async def _verify_channel_subscription(self, message: Message, user_id: int):
        """Verify channel subscription."""
        try:
            if not self.channel_manager:
                language = self.user_languages.get(user_id, Language.ENGLISH)
                messages = Messages(language)
                await message.edit_text(
                    messages.get_channel_subscription_verified_message(),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._get_main_menu_keyboard(user_id)
                )
                return
            
            user = message.from_user if hasattr(message, 'from_user') else None
            
            # Verify subscription
            is_subscribed = await self.channel_manager.check_user_subscription(user_id, user)
            
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            if is_subscribed:
                await message.edit_text(
                    messages.get_channel_subscription_verified_message(),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._get_main_menu_keyboard(user_id)
                )
            else:
                # Still not subscribed, show error
                async with self.session_factory() as session:
                    channel_repo = RequiredChannelRepository(session)
                    required_channels = await channel_repo.get_active_required_channels()
                
                channel_list = [
                    {"username": ch.channel_username, "channel_id": ch.channel_id}
                    for ch in required_channels
                ]
                
                await message.edit_text(
                    messages.get_channel_subscription_failed_message(channel_list),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._get_channel_subscription_keyboard(required_channels, user_id)
                )
                
        except Exception as e:
            logger.error(f"Error verifying channel subscription: {e}")
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            await message.answer(messages.get_error_message("Verification failed. Please try again."))
    
    # ==================== MENU DISPLAY METHODS ====================
    
    async def _show_main_menu(self, message: Message, user_id: int):
        """Show the main menu."""
        language = self.user_languages.get(user_id, Language.ENGLISH)
        messages = Messages(language)
        
        try:
            if message:
                await message.edit_text(
                    messages.get_main_menu_message(),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._get_main_menu_keyboard(user_id)
                )
        except:
            await message.answer(
                messages.get_main_menu_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_main_menu_keyboard(user_id)
            )
    
    # ==================== KEYBOARD HELPERS ====================
    
    def _get_main_menu_keyboard(self, user_id: int):
        """Get the main menu keyboard based on user language."""
        language = self.user_languages.get(user_id, Language.ENGLISH)
        
        if language == Language.ARABIC:
            return MainKeyboard.get_main_menu_arabic()
        else:
            return MainKeyboard.get_main_menu()
    
    def _get_back_keyboard(self, user_id: int):
        """Get the back keyboard."""
        language = self.user_languages.get(user_id, Language.ENGLISH)
        
        if language == Language.ARABIC:
            return MainKeyboard.get_back_button_arabic()
        else:
            return MainKeyboard.get_back_button()
    
    def _get_channel_subscription_keyboard(self, channels: list, user_id: int):
        """Get the channel subscription keyboard."""
        language = self.user_languages.get(user_id, Language.ENGLISH)
        
        if language == Language.ARABIC:
            return AdminKeyboard.get_channel_subscription_keyboard_arabic(channels)
        else:
            return AdminKeyboard.get_channel_subscription_keyboard(channels)


# Global bot manager instance
_bot_manager: Optional[BotManager] = None


async def create_bot(
    config: any = None,
    account_manager: Any = None,
    publishing_engine: Any = None,
    task_scheduler: Any = None,
    notification_manager: Any = None,
    admin_dashboard: Any = None,
    channel_manager: Any = None,
    subscription_manager: Any = None,
    broadcast_manager: Any = None,
    user_manager: Any = None,
    admin_manager: Any = None,
    statistics_manager: Any = None,
    audit_manager: Any = None,
    encryption_manager: Any = None,
    content_manager: Any = None,
    group_manager: Any = None,
    task_manager: Any = None,
    report_generator: Any = None,
    session_factory: Callable = None
) -> BotManager:
    """
    Create and configure the bot.
    
    Args:
        All the required managers and configuration.
        
    Returns:
        Configured BotManager instance.
    """
    global _bot_manager
    
    _bot_manager = BotManager(
        config=config,
        account_manager=account_manager,
        publishing_engine=publishing_engine,
        task_scheduler=task_scheduler,
        notification_manager=notification_manager,
        admin_dashboard=admin_dashboard,
        channel_manager=channel_manager,
        subscription_manager=subscription_manager,
        broadcast_manager=broadcast_manager,
        user_manager=user_manager,
        admin_manager=admin_manager,
        statistics_manager=statistics_manager,
        audit_manager=audit_manager,
        encryption_manager=encryption_manager,
        content_manager=content_manager,
        group_manager=group_manager,
        task_manager=task_manager,
        report_generator=report_generator,
        session_factory=session_factory
    )
    
    return _bot_manager


async def start_bot(bot_manager: BotManager = None):
    """
    Start the bot.
    
    Args:
        bot_manager: Optional bot manager instance. If None, uses global instance.
    """
    global _bot_manager
    
    if bot_manager is None:
        bot_manager = _bot_manager
    
    if bot_manager is None:
        raise ValueError("Bot manager not initialized. Call create_bot() first.")
    
    logger.info("Starting bot...")
    
    try:
        await bot_manager.dispatcher.start_polling(
            bot_manager.bot,
            skip_updates=True
        )
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


async def stop_bot(bot_manager: BotManager = None):
    """
    Stop the bot.
    
    Args:
        bot_manager: Optional bot manager instance. If None, uses global instance.
    """
    global _bot_manager
    
    if bot_manager is None:
        bot_manager = _bot_manager
    
    if bot_manager is None:
        return
    
    logger.info("Stopping bot...")
    
    try:
        await bot_manager.bot.session.close()
        logger.info("Bot stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")


def get_bot() -> Optional[Bot]:
    """Get the bot instance."""
    global _bot_manager
    return _bot_manager.bot if _bot_manager else None


__all__ = [
    'BotManager',
    'create_bot',
    'start_bot',
    'stop_bot',
    'get_bot',
]
