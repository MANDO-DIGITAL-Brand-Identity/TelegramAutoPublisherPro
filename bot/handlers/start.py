"""
Start handler for Telegram Auto Publisher Pro
Handles the /start command and initial setup
"""

import logging
from typing import Optional, Any, Callable

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from database.repositories import (
    UserRepository,
    AdministratorRepository,
    TelegramAccountRepository,
    SubscriptionRepository,
    RequiredChannelRepository,
)
from security.permissions import check_admin_access, check_user_access
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, AdminKeyboard
from config import config

logger = logging.getLogger(__name__)


class StartHandler:
    """
    Handles the /start command and user initialization.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        channel_manager: Any = None,
        subscription_manager: Any = None,
        user_manager: Any = None,
        admin_manager: Any = None
    ):
        """
        Initialize the start handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            channel_manager: Channel manager instance.
            subscription_manager: Subscription manager instance.
            user_manager: User manager instance.
            admin_manager: Admin manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.channel_manager = channel_manager
        self.subscription_manager = subscription_manager
        self.user_manager = user_manager
        self.admin_manager = admin_manager
        
        # User language preferences
        self.user_languages: dict = {}
    
    async def handle_start(self, message: Message):
        """
        Handle the /start command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Set default language
            if user_id not in self.user_languages:
                self.user_languages[user_id] = Language.ENGLISH
                if user.language_code and user.language_code.startswith('ar'):
                    self.user_languages[user_id] = Language.ARABIC
            
            messages = Messages(self.user_languages[user_id])
            
            # Check if user exists, create if not
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                existing_user = await user_repo.get_user(user_id)
                
                if not existing_user:
                    # Create new user
                    new_user = await user_repo.create({
                        "telegram_id": user_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "language_code": user.language_code,
                        "status": "active",
                        "is_bot": False
                    })
                    logger.info(f"Created new user: {user_id}")
                
                # Check if user is blocked
                if existing_user and existing_user.status == "blocked":
                    await message.answer(messages.get_permission_denied_message())
                    return
            
            # Check mandatory channel subscription
            if not await self._check_channel_subscription(message, user_id):
                return
            
            # Send welcome message
            await message.answer(
                messages.get_welcome_message(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_main_menu_keyboard(user_id)
            )
            
        except Exception as e:
            logger.error(f"Error handling start command: {e}")
            await message.answer("❌ An error occurred. Please try again.")
    
    async def _check_channel_subscription(self, message: Message, user_id: int) -> bool:
        """
        Check if user has subscribed to required channels.
        
        Args:
            message: The message to respond to.
            user_id: The user ID.
            
        Returns:
            True if subscription is verified or not required, False otherwise.
        """
        try:
            async with self.session_factory() as session:
                channel_repo = RequiredChannelRepository(session)
                required_channels = await channel_repo.get_active_required_channels()
            
            if not required_channels:
                return True
            
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            # Show subscription message with join buttons
            channel_list = [
                {"username": ch.channel_username, "channel_id": ch.channel_id}
                for ch in required_channels
            ]
            
            await message.answer(
                messages.get_channel_subscription_required_message(channel_list),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._get_channel_subscription_keyboard(channel_list, user_id)
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking channel subscription: {e}")
            return True  # Allow access on error
    
    async def handle_verify_subscription(self, callback: CallbackQuery):
        """
        Handle subscription verification callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user_id = callback.from_user.id
            language = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(language)
            
            # Verify subscription
            if await self._verify_subscription(user_id):
                # Subscription verified
                await callback.message.edit_text(
                    messages.get_channel_subscription_verified_message(),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._get_main_menu_keyboard(user_id)
                )
            else:
                # Subscription not verified
                async with self.session_factory() as session:
                    channel_repo = RequiredChannelRepository(session)
                    required_channels = await channel_repo.get_active_required_channels()
                
                channel_list = [
                    {"username": ch.channel_username, "channel_id": ch.channel_id}
                    for ch in required_channels
                ]
                
                await callback.message.edit_text(
                    messages.get_channel_subscription_failed_message([ch for ch in channel_list if ch.get('username')]),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._get_channel_subscription_keyboard(channel_list, user_id)
                )
            
        except Exception as e:
            logger.error(f"Error verifying subscription: {e}")
            try:
                await callback.message.answer("❌ Verification failed. Please try again.")
            except:
                pass
    
    async def _verify_subscription(self, user_id: int) -> bool:
        """
        Verify user's channel subscription.
        
        Args:
            user_id: The user ID.
            
        Returns:
            True if all required channels are joined, False otherwise.
        """
        try:
            # In a real implementation, we would use Telegram Bot API to check membership
            # For now, we'll return True to allow access
            # This is a placeholder that should be implemented with actual verification
            
            if self.channel_manager:
                return await self.channel_manager.verify_user_subscription(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying subscription: {e}")
            return True  # Allow access on error
    
    def _get_main_menu_keyboard(self, user_id: int) -> Any:
        """Get the main menu keyboard."""
        language = self.user_languages.get(user_id, Language.ENGLISH)
        
        if language == Language.ARABIC:
            return MainKeyboard.get_main_menu_arabic()
        else:
            return MainKeyboard.get_main_menu()
    
    def _get_channel_subscription_keyboard(self, channels: list, user_id: int) -> Any:
        """Get the channel subscription keyboard."""
        language = self.user_languages.get(user_id, Language.ENGLISH)
        
        if language == Language.ARABIC:
            return AdminKeyboard.get_channel_subscription_keyboard_arabic(channels)
        else:
            return AdminKeyboard.get_channel_subscription_keyboard(channels)


__all__ = [
    'StartHandler',
]
