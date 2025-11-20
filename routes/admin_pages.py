"""Admin page routes (non-API)."""

import logging

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from services.auth_service import AuthService

logger = logging.getLogger(__name__)

admin_pages_bp = Blueprint("admin_pages", __name__, url_prefix="/admin")


def require_admin():
    """Decorator helper to check admin status."""
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    return None


@admin_pages_bp.route("/users", methods=["GET"])
@login_required
def list_users():
    """
    List all users (admin only).

    This is a non-API route that matches the test expectations.

    Response:
        {
            "users": [...],
            "total": int
        }
    """
    # Check admin
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        result = AuthService.list_users(limit=1000, offset=0)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({"error": "Could not retrieve users"}), 500
