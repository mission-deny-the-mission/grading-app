"""
Tests for sharing_routes - covering all project sharing API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSharingRoutes:
    """Test cases for project sharing API routes."""

    def test_get_project_shares_authenticated(self, client, app, test_user, auth_headers):
        """Test getting project shares."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.get_project_shares.return_value = []
            response = client.get("/api/projects/test-project-id/shares", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert "project_id" in data
            assert "shares" in data

    def test_get_project_shares_unauthenticated(self, client, app):
        """Test getting project shares without authentication."""
        response = client.get("/api/projects/test-project-id/shares")
        assert response.status_code in [401, 302]

    def test_get_project_shares_exception(self, client, app, test_user, auth_headers):
        """Test exception handling in get_project_shares."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.get_project_shares.side_effect = Exception("Service error")
            response = client.get("/api/projects/test-project-id/shares", headers=auth_headers)
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data

    def test_share_project_success(self, client, app, test_user, auth_headers):
        """Test sharing a project successfully."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_share = MagicMock()
            mock_share.to_dict.return_value = {
                "id": "share-1",
                "user_id": "recipient-user-id",
                "permission_level": "read"
            }
            mock_service.share_project.return_value = mock_share

            response = client.post(
                "/api/projects/test-project-id/shares",
                headers=auth_headers,
                json={
                    "user_id": "recipient-user-id",
                    "permission_level": "read"
                }
            )
            assert response.status_code == 201
            data = response.get_json()
            assert data["success"] is True

    def test_share_project_missing_user_id(self, client, app, test_user, auth_headers):
        """Test sharing a project without user_id."""
        response = client.post(
            "/api/projects/test-project-id/shares",
            headers=auth_headers,
            json={
                "permission_level": "read"
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_share_project_value_error(self, client, app, test_user, auth_headers):
        """Test sharing a project with invalid data."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.share_project.side_effect = ValueError("Invalid user")
            response = client.post(
                "/api/projects/test-project-id/shares",
                headers=auth_headers,
                json={
                    "user_id": "invalid-user-id",
                    "permission_level": "read"
                }
            )
            assert response.status_code == 400

    def test_share_project_exception(self, client, app, test_user, auth_headers):
        """Test exception handling in share_project."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.share_project.side_effect = Exception("Service error")
            response = client.post(
                "/api/projects/test-project-id/shares",
                headers=auth_headers,
                json={
                    "user_id": "recipient-user-id",
                    "permission_level": "read"
                }
            )
            assert response.status_code == 500

    def test_update_share_permissions_success(self, client, app, test_user, auth_headers):
        """Test updating share permissions."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_share = MagicMock()
            mock_share.to_dict.return_value = {
                "id": "share-1",
                "user_id": "recipient-user-id",
                "permission_level": "write"
            }
            mock_service.update_share_permissions.return_value = mock_share

            response = client.patch(
                "/api/projects/test-project-id/shares/share-1",
                headers=auth_headers,
                json={"permission_level": "write"}
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_update_share_permissions_invalid_level(self, client, app, test_user, auth_headers):
        """Test updating share with invalid permission level."""
        response = client.patch(
            "/api/projects/test-project-id/shares/share-1",
            headers=auth_headers,
            json={"permission_level": "invalid"}
        )
        assert response.status_code == 400

    def test_update_share_permissions_missing_level(self, client, app, test_user, auth_headers):
        """Test updating share without permission level."""
        response = client.patch(
            "/api/projects/test-project-id/shares/share-1",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 400

    def test_update_share_permissions_not_found(self, client, app, test_user, auth_headers):
        """Test updating non-existent share."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.update_share_permissions.side_effect = ValueError("Share not found")
            response = client.patch(
                "/api/projects/test-project-id/shares/nonexistent",
                headers=auth_headers,
                json={"permission_level": "write"}
            )
            assert response.status_code == 404

    def test_update_share_permissions_exception(self, client, app, test_user, auth_headers):
        """Test exception handling in update_share_permissions."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.update_share_permissions.side_effect = Exception("Service error")
            response = client.patch(
                "/api/projects/test-project-id/shares/share-1",
                headers=auth_headers,
                json={"permission_level": "write"}
            )
            assert response.status_code == 500

    def test_revoke_share_success(self, client, app, test_user, auth_headers):
        """Test revoking a share successfully."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.revoke_share.return_value = None
            response = client.delete(
                "/api/projects/test-project-id/shares/share-1",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_revoke_share_value_error(self, client, app, test_user, auth_headers):
        """Test revoking share with invalid data."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.revoke_share.side_effect = ValueError("Cannot revoke")
            response = client.delete(
                "/api/projects/test-project-id/shares/share-1",
                headers=auth_headers
            )
            assert response.status_code == 400

    def test_revoke_share_exception(self, client, app, test_user, auth_headers):
        """Test exception handling in revoke_share."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.revoke_share.side_effect = Exception("Service error")
            response = client.delete(
                "/api/projects/test-project-id/shares/share-1",
                headers=auth_headers
            )
            assert response.status_code == 500

    def test_get_shared_with_me_success(self, client, app, test_user, auth_headers):
        """Test getting projects shared with current user."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.get_user_accessible_projects.return_value = {
                "user_id": test_user.id,
                "shared_projects": []
            }
            response = client.get("/api/projects/shared", headers=auth_headers)
            assert response.status_code == 200

    def test_get_shared_with_me_exception(self, client, app, test_user, auth_headers):
        """Test exception handling in get_shared_with_me."""
        with patch("routes.sharing_routes.SharingService") as mock_service:
            mock_service.get_user_accessible_projects.side_effect = Exception("Service error")
            response = client.get("/api/projects/shared", headers=auth_headers)
            assert response.status_code == 500
