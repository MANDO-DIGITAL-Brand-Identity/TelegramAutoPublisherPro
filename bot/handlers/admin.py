"""
Admin handler for Telegram Auto Publisher Pro
Handles administrator operations
"""

import logging
from typing import Optional, Any, Callable

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database.repositories import (
    UserRepository,
    AdministratorRepository,
    TelegramAccountRepository,
    SubscriptionRepository,
)
from security.permissions import check_admin_access, check_super_admin_access
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, AdminKeyboard
from config import config

logger = logging.getLogger(__name__)


class AdminHandler:
    """
    Handles administrator operations.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        admin_manager: Any = None,
        user_manager: Any = None,
        dashboard: Any = None,
        channel_manager: Any = None,
        broadcast_manager: Any = None,
        subscription_manager: Any = None,
        audit_manager: Any = None
    ):
        """
        Initialize the admin handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            admin_manager: Admin manager instance.
            user_manager: User manager instance.
            dashboard: Admin dashboard instance.
            channel_manager: Channel manager instance.
            broadcast_manager: Broadcast manager instance.
            subscription_manager: Subscription manager instance.
            audit_manager: Audit manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.admin_manager = admin_manager
        self.user_manager = user_manager
        self.dashboard = dashboard
        self.channel_manager = channel_manager
        self.broadcast_manager = broadcast_manager
        self.subscription_manager = subscription_manager
        self.audit_manager = audit_manager
        
        # User language preferences
        self.user_languages: dict = {}
    
    async def handle_admin(self, message: Message):
        """
        Handle the /admin command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await message.answer(
                    "You are not an administrator.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show admin menu
            keyboard = AdminKeyboard(lang).get_admin_menu_keyboard()
            await message.answer(
                messages.get_message("admin_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
                
        except Exception as e:
            logger.error(f"Error handling /admin: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_dashboard(self, callback: CallbackQuery):
        """
        Handle dashboard callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get dashboard stats
            if self.dashboard:
                stats = await self.dashboard.get_dashboard_stats()
                
                # Show dashboard
                keyboard = AdminKeyboard(lang).get_dashboard_keyboard()
                await callback.message.edit_text(
                    messages.get_message("dashboard_stats", stats=stats),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling dashboard: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_user_management(self, callback: CallbackQuery):
        """
        Handle user management callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show user management menu
            keyboard = AdminKeyboard(lang).get_user_management_keyboard()
            await callback.message.edit_text(
                messages.get_message("user_management"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling user_management: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_view_users(self, callback: CallbackQuery):
        """
        Handle view users callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get users
            if self.user_manager:
                users = await self.user_manager.get_all_users()
                
                # Show user list
                keyboard = AdminKeyboard(lang).get_user_list_keyboard(users)
                await callback.message.edit_text(
                    messages.get_message("user_list", users=users),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling view_users: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_search_users(self, callback: CallbackQuery):
        """
        Handle search users callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Ask for search query
            await callback.message.edit_text(
                messages.get_message("enter_search_query"),
                reply_markup=AdminKeyboard(lang).get_back_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling search_users: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_user_details(self, callback: CallbackQuery):
        """
        Handle user details callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get target user ID from callback data
            target_user_id = None
            if callback.data:
                try:
                    target_user_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not target_user_id:
                await callback.answer("Invalid user ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user details
            if self.user_manager:
                user_info = await self.user_manager.get_user_info(target_user_id)
                
                if user_info:
                    keyboard = AdminKeyboard(lang).get_user_details_keyboard(user_info)
                    await callback.message.edit_text(
                        messages.get_message("user_details", user=user_info),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("User not found", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling user_details: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_block_user(self, callback: CallbackQuery):
        """
        Handle block user callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get target user ID from callback data
            target_user_id = None
            if callback.data:
                try:
                    target_user_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not target_user_id:
                await callback.answer("Invalid user ID", show_alert=True)
                return
            
            # Confirm blocking
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            keyboard = AdminKeyboard(lang).get_confirm_action_keyboard(
                f"block_user_{target_user_id}",
                "Block User"
            )
            await callback.message.edit_text(
                messages.get_message("confirm_block_user"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling block_user: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_block(self, callback: CallbackQuery):
        """
        Handle confirm block callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get target user ID from callback data
            target_user_id = None
            if callback.data:
                try:
                    target_user_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not target_user_id:
                await callback.answer("Invalid user ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Block user
            if self.user_manager:
                success = await self.user_manager.block_user(target_user_id, user_id)
                
                if success:
                    await callback.answer("User blocked", show_alert=True)
                    
                    # Get updated user details
                    user_info = await self.user_manager.get_user_info(target_user_id)
                    keyboard = AdminKeyboard(lang).get_user_details_keyboard(user_info)
                    await callback.message.edit_text(
                        messages.get_message("user_details", user=user_info),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to block user", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_block: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_unblock_user(self, callback: CallbackQuery):
        """
        Handle unblock user callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get target user ID from callback data
            target_user_id = None
            if callback.data:
                try:
                    target_user_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not target_user_id:
                await callback.answer("Invalid user ID", show_alert=True)
                return
            
            # Confirm unblocking
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            keyboard = AdminKeyboard(lang).get_confirm_action_keyboard(
                f"unblock_user_{target_user_id}",
                "Unblock User"
            )
            await callback.message.edit_text(
                messages.get_message("confirm_unblock_user"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling unblock_user: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_unblock(self, callback: CallbackQuery):
        """
        Handle confirm unblock callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get target user ID from callback data
            target_user_id = None
            if callback.data:
                try:
                    target_user_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not target_user_id:
                await callback.answer("Invalid user ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Unblock user
            if self.user_manager:
                success = await self.user_manager.unblock_user(target_user_id, user_id)
                
                if success:
                    await callback.answer("User unblocked", show_alert=True)
                    
                    # Get updated user details
                    user_info = await self.user_manager.get_user_info(target_user_id)
                    keyboard = AdminKeyboard(lang).get_user_details_keyboard(user_info)
                    await callback.message.edit_text(
                        messages.get_message("user_details", user=user_info),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to unblock user", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_unblock: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_channel_management(self, callback: CallbackQuery):
        """
        Handle channel management callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show channel management menu
            if self.channel_manager:
                channels = await self.channel_manager.get_required_channels()
                keyboard = AdminKeyboard(lang).get_channel_management_keyboard(channels)
                await callback.message.edit_text(
                    messages.get_message("channel_management"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling channel_management: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_broadcast_management(self, callback: CallbackQuery):
        """
        Handle broadcast management callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show broadcast management menu
            keyboard = AdminKeyboard(lang).get_broadcast_management_keyboard()
            await callback.message.edit_text(
                messages.get_message("broadcast_management"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling broadcast_management: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_settings(self, callback: CallbackQuery):
        """
        Handle settings callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show settings menu
            keyboard = AdminKeyboard(lang).get_settings_keyboard()
            await callback.message.edit_text(
                messages.get_message("admin_settings"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling settings: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_audit_logs(self, callback: CallbackQuery):
        """
        Handle audit logs callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get recent audit logs
            if self.audit_manager:
                logs = await self.audit_manager.get_recent_logs(limit=20)
                
                # Show audit logs
                keyboard = AdminKeyboard(lang).get_audit_logs_keyboard()
                await callback.message.edit_text(
                    messages.get_message("audit_logs", logs=logs),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling audit_logs: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_admin(self, callback: CallbackQuery):
        """
        Handle back to admin callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Check if user is admin
            is_admin = await check_admin_access(user_id, self.session_factory)
            
            if not is_admin:
                await callback.answer("Access denied", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show admin menu
            keyboard = AdminKeyboard(lang).get_admin_menu_keyboard()
            await callback.message.edit_text(
                messages.get_message("admin_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_admin: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all admin handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_admin,
            Command("admin")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_dashboard,
            F.data == "admin_dashboard"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_user_management,
            F.data == "user_management"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_view_users,
            F.data == "view_users"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_search_users,
            F.data == "search_users"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_user_details,
            F.data.startswith("user_details_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_block_user,
            F.data.startswith("block_user_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_block,
            F.data.startswith("confirm_block_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_unblock_user,
            F.data.startswith("unblock_user_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_unblock,
            F.data.startswith("confirm_unblock_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_channel_management,
            F.data == "channel_management"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_broadcast_management,
            F.data == "broadcast_management"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_settings,
            F.data == "admin_settings"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_audit_logs,
            F.data == "audit_logs"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_admin,
            F.data == "back_to_admin"
        )
        
        logger.info("AdminHandler: All handlers registered")
