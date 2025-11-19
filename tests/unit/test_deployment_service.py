"""Unit tests for deployment service."""

import pytest

from models import DeploymentConfig, db
from services.deployment_service import DeploymentService


class TestDeploymentServiceMode:
    """Test deployment mode management."""

    def test_get_current_mode_default(self, app):
        """Test getting default mode."""
        with app.app_context():
            mode = DeploymentService.get_current_mode()

            assert mode in ("single-user", "multi-user")

    def test_set_mode_single_user(self, app):
        """Test setting single-user mode."""
        with app.app_context():
            DeploymentService.set_mode("single-user")

            mode = DeploymentService.get_current_mode()

            assert mode == "single-user"

    def test_set_mode_multi_user(self, app):
        """Test setting multi-user mode."""
        with app.app_context():
            DeploymentService.set_mode("multi-user")

            mode = DeploymentService.get_current_mode()

            assert mode == "multi-user"

    def test_set_mode_invalid(self, app):
        """Test setting invalid mode raises error."""
        with app.app_context():
            with pytest.raises(ValueError, match="Invalid deployment mode"):
                DeploymentService.set_mode("invalid-mode")

    def test_mode_persistence(self, app):
        """Test mode persists across calls."""
        with app.app_context():
            DeploymentService.set_mode("multi-user")

            mode1 = DeploymentService.get_current_mode()
            mode2 = DeploymentService.get_current_mode()

            assert mode1 == mode2 == "multi-user"


class TestDeploymentServiceValidation:
    """Test mode validation."""

    def test_validate_mode_consistency_match(self, app, monkeypatch):
        """Test validation passes when modes match."""
        with app.app_context():
            DeploymentService.set_mode("single-user")
            monkeypatch.setenv("DEPLOYMENT_MODE", "single-user")

            result = DeploymentService.validate_mode_consistency()

            assert result["valid"]
            assert result["env_mode"] == "single-user"
            assert result["db_mode"] == "single-user"

    def test_validate_mode_consistency_mismatch(self, app, monkeypatch):
        """Test validation fails when modes mismatch."""
        with app.app_context():
            DeploymentService.set_mode("single-user")
            monkeypatch.setenv("DEPLOYMENT_MODE", "multi-user")

            result = DeploymentService.validate_mode_consistency()

            assert not result["valid"]
            assert result["env_mode"] == "multi-user"
            assert result["db_mode"] == "single-user"


class TestDeploymentServiceChecks:
    """Test mode check methods."""

    def test_is_single_user_mode(self, app):
        """Test single-user mode check."""
        with app.app_context():
            DeploymentService.set_mode("single-user")

            assert DeploymentService.is_single_user_mode()
            assert not DeploymentService.is_multi_user_mode()

    def test_is_multi_user_mode(self, app):
        """Test multi-user mode check."""
        with app.app_context():
            DeploymentService.set_mode("multi-user")

            assert DeploymentService.is_multi_user_mode()
            assert not DeploymentService.is_single_user_mode()


class TestDeploymentServiceInitialize:
    """Test initialization."""

    def test_initialize_default_config(self, app):
        """Test initialization creates default config."""
        with app.app_context():
            # Clear existing config
            DeploymentConfig.query.delete()
            db.session.commit()

            config = DeploymentService.initialize_default_config()

            assert config is not None
            assert config.id == "singleton"

    def test_initialize_idempotent(self, app):
        """Test initialization is idempotent."""
        with app.app_context():
            DeploymentService.initialize_default_config()
            config1_id = DeploymentConfig.query.filter_by(id="singleton").first().id

            DeploymentService.initialize_default_config()
            config2_id = DeploymentConfig.query.filter_by(id="singleton").first().id

            assert config1_id == config2_id


class TestDeploymentServiceDict:
    """Test dictionary representation."""

    def test_get_config_dict(self, app):
        """Test getting config as dictionary."""
        with app.app_context():
            DeploymentService.set_mode("multi-user")

            config_dict = DeploymentService.get_config_dict()

            assert "id" in config_dict
            assert "mode" in config_dict
            assert "configured_at" in config_dict
            assert "updated_at" in config_dict
            assert config_dict["mode"] == "multi-user"
