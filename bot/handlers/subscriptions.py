"""
Subscriptions handler for Telegram Auto Publisher Pro
Handles subscription management operations
"""

import logging
from typing import Optional, Any, Callable

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database.repositories import (
    UserRepository,
    SubscriptionRepository,
)
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, MainKeyboard
from config import config

logger = logging.getLogger(__name__)


class SubscriptionsHandler:
    """
    Handles subscription management operations.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        subscription_manager: Any = None,
        user_manager: Any = None
    ):
        """
        Initialize the subscriptions handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            subscription_manager: Subscription manager instance.
            user_manager: User manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.subscription_manager = subscription_manager
        self.user_manager = user_manager
        
        # User language preferences
        self.user_languages: dict = {}
    
    async def handle_subscriptions(self, message: Message):
        """
        Handle the /subscriptions command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user subscription
            async with self.session_factory() as session:
                sub_repo = SubscriptionRepository(session)
                subscription = await sub_repo.get_by_field("user_id", user_id)
            
            # Show subscriptions menu
            keyboard = MainKeyboard(lang).get_subscriptions_menu_keyboard(subscription)
            await message.answer(
                messages.get_message("subscriptions_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
                
        except Exception as e:
            logger.error(f"Error handling /subscriptions: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_my_subscription(self, callback: CallbackQuery):
        """
        Handle my subscription callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user subscription
            async with self.session_factory() as session:
                sub_repo = SubscriptionRepository(session)
                subscription = await sub_repo.get_by_field("user_id", user_id)
            
            if not subscription:
                keyboard = MainKeyboard(lang).get_subscriptions_menu_keyboard(None)
                await callback.message.edit_text(
                    messages.get_message("no_subscription"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Show subscription details
            keyboard = MainKeyboard(lang).get_subscription_details_keyboard(subscription)
            await callback.message.edit_text(
                messages.get_message("subscription_details", subscription=subscription),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling my_subscription: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_subscription_plans(self, callback: CallbackQuery):
        """
        Handle subscription plans callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show subscription plans
            keyboard = MainKeyboard(lang).get_subscription_plans_keyboard()
            await callback.message.edit_text(
                messages.get_message("subscription_plans"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling subscription_plans: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_select_plan(self, callback: CallbackQuery):
        """
        Handle select plan callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get plan type from callback data
            plan_type = None
            if callback.data:
                plan_type = callback.data.replace("select_plan_", "")
            
            if not plan_type:
                await callback.answer("Invalid plan", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show plan details
            keyboard = MainKeyboard(lang).get_plan_details_keyboard(plan_type)
            await callback.message.edit_text(
                messages.get_message("plan_details", plan_type=plan_type),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling select_plan: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_activate_plan(self, callback: CallbackQuery):
        """
        Handle activate plan callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get plan type from callback data
            plan_type = None
            if callback.data:
                plan_type = callback.data.replace("activate_plan_", "")
            
            if not plan_type:
                await callback.answer("Invalid plan", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # For free plan, activate immediately
            if plan_type == "free":
                if self.subscription_manager:
                    success, subscription_info = await self.subscription_manager.create_subscription(
                        user_id=user_id,
                        subscription_type=plan_type,
                        duration_days=0,
                        auto_renew=False
                    )
                    
                    if success:
                        await callback.answer("Subscription activated", show_alert=True)
                        
                        # Show subscription details
                        async with self.session_factory() as session:
                            sub_repo = SubscriptionRepository(session)
                            subscription = await sub_repo.get_by_field("user_id", user_id)
                        
                        keyboard = MainKeyboard(lang).get_subscription_details_keyboard(subscription)
                        await callback.message.edit_text(
                            messages.get_message("subscription_details", subscription=subscription),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await callback.answer("Failed to activate subscription", show_alert=True)
                else:
                    await callback.answer("Service unavailable", show_alert=True)
            else:
                # For paid plans, show payment options
                keyboard = MainKeyboard(lang).get_payment_options_keyboard(plan_type)
                await callback.message.edit_text(
                    messages.get_message("select_payment_method", plan_type=plan_type),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling activate_plan: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_payment_method(self, callback: CallbackQuery):
        """
        Handle payment method selection.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get payment method from callback data
            payment_data = callback.data or ""
            parts = payment_data.split("_")
            if len(parts) >= 3:
                plan_type = parts[2]
                payment_method = parts[3] if len(parts) > 3 else None
            else:
                await callback.answer("Invalid payment data", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # In a real implementation, we would:
            # 1. Create a payment request
            # 2. Show payment link or instructions
            # 3. Wait for payment confirmation
            
            # For now, just show a message
            keyboard = MainKeyboard(lang).get_subscriptions_menu_keyboard(None)
            await callback.message.edit_text(
                messages.get_message("payment_not_implemented", 
                    plan_type=plan_type,
                    payment_method=payment_method or "unknown"
                ),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling payment_method: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_renew_subscription(self, callback: CallbackQuery):
        """
        Handle renew subscription callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get current subscription
            async with self.session_factory() as session:
                sub_repo = SubscriptionRepository(session)
                subscription = await sub_repo.get_by_field("user_id", user_id)
            
            if not subscription:
                await callback.answer("No subscription to renew", show_alert=True)
                return
            
            # For free subscription, just renew
            if subscription.subscription_type == "free":
                if self.subscription_manager:
                    success, subscription_info = await self.subscription_manager.renew_subscription(user_id)
                    
                    if success:
                        await callback.answer("Subscription renewed", show_alert=True)
                        
                        # Show subscription details
                        async with self.session_factory() as session:
                            sub_repo = SubscriptionRepository(session)
                            subscription = await sub_repo.get_by_field("user_id", user_id)
                        
                        keyboard = MainKeyboard(lang).get_subscription_details_keyboard(subscription)
                        await callback.message.edit_text(
                            messages.get_message("subscription_details", subscription=subscription),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await callback.answer("Failed to renew subscription", show_alert=True)
                else:
                    await callback.answer("Service unavailable", show_alert=True)
            else:
                # For paid subscriptions, show renewal options
                keyboard = MainKeyboard(lang).get_renewal_options_keyboard(subscription)
                await callback.message.edit_text(
                    messages.get_message("select_renewal_option"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling renew_subscription: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_cancel_subscription(self, callback: CallbackQuery):
        """
        Handle cancel subscription callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Confirm cancellation
            keyboard = MainKeyboard(lang).get_confirm_cancel_keyboard()
            await callback.message.edit_text(
                messages.get_message("confirm_cancel_subscription"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling cancel_subscription: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_cancel(self, callback: CallbackQuery):
        """
        Handle confirm cancel callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Cancel subscription
            if self.subscription_manager:
                success = await self.subscription_manager.cancel_subscription(user_id)
                
                if success:
                    await callback.answer("Subscription cancelled", show_alert=True)
                    
                    # Show subscriptions menu
                    keyboard = MainKeyboard(lang).get_subscriptions_menu_keyboard(None)
                    await callback.message.edit_text(
                        messages.get_message("subscription_cancelled"),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to cancel subscription", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_cancel: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_subscriptions(self, callback: CallbackQuery):
        """
        Handle back to subscriptions callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user subscription
            async with self.session_factory() as session:
                sub_repo = SubscriptionRepository(session)
                subscription = await sub_repo.get_by_field("user_id", user_id)
            
            # Show subscriptions menu
            keyboard = MainKeyboard(lang).get_subscriptions_menu_keyboard(subscription)
            await callback.message.edit_text(
                messages.get_message("subscriptions_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_subscriptions: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all subscription handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_subscriptions,
            Command("subscriptions")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_my_subscription,
            F.data == "my_subscription"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_subscription_plans,
            F.data == "subscription_plans"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_select_plan,
            F.data.startswith("select_plan_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_activate_plan,
            F.data.startswith("activate_plan_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_payment_method,
            F.data.startswith("payment_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_renew_subscription,
            F.data == "renew_subscription"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_cancel_subscription,
            F.data == "cancel_subscription"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_cancel,
            F.data == "confirm_cancel"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_subscriptions,
            F.data == "back_to_subscriptions"
        )
        
        logger.info("SubscriptionsHandler: All handlers registered")
