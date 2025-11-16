"""Project sharing API routes for collaboration."""

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from services.sharing_service import SharingService

logger = logging.getLogger(__name__)

sharing_bp = Blueprint("sharing", __name__, url_prefix="/api/projects")


@sharing_bp.route("/<project_id>/shares", methods=["GET"])
@login_required
def get_project_shares(project_id):
    """
    Get all shares for a project.

    Response:
        {
            "project_id": str,
            "shares": [
                {
                    "id": str,
                    "user_id": str,
                    "permission_level": str,
                    "granted_at": str,
                    "granted_by": str
                }
            ]
        }
    """
    try:
        shares = SharingService.get_project_shares(project_id)

        return jsonify(
            {
                "project_id": project_id,
                "shares": shares,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting project shares: {e}")
        return jsonify({"error": "Could not retrieve shares"}), 500


@sharing_bp.route("/<project_id>/shares", methods=["POST"])
@login_required
def share_project(project_id):
    """
    Share a project with another user.

    Request body:
        {
            "user_id": str,
            "permission_level": "read" | "write"
        }

    Response:
        {
            "success": bool,
            "share": {...},
            "message": str
        }
    """
    data = request.get_json() or {}
    recipient_id = data.get("user_id")
    permission_level = data.get("permission_level", "read")

    if not recipient_id:
        return jsonify({"success": False, "message": "user_id required"}), 400

    try:
        share = SharingService.share_project(project_id, current_user.id, recipient_id, permission_level)

        return jsonify(
            {
                "success": True,
                "message": f"Project shared with {recipient_id} ({permission_level})",
                "share": share.to_dict(),
            }
        ), 201

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error sharing project: {e}")
        return jsonify({"success": False, "message": "Could not share project"}), 500


@sharing_bp.route("/<project_id>/shares/<share_id>", methods=["PATCH"])
@login_required
def update_share_permissions(project_id, share_id):
    """
    Update permissions for a project share.

    Request body:
        {
            "permission_level": "read" | "write"
        }

    Response:
        {
            "success": bool,
            "share": {...},
            "message": str
        }
    """
    data = request.get_json() or {}
    permission_level = data.get("permission_level")

    if not permission_level or permission_level not in ("read", "write"):
        return jsonify({"success": False, "message": "Valid permission_level required (read or write)"}), 400

    try:
        share = SharingService.update_share_permissions(project_id, share_id, permission_level)

        return jsonify(
            {
                "success": True,
                "message": f"Permissions updated to {permission_level}",
                "share": share.to_dict(),
            }
        ), 200

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Error updating share permissions: {e}")
        return jsonify({"success": False, "message": "Could not update permissions"}), 500


@sharing_bp.route("/<project_id>/shares/<share_id>", methods=["DELETE"])
@login_required
def revoke_share(project_id, share_id):
    """
    Revoke access to a project.

    Response:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        SharingService.revoke_share(project_id, share_id)

        return jsonify(
            {
                "success": True,
                "message": f"Share revoked",
            }
        ), 200

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error revoking share: {e}")
        return jsonify({"success": False, "message": "Could not revoke share"}), 500


@sharing_bp.route("/shared", methods=["GET"])
@login_required
def get_shared_with_me():
    """
    Get projects shared with current user.

    Response:
        {
            "user_id": str,
            "shared_projects": [
                {
                    "project_id": str,
                    "permission_level": str
                }
            ]
        }
    """
    try:
        result = SharingService.get_user_accessible_projects(current_user.id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting shared projects: {e}")
        return jsonify({"error": "Could not retrieve shared projects"}), 500
