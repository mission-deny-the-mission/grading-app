"""Unit tests for authentication service."""

import pytest

from models import User, db
from services.auth_service import AuthService


class TestAuthServiceCreateUser:
    """Test user creation."""

    def test_create_user_success(self, app):
        """Test successful user creation."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "password123", "Test User")

            assert user.email == "test@example.com"
            assert user.display_name == "Test User"
            assert user.is_active
            assert not user.is_admin
            assert user.password_hash is not None
            assert user.password_hash != "password123"

    def test_create_user_duplicate_email(self, app):
        """Test creation fails with duplicate email."""
        with app.app_context():
            AuthService.create_user("test@example.com", "password123")

            with pytest.raises(ValueError, match="already registered"):
                AuthService.create_user("test@example.com", "otherpassword")

    def test_create_user_invalid_email(self, app):
        """Test creation fails with invalid email."""
        with app.app_context():
            with pytest.raises(ValueError, match="Invalid email"):
                AuthService.create_user("notanemail", "password123")

    def test_create_user_weak_password(self, app):
        """Test creation fails with weak password."""
        with app.app_context():
            with pytest.raises(ValueError, match="at least 8 characters"):
                AuthService.create_user("test@example.com", "weak")

    def test_create_user_admin_flag(self, app):
        """Test creating admin user."""
        with app.app_context():
            user = AuthService.create_user("admin@example.com", "password123", is_admin=True)

            assert user.is_admin


class TestAuthServicePassword:
    """Test password verification."""

    def test_verify_password_correct(self, app):
        """Test correct password verification."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "password123")

            assert AuthService.verify_password("password123", user.password_hash)

    def test_verify_password_incorrect(self, app):
        """Test incorrect password fails."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "password123")

            assert not AuthService.verify_password("wrongpassword", user.password_hash)


class TestAuthServiceAuthenticate:
    """Test authentication."""

    def test_authenticate_success(self, app):
        """Test successful authentication."""
        with app.app_context():
            AuthService.create_user("test@example.com", "password123")

            user = AuthService.authenticate("test@example.com", "password123")

            assert user is not None
            assert user.email == "test@example.com"

    def test_authenticate_wrong_password(self, app):
        """Test authentication fails with wrong password."""
        with app.app_context():
            AuthService.create_user("test@example.com", "password123")

            user = AuthService.authenticate("test@example.com", "wrongpassword")

            assert user is None

    def test_authenticate_nonexistent_user(self, app):
        """Test authentication fails for nonexistent user."""
        with app.app_context():
            user = AuthService.authenticate("nonexistent@example.com", "password123")

            assert user is None

    def test_authenticate_inactive_user(self, app):
        """Test authentication fails for inactive user."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "password123")
            user.is_active = False
            db.session.commit()

            authenticated_user = AuthService.authenticate("test@example.com", "password123")

            assert authenticated_user is None


class TestAuthServiceGetUser:
    """Test user retrieval."""

    def test_get_user_by_email(self, app):
        """Test getting user by email."""
        with app.app_context():
            created_user = AuthService.create_user("test@example.com", "password123")

            user = AuthService.get_user_by_email("test@example.com")

            assert user is not None
            assert user.id == created_user.id

    def test_get_user_by_id(self, app):
        """Test getting user by ID."""
        with app.app_context():
            created_user = AuthService.create_user("test@example.com", "password123")

            user = AuthService.get_user_by_id(created_user.id)

            assert user is not None
            assert user.email == "test@example.com"

    def test_get_nonexistent_user(self, app):
        """Test getting nonexistent user returns None."""
        with app.app_context():
            user = AuthService.get_user_by_email("nonexistent@example.com")

            assert user is None


class TestAuthServiceUpdateUser:
    """Test user updates."""

    def test_update_user_display_name(self, app):
        """Test updating user display name."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "password123")

            updated = AuthService.update_user(user.id, display_name="New Name")

            assert updated.display_name == "New Name"

    def test_update_user_password(self, app):
        """Test updating user password."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "oldpassword")

            AuthService.update_user(user.id, password="newpassword123")

            # Verify new password works
            authenticated = AuthService.authenticate("test@example.com", "newpassword123")
            assert authenticated is not None

            # Verify old password fails
            authenticated = AuthService.authenticate("test@example.com", "oldpassword")
            assert authenticated is None

    def test_update_user_email(self, app):
        """Test updating user email."""
        with app.app_context():
            user = AuthService.create_user("test@example.com", "password123")

            updated = AuthService.update_user(user.id, email="newemail@example.com")

            assert updated.email == "newemail@example.com"


class TestAuthServiceListUsers:
    """Test user listing."""

    def test_list_users(self, app):
        """Test listing users."""
        with app.app_context():
            AuthService.create_user("user1@example.com", "password123")
            AuthService.create_user("user2@example.com", "password123")
            AuthService.create_user("user3@example.com", "password123")

            result = AuthService.list_users(limit=10)

            assert result["total"] == 3
            assert len(result["users"]) == 3

    def test_list_users_pagination(self, app):
        """Test user listing with pagination."""
        with app.app_context():
            for i in range(10):
                AuthService.create_user(f"user{i}@example.com", "password123")

            result = AuthService.list_users(limit=5, offset=0)

            assert result["total"] == 10
            assert len(result["users"]) == 5
            assert result["limit"] == 5
            assert result["offset"] == 0


@pytest.fixture
def app():
    """Create Flask app for testing."""
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
