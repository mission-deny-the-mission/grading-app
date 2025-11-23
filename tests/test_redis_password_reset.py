"""
Redis Password Reset Token Tests

Tests for password reset token storage in Redis (multi-worker safe).
Ensures tokens are properly stored, validated, and expired in Redis.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from services.auth_service import AuthService


class TestRedisPasswordResetTokens:
    """Test password reset tokens are stored in Redis, not in-memory."""

    @patch('services.auth_service.get_redis_client')
    def test_password_reset_token_stored_in_redis(self, mock_get_redis, test_user):
        """Test that password reset tokens are stored in Redis."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Generate token
        result = AuthService.generate_password_reset_token(test_user.email)

        # Verify Redis setex was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args

        # Check token key format
        assert call_args[0][0].startswith('password_reset:')

        # Check expiration is 3600 seconds (1 hour)
        assert call_args[0][1] == 3600

        # Check token data contains user info
        assert test_user.id in call_args[0][2]
        assert test_user.email in call_args[0][2]

    @patch('services.auth_service.get_redis_client')
    def test_password_reset_token_validation_from_redis(self, mock_get_redis, test_user):
        """Test that token validation reads from Redis."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.get.return_value = f'{{"user_id": "{test_user.id}", "email": "{test_user.email}", "expires_at": "2099-12-31T23:59:59+00:00"}}'
        mock_get_redis.return_value = mock_redis

        # Validate token
        token_data = AuthService.validate_reset_token('test_token_12345')

        # Verify Redis get was called
        mock_redis.get.assert_called_once_with('password_reset:test_token_12345')

        # Check returned data
        assert token_data['valid'] is True
        assert token_data['user_id'] == test_user.id
        assert token_data['email'] == test_user.email

    @patch('services.auth_service.get_redis_client')
    def test_password_reset_token_invalidation_after_use(self, mock_get_redis, test_user):
        """Test that tokens are deleted from Redis after password reset."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.get.return_value = f'{{"user_id": "{test_user.id}", "email": "{test_user.email}", "expires_at": "2099-12-31T23:59:59+00:00"}}'
        mock_get_redis.return_value = mock_redis

        # Reset password with token
        AuthService.reset_password_with_token('test_token_12345', 'NewPass123!')

        # Verify Redis delete was called
        mock_redis.delete.assert_called_once_with('password_reset:test_token_12345')

    @patch('services.auth_service.get_redis_client')
    def test_password_reset_handles_redis_connection_failure(self, mock_get_redis, test_user):
        """Test graceful handling of Redis connection failures."""
        # Mock Redis to raise connection error
        import redis
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = redis.RedisError("Connection failed")
        mock_get_redis.return_value = mock_redis

        # Should raise ValueError with helpful message
        with pytest.raises(ValueError, match="Failed to generate password reset token"):
            AuthService.generate_password_reset_token(test_user.email)

    @patch('services.auth_service.get_redis_client')
    def test_password_reset_multi_worker_compatibility(self, mock_get_redis, test_user):
        """Test that tokens work across multiple workers (via Redis)."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Generate token in "worker 1"
        AuthService.generate_password_reset_token(test_user.email)

        # Simulate reading from "worker 2" (different process/memory space)
        mock_redis.get.return_value = f'{{"user_id": "{test_user.id}", "email": "{test_user.email}", "expires_at": "2099-12-31T23:59:59+00:00"}}'

        # Token should be retrievable (not in-memory only)
        token_data = AuthService.validate_reset_token('test_token_12345')
        assert token_data['valid'] is True

    @patch('services.auth_service.get_redis_client')
    def test_redis_ttl_automatic_expiration(self, mock_get_redis, test_user):
        """Test that Redis TTL automatically expires old tokens."""
        # Mock Redis client returning None (expired token)
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        # Should raise ValueError for expired/missing token
        with pytest.raises(ValueError, match="Invalid or expired reset token"):
            AuthService.validate_reset_token('expired_token_12345')

    def test_no_in_memory_token_storage(self):
        """Test that tokens are NOT stored in class variables (_reset_tokens)."""
        # Ensure the old in-memory storage pattern is removed
        assert not hasattr(AuthService, '_reset_tokens'), \
            "Password reset tokens should not use in-memory storage (_reset_tokens)"
