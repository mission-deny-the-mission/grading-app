"""
Authorization Decorators

Reusable decorators for common authorization patterns.
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user
from models import Project, GradingJob


def require_admin(f):
    """
    Decorator to require admin privileges.

    Usage:
        @app.route("/admin/users")
        @login_required  # Flask-Login already handles authentication
        @require_admin
        def list_users():
            return {...}

    Returns:
        403 Forbidden if user is not an admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        if not current_user.is_admin:
            return jsonify({"success": False, "error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated_function


def require_ownership(resource_type='project'):
    """
    Decorator factory to require resource ownership.

    Args:
        resource_type: Type of resource ('project', 'job', 'submission')

    Usage:
        @app.route("/api/projects/<project_id>", methods=["DELETE"])
        @login_required
        @require_ownership('project')
        def delete_project(project_id):
            # current_user owns the project
            return {...}

    Returns:
        403 Forbidden if user doesn't own the resource
        404 Not Found if resource doesn't exist
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"success": False, "error": "Authentication required"}), 401

            # Extract resource ID from route parameters
            resource_id = None
            if resource_type == 'project':
                resource_id = kwargs.get('project_id')
            elif resource_type == 'job':
                resource_id = kwargs.get('job_id')
            elif resource_type == 'submission':
                resource_id = kwargs.get('submission_id')

            if not resource_id:
                return jsonify({"success": False, "error": f"{resource_type}_id required"}), 400

            # Check ownership
            if resource_type == 'project':
                resource = Project.query.get(resource_id)
                if not resource:
                    return jsonify({"success": False, "error": "Project not found"}), 404
                if resource.owner_id != current_user.id and not current_user.is_admin:
                    return jsonify({"success": False, "error": "Access denied"}), 403

            elif resource_type == 'job':
                resource = GradingJob.query.get(resource_id)
                if not resource:
                    return jsonify({"success": False, "error": "Job not found"}), 404
                if resource.user_id != current_user.id and not current_user.is_admin:
                    return jsonify({"success": False, "error": "Access denied"}), 403

            # Add more resource types as needed

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_project_access(permission_level='read'):
    """
    Decorator factory to require project access (ownership or sharing).

    Args:
        permission_level: Required permission ('read' or 'write')

    Usage:
        @app.route("/api/projects/<project_id>/submissions", methods=["GET"])
        @login_required
        @require_project_access('read')
        def get_submissions(project_id):
            # User has at least read access to the project
            return {...}

        @app.route("/api/projects/<project_id>/submissions", methods=["POST"])
        @login_required
        @require_project_access('write')
        def create_submission(project_id):
            # User has write access to the project
            return {...}

    Returns:
        403 Forbidden if user doesn't have required access
        404 Not Found if project doesn't exist
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"success": False, "error": "Authentication required"}), 401

            project_id = kwargs.get('project_id')
            if not project_id:
                return jsonify({"success": False, "error": "project_id required"}), 400

            # Check project exists
            project = Project.query.get(project_id)
            if not project:
                return jsonify({"success": False, "error": "Project not found"}), 404

            # Admin always has access
            if current_user.is_admin:
                return f(*args, **kwargs)

            # Owner always has full access
            if project.owner_id == current_user.id:
                return f(*args, **kwargs)

            # Check shared access
            from services.sharing_service import SharingService

            if permission_level == 'read':
                # Read access: check if user can access
                if not SharingService.can_access_project(current_user.id, project_id, project.owner_id):
                    return jsonify({"success": False, "error": "Access denied"}), 403
            elif permission_level == 'write':
                # Write access: check if user can modify
                if not SharingService.can_modify_project(current_user.id, project_id, project.owner_id):
                    return jsonify({"success": False, "error": "Write access required"}), 403
            else:
                return jsonify({"success": False, "error": "Invalid permission level"}), 500

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_single_user_mode(f):
    """
    Decorator to restrict access to single-user mode only.

    Usage:
        @app.route("/api/quick-access")
        @require_single_user_mode
        def quick_access():
            # Only accessible in single-user mode
            return {...}

    Returns:
        403 Forbidden if not in single-user mode
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from services.deployment_service import DeploymentService

        if not DeploymentService.is_single_user_mode():
            return jsonify({"success": False, "error": "Only available in single-user mode"}), 403

        return f(*args, **kwargs)

    return decorated_function


def require_multi_user_mode(f):
    """
    Decorator to restrict access to multi-user mode only.

    Usage:
        @app.route("/admin/users")
        @login_required
        @require_admin
        @require_multi_user_mode
        def admin_users():
            # Only accessible in multi-user mode
            return {...}

    Returns:
        403 Forbidden if in single-user mode
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from services.deployment_service import DeploymentService

        if DeploymentService.is_single_user_mode():
            return jsonify({"success": False, "error": "Not available in single-user mode"}), 403

        return f(*args, **kwargs)

    return decorated_function
