"""
Content handler for Telegram Auto Publisher Pro
Handles content management operations
"""

import logging
from typing import Optional, Any, Callable
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, User, InputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode, ContentType

from database.repositories import (
    UserRepository,
    ContentRepository,
    MediaFileRepository,
)
from bot.messages import Messages, Language
from bot.keyboards import MainKeyboard
from config import config

logger = logging.getLogger(__name__)


class ContentHandler:
    """
    Handles content management operations.
    """
    
    def __init__(
        self,
        bot: Bot = None,
        session_factory: Callable = None,
        content_manager: Any = None,
        media_manager: Any = None
    ):
        """
        Initialize the content handler.
        
        Args:
            bot: The aiogram Bot instance.
            session_factory: Database session factory.
            content_manager: Content manager instance.
            media_manager: Media manager instance.
        """
        self.bot = bot
        self.session_factory = session_factory
        self.content_manager = content_manager
        self.media_manager = media_manager
        
        # User language preferences
        self.user_languages: dict = {}
        self.user_states: dict = {}
    
    async def handle_content(self, message: Message):
        """
        Handle the /content command.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                user_content = await content_repo.get_all(filters={"user_id": user_id})
            
            # Show content menu
            keyboard = MainKeyboard(lang).get_content_menu_keyboard(len(user_content))
            await message.answer(
                messages.get_message("content_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
                
        except Exception as e:
            logger.error(f"Error handling /content: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_add_content(self, callback: CallbackQuery):
        """
        Handle add content callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Show content type selection
            keyboard = MainKeyboard(lang).get_content_type_keyboard()
            await callback.message.edit_text(
                messages.get_message("select_content_type"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling add_content: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_content_type(self, callback: CallbackQuery):
        """
        Handle content type selection.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get content type from callback data
            content_type = None
            if callback.data:
                content_type = callback.data.replace("content_type_", "")
            
            if not content_type:
                await callback.answer("Invalid content type", show_alert=True)
                return
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Store state
            self.user_states[user_id] = {
                "adding_content": True,
                "content_type": content_type
            }
            
            # Ask for title
            await callback.message.edit_text(
                messages.get_message("enter_content_title"),
                reply_markup=MainKeyboard(lang).get_back_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling content_type: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_content_title(self, message: Message):
        """
        Handle content title input.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            title = message.text.strip()
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            if not title:
                await message.answer(
                    messages.get_message("invalid_title"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Update state
            if user_id in self.user_states:
                self.user_states[user_id]["title"] = title
            
            # Ask for content based on type
            state = self.user_states.get(user_id, {})
            content_type = state.get("content_type", "text")
            
            if content_type == "text":
                await message.answer(
                    messages.get_message("enter_text_content"),
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    messages.get_message("send_media_file"),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling content_title: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_text_content(self, message: Message):
        """
        Handle text content input.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            text = message.text.strip()
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            if not text:
                await message.answer(
                    messages.get_message("invalid_content"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Get state
            state = self.user_states.get(user_id, {})
            
            # Save content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                
                content = await content_repo.create({
                    "user_id": user_id,
                    "title": state.get("title", "Untitled"),
                    "content": text,
                    "content_type": state.get("content_type", "text"),
                    "created_at": datetime.utcnow()
                })
            
            if content:
                # Clear state
                self.user_states[user_id] = {}
                
                await message.answer(
                    messages.get_message("content_added_success"),
                    parse_mode=ParseMode.HTML
                )
                
                # Show content list
                async with self.session_factory() as session:
                    content_repo = ContentRepository(session)
                    user_content = await content_repo.get_all(filters={"user_id": user_id})
                
                keyboard = MainKeyboard(lang).get_content_list_keyboard(user_content)
                await message.answer(
                    messages.get_message("your_content"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    messages.get_message("error_adding_content"),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling text_content: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_media_content(self, message: Message):
        """
        Handle media content (photo, video, document).
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get state
            state = self.user_states.get(user_id, {})
            content_type = state.get("content_type", "text")
            
            # Check if message has media
            if message.photo:
                file_id = message.photo[-1].file_id
                media_type = "photo"
            elif message.video:
                file_id = message.video.file_id
                media_type = "video"
            elif message.document:
                file_id = message.document.file_id
                media_type = "document"
            elif message.audio:
                file_id = message.audio.file_id
                media_type = "audio"
            else:
                await message.answer(
                    messages.get_message("invalid_media_type"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Save media file
            async with self.session_factory() as session:
                media_repo = MediaFileRepository(session)
                content_repo = ContentRepository(session)
                
                # Save media file info
                media = await media_repo.create({
                    "user_id": user_id,
                    "file_id": file_id,
                    "file_unique_id": file_id,
                    "media_type": media_type,
                    "file_name": getattr(message.document, 'file_name', None) or getattr(message.video, 'file_name', None) or "",
                    "file_size": getattr(message.document, 'file_size', 0) or getattr(message.video, 'file_size', 0) or 0,
                    "mime_type": getattr(message.document, 'mime_type', None) or "",
                    "uploaded_at": datetime.utcnow()
                })
                
                # Save content
                content = await content_repo.create({
                    "user_id": user_id,
                    "title": state.get("title", "Untitled"),
                    "content": f"[Media: {media_type}] {file_id}",
                    "content_type": content_type,
                    "media_file_id": media.id if media else None,
                    "created_at": datetime.utcnow()
                })
            
            if content:
                # Clear state
                self.user_states[user_id] = {}
                
                await message.answer(
                    messages.get_message("content_added_success"),
                    parse_mode=ParseMode.HTML
                )
                
                # Show content list
                async with self.session_factory() as session:
                    content_repo = ContentRepository(session)
                    user_content = await content_repo.get_all(filters={"user_id": user_id})
                
                keyboard = MainKeyboard(lang).get_content_list_keyboard(user_content)
                await message.answer(
                    messages.get_message("your_content"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    messages.get_message("error_adding_content"),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling media_content: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_my_content(self, callback: CallbackQuery):
        """
        Handle my content callback.
        
        Args:
            callback: The callback query.
        """
        try:
            user = callback.from_user
            user_id = user.id
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            # Get user content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                user_content = await content_repo.get_all(filters={"user_id": user_id})
            
            if not user_content:
                keyboard = MainKeyboard(lang).get_content_menu_keyboard(0)
                await callback.message.edit_text(
                    messages.get_message("no_content"),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback.answer()
                return
            
            # Show content list
            keyboard = MainKeyboard(lang).get_content_list_keyboard(user_content)
            await callback.message.edit_text(
                messages.get_message("your_content"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling my_content: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_content_details(self, callback: CallbackQuery):
        """
        Handle content details callback.
        
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
            
            # Get content details
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                content = await content_repo.get(content_id)
            
            if not content or content.user_id != user_id:
                await callback.answer("Content not found", show_alert=True)
                return
            
            # Show content details
            keyboard = MainKeyboard(lang).get_content_details_keyboard(content)
            await callback.message.edit_text(
                messages.get_message("content_details", content=content),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling content_details: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_edit_content(self, callback: CallbackQuery):
        """
        Handle edit content callback.
        
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
            
            # Get content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                content = await content_repo.get(content_id)
            
            if not content or content.user_id != user_id:
                await callback.answer("Content not found", show_alert=True)
                return
            
            # Store state
            self.user_states[user_id] = {
                "editing_content": True,
                "content_id": content_id,
                "content_type": content.content_type
            }
            
            # Ask for new title
            await callback.message.edit_text(
                messages.get_message("enter_new_title"),
                reply_markup=MainKeyboard(lang).get_back_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling edit_content: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_new_title(self, message: Message):
        """
        Handle new title input.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            title = message.text.strip()
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            if not title:
                await message.answer(
                    messages.get_message("invalid_title"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Update state
            if user_id in self.user_states:
                self.user_states[user_id]["title"] = title
            
            # Ask for new content
            state = self.user_states.get(user_id, {})
            content_type = state.get("content_type", "text")
            
            if content_type == "text":
                await message.answer(
                    messages.get_message("enter_new_text_content"),
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    messages.get_message("send_new_media_file"),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling new_title: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_new_text_content(self, message: Message):
        """
        Handle new text content input.
        
        Args:
            message: The incoming message.
        """
        try:
            user = message.from_user
            user_id = user.id
            text = message.text.strip()
            
            # Get user language
            lang = self.user_languages.get(user_id, Language.ENGLISH)
            messages = Messages(lang)
            
            if not text:
                await message.answer(
                    messages.get_message("invalid_content"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Get state
            state = self.user_states.get(user_id, {})
            content_id = state.get("content_id")
            
            if not content_id:
                await message.answer(
                    messages.get_message("error_updating_content"),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Update content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                
                content = await content_repo.update(content_id, {
                    "title": state.get("title", "Untitled"),
                    "content": text,
                    "updated_at": datetime.utcnow()
                })
            
            if content:
                # Clear state
                self.user_states[user_id] = {}
                
                await message.answer(
                    messages.get_message("content_updated_success"),
                    parse_mode=ParseMode.HTML
                )
                
                # Show content details
                keyboard = MainKeyboard(lang).get_content_details_keyboard(content)
                await message.answer(
                    messages.get_message("content_details", content=content),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.answer(
                    messages.get_message("error_updating_content"),
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error handling new_text_content: {e}")
            await message.answer(
                "An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    async def handle_delete_content(self, callback: CallbackQuery):
        """
        Handle delete content callback.
        
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
            
            # Confirm deletion
            keyboard = MainKeyboard(lang).get_confirm_delete_keyboard(content_id)
            await callback.message.edit_text(
                messages.get_message("confirm_delete_content"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling delete_content: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_confirm_delete_content(self, callback: CallbackQuery):
        """
        Handle confirm delete content callback.
        
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
            
            # Delete content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                success = await content_repo.delete(content_id)
            
            if success:
                await callback.answer("Content deleted", show_alert=True)
                
                # Refresh content list
                async with self.session_factory() as session:
                    content_repo = ContentRepository(session)
                    user_content = await content_repo.get_all(filters={"user_id": user_id})
                
                if user_content:
                    keyboard = MainKeyboard(lang).get_content_list_keyboard(user_content)
                    await callback.message.edit_text(
                        messages.get_message("your_content"),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    keyboard = MainKeyboard(lang).get_content_menu_keyboard(0)
                    await callback.message.edit_text(
                        messages.get_message("no_content"),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await callback.answer("Failed to delete content", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error handling confirm_delete_content: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def handle_back_to_content(self, callback: CallbackQuery):
        """
        Handle back to content callback.
        
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
            
            # Get user content
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                user_content = await content_repo.get_all(filters={"user_id": user_id})
            
            keyboard = MainKeyboard(lang).get_content_menu_keyboard(len(user_content))
            await callback.message.edit_text(
                messages.get_message("content_menu"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error handling back_to_content: {e}")
            await callback.answer("Error occurred", show_alert=True)
    
    async def register_handlers(self, dispatcher: Dispatcher) -> None:
        """
        Register all content handlers with the dispatcher.
        
        Args:
            dispatcher: The aiogram Dispatcher instance.
        """
        # Commands
        dispatcher.register_message_handler(
            self.handle_content,
            Command("content")
        )
        
        # Callbacks
        dispatcher.register_callback_query_handler(
            self.handle_add_content,
            F.data == "add_content"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_content_type,
            F.data.startswith("content_type_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_my_content,
            F.data == "my_content"
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_content_details,
            F.data.startswith("content_details_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_edit_content,
            F.data.startswith("edit_content_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_delete_content,
            F.data.startswith("delete_content_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_confirm_delete_content,
            F.data.startswith("confirm_delete_content_")
        )
        
        dispatcher.register_callback_query_handler(
            self.handle_back_to_content,
            F.data == "back_to_content"
        )
        
        # Text handlers
        # These would need state management in a real implementation
        dispatcher.register_message_handler(
            self.handle_content_title,
            lambda message: message.text and user_id in self.user_states and self.user_states.get(user_id, {}).get("adding_content") and "title" not in self.user_states.get(user_id, {})
        )
        
        dispatcher.register_message_handler(
            self.handle_text_content,
            lambda message: message.text and user_id in self.user_states and self.user_states.get(user_id, {}).get("adding_content") and self.user_states.get(user_id, {}).get("content_type") == "text" and "title" in self.user_states.get(user_id, {})
        )
        
        dispatcher.register_message_handler(
            self.handle_new_title,
            lambda message: message.text and user_id in self.user_states and self.user_states.get(user_id, {}).get("editing_content") and "title" not in self.user_states.get(user_id, {})
        )
        
        dispatcher.register_message_handler(
            self.handle_new_text_content,
            lambda message: message.text and user_id in self.user_states and self.user_states.get(user_id, {}).get("editing_content") and self.user_states.get(user_id, {}).get("content_type") == "text" and "title" in self.user_states.get(user_id, {})
        )
        
        # Media handlers
        dispatcher.register_message_handler(
            self.handle_media_content,
            lambda message: message.content_type in [ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT, ContentType.AUDIO] and user_id in self.user_states and self.user_states.get(user_id, {}).get("adding_content")
        )
        
        logger.info("ContentHandler: All handlers registered")
