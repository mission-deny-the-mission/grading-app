"""Test data factories for creating realistic test objects."""

import random
import string
from datetime import datetime, timezone
from typing import Optional

from models import (
    AIProviderQuota,
    GradingJob,
    ProjectShare,
    User,
    UsageRecord,
    db,
)


class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    def create(
        email: Optional[str] = None,
        password: str = "Password123!",
        display_name: Optional[str] = None,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> User:
        """
        Create a test user.

        Args:
            email: User email (auto-generated if not provided)
            password: User password (default: Password123!)
            display_name: Display name (auto-generated if not provided)
            is_admin: Admin status
            is_active: Active status

        Returns:
            User: Created user object
        """
        if email is None:
            random_str = "".join(random.choices(string.ascii_lowercase, k=8))
            email = f"test_{random_str}@example.com"

        if display_name is None:
            display_name = f"Test User {email.split('@')[0]}"

        from services.auth_service import AuthService

        user = AuthService.create_user(
            email=email,
            password=password,
            display_name=display_name,
            is_admin=is_admin,
        )

        if not is_active:
            user.is_active = False
            db.session.commit()

        return user

    @staticmethod
    def create_batch(count: int = 3, **kwargs) -> list[User]:
        """Create multiple test users."""
        return [UserFactory.create(**kwargs) for _ in range(count)]


class ProjectFactory:
    """Factory for creating test projects (GradingJobs)."""

    @staticmethod
    def create(
        job_name: Optional[str] = None,
        owner_id: Optional[str] = None,
        description: Optional[str] = None,
        provider: str = "openrouter",
        model: str = "anthropic/claude-3-5-sonnet-20241022",
    ) -> GradingJob:
        """
        Create a test grading job/project.

        Args:
            job_name: Project name (auto-generated if not provided)
            owner_id: Owner user ID (auto-generated if not provided)
            description: Project description
            provider: AI provider
            model: AI model name

        Returns:
            GradingJob: Created project
        """
        if job_name is None:
            random_str = "".join(random.choices(string.ascii_lowercase, k=8))
            job_name = f"Test Project {random_str}"

        if owner_id is None:
            # Create a test user as owner
            owner = UserFactory.create()
            owner_id = owner.id

        if description is None:
            description = f"Test project for automated testing: {job_name}"

        project = GradingJob(
            job_name=job_name,
            description=description,
            provider=provider,
            model=model,
            prompt="Test grading prompt",
            priority=5,
            temperature=0.7,
            max_tokens=2000,
            owner_id=owner_id,  # Set owner for multi-user mode
        )
        db.session.add(project)
        db.session.commit()

        return project

    @staticmethod
    def create_batch(count: int = 3, **kwargs) -> list[GradingJob]:
        """Create multiple test projects."""
        return [ProjectFactory.create(**kwargs) for _ in range(count)]


class UsageRecordFactory:
    """Factory for creating test usage records."""

    @staticmethod
    def create(
        user_id: Optional[str] = None,
        provider: str = "openrouter",
        tokens_consumed: int = 1000,
        operation_type: str = "grading",
        project_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> UsageRecord:
        """
        Create a test usage record.

        Args:
            user_id: User ID (auto-generated if not provided)
            provider: AI provider
            tokens_consumed: Number of tokens consumed
            operation_type: Operation type
            project_id: Project ID
            model_name: Model name used

        Returns:
            UsageRecord: Created usage record
        """
        if user_id is None:
            user = UserFactory.create()
            user_id = user.id

        record = UsageRecord(
            user_id=user_id,
            provider=provider,
            tokens_consumed=tokens_consumed,
            timestamp=datetime.now(timezone.utc),
            project_id=project_id,
            operation_type=operation_type,
            model_name=model_name or f"{provider}/test-model",
        )
        db.session.add(record)
        db.session.commit()

        return record

    @staticmethod
    def create_batch(count: int = 5, **kwargs) -> list[UsageRecord]:
        """Create multiple usage records."""
        return [UsageRecordFactory.create(**kwargs) for _ in range(count)]


class QuotaFactory:
    """Factory for creating test quotas."""

    @staticmethod
    def create(
        user_id: Optional[str] = None,
        provider: str = "openrouter",
        limit_type: str = "tokens",
        limit_value: int = 100000,
        reset_period: str = "monthly",
    ) -> AIProviderQuota:
        """
        Create a test quota.

        Args:
            user_id: User ID (auto-generated if not provided)
            provider: AI provider
            limit_type: Limit type (tokens, requests)
            limit_value: Limit value (-1 for unlimited)
            reset_period: Reset period (daily, weekly, monthly, unlimited)

        Returns:
            AIProviderQuota: Created quota
        """
        if user_id is None:
            user = UserFactory.create()
            user_id = user.id

        quota = AIProviderQuota(
            user_id=user_id,
            provider=provider,
            limit_type=limit_type,
            limit_value=limit_value,
            reset_period=reset_period,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(quota)
        db.session.commit()

        return quota

    @staticmethod
    def create_batch(count: int = 3, **kwargs) -> list[AIProviderQuota]:
        """Create multiple quotas."""
        return [QuotaFactory.create(**kwargs) for _ in range(count)]


class ShareFactory:
    """Factory for creating test project shares."""

    @staticmethod
    def create(
        project_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        permission_level: str = "read",
    ) -> ProjectShare:
        """
        Create a test project share.

        Args:
            project_id: Project ID (auto-generated if not provided)
            owner_id: Owner user ID (auto-generated if not provided)
            recipient_id: Recipient user ID (auto-generated if not provided)
            permission_level: Permission level (read, write)

        Returns:
            ProjectShare: Created share
        """
        if project_id is None:
            project = ProjectFactory.create(owner_id=owner_id)
            project_id = project.id
            owner_id = project.owner_id

        if owner_id is None:
            owner = UserFactory.create()
            owner_id = owner.id

        if recipient_id is None:
            recipient = UserFactory.create()
            recipient_id = recipient.id

        share = ProjectShare(
            project_id=project_id,
            user_id=recipient_id,
            permission_level=permission_level,
            granted_by=owner_id,
            granted_at=datetime.now(timezone.utc),
        )
        db.session.add(share)
        db.session.commit()

        return share

    @staticmethod
    def create_batch(count: int = 3, **kwargs) -> list[ProjectShare]:
        """Create multiple project shares."""
        return [ShareFactory.create(**kwargs) for _ in range(count)]


class TestScenarios:
    """Pre-configured test scenarios for common testing patterns."""

    @staticmethod
    def create_multi_user_project_scenario():
        """
        Create a complete multi-user project scenario.

        Returns:
            dict: {
                "owner": User,
                "collaborators": list[User],
                "project": GradingJob,
                "shares": list[ProjectShare]
            }
        """
        owner = UserFactory.create(email="owner@example.com", display_name="Project Owner")
        collaborator1 = UserFactory.create(email="reader@example.com", display_name="Reader User")
        collaborator2 = UserFactory.create(email="writer@example.com", display_name="Writer User")

        project = ProjectFactory.create(
            job_name="Shared Test Project",
            owner_id=owner.id,
        )

        share_read = ShareFactory.create(
            project_id=project.id,
            owner_id=owner.id,
            recipient_id=collaborator1.id,
            permission_level="read",
        )

        share_write = ShareFactory.create(
            project_id=project.id,
            owner_id=owner.id,
            recipient_id=collaborator2.id,
            permission_level="write",
        )

        return {
            "owner": owner,
            "collaborators": [collaborator1, collaborator2],
            "project": project,
            "shares": [share_read, share_write],
        }

    @staticmethod
    def create_quota_limit_scenario(user_id: Optional[str] = None):
        """
        Create a quota limit scenario (user near quota limit).

        Returns:
            dict: {
                "user": User,
                "quota": AIProviderQuota,
                "usage_records": list[UsageRecord]
            }
        """
        if user_id is None:
            user = UserFactory.create(email="quota_user@example.com")
            user_id = user.id
        else:
            user = User.query.get(user_id)

        # Set quota to 100,000 tokens
        quota = QuotaFactory.create(
            user_id=user_id,
            provider="openrouter",
            limit_value=100000,
            reset_period="monthly",
        )

        # Create usage records totaling 85,000 tokens (85% of quota)
        usage_records = []
        for i in range(17):
            record = UsageRecordFactory.create(
                user_id=user_id,
                provider="openrouter",
                tokens_consumed=5000,
                operation_type="grading",
            )
            usage_records.append(record)

        return {
            "user": user,
            "quota": quota,
            "usage_records": usage_records,
        }

    @staticmethod
    def create_over_quota_scenario(user_id: Optional[str] = None):
        """
        Create an over-quota scenario (user exceeded quota).

        Returns:
            dict: {
                "user": User,
                "quota": AIProviderQuota,
                "usage_records": list[UsageRecord]
            }
        """
        if user_id is None:
            user = UserFactory.create(email="over_quota@example.com")
            user_id = user.id
        else:
            user = User.query.get(user_id)

        # Set quota to 50,000 tokens
        quota = QuotaFactory.create(
            user_id=user_id,
            provider="openrouter",
            limit_value=50000,
            reset_period="monthly",
        )

        # Create usage records totaling 55,000 tokens (110% of quota)
        usage_records = []
        for i in range(11):
            record = UsageRecordFactory.create(
                user_id=user_id,
                provider="openrouter",
                tokens_consumed=5000,
                operation_type="grading",
            )
            usage_records.append(record)

        return {
            "user": user,
            "quota": quota,
            "usage_records": usage_records,
        }
