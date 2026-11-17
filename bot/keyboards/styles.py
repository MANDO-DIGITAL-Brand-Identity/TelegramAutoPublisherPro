"""
Button styling system for Telegram Auto Publisher Pro
Centralized button styling definitions
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class ButtonStyle(Enum):
    """Button style types"""
    SUCCESS = "success"
    PRIMARY = "primary"
    DANGER = "danger"
    SECONDARY = "secondary"
    WARNING = "warning"
    INFO = "info"
    LIGHT = "light"
    DARK = "dark"


# Button style definitions
# Note: Telegram Bot API doesn't support native button colors,
# but we can use emojis and formatting to create visual distinction
BUTTON_STYLES: Dict[ButtonStyle, Dict[str, Any]] = {
    ButtonStyle.SUCCESS: {
        "prefix": "✅ ",
        "color": "green",
        "description": "For positive actions like Start, Confirm, Save",
        "use_for": [
            "Start Publishing",
            "Confirm Subscription",
            "Activate Account",
            "Save Settings",
            "Verify Membership",
            "Resume Task",
            "Confirm Operations",
            "Yes",
            "OK"
        ]
    },
    ButtonStyle.PRIMARY: {
        "prefix": "🔵 ",
        "color": "blue",
        "description": "For main navigation and information",
        "use_for": [
            "Main Menu",
            "Account Management",
            "Content Management",
            "Group Management",
            "Reports",
            "Settings",
            "Navigation",
            "Information Screens",
            "Dashboard",
            "Back"
        ]
    },
    ButtonStyle.DANGER: {
        "prefix": "❌ ",
        "color": "red",
        "description": "For destructive actions",
        "use_for": [
            "Delete Account",
            "Remove Administrator",
            "Block User",
            "Stop Publishing",
            "Delete Content",
            "Disable Account",
            "Destructive Operations",
            "No",
            "Cancel"
        ]
    },
    ButtonStyle.SECONDARY: {
        "prefix": "⚪ ",
        "color": "gray",
        "description": "For secondary actions",
        "use_for": [
            "Edit",
            "View",
            "Details",
            "Preview",
            "Refresh"
        ]
    },
    ButtonStyle.WARNING: {
        "prefix": "⚠️ ",
        "color": "orange",
        "description": "For warning actions",
        "use_for": [
            "Pause Publishing",
            "Suspend",
            "Warn"
        ]
    },
    ButtonStyle.INFO: {
        "prefix": "ℹ️ ",
        "color": "cyan",
        "description": "For information actions",
        "use_for": [
            "Help",
            "Info",
            "About",
            "Status"
        ]
    }
}


@dataclass
class ButtonConfig:
    """Configuration for a single button"""
    
    text: str
    callback_data: str
    style: ButtonStyle = ButtonStyle.PRIMARY
    url: Optional[str] = None
    switch_inline_query: Optional[str] = None
    switch_inline_query_current_chat: Optional[str] = None
    
    def get_display_text(self) -> str:
        """Get the display text with style prefix"""
        style_config = BUTTON_STYLES.get(self.style, BUTTON_STYLES[ButtonStyle.PRIMARY])
        prefix = style_config.get("prefix", "")
        return f"{prefix}{self.text}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for aiogram InlineKeyboardButton"""
        button_dict: Dict[str, Any] = {"text": self.get_display_text()}
        
        if self.callback_data:
            button_dict["callback_data"] = self.callback_data
        if self.url:
            button_dict["url"] = self.url
        if self.switch_inline_query:
            button_dict["switch_inline_query"] = self.switch_inline_query
        if self.switch_inline_query_current_chat:
            button_dict["switch_inline_query_current_chat"] = self.switch_inline_query_current_chat
        
        return button_dict


