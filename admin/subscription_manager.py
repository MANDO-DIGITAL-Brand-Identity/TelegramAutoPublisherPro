"""
Subscription manager for Telegram Auto Publisher Pro
Manages user subscriptions and premium features
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Tuple

from config import config
from database.models import (
    User,
    Subscription,
    SubscriptionType,
    SubscriptionStatus,
)
from database.repositories import (
    UserRepository,
    SubscriptionRepository,
    AuditLogRepository,
)
from .audit_manager import AuditManager

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionInfo:
    """Information about a subscription"""
    
    id: int
    user_id: int
    subscription_type: SubscriptionType
    status: SubscriptionStatus
    
    # Duration
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    
    # Features
    max_accounts: int = 2
    max_groups: int = 5
    min_publish_interval: int = 60
    
    # Payment
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    
    # Auto-renewal
    auto_renew: bool = False
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
    activated_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None


class SubscriptionManager:
    """
    Manages user subscriptions and premium features.
    Provides functionality for subscription management.
    """
    
    def __init__(
        self,
        user_manager: Any = None,
        session_factory: Callable = None,
        audit_manager: AuditManager = None,
        config: any = None
    ):
        """
        Initialize the subscription manager.
        
        Args:
            user_manager: User manager instance.
            session_factory: Database session factory.
            audit_manager: Audit manager instance.
            config: Application configuration.
        """
        self.user_manager = user_manager
        self.session_factory = session_factory
        self.audit_manager = audit_manager
        self.config = config or config
    
    async def get_subscription(self, user_id: int) -> Optional[SubscriptionInfo]:
        """
        Get subscription information for a user.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            SubscriptionInfo object, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                subscription = await subscription_repo.get_subscription_by_user(user_id)
                
                if not subscription:
                    return None
                
                return SubscriptionInfo(
                    id=subscription.id,
                    user_id=subscription.user_id,
                    subscription_type=SubscriptionType(subscription.subscription_type) if subscription.subscription_type else SubscriptionType.FREE,
                    status=SubscriptionStatus(subscription.status) if subscription.status else SubscriptionStatus.ACTIVE,
                    start_date=subscription.start_date,
                    end_date=subscription.end_date,
                    duration_days=subscription.duration_days,
                    max_accounts=subscription.max_accounts,
                    max_groups=subscription.max_groups,
                    min_publish_interval=subscription.min_publish_interval,
                    payment_method=subscription.payment_method,
                    transaction_id=subscription.transaction_id,
                    amount=subscription.amount,
                    currency=subscription.currency,
                    auto_renew=subscription.auto_renew,
                    created_at=subscription.created_at,
                    updated_at=subscription.updated_at,
                    activated_at=subscription.activated_at,
                    expired_at=subscription.expired_at
                )
                
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {e}")
            return None
    
    async def get_active_subscriptions(self) -> List[SubscriptionInfo]:
        """
        Get all active subscriptions.
        
        Returns:
            List of SubscriptionInfo objects for active subscriptions.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                subscriptions = await subscription_repo.get_active_subscriptions()
                
                subscription_infos = []
                for subscription in subscriptions:
                    subscription_info = await self._subscription_to_subscription_info(subscription)
                    if subscription_info:
                        subscription_infos.append(subscription_info)
                
                return subscription_infos
                
        except Exception as e:
            logger.error(f"Error getting active subscriptions: {e}")
            return []
    
    async def get_expired_subscriptions(self) -> List[SubscriptionInfo]:
        """
        Get all expired subscriptions.
        
        Returns:
            List of SubscriptionInfo objects for expired subscriptions.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                subscriptions = await subscription_repo.get_expired_subscriptions()
                
                subscription_infos = []
                for subscription in subscriptions:
                    subscription_info = await self._subscription_to_subscription_info(subscription)
                    if subscription_info:
                        subscription_infos.append(subscription_info)
                
                return subscription_infos
                
        except Exception as e:
            logger.error(f"Error getting expired subscriptions: {e}")
            return []
    
    async def _subscription_to_subscription_info(self, subscription: Subscription) -> Optional[SubscriptionInfo]:
        """
        Convert a Subscription to SubscriptionInfo.
        
        Args:
            subscription: The Subscription object.
            
        Returns:
            SubscriptionInfo object.
        """
        if not subscription:
            return None
        
        return SubscriptionInfo(
            id=subscription.id,
            user_id=subscription.user_id,
            subscription_type=SubscriptionType(subscription.subscription_type) if subscription.subscription_type else SubscriptionType.FREE,
            status=SubscriptionStatus(subscription.status) if subscription.status else SubscriptionStatus.ACTIVE,
            start_date=subscription.start_date,
            end_date=subscription.end_date,
            duration_days=subscription.duration_days,
            max_accounts=subscription.max_accounts,
            max_groups=subscription.max_groups,
            min_publish_interval=subscription.min_publish_interval,
            payment_method=subscription.payment_method,
            transaction_id=subscription.transaction_id,
            amount=subscription.amount,
            currency=subscription.currency,
            auto_renew=subscription.auto_renew,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            activated_at=subscription.activated_at,
            expired_at=subscription.expired_at
        )
    
    async def create_subscription(
        self,
        user_id: int,
        subscription_type: SubscriptionType = SubscriptionType.FREE,
        duration_days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_accounts: Optional[int] = None,
        max_groups: Optional[int] = None,
        min_publish_interval: Optional[int] = None,
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        auto_renew: bool = False,
        admin_id: int = None
    ) -> Tuple[bool, Optional[SubscriptionInfo], str]:
        """
        Create a new subscription.
        
        Args:
            user_id: The Telegram user ID.
            subscription_type: The subscription type.
            duration_days: Duration in days.
            start_date: Start date.
            end_date: End date.
            max_accounts: Maximum number of accounts.
            max_groups: Maximum number of groups.
            min_publish_interval: Minimum publish interval in minutes.
            payment_method: Payment method.
            transaction_id: Transaction ID.
            amount: Amount paid.
            currency: Currency.
            auto_renew: Whether to auto-renew.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, subscription_info, error_message).
        """
        try:
            async with self.session_factory() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_user(user_id)
                
                if not user:
                    return False, None, "User not found"
                
                # Check if user already has a subscription
                subscription_repo = SubscriptionRepository(session)
                existing_subscription = await subscription_repo.get_subscription_by_user(user_id)
                
                if existing_subscription:
                    # Update existing subscription
                    return await self.update_subscription(
                        user_id,
                        subscription_type=subscription_type,
                        duration_days=duration_days,
                        start_date=start_date,
                        end_date=end_date,
                        max_accounts=max_accounts,
                        max_groups=max_groups,
                        min_publish_interval=min_publish_interval,
                        payment_method=payment_method,
                        transaction_id=transaction_id,
                        amount=amount,
                        currency=currency,
                        auto_renew=auto_renew,
                        admin_id=admin_id
                    )
                
                # Set default values based on subscription type
                if max_accounts is None:
                    if subscription_type == SubscriptionType.FREE:
                        max_accounts = self.config.subscription.FREE_MAX_ACCOUNTS
                    else:
                        max_accounts = self.config.subscription.PREMIUM_MAX_ACCOUNTS
                
                if max_groups is None:
                    if subscription_type == SubscriptionType.FREE:
                        max_groups = self.config.subscription.FREE_MAX_GROUPS
                    else:
                        max_groups = self.config.subscription.PREMIUM_MAX_GROUPS
                
                if min_publish_interval is None:
                    if subscription_type == SubscriptionType.FREE:
                        min_publish_interval = self.config.subscription.FREE_PUBLISH_INTERVAL_MINUTES
                    else:
                        min_publish_interval = self.config.subscription.PREMIUM_PUBLISH_INTERVAL_MINUTES
                
                # Set dates
                now = datetime.utcnow()
                if start_date is None:
                    start_date = now
                
                if end_date is None:
                    if duration_days is not None:
                        end_date = start_date + timedelta(days=duration_days)
                    elif subscription_type == SubscriptionType.TRIAL:
                        end_date = start_date + timedelta(days=self.config.subscription.TRIAL_DAYS)
                    elif subscription_type == SubscriptionType.MONTHLY:
                        end_date = start_date + timedelta(days=self.config.subscription.PREMIUM_MONTHLY_DAYS)
                    elif subscription_type == SubscriptionType.YEARLY:
                        end_date = start_date + timedelta(days=self.config.subscription.PREMIUM_YEARLY_DAYS)
                    elif subscription_type == SubscriptionType.LIFETIME:
                        end_date = None  # No expiration
                    else:
                        end_date = start_date + timedelta(days=365)  # Default to 1 year
                
                # Create subscription
                subscription_data = {
                    "user_id": user_id,
                    "subscription_type": subscription_type.value,
                    "status": SubscriptionStatus.ACTIVE.value,
                    "start_date": start_date,
                    "end_date": end_date,
                    "duration_days": duration_days,
                    "max_accounts": max_accounts,
                    "max_groups": max_groups,
                    "min_publish_interval": min_publish_interval,
                    "payment_method": payment_method,
                    "transaction_id": transaction_id,
                    "amount": amount,
                    "currency": currency,
                    "auto_renew": auto_renew,
                    "created_at": now,
                    "updated_at": now,
                    "activated_at": now
                }
                
                subscription = await subscription_repo.create(subscription_data)
                
                # Update user premium status
                is_premium = subscription_type != SubscriptionType.FREE
                await user_repo.update(user_id, {"is_premium": is_premium})
                
                # Log the action
                if self.audit_manager and admin_id:
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="create_subscription",
                        action_type="subscription",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username or f"User {user_id}",
                        details={
                            "subscription_type": subscription_type.value,
                            "duration_days": duration_days,
                            "start_date": start_date.isoformat() if start_date else None,
                            "end_date": end_date.isoformat() if end_date else None
                        }
                    )
                
                logger.info(f"Created subscription {subscription.id} for user {user_id}")
                
                subscription_info = await self._subscription_to_subscription_info(subscription)
                return True, subscription_info, ""
                
        except Exception as e:
            logger.error(f"Error creating subscription for user {user_id}: {e}")
            return False, None, str(e)
    
    async def update_subscription(
        self,
        user_id: int,
        subscription_type: Optional[SubscriptionType] = None,
        duration_days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_accounts: Optional[int] = None,
        max_groups: Optional[int] = None,
        min_publish_interval: Optional[int] = None,
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        auto_renew: Optional[bool] = None,
        status: Optional[SubscriptionStatus] = None,
        admin_id: int = None
    ) -> Tuple[bool, Optional[SubscriptionInfo], str]:
        """
        Update a subscription.
        
        Args:
            user_id: The Telegram user ID.
            subscription_type: The subscription type.
            duration_days: Duration in days.
            start_date: Start date.
            end_date: End date.
            max_accounts: Maximum number of accounts.
            max_groups: Maximum number of groups.
            min_publish_interval: Minimum publish interval in minutes.
            payment_method: Payment method.
            transaction_id: Transaction ID.
            amount: Amount paid.
            currency: Currency.
            auto_renew: Whether to auto-renew.
            status: Subscription status.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, subscription_info, error_message).
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                subscription = await subscription_repo.get_subscription_by_user(user_id)
                
                if not subscription:
                    return False, None, "Subscription not found"
                
                # Store old values for logging
                old_values = {
                    "subscription_type": subscription.subscription_type,
                    "status": subscription.status,
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                    "max_accounts": subscription.max_accounts,
                    "max_groups": subscription.max_groups,
                    "min_publish_interval": subscription.min_publish_interval
                }
                
                # Prepare updates
                updates = {}
                
                if subscription_type is not None:
                    updates["subscription_type"] = subscription_type.value
                if duration_days is not None:
                    updates["duration_days"] = duration_days
                if start_date is not None:
                    updates["start_date"] = start_date
                if end_date is not None:
                    updates["end_date"] = end_date
                if max_accounts is not None:
                    updates["max_accounts"] = max_accounts
                if max_groups is not None:
                    updates["max_groups"] = max_groups
                if min_publish_interval is not None:
                    updates["min_publish_interval"] = min_publish_interval
                if payment_method is not None:
                    updates["payment_method"] = payment_method
                if transaction_id is not None:
                    updates["transaction_id"] = transaction_id
                if amount is not None:
                    updates["amount"] = amount
                if currency is not None:
                    updates["currency"] = currency
                if auto_renew is not None:
                    updates["auto_renew"] = auto_renew
                if status is not None:
                    updates["status"] = status.value
                
                updates["updated_at"] = datetime.utcnow()
                
                # Update subscription
                await subscription_repo.update(subscription.user_id, updates)
                
                # Update user premium status
                if subscription_type is not None:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_user(user_id)
                    if user:
                        is_premium = subscription_type != SubscriptionType.FREE
                        await user_repo.update(user_id, {"is_premium": is_premium})
                
                # Log the action
                if self.audit_manager and admin_id:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_user(user_id)
                    
                    new_values = {}
                    for key, value in updates.items():
                        if key != "updated_at":
                            new_values[key] = value
                    
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="update_subscription",
                        action_type="subscription",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username if user else f"User {user_id}",
                        old_values=old_values,
                        new_values=new_values
                    )
                
                logger.info(f"Updated subscription for user {user_id}")
                
                # Get updated subscription
                updated_subscription = await subscription_repo.get_subscription_by_user(user_id)
                subscription_info = await self._subscription_to_subscription_info(updated_subscription)
                return True, subscription_info, ""
                
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            return False, None, str(e)
    
    async def activate_subscription(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Activate a subscription.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self.update_subscription(
            user_id,
            status=SubscriptionStatus.ACTIVE,
            admin_id=admin_id
        )[0:2]
    
    async def deactivate_subscription(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Deactivate a subscription.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        return await self.update_subscription(
            user_id,
            status=SubscriptionStatus.ACTIVE,  # Deactivating means setting to inactive
            admin_id=admin_id
        )[0:2]
    
    async def expire_subscription(self, user_id: int, admin_id: int = None) -> Tuple[bool, str]:
        """
        Expire a subscription.
        
        Args:
            user_id: The Telegram user ID.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                
                if await subscription_repo.expire_subscription(user_id):
                    # Log the action
                    if self.audit_manager and admin_id:
                        user_repo = UserRepository(session)
                        user = await user_repo.get_user(user_id)
                        
                        await self.audit_manager.log_action(
                            administrator_id=admin_id,
                            action="expire_subscription",
                            action_type="subscription",
                            target_id=user_id,
                            target_type="user",
                            target_name=user.username if user else f"User {user_id}",
                            details={}
                        )
                    
                    logger.info(f"Expired subscription for user {user_id}")
                    return True, ""
                else:
                    return False, "Subscription not found"
                    
        except Exception as e:
            logger.error(f"Error expiring subscription for user {user_id}: {e}")
            return False, str(e)
    
    async def extend_subscription(
        self,
        user_id: int,
        days: int,
        admin_id: int = None
    ) -> Tuple[bool, str]:
        """
        Extend a subscription by a number of days.
        
        Args:
            user_id: The Telegram user ID.
            days: Number of days to extend.
            admin_id: The administrator ID making the change.
            
        Returns:
            Tuple of (success, error_message).
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                subscription = await subscription_repo.get_subscription_by_user(user_id)
                
                if not subscription:
                    return False, "Subscription not found"
                
                if not subscription.end_date:
                    return False, "Subscription has no end date"
                
                # Calculate new end date
                new_end_date = subscription.end_date + timedelta(days=days)
                
                # Update subscription
                await subscription_repo.update(subscription.user_id, {
                    "end_date": new_end_date,
                    "updated_at": datetime.utcnow()
                })
                
                # Log the action
                if self.audit_manager and admin_id:
                    user_repo = UserRepository(session)
                    user = await user_repo.get_user(user_id)
                    
                    await self.audit_manager.log_action(
                        administrator_id=admin_id,
                        action="extend_subscription",
                        action_type="subscription",
                        target_id=user_id,
                        target_type="user",
                        target_name=user.username if user else f"User {user_id}",
                        details={"days": days, "new_end_date": new_end_date.isoformat()}
                    )
                
                logger.info(f"Extended subscription for user {user_id} by {days} days")
                return True, ""
                
        except Exception as e:
            logger.error(f"Error extending subscription for user {user_id}: {e}")
            return False, str(e)
    
    async def is_premium(self, user_id: int) -> bool:
        """
        Check if a user has premium subscription.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            True if the user has premium subscription, False otherwise.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                return await subscription_repo.is_premium(user_id)
        except Exception as e:
            logger.error(f"Error checking premium status for user {user_id}: {e}")
            return False
    
    async def get_subscription_type(self, user_id: int) -> Optional[SubscriptionType]:
        """
        Get the subscription type for a user.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            SubscriptionType, or None if not found.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                return await subscription_repo.get_subscription_type(user_id)
        except Exception as e:
            logger.error(f"Error getting subscription type for user {user_id}: {e}")
            return None
    
    async def check_subscription_limits(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Check if a user has reached their subscription limits.
        
        Args:
            user_id: The Telegram user ID.
            
        Returns:
            Dictionary with limit information.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                subscription = await subscription_repo.get_subscription_by_user(user_id)
                
                if not subscription:
                    # No subscription, use free limits
                    return {
                        "has_subscription": False,
                        "max_accounts": self.config.subscription.FREE_MAX_ACCOUNTS,
                        "max_groups": self.config.subscription.FREE_MAX_GROUPS,
                        "min_publish_interval": self.config.subscription.FREE_PUBLISH_INTERVAL_MINUTES,
                        "limits_reached": False
                    }
                
                # Count user's accounts
                account_repo = TelegramAccountRepository(session)
                accounts = await account_repo.get_accounts_by_user(user_id)
                account_count = len(accounts)
                
                # Count user's groups
                from database.repositories import GroupRepository
                group_repo = GroupRepository(session)
                groups = await group_repo.get_all()
                user_groups = [g for g in groups if g.account_id in [a.id for a in accounts]]
                group_count = len(user_groups)
                
                limits_reached = (
                    account_count >= subscription.max_accounts or
                    group_count >= subscription.max_groups
                )
                
                return {
                    "has_subscription": True,
                    "subscription_type": subscription.subscription_type,
                    "max_accounts": subscription.max_accounts,
                    "max_groups": subscription.max_groups,
                    "min_publish_interval": subscription.min_publish_interval,
                    "current_accounts": account_count,
                    "current_groups": group_count,
                    "limits_reached": limits_reached
                }
                
        except Exception as e:
            logger.error(f"Error checking subscription limits for user {user_id}: {e}")
            return {}
    
    async def get_subscription_statistics(self) -> Dict[str, Any]:
        """
        Get subscription statistics.
        
        Returns:
            Dictionary with subscription statistics.
        """
        try:
            async with self.session_factory() as session:
                subscription_repo = SubscriptionRepository(session)
                
                all_subscriptions = await subscription_repo.get_all()
                
                # Count by type
                type_counts = {}
                for sub in all_subscriptions:
                    sub_type = sub.subscription_type
                    type_counts[sub_type] = type_counts.get(sub_type, 0) + 1
                
                # Count by status
                status_counts = {}
                for sub in all_subscriptions:
                    status = sub.status
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count premium vs free
                premium = len([s for s in all_subscriptions if s.subscription_type != SubscriptionType.FREE.value])
                free = len([s for s in all_subscriptions if s.subscription_type == SubscriptionType.FREE.value])
                
                return {
                    "total": len(all_subscriptions),
                    "by_type": type_counts,
                    "by_status": status_counts,
                    "premium": premium,
                    "free": free,
                    "active": status_counts.get(SubscriptionStatus.ACTIVE.value, 0),
                    "expired": status_counts.get(SubscriptionStatus.EXPIRED.value, 0)
                }
                
        except Exception as e:
            logger.error(f"Error getting subscription statistics: {e}")
            return {}


__all__ = [
    'SubscriptionInfo',
    'SubscriptionManager',
]
