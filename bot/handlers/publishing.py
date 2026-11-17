"""
Publishing handler for Telegram Auto Publisher Pro
Handles publishing operations
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
    PublishingTaskRepository,
    ContentRepository,
    GroupRepository,
)
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard, AccountKeyboard
from config import config

logger = logging.getLogger(__name__)


class PublishingHandler:
    """
    Handles publishing operations.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        publishing_engine: Any = None,
        task_scheduler: Any = None,
        account_manager: Any = None,
        content_manager: Any = None,
        group_manager: Any = None,
        notification_manager: Any = None
    ):
        """
        Initialize the publishing handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            publishing_engine: Publishing engine instance.
            task_scheduler: Task scheduler instance.
            account_manager: Account manager instance.
            content_manager: Content manager instance.
            group_manager: Group manager instance.
            notification_manager: Notification manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.publishing_engine = publishing_engine
        self.task_scheduler = task_scheduler
        self.account_manager = account_manager
        self.content_manager = content_manager
        self.group_manager = group_manager
        self.notification_manager = notification_manager
        
        # User language preferences
        self.user_languages: dict = {}
        self.user_states: dict = {}
    
    async def handle_publishing(self, message: Message):
        """
        Handle the /publishing command.
        
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
                    messages.get_message("no_accounts_publishing"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Show publishing menu
            keyboard = MainKeyboard(lang).get_publishing_menu_keyboard(accounts)
            await message.answer(
                messages.get_message("publishing_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
                
        except Exception as e:
            logger.error(f"Error handling /publishing: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_create_task(self, callback: CallbackQuery):
        """
        Handle create task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user's accounts, content, and groups
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                content_repo = ContentRepository(session)
                group_repo = GroupRepository(session)
                
                accounts = await account_repo.get_accounts_by_user(user_id)
                contents = await content_repo.get_all(filters={"user_id": user_id})
                groups = await group_repo.get_all(filters={"user_id": user_id})
            
            if not accounts:
                await callback.answer("No accounts available", show_alert=True)
                return
            
            if not contents:
                keyboard = MainKeyboard(lang).get_create_content_first_keyboard()
                await callback.message.edit_text(
                    messages.get_message("no_content_available"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Show task creation screen
            keyboard = MainKeyboard(lang).get_create_task_keyboard(accounts, contents, groups)
            await callback.message.edit_text(
                messages.get_message("create_task"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling create_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_select_account_for_task(self, callback: CallbackQuery):
        """
        Handle select account for task callback.
        
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
            
            # Store state
            self.user_states[user_id] = {
                "creating_task": True,
                "account_id": account_id
            }
            
            # Get contents and groups
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                group_repo = GroupRepository(session)
                
                contents = await content_repo.get_all(filters={"user_id": user_id})
                groups = await group_repo.get_all(filters={"user_id": user_id})
            
            # Show content selection
            keyboard = MainKeyboard(lang).get_select_content_keyboard(contents)
            await callback.message.edit_text(
                messages.get_message("select_content_for_task"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling select_account_for_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_select_content_for_task(self, callback: CallbackQuery):
        """
        Handle select content for task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get content ID from callback data
            content_id = None
            if callback.data:
                try:
                    content_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not content_id:
                await callback.answer("Invalid content ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Update state
            if user_id in self.user_states:
                self.user_states[user_id]["content_id"] = content_id
            
            # Get groups
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"user_id": user_id})
            
            # Show group selection
            keyboard = MainKeyboard(lang).get_select_groups_keyboard(groups)
            await callback.message.edit_text(
                messages.get_message("select_groups_for_task"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling select_content_for_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_select_groups_for_task(self, callback: CallbackQuery):
        """
        Handle select groups for task callback.
        
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
            
            # Update state
            if user_id in self.user_states:
                if "selected_groups" not in self.user_states[user_id]:
                    self.user_states[user_id]["selected_groups"] = []
                
                if group_id in self.user_states[user_id]["selected_groups"]:
                    self.user_states[user_id]["selected_groups"].remove(group_id)
                else:
                    self.user_states[user_id]["selected_groups"].append(group_id)
            
            # Get groups
            async with self.session_factory() as session:
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all(filters={"user_id": user_id})
            
            # Show updated group selection
            keyboard = MainKeyboard(lang).get_select_groups_keyboard(
                groups,
                selected_ids=self.user_states[user_id].get("selected_groups", [])
            )
            await callback.message.edit_text(
                messages.get_message("select_groups_for_task"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling select_groups_for_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_set_schedule_for_task(self, callback: CallbackQuery):
        """
        Handle set schedule for task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Check state
            if user_id not in self.user_states or "selected_groups" not in self.user_states[user_id]:
                await callback.answer("Please select at least one group", show_alert=True)
                return
            
            if not self.user_states[user_id].get("selected_groups"):
                await callback.answer("Please select at least one group", show_alert=True)
                return
            
            # Show schedule options
            keyboard = MainKeyboard(lang).get_schedule_options_keyboard()
            await callback.message.edit_text(
                messages.get_message("select_schedule"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling set_schedule_for_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_schedule_now(self, callback: CallbackQuery):
        """
        Handle schedule now callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Check state
            state = self.user_states.get(user_id, {})
            if not all(key in state for key in ["account_id", "content_id", "selected_groups"]):
                await callback.answer("Missing task information", show_alert=True)
                return
            
            # Create the task
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                task = await task_repo.create({
                    "user_id": user_id,
                    "name": f"Task {datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    "telegram_account_id": state["account_id"],
                    "content_id": state["content_id"],
                    "group_ids": state["selected_groups"],
                    "status": "pending",
                    "scheduled_at": datetime.utcnow(),
                    "created_at": datetime.utcnow()
                })
            
            if task:
                # Clear state
                self.user_states[user_id] = {}
                
                # Confirm task creation
                keyboard = MainKeyboard(lang).get_task_created_keyboard(task.id)
                await callback.message.edit_text(
                    messages.get_message("task_created_success"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                
                # Start the task if publishing engine is available
                if self.publishing_engine:
                    await self.publishing_engine.start_task(task.id)
            else:
                await callback.answer("Failed to create task", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling schedule_now: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_schedule_later(self, callback: CallbackQuery):
        """
        Handle schedule later callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Ask for date/time
            await callback.message.edit_text(
                messages.get_message("enter_schedule_time"),
                reply_markup=MainKeyboard(lang).get_back_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling schedule_later: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_my_tasks(self, callback: CallbackQuery):
        """
        Handle my tasks callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user tasks
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_all(filters={"user_id": user_id})
            
            if not tasks:
                keyboard = MainKeyboard(lang).get_publishing_menu_keyboard()
                await callback.message.edit_text(
                    messages.get_message("no_tasks"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Show task list
            keyboard = MainKeyboard(lang).get_task_list_keyboard(tasks)
            await callback.message.edit_text(
                messages.get_message("your_tasks"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling my_tasks: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_task_details(self, callback: CallbackQuery):
        """
        Handle task details callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get task details
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                task = await task_repo.get(task_id)
            
            if not task or task.user_id != user_id:
                await callback.answer("Task not found", show_alert=True)
                return
            
            # Show task details
            keyboard = MainKeyboard(lang).get_task_details_keyboard(task)
            await callback.message.edit_text(
                messages.get_message("task_details", task=task),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling task_details: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_start_task(self, callback: CallbackQuery):
        """
        Handle start task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Start the task
            if self.publishing_engine:
                success = await self.publishing_engine.start_task(task_id)
                if success:
                    await callback.answer("Task started", show_alert=True)
                    
                    # Refresh task details
                    async with self.session_factory() as session:
                        task_repo = PublishingTaskRepository(session)
                        task = await task_repo.get(task_id)
                    
                    keyboard = MainKeyboard(lang).get_task_details_keyboard(task)
                    await callback.message.edit_text(
                        messages.get_message("task_details", task=task),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to start task", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling start_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_stop_task(self, callback: CallbackQuery):
        """
        Handle stop task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Confirm stop
            keyboard = MainKeyboard(lang).get_confirm_stop_keyboard(task_id)
            await callback.message.edit_text(
                messages.get_message("confirm_stop_task"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling stop_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_stop(self, callback: CallbackQuery):
        """
        Handle confirm stop callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Stop the task
            if self.publishing_engine:
                success = await self.publishing_engine.stop_task(task_id)
                if success:
                    await callback.answer("Task stopped", show_alert=True)
                    
                    # Refresh task details
                    async with self.session_factory() as session:
                        task_repo = PublishingTaskRepository(session)
                        task = await task_repo.get(task_id)
                    
                    keyboard = MainKeyboard(lang).get_task_details_keyboard(task)
                    await callback.message.edit_text(
                        messages.get_message("task_details", task=task),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to stop task", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_stop: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_pause_task(self, callback: CallbackQuery):
        """
        Handle pause task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Pause the task
            if self.publishing_engine:
                success = await self.publishing_engine.pause_task(task_id)
                if success:
                    await callback.answer("Task paused", show_alert=True)
                    
                    # Refresh task details
                    async with self.session_factory() as session:
                        task_repo = PublishingTaskRepository(session)
                        task = await task_repo.get(task_id)
                    
                    keyboard = MainKeyboard(lang).get_task_details_keyboard(task)
                    await callback.message.edit_text(
                        messages.get_message("task_details", task=task),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to pause task", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling pause_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_resume_task(self, callback: CallbackQuery):
        """
        Handle resume task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Resume the task
            if self.publishing_engine:
                success = await self.publishing_engine.resume_task(task_id)
                if success:
                    await callback.answer("Task resumed", show_alert=True)
                    
                    # Refresh task details
                    async with self.session_factory() as session:
                        task_repo = PublishingTaskRepository(session)
                        task = await task_repo.get(task_id)
                    
                    keyboard = MainKeyboard(lang).get_task_details_keyboard(task)
                    await callback.message.edit_text(
                        messages.get_message("task_details", task=task),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.answer("Failed to resume task", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling resume_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_delete_task(self, callback: CallbackQuery):
        """
        Handle delete task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Confirm deletion
            keyboard = MainKeyboard(lang).get_confirm_delete_task_keyboard(task_id)
            await callback.message.edit_text(
                messages.get_message("confirm_delete_task"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling delete_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_delete_task(self, callback: CallbackQuery):
        """
        Handle confirm delete task callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get task ID from callback data
            task_id = None
            if callback.data:
                try:
                    task_id = int(callback.data.split("_")[-1])
                except (ValueError, IndexError):
                    pass
            
            if not task_id:
                await callback.answer("Invalid task ID", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Delete the task
            if self.publishing_engine:
                success = await self.publishing_engine.delete_task(task_id)
                if success:
                    await callback.answer("Task deleted", show_alert=True)
                    
                    # Refresh task list
                    async with self.session_factory() as session:
                        task_repo = PublishingTaskRepository(session)
                        tasks = await task_repo.get_all(filters={"user_id": user_id})
                    
                    if tasks:
                        keyboard = MainKeyboard(lang).get_task_list_keyboard(tasks)
                        await callback.message.edit_text(
                            messages.get_message("your_tasks"),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        keyboard = MainKeyboard(lang).get_publishing_menu_keyboard()
                        await callback.message.edit_text(
                            messages.get_message("no_tasks"),
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    await callback.answer("Failed to delete task", show_alert=True)
            else:
                await callback.answer("Service unavailable", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_delete_task: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_publishing(self, callback: CallbackQuery):
        """
        Handle back to publishing callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Clear state
            self.user_states[user_id] = {}
            
            # Get user's active account
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
            
            keyboard = MainKeyboard(lang).get_publishing_menu_keyboard(accounts)
            await callback.message.edit_text(
                messages.get_message("publishing_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_publishing: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all publishing handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_publishing,
            Command("publishing")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_create_task,
            F.data == "create_task"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_select_account_for_task,
            F.data.startswith("select_account_for_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_select_content_for_task,
            F.data.startswith("select_content_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_select_groups_for_task,
            F.data.startswith("select_group_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_set_schedule_for_task,
            F.data == "set_schedule"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_schedule_now,
            F.data == "schedule_now"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_schedule_later,
            F.data == "schedule_later"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_my_tasks,
            F.data == "my_tasks"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_task_details,
            F.data.startswith("task_details_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_start_task,
            F.data.startswith("start_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_stop_task,
            F.data.startswith("stop_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_stop,
            F.data.startswith("confirm_stop_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_pause_task,
            F.data.startswith("pause_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_resume_task,
            F.data.startswith("resume_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_delete_task,
            F.data.startswith("delete_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_delete_task,
            F.data.startswith("confirm_delete_task_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_publishing,
            F.data == "back_to_publishing"
        )
        
        logger.info("PublishingHandler: All handlers registered")
