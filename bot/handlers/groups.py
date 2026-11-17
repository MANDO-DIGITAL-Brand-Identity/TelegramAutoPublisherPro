"""
Groups handler for Telegram Auto Publisher Pro
Handles group management operations
"""

import logging
from typing import Optional, Any, Callable

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database.repositories import (
    UserRepository,
    TelegramAccountRepository,
    GroupRepository,
)
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, MainKeyboard
from config import config

logger = logging.getLogger(__name__)


class GroupsHandler:
    """
    Handles group management operations.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        account_manager: Any = None,
        group_manager: Any = None
    ):
        """
        Initialize the groups handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            account_manager: Account manager instance.
            group_manager: Group manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.account_manager = account_manager
        self.group_manager = group_manager
        
        # User language preferences
        self.user_languages: dict = {}
    
    async def handle_groups(self, message: Message):
        """
        Handle the /groups command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user's active account
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
            
            if not accounts:
                keyboard = MainKeyboard(lang).get_main_keyboard()
                await message.answer(
                    messages.get_message("no_accounts_groups"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Get groups for the first account
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"user_id": user_id})
            
            # Show groups menu
            keyboard = MainKeyboard(lang).get_groups_menu_keyboard(accounts, len(groups))
            await message.answer(
                messages.get_message("groups_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
                
        except Exception as e:
            logger.error(f"Error handling /groups: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_refresh_groups(self, callback: CallbackQuery):
        """
        Handle refresh groups callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                # Get first account
                async with self.session_factory() as session:
                    account_repo = TelegramAccountRepository(session)
                    accounts = await account_repo.get_accounts_by_user(user_id)
                    if accounts:
                        account_id = accounts[0].id
            
            if not account_id:
                await callback.answer("No account selected", show_alert=True)
                return
            
            # Refresh groups
            if self.group_manager:
                await callback.message.edit_text(
                    messages.get_message("refreshing_groups"),
                    parse_mode=ParseMode.HTML
                )
                
                # In a real implementation, we would use Telethon to fetch groups
                # For now, we'll just show a message
                await asyncio.sleep(1)
                
                # Get updated groups
                async with self.session_factory() as session:
                    group_repo = GroupRepository(session)
                    groups = await group_repo.get_all(filters={"telegram_account_id": account_id})
                
                keyboard = MainKeyboard(lang).get_group_list_keyboard(groups)
                await callback.message.edit_text(
                    messages.get_message("your_groups"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling refresh_groups: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_my_groups(self, callback: CallbackQuery):
        """
        Handle my groups callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                # Get first account
                async with self.session_factory() as session:
                    account_repo = TelegramAccountRepository(session)
                    accounts = await account_repo.get_accounts_by_user(user_id)
                    if accounts:
                        account_id = accounts[0].id
            
            if not account_id:
                keyboard = MainKeyboard(lang).get_groups_menu_keyboard([], 0)
                await callback.message.edit_text(
                    messages.get_message("no_accounts_groups"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Get groups
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"telegram_account_id": account_id})
            
            if not groups:
                keyboard = MainKeyboard(lang).get_groups_menu_keyboard([], 0)
                await callback.message.edit_text(
                    messages.get_message("no_groups"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Show group list
            keyboard = MainKeyboard(lang).get_group_list_keyboard(groups)
            await callback.message.edit_text(
                messages.get_message("your_groups"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling my_groups: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_group_details(self, callback: CallbackQuery):
        """
        Handle group details callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get group ID from callback data
            group_id = None
            if callback.data:
                try:
                    group_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not group_id:
                await callback.answer("Invalid group ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get group details
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                group = await group_repo.get(group_id)
            
            if not group:
                await callback.answer("Group not found", show_alert=True)
                return
            
            # Check if group belongs to user
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
                account_ids = [a.id for a in accounts]
            
            if group.telegram_account_id not in account_ids:
                await callback.answer("Group not found", show_alert=True)
                return
            
            # Show group details
            keyboard = MainKeyboard(lang).get_group_details_keyboard(group)
            await callback.message.edit_text(
                messages.get_message("group_details", group=group),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling group_details: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_select_all_groups(self, callback: CallbackQuery):
        """
        Handle select all groups callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                # Get first account
                async with self.session_factory() as session:
                    account_repo = TelegramAccountRepository(session)
                    accounts = await account_repo.get_accounts_by_user(user_id)
                    if accounts:
                        account_id = accounts[0].id
            
            if not account_id:
                await callback.answer("No account selected", show_alert=True)
                return
            
            # Get groups
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"telegram_account_id": account_id})
            
            # Mark all as selected
            if groups:
                for group in groups:
                    group.is_selected = True
                    await group_repo.update(group.id, {"is_selected": True})
            
            # Show updated group list
            keyboard = MainKeyboard(lang).get_group_list_keyboard(groups)
            await callback.message.edit_text(
                messages.get_message("all_groups_selected"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling select_all_groups: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_deselect_all_groups(self, callback: CallbackQuery):
        """
        Handle deselect all groups callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                # Get first account
                async with self.session_factory() as session:
                    account_repo = TelegramAccountRepository(session)
                    accounts = await account_repo.get_accounts_by_user(user_id)
                    if accounts:
                        account_id = accounts[0].id
            
            if not account_id:
                await callback.answer("No account selected", show_alert=True)
                return
            
            # Get groups
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"telegram_account_id": account_id})
            
            # Mark all as deselected
            if groups:
                for group in groups:
                    group.is_selected = False
                    await group_repo.update(group.id, {"is_selected": False})
            
            # Show updated group list
            keyboard = MainKeyboard(lang).get_group_list_keyboard(groups)
            await callback.message.edit_text(
                messages.get_message("all_groups_deselected"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling deselect_all_groups: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_toggle_group(self, callback: CallbackQuery):
        """
        Handle toggle group selection callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get group ID from callback data
            group_id = None
            if callback.data:
                try:
                    group_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not group_id:
                await callback.answer("Invalid group ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Toggle group selection
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                group = await group_repo.get(group_id)
            
            if not group:
                await callback.answer("Group not found", show_alert=True)
                return
            
            # Check if group belongs to user
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
                account_ids = [a.id for a in accounts]
            
            if group.telegram_account_id not in account_ids:
                await callback.answer("Group not found", show_alert=True)
                return
            
            # Toggle selection
            new_selection = not group.is_selected
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                await group_repo.update(group_id, {"is_selected": new_selection})
                group.is_selected = new_selection
            
            # Get all groups for this account
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"telegram_account_id": group.telegram_account_id})
            
            # Show updated group list
            keyboard = MainKeyboard(lang).get_group_list_keyboard(groups)
            await callback.message.edit_text(
                messages.get_message("your_groups"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling toggle_group: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_groups(self, callback: CallbackQuery):
        """
        Handle back to groups callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user's active account
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
            
            # Get groups for the first account
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"user_id": user_id})
            
            # Show groups menu
            keyboard = MainKeyboard(lang).get_groups_menu_keyboard(accounts, len(groups))
            await callback.message.edit_text(
                messages.get_message("groups_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_groups: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all groups handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_groups,
            Command("groups")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_refresh_groups,
            F.data.startswith("refresh_groups")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_my_groups,
            F.data.startswith("my_groups")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_group_details,
            F.data.startswith("group_details_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_select_all_groups,
            F.data.startswith("select_all_groups")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_deselect_all_groups,
            F.data.startswith("deselect_all_groups")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_toggle_group,
            F.data.startswith("toggle_group_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_groups,
            F.data == "back_to_groups"
        )
        
        logger.info("GroupsHandler: All handlers registered")
