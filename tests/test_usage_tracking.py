"""Usage tracking and quota enforcement tests."""

import pytest
from datetime import datetime, timedelta, timezone

from models import db
from services.deployment_service import DeploymentService
from services.usage_tracking_service import UsageTrackingService
from tests.factories import QuotaFactory, TestScenarios, UsageRecordFactory, UserFactory


class TestUsageRecording:
    """Test usage recording functionality."""

    def test_record_usage_success(self, app):
        """Test successful usage recording."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            record = UsageTrackingService.record_usage(
                user_id=user.id,
                provider="openrouter",
                tokens_consumed=1000,
                operation_type="grading",
                project_id="test-project-123",
                model_name="anthropic/claude-3-5-sonnet",
            )

            assert record is not None
            assert record.user_id == user.id
            assert record.provider == "openrouter"
            assert record.tokens_consumed == 1000
            assert record.operation_type == "grading"
            assert record.project_id == "test-project-123"

    def test_record_usage_creates_database_entry(self, app):
        """Test usage recording persists to database."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            UsageTrackingService.record_usage(
                user_id=user.id,
                provider="openrouter",
                tokens_consumed=1000,
                operation_type="grading",
            )

            # Verify database entry exists
            from models import UsageRecord

            records = UsageRecord.query.filter_by(user_id=user.id).all()
            assert len(records) == 1
            assert records[0].tokens_consumed == 1000

    def test_record_usage_multiple_providers(self, app):
        """Test recording usage across multiple providers."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Record usage for different providers
            UsageTrackingService.record_usage(
                user_id=user.id, provider="openrouter", tokens_consumed=1000, operation_type="grading"
            )
            UsageTrackingService.record_usage(
                user_id=user.id, provider="claude", tokens_consumed=2000, operation_type="ocr"
            )
            UsageTrackingService.record_usage(
                user_id=user.id, provider="gemini", tokens_consumed=500, operation_type="analysis"
            )

            # Verify all recorded
            from models import UsageRecord

            records = UsageRecord.query.filter_by(user_id=user.id).all()
            assert len(records) == 3


class TestQuotaCalculation:
    """Test quota calculation and current usage."""

    def test_get_current_usage_zero(self, app):
        """Test current usage returns zero when no usage exists."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            current = UsageTrackingService.get_current_usage(
                user_id=user.id, provider="openrouter", reset_period="monthly"
            )

            assert current == 0

    def test_get_current_usage_sums_tokens(self, app):
        """Test current usage correctly sums token consumption."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Record multiple usage entries
            UsageTrackingService.record_usage(
                user_id=user.id, provider="openrouter", tokens_consumed=1000, operation_type="grading"
            )
            UsageTrackingService.record_usage(
                user_id=user.id, provider="openrouter", tokens_consumed=2500, operation_type="grading"
            )
            UsageTrackingService.record_usage(
                user_id=user.id, provider="openrouter", tokens_consumed=1500, operation_type="grading"
            )

            current = UsageTrackingService.get_current_usage(
                user_id=user.id, provider="openrouter", reset_period="monthly"
            )

            assert current == 5000

    def test_get_current_usage_filters_by_provider(self, app):
        """Test current usage filters by provider correctly."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            UsageTrackingService.record_usage(
                user_id=user.id, provider="openrouter", tokens_consumed=1000, operation_type="grading"
            )
            UsageTrackingService.record_usage(
                user_id=user.id, provider="claude", tokens_consumed=2000, operation_type="grading"
            )

            current_openrouter = UsageTrackingService.get_current_usage(
                user_id=user.id, provider="openrouter", reset_period="monthly"
            )
            current_claude = UsageTrackingService.get_current_usage(
                user_id=user.id, provider="claude", reset_period="monthly"
            )

            assert current_openrouter == 1000
            assert current_claude == 2000


class TestQuotaEnforcement:
    """Test quota limit enforcement."""

    def test_check_quota_no_quota_unlimited(self, app):
        """Test quota check returns unlimited when no quota set."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            result = UsageTrackingService.check_quota(user_id=user.id, provider="openrouter")

            assert result["can_use"] is True
            assert result["limit"] == -1
            assert result["remaining"] == -1
            assert "unlimited" in result["message"].lower()

    def test_check_quota_within_limit(self, app):
        """Test quota check allows usage within limit."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Set quota
            QuotaFactory.create(
                user_id=user.id,
                provider="openrouter",
                limit_value=100000,
                reset_period="monthly",
            )

            # Use 50,000 tokens (50%)
            for _ in range(10):
                UsageTrackingService.record_usage(
                    user_id=user.id, provider="openrouter", tokens_consumed=5000, operation_type="grading"
                )

            result = UsageTrackingService.check_quota(user_id=user.id, provider="openrouter")

            assert result["can_use"] is True
            assert result["current_usage"] == 50000
            assert result["limit"] == 100000
            assert result["remaining"] == 50000
            assert result["percentage_used"] == 50.0
            assert result["warning"] is False

    def test_check_quota_exceeded(self, app):
        """Test quota check blocks usage when quota exceeded."""
        with app.app_context():
            scenario = TestScenarios.create_over_quota_scenario()
            user = scenario["user"]

            result = UsageTrackingService.check_quota(user_id=user.id, provider="openrouter")

            assert result["can_use"] is False
            assert result["current_usage"] > result["limit"]
            assert result["remaining"] == 0

    def test_check_quota_warning_threshold(self, app):
        """Test quota check warns at 80% usage."""
        with app.app_context():
            scenario = TestScenarios.create_quota_limit_scenario()
            user = scenario["user"]

            result = UsageTrackingService.check_quota(user_id=user.id, provider="openrouter")

            assert result["can_use"] is True
            assert result["percentage_used"] >= 80
            assert result["warning"] is True


