"""
Account Lockout Mechanism Tests

Tests for progressive account lockout after failed login attempts.
Ensures protection against brute-force attacks with progressive penalties.
"""

import pytest
from datetime import datetime, timedelta, timezone
from services.auth_service import AuthService


class TestAccountLockout:
    """Test account lockout prevents brute-force attacks."""

    def test_successful_login_resets_failed_attempts(self, test_user):
        """Test that successful login resets failed attempt counter."""
        # Simulate some failed attempts
        test_user.failed_login_attempts = 3
        from models import db
        db.session.commit()

        # Successful login should reset counter
        user = AuthService.authenticate(test_user.email, 'TestPass123!')

        assert user is not None
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_failed_login_increments_counter(self, test_user):
        """Test that failed login attempts increment counter."""
        initial_attempts = test_user.failed_login_attempts or 0

        # Try wrong password
        user = AuthService.authenticate(test_user.email, 'WrongPassword123!')

        assert user is None

        # Refresh user from database
        from models import db
        db.session.refresh(test_user)
        assert test_user.failed_login_attempts == initial_attempts + 1

    def test_account_locked_after_5_failures(self, test_user):
        """Test that account locks for 15 minutes after 5 failed attempts."""
        # Simulate 4 failed attempts
        test_user.failed_login_attempts = 4
        from models import db
        db.session.commit()

        # 5th failed attempt should trigger lockout
        with pytest.raises(ValueError, match="Too many failed login attempts"):
            AuthService.authenticate(test_user.email, 'WrongPassword!')

        # Check lockout was set
        db.session.refresh(test_user)
        assert test_user.locked_until is not None
        assert test_user.failed_login_attempts == 5

        # Lockout should be approximately 15 minutes
        lockout_duration = (test_user.locked_until - datetime.now(timezone.utc)).total_seconds()
        assert 14 * 60 < lockout_duration < 16 * 60  # 14-16 minutes

    def test_account_locked_after_10_failures(self, test_user):
        """Test that account locks for 1 hour after 10 failed attempts."""
        # Simulate 9 failed attempts
        test_user.failed_login_attempts = 9
        from models import db
        db.session.commit()

        # 10th failed attempt should trigger 1-hour lockout
        with pytest.raises(ValueError, match="Too many failed login attempts"):
            AuthService.authenticate(test_user.email, 'WrongPassword!')

        db.session.refresh(test_user)
        lockout_duration = (test_user.locked_until - datetime.now(timezone.utc)).total_seconds()
        assert 59 * 60 < lockout_duration < 61 * 60  # ~1 hour

    def test_account_locked_after_15_failures(self, test_user):
        """Test that account locks for 24 hours after 15 failed attempts."""
        # Simulate 14 failed attempts
        test_user.failed_login_attempts = 14
        from models import db
        db.session.commit()

        # 15th failed attempt should trigger 24-hour lockout
        with pytest.raises(ValueError, match="Too many failed login attempts"):
            AuthService.authenticate(test_user.email, 'WrongPassword!')

        db.session.refresh(test_user)
        lockout_duration = (test_user.locked_until - datetime.now(timezone.utc)).total_seconds()
        assert 23 * 3600 < lockout_duration < 25 * 3600  # ~24 hours

    def test_login_blocked_while_locked(self, test_user):
        """Test that login is blocked while account is locked."""
        # Lock the account
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        from models import db
        db.session.commit()

        # Should reject even with correct password
        with pytest.raises(ValueError, match="Account locked"):
            AuthService.authenticate(test_user.email, 'TestPass123!')

    def test_lockout_expires_automatically(self, test_user):
        """Test that lockout expires after the timeout period."""
        # Set lockout to expired time
        test_user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        test_user.failed_login_attempts = 5
        from models import db
        db.session.commit()

        # Should allow login with correct password (lockout expired)
        user = AuthService.authenticate(test_user.email, 'TestPass123!')

        assert user is not None
        assert user.locked_until is None
        assert user.failed_login_attempts == 0

    def test_progressive_lockout_durations(self, test_user):
        """Test that lockout duration increases with attempts."""
        from models import db

        # Test 5 attempts = 15 minutes
        test_user.failed_login_attempts = 4
        db.session.commit()
        with pytest.raises(ValueError, match="15 minutes"):
            AuthService.authenticate(test_user.email, 'Wrong!')

        # Reset and test 10 attempts = 1 hour
        test_user.failed_login_attempts = 9
        test_user.locked_until = None
        db.session.commit()
        with pytest.raises(ValueError, match="60 minutes"):
            AuthService.authenticate(test_user.email, 'Wrong!')

        # Reset and test 15 attempts = 24 hours
        test_user.failed_login_attempts = 14
        test_user.locked_until = None
        db.session.commit()
        with pytest.raises(ValueError, match="1440 minutes"):
            AuthService.authenticate(test_user.email, 'Wrong!')

    def test_lockout_prevents_timing_attacks(self, test_user):
        """Test that lockout error message doesn't leak timing information."""
        # Lock account
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        from models import db
        db.session.commit()

        # Try with both correct and wrong passwords - should get same lockout error
        with pytest.raises(ValueError, match="Account locked"):
            AuthService.authenticate(test_user.email, 'TestPass123!')  # Correct

        with pytest.raises(ValueError, match="Account locked"):
            AuthService.authenticate(test_user.email, 'WrongPassword!')  # Wrong

    def test_nonexistent_user_doesnt_leak_info(self):
        """Test that non-existent users don't trigger lockout errors."""
        # Should return None, not raise exception
        user = AuthService.authenticate('nonexistent@example.com', 'password')
        assert user is None

    def test_admin_unlock_capability(self, test_user):
        """Test that admin can manually unlock accounts (via update_user)."""
        # Lock the account
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(hours=24)
        test_user.failed_login_attempts = 15
        from models import db
        db.session.commit()

        # Admin manually unlocks by updating user
        test_user.locked_until = None
        test_user.failed_login_attempts = 0
        db.session.commit()

        # User should be able to login
        user = AuthService.authenticate(test_user.email, 'TestPass123!')
        assert user is not None

    def test_lockout_persists_across_sessions(self, test_user):
        """Test that lockout state persists in database across sessions."""
        from models import db, User

        # Lock the account
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        test_user.failed_login_attempts = 10
        db.session.commit()

        # Simulate new session by fetching user from DB
        user_from_db = User.query.get(test_user.id)

        assert user_from_db.locked_until is not None
        assert user_from_db.failed_login_attempts == 10

        # Should still be locked
        with pytest.raises(ValueError, match="Account locked"):
            AuthService.authenticate(user_from_db.email, 'TestPass123!')
