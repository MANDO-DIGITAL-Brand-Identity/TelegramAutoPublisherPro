"""
Audit manager for Telegram Auto Publisher Pro
Manages audit logging and tracking of administrative actions
"""

import asyncio
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    Administrator,
    AuditLog,
)
from database.repositories import (
    AdministratorRepository,
    AuditLogRepository,
)
from security.permissions import check_admin_access, check_super_admin_access

logger = logging.getLogger(__name__)


class AuditActionType(str, Enum):
    """Types of audit actions"""
    
    # User actions
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_BLOCK = "user_block"
    USER_UNBLOCK = "user_unblock"
    USER_ACTIVATE = "user_activate"
    USER_DEACTIVATE = "user_deactivate"
    
    # Account actions
    ACCOUNT_CREATE = "account_create"
    ACCOUNT_UPDATE = "account_update"
    ACCOUNT_DELETE = "account_delete"
    ACCOUNT_CONNECT = "account_connect"
    ACCOUNT_DISCONNECT = "account_disconnect"
    
    # Subscription actions
    SUBSCRIPTION_CREATE = "subscription_create"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_DELETE = "subscription_delete"
    SUBSCRIPTION_ACTIVATE = "subscription_activate"
    SUBSCRIPTION_EXPIRE = "subscription_expire"
    SUBSCRIPTION_RENEW = "subscription_renew"
    
    # Channel actions
    CHANNEL_ADD = "channel_add"
    CHANNEL_UPDATE = "channel_update"
    CHANNEL_REMOVE = "channel_remove"
    CHANNEL_ENABLE = "channel_enable"
    CHANNEL_DISABLE = "channel_disable"
    
    # Broadcast actions
    BROADCAST_CREATE = "broadcast_create"
    BROADCAST_UPDATE = "broadcast_update"
    BROADCAST_DELETE = "broadcast_delete"
    BROADCAST_SEND = "broadcast_send"
    BROADCAST_SCHEDULE = "broadcast_schedule"
    BROADCAST_CANCEL = "broadcast_cancel"
    
    # Admin actions
    ADMIN_CREATE = "admin_create"
    ADMIN_UPDATE = "admin_update"
    ADMIN_DELETE = "admin_delete"
    ADMIN_ROLE_CHANGE = "admin_role_change"
    
    # Publishing actions
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_START = "task_start"
    TASK_STOP = "task_stop"
    TASK_PAUSE = "task_pause"
    TASK_RESUME = "task_resume"
    
    # Content actions
    CONTENT_CREATE = "content_create"
    CONTENT_UPDATE = "content_update"
    CONTENT_DELETE = "content_delete"
    
    # Group actions
    GROUP_ADD = "group_add"
    GROUP_UPDATE = "group_update"
    GROUP_REMOVE = "group_remove"
    
    # System actions
    SYSTEM_SETTINGS = "system_settings"
    MAINTENANCE_MODE = "maintenance_mode"
    BACKUP = "backup"
    RESTORE = "restore"
    DATABASE_MANAGEMENT = "database_management"
    
    # Other
    OTHER = "other"


@dataclass
class AuditLogInfo:
    """Information about an audit log entry"""
    
    id: Optional[int] = None
    administrator_id: int = 0
    administrator_name: Optional[str] = None
    
    # Action information
    action: str = ""
    action_type: Optional[str] = None
    
    # Target information
    target_id: Optional[int] = None
    target_type: Optional[str] = None
    target_name: Optional[str] = None
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)
    
    # Result
    success: Optional[bool] = None
    error_message: Optional[str] = None
    
    # IP and device information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None


@dataclass
class AuditStats:
    """Audit log statistics"""
    
    total_logs: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    
    # By action type
    action_type_counts: Dict[str, int] = field(default_factory=dict)
    
    # By administrator
    admin_action_counts: Dict[int, int] = field(default_factory=dict)
    
    # Recent logs
    recent_logs: List[AuditLogInfo] = field(default_factory=list)


