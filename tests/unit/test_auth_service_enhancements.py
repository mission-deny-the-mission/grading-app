"""Unit tests for enhanced authentication service functionality."""

import os
from datetime import datetime, timedelta, timezone

import pytest

# Set TESTING environment variable before importing app
os.environ["TESTING"] = "True"

from services.auth_service import AuthService


class TestPasswordComplexity:
    """Test password complexity validation."""

    def test_password_meets_all_requirements(self):
        """Test password with all requirements passes validation."""
        # Valid password: 8+ chars, 1 uppercase, 1 number, 1 special
        valid_password = "MyPass123!"
        assert AuthService.validate_password(valid_password) is True

    def test_password_too_short(self):
        """Test password less than 8 characters fails."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            AuthService.validate_password("Pass1!")

    def test_password_missing_uppercase(self):
        """Test password without uppercase letter fails."""
        with pytest.raises(ValueError, match="at least 1 uppercase letter"):
            AuthService.validate_password("password123!")

    def test_password_missing_number(self):
        """Test password without number fails."""
        with pytest.raises(ValueError, match="at least 1 number"):
            AuthService.validate_password("Password!")

    def test_password_missing_special_char(self):
        """Test password without special character fails."""
        with pytest.raises(ValueError, match="at least 1 special character"):
            AuthService.validate_password("Password123")

    def test_password_validation_can_be_disabled(self):
        """Test password complexity check can be disabled for testing."""
        # Weak password should pass when complexity check is disabled
        weak_password = "password"
        assert AuthService.validate_password(weak_password, check_complexity=False) is True

    def test_password_with_multiple_special_chars(self):
        """Test password with various special characters."""
        passwords = [
            "MyPass123!",
            "MyPass123@",
            "MyPass123#",
            "MyPass123$",
            "MyPass123%",
            "MyPass123^",
            "MyPass123&",
            "MyPass123*",
            "MyPass123(",
            "MyPass123)",
        ]
        for password in passwords:
            assert AuthService.validate_password(password) is True

    def test_password_empty_string(self):
        """Test empty password fails."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            AuthService.validate_password("")

    def test_password_none(self):
        """Test None password fails."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            AuthService.validate_password(None)


class TestPasswordResetTokenGeneration:
    """Test password reset token generation."""

    def test_generate_reset_token_for_valid_user(self, app):
        """Test generating reset token for existing user."""
        with app.app_context():
            # Create a user
            user = AuthService.create_user("test@example.com", "Password123!", "Test User")

            # Generate reset token
            result = AuthService.generate_password_reset_token("test@example.com")

            assert "token" in result
            assert "expires_at" in result
            assert "user_id" in result
            assert result["user_id"] == user.id
            assert len(result["token"]) > 20  # Token should be reasonably long

    def test_generate_reset_token_for_nonexistent_user(self, app):
        """Test generating reset token for non-existent user returns error."""
        with app.app_context():
            with pytest.raises(ValueError, match="reset link has been sent"):
                AuthService.generate_password_reset_token("nonexistent@example.com")

    def test_reset_token_expires_after_one_hour(self, app):
        """Test reset token expiration time is 1 hour."""
        with app.app_context():
            # Create a user
            AuthService.create_user("test@example.com", "Password123!", "Test User")

            # Generate reset token
            result = AuthService.generate_password_reset_token("test@example.com")

            # Parse expiration time
            expires_at = datetime.fromisoformat(result["expires_at"])
            now = datetime.now(timezone.utc)

            # Should expire approximately 1 hour from now (allow 5 second variance)
            time_diff = (expires_at - now).total_seconds()
            assert 3595 <= time_diff <= 3605  # ~1 hour

    def test_multiple_reset_tokens_for_same_user(self, app):
        """Test generating multiple reset tokens replaces previous ones."""
        with app.app_context():
            # Create a user
            AuthService.create_user("test@example.com", "Password123!", "Test User")

            # Generate first token
            result1 = AuthService.generate_password_reset_token("test@example.com")
            token1 = result1["token"]

            # Generate second token
            result2 = AuthService.generate_password_reset_token("test@example.com")
            token2 = result2["token"]

            # Tokens should be different
            assert token1 != token2


class TestPasswordResetValidation:
    """Test password reset token validation."""

    def test_validate_valid_token(self, app):
        """Test validating a valid reset token."""
        with app.app_context():
            # Create user and token
            user = AuthService.create_user("test@example.com", "Password123!", "Test User")
            result = AuthService.generate_password_reset_token("test@example.com")
            token = result["token"]

            # Validate token
            validation = AuthService.validate_reset_token(token)

            assert validation["valid"] is True
            assert validation["user_id"] == user.id
            assert validation["email"] == "test@example.com"

    def test_validate_invalid_token(self, app):
        """Test validating an invalid token fails."""
        with app.app_context():
            with pytest.raises(ValueError, match="Invalid or expired"):
                AuthService.validate_reset_token("invalid-token-123")

    def test_validate_expired_token(self, app):
        """Test validating an expired token fails."""
        with app.app_context():
            # Create user and token
            AuthService.create_user("test@example.com", "Password123!", "Test User")
            result = AuthService.generate_password_reset_token("test@example.com")
            token = result["token"]

            # Manually expire the token
            if hasattr(AuthService, '_reset_tokens'):
                AuthService._reset_tokens[token]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=2)

            # Validation should fail
            with pytest.raises(ValueError, match="expired"):
                AuthService.validate_reset_token(token)


class TestPasswordResetWithToken:
    """Test password reset using token."""

    def test_reset_password_with_valid_token(self, app):
        """Test resetting password with valid token."""
        with app.app_context():
            # Create user
            user = AuthService.create_user("test@example.com", "OldPassword123!", "Test User")
            old_hash = user.password_hash

            # Generate token
            result = AuthService.generate_password_reset_token("test@example.com")
            token = result["token"]

            # Reset password
            updated_user = AuthService.reset_password_with_token(token, "NewPassword456!")

            assert updated_user.id == user.id
            assert updated_user.password_hash != old_hash

            # Old password should not work
            assert not AuthService.verify_password("OldPassword123!", updated_user.password_hash)

            # New password should work
            assert AuthService.verify_password("NewPassword456!", updated_user.password_hash)

    def test_reset_password_invalidates_token(self, app):
        """Test that using a token invalidates it."""
        with app.app_context():
            # Create user and token
            AuthService.create_user("test@example.com", "Password123!", "Test User")
            result = AuthService.generate_password_reset_token("test@example.com")
            token = result["token"]

            # Use token to reset password
            AuthService.reset_password_with_token(token, "NewPassword456!")

            # Token should now be invalid
            with pytest.raises(ValueError, match="Invalid or expired"):
                AuthService.validate_reset_token(token)

    def test_reset_password_with_weak_password_fails(self, app):
        """Test resetting password with weak password fails."""
        with app.app_context():
            # Create user and token
            AuthService.create_user("test@example.com", "Password123!", "Test User")
            result = AuthService.generate_password_reset_token("test@example.com")
            token = result["token"]

            # Try to reset with weak password
            with pytest.raises(ValueError, match="at least 1 uppercase"):
                AuthService.reset_password_with_token(token, "weakpassword")

    def test_reset_password_with_invalid_token_fails(self, app):
        """Test resetting password with invalid token fails."""
        with app.app_context():
            with pytest.raises(ValueError, match="Invalid or expired"):
                AuthService.reset_password_with_token("invalid-token", "NewPassword456!")

    def test_authentication_works_after_password_reset(self, app):
        """Test user can authenticate with new password after reset."""
        with app.app_context():
            # Create user
            AuthService.create_user("test@example.com", "OldPassword123!", "Test User")

            # Reset password
            result = AuthService.generate_password_reset_token("test@example.com")
            token = result["token"]
            AuthService.reset_password_with_token(token, "NewPassword456!")

            # Authentication should work with new password
            user = AuthService.authenticate("test@example.com", "NewPassword456!")
            assert user is not None
            assert user.email == "test@example.com"

            # Authentication should fail with old password
            user = AuthService.authenticate("test@example.com", "OldPassword123!")
            assert user is None
