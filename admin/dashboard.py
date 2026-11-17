"""
Admin dashboard for Telegram Auto Publisher Pro
Provides administrator access to system statistics and management
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User,
    Administrator,
    TelegramAccount,
    Subscription,
    PublishingTask,
    PublishingLog,
    Broadcast,
    AuditLog,
    UserStatus,
    AdminRole,
    SubscriptionType,
    SubscriptionStatus,
    TaskStatus,
)
from database.repositories import (
    UserRepository,
    AdministratorRepository,
    TelegramAccountRepository,
    SubscriptionRepository,
    PublishingTaskRepository,
    PublishingLogRepository,
    BroadcastRepository,
    AuditLogRepository,
    ApplicationSettingsRepository,
)
from security.permissions import check_admin_access, check_super_admin_access

logger = logging.getLogger(__name__)


@dataclass
class DashboardStats:
    """Dashboard statistics"""
    
    # User statistics
    total_users: int = 0
    active_users: int = 0
    blocked_users: int = 0
    inactive_users: int = 0
    
    # Account statistics
    total_accounts: int = 0
    connected_accounts: int = 0
    disconnected_accounts: int = 0
    
    # Subscription statistics
    total_subscriptions: int = 0
    free_subscriptions: int = 0
    premium_subscriptions: int = 0
    active_subscriptions: int = 0
    expired_subscriptions: int = 0
    
    # Administrator statistics
    total_admins: int = 0
    super_admins: int = 0
    regular_admins: int = 0
    moderators: int = 0
    support_staff: int = 0
    
    # Publishing statistics
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    # Broadcast statistics
    total_broadcasts: int = 0
    successful_broadcasts: int = 0
    failed_broadcasts: int = 0
    
    # System statistics
    bot_uptime: str = "0"
    database_status: str = "Unknown"
    
    # Recent activity
    recent_users: List[Dict[str, Any]] = field(default_factory=list)
    recent_tasks: List[Dict[str, Any]] = field(default_factory=list)
    recent_logs: List[Dict[str, Any]] = field(default_factory=list)


class AdminDashboard:
    """
    Administrator dashboard for Telegram Auto Publisher Pro.
    Provides access to system statistics, user management, and other admin features.
    """
    
    def __init__(
        self,
        config: any = None,
        user_manager: Any = None,
        admin_manager: Any = None,
        subscription_manager: Any = None,
        channel_manager: Any = None,
        statistics_manager: Any = None,
        audit_manager: Any = None,
        session_factory: Callable = None
    ):
        """
        Initialize the admin dashboard.
        
        Args:
            config: Application configuration.
            user_manager: User manager instance.
            admin_manager: Admin manager instance.
            subscription_manager: Subscription manager instance.
            channel_manager: Channel manager instance.
            statistics_manager: Statistics manager instance.
            audit_manager: Audit manager instance.
            session_factory: Database session factory.
        """
        self.config = config or config
        self.user_manager = user_manager
        self.admin_manager = admin_manager
        self.subscription_manager = subscription_manager
        self.channel_manager = channel_manager
        self.statistics_manager = statistics_manager
        self.audit_manager = audit_manager
        self.session_factory = session_factory
        
        # Bot start time
        self._bot_start_time = datetime.utcnow()
    
    async def check_admin_access(self, user_id: int) -> bool:
        """
        Check if a user has administrator access.
        
        Args:
            user_id: The user ID.
            
        Returns:
            True if the user is an administrator, False otherwise.
        """
        if self.admin_manager:
            return await self.admin_manager.is_admin(user_id)
        
        return await check_admin_access(user_id, self.session_factory)
    
    async def check_super_admin_access(self, user_id: int) -> bool:
        """
        Check if a user has super administrator access.
        
        Args:
            user_id: The user ID.
            
        Returns:
            True if the user is a super administrator, False otherwise.
        """
        if self.admin_manager:
            return await self.admin_manager.is_super_admin(user_id)
        
        return await check_super_admin_access(user_id, self.session_factory)
    
    async def get_dashboard_stats(self) -> DashboardStats:
        """
        Get dashboard statistics.
        
        Returns:
            DashboardStats object with all statistics.
        """
        stats = DashboardStats()
        
        try:
            async with self.session_factory() as session:
                # User statistics
                user_repo = UserRepository(session)
                stats.total_users = await user_repo.count()
                stats.active_users = len(await user_repo.get_active_users())
                stats.blocked_users = len(await user_repo.get_blocked_users())
                stats.inactive_users = stats.total_users - stats.active_users - stats.blocked_users
                
                # Get recent users
                stats.recent_users = [
                    {
                        "id": u.telegram_id,
                        "username": u.username,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "status": u.status,
                        "created_at": u.created_at
                    }
                    for u in (await user_repo.get_active_users(limit=5))
                ]
                
                # Account statistics
                account_repo = TelegramAccountRepository(session)
                all_accounts = await account_repo.get_all()
                stats.total_accounts = len(all_accounts)
                stats.connected_accounts = len([a for a in all_accounts if a.is_connected])
                stats.disconnected_accounts = stats.total_accounts - stats.connected_accounts
                
                # Subscription statistics
                subscription_repo = SubscriptionRepository(session)
                all_subscriptions = await subscription_repo.get_all()
                stats.total_subscriptions = len(all_subscriptions)
                stats.free_subscriptions = len([s for s in all_subscriptions if s.subscription_type == SubscriptionType.FREE.value])
                stats.premium_subscriptions = stats.total_subscriptions - stats.free_subscriptions
                stats.active_subscriptions = len([s for s in all_subscriptions if s.status == SubscriptionStatus.ACTIVE.value])
                stats.expired_subscriptions = len([s for s in all_subscriptions if s.status == SubscriptionStatus.EXPIRED.value])
                
                # Administrator statistics
                admin_repo = AdministratorRepository(session)
                all_admins = await admin_repo.get_all_active_admins()
                stats.total_admins = len(all_admins)
                stats.super_admins = len([a for a in all_admins if a.role == AdminRole.SUPER_ADMIN.value])
                stats.regular_admins = len([a for a in all_admins if a.role == AdminRole.ADMIN.value])
                stats.moderators = len([a for a in all_admins if a.role == AdminRole.MODERATOR.value])
                stats.support_staff = len([a for a in all_admins if a.role == AdminRole.SUPPORT.value])
                
                # Publishing statistics
                task_repo = PublishingTaskRepository(session)
                task_counts = await task_repo.count_by_status()
                stats.total_tasks = sum(task_counts.values())
                stats.pending_tasks = task_counts.get(TaskStatus.PENDING.value, 0)
                stats.running_tasks = task_counts.get(TaskStatus.RUNNING.value, 0)
                stats.completed_tasks = task_counts.get(TaskStatus.COMPLETED.value, 0)
                stats.failed_tasks = task_counts.get(TaskStatus.FAILED.value, 0)
                
                # Get recent tasks
                recent_tasks = await task_repo.get_tasks_by_status(TaskStatus.COMPLETED, limit=5)
                stats.recent_tasks = [
                    {
                        "id": t.id,
                        "user_id": t.user_id,
                        "account_id": t.account_id,
                        "status": t.status,
                        "scheduled_at": t.scheduled_at,
                        "completed_at": t.completed_at
                    }
                    for t in recent_tasks
                ]
                
                # Broadcast statistics
                broadcast_repo = BroadcastRepository(session)
                all_broadcasts = await broadcast_repo.get_all()
                stats.total_broadcasts = len(all_broadcasts)
                stats.successful_broadcasts = len([b for b in all_broadcasts if b.status == "sent"])
                stats.failed_broadcasts = len([b for b in all_broadcasts if b.status == "failed"])
                
                # Audit logs
                audit_repo = AuditLogRepository(session)
                recent_logs = await audit_repo.get_recent_logs(limit=5)
                stats.recent_logs = [
                    {
                        "id": log.id,
                        "administrator_id": log.administrator_id,
                        "action": log.action,
                        "action_type": log.action_type,
                        "target_type": log.target_type,
                        "target_id": log.target_id,
                        "success": log.success,
                        "created_at": log.created_at
                    }
                    for log in recent_logs
                ]
                
                # System statistics
                stats.bot_uptime = self._format_uptime(datetime.utcnow() - self._bot_start_time)
                
                # Database status
                stats.database_status = "Connected"
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
        
        return stats
    
    def _format_uptime(self, duration: timedelta) -> str:
        """
        Format a duration as a human-readable string.
        
        Args:
            duration: The duration to format.
            
        Returns:
            Formatted string.
        """
        total_seconds = int(duration.total_seconds())
        
        days = total_seconds // (24 * 3600)
        hours = (total_seconds % (24 * 3600)) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status information.
        
        Returns:
            Dictionary with system status information.
        """
        status = {
            "bot": {
                "status": "running",
                "version": self.config.APP_VERSION,
                "name": self.config.APP_NAME,
                "environment": self.config.ENVIRONMENT,
                "debug": self.config.DEBUG,
                "uptime": self._format_uptime(datetime.utcnow() - self._bot_start_time)
            },
            "database": {
                "status": "connected",
                "type": self.config.database.DB_TYPE
            },
            "scheduler": {
                "status": "enabled" if self.config.scheduler.ENABLED else "disabled",
                "timezone": self.config.scheduler.TIMEZONE
            }
        }
        
        try:
            # Check database connection
            if self.session_factory:
                from database.database import check_db_connection
                status["database"]["connected"] = await check_db_connection()
        except Exception as e:
            logger.error(f"Error checking database connection: {e}")
            status["database"]["connected"] = False
        
        return status
    
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
                
                # Count by registration date
                today = datetime.utcnow().date()
                yesterday = today - timedelta(days=1)
                this_week = today - timedelta(days=7)
                this_month = today - timedelta(days=30)
                
                users_today = len([
                    u for u in await user_repo.get_all()
                    if u.created_at and u.created_at.date() == today
                ])
                users_yesterday = len([
                    u for u in await user_repo.get_all()
                    if u.created_at and u.created_at.date() == yesterday
                ])
                users_this_week = len([
                    u for u in await user_repo.get_all()
                    if u.created_at and u.created_at.date() >= this_week
                ])
                users_this_month = len([
                    u for u in await user_repo.get_all()
                    if u.created_at and u.created_at.date() >= this_month
                ])
                
                return {
                    "total": total,
                    "active": active,
                    "blocked": blocked,
                    "inactive": total - active - blocked,
                    "today": users_today,
                    "yesterday": users_yesterday,
                    "this_week": users_this_week,
                    "this_month": users_this_month
                }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    async def get_account_statistics(self) -> Dict[str, Any]:
        """
        Get account statistics.
        
        Returns:
            Dictionary with account statistics.
        """
        try:
            async with self.session_factory() as session:
                account_repo = TelegramAccountRepository(session)
                
                total = await account_repo.count()
                connected = len(await account_repo.get_connected_accounts())
                
                # Count by user
                user_accounts = {}
                all_accounts = await account_repo.get_all()
                for account in all_accounts:
                    user_id = account.user_id
                    user_accounts[user_id] = user_accounts.get(user_id, 0) + 1
                
                # Find user with most accounts
                max_accounts = max(user_accounts.values()) if user_accounts else 0
                
                return {
                    "total": total,
                    "connected": connected,
                    "disconnected": total - connected,
                    "users_with_accounts": len(user_accounts),
                    "max_accounts_per_user": max_accounts
                }
        except Exception as e:
            logger.error(f"Error getting account statistics: {e}")
            return {}
    
    async def get_publishing_statistics(self) -> Dict[str, Any]:
        """
        Get publishing statistics.
        
        Returns:
            Dictionary with publishing statistics.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                log_repo = PublishingLogRepository(session)
                
                # Task statistics
                task_counts = await task_repo.count_by_status()
                
                # Log statistics
                total_logs = await log_repo.count()
                successful_logs = await log_repo.count_successful()
                failed_logs = await log_repo.count_failed()
                
                # Get recent activity
                recent_tasks = await task_repo.get_ready_tasks()
                
                return {
                    "tasks": task_counts,
                    "total_tasks": sum(task_counts.values()),
                    "logs": {
                        "total": total_logs,
                        "successful": successful_logs,
                        "failed": failed_logs,
                        "success_rate": (successful_logs / total_logs * 100) if total_logs > 0 else 0
                    },
                    "recent_activity": len(recent_tasks)
                }
        except Exception as e:
            logger.error(f"Error getting publishing statistics: {e}")
            return {}
    
    async def get_subscription_statistics(self) -> Dict[str, Any]:
        """
        Get subscription statistics.
        
        Returns:
            Dictionary with subscription statistics.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                
                all_subscriptions = await subscription_repo.get_all()
                
                # Count by type
                type_counts = {}
                for sub in all_subscriptions:
                    sub_type = sub.subscription_type
                    type_counts[sub_type] = type_counts.get(sub_type, 0) + 1
                
                # Count by status
                status_counts = {}
                for sub in all_subscriptions:
                    status = sub.status
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count premium vs free
                premium = len([s for s in all_subscriptions if s.subscription_type != SubscriptionType.FREE.value])
                free = len([s for s in all_subscriptions if s.subscription_type == SubscriptionType.FREE.value])
                
                return {
                    "total": len(all_subscriptions),
                    "by_type": type_counts,
                    "by_status": status_counts,
                    "premium": premium,
                    "free": free,
                    "active": status_counts.get(SubscriptionStatus.ACTIVE.value, 0),
                    "expired": status_counts.get(SubscriptionStatus.EXPIRED.value, 0)
                }
        except Exception as e:
            logger.error(f"Error getting subscription statistics: {e}")
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
                
                all_admins = await admin_repo.get_all_active_admins()
                
                # Count by role
                role_counts = {}
                for admin in all_admins:
                    role = admin.role
                    role_counts[role] = role_counts.get(role, 0) + 1
                
                return {
                    "total": len(all_admins),
                    "by_role": role_counts,
                    "super_admins": role_counts.get(AdminRole.SUPER_ADMIN.value, 0),
                    "admins": role_counts.get(AdminRole.ADMIN.value, 0),
                    "moderators": role_counts.get(AdminRole.MODERATOR.value, 0),
                    "support": role_counts.get(AdminRole.SUPPORT.value, 0)
                }
        except Exception as e:
            logger.error(f"Error getting admin statistics: {e}")
            return {}
    
    async def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent activity logs.
        
        Args:
            limit: Maximum number of logs to return.
            
        Returns:
            List of activity dictionaries.
        """
        try:
            async with self.session_factory() as session:
                audit_repo = AuditLogRepository(session)
                logs = await audit_repo.get_recent_logs(limit)
                
                return [
                    {
                        "id": log.id,
                        "administrator_id": log.administrator_id,
                        "action": log.action,
                        "action_type": log.action_type,
                        "target_type": log.target_type,
                        "target_id": log.target_id,
                        "target_name": log.target_name,
                        "success": log.success,
                        "error_message": log.error_message,
                        "created_at": log.created_at
                    }
                    for log in logs
                ]
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    async def get_system_settings(self) -> Dict[str, Any]:
        """
        Get system settings.
        
        Returns:
            Dictionary with system settings.
        """
        try:
            async with self.session_factory() as session:
                settings_repo = ApplicationSettingsRepository(session)
                settings = await settings_repo.get_settings()
                
                if not settings:
                    return {}
                
                return {
                    "app_name": settings.app_name,
                    "app_version": settings.app_version,
                    "app_description": settings.app_description,
                    "maintenance_mode": settings.maintenance_mode,
                    "maintenance_message": settings.maintenance_message
                }
        except Exception as e:
            logger.error(f"Error getting system settings: {e}")
            return {}
    
    async def update_system_settings(self, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update system settings.
        
        Args:
            settings: Dictionary with settings to update.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                settings_repo = ApplicationSettingsRepository(session)
                await settings_repo.set_settings(settings)
            
            logger.info("Updated system settings")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error updating system settings: {e}")
            return False, str(e)
    
    async def toggle_maintenance_mode(self, enable: bool) -> Tuple[bool, str]:
        """
        Toggle maintenance mode.
        
        Args:
            enable: Whether to enable maintenance mode.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                settings_repo = ApplicationSettingsRepository(session)
                await settings_repo.set_setting("maintenance_mode", enable)
            
            logger.info(f"Maintenance mode {'enabled' if enable else 'disabled'}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error toggling maintenance mode: {e}")
            return False, str(e)


__all__ = [
    'DashboardStats',
    'AdminDashboard',
]
