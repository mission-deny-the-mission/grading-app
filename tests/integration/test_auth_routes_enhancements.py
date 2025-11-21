"""Integration tests for enhanced authentication routes."""

import os

import pytest

# Set TESTING environment variable
os.environ["TESTING"] = "True"

from services.auth_service import AuthService
from services.deployment_service import DeploymentService


@pytest.fixture
def multi_user_mode(app):
    """Set deployment to multi-user mode."""
    with app.app_context():
        DeploymentService.set_mode("multi-user")
        yield
        # Cleanup
        DeploymentService.set_mode("single-user")


@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = AuthService.create_user("test@example.com", "TestPass123!", "Test User")
        yield user


class TestPasswordResetRequest:
    """Test password reset request endpoint."""

    def test_request_password_reset_for_existing_user(
        self, client, app, test_user, multi_user_mode
    ):
        """Test requesting password reset for existing user."""
        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "token" in data  # Development mode returns token
        assert "expires_at" in data

    def test_request_password_reset_for_nonexistent_user(
        self, client, app, multi_user_mode
    ):
        """Test requesting password reset for non-existent user (security behavior)."""
        response = client.post(
            "/api/auth/password-reset", json={"email": "nonexistent@example.com"}
        )

        # Should return success to not reveal if email exists
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "reset link has been sent" in data["message"]

    def test_request_password_reset_without_email(self, client, app, multi_user_mode):
        """Test requesting password reset without email fails."""
        response = client.post("/api/auth/password-reset", json={})

        assert response.status_code == 400
        assert response.get_json()["message"] == "Email required"

    def test_request_password_reset_in_single_user_mode_fails(
        self, client, app, test_user
    ):
        """Test password reset is disabled in single-user mode."""
        with app.app_context():
            DeploymentService.set_mode("single-user")

        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )

        assert response.status_code == 400
        assert "disabled in single-user mode" in response.get_json()["message"]

    def test_request_password_reset_production_mode_hides_token(
        self, client, app, test_user, multi_user_mode, monkeypatch
    ):
        """Test that password reset token is NOT returned in production environment."""
        # Set production environment (and ensure TESTING is not set to bypass)
        monkeypatch.setenv("FLASK_ENV", "production")
        monkeypatch.setenv("TESTING", "False")

        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # In production, token should NOT be in response
        assert "token" not in data
        assert "expires_at" not in data


