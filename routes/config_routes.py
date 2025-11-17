"""Configuration API routes for deployment mode management."""

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from models import DeploymentConfig, db
from services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__, url_prefix="/api/config")


@config_bp.route("/deployment-mode", methods=["GET"])
def get_deployment_mode():
    """
    Get current deployment mode.

    Response:
        {
            "mode": "single-user" | "multi-user",
            "configured_at": str (ISO format),
            "updated_at": str (ISO format)
        }
    """
    try:
        config = DeploymentService.get_config_dict()
        return jsonify(config), 200
    except Exception as e:
        logger.error(f"Error getting deployment mode: {e}")
        return jsonify({"error": "Could not retrieve deployment mode"}), 500


@config_bp.route("/deployment-mode", methods=["POST"])
def set_deployment_mode():
    """
    Set deployment mode (requires admin privilege).

    Request body:
        {
            "mode": "single-user" | "multi-user"
        }

    Response:
        {
            "success": bool,
            "mode": str,
            "message": str
        }
    """
    # Check admin privilege
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin only"}), 403

    data = request.get_json() or {}
    mode = data.get("mode")

    if not mode:
        return jsonify({"success": False, "message": "Mode parameter required"}), 400

    try:
        config = DeploymentService.set_mode(mode)
        logger.info(f"Deployment mode changed to: {mode}")

        return jsonify(
            {
                "success": True,
                "message": f"Deployment mode changed to {mode}",
                **config.to_dict(),
            }
        ), 200

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error setting deployment mode: {e}")
        return jsonify({"success": False, "message": "Could not change mode"}), 500


@config_bp.route("/deployment-mode/validate", methods=["GET"])
def validate_mode_consistency():
    """
    Validate deployment mode consistency between environment and database.

    Response:
        {
            "valid": bool,
            "env_mode": str,
            "db_mode": str,
            "message": str
        }
    """
    try:
        result = DeploymentService.validate_mode_consistency()
        return jsonify(result), 200 if result["valid"] else 500
    except Exception as e:
        logger.error(f"Error validating mode: {e}")
        return jsonify({"valid": False, "message": "Validation error"}), 500


@config_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for system status.

    Response:
        {
            "status": "ok",
            "deployment_mode": str,
            "timestamp": str
        }
    """
    try:
        mode = DeploymentService.get_current_mode()
        from datetime import datetime, timezone

        return jsonify(
            {
                "status": "ok",
                "deployment_mode": mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
