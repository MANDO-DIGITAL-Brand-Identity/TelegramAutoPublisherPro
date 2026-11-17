"""
Configuration management for Telegram Auto Publisher Pro
Uses Pydantic for validation and environment variables
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os
from pathlib import Path


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    DB_TYPE: str = Field(default="sqlite", description="Database type: sqlite or postgresql")
    SQLite_PATH: str = Field(default="data/bot.db", description="SQLite database path")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="telegram_publisher", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="", description="PostgreSQL password")
    
    @property
    def database_url(self) -> str:
        """Generate database URL based on configuration"""
        if self.DB_TYPE == "sqlite":
            # Ensure directory exists
            Path(self.SQLite_PATH).parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{self.SQLite_PATH}"
        else:
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class TelegramConfig(BaseSettings):
    """Telegram configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    BOT_TOKEN: str = Field(..., description="Bot token for aiogram control bot")
    BOT_USERNAME: str = Field(default="TelegramAutoPublisherBot", description="Bot username")
    
    # Telethon API configuration
    API_ID: int = Field(..., description="Telegram API ID from my.telegram.org")
    API_HASH: str = Field(..., description="Telegram API hash from my.telegram.org")
    
    # Session configuration
    SESSION_DIR: str = Field(default="sessions", description="Directory to store Telethon sessions")
    
    # Rate limiting
    RATE_LIMIT: int = Field(default=30, description="Requests per second limit")
    FLOOD_SLEEP_THRESHOLD: int = Field(default=60, description="Sleep time for FloodWait in seconds")
    
    # Proxy configuration (optional)
    PROXY_ENABLED: bool = Field(default=False, description="Enable proxy for Telethon")
    PROXY_HOST: str = Field(default="", description="Proxy host")
    PROXY_PORT: int = Field(default=0, description="Proxy port")
    PROXY_TYPE: str = Field(default="socks5", description="Proxy type: http, socks5, mtproto")
    
    @property
    def session_path(self) -> Path:
        """Get session directory path"""
        path = Path(self.SESSION_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


class SecurityConfig(BaseSettings):
    """Security configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Encryption
    ENCRYPTION_KEY: str = Field(default="", description="Encryption key for sensitive data")
    
    # Session protection
    SESSION_ENCRYPTION_ENABLED: bool = Field(default=True, description="Enable session file encryption")
    
    # Administrator configuration
    SUPER_ADMIN_ID: int = Field(..., description="Telegram user ID of the super administrator")
    ADMIN_IDS: List[int] = Field(default_factory=list, description="List of administrator user IDs")
    
    # Authentication
    TWO_FACTOR_REQUIRED: bool = Field(default=False, description="Require 2FA for all accounts")
    
    # File security
    MAX_FILE_SIZE_MB: int = Field(default=50, description="Maximum file size for uploads in MB")
    ALLOWED_EXTENSIONS: List[str] = Field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mp3", ".avi", ".mov",
        ".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"
    ], description="Allowed file extensions for uploads")


class SubscriptionConfig(BaseSettings):
    """Subscription management configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Free tier limits
    FREE_MAX_ACCOUNTS: int = Field(default=2, description="Maximum accounts for free users")
    FREE_MAX_GROUPS: int = Field(default=5, description="Maximum groups for free users")
    FREE_PUBLISH_INTERVAL_MINUTES: int = Field(default=60, description="Minimum publish interval for free users")
    
    # Premium tier limits
    PREMIUM_MAX_ACCOUNTS: int = Field(default=10, description="Maximum accounts for premium users")
    PREMIUM_MAX_GROUPS: int = Field(default=50, description="Maximum groups for premium users")
    PREMIUM_PUBLISH_INTERVAL_MINUTES: int = Field(default=5, description="Minimum publish interval for premium users")
    
    # Subscription duration
    PREMIUM_MONTHLY_DAYS: int = Field(default=30, description="Duration of monthly subscription in days")
    PREMIUM_YEARLY_DAYS: int = Field(default=365, description="Duration of yearly subscription in days")
    
    # Trial
    ENABLE_TRIAL: bool = Field(default=True, description="Enable trial subscription")
    TRIAL_DAYS: int = Field(default=7, description="Trial duration in days")
    
    # Notifications
    EXPIRATION_WARNING_DAYS: int = Field(default=3, description="Days before expiration to warn users")


class ChannelConfig(BaseSettings):
    """Mandatory channel subscription configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Required channels
    REQUIRED_CHANNELS: List[str] = Field(default_factory=list, description="List of required channel usernames")
    REQUIRED_CHANNEL_IDS: List[int] = Field(default_factory=list, description="List of required channel IDs")
    
    # Verification settings
    VERIFY_ON_STARTUP: bool = Field(default=True, description="Verify channel subscription on bot startup")
    VERIFY_INTERVAL_HOURS: int = Field(default=24, description="Re-verify subscription every X hours")
    ALLOW_WITHOUT_VERIFICATION: bool = Field(default=False, description="Allow access without channel verification")
    
    # Messages
    JOIN_MESSAGE: str = Field(default="Please join our channel to use the bot", description="Message to show when user needs to join")
    SUCCESS_MESSAGE: str = Field(default="Thank you for joining! You now have access.", description="Message after successful verification")


class SchedulerConfig(BaseSettings):
    """Scheduler configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    ENABLED: bool = Field(default=True, description="Enable scheduled publishing")
    TIMEZONE: str = Field(default="UTC", description="Timezone for scheduling")
    MAX_CONCURRENT_TASKS: int = Field(default=5, description="Maximum concurrent publishing tasks")
    TASK_TIMEOUT_MINUTES: int = Field(default=30, description="Task timeout in minutes")
    RETRY_ATTEMPTS: int = Field(default=3, description="Number of retry attempts for failed tasks")
    RETRY_DELAY_SECONDS: int = Field(default=60, description="Delay between retry attempts")


class LoggingConfig(BaseSettings):
    """Logging configuration"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")
    LOG_FILE: str = Field(default="logs/bot.log", description="Log file path")
    LOG_MAX_SIZE_MB: int = Field(default=10, description="Maximum log file size in MB")
    LOG_BACKUP_COUNT: int = Field(default=5, description="Number of backup log files")
    ENABLE_CONSOLE_LOG: bool = Field(default=True, description="Enable console logging")


class Settings(BaseSettings):
    """Main configuration class combining all configurations"""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    subscription: SubscriptionConfig = Field(default_factory=SubscriptionConfig)
    channel: ChannelConfig = Field(default_factory=ChannelConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # General settings
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    
    # Application
    APP_NAME: str = Field(default="Telegram Auto Publisher Pro", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    
    # Paths
    DATA_DIR: str = Field(default="data", description="Data directory")
    MEDIA_DIR: str = Field(default="media", description="Media directory")
    BACKUP_DIR: str = Field(default="backups", description="Backup directory")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == "development"


# Create configuration instance
config = Settings()

# Ensure directories exist
def ensure_directories():
    """Create necessary directories"""
    directories = [
        config.DATA_DIR,
        config.MEDIA_DIR,
        config.BACKUP_DIR,
        config.telegram.SESSION_DIR,
    ]
    
    # Add logging directory
    log_dir = config.logging.LOG_FILE if isinstance(config.logging.LOG_FILE, str) else str(config.logging.LOG_FILE)
    if log_dir:
        directories.append(Path(log_dir).parent if Path(log_dir).parent.exists() or str(Path(log_dir).parent) else "logs")
    
    # Add database directory for SQLite
    if config.database.DB_TYPE == "sqlite":
        db_path = Path(config.database.SQLite_PATH)
        directories.append(str(db_path.parent))
    
    for dir_path in directories:
        if dir_path:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print("Configuration loaded successfully")
    print(f"Database URL: {config.database.database_url}")
    print(f"Session directory: {config.telegram.session_path}")
    print(f"Environment: {config.ENVIRONMENT}")
