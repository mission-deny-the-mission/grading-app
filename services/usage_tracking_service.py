"""AI usage tracking service for monitoring and enforcing quota limits."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from models import AIProviderQuota, UsageRecord, db

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Service for tracking AI provider usage and managing quotas."""

    @staticmethod
    def record_usage(user_id, provider, tokens_consumed, operation_type, project_id=None, model_name=None):
        """
        Record AI provider usage for a user.

        Args:
            user_id: str - User ID
            provider: str - AI provider (openrouter, claude, gemini, lmstudio)
            tokens_consumed: int - Tokens/requests consumed
            operation_type: str - Operation type (grading, ocr, analysis)
            project_id: str - Optional project ID
            model_name: str - Optional model name used

        Returns:
            UsageRecord: Created usage record
        """
        try:
            record = UsageRecord(
                user_id=user_id,
                provider=provider,
                tokens_consumed=tokens_consumed,
                timestamp=datetime.now(timezone.utc),
                project_id=project_id,
                operation_type=operation_type,
                model_name=model_name,
            )
            db.session.add(record)
            db.session.commit()
            logger.info(f"Usage recorded for user {user_id}: {tokens_consumed} tokens from {provider}")
            return record
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording usage for user {user_id}: {e}")
            raise

    @staticmethod
    def get_current_usage(user_id, provider, reset_period="monthly"):
        """
        Get current usage for a user and provider.

        Args:
            user_id: str - User ID
            provider: str - AI provider
            reset_period: str - Period to calculate for (daily, weekly, monthly, unlimited)

        Returns:
            int: Total tokens consumed in current period
        """
        period_start = UsageTrackingService._get_period_start(reset_period)

        query = UsageRecord.query.filter(
            UsageRecord.user_id == user_id,
            UsageRecord.provider == provider,
            UsageRecord.timestamp >= period_start,
        )

        result = query.with_entities(func.sum(UsageRecord.tokens_consumed)).scalar()
        return result or 0

    @staticmethod
    def check_quota(user_id, provider):
        """
        Check if user has exceeded quota for provider.

        Args:
            user_id: str - User ID
            provider: str - AI provider

        Returns:
            dict: {
                "can_use": bool,
                "current_usage": int,
                "limit": int,
                "remaining": int,
                "percentage_used": float,
                "warning": bool (if >80% used)
            }
        """
        # Get user's quota for this provider
        quota = AIProviderQuota.query.filter_by(user_id=user_id, provider=provider).first()

        if not quota:
            # No quota defined = unlimited
            return {
                "can_use": True,
                "current_usage": 0,
                "limit": -1,
                "remaining": -1,
                "percentage_used": 0,
                "warning": False,
                "message": "No quota configured (unlimited)",
            }

        if quota.limit_value == -1:
            # Unlimited quota
            return {
                "can_use": True,
                "current_usage": 0,
                "limit": -1,
                "remaining": -1,
                "percentage_used": 0,
                "warning": False,
                "message": "Unlimited quota",
            }

        # Check actual usage
        current = UsageTrackingService.get_current_usage(user_id, provider, quota.reset_period)
        remaining = max(0, quota.limit_value - current)
        percentage_used = (current / quota.limit_value * 100) if quota.limit_value > 0 else 0
        warning = percentage_used >= 80

        return {
            "can_use": remaining > 0,
            "current_usage": current,
            "limit": quota.limit_value,
            "remaining": remaining,
            "percentage_used": round(percentage_used, 1),
            "warning": warning,
            "message": f"Usage: {current}/{quota.limit_value} tokens ({percentage_used:.1f}%)",
        }

    @staticmethod
    def get_current_usage_obj(user_id, provider):
        """Get current usage data as full object."""
        quota = AIProviderQuota.query.filter_by(user_id=user_id, provider=provider).first()
        return UsageTrackingService.check_quota(user_id, provider) if quota else None

    @staticmethod
    def get_usage_dashboard(user_id):
        """
        Get usage dashboard data for a user across all providers.

        Args:
            user_id: str - User ID

        Returns:
            dict: Aggregated usage data
        """
        quotas = AIProviderQuota.query.filter_by(user_id=user_id).all()

        provider_stats = []
        for quota in quotas:
            stats = UsageTrackingService.check_quota(user_id, quota.provider)
            stats["provider"] = quota.provider
            stats["reset_period"] = quota.reset_period
            provider_stats.append(stats)

        return {
            "user_id": user_id,
            "providers": provider_stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def get_usage_history(user_id, provider=None, limit=100, offset=0):
        """
        Get usage history for a user.

        Args:
            user_id: str - User ID
            provider: str - Optional provider filter
            limit: int - Maximum records to return
            offset: int - Records to skip

        Returns:
            dict: {records: list, total: int, limit: int, offset: int}
        """
        query = UsageRecord.query.filter_by(user_id=user_id)

        if provider:
            query = query.filter_by(provider=provider)

        total = query.count()
        records = query.order_by(UsageRecord.timestamp.desc()).limit(limit).offset(offset).all()

        return {
            "records": [r.to_dict() for r in records],
            "total": total,
            "limit": limit,
            "offset": offset,
            "user_id": user_id,
        }

    @staticmethod
    def set_quota(user_id, provider, limit_type, limit_value, reset_period):
        """
        Set or update quota for a user and provider.

        Args:
            user_id: str - User ID
            provider: str - AI provider
            limit_type: str - Limit metric (tokens, requests)
            limit_value: int - Maximum value (-1 for unlimited)
            reset_period: str - Reset frequency (daily, weekly, monthly, unlimited)

        Returns:
            AIProviderQuota: Created or updated quota
        """
        try:
            quota = AIProviderQuota.query.filter_by(user_id=user_id, provider=provider).first()

            if not quota:
                quota = AIProviderQuota(
                    user_id=user_id,
                    provider=provider,
                    limit_type=limit_type,
                    limit_value=limit_value,
                    reset_period=reset_period,
                )
                db.session.add(quota)
            else:
                quota.limit_type = limit_type
                quota.limit_value = limit_value
                quota.reset_period = reset_period
                quota.updated_at = datetime.now(timezone.utc)

            db.session.commit()
            logger.info(f"Quota set for user {user_id}, provider {provider}: {limit_value} {limit_type}")
            return quota
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error setting quota: {e}")
            raise

    @staticmethod
    def _get_period_start(reset_period):
        """
        Get the start datetime for a given period.

        Args:
            reset_period: str - Period type (daily, weekly, monthly, unlimited)

        Returns:
            datetime: Start of current period in UTC
        """
        now = datetime.now(timezone.utc)

        if reset_period == "daily":
            # Start of today
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        elif reset_period == "weekly":
            # Start of current week (Monday)
            days_since_monday = now.weekday()
            start = now - timedelta(days=days_since_monday)
            return start.replace(hour=0, minute=0, second=0, microsecond=0)

        elif reset_period == "monthly":
            # Start of current month
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        else:  # unlimited
            # Return very far in past (effectively no limit)
            return now - timedelta(days=36500)
