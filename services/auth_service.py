"""Authentication service for user management and authentication."""

import logging
import os
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

logger = logging.getLogger(__name__)

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
            check_deliverability = not os.getenv("TESTING", False)

        try:
            valid_email = validate_email(email, check_deliverability=check_deliverability)
            return valid_email.normalized
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email address: {str(e)}")

    @staticmethod
    def validate_password(password):
        """
        Validate password meets requirements.

        Args:
            password: str - Password to validate

        Returns:
            bool: True if valid

        Raises:
            ValueError: If password is invalid
        """
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
        return True

    @staticmethod
    def create_user(email, password, display_name=None, is_admin=False):
        """
        Create a new user account.

        Args:
            email: str - User email (must be unique)
            password: str - User password (will be hashed)
            display_name: str - Optional display name
            is_admin: bool - Whether user is an administrator

        Returns:
            User: Created user object

        Raises:
            ValueError: If email is invalid, password is weak, or email exists
        """
        # Validate inputs
        email = AuthService.validate_email(email)
        AuthService.validate_password(password)

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
        Authenticate user by email and password.

        Args:
            email: str - User email
            password: str - User password

        Returns:
            User: Authenticated user object or None

        Raises:
            ValueError: If email is invalid format
        """
        # Normalize email
        email = AuthService.validate_email(email)

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active:
            logger.warning(f"Authentication failed for {email}: user not found or inactive")
            return None

        # Verify password
        if not AuthService.verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed for {email}: invalid password")
            return None

        logger.info(f"User authenticated: {email}")
        return user

    @staticmethod
    def get_user_by_email(email):
        """Get user by email address."""
        try:
            email = AuthService.validate_email(email)
            return User.query.filter_by(email=email).first()
        except ValueError:
            return None

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
                user.display_name = kwargs["display_name"]
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
