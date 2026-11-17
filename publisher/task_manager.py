"""
Task manager for Telegram Auto Publisher Pro
Manages publishing tasks and their lifecycle
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Tuple
from enum import Enum

from config import config
from database.models import (
    PublishingTask,
    PublishingLog,
    TelegramAccount,
    Content,
    Group,
    TaskStatus,
    LogType,
)
from database.repositories import (
    PublishingTaskRepository,
    PublishingLogRepository,
    TelegramAccountRepository,
    ContentRepository,
    GroupRepository,
    AccountSettingsRepository,
)
from .engine import PublishingEngine, PublishConfig, PublishResultData
from .scheduler import TaskScheduler

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Task state enum"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a publishing task"""
    
    id: int
    user_id: int
    account_id: int
    group_id: Optional[int] = None
    content_id: Optional[int] = None
    
    # Task details
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    publish_at: Optional[datetime] = None
    timezone: str = "UTC"
    
    # Retry
    max_retries: int = 3
    retry_count: int = 0
    retry_delay_seconds: int = 60
    
    # Priority
    priority: int = 0
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Result
    result_message_id: Optional[int] = None
    result_message_link: Optional[str] = None
    error_message: Optional[str] = None


class TaskManager:
    """
    Manages publishing tasks and their lifecycle.
    Provides a higher-level interface for task management.
    """
    
    def __init__(
        self,
        publishing_engine: PublishingEngine = None,
        task_scheduler: TaskScheduler = None,
        session_factory: Callable = None
    ):
        """
        Initialize the task manager.
        
        Args:
            publishing_engine: Publishing engine instance.
            task_scheduler: Task scheduler instance.
            session_factory: Database session factory.
        """
        self.publishing_engine = publishing_engine
        self.task_scheduler = task_scheduler
        self.session_factory = session_factory
        
        # Task cache
        self._task_cache: Dict[int, TaskInfo] = {}
    
    async def create_task(
        self,
        user_id: int,
        account_id: int,
        content_id: Optional[int] = None,
        group_id: Optional[int] = None,
        text: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        priority: int = 0
    ) -> Tuple[bool, Optional[PublishingTask], str]:
        """
        Create a new publishing task.
        
        Args:
            user_id: The user ID.
            account_id: The account ID.
            content_id: The content ID to publish.
            group_id: The group ID to publish to.
            text: Text to publish.
            scheduled_at: When to publish (None for immediate).
            priority: Task priority.
            
        Returns:
            Tuple of (success, task, error_message).
        """
        try:
            # Validate inputs
            if not account_id:
                return False, None, "Account ID is required"
            
            if not content_id and not text:
                return False, None, "Content ID or text is required"
            
            if group_id:
                # Verify group exists and has permissions
                if self.task_scheduler and self.task_scheduler.account_manager:
                    group_manager = self.task_scheduler.account_manager.group_manager
                    if group_manager:
                        can_publish, error = await group_manager.can_publish_to_group(account_id, group_id)
                        if not can_publish:
                            return False, None, f"Cannot publish to group: {error}"
            
            # Create task in database
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                # Get account settings for retry configuration
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                task_data = {
                    "user_id": user_id,
                    "account_id": account_id,
                    "group_id": group_id,
                    "content_id": content_id,
                    "task_name": f"Publish to {group_id}" if group_id else "Publish",
                    "status": TaskStatus.PENDING.value,
                    "scheduled_at": scheduled_at or datetime.utcnow(),
                    "max_retries": settings.max_retries if settings else 3,
                    "retry_delay_seconds": settings.retry_delay_seconds if settings else 60,
                    "priority": priority,
                    "created_at": datetime.utcnow()
                }
                
                task = await task_repo.create(task_data)
                
                # Schedule the task
                if self.task_scheduler:
                    if not await self.task_scheduler.schedule_task(task):
                        # Delete the task if scheduling failed
                        await task_repo.delete(task.id)
                        return False, None, "Failed to schedule task"
                
                # Create task info and cache it
                task_info = await self._task_to_task_info(task)
                self._task_cache[task.id] = task_info
                
                logger.info(f"Created task {task.id} for account {account_id}")
                return True, task, ""
                
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return False, None, str(e)
    
    async def _task_to_task_info(self, task: PublishingTask) -> TaskInfo:
        """
        Convert a PublishingTask to TaskInfo.
        
        Args:
            task: The PublishingTask.
            
        Returns:
            TaskInfo object.
        """
        return TaskInfo(
            id=task.id,
            user_id=task.user_id,
            account_id=task.account_id,
            group_id=task.group_id,
            content_id=task.content_id,
            task_name=task.task_name,
            task_description=task.task_description,
            status=TaskStatus(task.status) if task.status else TaskStatus.PENDING,
            scheduled_at=task.scheduled_at,
            publish_at=task.publish_at,
            timezone=task.timezone or "UTC",
            max_retries=task.max_retries or 3,
            retry_count=task.retry_count or 0,
            retry_delay_seconds=task.retry_delay_seconds or 60,
            priority=task.priority or 0,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            failed_at=task.failed_at,
            result_message_id=task.result_message_id,
            result_message_link=task.result_message_link,
            error_message=task.error_message
        )
    
    async def get_task(self, task_id: int) -> Optional[TaskInfo]:
        """
        Get task information by ID.
        
        Args:
            task_id: The task ID.
            
        Returns:
            TaskInfo object, or None if not found.
        """
        # Check cache first
        if task_id in self._task_cache:
            return self._task_cache[task_id]
        
        # Get from database
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                task = await task_repo.get_task(task_id)
                
                if not task:
                    return None
                
                task_info = await self._task_to_task_info(task)
                self._task_cache[task_id] = task_info
                return task_info
                
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    async def get_tasks_by_user(self, user_id: int, limit: int = 100) -> List[TaskInfo]:
        """
        Get all tasks for a user.
        
        Args:
            user_id: The user ID.
            limit: Maximum number of tasks to return.
            
        Returns:
            List of TaskInfo objects.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_tasks_by_user(user_id, limit)
                
                task_infos = []
                for task in tasks:
                    task_info = await self._task_to_task_info(task)
                    task_infos.append(task_info)
                    self._task_cache[task.id] = task_info
                
                return task_infos
                
        except Exception as e:
            logger.error(f"Error getting tasks for user {user_id}: {e}")
            return []
    
    async def get_tasks_by_account(self, account_id: int, limit: int = 100) -> List[TaskInfo]:
        """
        Get all tasks for an account.
        
        Args:
            account_id: The account ID.
            limit: Maximum number of tasks to return.
            
        Returns:
            List of TaskInfo objects.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_tasks_by_account(account_id, limit)
                
                task_infos = []
                for task in tasks:
                    task_info = await self._task_to_task_info(task)
                    task_infos.append(task_info)
                    self._task_cache[task.id] = task_info
                
                return task_infos
                
        except Exception as e:
            logger.error(f"Error getting tasks for account {account_id}: {e}")
            return []
    
    async def get_pending_tasks(self, limit: int = 100) -> List[TaskInfo]:
        """
        Get all pending tasks.
        
        Args:
            limit: Maximum number of tasks to return.
            
        Returns:
            List of TaskInfo objects.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_tasks_by_status(TaskStatus.PENDING, limit)
                
                task_infos = []
                for task in tasks:
                    task_info = await self._task_to_task_info(task)
                    task_infos.append(task_info)
                    self._task_cache[task.id] = task_info
                
                return task_infos
                
        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []
    
    async def get_running_tasks(self) -> List[TaskInfo]:
        """
        Get all running tasks.
        
        Returns:
            List of TaskInfo objects.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_tasks_by_status(TaskStatus.RUNNING)
                
                task_infos = []
                for task in tasks:
                    task_info = await self._task_to_task_info(task)
                    task_infos.append(task_info)
                    self._task_cache[task.id] = task_info
                
                return task_infos
                
        except Exception as e:
            logger.error(f"Error getting running tasks: {e}")
            return []
    
    async def get_completed_tasks(self, limit: int = 100) -> List[TaskInfo]:
        """
        Get all completed tasks.
        
        Args:
            limit: Maximum number of tasks to return.
            
        Returns:
            List of TaskInfo objects.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_tasks_by_status(TaskStatus.COMPLETED, limit)
                
                task_infos = []
                for task in tasks:
                    task_info = await self._task_to_task_info(task)
                    task_infos.append(task_info)
                    self._task_cache[task.id] = task_info
                
                return task_infos
                
        except Exception as e:
            logger.error(f"Error getting completed tasks: {e}")
            return []
    
    async def get_failed_tasks(self, limit: int = 100) -> List[TaskInfo]:
        """
        Get all failed tasks.
        
        Args:
            limit: Maximum number of tasks to return.
            
        Returns:
            List of TaskInfo objects.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_tasks_by_status(TaskStatus.FAILED, limit)
                
                task_infos = []
                for task in tasks:
                    task_info = await self._task_to_task_info(task)
                    task_infos.append(task_info)
                    self._task_cache[task.id] = task_info
                
                return task_infos
                
        except Exception as e:
            logger.error(f"Error getting failed tasks: {e}")
            return []
    
    async def cancel_task(self, task_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Cancel a task.
        
        Args:
            task_id: The task ID.
            user_id: The user ID (for permission check).
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Get task
            task_info = await self.get_task(task_id)
            if not task_info:
                return False, "Task not found"
            
            # Check if user owns the task
            if task_info.user_id != user_id:
                return False, "You do not own this task"
            
            # Cancel the task
            if self.task_scheduler:
                if not await self.task_scheduler.cancel_task(task_id):
                    return False, "Failed to cancel task"
            
            # Update task status
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                await task_repo.update_task_status(
                    task_id,
                    TaskStatus.CANCELLED,
                    failed_at=datetime.utcnow()
                )
            
            # Update cache
            if task_id in self._task_cache:
                self._task_cache[task_id].status = TaskStatus.CANCELLED
                self._task_cache[task_id].failed_at = datetime.utcnow()
            
            logger.info(f"Cancelled task {task_id}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False, str(e)
    
    async def retry_task(self, task_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Retry a failed task.
        
        Args:
            task_id: The task ID.
            user_id: The user ID (for permission check).
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Get task
            task_info = await self.get_task(task_id)
            if not task_info:
                return False, "Task not found"
            
            # Check if user owns the task
            if task_info.user_id != user_id:
                return False, "You do not own this task"
            
            # Check if task can be retried
            if task_info.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False, "Task cannot be retried"
            
            # Reset retry count
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                await task_repo.update(task_id, {
                    "retry_count": 0,
                    "status": TaskStatus.PENDING.value,
                    "scheduled_at": datetime.utcnow()
                })
            
            # Reschedule the task
            if self.task_scheduler:
                async with self.session_factory() as session:
                    task_repo = PublishingTaskRepository(session)
                    task = await task_repo.get_task(task_id)
                    if task:
                        await self.task_scheduler.schedule_task(task)
            
            # Update cache
            if task_id in self._task_cache:
                self._task_cache[task_id].retry_count = 0
                self._task_cache[task_id].status = TaskStatus.PENDING
                self._task_cache[task_id].scheduled_at = datetime.utcnow()
            
            logger.info(f"Retried task {task_id}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error retrying task {task_id}: {e}")
            return False, str(e)
    
    async def delete_task(self, task_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Delete a task.
        
        Args:
            task_id: The task ID.
            user_id: The user ID (for permission check).
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            # Get task
            task_info = await self.get_task(task_id)
            if not task_info:
                return False, "Task not found"
            
            # Check if user owns the task
            if task_info.user_id != user_id:
                return False, "You do not own this task"
            
            # Cancel the task first
            if self.task_scheduler:
                await self.task_scheduler.cancel_task(task_id)
            
            # Delete the task
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                await task_repo.delete(task_id)
            
            # Remove from cache
            if task_id in self._task_cache:
                del self._task_cache[task_id]
            
            logger.info(f"Deleted task {task_id}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False, str(e)
    
    async def get_task_logs(self, task_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get logs for a specific task.
        
        Args:
            task_id: The task ID.
            limit: Maximum number of logs to return.
            
        Returns:
            List of log dictionaries.
        """
        try:
            async with self.session_factory() as session:
                log_repo = PublishingLogRepository(session)
                logs = await log_repo.get_logs_by_task(task_id, limit)
                
                log_list = []
                for log in logs:
                    log_list.append({
                        "id": log.id,
                        "log_type": log.log_type,
                        "operation": log.operation,
                        "message": log.message,
                        "success": log.success,
                        "error_message": log.error_message,
                        "target_type": log.target_type,
                        "target_id": log.target_id,
                        "target_name": log.target_name,
                        "content_type": log.content_type,
                        "content_id": log.content_id,
                        "created_at": log.created_at
                    })
                
                return log_list
                
        except Exception as e:
            logger.error(f"Error getting logs for task {task_id}: {e}")
            return []
    
    async def get_task_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get task statistics for a user.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Dictionary with task statistics.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                counts = await task_repo.count_by_status()
                
                return {
                    "total": sum(counts.values()),
                    "pending": counts.get(TaskStatus.PENDING.value, 0),
                    "running": counts.get(TaskStatus.RUNNING.value, 0),
                    "completed": counts.get(TaskStatus.COMPLETED.value, 0),
                    "failed": counts.get(TaskStatus.FAILED.value, 0),
                    "cancelled": counts.get(TaskStatus.CANCELLED.value, 0)
                }
                
        except Exception as e:
            logger.error(f"Error getting task statistics for user {user_id}: {e}")
            return {
                "total": 0,
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
    
    async def clear_completed_tasks(self, user_id: int, days: int = 30) -> int:
        """
        Clear completed tasks older than specified days.
        
        Args:
            user_id: The user ID.
            days: Number of days to keep completed tasks.
            
        Returns:
            Number of tasks deleted.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                # Get completed tasks older than cutoff
                tasks = await task_repo.get_tasks_by_user(user_id)
                
                deleted_count = 0
                for task in tasks:
                    if (task.status == TaskStatus.COMPLETED.value or 
                        task.status == TaskStatus.FAILED.value or
                        task.status == TaskStatus.CANCELLED.value) and \
                       task.completed_at and \
                       task.completed_at < cutoff_date:
                        
                        # Cancel the task first if it's scheduled
                        if self.task_scheduler:
                            await self.task_scheduler.cancel_task(task.id)
                        
                        await task_repo.delete(task.id)
                        
                        # Remove from cache
                        if task.id in self._task_cache:
                            del self._task_cache[task.id]
                        
                        deleted_count += 1
                
                logger.info(f"Cleared {deleted_count} old tasks for user {user_id}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error clearing old tasks for user {user_id}: {e}")
            return 0
    
    async def start_account_publishing(self, account_id: int, user_id: int) -> bool:
        """
        Start automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            user_id: The user ID.
            
        Returns:
            True if started successfully, False otherwise.
        """
        if self.task_scheduler:
            return await self.task_scheduler.start_account_publishing(account_id, user_id)
        return False
    
    async def stop_account_publishing(self, account_id: int, user_id: int) -> bool:
        """
        Stop automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            user_id: The user ID.
            
        Returns:
            True if stopped successfully, False otherwise.
        """
        if self.task_scheduler:
            return await self.task_scheduler.stop_account_publishing(account_id, user_id)
        return False
    
    async def pause_account_publishing(self, account_id: int, user_id: int) -> bool:
        """
        Pause automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            user_id: The user ID.
            
        Returns:
            True if paused successfully, False otherwise.
        """
        if self.task_scheduler:
            return await self.task_scheduler.pause_account_publishing(account_id, user_id)
        return False
    
    async def resume_account_publishing(self, account_id: int, user_id: int) -> bool:
        """
        Resume automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            user_id: The user ID.
            
        Returns:
            True if resumed successfully, False otherwise.
        """
        if self.task_scheduler:
            return await self.task_scheduler.resume_account_publishing(account_id, user_id)
        return False
    
    async def clear_cache(self):
        """Clear the task cache."""
        self._task_cache.clear()
        logger.info("Cleared task cache")


__all__ = [
    'TaskState',
    'TaskInfo',
    'TaskManager',
]
