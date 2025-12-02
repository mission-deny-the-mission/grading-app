"""Authentication service for user management and authentication."""

import json
import logging
import os
import secrets
import re
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from werkzeug.security import check_password_hash, generate_password_hash
import redis

from models import User, db

logger = logging.getLogger(__name__)

# Redis connection for password reset tokens (multi-worker safe)
_redis_client = None

def get_redis_client():
    """Get or create Redis client for password reset tokens."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client

# Minimum password length per requirements
MIN_PASSWORD_LENGTH = 8


class AuthService:
    """Service for authentication and user management."""

    @staticmethod
    def validate_email(email, check_deliverability=None):
        """
        Validate email format using email-validator.

        Args:
            email: str - Email address to validate
            check_deliverability: bool - Whether to check if domain can receive email.
                                        Defaults to False if TESTING env var is set, else True

        Returns:
            str: Normalized email address

        Raises:
            ValueError: If email is invalid
        """
        if check_deliverability is None:
            # Disable deliverability checks in test environments
            check_deliverability = not (os.getenv("TESTING", "").lower() in ["true", "1", "yes"])

        try:
            valid_email = validate_email(email, check_deliverability=check_deliverability)
            return valid_email.normalized
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email address: {str(e)}")

    @staticmethod
    def validate_password(password):
        """
        Validate password meets requirements (complexity always enforced for security).

        Password requirements:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 number
        - At least 1 special character

        Args:
            password: str - Password to validate

        Returns:
            bool: True if valid

        Raises:
            ValueError: If password is invalid
        """
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")

        # Check for uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must contain at least 1 uppercase letter")

        # Check for number
        if not re.search(r'\d', password):
            raise ValueError("Password must contain at least 1 number")

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least 1 special character")

        return True

    @staticmethod
    def sanitize_display_name(display_name):
        """
        Sanitize display name to prevent XSS and ensure valid format.

        Args:
            display_name: str - Display name to sanitize

        Returns:
            str: Sanitized display name

        Raises:
            ValueError: If display name is invalid
        """
        if not display_name:
            return None

        # Strip whitespace
        display_name = display_name.strip()

        # Length validation (max 100 chars as per model)
        if len(display_name) > 100:
            raise ValueError("Display name must be 100 characters or less")

        # Remove HTML/script tags and dangerous characters
        import html
        display_name = html.escape(display_name)

        # Allow only alphanumeric, spaces, hyphens, apostrophes, periods
        if not re.match(r"^[a-zA-Z0-9\s\-'.]+$", display_name):
            raise ValueError("Display name contains invalid characters. Use only letters, numbers, spaces, hyphens, apostrophes, and periods.")

        return display_name

    @staticmethod
    def create_user(email, password, display_name=None, is_admin=False):
        """
        Create a new user account with sanitized inputs.

        Args:
            email: str - User email (must be unique)
            password: str - User password (will be hashed)
            display_name: str - Optional display name (will be sanitized)
            is_admin: bool - Whether user is an administrator

        Returns:
            User: Created user object

        Raises:
            ValueError: If email is invalid, password is weak, or email exists
        """
        # Validate inputs
        email = AuthService.validate_email(email)
        AuthService.validate_password(password)
        if display_name:
            display_name = AuthService.sanitize_display_name(display_name)

        # Check for duplicate email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            raise ValueError(f"Email {email} already registered")

        # Hash password
        password_hash = generate_password_hash(password)

        # Create user
        try:
            user = User(
                email=email,
                password_hash=password_hash,
                display_name=display_name,
                is_admin=is_admin,
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"User created: {email}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user {email}: {e}")
            raise

    @staticmethod
    def verify_password(password, password_hash):
        """
        Verify password matches hash.

        Args:
            password: str - Password to verify
            password_hash: str - Hash to verify against

        Returns:
            bool: True if password matches
        """
        return check_password_hash(password_hash, password)

    @staticmethod
    def authenticate(email, password):
        """
        Authenticate user by email and password with account lockout protection.

        Args:
            email: str - User email
            password: str - User password

        Returns:
            User: Authenticated user object or None

        Raises:
            ValueError: If email is invalid format or account is locked
        """
        # Normalize email
        email = AuthService.validate_email(email)

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active:
            logger.warning(f"Authentication failed for {email}: user not found or inactive")
            return None

        # Check if account is locked
        if user.locked_until:
            now = datetime.now(timezone.utc)
            if now < user.locked_until:
                # Account is still locked
                remaining = (user.locked_until - now).total_seconds()
                logger.warning(f"Authentication failed for {email}: account locked for {remaining:.0f}s")
                raise ValueError(f"Account locked. Try again in {int(remaining // 60) + 1} minutes.")
            else:
                # Lockout expired - unlock account
                user.locked_until = None
                user.failed_login_attempts = 0
                db.session.commit()
                logger.info(f"Account lockout expired for {email}")

        # Verify password
        if not AuthService.verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # Progressive lockout: 5 failures = 15 min, 10 failures = 1 hour, 15+ failures = 24 hours
            if user.failed_login_attempts >= 15:
                lockout_duration = timedelta(hours=24)
            elif user.failed_login_attempts >= 10:
                lockout_duration = timedelta(hours=1)
            elif user.failed_login_attempts >= 5:
                lockout_duration = timedelta(minutes=15)
            else:
                lockout_duration = None

            if lockout_duration:
                user.locked_until = datetime.now(timezone.utc) + lockout_duration
                db.session.commit()
                logger.warning(f"Account locked for {email}: {user.failed_login_attempts} failed attempts")
                raise ValueError(f"Too many failed login attempts. Account locked for {int(lockout_duration.total_seconds() // 60)} minutes.")

            db.session.commit()
            logger.warning(f"Authentication failed for {email}: invalid password (attempt {user.failed_login_attempts})")
            return None

        # Successful login - reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()

        logger.info(f"User authenticated: {email}")
        return user

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID."""
        return User.query.get(user_id)

    @staticmethod
    def update_user(user_id, **kwargs):
        """
        Update user properties.

        Args:
            user_id: str - User ID
            **kwargs: Fields to update (email, display_name, password, is_admin, is_active)

        Returns:
            User: Updated user object
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        try:
            # Handle email change (must validate uniqueness)
            if "email" in kwargs:
                new_email = AuthService.validate_email(kwargs["email"])
                existing = User.query.filter_by(email=new_email).first()
                if existing and existing.id != user_id:
                    raise ValueError(f"Email {new_email} already in use")
                user.email = new_email

            # Handle password change
            if "password" in kwargs:
                AuthService.validate_password(kwargs["password"])
                user.password_hash = generate_password_hash(kwargs["password"])

            # Handle other fields
            if "display_name" in kwargs:
                user.display_name = AuthService.sanitize_display_name(kwargs["display_name"])
            if "is_admin" in kwargs:
                user.is_admin = kwargs["is_admin"]
            if "is_active" in kwargs:
                user.is_active = kwargs["is_active"]

            db.session.commit()
            logger.info(f"User updated: {user.email}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise

    @staticmethod
    def delete_user(user_id):
        """
        Delete a user account.

        Args:
            user_id: str - User ID to delete

        Returns:
            bool: True if successful
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        try:
            db.session.delete(user)
            db.session.commit()
            logger.info(f"User deleted: {user.email}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise

    @staticmethod
    def list_users(limit=100, offset=0):
        """
        List all users with pagination.

        Args:
            limit: int - Maximum number of users to return
            offset: int - Number of users to skip

        Returns:
            dict: {"users": list, "total": int, "limit": int, "offset": int}
        """
        total = User.query.count()
        users = User.query.limit(limit).offset(offset).all()

        return {
            "users": [u.to_dict() for u in users],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def generate_password_reset_token(email):
        """
        Generate a password reset token for a user.

        Token is stored in Redis with 1-hour expiration (multi-worker safe).
        In production, this would send an email (not implemented yet).

        Args:
            email: str - User email

        Returns:
            dict: {"token": str, "expires_at": datetime, "user_id": str}

        Raises:
            ValueError: If user not found
        """
        # Normalize email
        email = AuthService.validate_email(email)

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            # For security, don't reveal whether email exists
            logger.warning(f"Password reset requested for non-existent email: {email}")
            raise ValueError("If this email exists, a reset link has been sent")

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Store token in Redis (multi-worker safe)
        try:
            redis_client = get_redis_client()
            token_data = {
                "user_id": user.id,
                "email": email,
                "expires_at": expires_at.isoformat(),
            }
            # Store with 1 hour expiration (3600 seconds)
            redis_client.setex(
                f"password_reset:{token}",
                3600,
                json.dumps(token_data)
            )
        except Exception as e:
            logger.error(f"Error storing password reset token in Redis: {e}")
            raise ValueError("Failed to generate password reset token")

        logger.info(f"Password reset token generated for {email}")

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "user_id": user.id,
            "message": "Password reset token generated (email not sent in current implementation)",
        }

    @staticmethod
    def validate_reset_token(token):
        """
        Validate a password reset token from Redis.

        Args:
            token: str - Reset token

        Returns:
            dict: {"valid": bool, "user_id": str, "email": str}

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            redis_client = get_redis_client()
            token_key = f"password_reset:{token}"

            # Retrieve token data from Redis
            token_json = redis_client.get(token_key)
            if not token_json:
                raise ValueError("Invalid or expired reset token")

            token_data = json.loads(token_json)

            # Redis TTL handles expiration automatically, but double-check
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                redis_client.delete(token_key)
                raise ValueError("Reset token has expired")

            return {
                "valid": True,
                "user_id": token_data["user_id"],
                "email": token_data["email"],
            }
        except redis.RedisError as e:
            logger.error(f"Redis error validating reset token: {e}")
            raise ValueError("Failed to validate reset token")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid token data format: {e}")
            raise ValueError("Invalid reset token format")

    @staticmethod
    def reset_password_with_token(token, new_password):
        """
        Reset password using a valid token from Redis.

        Args:
            token: str - Reset token
            new_password: str - New password

        Returns:
            User: Updated user object

        Raises:
            ValueError: If token is invalid or password doesn't meet requirements
        """
        # Validate token
        token_data = AuthService.validate_reset_token(token)
        user_id = token_data["user_id"]

        # Validate new password
        AuthService.validate_password(new_password)

        # Update password
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        try:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()

            # Invalidate token after use (delete from Redis)
            try:
                redis_client = get_redis_client()
                redis_client.delete(f"password_reset:{token}")
            except redis.RedisError as e:
                logger.warning(f"Failed to delete used reset token from Redis: {e}")

            logger.info(f"Password reset successful for user {user.email}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting password: {e}")
            raise
