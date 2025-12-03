"""Authentication API routes for user login, logout, and session management."""

import logging
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user

from services.auth_service import AuthService
from services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Import limiter from utils to avoid circular imports
from utils.limiter import limiter


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per 15 minutes")
def login():
    """
    Login endpoint for multi-user mode.

    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }

    Response:
        {
            "success": bool,
            "user": {...},
            "message": str
        }
    """
    # Check deployment mode
    if DeploymentService.is_single_user_mode():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Authentication disabled in single-user mode",
                }
            ),
            400,
        )

    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return (
            jsonify({"success": False, "message": "Email and password required"}),
            400,
        )

    try:
        # Authenticate user
        user = AuthService.authenticate(email, password)

        if not user:
            logger.warning(f"Login failed for {email}: invalid credentials")
            return (
                jsonify({"success": False, "message": "Invalid email or password"}),
                401,
            )

        # Session fixation prevention: regenerate session ID on login
        # Flask-Login's login_user() automatically calls session.regenerate() in newer versions,
        # but we'll explicitly clear and set permanent flag for security
        session.clear()
        session.permanent = True

        # Login user with Flask-Login (this will set _user_id in session)
        login_user(user, remember=data.get("remember_me", False))

        # Set session timestamps for timeout tracking
        now = datetime.now(timezone.utc).isoformat()
        session['_session_created_at'] = now
        session['_last_activity'] = now

        logger.info(f"User logged in: {email}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Welcome, {user.display_name or user.email}",
                    "user": user.to_dict(),
                }
            ),
            200,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "message": "Login error"}), 500


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    Logout endpoint.

    Response:
        {
            "success": bool,
            "message": str
        }
    """
    email = current_user.email

    # Clear session data before logout to prevent session reuse
    session.clear()

    # Logout user (Flask-Login)
    logout_user()

    logger.info(f"User logged out: {email}")

    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@auth_bp.route("/session", methods=["GET"])
def get_session():
    """
    Get current session information.

    In single-user mode, returns a dummy session.
    In multi-user mode, returns logged-in user info or 401.

    Response:
        {
            "authenticated": bool,
            "user": {...} or null,
            "mode": str
        }
    """
    mode = DeploymentService.get_current_mode()

    # Single-user mode: always return authenticated (dummy session)
    if mode == "single-user":
        return (
            jsonify(
                {
                    "authenticated": True,
                    "user": {"email": "single-user@localhost", "id": "system"},
                    "mode": "single-user",
                }
            ),
            200,
        )

    # Multi-user mode: check actual authentication
    if current_user.is_authenticated:
        return (
            jsonify(
                {
                    "authenticated": True,
                    "user": current_user.to_dict(),
                    "mode": "multi-user",
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "authenticated": False,
                "user": None,
                "mode": "multi-user",
            }
        ),
        200,
    )


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    """
    Register a new user (admin-only in institutional deployments).

    Request body:
        {
            "email": "user@example.com",
            "password": "password123",
            "display_name": "John Doe",
            "is_admin": false
        }

    Response:
        {
            "success": bool,
            "user": {...},
            "message": str
        }
    """
    # Check deployment mode
    if DeploymentService.is_single_user_mode():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Registration disabled in single-user mode",
                }
            ),
            400,
        )

    # Check admin privilege - only admins can create users
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin only"}), 403

    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    display_name = data.get("display_name")

    if not email or not password:
        return (
            jsonify({"success": False, "message": "Email and password required"}),
            400,
        )

    try:
        user = AuthService.create_user(email, password, display_name)
        logger.info(f"User registered: {email}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"User {email} registered successfully",
                    "user": user.to_dict(),
                }
            ),
            201,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"success": False, "message": "Registration error"}), 500


@auth_bp.route("/password-reset", methods=["POST"])
@limiter.limit("3 per hour")
def request_password_reset():
    """
    Request password reset token.

    Request body:
        {
            "email": "user@example.com"
        }

    Response:
        {
            "success": bool,
            "message": str,
            "token": str (optional),  # Only included when FLASK_ENV != 'production'
            "expires_at": str (optional)  # Only included when FLASK_ENV != 'production'
        }

    Note: In production (FLASK_ENV='production'), the token is sent via email
    and not returned in the response for security.
    """
    # Check deployment mode
    if DeploymentService.is_single_user_mode():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Password reset disabled in single-user mode",
                }
            ),
            400,
        )

    data = request.get_json() or {}
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    try:
        result = AuthService.generate_password_reset_token(email)
        logger.info(f"Password reset requested for {email}")

        # Build response based on environment
        response_data = {
            "success": True,
            "message": "Password reset token generated",
        }

        # Only include token in non-production environments (development/testing)
        # In production, the token should be sent via email instead
        flask_env = os.getenv("FLASK_ENV", "production")
        is_testing = os.getenv("TESTING", "").lower() in ["true", "1", "yes"]

        if flask_env != "production" or is_testing:
            response_data["token"] = result["token"]
            response_data["expires_at"] = result["expires_at"]

        return jsonify(response_data), 200

    except ValueError as e:
        # Return success even if email doesn't exist (security best practice)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "If this email exists, a reset link has been sent",
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return (
            jsonify({"success": False, "message": "Password reset request failed"}),
            500,
        )


@auth_bp.route("/password-reset/<token>", methods=["POST"])
def reset_password(token):
    """
    Reset password using token.

    Request body:
        {
            "password": "newPassword123!"
        }

    Response:
        {
            "success": bool,
            "message": str
        }
    """
    # Check deployment mode
    if DeploymentService.is_single_user_mode():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Password reset disabled in single-user mode",
                }
            ),
            400,
        )

    data = request.get_json() or {}
    password = data.get("password")

    if not password:
        return jsonify({"success": False, "message": "Password required"}), 400

    try:
        user = AuthService.reset_password_with_token(token, password)
        logger.info(f"Password reset successful for {user.email}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Password reset successful",
                }
            ),
            200,
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return jsonify({"success": False, "message": "Password reset failed"}), 500


@auth_bp.route("/user", methods=["GET"])
@login_required
def get_current_user():
    """
    Get current authenticated user information.

    Response:
        {
            "success": bool,
            "user": {...}
        }
    """
    return (
        jsonify(
            {
                "success": True,
                "user": current_user.to_dict(),
            }
        ),
        200,
    )