class TestUsageHistory:
    """Test usage history retrieval."""

    def test_get_usage_history_empty(self, app):
        """Test usage history returns empty when no usage."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            history = UsageTrackingService.get_usage_history(user_id=user.id)

            assert history["total"] == 0
            assert len(history["records"]) == 0
            assert history["user_id"] == user.id

    def test_get_usage_history_returns_records(self, app):
        """Test usage history returns all records."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Create usage records
            for i in range(5):
                UsageTrackingService.record_usage(
                    user_id=user.id,
                    provider="openrouter",
                    tokens_consumed=1000 * (i + 1),
                    operation_type="grading",
                )

            history = UsageTrackingService.get_usage_history(user_id=user.id)

            assert history["total"] == 5
            assert len(history["records"]) == 5

    def test_get_usage_history_pagination(self, app):
        """Test usage history pagination."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Create 20 records
            for i in range(20):
                UsageTrackingService.record_usage(
                    user_id=user.id, provider="openrouter", tokens_consumed=1000, operation_type="grading"
                )

            # Get first page (10 records)
            page1 = UsageTrackingService.get_usage_history(user_id=user.id, limit=10, offset=0)

            # Get second page (10 records)
            page2 = UsageTrackingService.get_usage_history(user_id=user.id, limit=10, offset=10)

            assert page1["total"] == 20
            assert len(page1["records"]) == 10
            assert page2["total"] == 20
            assert len(page2["records"]) == 10

    def test_get_usage_history_filters_by_provider(self, app):
        """Test usage history filters by provider."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Create records for different providers
            for _ in range(3):
                UsageTrackingService.record_usage(
                    user_id=user.id, provider="openrouter", tokens_consumed=1000, operation_type="grading"
                )
            for _ in range(2):
                UsageTrackingService.record_usage(
                    user_id=user.id, provider="claude", tokens_consumed=1000, operation_type="grading"
                )

            history_openrouter = UsageTrackingService.get_usage_history(
                user_id=user.id, provider="openrouter"
            )
            history_claude = UsageTrackingService.get_usage_history(user_id=user.id, provider="claude")

            assert history_openrouter["total"] == 3
            assert history_claude["total"] == 2


class TestUsageDashboard:
    """Test usage dashboard aggregation."""

    def test_get_usage_dashboard_empty(self, app):
        """Test usage dashboard with no quotas."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            dashboard = UsageTrackingService.get_usage_dashboard(user_id=user.id)

            assert dashboard["user_id"] == user.id
            assert len(dashboard["providers"]) == 0
            assert "generated_at" in dashboard

    def test_get_usage_dashboard_multiple_providers(self, app):
        """Test usage dashboard with multiple providers."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Set quotas for multiple providers
            QuotaFactory.create(
                user_id=user.id, provider="openrouter", limit_value=100000, reset_period="monthly"
            )
            QuotaFactory.create(
                user_id=user.id, provider="claude", limit_value=50000, reset_period="weekly"
            )

            # Add usage for each
            UsageTrackingService.record_usage(
                user_id=user.id, provider="openrouter", tokens_consumed=10000, operation_type="grading"
            )
            UsageTrackingService.record_usage(
                user_id=user.id, provider="claude", tokens_consumed=5000, operation_type="ocr"
            )

            dashboard = UsageTrackingService.get_usage_dashboard(user_id=user.id)

            assert len(dashboard["providers"]) == 2
            assert dashboard["user_id"] == user.id

            # Find each provider stats
            openrouter_stats = next(p for p in dashboard["providers"] if p["provider"] == "openrouter")
            claude_stats = next(p for p in dashboard["providers"] if p["provider"] == "claude")

            assert openrouter_stats["current_usage"] == 10000
            assert claude_stats["current_usage"] == 5000


class TestQuotaManagement:
    """Test quota setting and management."""

    def test_set_quota_creates_new(self, app):
        """Test setting quota creates new quota record."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            quota = UsageTrackingService.set_quota(
                user_id=user.id,
                provider="openrouter",
                limit_type="tokens",
                limit_value=100000,
                reset_period="monthly",
            )

            assert quota is not None
            assert quota.user_id == user.id
            assert quota.provider == "openrouter"
            assert quota.limit_value == 100000

    def test_set_quota_updates_existing(self, app):
        """Test setting quota updates existing quota."""
        with app.app_context():
            user = UserFactory.create(email="test@example.com")

            # Create initial quota
            initial = UsageTrackingService.set_quota(
                user_id=user.id,
                provider="openrouter",
                limit_type="tokens",
                limit_value=100000,
                reset_period="monthly",
            )

            # Update quota
            updated = UsageTrackingService.set_quota(
                user_id=user.id,
                provider="openrouter",
                limit_type="tokens",
                limit_value=200000,
                reset_period="weekly",
            )

            assert initial.id == updated.id  # Same record
            assert updated.limit_value == 200000
            assert updated.reset_period == "weekly"


# Fixtures
@pytest.fixture
def app():
    """Create Flask app for testing."""
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        DeploymentService.initialize_default_config()
        yield app
        db.session.remove()
        db.drop_all()
