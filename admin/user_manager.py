"""
User manager for Telegram Auto Publisher Pro
Manages user accounts and their data
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User,
    Administrator,
    TelegramAccount,
    Subscription,
    UserStatus,
    AdminRole,
    SubscriptionType,
    SubscriptionStatus,
)
from database.repositories import (
    UserRepository,
    AdministratorRepository,
    TelegramAccountRepository,
    SubscriptionRepository,
    AuditLogRepository,
)
from security.permissions import check_admin_access, check_super_admin_access
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """Information about a user"""
    
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    
    # Status
    status: UserStatus = UserStatus.ACTIVE
    is_bot: bool = False
    is_premium: bool = False
    
    # Subscription
    subscription_type: Optional[SubscriptionType] = None
    subscription_status: Optional[SubscriptionStatus] = None
    subscription_end_date: Optional[datetime] = None
    
    # Accounts
    account_count: int = 0
    connected_account_count: int = 0
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
    last_active_at: Optional[datetime] = None
    
    # Administrator info
    is_admin: bool = False
    admin_role: Optional[AdminRole] = None


class UserManager:
    """
    Manages users and their data.
    Provides user management functionality for administrators.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        audit_manager: AuditManager = None,
        config: any = None
    ):
        """
        Initialize the user manager.
        
        Args:
            session_factory: Database session factory.
            audit_manager: Audit manager instance.
            config: Application configuration.
        """
        self.session_factory = session_factory
        self.audit_manager = audit_manager
        self.config = config or config
    
    async def check_admin_access(self, admin_id: int) -> bool:
        """
        Check if an administrator has access to user management.
        
        Args:
            admin_id: The administrator ID.
            
        Returns:
            True if the administrator has access, False otherwise.
        """
        return await check_admin_access(admin_id, self.session_factory)
    
    async def check_super_admin_access(self, admin_id: int) -> bool:
        """
        Check if an administrator has super admin access.
        
        Args:
            admin_id: The administrator ID.
            
        Returns:
            True if the administrator has super admin access, False otherwise.
        """
        return await check_super_admin_access(admin_id, self.session_factory)
    
    async def get_user(self, user_id: int) -> Optional[UserInfo]:
        """
        Get information about a user.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            UserInfo object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user_with_subscription(user_id)
                
                if not user:
                    return None
                
                # Get account count
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
                connected_accounts = [a for a in accounts if a.is_connected]
                
                # Get admin info
                admin_repo = AdministratorRepository(session)
                admin = await admin_repo.get_administrator(user_id)
                
                # Create user info
                user_info = UserInfo(
                    id=user.id,
                    telegram_id=user.telegram_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=user.language_code,
                    status=UserStatus(user.status) if user.status else UserStatus.ACTIVE,
                    is_bot=user.is_bot,
                    is_premium=user.is_premium,
                    subscription_type=SubscriptionType(user.subscription.subscription_type) if user.subscription else None,
                    subscription_status=SubscriptionStatus(user.subscription.status) if user.subscription else None,
                    subscription_end_date=user.subscription.end_date if user.subscription else None,
                    account_count=len(accounts),
                    connected_account_count=len(connected_accounts),
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    last_active_at=user.last_active_at,
                    is_admin=admin is not None,
                    admin_role=AdminRole(admin.role) if admin else None
                )
                
                return user_info
                
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[UserInfo]:
        """
        Get user information by Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID.
            
        Returns:
            UserInfo object, or None if not found.
        """
        return await self.get_user(telegram_id)
    
    async def get_users(self, limit: int = 100, offset: int = 0) -> List[UserInfo]:
        """
        Get a list of all users.
        
        Args:
            limit: Maximum number of users to return.
            offset: Offset for pagination.
            
        Returns:
            List of UserInfo objects.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                users = await user_repo.get_all(limit, offset)
                
                user_infos = []
                for user in users:
                    user_info = await self.get_user(user.telegram_id)
                    if user_info:
                        user_infos.append(user_info)
                
                return user_infos
                
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    async def get_active_users(self, limit: int = 100) -> List[UserInfo]:
        """
        Get a list of active users.
        
        Args:
            limit: Maximum number of users to return.
            
        Returns:
            List of UserInfo objects for active users.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                users = await user_repo.get_active_users(limit)
                
                user_infos = []
                for user in users:
                    user_info = await self.get_user(user.telegram_id)
                    if user_info:
                        user_infos.append(user_info)
                
                return user_infos
                
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    async def get_blocked_users(self) -> List[UserInfo]:
        """
        Get a list of blocked users.
        
        Returns:
            List of UserInfo objects for blocked users.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                users = await user_repo.get_blocked_users()
                
                user_infos = []
                for user in users:
                    user_info = await self.get_user(user.telegram_id)
                    if user_info:
                        user_infos.append(user_info)
                
                return user_infos
                
        except Exception as e:
            logger.error(f"Error getting blocked users: {e}")
            return []
    
    async def search_users(self, query: str, limit: int = 10) -> List[UserInfo]:
        """
        Search users by username, first name, or last name.
        
        Args:
            query: The search query.
            limit: Maximum number of users to return.
            
        Returns:
            List of UserInfo objects matching the query.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                users = await user_repo.search_users(query, limit)
                
                user_infos = []
                for user in users:
                    user_info = await self.get_user(user.telegram_id)
                    if user_info:
                        user_infos.append(user_info)
                
                return user_infos
                
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> Tuple[bool, Optional[UserInfo], str]:
        """
        Create a new user.
        
        Args:
            telegram_id: The Telegram user ID.
            username: The user's username.
            first_name: The user's first name.
            last_name: The user's last name.
            language_code: The user's language code.
            
        Returns:
            Tuple of (success, user_info, error_message).
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                
                # Check if user already exists
                existing_user = await user_repo.get_user(telegram_id)
                if existing_user:
                    return False, None, "User already exists"
                
                # Create user
                user_data = {
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "language_code": language_code,
                    "status": UserStatus.ACTIVE.value,
                    "is_bot": False,
                    "is_premium": False,
                    "created_at": datetime.utcnow()
                }
                
                user = await user_repo.create(user_data)
                
                # Create user info
                user_info = await self.get_user(telegram_id)
                
                # Log the action
                if self.audit_manager:
                    await self.audit_manager.log_action(
                        administrator_id=0,  # System action
                        action="create_user",
                        action_type="user",
                        target_id=telegram_id,
                        target_type="user",
                        target_name=username or f"User {telegram_id}",
                        details={"telegram_id": telegram_id, "username": username}
                    )
                
                logger.info(f"Created user {telegram_id}")
                return True, user_info, ""
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, None, str(e)
    
    async def update_user(
        self,
        user_id: int,
        updates: Dict[str, Any],
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Update user information.
        
        Args:
            user_id: The Telegram user ID.
            updates: Dictionary with fields to update.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                # Check if we can update this field
                allowed_fields = ['first_name', 'last_name', 'language_code', 'status']
                filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
                
                if not filtered_updates:
                    return False, "No valid fields to update"
                
                # Update user
                await user_repo.update(user_id, filtered_updates)
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="update_user",
                        action_type="user",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details=updates,
                        old_values={},
                        new_values=updates
                    )
                
                logger.info(f"Updated user {user_id}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False, str(e)
    
    async def activate_user(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Activate a user.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self._change_user_status(
            user_id,
            UserStatus.ACTIVE,
            admin_id
        )
    
    async def deactivate_user(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Deactivate a user.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self._change_user_status(
            user_id,
            UserStatus.INACTIVE,
            admin_id
        )
    
    async def block_user(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Block a user.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self._change_user_status(
            user_id,
            UserStatus.BLOCKED,
            admin_id
        )
    
    async def unblock_user(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Unblock a user.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self._change_user_status(
            user_id,
            UserStatus.ACTIVE,
            admin_id
        )
    
    async def _change_user_status(
        self,
        user_id: int,
        status: UserStatus,
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Change user status.
        
        Args:
            user_id: The Telegram user ID.
            status: The new status.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                old_status = user.status
                
                # Update status
                await user_repo.update(user_id, {"status": status.value})
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action=f"change_user_status_{status.value}",
                        action_type="user",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={"old_status": old_status, "new_status": status.value}
                    )
                
                logger.info(f"Changed user {user_id} status to {status.value}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error changing user {user_id} status: {e}")
            return False, str(e)
    
    async def delete_user(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Delete a user and all their data.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                # Delete user's accounts
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
                for account in accounts:
                    await account_repo.delete(account.id)
                
                # Delete user's subscription
                subscription_repo = SubscriptionRepository(session)
                subscription = await subscription_repo.get_subscription_by_user(user_id)
                if subscription:
                    await subscription_repo.delete(subscription.id)
                
                # Delete user
                await user_repo.delete(user_id)
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="delete_user",
                        action_type="user",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={"telegram_id": user_id}
                    )
                
                logger.info(f"Deleted user {user_id}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False, str(e)
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                
                total = await user_repo.count()
                active = len(await user_repo.get_active_users())
                blocked = len(await user_repo.get_blocked_users())
                
                return {
                    "total": total,
                    "active": active,
                    "blocked": blocked,
                    "inactive": total - active - blocked
                }
                
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a User object by ID.
        
        Args:
            user_id: The user ID.
            
        Returns:
            User object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                return await user_repo.get_user(user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    async def update_last_active(self, user_id: int) -> bool:
        """
        Update user's last active timestamp.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            True if updated successfully, False otherwise.
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                return await user_repo.update_last_active(user_id)
        except Exception as e:
            logger.error(f"Error updating last active for user {user_id}: {e}")
            return False


__all__ = [
    'UserInfo',
    'UserManager',
]
