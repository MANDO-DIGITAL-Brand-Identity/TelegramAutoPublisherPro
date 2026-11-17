"""
Report generator for Telegram Auto Publisher Pro
Generates various types of reports for the application
"""

import asyncio
import logging
import json
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User, Administrator, TelegramAccount, Content, Group,
    PublishingTask, PublishingLog, Subscription, Notification, AuditLog,
    TaskStatus, UserStatus, SubscriptionStatus
)
from database.repositories import (
    UserRepository, AdministratorRepository, TelegramAccountRepository,
    ContentRepository, GroupRepository, PublishingTaskRepository,
    PublishingLogRepository, SubscriptionRepository, NotificationRepository,
    AuditLogRepository
)
from .statistics import StatisticsManager, DashboardStats

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    DASHBOARD_SUMMARY = "dashboard_summary"
    DASHBOARD_DETAILED = "dashboard_detailed"
    USER_LIST = "user_list"
    ACCOUNT_LIST = "account_list"
    PUBLISHING_SUMMARY = "publishing_summary"
    TASK_LIST = "task_list"
    SUBSCRIPTION_LIST = "subscription_list"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    CONTENT_LIST = "content_list"
    GROUP_LIST = "group_list"
    SYSTEM_HEALTH = "system_health"
    ERROR_REPORT = "error_report"
    AUDIT_LOG = "audit_log"
    NOTIFICATION_LIST = "notification_list"


class ReportFormat(str, Enum):
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    CSV = "csv"


@dataclass
class ReportData:
    report_type: ReportType
    report_format: ReportFormat
    title: str = ""
    description: str = ""
    generated_at: Optional[datetime] = None
    generated_by: Optional[int] = None
    content: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    row_count: int = 0
    file_size: int = 0


@dataclass
class ReportConfig:
    report_type: ReportType
    report_format: ReportFormat = ReportFormat.TEXT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_by: str = "created_at"
    sort_descending: bool = True
    limit: int = 1000
    offset: int = 0
    include_details: bool = True
    include_statistics: bool = True