class AuditManager:
    """
    Manages audit logging and tracking of administrative actions.
    Provides functionality for logging, retrieving, and analyzing audit logs.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        audit_log_repository: AuditLogRepository = None,
        administrator_repository: AdministratorRepository = None,
        config: any = None
    ):
        """
        Initialize the audit manager.
        
        Args:
            session_factory: Database session factory.
            audit_log_repository: Audit log repository instance.
            administrator_repository: Administrator repository instance.
            config: Application configuration.
        """
        self.session_factory = session_factory
        self.config = config or config
        
        # Initialize repositories
        if audit_log_repository:
            self.audit_log_repository = audit_log_repository
        else:
            self.audit_log_repository = AuditLogRepository(session_factory)
            
        if administrator_repository:
            self.administrator_repository = administrator_repository
        else:
            self.administrator_repository = AdministratorRepository(session_factory)
        
        # Sensitive fields that should never be logged
        self._sensitive_fields = {
            "password", "token", "secret", "key", "code", "verification",
            "session", "auth", "api_key", "api_secret", "private_key"
        }
        
        logger.info("AuditManager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the audit manager.
        """
        logger.info("AuditManager: Initializing...")
        
        # Verify database connection
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                count = await self.audit_log_repository.count()
                logger.info(f"AuditManager: Found {count} existing audit logs")
        except Exception as e:
            logger.error(f"AuditManager: Error initializing: {e}")
            raise
        
        logger.info("AuditManager: Initialized successfully")
    
    async def close(self) -> None:
        """
        Close the audit manager.
        """
        logger.info("AuditManager: Closed")
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize details to remove sensitive information.
        
        Args:
            details: The details dictionary.
            
        Returns:
            Sanitized details dictionary.
        """
        if not details:
            return details
        
        sanitized = {}
        for key, value in details.items():
            # Check if key contains sensitive information
            if any(sensitive in key.lower() for sensitive in self._sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, str):
                # Check if value looks like a sensitive field
                if any(sensitive in value.lower() for sensitive in self._sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def log_action(
        self,
        administrator_id: int,
        action: str,
        action_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLogInfo]:
        """
        Log an administrative action.
        
        Args:
            administrator_id: The administrator ID.
            action: The action description.
            action_type: The type of action.
            target_id: The ID of the target entity.
            target_type: The type of the target entity.
            target_name: The name of the target entity.
            details: Additional details about the action.
            old_values: The old values before the action.
            new_values: The new values after the action.
            success: Whether the action was successful.
            error_message: Error message if the action failed.
            ip_address: The IP address of the administrator.
            user_agent: The user agent of the administrator.
            
        Returns:
            AuditLogInfo object, or None if logging failed.
        """
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                
                # Sanitize sensitive information
                sanitized_details = self._sanitize_details(details or {})
                sanitized_old = self._sanitize_details(old_values or {})
                sanitized_new = self._sanitize_details(new_values or {})
                
                # Create audit log
                audit_log = await self.audit_log_repository.log_action(
                    administrator_id=administrator_id,
                    action=action,
                    action_type=action_type,
                    target_id=target_id,
                    target_type=target_type,
                    target_name=target_name,
                    details=sanitized_details,
                    old_values=sanitized_old,
                    new_values=sanitized_new,
                    success=success,
                    error_message=error_message,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Get administrator name
                admin = await self.administrator_repository.get(administrator_id)
                admin_name = admin.username if admin else f"Admin {administrator_id}"
                
                audit_log_info = AuditLogInfo(
                    id=audit_log.id,
                    administrator_id=administrator_id,
                    administrator_name=admin_name,
                    action=action,
                    action_type=action_type,
                    target_id=target_id,
                    target_type=target_type,
                    target_name=target_name,
                    details=sanitized_details,
                    old_values=sanitized_old,
                    new_values=sanitized_new,
                    success=success,
                    error_message=error_message,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    created_at=audit_log.created_at
                )
                
                logger.debug(f"AuditManager: Logged action '{action}' by admin {administrator_id}")
                return audit_log_info
                
        except Exception as e:
            logger.error(f"AuditManager: Error logging action: {e}")
            return None
    
    async def log_user_action(
        self,
        administrator_id: int,
        action: str,
        user_id: int,
        user_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLogInfo]:
        """
        Log a user-related action.
        
        Args:
            administrator_id: The administrator ID.
            action: The action description.
            user_id: The user ID.
            user_name: The user name.
            details: Additional details.
            success: Whether the action was successful.
            error_message: Error message if the action failed.
            
        Returns:
            AuditLogInfo object, or None if logging failed.
        """
        return await self.log_action(
            administrator_id=administrator_id,
            action=action,
            action_type=AuditActionType.USER_UPDATE.value,
            target_id=user_id,
            target_type="user",
            target_name=user_name,
            details=details,
            success=success,
            error_message=error_message
        )
    
    async def log_account_action(
        self,
        administrator_id: int,
        action: str,
        account_id: int,
        account_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLogInfo]:
        """
        Log an account-related action.
        
        Args:
            administrator_id: The administrator ID.
            action: The action description.
            account_id: The account ID.
            account_name: The account name.
            details: Additional details.
            success: Whether the action was successful.
            error_message: Error message if the action failed.
            
        Returns:
            AuditLogInfo object, or None if logging failed.
        """
        return await self.log_action(
            administrator_id=administrator_id,
            action=action,
            action_type=AuditActionType.ACCOUNT_UPDATE.value,
            target_id=account_id,
            target_type="telegram_account",
            target_name=account_name,
            details=details,
            success=success,
            error_message=error_message
        )
    
    async def log_subscription_action(
        self,
        administrator_id: int,
        action: str,
        subscription_id: int,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLogInfo]:
        """
        Log a subscription-related action.
        
        Args:
            administrator_id: The administrator ID.
            action: The action description.
            subscription_id: The subscription ID.
            user_id: The user ID.
            details: Additional details.
            success: Whether the action was successful.
            error_message: Error message if the action failed.
            
        Returns:
            AuditLogInfo object, or None if logging failed.
        """
        return await self.log_action(
            administrator_id=administrator_id,
            action=action,
            action_type=AuditActionType.SUBSCRIPTION_UPDATE.value,
            target_id=subscription_id,
            target_type="subscription",
            target_name=f"Subscription {subscription_id}",
            details=details,
            success=success,
            error_message=error_message
        )
    
    async def log_admin_action(
        self,
        administrator_id: int,
        action: str,
        target_admin_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Optional[AuditLogInfo]:
        """
        Log an admin-related action.
        
        Args:
            administrator_id: The administrator ID performing the action.
            action: The action description.
            target_admin_id: The target administrator ID.
            details: Additional details.
            success: Whether the action was successful.
            error_message: Error message if the action failed.
            
        Returns:
            AuditLogInfo object, or None if logging failed.
        """
        return await self.log_action(
            administrator_id=administrator_id,
            action=action,
            action_type=AuditActionType.ADMIN_UPDATE.value,
            target_id=target_admin_id,
            target_type="administrator",
            target_name=f"Admin {target_admin_id}" if target_admin_id else None,
            details=details,
            success=success,
            error_message=error_message
        )
    
    async def get_audit_logs(
        self,
        administrator_id: Optional[int] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        descending: bool = True
    ) -> List[AuditLogInfo]:
        """
        Get audit logs with optional filters.
        
        Args:
            administrator_id: Filter by administrator ID.
            action_type: Filter by action type.
            target_type: Filter by target type.
            target_id: Filter by target ID.
            success: Filter by success status.
            start_date: Filter by start date.
            end_date: Filter by end date.
            limit: Maximum number of logs to return.
            offset: Offset for pagination.
            order_by: Field to order by.
            descending: Whether to order in descending order.
            
        Returns:
            List of AuditLogInfo objects.
        """
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                
                filters = {}
                if administrator_id is not None:
                    filters["administrator_id"] = administrator_id
                if action_type is not None:
                    filters["action_type"] = action_type
                if target_type is not None:
                    filters["target_type"] = target_type
                if target_id is not None:
                    filters["target_id"] = target_id
                if success is not None:
                    filters["success"] = success
                
                from sqlalchemy import and_, or_
                from database.models import AuditLog
                
                # Add date filters
                date_filters = []
                if start_date:
                    date_filters.append(AuditLog.created_at >= start_date)
                if end_date:
                    date_filters.append(AuditLog.created_at <= end_date)
                
                all_filters = [AuditLog.administrator_id == v for k, v in filters.items()]
                if date_filters:
                    all_filters.extend(date_filters)
                
                logs = await self.audit_log_repository.get_all(
                    filters=filters,
                    limit=limit,
                    offset=offset,
                    order_by=order_by,
                    descending=descending
                )
                
                # Get administrator names
                admin_ids = set(log.administrator_id for log in logs)
                admins = await self.administrator_repository.get_all(
                    filters={"user_id": list(admin_ids)}
                ) if admin_ids else []
                admin_map = {admin.user_id: admin.username for admin in admins}
                
                return [
                    AuditLogInfo(
                        id=log.id,
                        administrator_id=log.administrator_id,
                        administrator_name=admin_map.get(log.administrator_id, f"Admin {log.administrator_id}"),
                        action=log.action,
                        action_type=log.action_type,
                        target_id=log.target_id,
                        target_type=log.target_type,
                        target_name=log.target_name,
                        details=log.details or {},
                        old_values=log.old_values or {},
                        new_values=log.new_values or {},
                        success=log.success,
                        error_message=log.error_message,
                        ip_address=log.ip_address,
                        user_agent=log.user_agent,
                        created_at=log.created_at
                    )
                    for log in logs
                ]
                
        except Exception as e:
            logger.error(f"AuditManager: Error getting audit logs: {e}")
            return []
    
    async def get_recent_logs(self, limit: int = 20) -> List[AuditLogInfo]:
        """
        Get the most recent audit logs.
        
        Args:
            limit: Maximum number of logs to return.
            
        Returns:
            List of AuditLogInfo objects.
        """
        return await self.get_audit_logs(
            limit=limit,
            order_by="created_at",
            descending=True
        )
    
    async def get_logs_by_admin(self, administrator_id: int, limit: int = 50) -> List[AuditLogInfo]:
        """
        Get audit logs for a specific administrator.
        
        Args:
            administrator_id: The administrator ID.
            limit: Maximum number of logs to return.
            
        Returns:
            List of AuditLogInfo objects.
        """
        return await self.get_audit_logs(
            administrator_id=administrator_id,
            limit=limit,
            order_by="created_at",
            descending=True
        )
    
    async def get_logs_by_action_type(self, action_type: str, limit: int = 50) -> List[AuditLogInfo]:
        """
        Get audit logs by action type.
        
        Args:
            action_type: The action type to filter by.
            limit: Maximum number of logs to return.
            
        Returns:
            List of AuditLogInfo objects.
        """
        return await self.get_audit_logs(
            action_type=action_type,
            limit=limit,
            order_by="created_at",
            descending=True
        )
    
    async def get_logs_by_target(self, target_type: str, target_id: int, limit: int = 50) -> List[AuditLogInfo]:
        """
        Get audit logs by target type and ID.
        
        Args:
            target_type: The target type.
            target_id: The target ID.
            limit: Maximum number of logs to return.
            
        Returns:
            List of AuditLogInfo objects.
        """
        return await self.get_audit_logs(
            target_type=target_type,
            target_id=target_id,
            limit=limit,
            order_by="created_at",
            descending=True
        )
    
    async def get_statistics(self, days: int = 30) -> AuditStats:
        """
        Get audit log statistics.
        
        Args:
            days: Number of days to include in statistics.
            
        Returns:
            AuditStats object.
        """
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                
                from sqlalchemy import select, func, and_
                from database.models import AuditLog
                
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Total logs
                total_logs = await session.scalar(
                    select(func.count()).select_from(AuditLog).where(
                        AuditLog.created_at >= start_date
                    )
                ) or 0
                
                # Successful and failed actions
                successful_actions = await session.scalar(
                    select(func.count()).select_from(AuditLog).where(
                        and_(
                            AuditLog.created_at >= start_date,
                            AuditLog.success == True
                        )
                    )
                ) or 0
                
                failed_actions = await session.scalar(
                    select(func.count()).select_from(AuditLog).where(
                        and_(
                            AuditLog.created_at >= start_date,
                            AuditLog.success == False
                        )
                    )
                ) or 0
                
                # By action type
                action_types = await session.execute(
                    select(
                        AuditLog.action_type,
                        func.count()
                    ).select_from(AuditLog)
                    .where(AuditLog.created_at >= start_date)
                    .group_by(AuditLog.action_type)
                )
                action_type_counts = {row[0]: row[1] for row in action_types if row[0]}
                
                # By administrator
                admin_actions = await session.execute(
                    select(
                        AuditLog.administrator_id,
                        func.count()
                    ).select_from(AuditLog)
                    .where(AuditLog.created_at >= start_date)
                    .group_by(AuditLog.administrator_id)
                )
                admin_action_counts = {row[0]: row[1] for row in admin_actions if row[0]}
                
                # Recent logs
                recent_logs_result = await session.execute(
                    select(AuditLog)
                    .where(AuditLog.created_at >= start_date)
                    .order_by(AuditLog.created_at.desc())
                    .limit(10)
                )
                recent_logs_db = recent_logs_result.scalars().all()
                
                # Get administrator names
                admin_ids = set(log.administrator_id for log in recent_logs_db)
                admins = await self.administrator_repository.get_all(
                    filters={"user_id": list(admin_ids)}
                ) if admin_ids else []
                admin_map = {admin.user_id: admin.username for admin in admins}
                
                recent_logs = [
                    AuditLogInfo(
                        id=log.id,
                        administrator_id=log.administrator_id,
                        administrator_name=admin_map.get(log.administrator_id, f"Admin {log.administrator_id}"),
                        action=log.action,
                        action_type=log.action_type,
                        target_id=log.target_id,
                        target_type=log.target_type,
                        target_name=log.target_name,
                        details=log.details or {},
                        old_values=log.old_values or {},
                        new_values=log.new_values or {},
                        success=log.success,
                        error_message=log.error_message,
                        ip_address=log.ip_address,
                        user_agent=log.user_agent,
                        created_at=log.created_at
                    )
                    for log in recent_logs_db
                ]
                
                return AuditStats(
                    total_logs=total_logs,
                    successful_actions=successful_actions,
                    failed_actions=failed_actions,
                    action_type_counts=action_type_counts,
                    admin_action_counts=admin_action_counts,
                    recent_logs=recent_logs
                )
                
        except Exception as e:
            logger.error(f"AuditManager: Error getting statistics: {e}")
            return AuditStats()
    
    async def search_logs(
        self,
        query: str,
        limit: int = 50
    ) -> List[AuditLogInfo]:
        """
        Search audit logs by query string.
        
        Args:
            query: The search query.
            limit: Maximum number of logs to return.
            
        Returns:
            List of AuditLogInfo objects matching the query.
        """
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                
                from sqlalchemy import or_, text
                from database.models import AuditLog
                
                # Search in action, action_type, target_name, and details
                search_filters = [
                    AuditLog.action.ilike(f"%{query}%"),
                    AuditLog.action_type.ilike(f"%{query}%"),
                    AuditLog.target_name.ilike(f"%{query}%"),
                ]
                
                # For details, we need to use JSON functions (PostgreSQL) or string search
                # This is a simplified approach
                logs = await self.audit_log_repository.get_all(
                    filters={},
                    limit=limit,
                    order_by="created_at",
                    descending=True
                )
                
                # Filter in Python (for simplicity, in production use database JSON functions)
                filtered_logs = []
                for log in logs:
                    if (query.lower() in (log.action or "").lower() or
                        query.lower() in (log.action_type or "").lower() or
                        query.lower() in (log.target_name or "").lower()):
                        filtered_logs.append(log)
                
                # Get administrator names
                admin_ids = set(log.administrator_id for log in filtered_logs)
                admins = await self.administrator_repository.get_all(
                    filters={"user_id": list(admin_ids)}
                ) if admin_ids else []
                admin_map = {admin.user_id: admin.username for admin in admins}
                
                return [
                    AuditLogInfo(
                        id=log.id,
                        administrator_id=log.administrator_id,
                        administrator_name=admin_map.get(log.administrator_id, f"Admin {log.administrator_id}"),
                        action=log.action,
                        action_type=log.action_type,
                        target_id=log.target_id,
                        target_type=log.target_type,
                        target_name=log.target_name,
                        details=log.details or {},
                        old_values=log.old_values or {},
                        new_values=log.new_values or {},
                        success=log.success,
                        error_message=log.error_message,
                        ip_address=log.ip_address,
                        user_agent=log.user_agent,
                        created_at=log.created_at
                    )
                    for log in filtered_logs[:limit]
                ]
                
        except Exception as e:
            logger.error(f"AuditManager: Error searching logs: {e}")
            return []
    
    async def export_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> str:
        """
        Export audit logs to a specified format.
        
        Args:
            start_date: Start date for export.
            end_date: End date for export.
            format: Export format (json, csv).
            
        Returns:
            Exported data as string.
        """
        logs = await self.get_audit_logs(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        if format == "json":
            return json.dumps(
                [
                    {
                        "id": log.id,
                        "administrator_id": log.administrator_id,
                        "administrator_name": log.administrator_name,
                        "action": log.action,
                        "action_type": log.action_type,
                        "target_id": log.target_id,
                        "target_type": log.target_type,
                        "target_name": log.target_name,
                        "details": log.details,
                        "old_values": log.old_values,
                        "new_values": log.new_values,
                        "success": log.success,
                        "error_message": log.error_message,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    }
                    for log in logs
                ],
                indent=2
            )
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "Admin ID", "Admin Name", "Action", "Action Type",
                "Target ID", "Target Type", "Target Name", "Success",
                "Error Message", "IP Address", "User Agent", "Created At"
            ])
            
            # Write rows
            for log in logs:
                writer.writerow([
                    log.id,
                    log.administrator_id,
                    log.administrator_name or "",
                    log.action or "",
                    log.action_type or "",
                    log.target_id or "",
                    log.target_type or "",
                    log.target_name or "",
                    log.success,
                    log.error_message or "",
                    log.ip_address or "",
                    log.user_agent or "",
                    log.created_at.isoformat() if log.created_at else ""
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Clean up old audit logs.
        
        Args:
            days: Number of days to keep logs.
            
        Returns:
            Number of logs deleted.
        """
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                
                from sqlalchemy import delete, and_
                from database.models import AuditLog
                
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Delete logs older than cutoff
                stmt = delete(AuditLog).where(
                    AuditLog.created_at < cutoff_date
                )
                
                result = await session.execute(stmt)
                count = result.rowcount
                await session.commit()
                
                logger.info(f"AuditManager: Cleaned up {count} old audit logs")
                return count
                
        except Exception as e:
            logger.error(f"AuditManager: Error cleaning up old logs: {e}")
            return 0
