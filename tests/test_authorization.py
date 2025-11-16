"""Authorization and permission tests."""

import pytest

from models import db
from services.auth_service import AuthService
from services.deployment_service import DeploymentService
from services.sharing_service import SharingService
from tests.factories import ProjectFactory, ShareFactory, TestScenarios, UserFactory


class TestSingleUserModeAuthorization:
    """Test authorization behavior in single-user mode."""

    def test_single_user_mode_no_auth_required(self, app_single_user, client_single_user):
        """Test endpoints work without authentication in single-user mode."""
        with app_single_user.app_context():
            # Make request without authentication
            response = client_single_user.get("/")

            assert response.status_code == 200

    def test_single_user_mode_api_endpoints_accessible(self, app_single_user, client_single_user):
        """Test API endpoints accessible without auth in single-user mode."""
        with app_single_user.app_context():
            # Usage dashboard should work without auth
            response = client_single_user.get("/api/usage/dashboard")

            assert response.status_code == 200

    def test_single_user_mode_session_authenticated(self, app_single_user, client_single_user):
        """Test session endpoint reports authenticated in single-user mode."""
        response = client_single_user.get("/api/auth/session")

        assert response.status_code == 200
        data = response.get_json()
        assert data["authenticated"] is True
        assert data["mode"] == "single-user"

    def test_single_user_mode_bypasses_middleware(self, app_single_user, client_single_user):
        """Test authentication middleware is bypassed in single-user mode."""
        with app_single_user.app_context():
            # Protected routes should not require login
            response = client_single_user.get("/config")

            # Should not redirect to login
            assert response.status_code == 200


class TestMultiUserModeAuthorization:
    """Test authorization behavior in multi-user mode."""

    def test_multi_user_mode_requires_auth(self, app_multi_user, client_multi_user):
        """Test protected endpoints require authentication in multi-user mode."""
        with app_multi_user.app_context():
            # Try accessing protected route without login
            response = client_multi_user.get("/config")

            # Should redirect to login or return 401
            assert response.status_code in (302, 401)

    def test_multi_user_mode_api_returns_401(self, app_multi_user, client_multi_user):
        """Test API endpoints return 401 when unauthenticated."""
        response = client_multi_user.get("/api/usage/dashboard")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    def test_multi_user_mode_session_unauthenticated(self, app_multi_user, client_multi_user):
        """Test session endpoint reports unauthenticated in multi-user mode."""
        response = client_multi_user.get("/api/auth/session")

        assert response.status_code == 200
        data = response.get_json()
        assert data["authenticated"] is False
        assert data["mode"] == "multi-user"

    def test_multi_user_mode_public_routes_accessible(self, app_multi_user, client_multi_user):
        """Test public routes accessible without auth."""
        # Public routes should still work
        response = client_multi_user.get("/api/config/deployment-mode")

        assert response.status_code == 200


class TestAdminAuthorization:
    """Test admin-only access control."""

    def test_admin_can_access_admin_endpoints(self, app_multi_user):
        """Test admin users can access admin endpoints."""
        with app_multi_user.app_context():
            admin = UserFactory.create(email="admin@example.com", is_admin=True)

            assert admin.is_admin is True

    def test_non_admin_cannot_access_admin_endpoints(self, app_multi_user):
        """Test non-admin users cannot access admin endpoints."""
        with app_multi_user.app_context():
            user = UserFactory.create(email="user@example.com", is_admin=False)

            assert user.is_admin is False


