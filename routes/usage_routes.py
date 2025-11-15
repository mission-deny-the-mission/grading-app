"""Usage tracking and quota management API routes."""

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from models import AIProviderQuota, db
from services.deployment_service import DeploymentService
from services.usage_tracking_service import UsageTrackingService

logger = logging.getLogger(__name__)

usage_bp = Blueprint("usage", __name__, url_prefix="/api/usage")


@usage_bp.route("/dashboard", methods=["GET"])
def get_usage_dashboard():
    """
    Get usage dashboard for current user.

    In single-user mode, returns empty dashboard.
    In multi-user mode, requires login.

    Response:
        {
            "user_id": str,
            "providers": [
                {
                    "provider": str,
                    "can_use": bool,
                    "current_usage": int,
                    "limit": int,
                    "remaining": int,
                    "percentage_used": float,
                    "warning": bool,
                    "reset_period": str
                }
            ],
            "generated_at": str
        }
    """
    # Single-user mode: no usage tracking
    if DeploymentService.is_single_user_mode():
        return jsonify(
            {
                "user_id": "system",
                "providers": [],
                "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "message": "Usage tracking disabled in single-user mode",
            }
        ), 200

    # Multi-user mode: require login
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    try:
        dashboard = UsageTrackingService.get_usage_dashboard(current_user.id)
        return jsonify(dashboard), 200
    except Exception as e:
        logger.error(f"Error getting usage dashboard: {e}")
        return jsonify({"error": "Could not retrieve usage dashboard"}), 500


@usage_bp.route("/quotas", methods=["GET"])
@login_required
def get_quotas():
    """
    Get user's quotas for all providers.

    Response:
        {
            "user_id": str,
            "quotas": [
                {
                    "id": str,
                    "provider": str,
                    "limit_type": str,
                    "limit_value": int,
                    "reset_period": str,
                    "created_at": str,
                    "updated_at": str
                }
            ]
        }
    """
    try:
        quotas = AIProviderQuota.query.filter_by(user_id=current_user.id).all()

        return jsonify(
            {
                "user_id": current_user.id,
                "quotas": [q.to_dict() for q in quotas],
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting quotas: {e}")
        return jsonify({"error": "Could not retrieve quotas"}), 500


@usage_bp.route("/quotas/<user_id>", methods=["PUT"])
@login_required
def set_quota(user_id):
    """
    Set quota for a user (admin only).

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
    # Admin check
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin only"}), 403

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
                "message": f"Quota set for {provider}",
                "quota": quota.to_dict(),
            }
        ), 200

    except Exception as e:
        logger.error(f"Error setting quota: {e}")
        return jsonify({"success": False, "message": "Could not set quota"}), 500


@usage_bp.route("/history", methods=["GET"])
@login_required
def get_usage_history():
    """
    Get usage history for current user.

    Query parameters:
        provider: str (optional) - Filter by provider
        limit: int (default 100) - Max records
        offset: int (default 0) - Pagination offset

    Response:
        {
            "user_id": str,
            "records": [...],
            "total": int,
            "limit": int,
            "offset": int
        }
    """
    provider = request.args.get("provider")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    try:
        history = UsageTrackingService.get_usage_history(current_user.id, provider, limit, offset)
        return jsonify(history), 200
    except Exception as e:
        logger.error(f"Error getting usage history: {e}")
        return jsonify({"error": "Could not retrieve usage history"}), 500


@usage_bp.route("/reports", methods=["GET"])
@login_required
def get_usage_reports():
    """
    Get aggregated usage reports (admin only).

    Response:
        {
            "generated_at": str,
            "summary": {
                "total_users": int,
                "total_providers": int,
                "total_usage": int
            }
        }
    """
    # Admin check
    if not current_user.is_admin:
        return jsonify({"error": "Admin only"}), 403

    try:
        from datetime import datetime, timezone

        from models import UsageRecord, User

        total_users = User.query.count()
        total_usage = (
            db.session.query(db.func.sum(UsageRecord.tokens_consumed)).scalar() or 0
        )

        return jsonify(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_users": total_users,
                    "total_usage": total_usage,
                    # Add more metrics as needed
                },
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting usage reports: {e}")
        return jsonify({"error": "Could not retrieve reports"}), 500
