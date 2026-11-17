"""
Admin keyboard for Telegram Auto Publisher Pro
Contains administrator dashboard keyboards
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .styles import ButtonStyles


class AdminKeyboard:
    """
    Administrator dashboard keyboard.
    """
    
    @staticmethod
    def get_admin_main_menu() -> InlineKeyboardMarkup:
        """Get the admin main menu."""
        buttons = [
            [
                ButtonStyles.dashboard().to_dict() | {"callback_data": "admin_dashboard"},
                ButtonStyles.user_management().to_dict() | {"callback_data": "admin_users"}
            ],
            [
                ButtonStyles.admin_management().to_dict() | {"callback_data": "admin_admins"},
                ButtonStyles.subscription_management().to_dict() | {"callback_data": "admin_subscriptions"}
            ],
            [
                ButtonStyles.broadcast_management().to_dict() | {"callback_data": "admin_broadcasts"},
                ButtonStyles.system_settings().to_dict() | {"callback_data": "admin_settings"}
            ],
            [
                ButtonStyles.activity_logs().to_dict() | {"callback_data": "admin_logs"},
                ButtonStyles.error_reports().to_dict() | {"callback_data": "admin_errors"}
            ],
            [
                ButtonStyles.database_management().to_dict() | {"callback_data": "admin_database"},
                ButtonStyles.backup_restore().to_dict() | {"callback_data": "admin_backup"}
            ],
            [
                ButtonStyles.maintenance_mode().to_dict() | {"callback_data": "admin_maintenance"},
                ButtonStyles.back_button().to_dict() | {"callback_data": "main_menu"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_admin_main_menu_arabic() -> InlineKeyboardMarkup:
        """Get the admin main menu in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="📊 لوحة التحكم", callback_data="admin_dashboard"),
                InlineKeyboardButton(text="👥 إدارة المستخدمين", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="👑 إدارة المشرفين", callback_data="admin_admins"),
                InlineKeyboardButton(text="💳 إدارة الاشتراكات", callback_data="admin_subscriptions")
            ],
            [
                InlineKeyboardButton(text="📢 إدارة البث", callback_data="admin_broadcasts"),
                InlineKeyboardButton(text="⚙️ إعدادات النظام", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton(text="📜 سجلات النشاط", callback_data="admin_logs"),
                InlineKeyboardButton(text="⚠️ تقارير الأخطاء", callback_data="admin_errors")
            ],
            [
                InlineKeyboardButton(text="🗃️ إدارة قاعدة البيانات", callback_data="admin_database"),
                InlineKeyboardButton(text="💾 النسخ الاحتياطي", callback_data="admin_backup")
            ],
            [
                InlineKeyboardButton(text="🔧 وضع الصيانة", callback_data="admin_maintenance"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_dashboard_stats_keyboard() -> InlineKeyboardMarkup:
        """Get dashboard statistics keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="👥 Users", callback_data="stats_users"),
                InlineKeyboardButton(text="👥 Active Users", callback_data="stats_active_users")
            ],
            [
                InlineKeyboardButton(text="🤖 Bots", callback_data="stats_bots"),
                InlineKeyboardButton(text="👑 Admins", callback_data="stats_admins")
            ],
            [
                InlineKeyboardButton(text="📊 Accounts", callback_data="stats_accounts"),
                InlineKeyboardButton(text="✅ Connected", callback_data="stats_connected")
            ],
            [
                InlineKeyboardButton(text="💳 Subscriptions", callback_data="stats_subscriptions"),
                InlineKeyboardButton(text="📢 Broadcasts", callback_data="stats_broadcasts")
            ],
            [
                ButtonStyles.back_button().to_dict() | {"callback_data": "admin_dashboard"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_user_management_keyboard() -> InlineKeyboardMarkup:
        """Get user management keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="👥 All Users", callback_data="admin_users_all"),
                InlineKeyboardButton(text="✅ Active Users", callback_data="admin_users_active")
            ],
            [
                InlineKeyboardButton(text="❌ Blocked Users", callback_data="admin_users_blocked"),
                InlineKeyboardButton(text="🔍 Search Users", callback_data="admin_users_search")
            ],
            [
                InlineKeyboardButton(text="➕ Add User", callback_data="admin_user_add"),
                InlineKeyboardButton(text="📊 User Stats", callback_data="admin_users_stats")
            ],
            [
                ButtonStyles.back_button().to_dict() | {"callback_data": "admin_dashboard"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_user_management_keyboard_arabic() -> InlineKeyboardMarkup:
        """Get user management keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="👥 جميع المستخدمين", callback_data="admin_users_all"),
                InlineKeyboardButton(text="✅ المستخدمين النشطين", callback_data="admin_users_active")
            ],
            [
                InlineKeyboardButton(text="❌ المستخدمين المحظورين", callback_data="admin_users_blocked"),
                InlineKeyboardButton(text="🔍 بحث عن مستخدم", callback_data="admin_users_search")
            ],
            [
                InlineKeyboardButton(text="➕ إضافة مستخدم", callback_data="admin_user_add"),
                InlineKeyboardButton(text="📊 إحصائيات المستخدمين", callback_data="admin_users_stats")
            ],
            [
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="admin_dashboard")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_user_action_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """Get keyboard with user actions."""
        buttons = [
            [
                InlineKeyboardButton(text="👁️ View Profile", callback_data=f"admin_user_view_{user_id}"),
                InlineKeyboardButton(text="⚙️ Edit", callback_data=f"admin_user_edit_{user_id}")
            ],
            [
                InlineKeyboardButton(text="✅ Activate", callback_data=f"admin_user_activate_{user_id}"),
                InlineKeyboardButton(text="❌ Deactivate", callback_data=f"admin_user_deactivate_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🔒 Block", callback_data=f"admin_user_block_{user_id}"),
                InlineKeyboardButton(text="🔓 Unblock", callback_data=f"admin_user_unblock_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🗑️ Delete", callback_data=f"admin_user_delete_confirm_{user_id}"),
                ButtonStyles.back_button().to_dict() | {"callback_data": "admin_users"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_user_action_keyboard_arabic(user_id: int) -> InlineKeyboardMarkup:
        """Get keyboard with user actions in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="👁️ عرض الملف الشخصي", callback_data=f"admin_user_view_{user_id}"),
                InlineKeyboardButton(text="⚙️ تعديل", callback_data=f"admin_user_edit_{user_id}")
            ],
            [
                InlineKeyboardButton(text="✅ تفعيل", callback_data=f"admin_user_activate_{user_id}"),
                InlineKeyboardButton(text="❌ تعطيل", callback_data=f"admin_user_deactivate_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🔒 حظر", callback_data=f"admin_user_block_{user_id}"),
                InlineKeyboardButton(text="🔓 رفع الحظر", callback_data=f"admin_user_unblock_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🗑️ حذف", callback_data=f"admin_user_delete_confirm_{user_id}"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="admin_users")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_admin_management_keyboard() -> InlineKeyboardMarkup:
        """Get admin management keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="👑 All Admins", callback_data="admin_admins_all"),
                InlineKeyboardButton(text="✅ Active Admins", callback_data="admin_admins_active")
            ],
            [
                InlineKeyboardButton(text="➕ Add Admin", callback_data="admin_admin_add"),
                InlineKeyboardButton(text="🔍 Search Admins", callback_data="admin_admins_search")
            ],
            [
                InlineKeyboardButton(text="📊 Admin Stats", callback_data="admin_admins_stats"),
                ButtonStyles.back_button().to_dict() | {"callback_data": "admin_dashboard"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_admin_management_keyboard_arabic() -> InlineKeyboardMarkup:
        """Get admin management keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="👑 جميع المشرفين", callback_data="admin_admins_all"),
                InlineKeyboardButton(text="✅ المشرفين النشطين", callback_data="admin_admins_active")
            ],
            [
                InlineKeyboardButton(text="➕ إضافة مشرف", callback_data="admin_admin_add"),
                InlineKeyboardButton(text="🔍 بحث عن مشرف", callback_data="admin_admins_search")
            ],
            [
                InlineKeyboardButton(text="📊 إحصائيات المشرفين", callback_data="admin_admins_stats"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="admin_dashboard")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_broadcast_management_keyboard() -> InlineKeyboardMarkup:
        """Get broadcast management keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="➕ Create Broadcast", callback_data="admin_broadcast_create"),
                InlineKeyboardButton(text="📜 My Broadcasts", callback_data="admin_broadcasts_my")
            ],
            [
                InlineKeyboardButton(text="📤 Send Now", callback_data="admin_broadcast_send"),
                InlineKeyboardButton(text="⏰ Schedule", callback_data="admin_broadcast_schedule")
            ],
            [
                InlineKeyboardButton(text="📊 Broadcast Stats", callback_data="admin_broadcasts_stats"),
                ButtonStyles.back_button().to_dict() | {"callback_data": "admin_dashboard"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_broadcast_management_keyboard_arabic() -> InlineKeyboardMarkup:
        """Get broadcast management keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="➕ إنشاء بث", callback_data="admin_broadcast_create"),
                InlineKeyboardButton(text="📜 بثي", callback_data="admin_broadcasts_my")
            ],
            [
                InlineKeyboardButton(text="📤 ارسال الآن", callback_data="admin_broadcast_send"),
                InlineKeyboardButton(text="⏰ جدولة", callback_data="admin_broadcast_schedule")
            ],
            [
                InlineKeyboardButton(text="📊 إحصائيات البث", callback_data="admin_broadcasts_stats"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="admin_dashboard")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_channel_subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
        """Get channel subscription keyboard."""
        buttons = []
        
        # Add join buttons for each channel
        for channel in channels:
            username = channel.get('username') or channel.get('channel_username')
            if username:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"Join @{username}",
                        url=f"https://t.me/{username}"
                    )
                ])
        
        # Add verify button
        buttons.append([
            ButtonStyles.verify_subscription().to_dict()
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_channel_subscription_keyboard_arabic(channels: list) -> InlineKeyboardMarkup:
        """Get channel subscription keyboard in Arabic."""
        buttons = []
        
        # Add join buttons for each channel
        for channel in channels:
            username = channel.get('username') or channel.get('channel_username')
            if username:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"انضم إلى @{username}",
                        url=f"https://t.me/{username}"
                    )
                ])
        
        # Add verify button
        buttons.append([
            InlineKeyboardButton(text="✅ تحقق من الاشتراك", callback_data="verify_subscription")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_required_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
        """Get required channels management keyboard."""
        buttons = [
            [
                InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_channel_add"),
                InlineKeyboardButton(text="🗑️ Remove Channel", callback_data="admin_channel_remove")
            ],
            [
                InlineKeyboardButton(text="📋 List Channels", callback_data="admin_channels_list"),
                ButtonStyles.back_button().to_dict() | {"callback_data": "admin_settings"}
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_required_channels_keyboard_arabic() -> InlineKeyboardMarkup:
        """Get required channels management keyboard in Arabic."""
        buttons = [
            [
                InlineKeyboardButton(text="➕ إضافة قناة", callback_data="admin_channel_add"),
                InlineKeyboardButton(text="🗑️ إزالة قناة", callback_data="admin_channel_remove")
            ],
            [
                InlineKeyboardButton(text="📋 قائمة القنوات", callback_data="admin_channels_list"),
                InlineKeyboardButton(text="⬅️ الرجوع", callback_data="admin_settings")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = [
    'AdminKeyboard',
]
