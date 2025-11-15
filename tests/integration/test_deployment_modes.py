"""Integration tests for deployment modes."""

import pytest

from models import db
from services.auth_service import AuthService
from services.deployment_service import DeploymentService


class TestSingleUserMode:
    """Test single-user deployment mode."""

    def test_single_user_mode_active(self, app_single_user):
        """Test single-user mode is active."""
        with app_single_user.app_context():
            assert DeploymentService.is_single_user_mode()

    def test_single_user_mode_config_endpoint(self, app_single_user, client_single_user):
        """Test config endpoint in single-user mode."""
        response = client_single_user.get("/api/config/deployment-mode")

        assert response.status_code == 200
        data = response.get_json()
        assert data["mode"] == "single-user"

    def test_single_user_mode_health_check(self, app_single_user, client_single_user):
        """Test health check in single-user mode."""
        response = client_single_user.get("/api/config/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["deployment_mode"] == "single-user"

    def test_single_user_mode_session_endpoint(self, app_single_user, client_single_user):
        """Test session endpoint in single-user mode."""
        response = client_single_user.get("/api/auth/session")

        assert response.status_code == 200
        data = response.get_json()
        assert data["authenticated"]
        assert data["mode"] == "single-user"

    def test_single_user_mode_usage_dashboard(self, app_single_user, client_single_user):
        """Test usage dashboard in single-user mode."""
        response = client_single_user.get("/api/usage/dashboard")

        assert response.status_code == 200
        data = response.get_json()
        assert data["providers"] == []
        assert "message" in data


class TestMultiUserMode:
    """Test multi-user deployment mode."""

    def test_multi_user_mode_active(self, app_multi_user):
        """Test multi-user mode is active."""
        with app_multi_user.app_context():
            assert DeploymentService.is_multi_user_mode()

    def test_multi_user_mode_config_endpoint(self, app_multi_user, client_multi_user):
        """Test config endpoint in multi-user mode."""
        response = client_multi_user.get("/api/config/deployment-mode")

        assert response.status_code == 200
        data = response.get_json()
        assert data["mode"] == "multi-user"

    def test_multi_user_mode_session_unauthenticated(self, app_multi_user, client_multi_user):
        """Test session endpoint returns unauthenticated in multi-user mode."""
        response = client_multi_user.get("/api/auth/session")

        assert response.status_code == 200
        data = response.get_json()
        assert not data["authenticated"]
        assert data["mode"] == "multi-user"

    def test_multi_user_mode_login_required(self, app_multi_user, client_multi_user):
        """Test usage dashboard requires login in multi-user mode."""
        response = client_multi_user.get("/api/usage/dashboard")

        assert response.status_code == 401


class TestModeSwitch:
    """Test switching between modes."""

    def test_switch_single_to_multi_user(self, app):
        """Test switching from single-user to multi-user mode."""
        with app.app_context():
            # Start with single-user
            DeploymentService.set_mode("single-user")
            assert DeploymentService.is_single_user_mode()

            # Switch to multi-user
            DeploymentService.set_mode("multi-user")
            assert DeploymentService.is_multi_user_mode()

    def test_switch_multi_to_single_user(self, app):
        """Test switching from multi-user to single-user mode."""
        with app.app_context():
            # Start with multi-user
            DeploymentService.set_mode("multi-user")
            assert DeploymentService.is_multi_user_mode()

            # Switch to single-user
            DeploymentService.set_mode("single-user")
            assert DeploymentService.is_single_user_mode()

    def test_mode_persistence_across_requests(self, app_multi_user, client_multi_user):
        """Test mode persists across multiple requests."""
        response1 = client_multi_user.get("/api/config/deployment-mode")
        response2 = client_multi_user.get("/api/config/deployment-mode")

        data1 = response1.get_json()
        data2 = response2.get_json()

        assert data1["mode"] == data2["mode"] == "multi-user"


class TestUserCreationInMultiUserMode:
    """Test user creation behavior in multi-user mode."""

    def test_create_user_in_multi_user_mode(self, app_multi_user):
        """Test creating user in multi-user mode."""
        with app_multi_user.app_context():
            user = AuthService.create_user("test@example.com", "password123")

            assert user.email == "test@example.com"
            assert user.is_active

    def test_authentication_in_multi_user_mode(self, app_multi_user, client_multi_user):
        """Test authentication in multi-user mode."""
        with app_multi_user.app_context():
            AuthService.create_user("test@example.com", "password123")

        # Try to login
        response = client_multi_user.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"]


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
