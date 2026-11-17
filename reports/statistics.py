"""
Statistics manager for Telegram Auto Publisher Pro
Provides comprehensive statistics for users, publishing, and system
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User,
    Administrator,
    TelegramAccount,
    Content,
    Group,
    PublishingTask,
    PublishingLog,
    Subscription,
    SubscriptionType,
    SubscriptionStatus,
    TaskStatus,
    UserStatus,
    AdminRole,
)
from database.repositories import (
    UserRepository,
    AdministratorRepository,
    TelegramAccountRepository,
    ContentRepository,
    GroupRepository,
    PublishingTaskRepository,
    PublishingLogRepository,
    SubscriptionRepository,
)

logger = logging.getLogger(__name__)


class StatisticPeriod(str, Enum):
    """Time periods for statistics"""
    
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    ALL_TIME = "all_time"
    CUSTOM = "custom"


@dataclass
class PublishingStats:
    """Publishing statistics"""
    
    # Task statistics
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    paused_tasks: int = 0
    cancelled_tasks: int = 0
    
    # Operation statistics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    
    # Success rate
    success_rate: float = 0.0
    
    # Time-based statistics
    operations_today: int = 0
    operations_this_week: int = 0
    operations_this_month: int = 0
    
    # Average statistics
    avg_operations_per_day: float = 0.0
    avg_success_rate: float = 0.0
    
    # Most active
    most_active_account_id: Optional[int] = None
    most_active_account_tasks: int = 0
    most_active_group_id: Optional[int] = None
    most_active_group_posts: int = 0


@dataclass
class UserStats:
    """User statistics"""
    
    # User counts
    total_users: int = 0
    active_users: int = 0
    inactive_users: int = 0
    blocked_users: int = 0
    suspended_users: int = 0
    
    # New users
    new_users_today: int = 0
    new_users_this_week: int = 0
    new_users_this_month: int = 0
    
    # User activity
    active_today: int = 0
    active_this_week: int = 0
    active_this_month: int = 0
    
    # Account statistics per user
    avg_accounts_per_user: float = 0.0
    max_accounts_per_user: int = 0
    
    # Top users
    top_users_by_tasks: List[Tuple[int, str, int]] = field(default_factory=list)
    top_users_by_accounts: List[Tuple[int, str, int]] = field(default_factory=list)


@dataclass
class AccountStats:
    """Account statistics"""
    
    total_accounts: int = 0
    connected_accounts: int = 0
    disconnected_accounts: int = 0
    
    # By status
    active_accounts: int = 0
    inactive_accounts: int = 0
    
    # Account types
    user_accounts: int = 0
    bot_accounts: int = 0
    
    # Connection statistics
    avg_connection_duration: float = 0.0
    longest_connection: float = 0.0
    
    # Most used accounts
    most_used_accounts: List[Tuple[int, str, int]] = field(default_factory=list)


@dataclass
class SubscriptionStats:
    """Subscription statistics"""
    
    total_subscriptions: int = 0
    active_subscriptions: int = 0
    expired_subscriptions: int = 0
    cancelled_subscriptions: int = 0
    
    # By type
    free_subscriptions: int = 0
    premium_subscriptions: int = 0
    monthly_subscriptions: int = 0
    yearly_subscriptions: int = 0
    lifetime_subscriptions: int = 0
    trial_subscriptions: int = 0
    
    # Expiring soon
    expiring_in_7_days: int = 0
    expiring_in_30_days: int = 0
    
    # Revenue (if applicable)
    total_revenue: float = 0.0
    monthly_revenue: float = 0.0
    
    # Conversion
    free_to_premium: int = 0


@dataclass
class ContentStats:
    """Content statistics"""
    
    total_content: int = 0
    text_content: int = 0
    image_content: int = 0
    video_content: int = 0
    document_content: int = 0
    audio_content: int = 0
    media_content: int = 0
    
    # Content by status
    published_content: int = 0
    draft_content: int = 0
    scheduled_content: int = 0
    
    # Most popular content
    most_published_content: List[Tuple[int, str, int]] = field(default_factory=list)
    most_viewed_content: List[Tuple[int, str, int]] = field(default_factory=list)


@dataclass
class GroupStats:
    """Group statistics"""
    
    total_groups: int = 0
    channels: int = 0
    groups: int = 0
    supergroups: int = 0
    
    # Permission statistics
    groups_with_permissions: int = 0
    groups_without_permissions: int = 0
    
    # Activity
    most_active_groups: List[Tuple[int, str, int]] = field(default_factory=list)
    least_active_groups: List[Tuple[int, str, int]] = field(default_factory=list)


@dataclass
class SystemStats:
    """System statistics"""
    
    # Database
    database_size: float = 0.0  # in MB
    table_counts: Dict[str, int] = field(default_factory=dict)
    
    # Performance
    avg_response_time: float = 0.0  # in ms
    peak_response_time: float = 0.0
    
    # Uptime
    uptime: float = 0.0  # in hours
    last_restart: Optional[datetime] = None
    
    # Resource usage
    memory_usage: float = 0.0  # in MB
    cpu_usage: float = 0.0  # percentage
    
    # Bot statistics
    bot_start_time: Optional[datetime] = None
    messages_processed: int = 0
    callbacks_processed: int = 0
    
    # Errors
    total_errors: int = 0
    errors_today: int = 0
    errors_this_week: int = 0


@dataclass
class DashboardStats:
    """Combined dashboard statistics"""
    
    # User statistics
    user_stats: UserStats = field(default_factory=UserStats)
    
    # Account statistics
    account_stats: AccountStats = field(default_factory=AccountStats)
    
    # Publishing statistics
    publishing_stats: PublishingStats = field(default_factory=PublishingStats)
    
    # Subscription statistics
    subscription_stats: SubscriptionStats = field(default_factory=SubscriptionStats)
    
    # Content statistics
    content_stats: ContentStats = field(default_factory=ContentStats)
    
    # Group statistics
    group_stats: GroupStats = field(default_factory=GroupStats)
    
    # System statistics
    system_stats: SystemStats = field(default_factory=SystemStats)
    
    # Last updated
    last_updated: Optional[datetime] = None


class StatisticsManager:
    """
    Manages all statistics for the application.
    Provides functionality for collecting, analyzing, and retrieving statistics.
    """
    
    def __init__(
        self,
        session_factory: Callable = None,
        user_repository: UserRepository = None,
        administrator_repository: AdministratorRepository = None,
        telegram_account_repository: TelegramAccountRepository = None,
        content_repository: ContentRepository = None,
        group_repository: GroupRepository = None,
        publishing_task_repository: PublishingTaskRepository = None,
        publishing_log_repository: PublishingLogRepository = None,
        subscription_repository: SubscriptionRepository = None,
        config: any = None
    ):
        """
        Initialize the statistics manager.
        
        Args:
            session_factory: Database session factory.
            user_repository: User repository instance.
            administrator_repository: Administrator repository instance.
            telegram_account_repository: Telegram account repository instance.
            content_repository: Content repository instance.
            group_repository: Group repository instance.
            publishing_task_repository: Publishing task repository instance.
            publishing_log_repository: Publishing log repository instance.
            subscription_repository: Subscription repository instance.
            config: Application configuration.
        """
        self.session_factory = session_factory
        self.config = config or config
        
        # Initialize repositories
        if user_repository:
            self.user_repository = user_repository
        else:
            self.user_repository = UserRepository(session_factory)
            
        if administrator_repository:
            self.administrator_repository = administrator_repository
        else:
            self.administrator_repository = AdministratorRepository(session_factory)
            
        if telegram_account_repository:
            self.telegram_account_repository = telegram_account_repository
        else:
            self.telegram_account_repository = TelegramAccountRepository(session_factory)
            
        if content_repository:
            self.content_repository = content_repository
        else:
            self.content_repository = ContentRepository(session_factory)
            
        if group_repository:
            self.group_repository = group_repository
        else:
            self.group_repository = GroupRepository(session_factory)
            
        if publishing_task_repository:
            self.publishing_task_repository = publishing_task_repository
        else:
            self.publishing_task_repository = PublishingTaskRepository(session_factory)
            
        if publishing_log_repository:
            self.publishing_log_repository = publishing_log_repository
        else:
            self.publishing_log_repository = PublishingLogRepository(session_factory)
            
        if subscription_repository:
            self.subscription_repository = subscription_repository
        else:
            self.subscription_repository = SubscriptionRepository(session_factory)
        
        # Cache for statistics
        self._stats_cache: Optional[DashboardStats] = None
        self._cache_last_updated: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        
        logger.info("StatisticsManager initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the statistics manager.
        """
        logger.info("StatisticsManager: Initializing...")
        
        # Pre-load statistics
        await self.get_dashboard_stats(force=True)
        
        logger.info("StatisticsManager: Initialized successfully")
    
    async def close(self) -> None:
        """
        Close the statistics manager.
        """
        logger.info("StatisticsManager: Closed")
    
    async def get_dashboard_stats(self, force: bool = False) -> DashboardStats:
        """
        Get combined dashboard statistics.
        
        Args:
            force: Whether to force refresh the cache.
            
        Returns:
            DashboardStats object.
        """
        if not force and self._stats_cache:
            if self._cache_last_updated and (datetime.utcnow() - self._cache_last_updated) < self._cache_ttl:
                return self._stats_cache
        
        # Collect all statistics in parallel
        user_stats_task = asyncio.create_task(self.get_user_stats())
        account_stats_task = asyncio.create_task(self.get_account_stats())
        publishing_stats_task = asyncio.create_task(self.get_publishing_stats())
        subscription_stats_task = asyncio.create_task(self.get_subscription_stats())
        content_stats_task = asyncio.create_task(self.get_content_stats())
        group_stats_task = asyncio.create_task(self.get_group_stats())
        system_stats_task = asyncio.create_task(self.get_system_stats())
        
        # Wait for all tasks
        user_stats = await user_stats_task
        account_stats = await account_stats_task
        publishing_stats = await publishing_stats_task
        subscription_stats = await subscription_stats_task
        content_stats = await content_stats_task
        group_stats = await group_stats_task
        system_stats = await system_stats_task
        
        dashboard_stats = DashboardStats(
            user_stats=user_stats,
            account_stats=account_stats,
            publishing_stats=publishing_stats,
            subscription_stats=subscription_stats,
            content_stats=content_stats,
            group_stats=group_stats,
            system_stats=system_stats,
            last_updated=datetime.utcnow()
        )
        
        # Update cache
        self._stats_cache = dashboard_stats
        self._cache_last_updated = datetime.utcnow()
        
        return dashboard_stats
    
    async def get_user_stats(self) -> UserStats:
        """
        Get user statistics.
        
        Returns:
            UserStats object.
        """
        try:
            async with self.session_factory() as session:
                self.user_repository.session = session
                self.telegram_account_repository.session = session
                self.publishing_task_repository.session = session
                
                from sqlalchemy import select, func, and_, or_
                from database.models import User, TelegramAccount, PublishingTask
                
                # Total users
                total_users = await session.scalar(
                    select(func.count()).select_from(User)
                ) or 0
                
                # By status
                active_users = await session.scalar(
                    select(func.count()).select_from(User).where(
                        User.status == UserStatus.ACTIVE.value
                    )
                ) or 0
                
                inactive_users = await session.scalar(
                    select(func.count()).select_from(User).where(
                        User.status == UserStatus.INACTIVE.value
                    )
                ) or 0
                
                blocked_users = await session.scalar(
                    select(func.count()).select_from(User).where(
                        User.status == UserStatus.BLOCKED.value
                    )
                ) or 0
                
                suspended_users = await session.scalar(
                    select(func.count()).select_from(User).where(
                        User.status == UserStatus.SUSPENDED.value
                    )
                ) or 0
                
                # New users today
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                new_users_today = await session.scalar(
                    select(func.count()).select_from(User).where(
                        and_(
                            User.created_at >= today_start,
                            User.created_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # New users this week
                week_start = today_start - timedelta(days=today_start.weekday())
                new_users_this_week = await session.scalar(
                    select(func.count()).select_from(User).where(
                        and_(
                            User.created_at >= week_start,
                            User.created_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # New users this month
                month_start = today_start.replace(day=1)
                new_users_this_month = await session.scalar(
                    select(func.count()).select_from(User).where(
                        and_(
                            User.created_at >= month_start,
                            User.created_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # Active today (users with activity today)
                active_today = await session.scalar(
                    select(func.count()).select_from(User).where(
                        and_(
                            User.last_active_at >= today_start,
                            User.last_active_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # Average accounts per user
                total_accounts = await session.scalar(
                    select(func.count()).select_from(TelegramAccount)
                ) or 0
                avg_accounts = total_accounts / total_users if total_users > 0 else 0.0
                
                # Max accounts per user
                max_accounts = await session.scalar(
                    select(func.max(func.count(TelegramAccount.id)))
                    .select_from(TelegramAccount)
                    .group_by(TelegramAccount.user_id)
                ) or 0
                
                # Top users by tasks
                top_users_tasks = await session.execute(
                    select(
                        User.telegram_id,
                        User.username,
                        func.count(PublishingTask.id)
                    )
                    .select_from(User)
                    .outerjoin(PublishingTask, User.telegram_id == PublishingTask.user_id)
                    .group_by(User.telegram_id, User.username)
                    .order_by(func.count(PublishingTask.id).desc())
                    .limit(5)
                )
                top_users_by_tasks = [
                    (row[0], row[1] or f"User {row[0]}", row[2])
                    for row in top_users_tasks
                ]
                
                # Top users by accounts
                top_users_accounts = await session.execute(
                    select(
                        User.telegram_id,
                        User.username,
                        func.count(TelegramAccount.id)
                    )
                    .select_from(User)
                    .outerjoin(TelegramAccount, User.telegram_id == TelegramAccount.user_id)
                    .group_by(User.telegram_id, User.username)
                    .order_by(func.count(TelegramAccount.id).desc())
                    .limit(5)
                )
                top_users_by_accounts = [
                    (row[0], row[1] or f"User {row[0]}", row[2])
                    for row in top_users_accounts
                ]
                
                return UserStats(
                    total_users=total_users,
                    active_users=active_users,
                    inactive_users=inactive_users,
                    blocked_users=blocked_users,
                    suspended_users=suspended_users,
                    new_users_today=new_users_today,
                    new_users_this_week=new_users_this_week,
                    new_users_this_month=new_users_this_month,
                    active_today=active_today,
                    avg_accounts_per_user=avg_accounts,
                    max_accounts_per_user=max_accounts,
                    top_users_by_tasks=top_users_by_tasks,
                    top_users_by_accounts=top_users_by_accounts
                )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting user stats: {e}")
            return UserStats()
    
    async def get_account_stats(self) -> AccountStats:
        """
        Get account statistics.
        
        Returns:
            AccountStats object.
        """
        try:
            async with self.session_factory() as session:
                self.telegram_account_repository.session = session
                self.publishing_task_repository.session = session
                
                from sqlalchemy import select, func, and_
                from database.models import TelegramAccount, PublishingTask
                
                # Total accounts
                total_accounts = await session.scalar(
                    select(func.count()).select_from(TelegramAccount)
                ) or 0
                
                # Connected accounts
                connected_accounts = await session.scalar(
                    select(func.count()).select_from(TelegramAccount).where(
                        TelegramAccount.is_connected == True
                    )
                ) or 0
                
                # Disconnected accounts
                disconnected_accounts = total_accounts - connected_accounts
                
                # Active accounts (have recent activity)
                active_accounts = await session.scalar(
                    select(func.count()).select_from(TelegramAccount).where(
                        and_(
                            TelegramAccount.is_connected == True,
                            TelegramAccount.last_active_at >= datetime.utcnow() - timedelta(days=7)
                        )
                    )
                ) or 0
                
                # Inactive accounts
                inactive_accounts = total_accounts - active_accounts
                
                # Most used accounts (by task count)
                most_used = await session.execute(
                    select(
                        TelegramAccount.id,
                        TelegramAccount.account_name,
                        func.count(PublishingTask.id)
                    )
                    .select_from(TelegramAccount)
                    .outerjoin(PublishingTask, TelegramAccount.id == PublishingTask.telegram_account_id)
                    .group_by(TelegramAccount.id, TelegramAccount.account_name)
                    .order_by(func.count(PublishingTask.id).desc())
                    .limit(5)
                )
                most_used_accounts = [
                    (row[0], row[1] or f"Account {row[0]}", row[2])
                    for row in most_used
                ]
                
                return AccountStats(
                    total_accounts=total_accounts,
                    connected_accounts=connected_accounts,
                    disconnected_accounts=disconnected_accounts,
                    active_accounts=active_accounts,
                    inactive_accounts=inactive_accounts,
                    most_used_accounts=most_used_accounts
                )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting account stats: {e}")
            return AccountStats()
    
    async def get_publishing_stats(self) -> PublishingStats:
        """
        Get publishing statistics.
        
        Returns:
            PublishingStats object.
        """
        try:
            async with self.session_factory() as session:
                self.publishing_task_repository.session = session
                self.publishing_log_repository.session = session
                
                from sqlalchemy import select, func, and_
                from database.models import PublishingTask, PublishingLog
                
                # Task statistics
                total_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask)
                ) or 0
                
                pending_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask).where(
                        PublishingTask.status == TaskStatus.PENDING.value
                    )
                ) or 0
                
                running_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask).where(
                        PublishingTask.status == TaskStatus.RUNNING.value
                    )
                ) or 0
                
                completed_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask).where(
                        PublishingTask.status == TaskStatus.COMPLETED.value
                    )
                ) or 0
                
                failed_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask).where(
                        PublishingTask.status == TaskStatus.FAILED.value
                    )
                ) or 0
                
                paused_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask).where(
                        PublishingTask.status == TaskStatus.PAUSED.value
                    )
                ) or 0
                
                cancelled_tasks = await session.scalar(
                    select(func.count()).select_from(PublishingTask).where(
                        PublishingTask.status == TaskStatus.CANCELLED.value
                    )
                ) or 0
                
                # Operation statistics from logs
                total_operations = await session.scalar(
                    select(func.count()).select_from(PublishingLog)
                ) or 0
                
                successful_operations = await session.scalar(
                    select(func.count()).select_from(PublishingLog).where(
                        PublishingLog.status == "success"
                    )
                ) or 0
                
                failed_operations = await session.scalar(
                    select(func.count()).select_from(PublishingLog).where(
                        PublishingLog.status == "failed"
                    )
                ) or 0
                
                # Calculate success rate
                success_rate = (successful_operations / total_operations) * 100 if total_operations > 0 else 0.0
                
                # Operations today
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                operations_today = await session.scalar(
                    select(func.count()).select_from(PublishingLog).where(
                        and_(
                            PublishingLog.created_at >= today_start,
                            PublishingLog.created_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # Operations this week
                week_start = today_start - timedelta(days=today_start.weekday())
                operations_this_week = await session.scalar(
                    select(func.count()).select_from(PublishingLog).where(
                        and_(
                            PublishingLog.created_at >= week_start,
                            PublishingLog.created_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # Operations this month
                month_start = today_start.replace(day=1)
                operations_this_month = await session.scalar(
                    select(func.count()).select_from(PublishingLog).where(
                        and_(
                            PublishingLog.created_at >= month_start,
                            PublishingLog.created_at <= datetime.utcnow()
                        )
                    )
                ) or 0
                
                # Most active account
                most_active_account = await session.execute(
                    select(
                        PublishingTask.telegram_account_id,
                        func.count(PublishingTask.id)
                    )
                    .select_from(PublishingTask)
                    .group_by(PublishingTask.telegram_account_id)
                    .order_by(func.count(PublishingTask.id).desc())
                    .limit(1)
                )
                most_active_account_row = most_active_account.first()
                most_active_account_id = most_active_account_row[0] if most_active_account_row else None
                most_active_account_tasks = most_active_account_row[1] if most_active_account_row else 0
                
                # Most active group
                most_active_group = await session.execute(
                    select(
                        PublishingTask.group_id,
                        func.count(PublishingTask.id)
                    )
                    .select_from(PublishingTask)
                    .group_by(PublishingTask.group_id)
                    .order_by(func.count(PublishingTask.id).desc())
                    .limit(1)
                )
                most_active_group_row = most_active_group.first()
                most_active_group_id = most_active_group_row[0] if most_active_group_row else None
                most_active_group_posts = most_active_group_row[1] if most_active_group_row else 0
                
                return PublishingStats(
                    total_tasks=total_tasks,
                    pending_tasks=pending_tasks,
                    running_tasks=running_tasks,
                    completed_tasks=completed_tasks,
                    failed_tasks=failed_tasks,
                    paused_tasks=paused_tasks,
                    cancelled_tasks=cancelled_tasks,
                    total_operations=total_operations,
                    successful_operations=successful_operations,
                    failed_operations=failed_operations,
                    success_rate=success_rate,
                    operations_today=operations_today,
                    operations_this_week=operations_this_week,
                    operations_this_month=operations_this_month,
                    most_active_account_id=most_active_account_id,
                    most_active_account_tasks=most_active_account_tasks,
                    most_active_group_id=most_active_group_id,
                    most_active_group_posts=most_active_group_posts
                )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting publishing stats: {e}")
            return PublishingStats()
    
    async def get_subscription_stats(self) -> SubscriptionStats:
        """
        Get subscription statistics.
        
        Returns:
            SubscriptionStats object.
        """
        try:
            async with self.session_factory() as session:
                self.subscription_repository.session = session
                
                from sqlalchemy import select, func, and_, or_
                from database.models import Subscription
                
                # Total subscriptions
                total_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription)
                ) or 0
                
                # Active subscriptions
                active_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.status == SubscriptionStatus.ACTIVE.value
                    )
                ) or 0
                
                # Expired subscriptions
                expired_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.status == SubscriptionStatus.EXPIRED.value
                    )
                ) or 0
                
                # Cancelled subscriptions
                cancelled_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.status == SubscriptionStatus.CANCELLED.value
                    )
                ) or 0
                
                # By type
                free_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.subscription_type == SubscriptionType.FREE.value
                    )
                ) or 0
                
                premium_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.subscription_type == SubscriptionType.PREMIUM.value
                    )
                ) or 0
                
                monthly_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.subscription_type == SubscriptionType.MONTHLY.value
                    )
                ) or 0
                
                yearly_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.subscription_type == SubscriptionType.YEARLY.value
                    )
                ) or 0
                
                lifetime_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.subscription_type == SubscriptionType.LIFETIME.value
                    )
                ) or 0
                
                trial_subscriptions = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.subscription_type == SubscriptionType.TRIAL.value
                    )
                ) or 0
                
                # Expiring soon (7 days)
                seven_days_later = datetime.utcnow() + timedelta(days=7)
                expiring_in_7_days = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE.value,
                            Subscription.end_date >= datetime.utcnow(),
                            Subscription.end_date <= seven_days_later
                        )
                    )
                ) or 0
                
                # Expiring soon (30 days)
                thirty_days_later = datetime.utcnow() + timedelta(days=30)
                expiring_in_30_days = await session.scalar(
                    select(func.count()).select_from(Subscription).where(
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE.value,
                            Subscription.end_date >= datetime.utcnow(),
                            Subscription.end_date <= thirty_days_later
                        )
                    )
                ) or 0
                
                return SubscriptionStats(
                    total_subscriptions=total_subscriptions,
                    active_subscriptions=active_subscriptions,
                    expired_subscriptions=expired_subscriptions,
                    cancelled_subscriptions=cancelled_subscriptions,
                    free_subscriptions=free_subscriptions,
                    premium_subscriptions=premium_subscriptions,
                    monthly_subscriptions=monthly_subscriptions,
                    yearly_subscriptions=yearly_subscriptions,
                    lifetime_subscriptions=lifetime_subscriptions,
                    trial_subscriptions=trial_subscriptions,
                    expiring_in_7_days=expiring_in_7_days,
                    expiring_in_30_days=expiring_in_30_days
                )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting subscription stats: {e}")
            return SubscriptionStats()
    
    async def get_content_stats(self) -> ContentStats:
        """
        Get content statistics.
        
        Returns:
            ContentStats object.
        """
        try:
            async with self.session_factory() as session:
                self.content_repository.session = session
                self.publishing_log_repository.session = session
                
                from sqlalchemy import select, func, and_
                from database.models import Content, PublishingLog
                from database.models import ContentType
                
                # Total content
                total_content = await session.scalar(
                    select(func.count()).select_from(Content)
                ) or 0
                
                # By type
                text_content = await session.scalar(
                    select(func.count()).select_from(Content).where(
                        Content.content_type == ContentType.TEXT.value
                    )
                ) or 0
                
                image_content = await session.scalar(
                    select(func.count()).select_from(Content).where(
                        Content.content_type == ContentType.IMAGE.value
                    )
                ) or 0
                
                video_content = await session.scalar(
                    select(func.count()).select_from(Content).where(
                        Content.content_type == ContentType.VIDEO.value
                    )
                ) or 0
                
                document_content = await session.scalar(
                    select(func.count()).select_from(Content).where(
                        Content.content_type == ContentType.DOCUMENT.value
                    )
                ) or 0
                
                audio_content = await session.scalar(
                    select(func.count()).select_from(Content).where(
                        Content.content_type == ContentType.AUDIO.value
                    )
                ) or 0
                
                media_content = await session.scalar(
                    select(func.count()).select_from(Content).where(
                        Content.content_type == ContentType.MEDIA.value
                    )
                ) or 0
                
                # Most published content
                most_published = await session.execute(
                    select(
                        PublishingLog.content_id,
                        Content.title,
                        func.count(PublishingLog.id)
                    )
                    .select_from(PublishingLog)
                    .join(Content, PublishingLog.content_id == Content.id)
                    .group_by(PublishingLog.content_id, Content.title)
                    .order_by(func.count(PublishingLog.id).desc())
                    .limit(5)
                )
                most_published_content = [
                    (row[0], row[1] or f"Content {row[0]}", row[2])
                    for row in most_published
                ]
                
                return ContentStats(
                    total_content=total_content,
                    text_content=text_content,
                    image_content=image_content,
                    video_content=video_content,
                    document_content=document_content,
                    audio_content=audio_content,
                    media_content=media_content,
                    most_published_content=most_published_content
                )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting content stats: {e}")
            return ContentStats()
    
    async def get_group_stats(self) -> GroupStats:
        """
        Get group statistics.
        
        Returns:
            GroupStats object.
        """
        try:
            async with self.session_factory() as session:
                self.group_repository.session = session
                self.publishing_task_repository.session = session
                
                from sqlalchemy import select, func, and_
                from database.models import Group, PublishingTask
                from database.models import GroupType
                
                # Total groups
                total_groups = await session.scalar(
                    select(func.count()).select_from(Group)
                ) or 0
                
                # By type
                channels = await session.scalar(
                    select(func.count()).select_from(Group).where(
                        Group.group_type == GroupType.CHANNEL.value
                    )
                ) or 0
                
                groups = await session.scalar(
                    select(func.count()).select_from(Group).where(
                        Group.group_type == GroupType.GROUP.value
                    )
                ) or 0
                
                supergroups = await session.scalar(
                    select(func.count()).select_from(Group).where(
                        Group.group_type == GroupType.SUPERGROUP.value
                    )
                ) or 0
                
                # Most active groups
                most_active = await session.execute(
                    select(
                        PublishingTask.group_id,
                        Group.group_name,
                        func.count(PublishingTask.id)
                    )
                    .select_from(PublishingTask)
                    .join(Group, PublishingTask.group_id == Group.id)
                    .group_by(PublishingTask.group_id, Group.group_name)
                    .order_by(func.count(PublishingTask.id).desc())
                    .limit(5)
                )
                most_active_groups = [
                    (row[0], row[1] or f"Group {row[0]}", row[2])
                    for row in most_active
                ]
                
                return GroupStats(
                    total_groups=total_groups,
                    channels=channels,
                    groups=groups,
                    supergroups=supergroups,
                    most_active_groups=most_active_groups
                )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting group stats: {e}")
            return GroupStats()
    
    async def get_system_stats(self) -> SystemStats:
        """
        Get system statistics.
        
        Returns:
            SystemStats object.
        """
        try:
            # Get database size (approximate)
            database_size = 0.0
            
            # Get table counts
            table_counts = {}
            
            async with self.session_factory() as session:
                from sqlalchemy import select, func, inspect
                from database.models import Base
                
                # Get all table names
                inspector = inspect(Base.registry)
                table_names = inspector.get_table_names()
                
                for table_name in table_names:
                    if table_name.startswith("alembic"):
                        continue
                    count = await session.scalar(
                        select(func.count()).select_from(Base.registry.tables[table_name])
                    ) or 0
                    table_counts[table_name] = count
                
                # Get total database size (PostgreSQL specific)
                try:
                    result = await session.execute(
                        select(func.sum(func.pg_total_relation_size(func.quote_ident(table_name))))
                        .select_from(func.unnest(table_names))
                    )
                    database_size = (result.scalar() or 0) / (1024 * 1024)  # Convert to MB
                except Exception:
                    # Fallback for SQLite or other databases
                    database_size = 0.0
            
            return SystemStats(
                database_size=database_size,
                table_counts=table_counts
            )
                
        except Exception as e:
            logger.error(f"StatisticsManager: Error getting system stats: {e}")
            return SystemStats()
    
    async def get_stats_by_period(
        self,
        period: StatisticPeriod,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> DashboardStats:
        """
        Get statistics for a specific time period.
        
        Args:
            period: The time period.
            start_date: Optional custom start date.
            end_date: Optional custom end date.
            
        Returns:
            DashboardStats object for the period.
        """
        # Calculate date range based on period
        now = datetime.utcnow()
        
        if period == StatisticPeriod.TODAY:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == StatisticPeriod.YESTERDAY:
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == StatisticPeriod.LAST_7_DAYS:
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == StatisticPeriod.LAST_30_DAYS:
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == StatisticPeriod.THIS_MONTH:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == StatisticPeriod.LAST_MONTH:
            first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
            start_date = last_day_of_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = first_day_of_current_month
        elif period == StatisticPeriod.ALL_TIME:
            start_date = None
            end_date = None
        
        # For now, just return current stats (period filtering would be implemented in each stat method)
        return await self.get_dashboard_stats(force=True)
    
    async def refresh_cache(self) -> None:
        """
        Force refresh the statistics cache.
        """
        await self.get_dashboard_stats(force=True)
        logger.info("StatisticsManager: Cache refreshed")
