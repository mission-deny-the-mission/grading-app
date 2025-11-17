"""Deployment configuration service for managing single-user vs multi-user modes."""

import logging
import os
from datetime import datetime, timezone

from models import DeploymentConfig, db

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service for managing deployment mode configuration and validation."""

    @staticmethod
    def get_current_mode():
        """Get the current deployment mode from database."""
        try:
            mode = DeploymentConfig.get_current_mode()
            return mode
        except Exception as e:
            logger.error(f"Error getting deployment mode: {e}")
            return "single-user"  # Default fallback

    @staticmethod
    def set_mode(mode):
        """
        Set the deployment mode (single-user or multi-user).

        Args:
            mode: str - "single-user" or "multi-user"

        Returns:
            DeploymentConfig: Updated configuration object

        Raises:
            ValueError: If mode is not valid
        """
        if mode not in ("single-user", "multi-user"):
            raise ValueError(f"Invalid deployment mode: {mode}. Must be 'single-user' or 'multi-user'")

        try:
            config = DeploymentConfig.set_mode(mode)
            logger.info(f"Deployment mode changed to: {mode}")
            return config
        except Exception as e:
            logger.error(f"Error setting deployment mode: {e}")
            raise

    @staticmethod
    def validate_mode_consistency():
        """
        Validate that environment variable matches database configuration.

        This catches configuration mismatches between restarts that could cause
        unexpected authentication behavior.

        Returns:
            dict: {"valid": bool, "env_mode": str, "db_mode": str, "message": str}
        """
        env_mode = os.getenv("DEPLOYMENT_MODE", "single-user")
        db_mode = DeploymentConfig.get_current_mode()

        if env_mode != db_mode:
            message = (
                f"Deployment mode mismatch: Environment={env_mode}, Database={db_mode}. "
                f"Update DEPLOYMENT_MODE env var or set database mode to match."
            )
            logger.error(message)
            return {
                "valid": False,
                "env_mode": env_mode,
                "db_mode": db_mode,
                "message": message,
            }

        return {
            "valid": True,
            "env_mode": env_mode,
            "db_mode": db_mode,
            "message": f"Mode consistency verified: {db_mode}",
        }

    @staticmethod
    def initialize_default_config():
        """Initialize default deployment configuration if not already set."""
        try:
            config = DeploymentConfig.query.filter_by(id="singleton").first()
            if not config:
                env_mode = os.getenv("DEPLOYMENT_MODE", "single-user")
                config = DeploymentConfig(id="singleton", mode=env_mode)
                db.session.add(config)
                db.session.commit()
                logger.info(f"Initialized deployment config with mode: {env_mode}")
                return config
            return config
        except Exception as e:
            logger.error(f"Error initializing deployment config: {e}")
            raise

    @staticmethod
    def get_config_dict():
        """Get deployment configuration as dictionary."""
        config = DeploymentConfig.query.filter_by(id="singleton").first()
        if config:
            return config.to_dict()
        return {
            "id": "singleton",
            "mode": "single-user",
            "configured_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def is_single_user_mode():
        """Check if system is in single-user mode."""
        mode = DeploymentService.get_current_mode()
        return mode == "single-user"

    @staticmethod
    def is_multi_user_mode():
        """Check if system is in multi-user mode."""
        mode = DeploymentService.get_current_mode()
        return mode == "multi-user"