class TestPasswordResetCompletion:
    """Test password reset completion endpoint."""

    def test_reset_password_with_valid_token(
        self, client, app, test_user, multi_user_mode
    ):
        """Test resetting password with valid token."""
        # Request reset
        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )
        token = response.get_json()["token"]

        # Reset password
        response = client.post(
            f"/api/auth/password-reset/{token}", json={"password": "NewPassword456!"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "Password reset successful"

    def test_login_works_after_password_reset(
        self, client, app, test_user, multi_user_mode
    ):
        """Test user can login with new password after reset."""
        # Request and complete reset
        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )
        token = response.get_json()["token"]

        client.post(
            f"/api/auth/password-reset/{token}", json={"password": "NewPassword456!"}
        )

        # Login with new password should work
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "NewPassword456!"},
        )
        assert response.status_code == 200

        # Login with old password should fail
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 401

    def test_reset_password_with_invalid_token(self, client, app, multi_user_mode):
        """Test resetting password with invalid token fails."""
        response = client.post(
            "/api/auth/password-reset/invalid-token-123",
            json={"password": "NewPassword456!"},
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.get_json()["message"]

    def test_reset_password_with_weak_password(
        self, client, app, test_user, multi_user_mode
    ):
        """Test resetting password with weak password fails."""
        # Request reset
        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )
        token = response.get_json()["token"]

        # Try weak password
        response = client.post(
            f"/api/auth/password-reset/{token}", json={"password": "weak"}
        )

        assert response.status_code == 400
        assert "at least 8 characters" in response.get_json()["message"]

    def test_reset_password_without_password_fails(
        self, client, app, test_user, multi_user_mode
    ):
        """Test resetting password without providing password fails."""
        # Request reset
        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )
        token = response.get_json()["token"]

        # Try without password
        response = client.post(f"/api/auth/password-reset/{token}", json={})

        assert response.status_code == 400
        assert "Password required" in response.get_json()["message"]

    def test_token_can_only_be_used_once(self, client, app, test_user, multi_user_mode):
        """Test reset token becomes invalid after use."""
        # Request reset
        response = client.post(
            "/api/auth/password-reset", json={"email": "test@example.com"}
        )
        token = response.get_json()["token"]

        # Use token once
        client.post(
            f"/api/auth/password-reset/{token}", json={"password": "NewPassword456!"}
        )

        # Try to use again
        response = client.post(
            f"/api/auth/password-reset/{token}",
            json={"password": "AnotherPassword789!"},
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.get_json()["message"]

    def test_reset_password_in_single_user_mode_fails(self, client, app, test_user):
        """Test password reset completion is disabled in single-user mode."""
        with app.app_context():
            DeploymentService.set_mode("single-user")

        response = client.post(
            "/api/auth/password-reset/some-token", json={"password": "NewPassword456!"}
        )

        assert response.status_code == 400
        assert "disabled in single-user mode" in response.get_json()["message"]


class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_when_logged_in(
        self, client, app, test_user, multi_user_mode
    ):
        """Test getting current user information when logged in."""
        with client:
            # Login
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "TestPass123!"},
            )
            assert response.status_code == 200

            # Get current user
            response = client.get("/api/auth/user")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["user"]["email"] == "test@example.com"
            assert "password_hash" not in data["user"]  # Should not expose password

    def test_get_current_user_when_not_logged_in(self, client, app, multi_user_mode):
        """Test getting current user when not logged in fails."""
        response = client.get("/api/auth/user")
        assert response.status_code in [
            302,
            401,
        ]  # 302 redirect or 401 unauthorized both valid


class TestRegistration:
    """Test user registration endpoint (admin-only in multi-user mode)."""

    def test_register_new_user(self, client, app, admin_user, multi_user_mode):
        """Test registering a new user as admin."""
        # Login as admin first - registration requires admin privileges
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
        )
        assert login_response.status_code == 200

        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "NewUserPass123!",
                "display_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["email"] == "newuser@example.com"
        assert "password_hash" not in data["user"]

    def test_register_with_duplicate_email_fails(
        self, client, app, test_user, admin_user, multi_user_mode
    ):
        """Test registering with existing email fails."""
        # Login as admin first
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
        )
        assert login_response.status_code == 200

        response = client.post(
            "/api/auth/register",
            json={
                "email": "testuser@example.com",  # Already exists (test_user)
                "password": "Password123!",
                "display_name": "Duplicate User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.get_json()["message"]

    def test_register_with_weak_password_fails(self, client, app, admin_user, multi_user_mode):
        """Test registering with weak password fails."""
        # Login as admin first
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
        )
        assert login_response.status_code == 200

        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "weak",
                "display_name": "New User",
            },
        )

        assert response.status_code == 400
        # Should fail validation
        assert "message" in response.get_json()

    def test_register_without_email_fails(self, client, app, admin_user, multi_user_mode):
        """Test registering without email fails."""
        # Login as admin first
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
        )
        assert login_response.status_code == 200

        response = client.post(
            "/api/auth/register",
            json={"password": "Password123!", "display_name": "New User"},
        )

        assert response.status_code == 400
        assert "Email and password required" in response.get_json()["message"]

    def test_register_in_single_user_mode_fails(self, client, app):
        """Test registration is disabled in single-user mode."""
        with app.app_context():
            DeploymentService.set_mode("single-user")

        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "Password123!",
                "display_name": "New User",
            },
        )

        assert response.status_code == 400
        assert "disabled in single-user mode" in response.get_json()["message"]
