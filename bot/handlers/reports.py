"""
Reports handler for Telegram Auto Publisher Pro
Handles report generation and viewing
"""

import logging
from typing import Optional, Any, Callable

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, User
from aiogram.filters import Command
from aiogram.enums import ParseMode

from database.repositories import (
    UserRepository,
    PublishingTaskRepository,
    PublishingLogRepository,
)
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, MainKeyboard
from config import config

logger = logging.getLogger(__name__)


class ReportsHandler:
    """
    Handles report generation and viewing.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        statistics_manager: Any = None,
        report_generator: Any = None,
        publishing_engine: Any = None
    ):
        """
        Initialize the reports handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            statistics_manager: Statistics manager instance.
            report_generator: Report generator instance.
            publishing_engine: Publishing engine instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.statistics_manager = statistics_manager
        self.report_generator = report_generator
        self.publishing_engine = publishing_engine
        
        # User language preferences
        self.user_languages: dict = {}
    
    async def handle_reports(self, message: Message):
        """
        Handle the /reports command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show reports menu
            keyboard = MainKeyboard(lang).get_reports_menu_keyboard()
            await message.answer(
                messages.get_message("reports_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
                
        except Exception as e:
            logger.error(f"Error handling /reports: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_publishing_report(self, callback: CallbackQuery):
        """
        Handle publishing report callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user's publishing statistics
            if self.statistics_manager:
                dashboard_stats = await self.statistics_manager.get_dashboard_stats()
                publishing_stats = dashboard_stats.publishing_stats
                
                # Show publishing report
                keyboard = MainKeyboard(lang).get_publishing_report_keyboard()
                await callback.message.edit_text(
                    messages.get_message("publishing_report", stats=publishing_stats),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling publishing_report: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_task_history(self, callback: CallbackQuery):
        """
        Handle task history callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user's tasks
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_all(
                    filters={"user_id": user_id},
                    limit=20,
                    order_by="created_at",
                    descending=True
                )
            
            if not tasks:
                keyboard = MainKeyboard(lang).get_reports_menu_keyboard()
                await callback.message.edit_text(
                    messages.get_message("no_task_history"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Show task history
            keyboard = MainKeyboard(lang).get_task_history_keyboard(tasks)
            await callback.message.edit_text(
                messages.get_message("task_history", tasks=tasks),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling task_history: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_statistics(self, callback: CallbackQuery):
        """
        Handle statistics callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user statistics
            if self.statistics_manager:
                user_stats = await self.statistics_manager.get_user_stats()
                account_stats = await self.statistics_manager.get_account_stats()
                
                # Show statistics
                keyboard = MainKeyboard(lang).get_statistics_keyboard()
                await callback.message.edit_text(
                    messages.get_message("user_statistics", 
                        user_stats=user_stats,
                        account_stats=account_stats
                    ),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling statistics: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_export_report(self, callback: CallbackQuery):
        """
        Handle export report callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get report type from callback data
            report_type = None
            if callback.data:
                report_type = callback.data.replace("export_", "")
            
            if not report_type:
                await callback.answer("Invalid report type", show_alert=True)
                return
            
            # Generate and export report
            if self.report_generator:
                from reports.report_generator import ReportConfig, ReportFormat
                
                config = ReportConfig(
                    report_type=report_type,
                    report_format=ReportFormat.TEXT,
                    limit=100
                )
                
                report_data = await self.report_generator.generate_report(config, user_id)
                
                if report_data.content:
                    # Send the report as a message
                    await callback.message.answer(
                        f"<b>Report: {report_data.title}</b>\n\n{report_data.content[:3000]}",
                        parse_mode=ParseMode.HTML
                    )
                    
                    if len(report_data.content) > 3000:
                        await callback.message.answer(
                            report_data.content[3000:6000],
                            parse_mode=ParseMode.HTML
                        )
                    
                    await callback.answer("Report generated")
                else:
                    await callback.answer("Failed to generate report", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling export_report: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_reports(self, callback: CallbackQuery):
        """
        Handle back to reports callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show reports menu
            keyboard = MainKeyboard(lang).get_reports_menu_keyboard()
            await callback.message.edit_text(
                messages.get_message("reports_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_reports: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all report handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_reports,
            Command("reports")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_publishing_report,
            F.data == "publishing_report"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_task_history,
            F.data == "task_history"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_statistics,
            F.data == "statistics"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_export_report,
            F.data.startswith("export_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_reports,
            F.data == "back_to_reports"
        )
        
        logger.info("ReportsHandler: All handlers registered")
