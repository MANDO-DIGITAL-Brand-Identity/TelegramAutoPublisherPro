#!/usr/bin/env python3
"""
Telegram Auto Publisher Pro - Main Application Entry Point

This module initializes and runs the complete application including:
- Telethon client management
- aiogram control bot
- Database connections
- Scheduler
- All service modules
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config, ensure_directories
from database.database import init_db, get_async_session
from database.models import Base

# Initialize logging
from security.encryption import EncryptionManager
from security.permissions import PermissionManager
from security.validation import ValidationManager
from accounts.manager import AccountManager
from accounts.authentication import Authenticator
from accounts.session_manager import SessionManager
from accounts.connection import ConnectionManager
from publisher.engine import PublishingEngine
from publisher.scheduler import TaskScheduler
from publisher.content_manager import ContentManager
from publisher.group_manager import GroupManager
from publisher.task_manager import TaskManager
from notifications.manager import NotificationManager
from admin.dashboard import AdminDashboard
from admin.channel_manager import ChannelManager
from admin.subscription_manager import SubscriptionManager
from admin.broadcast_manager import BroadcastManager
from admin.audit_manager import AuditManager
from admin.user_manager import UserManager
from admin.admin_manager import AdminManager
from reports.statistics import StatisticsManager
from reports.report_generator import ReportGenerator
from bot.main import create_bot, start_bot


class Application:
    """Main application class that orchestrates all components"""
    
    def __init__(self):
        """Initialize the application"""
        self.config = config
        self.db_initialized = False
        self.encryption_manager: Optional[EncryptionManager] = None
        self.permission_manager: Optional[PermissionManager] = None
        self.validation_manager: Optional[ValidationManager] = None
        self.account_manager: Optional[AccountManager] = None
        self.authenticator: Optional[Authenticator] = None
        self.session_manager: Optional[SessionManager] = None
        self.connection_manager: Optional[ConnectionManager] = None
        self.publishing_engine: Optional[PublishingEngine] = None
        self.task_scheduler: Optional[TaskScheduler] = None
        self.content_manager: Optional[ContentManager] = None
        self.group_manager: Optional[GroupManager] = None
        self.task_manager: Optional[TaskManager] = None
        self.notification_manager: Optional[NotificationManager] = None
        self.admin_dashboard: Optional[AdminDashboard] = None
        self.channel_manager: Optional[ChannelManager] = None
        self.subscription_manager: Optional[SubscriptionManager] = None
        self.broadcast_manager: Optional[BroadcastManager] = None
        self.audit_manager: Optional[AuditManager] = None
        self.user_manager: Optional[UserManager] = None
        self.admin_manager: Optional[AdminManager] = None
        self.statistics_manager: Optional[StatisticsManager] = None
        self.report_generator: Optional[ReportGenerator] = None
        self.bot = None
        
        # Setup logging
        self._setup_logging()
        
        # Ensure directories exist
        ensure_directories()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing {self.config.APP_NAME} v{self.config.APP_VERSION}")
        self.logger.info(f"Environment: {self.config.ENVIRONMENT}")
        self.logger.info(f"Debug mode: {self.config.DEBUG}")
    
    def _setup_logging(self):
        """Configure logging for the application"""
        log_level = getattr(logging, self.config.logging.LOG_LEVEL.upper(), logging.INFO)
        
        # Create log directory
        log_dir = Path(self.config.logging.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(
                    self.config.logging.LOG_FILE,
                    maxBytes=self.config.logging.LOG_MAX_SIZE_MB * 1024 * 1024,
                    backupCount=self.config.logging.LOG_BACKUP_COUNT,
                    encoding='utf-8'
                ),
            ]
        )
        
        # Add console handler if enabled
        if self.config.logging.ENABLE_CONSOLE_LOG:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logging.getLogger().addHandler(console_handler)
        
        # Set specific log levels for noisy libraries
        logging.getLogger('telethon').setLevel(logging.WARNING)
        logging.getLogger('aiogram').setLevel(logging.INFO)
        logging.getLogger('apscheduler').setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize all application components"""
        self.logger.info("Starting application initialization...")
        
        try:
            # 1. Initialize database
            self.logger.info("Initializing database...")
            await self._initialize_database()
            self.logger.info("Database initialized successfully")
            
            # 2. Initialize security managers
            self.logger.info("Initializing security managers...")
            self.encryption_manager = EncryptionManager(
                key=self.config.security.ENCRYPTION_KEY
            )
            self.permission_manager = PermissionManager(
                config=self.config,
                session_factory=get_async_session
            )
            self.validation_manager = ValidationManager()
            self.logger.info("Security managers initialized")
            
            # 3. Initialize managers
            self.logger.info("Initializing service managers...")
            
            # Create session factory
            self.session_factory = get_async_session
            
            # ==================== ACCOUNTS MODULE ====================
            
            # Session manager for Telethon sessions
            self.session_manager = SessionManager(
                config=self.config,
                encryption_manager=self.encryption_manager
            )
            
            # Connection manager for Telethon clients
            self.connection_manager = ConnectionManager(
                config=self.config,
                session_manager=self.session_manager
            )
            
            # Authenticator for login
            self.authenticator = Authenticator(
                config=self.config,
                session_manager=self.session_manager,
                connection_manager=self.connection_manager
            )
            
            # Account manager (main interface)
            self.account_manager = AccountManager(
                config=self.config,
                encryption_manager=self.encryption_manager,
                session_factory=self.session_factory,
                authenticator=self.authenticator,
                session_manager=self.session_manager,
                connection_manager=self.connection_manager
            )
            
            # ==================== PUBLISHER MODULE ====================
            
            # Content manager
            self.content_manager = ContentManager(
                config=self.config,
                session_factory=self.session_factory
            )
            
            # Group manager
            self.group_manager = GroupManager(
                config=self.config,
                session_factory=self.session_factory,
                account_manager=self.account_manager
            )
            
            # Task manager
            self.task_manager = TaskManager(
                config=self.config,
                session_factory=self.session_factory
            )
            
            # Publishing engine
            self.publishing_engine = PublishingEngine(
                config=self.config,
                account_manager=self.account_manager,
                session_factory=self.session_factory
            )
            
            # Task scheduler
            self.task_scheduler = TaskScheduler(
                config=self.config,
                publishing_engine=self.publishing_engine,
                session_factory=self.session_factory
            )
            
            # ==================== NOTIFICATIONS MODULE ====================
            
            # Notification manager
            self.notification_manager = NotificationManager(
                config=self.config,
                session_factory=self.session_factory
            )
            
            # ==================== REPORTS MODULE ====================
            
            # Statistics manager
            self.statistics_manager = StatisticsManager(
                session_factory=self.session_factory
            )
            
            # Report generator
            self.report_generator = ReportGenerator(
                session_factory=self.session_factory,
                statistics_manager=self.statistics_manager
            )
            
            # ==================== ADMIN MODULE ====================
            
            # User manager
            self.user_manager = UserManager(
                session_factory=self.session_factory,
                audit_manager=None  # Will be set after audit_manager is created
            )
            
            # Admin manager
            self.admin_manager = AdminManager(
                session_factory=self.session_factory,
                audit_manager=None,  # Will be set after audit_manager is created
                config=self.config
            )
            
            # Channel manager
            self.channel_manager = ChannelManager(
                session_factory=self.session_factory,
                config=self.config
            )
            
            # Subscription manager
            self.subscription_manager = SubscriptionManager(
                session_factory=self.session_factory,
                user_manager=self.user_manager,
                audit_manager=None,  # Will be set after audit_manager is created
                config=self.config
            )
            
            # Broadcast manager
            self.broadcast_manager = BroadcastManager(
                session_factory=self.session_factory,
                notification_manager=self.notification_manager,
                audit_manager=None  # Will be set after audit_manager is created
            )
            
            # Audit manager
            self.audit_manager = AuditManager(
                session_factory=self.session_factory
            )
            
            # Now set the audit_manager references
            self.user_manager.audit_manager = self.audit_manager
            self.admin_manager.audit_manager = self.audit_manager
            self.subscription_manager.audit_manager = self.audit_manager
            self.broadcast_manager.audit_manager = self.audit_manager
            
            # Admin dashboard
            self.admin_dashboard = AdminDashboard(
                config=self.config,
                user_manager=self.user_manager,
                admin_manager=self.admin_manager,
                subscription_manager=self.subscription_manager,
                channel_manager=self.channel_manager,
                statistics_manager=self.statistics_manager,
                audit_manager=self.audit_manager,
                session_factory=self.session_factory
            )
            
            self.logger.info("All service managers initialized")
            
            # 4. Initialize publishing engine with dependencies
            self.publishing_engine.set_dependencies(
                notification_manager=self.notification_manager,
                statistics_manager=self.statistics_manager,
                content_manager=self.content_manager,
                group_manager=self.group_manager,
                task_manager=self.task_manager
            )
            
            # 5. Initialize task scheduler with dependencies
            self.task_scheduler.set_dependencies(
                account_manager=self.account_manager,
                notification_manager=self.notification_manager,
                content_manager=self.content_manager,
                group_manager=self.group_manager,
                task_manager=self.task_manager
            )
            
            # 6. Initialize content manager with dependencies
            if hasattr(self.content_manager, 'set_dependencies'):
                self.content_manager.set_dependencies(
                    notification_manager=self.notification_manager
                )
            
            # 7. Initialize group manager with dependencies
            if hasattr(self.group_manager, 'set_dependencies'):
                self.group_manager.set_dependencies(
                    notification_manager=self.notification_manager
                )
            
            # 8. Initialize task manager with dependencies
            if hasattr(self.task_manager, 'set_dependencies'):
                self.task_manager.set_dependencies(
                    notification_manager=self.notification_manager,
                    publishing_engine=self.publishing_engine
                )
            
            # 9. Initialize notification manager with dependencies
            if hasattr(self.notification_manager, 'set_dependencies'):
                self.notification_manager.set_dependencies(
                    user_manager=self.user_manager
                )
            
            self.logger.info("All dependencies set")
            
            # 10. Initialize and start the control bot
            self.logger.info("Initializing control bot...")
            self.bot = await create_bot(
                config=self.config,
                account_manager=self.account_manager,
                publishing_engine=self.publishing_engine,
                task_scheduler=self.task_scheduler,
                notification_manager=self.notification_manager,
                admin_dashboard=self.admin_dashboard,
                channel_manager=self.channel_manager,
                subscription_manager=self.subscription_manager,
                broadcast_manager=self.broadcast_manager,
                user_manager=self.user_manager,
                admin_manager=self.admin_manager,
                statistics_manager=self.statistics_manager,
                audit_manager=self.audit_manager,
                encryption_manager=self.encryption_manager,
                content_manager=self.content_manager,
                group_manager=self.group_manager,
                task_manager=self.task_manager,
                report_generator=self.report_generator,
                session_factory=self.session_factory
            )
            self.logger.info("Control bot initialized")
            
            # 11. Start task scheduler
            if self.config.scheduler.ENABLED:
                self.logger.info("Starting task scheduler...")
                await self.task_scheduler.start()
                self.logger.info("Task scheduler started")
            
            # 12. Recover interrupted tasks
            self.logger.info("Recovering interrupted tasks...")
            await self.task_scheduler.recover_tasks()
            self.logger.info("Task recovery completed")
            
            self.logger.info("Application initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}", exc_info=True)
            raise
    
    async def _initialize_database(self):
        """Initialize database tables and connections"""
        try:
            # Create async engine and tables
            from database.database import engine
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.db_initialized = True
            self.logger.info("Database tables created/verified")
            
            # Initialize database with default data if needed
            await self._initialize_default_data()
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise
    
    async def _initialize_default_data(self):
        """Initialize default application settings and data"""
        from database.repositories import ApplicationSettingsRepository
        from datetime import datetime
        
        try:
            async with self.session_factory() as session:
                repo = ApplicationSettingsRepository(session)
                
                # Check if settings exist
                settings = await repo.get_settings()
                if not settings:
                    # Create default settings
                    default_settings = {
                        "app_name": self.config.APP_NAME,
                        "app_version": self.config.APP_VERSION,
                        "maintenance_mode": False,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    await repo.set_settings(default_settings)
                    self.logger.info("Default application settings created")
                
                # Verify super admin exists
                from database.repositories import UserRepository
                user_repo = UserRepository(session)
                
                super_admin_id = self.config.security.SUPER_ADMIN_ID
                super_admin = await user_repo.get_user(super_admin_id)
                
                if not super_admin:
                    # Create super admin user
                    from database.models import User, UserStatus
                    super_admin = User(
                        telegram_id=super_admin_id,
                        username="super_admin",
                        first_name="Super Admin",
                        status=UserStatus.ACTIVE,
                        is_bot=False,
                        created_at=datetime.utcnow()
                    )
                    session.add(super_admin)
                    await session.commit()
                    self.logger.info(f"Super admin user created: {super_admin_id}")
                
                # Verify super admin has admin privileges
                from database.repositories import AdministratorRepository
                admin_repo = AdministratorRepository(session)
                
                admin = await admin_repo.get_administrator(super_admin_id)
                if not admin:
                    from database.models import Administrator, AdminRole
                    admin = Administrator(
                        user_id=super_admin_id,
                        role=AdminRole.SUPER_ADMIN,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    session.add(admin)
                    await session.commit()
                    self.logger.info(f"Super admin privileges granted: {super_admin_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize default data: {e}", exc_info=True)
            # Don't fail the application if default data initialization fails
            pass
    
    async def run(self):
        """Run the application"""
        try:
            # Initialize all components
            await self.initialize()
            
            # Start the bot
            self.logger.info("Starting control bot...")
            await start_bot(self.bot)
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
            await self.shutdown()
        except Exception as e:
            self.logger.error(f"Application error: {e}", exc_info=True)
            await self.shutdown()
            sys.exit(1)
    
    async def shutdown(self):
        """Shutdown the application gracefully"""
        self.logger.info("Shutting down application...")
        
        try:
            # Stop task scheduler
            if self.task_scheduler:
                await self.task_scheduler.stop()
                self.logger.info("Task scheduler stopped")
            
            # Stop publishing engine
            if self.publishing_engine:
                await self.publishing_engine.stop()
                self.logger.info("Publishing engine stopped")
            
            # Stop bot
            if self.bot:
                await self.bot.session.close()
                self.logger.info("Control bot stopped")
            
            # Close all Telethon clients
            if self.account_manager:
                await self.account_manager.close_all_clients()
                self.logger.info("All Telethon clients disconnected")
            
            self.logger.info("Application shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)


def main():
    """Main entry point"""
    # Create and run application
    app = Application()
    
    # Run the application
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
