"""
Tests for config_routes - covering deployment mode management API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestConfigRoutes:
    """Test cases for configuration API routes."""

    def test_get_deployment_mode_success(self, client, app):
        """Test getting deployment mode."""
        response = client.get("/api/config/deployment-mode")
        assert response.status_code == 200
        data = response.get_json()
        assert "mode" in data

    def test_get_deployment_mode_exception(self, client, app):
        """Test exception handling in get_deployment_mode."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.get_config_dict.side_effect = Exception("Service error")
            response = client.get("/api/config/deployment-mode")
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data

    def test_set_deployment_mode_admin_success(self, client, app, admin_user, admin_headers):
        """Test setting deployment mode as admin."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_config = MagicMock()
            mock_config.to_dict.return_value = {
                "mode": "single-user",
                "configured_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
            mock_service.set_mode.return_value = mock_config

            response = client.post(
                "/api/config/deployment-mode",
                headers=admin_headers,
                json={"mode": "single-user"}
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_set_deployment_mode_non_admin(self, client, app, test_user, auth_headers):
        """Test setting deployment mode as non-admin fails."""
        response = client.post(
            "/api/config/deployment-mode",
            headers=auth_headers,
            json={"mode": "single-user"}
        )
        assert response.status_code == 403

    def test_set_deployment_mode_unauthenticated(self, client, app):
        """Test setting deployment mode without authentication."""
        response = client.post(
            "/api/config/deployment-mode",
            json={"mode": "single-user"}
        )
        assert response.status_code == 403

    def test_set_deployment_mode_missing_mode(self, client, app, admin_user, admin_headers):
        """Test setting deployment mode without mode parameter."""
        response = client.post(
            "/api/config/deployment-mode",
            headers=admin_headers,
            json={}
        )
        assert response.status_code == 400

    def test_set_deployment_mode_invalid_mode(self, client, app, admin_user, admin_headers):
        """Test setting deployment mode with invalid mode."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.set_mode.side_effect = ValueError("Invalid mode")
            response = client.post(
                "/api/config/deployment-mode",
                headers=admin_headers,
                json={"mode": "invalid-mode"}
            )
            assert response.status_code == 400

    def test_set_deployment_mode_exception(self, client, app, admin_user, admin_headers):
        """Test exception handling in set_deployment_mode."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.set_mode.side_effect = Exception("Service error")
            response = client.post(
                "/api/config/deployment-mode",
                headers=admin_headers,
                json={"mode": "single-user"}
            )
            assert response.status_code == 500

    def test_validate_mode_consistency_valid(self, client, app):
        """Test validating mode consistency when valid."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.validate_mode_consistency.return_value = {
                "valid": True,
                "env_mode": "multi-user",
                "db_mode": "multi-user",
                "message": "Modes are consistent"
            }
            response = client.get("/api/config/deployment-mode/validate")
            assert response.status_code == 200
            data = response.get_json()
            assert data["valid"] is True

    def test_validate_mode_consistency_invalid(self, client, app):
        """Test validating mode consistency when invalid."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.validate_mode_consistency.return_value = {
                "valid": False,
                "env_mode": "single-user",
                "db_mode": "multi-user",
                "message": "Modes are inconsistent"
            }
            response = client.get("/api/config/deployment-mode/validate")
            assert response.status_code == 500
            data = response.get_json()
            assert data["valid"] is False

    def test_validate_mode_consistency_exception(self, client, app):
        """Test exception handling in validate_mode_consistency."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.validate_mode_consistency.side_effect = Exception("Validation error")
            response = client.get("/api/config/deployment-mode/validate")
            assert response.status_code == 500
            data = response.get_json()
            assert data["valid"] is False

    def test_health_check_success(self, client, app):
        """Test health check endpoint."""
        response = client.get("/api/config/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "deployment_mode" in data
        assert "timestamp" in data

    def test_health_check_exception(self, client, app):
        """Test exception handling in health check."""
        with patch("routes.config_routes.DeploymentService") as mock_service:
            mock_service.get_current_mode.side_effect = Exception("Health check error")
            response = client.get("/api/config/health")
            assert response.status_code == 500
            data = response.get_json()
            assert data["status"] == "error"
