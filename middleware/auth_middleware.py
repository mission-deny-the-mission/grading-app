"""Authentication middleware for enforcing login based on deployment mode."""

import logging
from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from flask_login import current_user, logout_user

from services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)


def require_login(f):
    """Decorator to require login for a route (only enforced in multi-user mode)."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In single-user mode, skip authentication entirely
        if DeploymentService.is_single_user_mode():
            return f(*args, **kwargs)

        # In multi-user mode, require login
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))

        return f(*args, **kwargs)

    return decorated_function


def _validate_session_timeout():
    """Validate session timeout (absolute and idle timeout).

    Returns:
        bool: True if session is valid, False if expired
    """
    if not current_user.is_authenticated:
        return True  # No session to validate

    # Get PERMANENT_SESSION_LIFETIME from session-specific override or app config
    from flask import current_app
    max_lifetime = None

    # First check if session has a permanent_session_lifetime attribute
    if hasattr(session, 'permanent_session_lifetime') and session.permanent_session_lifetime is not None:
        max_lifetime = session.permanent_session_lifetime
    # Fall back to session dict key
    elif 'permanent_session_lifetime' in session:
        max_lifetime = session.get('permanent_session_lifetime')
    # Fall back to app config
    else:
        max_lifetime = current_app.config.get('PERMANENT_SESSION_LIFETIME', 1800)

    # Convert to seconds if it's a timedelta
    if hasattr(max_lifetime, 'total_seconds'):
        max_lifetime = int(max_lifetime.total_seconds())

    # Check absolute timeout (session created time)
    if '_session_created_at' in session:
        try:
            created_at = datetime.fromisoformat(session['_session_created_at'])
            now = datetime.now(timezone.utc)

            # Check if session has exceeded absolute timeout
            age = (now - created_at).total_seconds()
            if age > max_lifetime:
                logger.warning(f"Session expired (absolute timeout): {age}s > {max_lifetime}s")
                return False
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid session created_at timestamp: {e}")
            return False

    # Check idle timeout (last activity time)
    if '_last_activity' in session:
        try:
            last_activity = datetime.fromisoformat(session['_last_activity'])
            now = datetime.now(timezone.utc)

            # Check if session has been idle for too long
            idle_time = (now - last_activity).total_seconds()
            if idle_time > max_lifetime:
                logger.warning(f"Session expired (idle timeout): {idle_time}s > {max_lifetime}s")
                return False

            # Update last activity timestamp
            session['_last_activity'] = now.isoformat()
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid session last_activity timestamp: {e}")
            # Initialize if missing
            session['_last_activity'] = datetime.now(timezone.utc).isoformat()
    else:
        # Initialize last activity if missing
        session['_last_activity'] = datetime.now(timezone.utc).isoformat()

    return True


def _validate_user_status():
    """Validate that user is still active.

    Returns:
        bool: True if user is valid, False if deactivated
    """
    if not current_user.is_authenticated:
        return True  # No user to validate

    # Check if user is still active
    if not current_user.is_active:
        logger.warning(f"User {current_user.email} is deactivated, invalidating session")
        return False

    return True


def _is_api_request():
    """Check if the current request is an API request."""
    return request.path.startswith("/api/")


def init_auth_middleware(app):
    """Initialize authentication middleware for the Flask application."""

    @app.before_request
    def before_request():
        """Execute authentication checks before each request."""
        # Skip auth checks for static files and auth blueprint
        if request.path.startswith("/static") or (request.endpoint and request.endpoint.startswith("auth.")):
            return

        # In single-user mode, skip all authentication
        if DeploymentService.is_single_user_mode():
            logger.debug("Single-user mode: skipping authentication")
            return

        # Validate session timeout and user status for authenticated users
        if current_user.is_authenticated:
            # Check if session has expired
            if not _validate_session_timeout():
                logger.info(f"Session expired for user {current_user.email}")
                logout_user()
                session.clear()

                # For API requests, return JSON error
                if _is_api_request():
                    return jsonify({"error": "Session expired"}), 401
                else:
                    # Redirect to login page
                    login_url = url_for("auth_pages.login_page")
                    return redirect(f"{login_url}?next={request.url}")

            # Check if user is still active
            if not _validate_user_status():
                logger.info(f"User {current_user.email} is no longer active, invalidating session")
                logout_user()
                session.clear()

                # For API requests, return JSON error
                if _is_api_request():
                    return jsonify({"error": "Account deactivated"}), 401
                else:
                    # Redirect to login page
                    login_url = url_for("auth_pages.login_page")
                    return redirect(login_url)

        # In multi-user mode, user must be logged in
        if not current_user.is_authenticated:
            # Allow some public routes without login
            public_routes = {
                "auth.login",
                "auth.register",
                "legacy_auth.login_redirect",
                "legacy_auth.register_redirect",
                "config.get_deployment_mode",  # Allow checking deployment mode
                "config.health_check",  # Allow health checks
                "main.index",
                "main.setup",
            }

            if request.endpoint not in public_routes:
                logger.warning(f"Unauthenticated request to {request.endpoint}: {request.path}")

                # For API requests, return JSON error instead of redirecting
                if _is_api_request():
                    return jsonify({"error": "Unauthorized"}), 401
                else:
                    # Redirect to HTML login page and preserve original destination
                    login_url = url_for("auth_pages.login_page")
                    return redirect(f"{login_url}?next={request.url}")

        logger.debug(f"User {current_user.email if current_user.is_authenticated else 'anonymous'} accessing {request.path}")

    @app.after_request
    def after_request(response):
        """Execute after each request - add security headers."""
        # Content Security Policy - prevent XSS and injection attacks
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # X-Frame-Options - prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # X-Content-Type-Options - prevent MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Strict-Transport-Security (HSTS) - enforce HTTPS
        # Only set in production to avoid localhost issues in development
        import os
        if os.getenv('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Referrer-Policy - control information leakage
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions-Policy - restrict browser features
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=()'
        )

        return response
