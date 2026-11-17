"""
Account keyboard for Telegram Auto Publisher Pro
Contains account management keyboards
"""

from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .styles import ButtonStyles


class AccountKeyboard:
    """
    Account management keyboard.
    """
    
    @staticmethod
    def get_account_menu() -> InlineKeyboardMarkup:
        """Get the account management menu."""
        buttons = [
            [
                InlineKeyboardButton(text="➕ Add Account", callback_data="add_account"),
                InlineKeyboardButton(text="📋 My Accounts", callback_data="my_accounts")
            ],
            [
                InlineKeyboardButton(text="🔄 Reconnect", callback_data="reconnect_account"),
                InlineKeyboardButton(text="🗑️ Delete Account", callback_data="delete_account")
            ],
            [
                ButtonStyles.back_button().to_dict()
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_menu_arabic() -> InlineKeyboardMarkup:
        """Get the account management menu in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="➕ إضافة حساب", callback_data="add_account"),
                InlineKeyboardButton(text="📋 حساباتي", callback_data="my_accounts")
            ],
            [
                InlineKeyboardButton(text="🔄 إعادة الاتصال", callback_data="reconnect_account"),
                InlineKeyboardButton(text="🗑️ حذف الحساب", callback_data="delete_account")
            ],
            [
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_list_keyboard(
        accounts: list,
        page: int = 1,
        per_page: int = 5
    ) -> InlineKeyboardMarkup:
        """Get keyboard with list of accounts."""
        buttons = []
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_accounts = accounts[start_idx:end_idx]
        total_pages = (len(accounts) + per_page - 1) // per_page
        
        # Add account buttons
        for account in page_accounts:
            status = "✅" if account.get("is_connected") else "❌"
            account_name = account.get("account_name") or account.get("phone_number") or "Unknown"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {account_name}",
                    callback_data=f"select_account_{account.get('id')}"
                )
            ])
        
        # Add pagination buttons
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"account_list_{page - 1}"
            ))
        
        pagination_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="no_op"
        ))
        
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"account_list_{page + 1}"
            ))
        
        if pagination_buttons:
            buttons.append(pagination_buttons)
        
        # Add back button
        buttons.append([ButtonStyles.back_button().to_dict()])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_list_keyboard_arabic(
        accounts: list,
        page: int = 1,
        per_page: int = 5
    ) -> InlineKeyboardMarkup:
        """Get keyboard with list of accounts in Arabic."""
        buttons = []
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_accounts = accounts[start_idx:end_idx]
        total_pages = (len(accounts) + per_page - 1) // per_page
        
        # Add account buttons
        for account in page_accounts:
            status = "✅" if account.get("is_connected") else "❌"
            account_name = account.get("account_name") or account.get("phone_number") or "غير معروف"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {account_name}",
                    callback_data=f"select_account_{account.get('id')}"
                )
            ])
        
        # Add pagination buttons
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton(
                text="⬅️ السابق",
                callback_data=f"account_list_{page - 1}"
            ))
        
        pagination_buttons.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="no_op"
        ))
        
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton(
                text="التالي ➡️",
                callback_data=f"account_list_{page + 1}"
            ))
        
        if pagination_buttons:
            buttons.append(pagination_buttons)
        
        # Add back button
        buttons.append([InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_actions_keyboard(account_id: int) -> InlineKeyboardMarkup:
        """Get keyboard with account actions."""
        buttons = [
            [
                InlineKeyboardButton(text="🔄 Reconnect", callback_data=f"reconnect_{account_id}"),
                InlineKeyboardButton(text="📊 Statistics", callback_data=f"stats_{account_id}")
            ],
            [
                InlineKeyboardButton(text="⚙️ Settings", callback_data=f"settings_{account_id}"),
                InlineKeyboardButton(text="👥 Groups", callback_data=f"groups_{account_id}")
            ],
            [
                InlineKeyboardButton(text="📝 Content", callback_data=f"content_{account_id}"),
                InlineKeyboardButton(text="📢 Publish", callback_data=f"publish_{account_id}")
            ],
            [
                InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_confirm_{account_id}"),
                ButtonStyles.back_button().to_dict()
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_actions_keyboard_arabic(account_id: int) -> InlineKeyboardMarkup:
        """Get keyboard with account actions in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="🔄 إعادة الاتصال", callback_data=f"reconnect_{account_id}"),
                InlineKeyboardButton(text="📊 الإحصائيات", callback_data=f"stats_{account_id}")
            ],
            [
                InlineKeyboardButton(text="⚙️ الإعدادات", callback_data=f"settings_{account_id}"),
                InlineKeyboardButton(text="👥 المجموعات", callback_data=f"groups_{account_id}")
            ],
            [
                InlineKeyboardButton(text="📝 المحتوى", callback_data=f"content_{account_id}"),
                InlineKeyboardButton(text="📢 نشر", callback_data=f"publish_{account_id}")
            ],
            [
                InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_confirm_{account_id}"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_delete_confirmation_keyboard(account_id: int) -> InlineKeyboardMarkup:
        """Get delete confirmation keyboard."""
        buttons = [
            [
                InlineKeyboardButton(
                    text="⚠️ Yes, Delete",
                    callback_data=f"delete_confirmed_{account_id}"
                )
            ],
            [
                ButtonStyles.cancel_button().to_dict()
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_delete_confirmation_keyboard_arabic(account_id: int) -> InlineKeyboardMarkup:
        """Get delete confirmation keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(
                    text="⚠️ نعم، حذف",
                    callback_data=f"delete_confirmed_{account_id}"
                )
            ],
            [
                InlineKeyboardButton(text="❌ لا", callback_data="cancel")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_settings_keyboard(account_id: int) -> InlineKeyboardMarkup:
        """Get account settings keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="📝 Account Name", callback_data=f"set_name_{account_id}"),
                InlineKeyboardButton(text="📞 Phone", callback_data=f"set_phone_{account_id}")
            ],
            [
                InlineKeyboardButton(text="⏰ Publish Interval", callback_data=f"set_interval_{account_id}"),
                InlineKeyboardButton(text="🎯 Publish Mode", callback_data=f"set_mode_{account_id}")
            ],
            [
                InlineKeyboardButton(text="📊 Statistics", callback_data=f"stats_{account_id}"),
                ButtonStyles.back_button().to_dict()
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_account_settings_keyboard_arabic(account_id: int) -> InlineKeyboardMarkup:
        """Get account settings keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="📝 اسم الحساب", callback_data=f"set_name_{account_id}"),
                InlineKeyboardButton(text="📞 الهاتف", callback_data=f"set_phone_{account_id}")
            ],
            [
                InlineKeyboardButton(text="⏰ فترة النشر", callback_data=f"set_interval_{account_id}"),
                InlineKeyboardButton(text="🎯 وضع النشر", callback_data=f"set_mode_{account_id}")
            ],
            [
                InlineKeyboardButton(text="📊 الإحصائيات", callback_data=f"stats_{account_id}"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_publishing_control_keyboard(account_id: int, is_publishing: bool = False) -> InlineKeyboardMarkup:
        """Get publishing control keyboard."""
        if is_publishing:
            buttons = [
                [
                    ButtonStyles.pause_publishing().to_dict() | {"callback_data": f"pause_publishing_{account_id}"},
                    ButtonStyles.stop_publishing().to_dict() | {"callback_data": f"stop_publishing_{account_id}"}
                ],
                [
                    ButtonStyles.back_button().to_dict()
                ]
            ]
        else:
            buttons = [
                [
                    ButtonStyles.start_publishing().to_dict() | {"callback_data": f"start_publishing_{account_id}"}
                ],
                [
                    ButtonStyles.back_button().to_dict()
                ]
            ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_publishing_control_keyboard_arabic(account_id: int, is_publishing: bool = False) -> InlineKeyboardMarkup:
        """Get publishing control keyboard in Arabic."""
        if is_publishing:
            buttons = [
                [
                    InlineKeyboardButton(text="⏸️ ايقاف مؤقت", callback_data=f"pause_publishing_{account_id}"),
                    InlineKeyboardButton(text="❌ ايقاف", callback_data=f"stop_publishing_{account_id}")
                ],
                [
                    InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")
                ]
            ]
        else:
            buttons = [
                [
                    InlineKeyboardButton(text="▶️ بدء النشر", callback_data=f"start_publishing_{account_id}")
                ],
                [
                    InlineKeyboardButton(text="⬅️ الرجوع", callback_data="back")
                ]
            ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = [
    'AccountKeyboard',
]
