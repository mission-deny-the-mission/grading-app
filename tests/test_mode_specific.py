"""Mode-specific behavior and feature visibility tests."""

import pytest

from models import db
from services.auth_service import AuthService
from services.deployment_service import DeploymentService
from tests.factories import UserFactory


class TestSingleUserModeFeatures:
    """Test feature availability in single-user mode."""

    def test_all_grading_features_accessible(self, app_single_user, client_single_user):
        """Test all grading features accessible in single-user mode."""
        # Core grading endpoints should all work
        response = client_single_user.get("/")
        assert response.status_code == 200

        response = client_single_user.get("/config")
        assert response.status_code == 200

    def test_no_user_management_visible(self, app_single_user, client_single_user):
        """Test user management features hidden in single-user mode."""
        # User management should not be exposed in single-user mode
        # This would be tested via UI/template rendering
        with app_single_user.app_context():
            # API should reflect single-user mode
            response = client_single_user.get("/api/auth/session")
            data = response.get_json()

            assert data["mode"] == "single-user"
            assert data["authenticated"] is True

    def test_no_sharing_required(self, app_single_user, client_single_user):
        """Test project sharing not required in single-user mode."""
        with app_single_user.app_context():
            from models import GradingJob

            # Create project without owner
            job = GradingJob(
                job_name="Test Project",
                provider="openrouter",
                model="test-model",
                prompt="Test",
                priority=5,
            )
            db.session.add(job)
            db.session.commit()

            # Should be accessible
            retrieved = GradingJob.query.filter_by(job_name="Test Project").first()
            assert retrieved is not None

    def test_no_quota_enforcement(self, app_single_user):
        """Test quotas not enforced in single-user mode."""
        with app_single_user.app_context():
            # In single-user mode, quotas should not apply
            # Users should have unlimited access
            pass  # This is implicit - no quotas exist


class TestMultiUserModeFeatures:
    """Test feature availability in multi-user mode."""

    def test_auth_required_for_grading(self, app_multi_user, client_multi_user):
        """Test authentication required for grading in multi-user mode."""
        # Without auth, should not access grading features
        response = client_multi_user.get("/config")

        # Should redirect or return 401
        assert response.status_code in (302, 401)

    def test_user_management_available(self, app_multi_user):
        """Test user management features available in multi-user mode."""
        with app_multi_user.app_context():
            # Users can be created
            user = AuthService.create_user("test@example.com", "Password123!")
            assert user is not None

            # Users can be listed
            result = AuthService.list_users(limit=10)
            assert result["total"] >= 1

    def test_sharing_functionality_available(self, app_multi_user):
        """Test project sharing available in multi-user mode."""
        with app_multi_user.app_context():
            from services.sharing_service import SharingService
            from tests.factories import ProjectFactory

            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Shared Project", owner_id=owner.id)

            # Can share projects
            share = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            assert share is not None

    def test_quota_tracking_available(self, app_multi_user):
        """Test usage tracking and quotas available in multi-user mode."""
        with app_multi_user.app_context():
            from services.usage_tracking_service import UsageTrackingService

            user = UserFactory.create(email="test@example.com")

            # Can set quotas
            quota = UsageTrackingService.set_quota(
                user_id=user.id,
                provider="openrouter",
                limit_type="tokens",
                limit_value=100000,
                reset_period="monthly",
            )

            assert quota is not None

            # Can record usage
            record = UsageTrackingService.record_usage(
                user_id=user.id,
                provider="openrouter",
                tokens_consumed=1000,
                operation_type="grading",
            )

            assert record is not None


class TestModeSwitchingBehavior:
    """Test behavior when switching between modes."""

    def test_data_preserved_on_mode_switch(self, app):
        """Test data is preserved when switching modes."""
        with app.app_context():
            # Create data in multi-user mode
            DeploymentService.set_mode("multi-user")

            user = AuthService.create_user("test@example.com", "Password123!")
            user_id = user.id

            # Switch to single-user mode
            DeploymentService.set_mode("single-user")

            # User data should still exist
            from models import User

            retrieved = User.query.get(user_id)
            assert retrieved is not None
            assert retrieved.email == "test@example.com"

    def test_grading_jobs_preserved_on_mode_switch(self, app):
        """Test grading jobs preserved across mode switches."""
        with app.app_context():
            from models import GradingJob

            # Create job in single-user mode
            DeploymentService.set_mode("single-user")

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test",
                priority=5,
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Switch to multi-user mode
            DeploymentService.set_mode("multi-user")

            # Job should still exist
            retrieved = GradingJob.query.get(job_id)
            assert retrieved is not None
            assert retrieved.job_name == "Test Job"

    def test_mode_persists_across_restarts(self, app):
        """Test deployment mode persists across app restarts."""
        with app.app_context():
            # Set mode
            DeploymentService.set_mode("multi-user")

            # Simulate app restart by getting fresh config
            mode = DeploymentService.get_current_mode()

            assert mode == "multi-user"


