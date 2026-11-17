"""
Task scheduler for Telegram Auto Publisher Pro
Handles scheduled publishing tasks using APScheduler
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Set
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from config import config
from database.models import (
    PublishingTask,
    TelegramAccount,
    Content,
    Group,
    TaskStatus,
)
from database.repositories import (
    PublishingTaskRepository,
    TelegramAccountRepository,
    ContentRepository,
    GroupRepository,
    AccountSettingsRepository,
)
from .engine import PublishingEngine, PublishConfig, PublishResultData
from accounts.manager import AccountManager

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type enum"""
    PUBLISH = "publish"
    SCHEDULED_PUBLISH = "scheduled_publish"
    RECURRING_PUBLISH = "recurring_publish"


class TaskScheduler:
    """
    Scheduler for publishing tasks.
    Uses APScheduler for scheduling and manages task execution.
    """
    
    def __init__(
        self,
        config: any = None,
        publishing_engine: PublishingEngine = None,
        session_factory: Callable = None
    ):
        """
        Initialize the task scheduler.
        
        Args:
            config: Application configuration.
            publishing_engine: Publishing engine instance.
            session_factory: Database session factory.
        """
        self.config = config or config
        self.publishing_engine = publishing_engine
        self.session_factory = session_factory
        
        # Scheduler
        self.scheduler = AsyncIOScheduler(timezone=self.config.scheduler.TIMEZONE)
        
        # Task tracking
        self._active_tasks: Dict[str, Any] = {}
        self._task_jobs: Dict[str, Any] = {}
        
        # Account manager for getting clients
        self.account_manager = None
        
        # Notification manager
        self.notification_manager = None
    
    def set_dependencies(
        self,
        account_manager: AccountManager = None,
        notification_manager: Any = None
    ):
        """
        Set optional dependencies.
        
        Args:
            account_manager: Account manager instance.
            notification_manager: Notification manager instance.
        """
        self.account_manager = account_manager
        self.notification_manager = notification_manager
    
    async def start(self):
        """Start the scheduler."""
        if self.config.scheduler.ENABLED:
            self.scheduler.start()
            logger.info("Task scheduler started")
        else:
            logger.info("Task scheduler is disabled")
    
    async def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Task scheduler stopped")
    
    async def schedule_task(
        self,
        task: PublishingTask
    ) -> bool:
        """
        Schedule a publishing task.
        
        Args:
            task: The publishing task to schedule.
            
        Returns:
            True if scheduled successfully, False otherwise.
        """
        try:
            # Check if task is already scheduled
            if str(task.id) in self._task_jobs:
                logger.warning(f"Task {task.id} is already scheduled")
                return False
            
            # Check if task should be executed immediately
            if task.status == TaskStatus.PENDING.value and task.scheduled_at <= datetime.utcnow():
                # Execute immediately
                await self._execute_task(task)
                return True
            
            # Schedule the task
            if task.scheduled_at:
                # Schedule at specific time
                trigger = DateTrigger(run_date=task.scheduled_at)
            elif task.schedule_cron:
                # Schedule using cron
                trigger = CronTrigger.from_crontab(task.schedule_cron)
            else:
                # Schedule immediately
                trigger = DateTrigger(run_date=datetime.utcnow())
            
            # Add the job
            job = self.scheduler.add_job(
                self._execute_task,
                trigger,
                args=[task],
                id=str(task.id),
                replace_existing=True
            )
            
            self._task_jobs[str(task.id)] = job
            logger.info(f"Scheduled task {task.id} for {task.scheduled_at}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling task {task.id}: {e}")
            return False
    
    async def schedule_tasks(self):
        """Schedule all pending tasks from the database."""
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                tasks = await task_repo.get_pending_tasks()
                
                for task in tasks:
                    await self.schedule_task(task)
            
            logger.info(f"Scheduled {len(tasks)} pending tasks")
            
        except Exception as e:
            logger.error(f"Error scheduling tasks: {e}")
    
    async def _execute_task(self, task: PublishingTask):
        """
        Execute a publishing task.
        
        Args:
            task: The publishing task to execute.
        """
        try:
            # Update task status
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                await task_repo.update_task_status(
                    task.id,
                    TaskStatus.RUNNING,
                    started_at=datetime.utcnow()
                )
            
            # Prepare publish config
            config = PublishConfig(
                account_id=task.account_id,
                group_id=task.group_id,
                content_id=task.content_id,
                text=None,  # Will be loaded from content
                schedule_time=task.scheduled_at
            )
            
            # Execute publishing
            result = await self.publishing_engine.publish(config)
            
            # Update task status
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                if result.result.value == "success":
                    await task_repo.update_task_status(
                        task.id,
                        TaskStatus.COMPLETED,
                        completed_at=datetime.utcnow(),
                        result_message_id=result.message_id
                    )
                    
                    # Log the result
                    log_repo = PublishingLogRepository(session)
                    await log_repo.create({
                        "task_id": task.id,
                        "account_id": task.account_id,
                        "user_id": task.user_id,
                        "log_type": LogType.PUBLISH.value,
                        "operation": "publish",
                        "success": True,
                        "target_type": "group",
                        "target_id": task.group_id,
                        "content_type": "text",
                        "content_id": task.content_id
                    })
                else:
                    # Retry if needed
                    if task.retry_count < task.max_retries:
                        await task_repo.increment_retry_count(task.id)
                        
                        # Reschedule with delay
                        retry_delay = task.retry_delay_seconds or self.config.scheduler.RETRY_DELAY_SECONDS
                        new_scheduled_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                        
                        await task_repo.update(task.id, {
                            "scheduled_at": new_scheduled_at,
                            "status": TaskStatus.PENDING.value
                        })
                        
                        # Reschedule the task
                        await self.schedule_task(task)
                    else:
                        await task_repo.update_task_status(
                            task.id,
                            TaskStatus.FAILED,
                            failed_at=datetime.utcnow(),
                            error_message=result.error_message
                        )
                        
                        # Log the failure
                        log_repo = PublishingLogRepository(session)
                        await log_repo.create({
                            "task_id": task.id,
                            "account_id": task.account_id,
                            "user_id": task.user_id,
                            "log_type": LogType.ERROR.value,
                            "operation": "publish",
                            "success": False,
                            "target_type": "group",
                            "target_id": task.group_id,
                            "content_type": "text",
                            "content_id": task.content_id,
                            "error_message": result.error_message
                        })
            
            # Send notification
            if self.notification_manager:
                if result.result.value == "success":
                    await self.notification_manager.notify_task_success(task.id, task.user_id)
                else:
                    await self.notification_manager.notify_task_failure(task.id, task.user_id, result.error_message)
            
            # Clean up
            if str(task.id) in self._task_jobs:
                del self._task_jobs[str(task.id)]
            
            logger.info(f"Executed task {task.id}: {result.result.value}")
            
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}")
            
            # Update task status
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                await task_repo.update_task_status(
                    task.id,
                    TaskStatus.FAILED,
                    failed_at=datetime.utcnow(),
                    error_message=str(e)
                )
            
            # Clean up
            if str(task.id) in self._task_jobs:
                del self._task_jobs[str(task.id)]
    
    async def cancel_task(self, task_id: int) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: The task ID.
            
        Returns:
            True if cancelled successfully, False otherwise.
        """
        try:
            # Remove from scheduler
            if str(task_id) in self._task_jobs:
                self._task_jobs[str(task_id)].remove()
                del self._task_jobs[str(task_id)]
            
            # Update task status
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                await task_repo.update_task_status(
                    task_id,
                    TaskStatus.CANCELLED,
                    failed_at=datetime.utcnow()
                )
            
            logger.info(f"Cancelled task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    async def recover_tasks(self) -> int:
        """
        Recover interrupted tasks from the database.
        
        Returns:
            Number of tasks recovered.
        """
        count = 0
        
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                # Get all running tasks (they were interrupted)
                running_tasks = await task_repo.get_tasks_by_status(TaskStatus.RUNNING)
                
                for task in running_tasks:
                    # Mark as pending for rescheduling
                    await task_repo.update_task_status(
                        task.id,
                        TaskStatus.PENDING
                    )
                    
                    # Schedule the task
                    if await self.schedule_task(task):
                        count += 1
            
            logger.info(f"Recovered {count} interrupted tasks")
            
        except Exception as e:
            logger.error(f"Error recovering tasks: {e}")
        
        return count
    
    async def get_scheduled_tasks(self) -> List[PublishingTask]:
        """
        Get all scheduled tasks.
        
        Returns:
            List of scheduled tasks.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                return await task_repo.get_scheduled_tasks()
        except Exception as e:
            logger.error(f"Error getting scheduled tasks: {e}")
            return []
    
    async def get_ready_tasks(self) -> List[PublishingTask]:
        """
        Get all tasks that are ready to be executed.
        
        Returns:
            List of ready tasks.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                return await task_repo.get_ready_tasks()
        except Exception as e:
            logger.error(f"Error getting ready tasks: {e}")
            return []
    
    async def create_publishing_task(
        self,
        user_id: int,
        account_id: int,
        content_id: Optional[int] = None,
        group_id: Optional[int] = None,
        scheduled_at: Optional[datetime] = None,
        text: Optional[str] = None
    ) -> Optional[PublishingTask]:
        """
        Create a new publishing task.
        
        Args:
            user_id: The user ID.
            account_id: The account ID.
            content_id: The content ID.
            group_id: The group ID.
            scheduled_at: The scheduled time.
            text: The text to publish.
            
        Returns:
            The created task, or None if failed.
        """
        try:
            async with self.session_factory() as session:
                task_repo = PublishingTaskRepository(session)
                
                # Get account settings for defaults
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                task_data = {
                    "user_id": user_id,
                    "account_id": account_id,
                    "content_id": content_id,
                    "group_id": group_id,
                    "task_name": f"Publish to {group_id}" if group_id else "Publish",
                    "status": TaskStatus.PENDING.value,
                    "scheduled_at": scheduled_at or datetime.utcnow(),
                    "max_retries": settings.max_retries if settings else 3,
                    "retry_delay_seconds": settings.retry_delay_seconds if settings else 60,
                    "priority": 0,
                    "created_at": datetime.utcnow()
                }
                
                task = await task_repo.create(task_data)
                
                # Schedule the task
                if await self.schedule_task(task):
                    return task
                else:
                    # Delete the task if scheduling failed
                    await task_repo.delete(task.id)
                    return None
            
        except Exception as e:
            logger.error(f"Error creating publishing task: {e}")
            return None
    
    async def start_account_publishing(self, account_id: int, user_id: int) -> bool:
        """
        Start automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            user_id: The user ID.
            
        Returns:
            True if started successfully, False otherwise.
        """
        try:
            # Get account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                settings = await settings_repo.get_settings_by_account(account_id)
                
                if not settings:
                    return False
                
                # Update settings
                await settings_repo.update_publishing_settings(
                    account_id,
                    publishing_enabled=True
                )
            
            # Start publishing in the engine
            if self.publishing_engine:
                return await self.publishing_engine.start_publishing(account_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting account publishing: {e}")
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
        try:
            # Update account settings
            async with self.session_factory() as session:
                settings_repo = AccountSettingsRepository(session)
                await settings_repo.update_publishing_settings(
                    account_id,
                    publishing_enabled=False
                )
            
            # Stop publishing in the engine
            if self.publishing_engine:
                return await self.publishing_engine.stop_publishing(account_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping account publishing: {e}")
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
        if self.publishing_engine:
            return await self.publishing_engine.pause_publishing(account_id)
        return True
    
    async def resume_account_publishing(self, account_id: int, user_id: int) -> bool:
        """
        Resume automatic publishing for an account.
        
        Args:
            account_id: The account ID.
            user_id: The user ID.
            
        Returns:
            True if resumed successfully, False otherwise.
        """
        if self.publishing_engine:
            return await self.publishing_engine.resume_publishing(account_id)
        return True


__all__ = [
    'TaskType',
    'TaskScheduler',
]