@dataclass
class KeyboardConfig:
    """Configuration for a keyboard (inline keyboard)"""
    
    buttons: List[List[ButtonConfig]] = field(default_factory=list)
    resize_keyboard: bool = True
    one_time_keyboard: bool = False
    selective: bool = False
    
    def add_row(self, buttons: List[ButtonConfig]) -> None:
        """Add a row of buttons"""
        self.buttons.append(buttons)
    
    def add_button(self, button: ButtonConfig) -> None:
        """Add a single button in a new row"""
        self.buttons.append([button])
    
    def to_aiogram_format(self) -> List[List[Dict[str, Any]]]:
        """Convert to aiogram InlineKeyboardMarkup format"""
        return [[btn.to_dict() for btn in row] for row in self.buttons]


class ButtonStyles:
    """
    Centralized button styling system.
    Provides pre-defined button configurations with consistent styling.
    """
    
    # ===========================================
    # SUCCESS BUTTONS
    # ===========================================
    
    @staticmethod
    def success(text: str, callback_data: str) -> ButtonConfig:
        """Create a success-style button"""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            style=ButtonStyle.SUCCESS
        )
    
    @staticmethod
    def start_publishing() -> ButtonConfig:
        """Start Publishing button"""
        return ButtonStyles.success("Start Publishing", "start_publishing")
    
    @staticmethod
    def confirm_subscription() -> ButtonConfig:
        """Confirm Subscription button"""
        return ButtonStyles.success("Confirm Subscription", "confirm_subscription")
    
    @staticmethod
    def activate_account() -> ButtonConfig:
        """Activate Account button"""
        return ButtonStyles.success("Activate Account", "activate_account")
    
    @staticmethod
    def save_settings() -> ButtonConfig:
        """Save Settings button"""
        return ButtonStyles.success("Save Settings", "save_settings")
    
    @staticmethod
    def verify_membership() -> ButtonConfig:
        """Verify Membership button"""
        return ButtonStyles.success("Verify Membership", "verify_membership")
    
    @staticmethod
    def resume_task() -> ButtonConfig:
        """Resume Task button"""
        return ButtonStyles.success("Resume Task", "resume_task")
    
    @staticmethod
    def confirm_operation() -> ButtonConfig:
        """Confirm Operation button"""
        return ButtonStyles.success("Confirm", "confirm")
    
    @staticmethod
    def yes_button() -> ButtonConfig:
        """Yes button"""
        return ButtonStyles.success("Yes", "yes")
    
    @staticmethod
    def ok_button() -> ButtonConfig:
        """OK button"""
        return ButtonStyles.success("OK", "ok")
    
    # ===========================================
    # PRIMARY BUTTONS
    # ===========================================
    
    @staticmethod
    def primary(text: str, callback_data: str) -> ButtonConfig:
        """Create a primary-style button"""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            style=ButtonStyle.PRIMARY
        )
    
    @staticmethod
    def main_menu() -> ButtonConfig:
        """Main Menu button"""
        return ButtonStyles.primary("Main Menu", "main_menu")
    
    @staticmethod
    def account_management() -> ButtonConfig:
        """Account Management button"""
        return ButtonStyles.primary("Account Management", "account_management")
    
    @staticmethod
    def content_management() -> ButtonConfig:
        """Content Management button"""
        return ButtonStyles.primary("Content Management", "content_management")
    
    @staticmethod
    def group_management() -> ButtonConfig:
        """Group Management button"""
        return ButtonStyles.primary("Group Management", "group_management")
    
    @staticmethod
    def publishing_management() -> ButtonConfig:
        """Publishing Management button"""
        return ButtonStyles.primary("Publishing Management", "publishing_management")
    
    @staticmethod
    def reports() -> ButtonConfig:
        """Reports button"""
        return ButtonStyles.primary("Reports", "reports")
    
    @staticmethod
    def settings() -> ButtonConfig:
        """Settings button"""
        return ButtonStyles.primary("Settings", "settings")
    
    @staticmethod
    def navigation() -> ButtonConfig:
        """Navigation button"""
        return ButtonStyles.primary("Navigation", "navigation")
    
    @staticmethod
    def information_screens() -> ButtonConfig:
        """Information Screens button"""
        return ButtonStyles.primary("Information", "information")
    
    @staticmethod
    def dashboard() -> ButtonConfig:
        """Dashboard button"""
        return ButtonStyles.primary("Dashboard", "dashboard")
    
    @staticmethod
    def back_button() -> ButtonConfig:
        """Back button"""
        return ButtonStyles.primary("Back", "back")
    
    @staticmethod
    def private_messaging() -> ButtonConfig:
        """Private Messaging button"""
        return ButtonStyles.primary("Private Messaging", "private_messaging")
    
    @staticmethod
    def subscription_management() -> ButtonConfig:
        """Subscription Management button"""
        return ButtonStyles.primary("Subscription Management", "subscription_management")
    
    @staticmethod
    def help_support() -> ButtonConfig:
        """Help and Support button"""
        return ButtonStyles.primary("Help and Support", "help_support")
    
    @staticmethod
    def application_settings() -> ButtonConfig:
        """Application Settings button"""
        return ButtonStyles.primary("Application Settings", "application_settings")
    
    # ===========================================
    # DANGER BUTTONS
    # ===========================================
    
    @staticmethod
    def danger(text: str, callback_data: str) -> ButtonConfig:
        """Create a danger-style button"""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            style=ButtonStyle.DANGER
        )
    
    @staticmethod
    def delete_account() -> ButtonConfig:
        """Delete Account button"""
        return ButtonStyles.danger("Delete Account", "delete_account")
    
    @staticmethod
    def remove_administrator() -> ButtonConfig:
        """Remove Administrator button"""
        return ButtonStyles.danger("Remove Administrator", "remove_administrator")
    
    @staticmethod
    def block_user() -> ButtonConfig:
        """Block User button"""
        return ButtonStyles.danger("Block User", "block_user")
    
    @staticmethod
    def stop_publishing() -> ButtonConfig:
        """Stop Publishing button"""
        return ButtonStyles.danger("Stop Publishing", "stop_publishing")
    
    @staticmethod
    def delete_content() -> ButtonConfig:
        """Delete Content button"""
        return ButtonStyles.danger("Delete Content", "delete_content")
    
    @staticmethod
    def disable_account() -> ButtonConfig:
        """Disable Account button"""
        return ButtonStyles.danger("Disable Account", "disable_account")
    
    @staticmethod
    def destructive_operation() -> ButtonConfig:
        """Destructive Operation button"""
        return ButtonStyles.danger("Destructive Operation", "destructive_operation")
    
    @staticmethod
    def no_button() -> ButtonConfig:
        """No button"""
        return ButtonStyles.danger("No", "no")
    
    @staticmethod
    def cancel_button() -> ButtonConfig:
        """Cancel button"""
        return ButtonStyles.danger("Cancel", "cancel")
    
    # ===========================================
    # SECONDARY BUTTONS
    # ===========================================
    
    @staticmethod
    def secondary(text: str, callback_data: str) -> ButtonConfig:
        """Create a secondary-style button"""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            style=ButtonStyle.SECONDARY
        )
    
    @staticmethod
    def edit() -> ButtonConfig:
        """Edit button"""
        return ButtonStyles.secondary("Edit", "edit")
    
    @staticmethod
    def view() -> ButtonConfig:
        """View button"""
        return ButtonStyles.secondary("View", "view")
    
    @staticmethod
    def details() -> ButtonConfig:
        """Details button"""
        return ButtonStyles.secondary("Details", "details")
    
    @staticmethod
    def preview() -> ButtonConfig:
        """Preview button"""
        return ButtonStyles.secondary("Preview", "preview")
    
    @staticmethod
    def refresh() -> ButtonConfig:
        """Refresh button"""
        return ButtonStyles.secondary("Refresh", "refresh")
    
    # ===========================================
    # WARNING BUTTONS
    # ===========================================
    
    @staticmethod
    def warning(text: str, callback_data: str) -> ButtonConfig:
        """Create a warning-style button"""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            style=ButtonStyle.WARNING
        )
    
    @staticmethod
    def pause_publishing() -> ButtonConfig:
        """Pause Publishing button"""
        return ButtonStyles.warning("Pause Publishing", "pause_publishing")
    
    @staticmethod
    def suspend() -> ButtonConfig:
        """Suspend button"""
        return ButtonStyles.warning("Suspend", "suspend")
    
    @staticmethod
    def warn() -> ButtonConfig:
        """Warn button"""
        return ButtonStyles.warning("Warn", "warn")
    
    # ===========================================
    # INFO BUTTONS
    # ===========================================
    
    @staticmethod
    def info(text: str, callback_data: str) -> ButtonConfig:
        """Create an info-style button"""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            style=ButtonStyle.INFO
        )
    
    @staticmethod
    def help_button() -> ButtonConfig:
        """Help button"""
        return ButtonStyles.info("Help", "help")
    
    @staticmethod
    def about() -> ButtonConfig:
        """About button"""
        return ButtonStyles.info("About", "about")
    
    @staticmethod
    def status() -> ButtonConfig:
        """Status button"""
        return ButtonStyles.info("Status", "status")
    
    # ===========================================
    # CHANNEL SUBSCRIPTION BUTTONS
    # ===========================================
    
    @staticmethod
    def join_channel(channel_username: str) -> ButtonConfig:
        """Join Channel button"""
        return ButtonConfig(
            text=f"Join @{channel_username}",
            url=f"https://t.me/{channel_username}",
            style=ButtonStyle.PRIMARY
        )
    
    @staticmethod
    def verify_subscription() -> ButtonConfig:
        """Verify Subscription button"""
        return ButtonStyles.success("Verify Subscription", "verify_subscription")
    
    # ===========================================
    # ADMIN BUTTONS
    # ===========================================
    
    @staticmethod
    def admin_dashboard() -> ButtonConfig:
        """Admin Dashboard button"""
        return ButtonStyles.primary("Admin Dashboard", "admin_dashboard")
    
    @staticmethod
    def user_management() -> ButtonConfig:
        """User Management button"""
        return ButtonStyles.primary("User Management", "user_management")
    
    @staticmethod
    def admin_management() -> ButtonConfig:
        """Admin Management button"""
        return ButtonStyles.primary("Admin Management", "admin_management")
    
    @staticmethod
    def broadcast_management() -> ButtonConfig:
        """Broadcast Management button"""
        return ButtonStyles.primary("Broadcast Management", "broadcast_management")
    
    @staticmethod
    def system_settings() -> ButtonConfig:
        """System Settings button"""
        return ButtonStyles.primary("System Settings", "system_settings")
    
    @staticmethod
    def activity_logs() -> ButtonConfig:
        """Activity Logs button"""
        return ButtonStyles.primary("Activity Logs", "activity_logs")
    
    @staticmethod
    def error_reports() -> ButtonConfig:
        """Error Reports button"""
        return ButtonStyles.primary("Error Reports", "error_reports")
    
    @staticmethod
    def database_management() -> ButtonConfig:
        """Database Management button"""
        return ButtonStyles.primary("Database Management", "database_management")
    
    @staticmethod
    def backup_restore() -> ButtonConfig:
        """Backup and Restore button"""
        return ButtonStyles.primary("Backup and Restore", "backup_restore")
    
    @staticmethod
    def maintenance_mode() -> ButtonConfig:
        """Maintenance Mode button"""
        return ButtonStyles.warning("Maintenance Mode", "maintenance_mode")


__all__ = [
    'ButtonStyle',
    'BUTTON_STYLES',
    'ButtonConfig',
    'KeyboardConfig',
    'ButtonStyles',
]
