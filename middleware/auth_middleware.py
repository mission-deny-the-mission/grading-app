"""Authentication middleware for enforcing login based on deployment mode."""

import logging
from functools import wraps

from flask import redirect, request, session, url_for
from flask_login import current_user

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


def init_auth_middleware(app):
    """Initialize authentication middleware for the Flask application."""

    @app.before_request
    def before_request():
        """Execute authentication checks before each request."""
        # Skip auth checks for static files and auth blueprint
        if request.path.startswith("/static") or request.endpoint.startswith("auth."):
            return

        # In single-user mode, skip all authentication
        if DeploymentService.is_single_user_mode():
            logger.debug("Single-user mode: skipping authentication")
            return

        # In multi-user mode, user must be logged in
        if not current_user.is_authenticated:
            # Allow some public routes without login
            public_routes = {
                "auth.login",
                "auth.register",
                "main.index",
                "main.setup",
            }

            if request.endpoint not in public_routes:
                logger.warning(f"Unauthenticated request to {request.endpoint}: {request.path}")
                return redirect(url_for("auth.login", next=request.url))

        logger.debug(f"User {current_user.email if current_user.is_authenticated else 'anonymous'} accessing {request.path}")

    @app.after_request
    def after_request(response):
        """Execute after each request."""
        # Ensure secure cookies in production
        # This will be enforced at Flask config level
        return response
