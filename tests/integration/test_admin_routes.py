"""Integration tests for admin user management routes."""

import os

import pytest

# Set TESTING environment variable
os.environ["TESTING"] = "True"

from flask_login import login_user

from models import User, db
from services.auth_service import AuthService
from services.deployment_service import DeploymentService


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        user = AuthService.create_user("admin@example.com", "AdminPass123!", "Admin User", is_admin=True)
        yield user


@pytest.fixture
def regular_user(app):
    """Create a regular user for testing."""
    with app.app_context():
        user = AuthService.create_user("user@example.com", "UserPass123!", "Regular User", is_admin=False)
        yield user


@pytest.fixture
def multi_user_mode(app):
    """Set deployment to multi-user mode."""
    with app.app_context():
        DeploymentService.set_mode("multi-user")
        yield
        # Cleanup: reset to single-user mode
        DeploymentService.set_mode("single-user")


class TestAdminListUsers:
    """Test admin list users endpoint."""

    def test_list_users_as_admin(self, client, app, admin_user, multi_user_mode):
        """Test admin can list all users."""
        with app.app_context():
            # Create additional users
            AuthService.create_user("user1@example.com", "UserPass123!", "User 1")
            AuthService.create_user("user2@example.com", "UserPass123!", "User 2")

        # Login as admin
        with client:
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )
            assert response.status_code == 200

            # List users
            response = client.get("/api/admin/users")
            assert response.status_code == 200

            data = response.get_json()
            assert "users" in data
            assert len(data["users"]) >= 3  # admin + 2 users
            assert data["total"] >= 3

    def test_list_users_as_regular_user_fails(self, client, app, regular_user, multi_user_mode):
        """Test regular user cannot list users."""
        with client:
            response = client.post(
                "/api/auth/login",
                json={"email": "user@example.com", "password": "UserPass123!"}
            )
            assert response.status_code == 200

            # Try to list users
            response = client.get("/api/admin/users")
            assert response.status_code == 403
            assert response.get_json()["message"] == "Admin access required"

    def test_list_users_pagination(self, client, app, admin_user, multi_user_mode):
        """Test user list pagination."""
        with app.app_context():
            # Create multiple users
            for i in range(5):
                AuthService.create_user(f"user{i}@example.com", "UserPass123!", f"User {i}")

        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Get first page
            response = client.get("/api/admin/users?limit=3&offset=0")
            data = response.get_json()
            assert len(data["users"]) == 3
            assert data["limit"] == 3
            assert data["offset"] == 0

            # Get second page
            response = client.get("/api/admin/users?limit=3&offset=3")
            data = response.get_json()
            assert len(data["users"]) >= 1


class TestAdminGetUser:
    """Test admin get user details endpoint."""

    def test_get_user_as_admin(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can get user details."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Get user details
            response = client.get(f"/api/admin/users/{regular_user.id}")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["user"]["email"] == "user@example.com"
            assert data["user"]["is_admin"] is False

    def test_get_nonexistent_user(self, client, app, admin_user, multi_user_mode):
        """Test getting non-existent user returns 404."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Try to get non-existent user
            response = client.get("/api/admin/users/nonexistent-id")
            assert response.status_code == 404


class TestAdminCreateUser:
    """Test admin create user endpoint."""

    def test_create_user_as_admin(self, client, app, admin_user, multi_user_mode):
        """Test admin can create new users."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Create new user
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "newuser@example.com",
                    "password": "NewUserPass123!",
                    "display_name": "New User",
                    "is_admin": False
                }
            )
            assert response.status_code == 201

            data = response.get_json()
            assert data["success"] is True
            assert data["user"]["email"] == "newuser@example.com"
            assert data["user"]["is_admin"] is False

    def test_create_user_with_duplicate_email_fails(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test creating user with existing email fails."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Try to create user with existing email
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "user@example.com",  # Already exists
                    "password": "Password123!",
                    "display_name": "Duplicate User"
                }
            )
            assert response.status_code == 400
            assert "already registered" in response.get_json()["message"]

    def test_create_user_with_weak_password_fails(self, client, app, admin_user, multi_user_mode):
        """Test creating user with weak password fails."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Try to create user with weak password
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "newuser@example.com",
                    "password": "weak",  # Too short, no uppercase, etc.
                    "display_name": "New User"
                }
            )
            assert response.status_code == 400


class TestAdminDeleteUser:
    """Test admin delete user endpoint."""

    def test_delete_user_as_admin(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can delete users."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Delete user
            response = client.delete(f"/api/admin/users/{regular_user.id}")
            assert response.status_code == 200
            assert response.get_json()["success"] is True

    def test_admin_cannot_delete_self(self, client, app, admin_user, multi_user_mode):
        """Test admin cannot delete themselves."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Try to delete self
            response = client.delete(f"/api/admin/users/{admin_user.id}")
            assert response.status_code == 400
            assert "Cannot delete yourself" in response.get_json()["message"]


class TestAdminUpdateUserRole:
    """Test admin update user role endpoint."""

    def test_update_user_role_to_admin(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can promote user to admin."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Update role
            response = client.patch(
                f"/api/admin/users/{regular_user.id}/role",
                json={"is_admin": True}
            )
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["user"]["is_admin"] is True

    def test_admin_cannot_change_own_role(self, client, app, admin_user, multi_user_mode):
        """Test admin cannot change their own role."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Try to change own role
            response = client.patch(
                f"/api/admin/users/{admin_user.id}/role",
                json={"is_admin": False}
            )
            assert response.status_code == 400
            assert "Cannot change your own role" in response.get_json()["message"]


class TestAdminUpdateUser:
    """Test admin update user endpoint."""

    def test_update_user_email(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can update user email."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Update email
            response = client.patch(
                f"/api/admin/users/{regular_user.id}",
                json={"email": "newemail@example.com"}
            )
            assert response.status_code == 200

            data = response.get_json()
            assert data["user"]["email"] == "newemail@example.com"

    def test_update_user_password(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can reset user password."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Reset password
            response = client.patch(
                f"/api/admin/users/{regular_user.id}",
                json={"password": "NewPassword456!"}
            )
            assert response.status_code == 200

        # User should be able to login with new password
        response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "NewPassword456!"}
        )
        assert response.status_code == 200

    def test_update_user_display_name(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can update user display name."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Update display name
            response = client.patch(
                f"/api/admin/users/{regular_user.id}",
                json={"display_name": "Updated Name"}
            )
            assert response.status_code == 200

            data = response.get_json()
            assert data["user"]["display_name"] == "Updated Name"

    def test_update_user_is_active(self, client, app, admin_user, regular_user, multi_user_mode):
        """Test admin can deactivate users."""
        with client:
            # Login as admin
            response = client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "AdminPass123!"}
            )

            # Deactivate user
            response = client.patch(
                f"/api/admin/users/{regular_user.id}",
                json={"is_active": False}
            )
            assert response.status_code == 200

            data = response.get_json()
            assert data["user"]["is_active"] is False