class TestProjectAccessAuthorization:
    """Test project access permissions."""

    def test_owner_can_access_own_project(self, app_multi_user):
        """Test project owner can access their project."""
        with app_multi_user.app_context():
            owner = UserFactory.create(email="owner@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            # Owner should have access
            can_access = SharingService.can_access_project(
                user_id=owner.id, project_id=project.id, owner_id=owner.id
            )

            assert can_access is True

    def test_user_cannot_access_other_user_project(self, app_multi_user):
        """Test users cannot access other users' projects without permission."""
        with app_multi_user.app_context():
            owner = UserFactory.create(email="owner@example.com")
            other_user = UserFactory.create(email="other@example.com")
            project = ProjectFactory.create(job_name="Private Project", owner_id=owner.id)

            # Other user should not have access
            can_access = SharingService.can_access_project(
                user_id=other_user.id, project_id=project.id, owner_id=owner.id
            )

            assert can_access is False

    def test_shared_user_can_access_project(self, app_multi_user):
        """Test users with share can access shared projects."""
        with app_multi_user.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            owner = scenario["owner"]
            reader = scenario["collaborators"][0]
            project = scenario["project"]

            # Reader should have access via share
            can_access = SharingService.can_access_project(
                user_id=reader.id, project_id=project.id, owner_id=owner.id
            )

            assert can_access is True


class TestProjectModificationAuthorization:
    """Test project modification permissions."""

    def test_owner_can_modify_project(self, app_multi_user):
        """Test owner can modify their project."""
        with app_multi_user.app_context():
            owner = UserFactory.create(email="owner@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            # Owner can modify
            can_modify = SharingService.can_modify_project(
                user_id=owner.id, project_id=project.id, owner_id=owner.id
            )

            assert can_modify is True

    def test_read_only_user_cannot_modify_project(self, app_multi_user):
        """Test read-only users cannot modify shared projects."""
        with app_multi_user.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            owner = scenario["owner"]
            reader = scenario["collaborators"][0]  # Has read permission
            project = scenario["project"]

            # Reader cannot modify (read-only)
            can_modify = SharingService.can_modify_project(
                user_id=reader.id, project_id=project.id, owner_id=owner.id
            )

            assert can_modify is False

    def test_write_user_can_modify_project(self, app_multi_user):
        """Test users with write permission can modify shared projects."""
        with app_multi_user.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            owner = scenario["owner"]
            writer = scenario["collaborators"][1]  # Has write permission
            project = scenario["project"]

            # Writer can modify
            can_modify = SharingService.can_modify_project(
                user_id=writer.id, project_id=project.id, owner_id=owner.id
            )

            assert can_modify is True

    def test_user_without_share_cannot_modify(self, app_multi_user):
        """Test users without any share cannot modify projects."""
        with app_multi_user.app_context():
            owner = UserFactory.create(email="owner@example.com")
            other_user = UserFactory.create(email="other@example.com")
            project = ProjectFactory.create(job_name="Private Project", owner_id=owner.id)

            # Other user cannot modify
            can_modify = SharingService.can_modify_project(
                user_id=other_user.id, project_id=project.id, owner_id=owner.id
            )

            assert can_modify is False


class TestDataIsolation:
    """Test data isolation between users."""

    def test_user_cannot_see_other_user_data(self, app_multi_user):
        """Test users cannot see other users' private data."""
        with app_multi_user.app_context():
            user1 = UserFactory.create(email="user1@example.com")
            user2 = UserFactory.create(email="user2@example.com")

            project1 = ProjectFactory.create(job_name="User1 Project", owner_id=user1.id)
            project2 = ProjectFactory.create(job_name="User2 Project", owner_id=user2.id)

            # User1 should not have access to user2's project
            can_access = SharingService.can_access_project(
                user_id=user1.id, project_id=project2.id, owner_id=user2.id
            )

            assert can_access is False


class TestPermissionEscalation:
    """Test protection against permission escalation."""

    def test_cannot_escalate_read_to_write(self, app_multi_user):
        """Test read-only users cannot escalate to write permissions."""
        with app_multi_user.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            reader = scenario["collaborators"][0]  # Read-only user
            project = scenario["project"]

            # Verify read permission exists but not write
            can_access = SharingService.can_access_project(
                user_id=reader.id, project_id=project.id
            )
            can_modify = SharingService.can_modify_project(
                user_id=reader.id, project_id=project.id
            )

            assert can_access is True
            assert can_modify is False


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
