"""Project management API routes for multi-user data isolation."""

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from models import GradingJob, ProjectShare, db
from services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


def check_project_access(project_id, user_id, required_permission="read"):
    """
    Check if user has access to a project.

    Args:
        project_id: ID of the project (GradingJob)
        user_id: ID of the user
        required_permission: "read" or "write"

    Returns:
        tuple: (has_access: bool, project: GradingJob or None, reason: str)
    """
    project = GradingJob.query.get(project_id)
    if not project:
        return False, None, "not_found"

    # Owner has full access
    if project.owner_id == user_id:
        return True, project, "owner"

    # Check for shared access
    share = ProjectShare.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()

    if share:
        if required_permission == "write" and share.permission_level != "write":
            return False, project, "insufficient_permission"
        return True, project, "shared"

    # Admin can view (but not modify without ownership)
    if hasattr(current_user, 'is_admin') and current_user.is_admin:
        if required_permission == "read":
            return True, project, "admin"

    return False, project, "no_access"


@projects_bp.route("", methods=["GET"])
@login_required
def list_projects():
    """
    Get list of projects accessible to current user.

    In multi-user mode, returns only projects owned by or shared with the user.
    In single-user mode, returns all projects.

    Response:
        {
            "projects": [
                {
                    "id": str,
                    "job_name": str,
                    "status": str,
                    "created_at": str,
                    ...
                }
            ]
        }
    """
    try:
        # In multi-user mode, filter by user
        if DeploymentService.is_multi_user_mode():
            # Get owned projects
            owned_projects = GradingJob.query.filter_by(owner_id=current_user.id).all()

            # Get shared projects
            shares = ProjectShare.query.filter_by(user_id=current_user.id).all()
            shared_project_ids = [share.project_id for share in shares]
            shared_projects = GradingJob.query.filter(GradingJob.id.in_(shared_project_ids)).all() if shared_project_ids else []

            # Combine and deduplicate
            all_projects = list({p.id: p for p in (owned_projects + shared_projects)}.values())
        else:
            # Single-user mode: return all projects
            all_projects = GradingJob.query.all()

        # Sort by creation date (newest first)
        all_projects.sort(key=lambda p: p.created_at, reverse=True)

        return jsonify({
            "projects": [project.to_dict() for project in all_projects]
        }), 200

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({"error": "Could not retrieve projects"}), 500


@projects_bp.route("/<project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    """
    Get a specific project by ID.

    Returns 403 if user doesn't have access.
    Returns 404 if project doesn't exist.

    Response:
        {
            "id": str,
            "job_name": str,
            "status": str,
            ...
        }
    """
    try:
        has_access, project, _reason = check_project_access(project_id, current_user.id, "read")

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if not has_access:
            return jsonify({"error": "Access denied"}), 403

        return jsonify(project.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting project: {e}")
        return jsonify({"error": "Could not retrieve project"}), 500


@projects_bp.route("/<project_id>", methods=["PUT"])
@login_required
def update_project(project_id):
    """
    Update a project.

    Only users with write permission can update.

    Request body:
        {
            "job_name": str (optional),
            "description": str (optional),
            "status": str (optional),
            ...
        }

    Response:
        {
            "success": bool,
            "project": {...},
            "message": str
        }
    """
    try:
        has_access, project, _reason = check_project_access(project_id, current_user.id, "write")

        if not project:
            return jsonify({"error": "Project not found"}), 404

        if not has_access:
            return jsonify({"error": "Write access required"}), 403

        data = request.get_json() or {}

        # Update allowed fields
        if "job_name" in data:
            project.job_name = data["job_name"]
        if "description" in data:
            project.description = data["description"]
        if "status" in data:
            project.status = data["status"]
        if "priority" in data:
            project.priority = data["priority"]

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Project updated successfully",
            "project": project.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating project: {e}")
        db.session.rollback()
        return jsonify({"error": "Could not update project"}), 500


@projects_bp.route("/<project_id>", methods=["DELETE"])
@login_required
def delete_project(project_id):
    """
    Delete a project.

    Only the owner can delete a project.

    Response:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        project = GradingJob.query.get(project_id)

        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Only owner can delete
        if project.owner_id != current_user.id:
            return jsonify({"error": "Only project owner can delete"}), 403

        db.session.delete(project)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Project deleted successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        db.session.rollback()
        return jsonify({"error": "Could not delete project"}), 500