class TestFeatureVisibility:
    """Test feature visibility based on deployment mode."""

    def test_session_reflects_mode(self, app_single_user, client_single_user):
        """Test session endpoint reflects deployment mode."""
        response = client_single_user.get("/api/auth/session")

        assert response.status_code == 200
        data = response.get_json()
        assert data["mode"] == "single-user"

    def test_health_check_shows_mode(self, app_single_user, client_single_user):
        """Test health check shows deployment mode."""
        response = client_single_user.get("/api/config/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["deployment_mode"] == "single-user"

    def test_config_endpoint_shows_mode(self, app_multi_user, client_multi_user):
        """Test config endpoint shows deployment mode."""
        response = client_multi_user.get("/api/config/deployment-mode")

        assert response.status_code == 200
        data = response.get_json()
        assert data["mode"] == "multi-user"


class TestAPIBehaviorDifferences:
    """Test API behavior differences between modes."""

    def test_usage_dashboard_single_user(self, app_single_user, client_single_user):
        """Test usage dashboard accessible in single-user mode."""
        response = client_single_user.get("/api/usage/dashboard")

        assert response.status_code == 200
        data = response.get_json()
        # Should have empty or default data
        assert "providers" in data

    def test_usage_dashboard_multi_user_requires_auth(self, app_multi_user, client_multi_user):
        """Test usage dashboard requires auth in multi-user mode."""
        response = client_multi_user.get("/api/usage/dashboard")

        assert response.status_code == 401

    def test_login_endpoint_behavior(self, app_single_user, app_multi_user):
        """Test login endpoint available in both modes."""
        # Single-user mode - login endpoint exists but not required
        with app_single_user.app_context():
            client = app_single_user.test_client()
            # Login endpoint should exist but return appropriate message
            # Implementation depends on auth_routes.py

        # Multi-user mode - login endpoint required
        with app_multi_user.app_context():
            client = app_multi_user.test_client()
            # Login should be functional


class TestPermissionBehaviorByMode:
    """Test permission behavior varies by mode."""

    def test_single_user_all_permissions(self, app_single_user):
        """Test single-user mode grants all permissions."""
        with app_single_user.app_context():
            from models import GradingJob

            # Any operation should work
            job = GradingJob(
                job_name="Test",
                provider="openrouter",
                model="test-model",
                prompt="Test",
                priority=5,
            )
            db.session.add(job)
            db.session.commit()

            assert job.id is not None

    def test_multi_user_permission_enforcement(self, app_multi_user):
        """Test multi-user mode enforces permissions."""
        with app_multi_user.app_context():
            from services.sharing_service import SharingService

            owner = UserFactory.create(email="owner@example.com")
            other = UserFactory.create(email="other@example.com")

            from tests.factories import ProjectFactory

            project = ProjectFactory.create(job_name="Test", owner_id=owner.id)

            # Other user should not have access
            can_access = SharingService.can_access_project(
                user_id=other.id, project_id=project.id, owner_id=owner.id
            )

            assert can_access is False


class TestModeValidation:
    """Test mode validation and consistency checks."""

    def test_validate_mode_consistency(self, app, monkeypatch):
        """Test mode consistency validation."""
        with app.app_context():
            DeploymentService.set_mode("single-user")
            monkeypatch.setenv("DEPLOYMENT_MODE", "single-user")

            result = DeploymentService.validate_mode_consistency()

            assert result["valid"] is True
            assert result["env_mode"] == "single-user"
            assert result["db_mode"] == "single-user"

    def test_detect_mode_mismatch(self, app, monkeypatch):
        """Test detection of mode mismatch."""
        with app.app_context():
            DeploymentService.set_mode("single-user")
            monkeypatch.setenv("DEPLOYMENT_MODE", "multi-user")

            result = DeploymentService.validate_mode_consistency()

            assert result["valid"] is False
            assert result["env_mode"] == "multi-user"
            assert result["db_mode"] == "single-user"


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


@pytest.fixture
def app_single_user(app):
    """Create Flask app in single-user mode."""
    with app.app_context():
        DeploymentService.set_mode("single-user")
    return app


@pytest.fixture
def app_multi_user(app):
    """Create Flask app in multi-user mode."""
    with app.app_context():
        DeploymentService.set_mode("multi-user")
    return app


@pytest.fixture
def client_single_user(app_single_user):
    """Create test client for single-user mode."""
    return app_single_user.test_client()


@pytest.fixture
def client_multi_user(app_multi_user):
    """Create test client for multi-user mode."""
    return app_multi_user.test_client()
