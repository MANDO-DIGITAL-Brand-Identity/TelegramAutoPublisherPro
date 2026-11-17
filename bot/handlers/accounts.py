"""
Accounts handler for Telegram Auto Publisher Pro
Handles account management operations
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
from security.permissions import check_admin_access, check_user_access
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, AccountKeyboard
from config import config

logger = logging.getLogger(__name__)


class AccountsHandler:
    """
    Handles account management operations.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        account_manager: Any = None,
        user_manager: Any = None,
        notification_manager: Any = None,
        channel_manager: Any = None
    ):
        """
        Initialize the accounts handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            account_manager: Account manager instance.
            user_manager: User manager instance.
            notification_manager: Notification manager instance.
            channel_manager: Channel manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.account_manager = account_manager
        self.user_manager = user_manager
        self.notification_manager = notification_manager
        self.channel_manager = channel_manager
        
        # User language preferences
        self.user_languages: dict = {}
    
    async def handle_accounts(self, message: Message):
        """
        Handle the /accounts command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Check if user has access
            if self.channel_manager:
                has_access = await self.channel_manager.check_user_access(user_id, user)
                if not has_access:
                    missing = await self.channel_manager.get_missing_channels(user_id, user)
                    if missing:
                        join_urls = await self.channel_manager.get_join_urls(user_id, user)
                        if join_urls:
                            await message.answer(
                                messages.get_message("channel_required"),
                                parse_mode=ParseMode.HTML
                            )
                            return
            
            # Get user accounts
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                user_accounts = await account_repo.get_accounts_by_user(user_id)
            
            if not user_accounts:
                # No accounts, show add account screen
                keyboard = AccountKeyboard(lang).get_add_account_keyboard()
                await message.answer(
                    messages.get_message("no_accounts"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Show account list
                keyboard = AccountKeyboard(lang).get_account_list_keyboard(user_accounts)
                await message.answer(
                    messages.get_message("your_accounts"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling /accounts: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_add_account(self, callback: CallbackQuery):
        """
        Handle the add account callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show phone number input screen
            await callback.message.edit_text(
                messages.get_message("enter_phone_number"),
                reply_markup=AccountKeyboard(lang).get_back_keyboard(),
                parse_mode=ParseMode.HTML
            )
            
            # Set state for next message
            # In a real implementation, we would use aiogram's FSM
            # For now, we'll just acknowledge
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling add_account: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_phone_number(self, message: Message):
        """
        Handle phone number input.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            phone_number = message.text.strip()
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Validate phone number
            if not phone_number:
                await message.answer(
                    messages.get_message("invalid_phone_number"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Check if account with this phone already exists
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                existing = await account_repo.get_by_phone(phone_number)
                
                if existing:
                    await message.answer(
                        messages.get_message("phone_already_exists"),
                        parse_mode=ParseMode.HTML
                    )
                    return
            
            # Start authentication
            if self.account_manager:
                # Create authentication state
                # In a real implementation, we would store this state
                
                # For now, just show verification code input
                keyboard = AccountKeyboard(lang).get_verify_code_keyboard()
                await message.answer(
                    messages.get_message("enter_verification_code"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    messages.get_message("error_no_account_manager"),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling phone_number: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_verify_code(self, message: Message):
        """
        Handle verification code input.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            code = message.text.strip()
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Validate code
            if not code or not code.isdigit():
                await message.answer(
                    messages.get_message("invalid_verification_code"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # In a real implementation, we would:
            # 1. Get the phone number from state
            # 2. Verify the code with Telethon
            # 3. Create the account
            
            # For now, just show success message
            await message.answer(
                messages.get_message("account_added_success"),
                parse_mode=ParseMode.HTML
            )
            
            # Show account list
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                user_accounts = await account_repo.get_accounts_by_user(user_id)
            
            keyboard = AccountKeyboard(lang).get_account_list_keyboard(user_accounts)
            await message.answer(
                messages.get_message("your_accounts"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error handling verify_code: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_account_list(self, callback: CallbackQuery):
        """
        Handle account list callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user accounts
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                user_accounts = await account_repo.get_accounts_by_user(user_id)
            
            # Show account list
            keyboard = AccountKeyboard(lang).get_account_list_keyboard(user_accounts)
            await callback.message.edit_text(
                messages.get_message("your_accounts"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling account_list: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_select_account(self, callback: CallbackQuery):
        """
        Handle select account callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get(account_id)
            
            if not account:
                await callback.answer("Account not found", show_alert=True)
                return
            
            # Show account details
            keyboard = AccountKeyboard(lang).get_account_details_keyboard(account)
            await callback.message.edit_text(
                messages.get_message("account_details", account=account),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling select_account: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_account_settings(self, callback: CallbackQuery):
        """
        Handle account settings callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get account info
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                account = await account_repo.get(account_id)
            
            if not account:
                await callback.answer("Account not found", show_alert=True)
                return
            
            # Show account settings
            keyboard = AccountKeyboard(lang).get_account_settings_keyboard(account)
            await callback.message.edit_text(
                messages.get_message("account_settings", account=account),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling account_settings: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_connect_account(self, callback: CallbackQuery):
        """
        Handle connect account callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Connect the account
            if self.account_manager:
                success = await self.account_manager.connect_account(account_id)
                if success:
                    await callback.answer("Account connected", show_alert=True)
                    
                    # Refresh account details
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        account = await account_repo.get(account_id)
                    
                    keyboard = AccountKeyboard(lang).get_account_details_keyboard(account)
                    await callback.message.edit_text(
                        messages.get_message("account_details", account=account),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to connect account", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling connect_account: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_disconnect_account(self, callback: CallbackQuery):
        """
        Handle disconnect account callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Confirm disconnection
            keyboard = AccountKeyboard(lang).get_confirm_disconnect_keyboard(account_id)
            await callback.message.edit_text(
                messages.get_message("confirm_disconnect"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling disconnect_account: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_disconnect(self, callback: CallbackQuery):
        """
        Handle confirm disconnect callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Disconnect the account
            if self.account_manager:
                success = await self.account_manager.disconnect_account(account_id)
                if success:
                    await callback.answer("Account disconnected", show_alert=True)
                    
                    # Refresh account list
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        user_accounts = await account_repo.get_accounts_by_user(user_id)
                    
                    keyboard = AccountKeyboard(lang).get_account_list_keyboard(user_accounts)
                    await callback.message.edit_text(
                        messages.get_message("your_accounts"),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to disconnect account", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_disconnect: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_delete_account(self, callback: CallbackQuery):
        """
        Handle delete account callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Confirm deletion
            keyboard = AccountKeyboard(lang).get_confirm_delete_keyboard(account_id)
            await callback.message.edit_text(
                messages.get_message("confirm_delete_account"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling delete_account: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_delete(self, callback: CallbackQuery):
        """
        Handle confirm delete callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get account ID from callback data
            account_id = None
            if callback.data:
                try:
                    account_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not account_id:
                await callback.answer("Invalid account ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Delete the account
            if self.account_manager:
                success = await self.account_manager.delete_account(account_id)
                if success:
                    await callback.answer("Account deleted", show_alert=True)
                    
                    # Refresh account list
                    async with self.session_factory() as session:
                        account_repo = TelegramAccountRepository(session)
                        user_accounts = await account_repo.get_accounts_by_user(user_id)
                    
                    if user_accounts:
                        keyboard = AccountKeyboard(lang).get_account_list_keyboard(user_accounts)
                        await callback.message.edit_text(
                            messages.get_message("your_accounts"),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        keyboard = AccountKeyboard(lang).get_add_account_keyboard()
                        await callback.message.edit_text(
                            messages.get_message("no_accounts"),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    await callback.answer("Failed to delete account", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_delete: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_accounts(self, callback: CallbackQuery):
        """
        Handle back to accounts callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user accounts
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                user_accounts = await account_repo.get_accounts_by_user(user_id)
            
            keyboard = AccountKeyboard(lang).get_account_list_keyboard(user_accounts)
            await callback.message.edit_text(
                messages.get_message("your_accounts"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_accounts: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all account handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_accounts,
            Command("accounts")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_add_account,
            F.data == "add_account"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_account_list,
            F.data == "account_list"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_select_account,
            F.data.startswith("select_account_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_account_settings,
            F.data.startswith("account_settings_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_connect_account,
            F.data.startswith("connect_account_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_disconnect_account,
            F.data.startswith("disconnect_account_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_disconnect,
            F.data.startswith("confirm_disconnect_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_delete_account,
            F.data.startswith("delete_account_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_delete,
            F.data.startswith("confirm_delete_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_accounts,
            F.data == "back_to_accounts"
        )
        
        # Text handlers (for phone number and verification code)
        # These would need state management in a real implementation
        # For now, we'll just register them without state
        dispatcher.register_message_handler(
            self.handle_phone_number,
            lambda message: message.text and message.text.strip() and len(message.text.strip()) > 5
        )
        
        dispatcher.register_message_handler(
            self.handle_verify_code,
            lambda message: message.text and message.text.strip().isdigit() and len(message.text.strip()) >= 5
        )
        
        logger.info("AccountsHandler: All handlers registered")