class ReportGenerator:
    def __init__(
        self,
        session_factory: Callable = None,
        statistics_manager: StatisticsManager = None,
        user_repository: UserRepository = None,
        administrator_repository: AdministratorRepository = None,
        telegram_account_repository: TelegramAccountRepository = None,
        content_repository: ContentRepository = None,
        group_repository: GroupRepository = None,
        publishing_task_repository: PublishingTaskRepository = None,
        publishing_log_repository: PublishingLogRepository = None,
        subscription_repository: SubscriptionRepository = None,
        notification_repository: NotificationRepository = None,
        audit_log_repository: AuditLogRepository = None,
        config: any = None
    ):
        self.session_factory = session_factory
        self.config = config or config
        self.statistics_manager = statistics_manager or StatisticsManager(session_factory)
        self.user_repository = user_repository or UserRepository(session_factory)
        self.administrator_repository = administrator_repository or AdministratorRepository(session_factory)
        self.telegram_account_repository = telegram_account_repository or TelegramAccountRepository(session_factory)
        self.content_repository = content_repository or ContentRepository(session_factory)
        self.group_repository = group_repository or GroupRepository(session_factory)
        self.publishing_task_repository = publishing_task_repository or PublishingTaskRepository(session_factory)
        self.publishing_log_repository = publishing_log_repository or PublishingLogRepository(session_factory)
        self.subscription_repository = subscription_repository or SubscriptionRepository(session_factory)
        self.notification_repository = notification_repository or NotificationRepository(session_factory)
        self.audit_log_repository = audit_log_repository or AuditLogRepository(session_factory)
        logger.info("ReportGenerator initialized")

    async def initialize(self) -> None:
        logger.info("ReportGenerator: Initializing...")
        await self.statistics_manager.initialize()
        logger.info("ReportGenerator: Initialized successfully")

    async def generate_report(
        self,
        report_config: ReportConfig,
        administrator_id: Optional[int] = None
    ) -> ReportData:
        logger.info(f"ReportGenerator: Generating {report_config.report_type.value} report")
        report_type = report_config.report_type

        if report_type == ReportType.DASHBOARD_SUMMARY:
            return await self._generate_dashboard_summary(report_config, administrator_id)
        elif report_type == ReportType.USER_LIST:
            return await self._generate_user_list(report_config, administrator_id)
        elif report_type == ReportType.ACCOUNT_LIST:
            return await self._generate_account_list(report_config, administrator_id)
        elif report_type == ReportType.PUBLISHING_SUMMARY:
            return await self._generate_publishing_summary(report_config, administrator_id)
        elif report_type == ReportType.TASK_LIST:
            return await self._generate_task_list(report_config, administrator_id)
        elif report_type == ReportType.SUBSCRIPTION_LIST:
            return await self._generate_subscription_list(report_config, administrator_id)
        elif report_type == ReportType.SUBSCRIPTION_EXPIRING:
            return await self._generate_subscription_expiring(report_config, administrator_id)
        elif report_type == ReportType.CONTENT_LIST:
            return await self._generate_content_list(report_config, administrator_id)
        elif report_type == ReportType.GROUP_LIST:
            return await self._generate_group_list(report_config, administrator_id)
        elif report_type == ReportType.AUDIT_LOG:
            return await self._generate_audit_log(report_config, administrator_id)
        elif report_type == ReportType.NOTIFICATION_LIST:
            return await self._generate_notification_list(report_config, administrator_id)
        else:
            return ReportData(
                report_type=report_type,
                report_format=report_config.report_format,
                title="Report",
                content=f"Unsupported report type: {report_type}"
            )

    async def _generate_dashboard_summary(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        dashboard_stats = await self.statistics_manager.get_dashboard_stats(force=True)
        if config.report_format == ReportFormat.JSON:
            content = self._dashboard_to_json(dashboard_stats)
        elif config.report_format == ReportFormat.CSV:
            content = self._dashboard_to_csv(dashboard_stats)
        else:
            content = self._dashboard_to_text(dashboard_stats)
        return ReportData(
            report_type=ReportType.DASHBOARD_SUMMARY,
            report_format=config.report_format,
            title="Dashboard Summary",
            generated_at=datetime.utcnow(),
            generated_by=admin_id,
            content=content,
            row_count=1,
            file_size=len(content)
        )

    def _dashboard_to_text(self, stats: DashboardStats) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("TELEGRAM AUTO PUBLISHER PRO - DASHBOARD SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append("")
        lines.append("USER STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total Users: {stats.user_stats.total_users}")
        lines.append(f"Active Users: {stats.user_stats.active_users}")
        lines.append(f"New Users Today: {stats.user_stats.new_users_today}")
        lines.append("")
        lines.append("ACCOUNT STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total Accounts: {stats.account_stats.total_accounts}")
        lines.append(f"Connected: {stats.account_stats.connected_accounts}")
        lines.append("")
        lines.append("PUBLISHING STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total Tasks: {stats.publishing_stats.total_tasks}")
        lines.append(f"Completed: {stats.publishing_stats.completed_tasks}")
        lines.append(f"Success Rate: {stats.publishing_stats.success_rate:.2f}%")
        lines.append("")
        lines.append("SUBSCRIPTION STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total: {stats.subscription_stats.total_subscriptions}")
        lines.append(f"Active: {stats.subscription_stats.active_subscriptions}")
        lines.append(f"Premium: {stats.subscription_stats.premium_subscriptions}")
        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

    def _dashboard_to_json(self, stats: DashboardStats) -> str:
        data = {
            "report_type": "dashboard_summary",
            "generated_at": datetime.utcnow().isoformat(),
            "user_stats": {
                "total_users": stats.user_stats.total_users,
                "active_users": stats.user_stats.active_users,
                "new_users_today": stats.user_stats.new_users_today,
            },
            "account_stats": {
                "total_accounts": stats.account_stats.total_accounts,
                "connected_accounts": stats.account_stats.connected_accounts,
            },
            "publishing_stats": {
                "total_tasks": stats.publishing_stats.total_tasks,
                "completed_tasks": stats.publishing_stats.completed_tasks,
                "success_rate": stats.publishing_stats.success_rate,
            },
            "subscription_stats": {
                "total_subscriptions": stats.subscription_stats.total_subscriptions,
                "active_subscriptions": stats.subscription_stats.active_subscriptions,
                "premium_subscriptions": stats.subscription_stats.premium_subscriptions,
            }
        }
        return json.dumps(data, indent=2, default=str)

    def _dashboard_to_csv(self, stats: DashboardStats) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Category", "Metric", "Value"])
        writer.writerow(["Users", "Total", stats.user_stats.total_users])
        writer.writerow(["Users", "Active", stats.user_stats.active_users])
        writer.writerow(["Accounts", "Total", stats.account_stats.total_accounts])
        writer.writerow(["Accounts", "Connected", stats.account_stats.connected_accounts])
        writer.writerow(["Publishing", "Total Tasks", stats.publishing_stats.total_tasks])
        writer.writerow(["Publishing", "Completed", stats.publishing_stats.completed_tasks])
        writer.writerow(["Subscriptions", "Total", stats.subscription_stats.total_subscriptions])
        writer.writerow(["Subscriptions", "Active", stats.subscription_stats.active_subscriptions])
        return output.getvalue()

    async def _generate_user_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.user_repository.session = session
                users = await self.user_repository.get_all(
                    filters=config.filters,
                    limit=config.limit,
                    offset=config.offset,
                    order_by=config.sort_by,
                    descending=config.sort_descending
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._users_to_json(users)
                elif config.report_format == ReportFormat.CSV:
                    content = self._users_to_csv(users)
                else:
                    content = self._users_to_text(users)
                return ReportData(
                    report_type=ReportType.USER_LIST,
                    report_format=config.report_format,
                    title="User List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(users),
                    file_size=len(content)
                )
        except Exception as e:
            logger.error(f"Error generating user list: {e}")
            return ReportData(
                report_type=ReportType.USER_LIST,
                report_format=config.report_format,
                title="User List",
                content=f"Error: {e}"
            )

    def _users_to_text(self, users: List[User]) -> str:
        lines = ["USER LIST", "=" * 60]
        lines.append(f"{'ID':<10} {'Username':<20} {'Name':<25} {'Status':<10}")
        lines.append("-" * 60)
        for u in users:
            name = f"{u.first_name or ''} {u.last_name or ''}".strip()
            lines.append(f"{u.telegram_id:<10} {u.username or '':<20} {name:<25} {u.status.value if u.status else '':<10}")
        return "\n".join(lines)

    def _users_to_json(self, users: List[User]) -> str:
        data = [{
            "telegram_id": u.telegram_id,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "status": u.status.value if u.status else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        } for u in users]
        return json.dumps(data, indent=2, default=str)

    def _users_to_csv(self, users: List[User]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Telegram ID", "Username", "First Name", "Last Name", "Status", "Created At"])
        for u in users:
            writer.writerow([
                u.telegram_id,
                u.username or "",
                u.first_name or "",
                u.last_name or "",
                u.status.value if u.status else "",
                u.created_at.isoformat() if u.created_at else ""
            ])
        return output.getvalue()

    async def _generate_account_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.telegram_account_repository.session = session
                accounts = await self.telegram_account_repository.get_all(
                    filters=config.filters,
                    limit=config.limit,
                    offset=config.offset
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._accounts_to_json(accounts)
                elif config.report_format == ReportFormat.CSV:
                    content = self._accounts_to_csv(accounts)
                else:
                    content = self._accounts_to_text(accounts)
                return ReportData(
                    report_type=ReportType.ACCOUNT_LIST,
                    report_format=config.report_format,
                    title="Account List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(accounts),
                    file_size=len(content)
                )
        except Exception as e:
            logger.error(f"Error generating account list: {e}")
            return ReportData(
                report_type=ReportType.ACCOUNT_LIST,
                report_format=config.report_format,
                title="Account List",
                content=f"Error: {e}"
            )

    def _accounts_to_text(self, accounts: List[TelegramAccount]) -> str:
        lines = ["ACCOUNT LIST", "=" * 60]
        lines.append(f"{'ID':<8} {'Name':<20} {'Phone':<15} {'Connected':<10}")
        lines.append("-" * 60)
        for a in accounts:
            lines.append(f"{a.id:<8} {a.account_name or '':<20} {a.phone_number or '':<15} {a.is_connected}")
        return "\n".join(lines)

    def _accounts_to_json(self, accounts: List[TelegramAccount]) -> str:
        data = [{
            "id": a.id,
            "account_name": a.account_name,
            "phone_number": a.phone_number,
            "is_connected": a.is_connected,
            "user_id": a.user_id,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in accounts]
        return json.dumps(data, indent=2, default=str)

    def _accounts_to_csv(self, accounts: List[TelegramAccount]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Name", "Phone", "Connected", "User ID", "Created At"])
        for a in accounts:
            writer.writerow([
                a.id,
                a.account_name or "",
                a.phone_number or "",
                a.is_connected,
                a.user_id or "",
                a.created_at.isoformat() if a.created_at else ""
            ])
        return output.getvalue()

    async def _generate_publishing_summary(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        dashboard_stats = await self.statistics_manager.get_dashboard_stats(force=True)
        ps = dashboard_stats.publishing_stats
        if config.report_format == ReportFormat.JSON:
            content = json.dumps({
                "total_tasks": ps.total_tasks,
                "completed": ps.completed_tasks,
                "failed": ps.failed_tasks,
                "success_rate": ps.success_rate,
                "total_operations": ps.total_operations
            }, indent=2)
        else:
            content = f"PUBLISHING SUMMARY\n{'='*40}\n"
            content += f"Total Tasks: {ps.total_tasks}\n"
            content += f"Completed: {ps.completed_tasks}\n"
            content += f"Failed: {ps.failed_tasks}\n"
            content += f"Success Rate: {ps.success_rate:.2f}%\n"
            content += f"Total Operations: {ps.total_operations}\n"
        return ReportData(
            report_type=ReportType.PUBLISHING_SUMMARY,
            report_format=config.report_format,
            title="Publishing Summary",
            generated_at=datetime.utcnow(),
            generated_by=admin_id,
            content=content
        )

    async def _generate_task_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.publishing_task_repository.session = session
                tasks = await self.publishing_task_repository.get_all(
                    filters=config.filters,
                    limit=config.limit,
                    offset=config.offset
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._tasks_to_json(tasks)
                elif config.report_format == ReportFormat.CSV:
                    content = self._tasks_to_csv(tasks)
                else:
                    content = self._tasks_to_text(tasks)
                return ReportData(
                    report_type=ReportType.TASK_LIST,
                    report_format=config.report_format,
                    title="Task List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(tasks)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.TASK_LIST,
                report_format=config.report_format,
                title="Task List",
                content=f"Error: {e}"
            )

    def _tasks_to_text(self, tasks: List[PublishingTask]) -> str:
        lines = ["TASK LIST", "=" * 60]
        lines.append(f"{'ID':<8} {'Name':<20} {'Status':<12} {'Created':<20}")
        lines.append("-" * 60)
        for t in tasks:
            lines.append(f"{t.id:<8} {t.name or '':<20} {t.status.value if t.status else '':<12} {t.created_at.isoformat() if t.created_at else '':<20}")
        return "\n".join(lines)

    def _tasks_to_json(self, tasks: List[PublishingTask]) -> str:
        data = [{
            "id": t.id,
            "name": t.name,
            "status": t.status.value if t.status else None,
            "telegram_account_id": t.telegram_account_id,
            "group_id": t.group_id,
            "content_id": t.content_id,
            "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in tasks]
        return json.dumps(data, indent=2, default=str)

    def _tasks_to_csv(self, tasks: List[PublishingTask]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Name", "Status", "Account ID", "Group ID", "Content ID", "Scheduled At", "Created At"])
        for t in tasks:
            writer.writerow([
                t.id,
                t.name or "",
                t.status.value if t.status else "",
                t.telegram_account_id or "",
                t.group_id or "",
                t.content_id or "",
                t.scheduled_at.isoformat() if t.scheduled_at else "",
                t.created_at.isoformat() if t.created_at else ""
            ])
        return output.getvalue()

    async def _generate_subscription_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.subscription_repository.session = session
                subs = await self.subscription_repository.get_all(
                    filters=config.filters,
                    limit=config.limit,
                    offset=config.offset
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._subs_to_json(subs)
                elif config.report_format == ReportFormat.CSV:
                    content = self._subs_to_csv(subs)
                else:
                    content = self._subs_to_text(subs)
                return ReportData(
                    report_type=ReportType.SUBSCRIPTION_LIST,
                    report_format=config.report_format,
                    title="Subscription List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(subs)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.SUBSCRIPTION_LIST,
                report_format=config.report_format,
                title="Subscription List",
                content=f"Error: {e}"
            )

    def _subs_to_text(self, subs: List[Subscription]) -> str:
        lines = ["SUBSCRIPTION LIST", "=" * 60]
        lines.append(f"{'ID':<8} {'User ID':<12} {'Type':<15} {'Status':<12} {'End Date':<20}")
        lines.append("-" * 60)
        for s in subs:
            lines.append(f"{s.id:<8} {s.user_id:<12} {s.subscription_type.value if s.subscription_type else '':<15} {s.status.value if s.status else '':<12} {s.end_date.isoformat() if s.end_date else '':<20}")
        return "\n".join(lines)

    def _subs_to_json(self, subs: List[Subscription]) -> str:
        data = [{
            "id": s.id,
            "user_id": s.user_id,
            "subscription_type": s.subscription_type.value if s.subscription_type else None,
            "status": s.status.value if s.status else None,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "auto_renew": s.auto_renew
        } for s in subs]
        return json.dumps(data, indent=2, default=str)

    def _subs_to_csv(self, subs: List[Subscription]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "User ID", "Type", "Status", "Start Date", "End Date", "Auto Renew"])
        for s in subs:
            writer.writerow([
                s.id,
                s.user_id or "",
                s.subscription_type.value if s.subscription_type else "",
                s.status.value if s.status else "",
                s.start_date.isoformat() if s.start_date else "",
                s.end_date.isoformat() if s.end_date else "",
                s.auto_renew
            ])
        return output.getvalue()

    async def _generate_subscription_expiring(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.subscription_repository.session = session
                from sqlalchemy import and_
                thirty_days_later = datetime.utcnow() + timedelta(days=30)
                subs = await self.subscription_repository.get_all(
                    filters={
                        "status": SubscriptionStatus.ACTIVE.value,
                        "end_date": {"gte": datetime.utcnow(), "lte": thirty_days_later}
                    },
                    limit=config.limit
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._subs_to_json(subs)
                elif config.report_format == ReportFormat.CSV:
                    content = self._subs_to_csv(subs)
                else:
                    content = self._subs_to_text(subs)
                return ReportData(
                    report_type=ReportType.SUBSCRIPTION_EXPIRING,
                    report_format=config.report_format,
                    title="Expiring Subscriptions",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(subs)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.SUBSCRIPTION_EXPIRING,
                report_format=config.report_format,
                title="Expiring Subscriptions",
                content=f"Error: {e}"
            )

    async def _generate_content_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.content_repository.session = session
                contents = await self.content_repository.get_all(
                    filters=config.filters,
                    limit=config.limit
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._contents_to_json(contents)
                elif config.report_format == ReportFormat.CSV:
                    content = self._contents_to_csv(contents)
                else:
                    content = self._contents_to_text(contents)
                return ReportData(
                    report_type=ReportType.CONTENT_LIST,
                    report_format=config.report_format,
                    title="Content List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(contents)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.CONTENT_LIST,
                report_format=config.report_format,
                title="Content List",
                content=f"Error: {e}"
            )

    def _contents_to_text(self, contents: List[Content]) -> str:
        lines = ["CONTENT LIST", "=" * 60]
        lines.append(f"{'ID':<8} {'Title':<25} {'Type':<15} {'Created':<20}")
        lines.append("-" * 60)
        for c in contents:
            lines.append(f"{c.id:<8} {c.title or '':<25} {c.content_type.value if c.content_type else '':<15} {c.created_at.isoformat() if c.created_at else '':<20}")
        return "\n".join(lines)

    async def _generate_group_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.group_repository.session = session
                groups = await self.group_repository.get_all(
                    filters=config.filters,
                    limit=config.limit
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._groups_to_json(groups)
                elif config.report_format == ReportFormat.CSV:
                    content = self._groups_to_csv(groups)
                else:
                    content = self._groups_to_text(groups)
                return ReportData(
                    report_type=ReportType.GROUP_LIST,
                    report_format=config.report_format,
                    title="Group List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(groups)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.GROUP_LIST,
                report_format=config.report_format,
                title="Group List",
                content=f"Error: {e}"
            )

    def _groups_to_text(self, groups: List[Group]) -> str:
        lines = ["GROUP LIST", "=" * 60]
        lines.append(f"{'ID':<8} {'Name':<25} {'Type':<15} {'Group ID':<15}")
        lines.append("-" * 60)
        for g in groups:
            lines.append(f"{g.id:<8} {g.group_name or '':<25} {g.group_type.value if g.group_type else '':<15} {g.group_id or '':<15}")
        return "\n".join(lines)

    async def _generate_audit_log(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.audit_log_repository.session = session
                logs = await self.audit_log_repository.get_all(
                    filters=config.filters,
                    limit=config.limit,
                    offset=config.offset,
                    order_by=config.sort_by,
                    descending=config.sort_descending
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._audit_logs_to_json(logs)
                elif config.report_format == ReportFormat.CSV:
                    content = self._audit_logs_to_csv(logs)
                else:
                    content = self._audit_logs_to_text(logs)
                return ReportData(
                    report_type=ReportType.AUDIT_LOG,
                    report_format=config.report_format,
                    title="Audit Log",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(logs)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.AUDIT_LOG,
                report_format=config.report_format,
                title="Audit Log",
                content=f"Error: {e}"
            )

    def _audit_logs_to_text(self, logs: List[AuditLog]) -> str:
        lines = ["AUDIT LOG", "=" * 60]
        lines.append(f"{'ID':<8} {'Admin':<12} {'Action':<25} {'Target':<20}")
        lines.append("-" * 60)
        for l in logs:
            target = f"{l.target_type}:{l.target_id}" if l.target_type and l.target_id else ""
            lines.append(f"{l.id:<8} {l.administrator_id:<12} {l.action or '':<25} {target:<20}")
        return "\n".join(lines)

    async def _generate_notification_list(
        self, config: ReportConfig, admin_id: Optional[int] = None
    ) -> ReportData:
        try:
            async with self.session_factory() as session:
                self.notification_repository.session = session
                notifs = await self.notification_repository.get_all(
                    filters=config.filters,
                    limit=config.limit
                )
                if config.report_format == ReportFormat.JSON:
                    content = self._notifs_to_json(notifs)
                elif config.report_format == ReportFormat.CSV:
                    content = self._notifs_to_csv(notifs)
                else:
                    content = self._notifs_to_text(notifs)
                return ReportData(
                    report_type=ReportType.NOTIFICATION_LIST,
                    report_format=config.report_format,
                    title="Notification List",
                    generated_at=datetime.utcnow(),
                    generated_by=admin_id,
                    content=content,
                    row_count=len(notifs)
                )
        except Exception as e:
            return ReportData(
                report_type=ReportType.NOTIFICATION_LIST,
                report_format=config.report_format,
                title="Notification List",
                content=f"Error: {e}"
            )

    def _notifs_to_text(self, notifs: List[Notification]) -> str:
        lines = ["NOTIFICATION LIST", "=" * 60]
        lines.append(f"{'ID':<8} {'User ID':<12} {'Type':<20} {'Read':<5} {'Created':<20}")
        lines.append("-" * 60)
        for n in notifs:
            lines.append(f"{n.id:<8} {n.user_id:<12} {n.notification_type or '':<20} {n.is_read:<5} {n.created_at.isoformat() if n.created_at else '':<20}")
        return "\n".join(lines)
