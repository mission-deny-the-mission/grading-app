"""
Permission Enforcement Middleware

Provides decorators for protecting routes with permission checks.
Implements T122-T123: Permission enforcement for scheme routes.
"""

from functools import wraps
from flask import jsonify, session
from services.permission_checker import PermissionChecker
from services.deployment_service import DeploymentService


def get_current_user_id():
    """
    Get current user ID from session.

    In tests, this uses session['user_id'].
    In production with flask-login, would use current_user.id.
    """
    try:
        from flask_login import current_user
        if hasattr(current_user, 'id') and current_user.id:
            return current_user.id
    except (ImportError, AttributeError):
        pass

    # Fallback to session for testing
    return session.get('user_id')


def require_scheme_permission(required_permission):
    """
    Decorator to require specific permission level for scheme access.

    Usage:
        @require_scheme_permission('VIEW_ONLY')
        def get_scheme(scheme_id):
            ...

        @require_scheme_permission('EDITABLE')
        def update_scheme(scheme_id):
            ...

    Args:
        required_permission: Permission level required (VIEW_ONLY, EDITABLE, COPY)

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In single-user mode, skip permission checks
            if DeploymentService.is_single_user_mode():
                return f(*args, **kwargs)

            # Get current user
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"error": "Authentication required"}), 401

            # Extract scheme_id from kwargs or args
            scheme_id = kwargs.get('scheme_id')
            if not scheme_id and len(args) > 0:
                scheme_id = args[0]

            if not scheme_id:
                return jsonify({"error": "Scheme ID is required"}), 400

            # Check if user is owner (owners have all permissions)
            if PermissionChecker.is_owner(current_user_id, scheme_id):
                return f(*args, **kwargs)

            # Check if user has required permission
            has_permission = False
            if required_permission == 'VIEW_ONLY':
                has_permission = PermissionChecker.can_view_scheme(current_user_id, scheme_id)
            elif required_permission == 'EDITABLE':
                has_permission = PermissionChecker.can_edit_scheme(current_user_id, scheme_id)
            elif required_permission == 'COPY':
                has_permission = PermissionChecker.can_copy_scheme(current_user_id, scheme_id)
            else:
                # Generic permission check
                has_permission = PermissionChecker.has_permission(
                    current_user_id, scheme_id, required_permission
                )

            if not has_permission:
                return jsonify({
                    "error": f"Permission denied. Required permission: {required_permission}"
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_scheme_owner():
    """
    Decorator to require user to be scheme owner.

    Usage:
        @require_scheme_owner()
        def delete_scheme(scheme_id):
            ...

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In single-user mode, skip owner checks
            if DeploymentService.is_single_user_mode():
                return f(*args, **kwargs)

            # Get current user
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"error": "Authentication required"}), 401

            # Extract scheme_id from kwargs or args
            scheme_id = kwargs.get('scheme_id')
            if not scheme_id and len(args) > 0:
                scheme_id = args[0]

            if not scheme_id:
                return jsonify({"error": "Scheme ID is required"}), 400

            # Check if user is owner
            if not PermissionChecker.is_owner(current_user_id, scheme_id):
                return jsonify({"error": "Only scheme owner can perform this action"}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator
