"""
Content manager for Telegram Auto Publisher Pro
Manages content creation, storage, and retrieval
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple
from enum import Enum

from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

from config import config
from database.models import (
    Content,
    MediaFile,
    User,
    TelegramAccount,
    ContentType,
    MediaType,
)
from database.repositories import (
    ContentRepository,
    MediaFileRepository,
    UserRepository,
    TelegramAccountRepository,
)
from security.validation import ValidationManager

logger = logging.getLogger(__name__)


@dataclass
class ContentData:
    """Data for creating new content"""
    
    user_id: int
    account_id: Optional[int] = None
    content_type: ContentType = ContentType.TEXT
    
    # Content data
    title: Optional[str] = None
    text: Optional[str] = None
    caption: Optional[str] = None
    
    # Media
    media_type: Optional[MediaType] = None
    media_file_path: Optional[Path] = None
    media_file_id: Optional[int] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    parse_mode: str = "HTML"


class ContentManager:
    """
    Manages content for publishing.
    Handles content creation, storage, retrieval, and management.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        validation_manager: ValidationManager = None
    ):
        """
        Initialize the content manager.
        
        Args:
            session_factory: Database session factory.
            validation_manager: Validation manager for input validation.
        """
        self.session_factory = session_factory
        self.validation_manager = validation_manager or ValidationManager()
        
        # Media directory
        self.media_dir = Path(config.MEDIA_DIR)
        self.media_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_content(
        self,
        content_data: ContentData
    ) -> Tuple[bool, Optional[Content], str]:
        """
        Create new content.
        
        Args:
            content_data: Content data for the new content.
            
        Returns:
            Tuple of (success, content, error_message).
        """
        try:
            # Validate content
            if content_data.content_type == ContentType.TEXT:
                if not content_data.text:
                    return False, None, "Text content is required"
                
                is_valid, error = self.validation_manager.validate_text_content(content_data.text)
                if not is_valid:
                    return False, None, error
            
            # Handle media upload
            media_file_id = None
            if content_data.media_file_path:
                media_file = await self._upload_media(
                    content_data.user_id,
                    content_data.media_file_path,
                    content_data.media_type
                )
                if media_file:
                    media_file_id = media_file.id
            
            # Create content record
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                
                content_data_dict = {
                    "user_id": content_data.user_id,
                    "account_id": content_data.account_id,
                    "content_type": content_data.content_type.value,
                    "media_type": content_data.media_type.value if content_data.media_type else None,
                    "media_file_id": media_file_id,
                    "title": content_data.title,
                    "text": content_data.text,
                    "caption": content_data.caption,
                    "parse_mode": content_data.parse_mode,
                    "tags": content_data.tags,
                    "category": content_data.category,
                    "is_active": True,
                    "is_published": False,
                    "created_at": datetime.utcnow()
                }
                
                content = await content_repo.create(content_data_dict)
                
                logger.info(f"Created content {content.id} for user {content_data.user_id}")
                return True, content, ""
                
        except Exception as e:
            logger.error(f"Error creating content: {e}")
            return False, None, str(e)
    
    async def _upload_media(
        self,
        user_id: int,
        file_path: Path,
        media_type: Optional[MediaType] = None
    ) -> Optional[MediaFile]:
        """
        Upload a media file.
        
        Args:
            user_id: The user ID.
            file_path: Path to the media file.
            media_type: The media type.
            
        Returns:
            The created MediaFile record, or None if failed.
        """
        try:
            # Validate file
            is_valid, error = self.validation_manager.validate_media_file(
                file_path,
                allowed_extensions=None
            )
            
            if not is_valid:
                logger.warning(f"Invalid media file: {error}")
                return None
            
            # Determine media type from file extension
            if not media_type:
                media_type = self._get_media_type_from_extension(file_path.suffix)
            
            # Copy file to media directory
            file_name = f"user_{user_id}_{datetime.utcnow().timestamp()}{file_path.suffix}"
            dest_path = self.media_dir / file_name
            
            # Copy the file
            with open(file_path, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            
            # Create media file record
            async with self.session_factory() as session:
                media_repo = MediaFileRepository(session)
                
                media_data = {
                    "user_id": user_id,
                    "file_name": file_path.name,
                    "file_path": str(dest_path),
                    "media_type": media_type.value,
                    "file_size": file_path.stat().st_size,
                    "mime_type": self._get_mime_type(file_path.suffix),
                    "is_uploaded": False,
                    "is_processed": False,
                    "created_at": datetime.utcnow()
                }
                
                media_file = await media_repo.create(media_data)
                
                logger.info(f"Uploaded media file {media_file.id} for user {user_id}")
                return media_file
                
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None
    
    def _get_media_type_from_extension(self, extension: str) -> MediaType:
        """
        Get media type from file extension.
        
        Args:
            extension: The file extension.
            
        Returns:
            The MediaType.
        """
        extension = extension.lower()
        
        if extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return MediaType.PHOTO
        elif extension in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return MediaType.VIDEO
        elif extension in ['.mp3', '.wav', '.ogg', '.m4a']:
            return MediaType.AUDIO
        elif extension in ['.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx']:
            return MediaType.DOCUMENT
        else:
            return MediaType.DOCUMENT
    
    def _get_mime_type(self, extension: str) -> str:
        """
        Get MIME type from file extension.
        
        Args:
            extension: The file extension.
            
        Returns:
            The MIME type string.
        """
        extension = extension.lower()
        
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        return mime_types.get(extension, 'application/octet-stream')
    
    async def get_content(self, content_id: int) -> Optional[Content]:
        """
        Get content by ID.
        
        Args:
            content_id: The content ID.
            
        Returns:
            The Content object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                return await content_repo.get_content_with_media(content_id)
        except Exception as e:
            logger.error(f"Error getting content {content_id}: {e}")
            return None
    
    async def get_contents_by_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Content]:
        """
        Get all contents for a user.
        
        Args:
            user_id: The user ID.
            limit: Maximum number of contents to return.
            offset: Offset for pagination.
            
        Returns:
            List of Content objects.
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                return await content_repo.get_contents_by_user(user_id, limit, offset)
        except Exception as e:
            logger.error(f"Error getting contents for user {user_id}: {e}")
            return []
    
    async def get_active_contents_by_user(self, user_id: int, limit: int = 100) -> List[Content]:
        """
        Get all active contents for a user.
        
        Args:
            user_id: The user ID.
            limit: Maximum number of contents to return.
            
        Returns:
            List of Content objects.
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                return await content_repo.get_active_contents_by_user(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting active contents for user {user_id}: {e}")
            return []
    
    async def get_random_content(self, user_id: int, exclude_id: int = None) -> Optional[Content]:
        """
        Get a random content for a user.
        
        Args:
            user_id: The user ID.
            exclude_id: Content ID to exclude.
            
        Returns:
            A random Content object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                return await content_repo.get_random_content(user_id, exclude_id)
        except Exception as e:
            logger.error(f"Error getting random content for user {user_id}: {e}")
            return None
    
    async def update_content(
        self,
        content_id: int,
        updates: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Update content.
        
        Args:
            content_id: The content ID.
            updates: Dictionary with fields to update.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                content = await content_repo.get_content(content_id)
                
                if not content:
                    return False, "Content not found"
                
                # Validate updates
                if 'text' in updates:
                    is_valid, error = self.validation_manager.validate_text_content(updates['text'])
                    if not is_valid:
                        return False, error
                
                await content_repo.update(content_id, updates)
                
                logger.info(f"Updated content {content_id}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error updating content {content_id}: {e}")
            return False, str(e)
    
    async def delete_content(self, content_id: int) -> Tuple[bool, str]:
        """
        Delete content.
        
        Args:
            content_id: The content ID.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                content = await content_repo.get_content(content_id)
                
                if not content:
                    return False, "Content not found"
                
                # Delete associated media file if it exists
                if content.media_file_id:
                    media_repo = MediaFileRepository(session)
                    media_file = await media_repo.get_media_file(content.media_file_id)
                    
                    if media_file:
                        # Delete the file from disk
                        if media_file.file_path and Path(media_file.file_path).exists():
                            Path(media_file.file_path).unlink()
                        
                        await media_repo.delete(content.media_file_id)
                
                await content_repo.delete(content_id)
                
                logger.info(f"Deleted content {content_id}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error deleting content {content_id}: {e}")
            return False, str(e)
    
    async def search_contents(
        self,
        user_id: int,
        query: str,
        limit: int = 10
    ) -> List[Content]:
        """
        Search contents by title or text.
        
        Args:
            user_id: The user ID.
            query: The search query.
            limit: Maximum number of results.
            
        Returns:
            List of Content objects matching the query.
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                return await content_repo.search_contents(user_id, query, limit)
        except Exception as e:
            logger.error(f"Error searching contents for user {user_id}: {e}")
            return []
    
    async def toggle_content_active(self, content_id: int, is_active: bool) -> Tuple[bool, str]:
        """
        Toggle content active status.
        
        Args:
            content_id: The content ID.
            is_active: Whether the content should be active.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                content = await content_repo.get_content(content_id)
                
                if not content:
                    return False, "Content not found"
                
                await content_repo.update(content_id, {"is_active": is_active})
                
                logger.info(f"Toggled content {content_id} active status to {is_active}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error toggling content {content_id} active status: {e}")
            return False, str(e)
    
    async def get_content_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get content statistics for a user.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Dictionary with content statistics.
        """
        try:
            async with self.session_factory() as session:
                content_repo = ContentRepository(session)
                
                total = await content_repo.count_by_user(user_id)
                active = len(await content_repo.get_active_contents_by_user(user_id))
                
                # Count by type
                text_count = await content_repo.count_by_type(user_id, ContentType.TEXT)
                image_count = await content_repo.count_by_type(user_id, ContentType.IMAGE)
                video_count = await content_repo.count_by_type(user_id, ContentType.VIDEO)
                document_count = await content_repo.count_by_type(user_id, ContentType.DOCUMENT)
                
                return {
                    "total": total,
                    "active": active,
                    "inactive": total - active,
                    "by_type": {
                        "text": text_count,
                        "image": image_count,
                        "video": video_count,
                        "document": document_count
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting content statistics for user {user_id}: {e}")
            return {
                "total": 0,
                "active": 0,
                "inactive": 0,
                "by_type": {}
            }
    
    async def import_content_from_message(
        self,
        user_id: int,
        message: Any,
        account_id: Optional[int] = None
    ) -> Tuple[bool, Optional[Content], str]:
        """
        Import content from a Telegram message.
        
        Args:
            user_id: The user ID.
            message: The Telegram message.
            account_id: Optional account ID.
            
        Returns:
            Tuple of (success, content, error_message).
        """
        try:
            content_type = ContentType.TEXT
            media_type = None
            media_file_id = None
            text = message.text or message.raw_text or ""
            
            # Check for media
            if hasattr(message, 'media') and message.media:
                media = message.media
                
                if isinstance(media, MessageMediaPhoto):
                    content_type = ContentType.IMAGE
                    media_type = MediaType.PHOTO
                elif isinstance(media, MessageMediaDocument):
                    # Check if it's a video document
                    if hasattr(media, 'document') and hasattr(media.document, 'mime_type'):
                        if 'video' in media.document.mime_type.lower():
                            content_type = ContentType.VIDEO
                            media_type = MediaType.VIDEO
                        else:
                            content_type = ContentType.DOCUMENT
                            media_type = MediaType.DOCUMENT
                    else:
                        content_type = ContentType.DOCUMENT
                        media_type = MediaType.DOCUMENT
            
            # Create content data
            content_data = ContentData(
                user_id=user_id,
                account_id=account_id,
                content_type=content_type,
                text=text,
                caption=message.caption if hasattr(message, 'caption') else None,
                media_type=media_type
            )
            
            # Create content
            success, content, error = await self.create_content(content_data)
            
            if success and content and message.media:
                # Download and save media
                # This is a placeholder - in a real implementation, we would download the media
                pass
            
            return success, content, error
            
        except Exception as e:
            logger.error(f"Error importing content from message: {e}")
            return False, None, str(e)


__all__ = [
    'ContentData',
    'ContentManager',
]
