"""Admin dashboard API routes for user management."""

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import limiter
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def require_admin():
    """Decorator helper to check admin status."""
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    return None


@admin_bp.route("/users", methods=["GET"])
@login_required
@limiter.limit("50 per hour")
def list_users():
    """
    List all users with pagination (admin only).

    Query parameters:
        limit: int (default 100) - Maximum users to return
        offset: int (default 0) - Pagination offset

    Response:
        {
            "users": [...],
            "total": int,
            "limit": int,
            "offset": int
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    try:
        result = AuthService.list_users(limit=limit, offset=offset)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({"error": "Could not retrieve users"}), 500


@admin_bp.route("/users/<user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    """
    Get user details by ID (admin only).

    Response:
        {
            "success": bool,
            "user": {...}
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        user = AuthService.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        return jsonify(
            {
                "success": True,
                "user": user.to_dict(),
            }
        ), 200
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({"success": False, "message": "Could not retrieve user"}), 500


@admin_bp.route("/users", methods=["POST"])
@login_required
def create_user():
    """
    Create a new user (admin only).

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
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    display_name = data.get("display_name")
    is_admin = data.get("is_admin", False)

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    try:
        user = AuthService.create_user(email, password, display_name, is_admin)
        logger.info(f"Admin created user: {email}")

        return jsonify(
            {
                "success": True,
                "message": f"User {email} created successfully",
                "user": user.to_dict(),
            }
        ), 201

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({"success": False, "message": "User creation failed"}), 500


@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    """
    Delete a user (admin only).

    Cannot delete self.

    Response:
        {
            "success": bool,
            "message": str
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    # Prevent self-deletion
    if user_id == current_user.id:
        return jsonify({"success": False, "message": "Cannot delete yourself"}), 400

    try:
        AuthService.delete_user(user_id)
        logger.info(f"Admin deleted user: {user_id}")

        return jsonify(
            {
                "success": True,
                "message": "User deleted successfully",
            }
        ), 200

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({"success": False, "message": "User deletion failed"}), 500


@admin_bp.route("/users/<user_id>/role", methods=["PATCH"])
@login_required
def update_user_role(user_id):
    """
    Update user role (admin only).

    Cannot change own role.

    Request body:
        {
            "is_admin": true/false
        }

    Response:
        {
            "success": bool,
            "user": {...},
            "message": str
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    # Prevent changing own role
    if user_id == current_user.id:
        return jsonify({"success": False, "message": "Cannot change your own role"}), 400

    data = request.get_json() or {}
    is_admin = data.get("is_admin")

    if is_admin is None:
        return jsonify({"success": False, "message": "is_admin field required"}), 400

    try:
        user = AuthService.update_user(user_id, is_admin=is_admin)
        logger.info(f"Admin updated user role: {user_id} -> is_admin={is_admin}")

        return jsonify(
            {
                "success": True,
                "message": f"User role updated",
                "user": user.to_dict(),
            }
        ), 200

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return jsonify({"success": False, "message": "Role update failed"}), 500


@admin_bp.route("/users/<user_id>", methods=["PATCH"])
@login_required
def update_user(user_id):
    """
    Update user details (admin only).

    Request body (all optional):
        {
            "email": "newemail@example.com",
            "display_name": "New Name",
            "is_active": true/false,
            "password": "newPassword123!"  # Admin can reset password
        }

    Response:
        {
            "success": bool,
            "user": {...},
            "message": str
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}

    # Build update kwargs
    update_fields = {}
    if "email" in data:
        update_fields["email"] = data["email"]
    if "display_name" in data:
        update_fields["display_name"] = data["display_name"]
    if "is_active" in data:
        update_fields["is_active"] = data["is_active"]
    if "password" in data:
        update_fields["password"] = data["password"]

    if not update_fields:
        return jsonify({"success": False, "message": "No fields to update"}), 400

    try:
        user = AuthService.update_user(user_id, **update_fields)
        logger.info(f"Admin updated user: {user_id}")

        return jsonify(
            {
                "success": True,
                "message": "User updated successfully",
                "user": user.to_dict(),
            }
        ), 200

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({"success": False, "message": "User update failed"}), 500


@admin_bp.route("/users/<user_id>/quotas", methods=["PUT"])
@login_required
def update_user_quotas(user_id):
    """
    Update user quotas (admin only).

    Request body:
        {
            "provider": str,
            "limit_type": str,
            "limit_value": int,
            "reset_period": str
        }

    Response:
        {
            "success": bool,
            "quota": {...},
            "message": str
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    from services.usage_tracking_service import UsageTrackingService

    data = request.get_json() or {}
    provider = data.get("provider")
    limit_type = data.get("limit_type")
    limit_value = data.get("limit_value")
    reset_period = data.get("reset_period")

    if not all([provider, limit_type, limit_value is not None, reset_period]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        quota = UsageTrackingService.set_quota(user_id, provider, limit_type, limit_value, reset_period)

        return jsonify(
            {
                "success": True,
                "message": f"Quota updated for user {user_id}",
                "quota": quota.to_dict(),
            }
        ), 200

    except Exception as e:
        logger.error(f"Error updating quota: {e}")
        return jsonify({"success": False, "message": "Quota update failed"}), 500
