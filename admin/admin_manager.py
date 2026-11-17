"""
Admin manager for Telegram Auto Publisher Pro
Manages administrator accounts and permissions
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
    AdminRole,
    UserStatus,
)
from database.repositories import (
    UserRepository,
    AdministratorRepository,
    AuditLogRepository,
)
from security.permissions import check_admin_access, check_super_admin_access
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


@dataclass
class AdminInfo:
    """Information about an administrator"""
    
    user_id: int
    role: AdminRole
    is_active: bool = True
    
    # User information
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Permissions
    can_manage_users: bool = True
    can_manage_accounts: bool = True
    can_manage_subscriptions: bool = True
    can_manage_channels: bool = True
    can_manage_broadcasts: bool = True
    can_manage_settings: bool = False
    can_view_audit_logs: bool = True
    can_manage_admins: bool = False
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
    last_login_at: Optional[datetime] = None


class AdminManager:
    """
    Manages administrator accounts and permissions.
    Provides functionality for adding, removing, and managing administrators.
    """
    
    def __init__(
        self,
        config: any = None,
        session_factory: Callable = None,
        audit_manager: AuditManager = None
    ):
        """
        Initialize the admin manager.
        
        Args:
            config: Application configuration.
            session_factory: Database session factory.
            audit_manager: Audit manager instance.
        """
        self.config = config or config
        self.session_factory = session_factory
        self.audit_manager = audit_manager
    
    async def is_admin(self, user_id: int) -> bool:
        """
        Check if a user is an administrator.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            True if the user is an administrator, False otherwise.
        """
        return await check_admin_access(user_id, self.session_factory)
    
    async def is_super_admin(self, user_id: int) -> bool:
        """
        Check if a user is a super administrator.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            True if the user is a super administrator, False otherwise.
        """
        return await check_super_admin_access(user_id, self.session_factory)
    
    async def get_admin(self, user_id: int) -> Optional[AdminInfo]:
        """
        Get information about an administrator.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            AdminInfo object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                admin_repo = AdministratorRepository(session)
                admin = await admin_repo.get_administrator_with_user(user_id)
                
                if not admin:
                    return None
                
                return AdminInfo(
                    user_id=admin.user_id,
                    role=AdminRole(admin.role) if admin.role else AdminRole.ADMIN,
                    is_active=admin.is_active,
                    username=admin.user.username if admin.user else None,
                    first_name=admin.user.first_name if admin.user else None,
                    last_name=admin.user.last_name if admin.user else None,
                    can_manage_users=admin.can_manage_users,
                    can_manage_accounts=admin.can_manage_accounts,
                    can_manage_subscriptions=admin.can_manage_subscriptions,
                    can_manage_channels=admin.can_manage_channels,
                    can_manage_broadcasts=admin.can_manage_broadcasts,
                    can_manage_settings=admin.can_manage_settings,
                    can_view_audit_logs=admin.can_view_audit_logs,
                    can_manage_admins=admin.can_manage_admins,
                    created_at=admin.created_at,
                    updated_at=admin.updated_at,
                    last_login_at=admin.last_login_at
                )
                
        except Exception as e:
            logger.error(f"Error getting admin {user_id}: {e}")
            return None
    
    async def get_admins(self, limit: int = 100) -> List[AdminInfo]:
        """
        Get a list of all administrators.
        
        Args:
            limit: Maximum number of administrators to return.
            
        Returns:
            List of AdminInfo objects.
        """
        try:
            async with self.session_factory() as session:
                admin_repo = AdministratorRepository(session)
                admins = await admin_repo.get_all_active_admins()
                
                admin_infos = []
                for admin in admins:
                    admin_info = await self.get_admin(admin.user_id)
                    if admin_info:
                        admin_infos.append(admin_info)
                
                return admin_infos
                
        except Exception as e:
            logger.error(f"Error getting admins: {e}")
            return []
    
    async def get_admins_by_role(self, role: AdminRole) -> List[AdminInfo]:
        """
        Get administrators by role.
        
        Args:
            role: The admin role to filter by.
            
        Returns:
            List of AdminInfo objects with the specified role.
        """
        try:
            async with self.session_factory() as session:
                admin_repo = AdministratorRepository(session)
                admins = await admin_repo.get_admins_by_role(role)
                
                admin_infos = []
                for admin in admins:
                    admin_info = await self.get_admin(admin.user_id)
                    if admin_info:
                        admin_infos.append(admin_info)
                
                return admin_infos
                
        except Exception as e:
            logger.error(f"Error getting admins by role {role}: {e}")
            return []
    
    async def get_super_admins(self) -> List[AdminInfo]:
        """
        Get all super administrators.
        
        Returns:
            List of AdminInfo objects for super administrators.
        """
        return await self.get_admins_by_role(AdminRole.SUPER_ADMIN)
    
    async def add_admin(
        self,
        user_id: int,
        role: AdminRole = AdminRole.ADMIN,
        permissions: Optional[Dict[str, bool]] = None,
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Add a new administrator.
        
        Args:
            user_id: The Telegram user ID to make an administrator.
            role: The admin role to assign.
            permissions: Optional dictionary with custom permissions.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Check if the requesting admin has permission
            if admin_id and not await self.is_super_admin(admin_id):
                return False, "Only super admins can add administrators"
            
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                # Check if user is already an admin
                admin_repo = AdministratorRepository(session)
                existing_admin = await admin_repo.get_administrator(user_id)
                if existing_admin:
                    return False, "User is already an administrator"
                
                # Set default permissions based on role
                default_permissions = self._get_default_permissions(role)
                if permissions:
                    default_permissions.update(permissions)
                
                # Create admin
                admin_data = {
                    "user_id": user_id,
                    "role": role.value,
                    "is_active": True,
                    "can_manage_users": default_permissions.get("can_manage_users", True),
                    "can_manage_accounts": default_permissions.get("can_manage_accounts", True),
                    "can_manage_subscriptions": default_permissions.get("can_manage_subscriptions", True),
                    "can_manage_channels": default_permissions.get("can_manage_channels", True),
                    "can_manage_broadcasts": default_permissions.get("can_manage_broadcasts", True),
                    "can_manage_settings": default_permissions.get("can_manage_settings", False),
                    "can_view_audit_logs": default_permissions.get("can_view_audit_logs", True),
                    "can_manage_admins": default_permissions.get("can_manage_admins", False),
                    "created_at": datetime.utcnow()
                }
                
                await admin_repo.create(admin_data)
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="add_admin",
                        action_type="admin",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={"role": role.value, **default_permissions}
                    )
                
                logger.info(f"Added admin {user_id} with role {role.value}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error adding admin {user_id}: {e}")
            return False, str(e)
    
    def _get_default_permissions(self, role: AdminRole) -> Dict[str, bool]:
        """
        Get default permissions for a role.
        
        Args:
            role: The admin role.
            
        Returns:
            Dictionary with default permissions.
        """
        if role == AdminRole.SUPER_ADMIN:
            return {
                "can_manage_users": True,
                "can_manage_accounts": True,
                "can_manage_subscriptions": True,
                "can_manage_channels": True,
                "can_manage_broadcasts": True,
                "can_manage_settings": True,
                "can_view_audit_logs": True,
                "can_manage_admins": True
            }
        elif role == AdminRole.ADMIN:
            return {
                "can_manage_users": True,
                "can_manage_accounts": True,
                "can_manage_subscriptions": True,
                "can_manage_channels": True,
                "can_manage_broadcasts": True,
                "can_manage_settings": False,
                "can_view_audit_logs": True,
                "can_manage_admins": False
            }
        elif role == AdminRole.MODERATOR:
            return {
                "can_manage_users": True,
                "can_manage_accounts": True,
                "can_manage_subscriptions": False,
                "can_manage_channels": True,
                "can_manage_broadcasts": False,
                "can_manage_settings": False,
                "can_view_audit_logs": True,
                "can_manage_admins": False
            }
        else:  # SUPPORT
            return {
                "can_manage_users": False,
                "can_manage_accounts": False,
                "can_manage_subscriptions": False,
                "can_manage_channels": False,
                "can_manage_broadcasts": False,
                "can_manage_settings": False,
                "can_view_audit_logs": True,
                "can_manage_admins": False
            }
    
    async def remove_admin(
        self,
        user_id: int,
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Remove an administrator.
        
        Args:
            user_id: The Telegram user ID to remove from administrators.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Check if the requesting admin has permission
            if admin_id:
                if not await self.is_super_admin(admin_id):
                    # Check if the admin is trying to remove themselves
                    if user_id == admin_id:
                        return False, "Cannot remove yourself"
                    return False, "Only super admins can remove administrators"
            
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                admin_repo = AdministratorRepository(session)
                admin = await admin_repo.get_administrator(user_id)
                
                if not admin:
                    return False, "User is not an administrator"
                
                # Don't allow removing the last super admin
                if admin.role == AdminRole.SUPER_ADMIN.value:
                    super_admins = await admin_repo.get_admins_by_role(AdminRole.SUPER_ADMIN)
                    if len(super_admins) <= 1:
                        return False, "Cannot remove the last super administrator"
                
                await admin_repo.delete(admin.id)
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="remove_admin",
                        action_type="admin",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={"role": admin.role}
                    )
                
                logger.info(f"Removed admin {user_id}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error removing admin {user_id}: {e}")
            return False, str(e)
    
    async def update_admin_role(
        self,
        user_id: int,
        new_role: AdminRole,
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Update an administrator's role.
        
        Args:
            user_id: The Telegram user ID.
            new_role: The new role to assign.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Check if the requesting admin has permission
            if admin_id and not await self.is_super_admin(admin_id):
                return False, "Only super admins can change admin roles"
            
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                admin_repo = AdministratorRepository(session)
                admin = await admin_repo.get_administrator(user_id)
                
                if not admin:
                    return False, "User is not an administrator"
                
                old_role = admin.role
                
                # Update role
                await admin_repo.update(admin.id, {"role": new_role.value})
                
                # Update permissions based on new role
                permissions = self._get_default_permissions(new_role)
                await admin_repo.update(admin.id, permissions)
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="update_admin_role",
                        action_type="admin",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={"old_role": old_role, "new_role": new_role.value}
                    )
                
                logger.info(f"Updated admin {user_id} role to {new_role.value}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error updating admin {user_id} role: {e}")
            return False, str(e)
    
    async def update_admin_permissions(
        self,
        user_id: int,
        permissions: Dict[str, bool],
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Update an administrator's permissions.
        
        Args:
            user_id: The Telegram user ID.
            permissions: Dictionary with permissions to update.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Check if the requesting admin has permission
            if admin_id and not await self.is_super_admin(admin_id):
                return False, "Only super admins can change admin permissions"
            
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                admin_repo = AdministratorRepository(session)
                admin = await admin_repo.get_administrator(user_id)
                
                if not admin:
                    return False, "User is not an administrator"
                
                # Get old permissions
                old_permissions = {
                    "can_manage_users": admin.can_manage_users,
                    "can_manage_accounts": admin.can_manage_accounts,
                    "can_manage_subscriptions": admin.can_manage_subscriptions,
                    "can_manage_channels": admin.can_manage_channels,
                    "can_manage_broadcasts": admin.can_manage_broadcasts,
                    "can_manage_settings": admin.can_manage_settings,
                    "can_view_audit_logs": admin.can_view_audit_logs,
                    "can_manage_admins": admin.can_manage_admins
                }
                
                # Update permissions
                await admin_repo.update(admin.id, permissions)
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="update_admin_permissions",
                        action_type="admin",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        old_values=old_permissions,
                        new_values=permissions
                    )
                
                logger.info(f"Updated admin {user_id} permissions")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error updating admin {user_id} permissions: {e}")
            return False, str(e)
    
    async def activate_admin(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Activate an administrator.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self._change_admin_status(user_id, True, admin_id)
    
    async def deactivate_admin(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Deactivate an administrator.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self._change_admin_status(user_id, False, admin_id)
    
    async def _change_admin_status(
        self,
        user_id: int,
        is_active: bool,
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Change administrator active status.
        
        Args:
            user_id: The Telegram user ID.
            is_active: Whether the admin should be active.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Check if the requesting admin has permission
            if admin_id and not await self.is_super_admin(admin_id):
                return False, "Only super admins can change admin status"
            
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, "User not found"
                
                admin_repo = AdministratorRepository(session)
                admin = await admin_repo.get_administrator(user_id)
                
                if not admin:
                    return False, "User is not an administrator"
                
                # Update status
                await admin_repo.update(admin.id, {"is_active": is_active})
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action=f"{'activate' if is_active else 'deactivate'}_admin",
                        action_type="admin",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={"is_active": is_active}
                    )
                
                logger.info(f"{'Activated' if is_active else 'Deactivated'} admin {user_id}")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error changing admin {user_id} status: {e}")
            return False, str(e)
    
    async def get_admin_permissions(self, user_id: int) -> Dict[str, bool]:
        """
        Get an administrator's permissions.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            Dictionary with the administrator's permissions.
        """
        try:
            async with self.session_factory() as session:
                admin_repo = AdministratorRepository(session)
                return await admin_repo.get_admin_permissions(user_id)
        except Exception as e:
            logger.error(f"Error getting admin {user_id} permissions: {e}")
            return {}
    
    async def get_admin_statistics(self) -> Dict[str, Any]:
        """
        Get administrator statistics.
        
        Returns:
            Dictionary with administrator statistics.
        """
        try:
            async with self.session_factory() as session:
                admin_repo = AdministratorRepository(session)
                
                total = len(await admin_repo.get_all_active_admins())
                super_admins = len(await admin_repo.get_admins_by_role(AdminRole.SUPER_ADMIN))
                admins = len(await admin_repo.get_admins_by_role(AdminRole.ADMIN))
                moderators = len(await admin_repo.get_admins_by_role(AdminRole.MODERATOR))
                support = len(await admin_repo.get_admins_by_role(AdminRole.SUPPORT))
                
                return {
                    "total": total,
                    "super_admins": super_admins,
                    "admins": admins,
                    "moderators": moderators,
                    "support": support
                }
                
        except Exception as e:
            logger.error(f"Error getting admin statistics: {e}")
            return {}
    
    async def get_admins_with_permission(self, permission: str) -> List[AdminInfo]:
        """
        Get administrators with a specific permission.
        
        Args:
            permission: The permission to check for.
            
        Returns:
            List of AdminInfo objects with the specified permission.
        """
        try:
            async with self.session_factory() as session:
                admin_repo = AdministratorRepository(session)
                all_admins = await admin_repo.get_all_active_admins()
                
                admin_infos = []
                for admin in all_admins:
                    permissions = await admin_repo.get_admin_permissions(admin.user_id)
                    if permissions.get(permission, False):
                        admin_info = await self.get_admin(admin.user_id)
                        if admin_info:
                            admin_infos.append(admin_info)
                
                return admin_infos
                
        except Exception as e:
            logger.error(f"Error getting admins with permission {permission}: {e}")
            return []


__all__ = [
    'AdminInfo',
    'AdminManager',
]
