"""
Tests for usage_routes - covering all usage tracking API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestUsageRoutes:
    """Test cases for usage tracking API routes."""

    def test_get_usage_authenticated(self, client, app, test_user, auth_headers):
        """Test getting usage records for authenticated user."""
        response = client.get("/api/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "user_id" in data
        assert "usage_records" in data
        assert "total_tokens" in data

    def test_get_usage_unauthenticated(self, client, app):
        """Test getting usage records without authentication."""
        response = client.get("/api/usage")
        # Should redirect to login or return 401
        assert response.status_code in [401, 302]

    def test_get_usage_exception_handling(self, client, app, test_user, auth_headers):
        """Test exception handling in get_usage route."""
        with patch("models.UsageRecord") as mock_model:
            mock_model.query.filter_by.side_effect = Exception("Database error")
            response = client.get("/api/usage", headers=auth_headers)
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data

    def test_get_usage_dashboard_single_user_mode(self, client, app):
        """Test usage dashboard in single-user mode."""
        with patch("routes.usage_routes.DeploymentService") as mock_deploy:
            mock_deploy.is_single_user_mode.return_value = True
            response = client.get("/api/usage/dashboard")
            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert "single-user" in data["message"]

    def test_get_usage_dashboard_multi_user_authenticated(self, client, app, test_user, auth_headers):
        """Test usage dashboard in multi-user mode with authentication."""
        with patch("routes.usage_routes.DeploymentService") as mock_deploy:
            mock_deploy.is_single_user_mode.return_value = False
            with patch("routes.usage_routes.UsageTrackingService") as mock_service:
                mock_service.get_usage_dashboard.return_value = {
                    "user_id": test_user.id,
                    "providers": [],
                    "generated_at": "2024-01-01T00:00:00Z"
                }
                response = client.get("/api/usage/dashboard", headers=auth_headers)
                assert response.status_code == 200

    def test_get_usage_dashboard_multi_user_unauthenticated(self, client, app):
        """Test usage dashboard in multi-user mode without authentication."""
        with patch("routes.usage_routes.DeploymentService") as mock_deploy:
            mock_deploy.is_single_user_mode.return_value = False
            response = client.get("/api/usage/dashboard")
            assert response.status_code == 401
            data = response.get_json()
            assert "error" in data

    def test_get_usage_dashboard_exception_handling(self, client, app, test_user, auth_headers):
        """Test exception handling in usage dashboard."""
        with patch("routes.usage_routes.DeploymentService") as mock_deploy:
            mock_deploy.is_single_user_mode.return_value = False
            with patch("routes.usage_routes.UsageTrackingService") as mock_service:
                mock_service.get_usage_dashboard.side_effect = Exception("Service error")
                response = client.get("/api/usage/dashboard", headers=auth_headers)
                assert response.status_code == 500

    def test_get_quotas_authenticated(self, client, app, test_user, auth_headers):
        """Test getting quotas for authenticated user."""
        response = client.get("/api/usage/quotas", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "user_id" in data
        assert "quotas" in data

    def test_get_quotas_exception_handling(self, client, app, test_user, auth_headers):
        """Test exception handling in get_quotas route."""
        with patch("routes.usage_routes.AIProviderQuota") as mock_model:
            mock_model.query.filter_by.side_effect = Exception("Database error")
            response = client.get("/api/usage/quotas", headers=auth_headers)
            assert response.status_code == 500

    def test_set_quota_admin_success(self, client, app, admin_user, admin_headers, test_user):
        """Test setting quota as admin."""
        with patch("routes.usage_routes.UsageTrackingService") as mock_service:
            mock_quota = MagicMock()
            mock_quota.to_dict.return_value = {
                "id": "quota-1",
                "provider": "openai",
                "limit_type": "tokens",
                "limit_value": 1000,
                "reset_period": "monthly"
            }
            mock_service.set_quota.return_value = mock_quota

            response = client.put(
                f"/api/usage/quotas/{test_user.id}",
                headers=admin_headers,
                json={
                    "provider": "openai",
                    "limit_type": "tokens",
                    "limit_value": 1000,
                    "reset_period": "monthly"
                }
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_set_quota_non_admin(self, client, app, test_user, auth_headers):
        """Test setting quota as non-admin fails."""
        response = client.put(
            f"/api/usage/quotas/{test_user.id}",
            headers=auth_headers,
            json={
                "provider": "openai",
                "limit_type": "tokens",
                "limit_value": 1000,
                "reset_period": "monthly"
            }
        )
        assert response.status_code == 403

    def test_set_quota_missing_fields(self, client, app, admin_user, admin_headers, test_user):
        """Test setting quota with missing fields."""
        response = client.put(
            f"/api/usage/quotas/{test_user.id}",
            headers=admin_headers,
            json={
                "provider": "openai"
                # Missing other required fields
            }
        )
        assert response.status_code == 400

    def test_set_quota_exception_handling(self, client, app, admin_user, admin_headers, test_user):
        """Test exception handling in set_quota route."""
        with patch("routes.usage_routes.UsageTrackingService") as mock_service:
            mock_service.set_quota.side_effect = Exception("Service error")
            response = client.put(
                f"/api/usage/quotas/{test_user.id}",
                headers=admin_headers,
                json={
                    "provider": "openai",
                    "limit_type": "tokens",
                    "limit_value": 1000,
                    "reset_period": "monthly"
                }
            )
            assert response.status_code == 500

    def test_get_usage_history_authenticated(self, client, app, test_user, auth_headers):
        """Test getting usage history."""
        with patch("routes.usage_routes.UsageTrackingService") as mock_service:
            mock_service.get_usage_history.return_value = {
                "user_id": test_user.id,
                "records": [],
                "total": 0,
                "limit": 100,
                "offset": 0
            }
            response = client.get("/api/usage/history", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert "records" in data

    def test_get_usage_history_with_params(self, client, app, test_user, auth_headers):
        """Test getting usage history with query parameters."""
        with patch("routes.usage_routes.UsageTrackingService") as mock_service:
            mock_service.get_usage_history.return_value = {
                "user_id": test_user.id,
                "records": [],
                "total": 0,
                "limit": 50,
                "offset": 10
            }
            response = client.get(
                "/api/usage/history?provider=openai&limit=50&offset=10",
                headers=auth_headers
            )
            assert response.status_code == 200

    def test_get_usage_history_exception_handling(self, client, app, test_user, auth_headers):
        """Test exception handling in usage history."""
        with patch("routes.usage_routes.UsageTrackingService") as mock_service:
            mock_service.get_usage_history.side_effect = Exception("Service error")
            response = client.get("/api/usage/history", headers=auth_headers)
            assert response.status_code == 500

    def test_get_usage_reports_admin(self, client, app, admin_user, admin_headers):
        """Test getting usage reports as admin."""
        response = client.get("/api/usage/reports", headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "generated_at" in data
        assert "summary" in data

    def test_get_usage_reports_non_admin(self, client, app, test_user, auth_headers):
        """Test getting usage reports as non-admin fails."""
        response = client.get("/api/usage/reports", headers=auth_headers)
        assert response.status_code == 403

    def test_get_usage_reports_exception_handling(self, client, app, admin_user, admin_headers):
        """Test exception handling in usage reports."""
        with patch("models.User") as mock_user:
            mock_user.query.count.side_effect = Exception("Database error")
            response = client.get("/api/usage/reports", headers=admin_headers)
            assert response.status_code == 500
