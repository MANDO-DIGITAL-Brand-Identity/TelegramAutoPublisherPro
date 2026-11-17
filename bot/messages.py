"""
Message templates for Telegram Auto Publisher Pro
Contains all message texts in Arabic and English
"""

from typing import Dict, Optional
from enum import Enum


class Language(Enum):
    """Supported languages"""
    ARABIC = "ar"
    ENGLISH = "en"


class Messages:
    """
    Message templates for the bot.
    Supports both Arabic and English.
    """
    
    def __init__(self, language: Language = Language.ENGLISH):
        """
        Initialize the message templates.
        
        Args:
            language: The language to use (Arabic or English).
        """
        self.language = language
    
    # ===========================================
    # START AND WELCOME MESSAGES
    # ===========================================
    
    def get_welcome_message(self, bot_name: str = "Telegram Auto Publisher Pro") -> str:
        """Get the welcome message."""
        if self.language == Language.ARABIC:
            return (
                f"🌟 أهلاً وسهلاً بك في {bot_name}! 🌟\n\n"
                "نظام نشر تلقائي متكامل لادارة حسابات تيليجرام.\n\n"
                "✅ ادارة حسابات متعددة\n"
                "✅ نشر محتوى تلقائي\n"
                "✅ جدولة المنشورات\n"
                "✅ ادارة المجموعات والقنوات\n"
                "✅ لوحة تحكم ادارية كاملة\n\n"
                "اضغط على /start للبدء"
            )
        else:
            return (
                f"🌟 Welcome to {bot_name}! 🌟\n\n"
                "A comprehensive auto-publishing system for managing Telegram accounts.\n\n"
                "✅ Multi-account management\n"
                "✅ Automatic content publishing\n"
                "✅ Scheduled publishing\n"
                "✅ Group and channel management\n"
                "✅ Complete admin dashboard\n\n"
                "Press /start to begin"
            )
    
    def get_start_message(self, user_name: str = "User") -> str:
        """Get the start message."""
        if self.language == Language.ARABIC:
            return (
                f"👋 مرحبا {user_name}!\n\n"
                "مرحبا بك في نظام النشر التلقائي.\n\n"
                "يرجى الاشتراك في القنوات المطلوبة للمتابعة.\n\n"
                "اضغط على الزر أدناه للمتابعة."
            )
        else:
            return (
                f"👋 Hello {user_name}!\n\n"
                "Welcome to the Auto Publisher system.\n\n"
                "Please subscribe to the required channels to continue.\n\n"
                "Press the button below to continue."
            )
    
    def get_main_menu_message(self) -> str:
        """Get the main menu message."""
        if self.language == Language.ARABIC:
            return (
                "📱 **القائمة الرئيسية** 📱\n\n"
                "اختر أحد الخيارات:"
            )
        else:
            return (
                "📱 **Main Menu** 📱\n\n"
                "Please select an option:"
            )
    
    # ===========================================
    # ACCOUNT MESSAGES
    # ===========================================
    
    def get_account_menu_message(self) -> str:
        """Get the account menu message."""
        if self.language == Language.ARABIC:
            return (
                "👥 **إدارة الحسابات** 👥\n\n"
                "ادارة حسابات تيليجرام الخاصة بك."
            )
        else:
            return (
                "👥 **Account Management** 👥\n\n"
                "Manage your Telegram accounts."
            )
    
    def get_add_account_message(self) -> str:
        """Get the add account message."""
        if self.language == Language.ARABIC:
            return (
                "➕ **إضافة حساب جديد** ➕\n\n"
                "يرجى ادخال رقم الهاتف للحساب الذي تريد اضافته.\n"
                "مثال: +966123456789"
            )
        else:
            return (
                "➕ **Add New Account** ➕\n\n"
                "Please enter the phone number for the account you want to add.\n"
                "Example: +1234567890"
            )
    
    def get_phone_number_invalid_message(self) -> str:
        """Get phone number invalid message."""
        if self.language == Language.ARABIC:
            return "❌ رقم الهاتف غير صالح. يرجى المحاولة مرة أخرى."
        else:
            return "❌ Invalid phone number. Please try again."
    
    def get_verification_code_message(self, phone_number: str) -> str:
        """Get verification code message."""
        if self.language == Language.ARABIC:
            return (
                f"📱 **رمز التحقق** 📱\n\n"
                f"تم ارسال رمز التحقق الى الرقم: {phone_number}\n\n"
                "يرجى ادخال الرمز المكون من 5 ارقام."
            )
        else:
            return (
                f"📱 **Verification Code** 📱\n\n"
                f"Verification code has been sent to: {phone_number}\n\n"
                "Please enter the 5-digit code."
            )
    
    def get_2fa_password_message(self) -> str:
        """Get 2FA password message."""
        if self.language == Language.ARABIC:
            return (
                "🔒 **التحقق بخطوتين** 🔒\n\n"
                "حسابك يتطلب التحقق بخطوتين.\n"
                "يرجى ادخال كلمة المرور."
            )
        else:
            return (
                "🔒 **Two-Factor Authentication** 🔒\n\n"
                "Your account requires two-factor authentication.\n"
                "Please enter your password."
            )
    
    def get_account_added_message(self, phone_number: str, account_id: int) -> str:
        """Get account added message."""
        if self.language == Language.ARABIC:
            return (
                f"✅ **تم اضافة الحساب** ✅\n\n"
                f"رقم الهاتف: {phone_number}\n"
                f"معرف الحساب: {account_id}\n\n"
                "يمكنك الآن استخدام هذا الحساب للنشر."
            )
        else:
            return (
                f"✅ **Account Added** ✅\n\n"
                f"Phone number: {phone_number}\n"
                f"Account ID: {account_id}\n\n"
                "You can now use this account for publishing."
            )
    
    def get_account_removed_message(self, account_id: int) -> str:
        """Get account removed message."""
        if self.language == Language.ARABIC:
            return (
                f"✅ **تم حذف الحساب** ✅\n\n"
                f"معرف الحساب: {account_id}\n\n"
                "تم حذف الحساب وجميع بياناته."
            )
        else:
            return (
                f"✅ **Account Removed** ✅\n\n"
                f"Account ID: {account_id}\n\n"
                "The account and all its data have been removed."
            )
    
    def get_account_list_message(self, accounts: list) -> str:
        """Get account list message."""
        if not accounts:
            if self.language == Language.ARABIC:
                return "❌ لا يوجد حسابات مضافة."
            else:
                return "❌ No accounts added yet."
        
        if self.language == Language.ARABIC:
            message = "📋 **قائمة الحسابات** 📋\n\n"
            for i, account in enumerate(accounts, 1):
                status = "✅ متصل" if account.is_connected else "❌ غير متصل"
                message += f"{i}. {account.phone_number} - {account.account_name or 'غير معروف'}\n"
                message += f"   الحالة: {status}\n"
                message += f"   المعرف: {account.id}\n\n"
            return message
        else:
            message = "📋 **Account List** 📋\n\n"
            for i, account in enumerate(accounts, 1):
                status = "✅ Connected" if account.is_connected else "❌ Disconnected"
                message += f"{i}. {account.phone_number} - {account.account_name or 'Unknown'}\n"
                message += f"   Status: {status}\n"
                message += f"   ID: {account.id}\n\n"
            return message
    
    def get_account_info_message(self, account_info: dict) -> str:
        """Get account information message."""
        if self.language == Language.ARABIC:
            status = "✅ متصل" if account_info.get("is_connected") else "❌ غير متصل"
            publishing = "✅ نشط" if account_info.get("is_publishing") else "❌ غير نشط"
            
            return (
                f"📊 **معلومات الحساب** 📊\n\n"
                f"الرقم: {account_info.get('phone_number', 'غير متوفر')}\n"
                f"الاسم: {account_info.get('account_name', 'غير متوفر')}\n"
                f"حالة الاتصال: {status}\n"
                f"حالة النشر: {publishing}\n"
                f"فترة النشر: {account_info.get('publishing_interval', 60)} دقيقة\n"
                f"المنشورات الناجحة: {account_info.get('successful_published', 0)}\n"
                f"المنشورات الفاشلة: {account_info.get('failed_published', 0)}\n"
            )
        else:
            status = "✅ Connected" if account_info.get("is_connected") else "❌ Disconnected"
            publishing = "✅ Active" if account_info.get("is_publishing") else "❌ Inactive"
            
            return (
                f"📊 **Account Information** 📊\n\n"
                f"Phone: {account_info.get('phone_number', 'N/A')}\n"
                f"Name: {account_info.get('account_name', 'N/A')}\n"
                f"Connection: {status}\n"
                f"Publishing: {publishing}\n"
                f"Interval: {account_info.get('publishing_interval', 60)} minutes\n"
                f"Successful: {account_info.get('successful_published', 0)}\n"
                f"Failed: {account_info.get('failed_published', 0)}\n"
            )
    
    # ===========================================
    # CHANNEL SUBSCRIPTION MESSAGES
    # ===========================================
    
    def get_channel_subscription_required_message(self, channels: list) -> str:
        """Get channel subscription required message."""
        if self.language == Language.ARABIC:
            message = "📢 **الاشتراك في القنوات المطلوبة** 📢\n\n"
            message += "يجب الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
            for i, channel in enumerate(channels, 1):
                message += f"{i}. @{channel.get('username', channel.get('channel_username', 'Unknown'))}\n"
            message += "\nاضغط على زر التحقق بعد الاشتراك."
            return message
        else:
            message = "📢 **Required Channel Subscription** 📢\n\n"
            message += "You must subscribe to the following channels to use the bot:\n\n"
            for i, channel in enumerate(channels, 1):
                message += f"{i}. @{channel.get('username', channel.get('channel_username', 'Unknown'))}\n"
            message += "\nPress the verify button after subscribing."
            return message
    
    def get_channel_subscription_verified_message(self) -> str:
        """Get channel subscription verified message."""
        if self.language == Language.ARABIC:
            return (
                "✅ **تم التحقق من الاشتراك** ✅\n\n"
                "شكراً لك على الاشتراك في القنوات المطلوبة.\n"
                "يمكنك الآن استخدام جميع ميزات البوت."
            )
        else:
            return (
                "✅ **Subscription Verified** ✅\n\n"
                "Thank you for subscribing to the required channels.\n"
                "You can now use all bot features."
            )
    
    def get_channel_subscription_failed_message(self, failed_channels: list) -> str:
        """Get channel subscription failed message."""
        if self.language == Language.ARABIC:
            message = "❌ **فشل التحقق من الاشتراك** ❌\n\n"
            message += "لم يتم الاشتراك في القنوات التالية:\n\n"
            for channel in failed_channels:
                message += f"- @{channel.get('username', 'Unknown')}\n"
            message += "\nيرجى الاشتراك في هذه القنوات ثم المحاولة مرة أخرى."
            return message
        else:
            message = "❌ **Subscription Verification Failed** ❌\n\n"
            message += "You have not subscribed to the following channels:\n\n"
            for channel in failed_channels:
                message += f"- @{channel.get('username', 'Unknown')}\n"
            message += "\nPlease subscribe to these channels and try again."
            return message
    
    # ===========================================
    # CONTENT MESSAGES
    # ===========================================
    
    def get_content_menu_message(self) -> str:
        """Get content menu message."""
        if self.language == Language.ARABIC:
            return (
                "📝 **إدارة المحتوى** 📝\n\n"
                "ادارة المنشورات والمحتوى للنشر."
            )
        else:
            return (
                "📝 **Content Management** 📝\n\n"
                "Manage posts and content for publishing."
            )
    
    def get_add_content_message(self) -> str:
        """Get add content message."""
        if self.language == Language.ARABIC:
            return (
                "➕ **إضافة محتوى جديد** ➕\n\n"
                "يرجى ارسال النص او المرفق الذي تريد حفظه."
            )
        else:
            return (
                "➕ **Add New Content** ➕\n\n"
                "Please send the text or media you want to save."
            )
    
    def get_content_added_message(self, content_id: int) -> str:
        """Get content added message."""
        if self.language == Language.ARABIC:
            return f"✅ **تم حفظ المحتوى** ✅\n\nمعرف المحتوى: {content_id}"
        else:
            return f"✅ **Content Saved** ✅\n\nContent ID: {content_id}"
    
    def get_content_list_message(self, contents: list) -> str:
        """Get content list message."""
        if not contents:
            if self.language == Language.ARABIC:
                return "❌ لا يوجد محتوى محفوظ."
            else:
                return "❌ No content saved yet."
        
        if self.language == Language.ARABIC:
            message = "📋 **قائمة المحتوى** 📋\n\n"
            for i, content in enumerate(contents, 1):
                content_type = self._get_content_type_ar(content.get('content_type', 'text'))
                message += f"{i}. {content.get('title', 'بدون عنوان')} - {content_type}\n"
                message += f"   المعرف: {content.get('id')}\n\n"
            return message
        else:
            message = "📋 **Content List** 📋\n\n"
            for i, content in enumerate(contents, 1):
                content_type = content.get('content_type', 'text').upper()
                message += f"{i}. {content.get('title', 'Untitled')} - {content_type}\n"
                message += f"   ID: {content.get('id')}\n\n"
            return message
    
    def _get_content_type_ar(self, content_type: str) -> str:
        """Get Arabic content type name."""
        types = {
            'text': 'نص',
            'image': 'صورة',
            'video': 'فيديو',
            'document': 'مستند',
            'audio': 'صوت'
        }
        return types.get(content_type, content_type)
    
    # ===========================================
    # GROUP MESSAGES
    # ===========================================
    
    def get_group_menu_message(self) -> str:
        """Get group menu message."""
        if self.language == Language.ARABIC:
            return (
                "👥 **إدارة المجموعات** 👥\n\n"
                "ادارة المجموعات والقنوات للنشر."
            )
        else:
            return (
                "👥 **Group Management** 👥\n\n"
                "Manage groups and channels for publishing."
            )
    
    def get_group_list_message(self, groups: list) -> str:
        """Get group list message."""
        if not groups:
            if self.language == Language.ARABIC:
                return "❌ لا يوجد مجموعات."
            else:
                return "❌ No groups available."
        
        if self.language == Language.ARABIC:
            message = "📋 **قائمة المجموعات** 📋\n\n"
            for i, group in enumerate(groups, 1):
                group_type = "قناة" if group.get('is_broadcast') else "مجموعة"
                message += f"{i}. {group.get('title', 'بدون اسم')} ({group_type})\n"
                message += f"   المعرف: {group.get('id')}\n\n"
            return message
        else:
            message = "📋 **Group List** 📋\n\n"
            for i, group in enumerate(groups, 1):
                group_type = "Channel" if group.get('is_broadcast') else "Group"
                message += f"{i}. {group.get('title', 'Untitled')} ({group_type})\n"
                message += f"   ID: {group.get('id')}\n\n"
            return message
    
    # ===========================================
    # PUBLISHING MESSAGES
    # ===========================================
    
    def get_publishing_menu_message(self) -> str:
        """Get publishing menu message."""
        if self.language == Language.ARABIC:
            return (
                "📢 **إدارة النشر** 📢\n\n"
                "ضبط اعدادات النشر وتخطيط المنشورات."
            )
        else:
            return (
                "📢 **Publishing Management** 📢\n\n"
                "Configure publishing settings and schedule posts."
            )
    
    def get_publishing_started_message(self, account_id: int) -> str:
        """Get publishing started message."""
        if self.language == Language.ARABIC:
            return (
                f"✅ **تم بدء النشر** ✅\n\n"
                f"معرف الحساب: {account_id}\n\n"
                "سيتم نشر المحتوى وفقاً للجدول الزمني."
            )
        else:
            return (
                f"✅ **Publishing Started** ✅\n\n"
                f"Account ID: {account_id}\n\n"
                "Content will be published according to the schedule."
            )
    
    def get_publishing_stopped_message(self, account_id: int) -> str:
        """Get publishing stopped message."""
        if self.language == Language.ARABIC:
            return (
                f"✅ **تم ايقاف النشر** ✅\n\n"
                f"معرف الحساب: {account_id}\n\n"
                "تم ايقاف نشر المحتوى."
            )
        else:
            return (
                f"✅ **Publishing Stopped** ✅\n\n"
                f"Account ID: {account_id}\n\n"
                "Content publishing has been stopped."
            )
    
    def get_publishing_report_message(self, stats: dict) -> str:
        """Get publishing report message."""
        if self.language == Language.ARABIC:
            success_rate = stats.get('success_rate', 0)
            total = stats.get('total_published', 0)
            successful = stats.get('successful_published', 0)
            failed = stats.get('failed_published', 0)
            
            # Create progress bar
            progress = int(success_rate / 10) if success_rate > 0 else 0
            bar = "█" * progress + "░" * (10 - progress)
            
            return (
                f"📊 **تقرير النشر** 📊\n\n"
                f"إجمالي المنشورات: {total}\n"
                f"الناجحة: {successful}\n"
                f"الفاشلة: {failed}\n"
                f"نسبة النجاح: {success_rate:.1f}%\n\n"
                f"شريط التقدم: [{bar}] {success_rate:.1f}%\n"
            )
        else:
            success_rate = stats.get('success_rate', 0)
            total = stats.get('total_published', 0)
            successful = stats.get('successful_published', 0)
            failed = stats.get('failed_published', 0)
            
            # Create progress bar
            progress = int(success_rate / 10) if success_rate > 0 else 0
            bar = "█" * progress + "░" * (10 - progress)
            
            return (
                f"📊 **Publishing Report** 📊\n\n"
                f"Total: {total}\n"
                f"Successful: {successful}\n"
                f"Failed: {failed}\n"
                f"Success Rate: {success_rate:.1f}%\n\n"
                f"Progress: [{bar}] {success_rate:.1f}%\n"
            )
    
    # ===========================================
    # SUBSCRIPTION MESSAGES
    # ===========================================
    
    def get_subscription_menu_message(self) -> str:
        """Get subscription menu message."""
        if self.language == Language.ARABIC:
            return (
                "💳 **إدارة الاشتراك** 💳\n\n"
                "ادارة اشتراكك والحصول على ميزات إضافية."
            )
        else:
            return (
                "💳 **Subscription Management** 💳\n\n"
                "Manage your subscription and get premium features."
            )
    
    def get_subscription_info_message(self, subscription: dict) -> str:
        """Get subscription info message."""
        if self.language == Language.ARABIC:
            subscription_type = subscription.get('subscription_type', 'free')
            type_name = self._get_subscription_type_ar(subscription_type)
            status = subscription.get('status', 'active')
            status_name = "نشط" if status == "active" else "منتهي"
            
            return (
                f"💳 **معلومات الاشتراك** 💳\n\n"
                f"النوع: {type_name}\n"
                f"الحالة: {status_name}\n"
                f"بداية الاشتراك: {subscription.get('start_date', 'N/A')}\n"
                f"نهاية الاشتراك: {subscription.get('end_date', 'N/A')}\n"
            )
        else:
            subscription_type = subscription.get('subscription_type', 'free')
            status = subscription.get('status', 'active')
            
            return (
                f"💳 **Subscription Information** 💳\n\n"
                f"Type: {subscription_type.upper()}\n"
                f"Status: {status.upper()}\n"
                f"Start Date: {subscription.get('start_date', 'N/A')}\n"
                f"End Date: {subscription.get('end_date', 'N/A')}\n"
            )
    
    def _get_subscription_type_ar(self, subscription_type: str) -> str:
        """Get Arabic subscription type name."""
        types = {
            'free': 'مجاني',
            'premium': 'مميز',
            'monthly': 'شهري',
            'yearly': 'سنوي',
            'lifetime': 'مدى الحياة',
            'trial': 'تجريبي'
        }
        return types.get(subscription_type, subscription_type)
    
    # ===========================================
    # ADMIN MESSAGES
    # ===========================================
    
    def get_admin_menu_message(self) -> str:
        """Get admin menu message."""
        if self.language == Language.ARABIC:
            return (
                "👑 **لوحة تحكم المشرف** 👑\n\n"
                "ادارة النظام والمستخدمين."
            )
        else:
            return (
                "👑 **Admin Dashboard** 👑\n\n"
                "Manage the system and users."
            )
    
    def get_admin_dashboard_message(self, stats: dict) -> str:
        """Get admin dashboard message."""
        if self.language == Language.ARABIC:
            return (
                f"📊 **إحصائيات النظام** 📊\n\n"
                f"عدد المستخدمين: {stats.get('total_users', 0)}\n"
                f"المستخدمين النشطين: {stats.get('active_users', 0)}\n"
                f"الحسابات المتصلة: {stats.get('connected_accounts', 0)}\n"
                f"المشتركين المميزين: {stats.get('premium_subscribers', 0)}\n"
                f"إجمالي المنشورات: {stats.get('total_published', 0)}\n"
            )
        else:
            return (
                f"📊 **System Statistics** 📊\n\n"
                f"Total Users: {stats.get('total_users', 0)}\n"
                f"Active Users: {stats.get('active_users', 0)}\n"
                f"Connected Accounts: {stats.get('connected_accounts', 0)}\n"
                f"Premium Subscribers: {stats.get('premium_subscribers', 0)}\n"
                f"Total Published: {stats.get('total_published', 0)}\n"
            )
    
    # ===========================================
    # ERROR MESSAGES
    # ===========================================
    
    def get_error_message(self, error: str) -> str:
        """Get error message."""
        if self.language == Language.ARABIC:
            return f"❌ **خطأ** ❌\n\n{error}"
        else:
            return f"❌ **Error** ❌\n\n{error}"
    
    def get_permission_denied_message(self) -> str:
        """Get permission denied message."""
        if self.language == Language.ARABIC:
            return "❌ **غير مصرح** ❌\n\nليس لديك صلاحية للقيام بهذا الإجراء."
        else:
            return "❌ **Permission Denied** ❌\n\nYou do not have permission to perform this action."
    
    def get_not_found_message(self, item: str = "Item") -> str:
        """Get not found message."""
        if self.language == Language.ARABIC:
            return f"❌ **غير موجود** ❌\n\n{item} غير موجود."
        else:
            return f"❌ **Not Found** ❌\n\n{item} not found."
    
    # ===========================================
    # OTHER MESSAGES
    # ===========================================
    
    def get_help_message(self) -> str:
        """Get help message."""
        if self.language == Language.ARABIC:
            return (
                "❓ **المساعدة** ❓\n\n"
                "للحصول على مساعدة، يمكنك:\n"
                "- الاتصال بدعم البوت\n"
                "- قراءة الوثائق\n"
                "- الانضمام إلى مجموعة الدعم\n\n"
                "لمزيد من المعلومات، اضغط على زر المساعدة."
            )
        else:
            return (
                "❓ **Help** ❓\n\n"
                "For help, you can:\n"
                "- Contact bot support\n"
                "- Read the documentation\n"
                "- Join the support group\n\n"
                "For more information, press the Help button."
            )
    
    def get_settings_message(self) -> str:
        """Get settings message."""
        if self.language == Language.ARABIC:
            return (
                "⚙️ **الإعدادات** ⚙️\n\n"
                "ضبط اعدادات البوت."
            )
        else:
            return (
                "⚙️ **Settings** ⚙️\n\n"
                "Configure bot settings."
            )
    
    def get_back_message(self) -> str:
        """Get back message."""
        if self.language == Language.ARABIC:
            return "⬅️ **الرجوع**"
        else:
            return "⬅️ **Back**"
    
    def get_cancel_message(self) -> str:
        """Get cancel message."""
        if self.language == Language.ARABIC:
            return "❌ **إلغاء**"
        else:
            return "❌ **Cancel**"
    
    def get_confirm_message(self, action: str) -> str:
        """Get confirmation message."""
        if self.language == Language.ARABIC:
            return f"⚠️ **تأكيد {action}** ⚠️\n\nهل أنت متأكد من أنك تريد {action}?"
        else:
            return f"⚠️ **Confirm {action}** ⚠️\n\nAre you sure you want to {action}?"


# Create default message instances
messages_ar = Messages(Language.ARABIC)
messages_en = Messages(Language.ENGLISH)


__all__ = [
    'Language',
    'Messages',
    'messages_ar',
    'messages_en',
]
