"""
Permission management for Telegram Auto Publisher Pro
Handles role-based access control and permission checks
"""

import functools
import logging
from typing import Callable, Optional, Any, Coroutine

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

from database.repositories import AdministratorRepository, UserRepository
from config import config

logger = logging.getLogger(__name__)


class PermissionManager:
    """
    Manages permission checks and role-based access control.
    """
    
    def __init__(self, session_factory: Callable = None):
        """
        Initialize the permission manager.
        
        Args:
            session_factory: A callable that returns an async database session.
        """
        self.session_factory = session_factory
    
    async def check_admin_access(self, user_id: int) -> bool:
        """
        Check if a user has administrator access.
        
        Args:
            user_id: The Telegram user ID to check.
            
        Returns:
            True if the user is an administrator, False otherwise.
        """
        if not self.session_factory:
            return False
        
        try:
            async with self.session_factory() as session:
                repo = AdministratorRepository(session)
                return await repo.is_admin(user_id)
        except Exception as e:
            logger.error(f"Error checking admin access: {e}")
            return False
    
    async def check_super_admin_access(self, user_id: int) -> bool:
        """
        Check if a user has super administrator access.
        
        Args:
            user_id: The Telegram user ID to check.
            
        Returns:
            True if the user is a super administrator, False otherwise.
        """
        if not self.session_factory:
            return False
        
        try:
            async with self.session_factory() as session:
                repo = AdministratorRepository(session)
                return await repo.is_super_admin(user_id)
        except Exception as e:
            logger.error(f"Error checking super admin access: {e}")
            return False
    
    async def check_user_active(self, user_id: int) -> bool:
        """
        Check if a user is active.
        
        Args:
            user_id: The Telegram user ID to check.
            
        Returns:
            True if the user is active, False otherwise.
        """
        if not self.session_factory:
            return True  # Assume active if we can't check
        
        try:
            async with self.session_factory() as session:
                repo = UserRepository(session)
                user = await repo.get_user(user_id)
                return user is not None and user.status == "active"
        except Exception as e:
            logger.error(f"Error checking user active status: {e}")
            return True  # Fail safe - assume active
    
    async def check_user_blocked(self, user_id: int) -> bool:
        """
        Check if a user is blocked.
        
        Args:
            user_id: The Telegram user ID to check.
            
        Returns:
            True if the user is blocked, False otherwise.
        """
        if not self.session_factory:
            return False
        
        try:
            async with self.session_factory() as session:
                repo = UserRepository(session)
                user = await repo.get_user(user_id)
                return user is not None and user.status == "blocked"
        except Exception as e:
            logger.error(f"Error checking user blocked status: {e}")
            return False
    
    async def get_admin_permissions(self, user_id: int) -> dict:
        """
        Get all permissions for an administrator.
        
        Args:
            user_id: The Telegram user ID to check.
            
        Returns:
            A dictionary of permissions.
        """
        if not self.session_factory:
            return {}
        
        try:
            async with self.session_factory() as session:
                repo = AdministratorRepository(session)
                return await repo.get_admin_permissions(user_id)
        except Exception as e:
            logger.error(f"Error getting admin permissions: {e}")
            return {}


# Permission check functions (can be used as decorators)

async def check_admin_access(user_id: int, session_factory: Callable = None) -> bool:
    """
    Check if a user has administrator access.
    
    Args:
        user_id: The Telegram user ID to check.
        session_factory: Optional session factory for database access.
        
    Returns:
        True if the user is an administrator, False otherwise.
    """
    if session_factory:
        manager = PermissionManager(session_factory)
        return await manager.check_admin_access(user_id)
    
    # Fallback to config-based check
    return user_id in [config.security.SUPER_ADMIN_ID] + config.security.ADMIN_IDS


async def check_super_admin_access(user_id: int, session_factory: Callable = None) -> bool:
    """
    Check if a user has super administrator access.
    
    Args:
        user_id: The Telegram user ID to check.
        session_factory: Optional session factory for database access.
        
    Returns:
        True if the user is a super administrator, False otherwise.
    """
    if session_factory:
        manager = PermissionManager(session_factory)
        return await manager.check_super_admin_access(user_id)
    
    # Fallback to config-based check
    return user_id == config.security.SUPER_ADMIN_ID


async def check_user_access(user_id: int, session_factory: Callable = None) -> bool:
    """
    Check if a user has access (not blocked).
    
    Args:
        user_id: The Telegram user ID to check.
        session_factory: Optional session factory for database access.
        
    Returns:
        True if the user has access, False otherwise.
    """
    if session_factory:
        manager = PermissionManager(session_factory)
        return await manager.check_user_active(user_id) and not await manager.check_user_blocked(user_id)
    
    return True  # Assume access if we can't check


# Decorators for permission checks

def require_admin(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """
    Decorator to require administrator access.
    
    Args:
        func: The handler function to decorate.
        
    Returns:
        The decorated function.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user_id from args
        user_id = None
        
        # Try to get user_id from Message or CallbackQuery
        for arg in args:
            if isinstance(arg, (Message, CallbackQuery)):
                user_id = arg.from_user.id
                break
        
        if user_id is None:
            # Try to get from kwargs
            user_id = kwargs.get('user_id')
        
        if user_id is None:
            logger.warning("Could not determine user_id for permission check")
            return None
        
        # Check admin access
        session_factory = kwargs.get('session_factory')
        if not await check_admin_access(user_id, session_factory):
            logger.warning(f"User {user_id} attempted to access admin-only function")
            return None
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_super_admin(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """
    Decorator to require super administrator access.
    
    Args:
        func: The handler function to decorate.
        
    Returns:
        The decorated function.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user_id from args
        user_id = None
        
        # Try to get user_id from Message or CallbackQuery
        for arg in args:
            if isinstance(arg, (Message, CallbackQuery)):
                user_id = arg.from_user.id
                break
        
        if user_id is None:
            # Try to get from kwargs
            user_id = kwargs.get('user_id')
        
        if user_id is None:
            logger.warning("Could not determine user_id for permission check")
            return None
        
        # Check super admin access
        session_factory = kwargs.get('session_factory')
        if not await check_super_admin_access(user_id, session_factory):
            logger.warning(f"User {user_id} attempted to access super admin-only function")
            return None
        
        return await func(*args, **kwargs)
    
    return wrapper


__all__ = [
    'PermissionManager',
    'check_admin_access',
    'check_super_admin_access',
    'check_user_access',
    'require_admin',
    'require_super_admin',
]
