"""
Main keyboard for Telegram Auto Publisher Pro
Contains the main menu and navigation keyboards
"""

from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .styles import ButtonStyles, ButtonConfig, KeyboardConfig


class MainKeyboard:
    """
    Main keyboard with navigation buttons.
    """
    
    @staticmethod
    def get_main_menu() -> InlineKeyboardMarkup:
        """Get the main menu keyboard."""
        buttons = [
            [
                ButtonStyles.account_management().to_dict(),
                ButtonStyles.publishing_management().to_dict()
            ],
            [
                ButtonStyles.content_management().to_dict(),
                ButtonStyles.group_management().to_dict()
            ],
            [
                ButtonStyles.private_messaging().to_dict(),
                ButtonStyles.reports().to_dict()
            ],
            [
                ButtonStyles.subscription_management().to_dict(),
                ButtonStyles.application_settings().to_dict()
            ],
            [
                ButtonStyles.help_support().to_dict()
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_main_menu_arabic() -> InlineKeyboardMarkup:
        """Get the main menu keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="👥 إدارة الحسابات", callback_data="account_management"),
                InlineKeyboardButton(text="📢 إدارة النشر", callback_data="publishing_management")
            ],
            [
                InlineKeyboardButton(text="📝 إدارة المحتوى", callback_data="content_management"),
                InlineKeyboardButton(text="👥 إدارة المجموعات", callback_data="group_management")
            ],
            [
                InlineKeyboardButton(text="💬 المراسلات الخاصة", callback_data="private_messaging"),
                InlineKeyboardButton(text="📊 التقارير", callback_data="reports")
            ],
            [
                InlineKeyboardButton(text="💳 إدارة الاشتراك", callback_data="subscription_management"),
                InlineKeyboardButton(text="⚙️ إعدادات التطبيق", callback_data="application_settings")
            ],
            [
                InlineKeyboardButton(text="❓ المساعدة والدعم", callback_data="help_support")
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
        """Get a simple back button."""
        buttons = [[ButtonStyles.back_button().to_dict()]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_back_button_arabic() -> InlineKeyboardMarkup:
        """Get a back button in Arabic."""
        buttons = [[InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_confirm_cancel_buttons(
        confirm_callback: str = "confirm",
        cancel_callback: str = "cancel"
    ) -> InlineKeyboardMarkup:
        """Get confirm and cancel buttons."""
        buttons = [
            [
                ButtonStyles.yes_button().to_dict() | {"callback_data": confirm_callback},
                ButtonStyles.cancel_button().to_dict() | {"callback_data": cancel_callback}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_confirm_cancel_buttons_arabic(
        confirm_callback: str = "confirm",
        cancel_callback: str = "cancel"
    ) -> InlineKeyboardMarkup:
        """Get confirm and cancel buttons in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="✅ نعم", callback_data=confirm_callback),
                InlineKeyboardButton(text="❌ لا", callback_data=cancel_callback)
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_pagination_buttons(
        page: int,
        total_pages: int,
        base_callback: str = "page"
    ) -> InlineKeyboardMarkup:
        """Get pagination buttons."""
        buttons = []
        
        # Previous button
        if page > 1:
            buttons.append(ButtonStyles.back_button().to_dict() | {
                "callback_data": f"{base_callback}_{page - 1}",
                "text": "⬅️ Previous"
            })
        
        # Page indicator (not clickable)
        buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="no_op"
        ))
        
        # Next button
        if page < total_pages:
            buttons.append(ButtonStyles.primary("Next", f"{base_callback}_{page + 1}").to_dict() | {
                "text": "Next ➡️"
            })
        
        return InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    @staticmethod
    def get_pagination_buttons_arabic(
        page: int,
        total_pages: int,
        base_callback: str = "page"
    ) -> InlineKeyboardMarkup:
        """Get pagination buttons in Arabic."""
        buttons = []
        
        # Previous button
        if page > 1:
            buttons.append(InlineKeyboardButton(
                text="⬅️ السابق",
                callback_data=f"{base_callback}_{page - 1}"
            ))
        
        # Page indicator
        buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="no_op"
        ))
        
        # Next button
        if page < total_pages:
            buttons.append(InlineKeyboardButton(
                text="التالي ➡️",
                callback_data=f"{base_callback}_{page + 1}"
            ))
        
        return InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    @staticmethod
    def get_language_selection() -> InlineKeyboardMarkup:
        """Get language selection keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="language_en"),
                InlineKeyboardButton(text="🇸🇦 العربية", callback_data="language_ar")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = [
    'MainKeyboard',
]
