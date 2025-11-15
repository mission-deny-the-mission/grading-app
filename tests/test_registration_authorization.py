"""
Registration Authorization Tests

Tests that user registration endpoint properly enforces admin-only access.
Prevents unauthorized user creation and privilege escalation attacks.
"""

import pytest


class TestRegistrationAuthorization:
    """Test that only admins can register new users."""

    def test_registration_requires_authentication(self, client):
        """Test that registration endpoint requires authentication."""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'NewPass123!',
            'display_name': 'New User'
        })

        assert response.status_code == 403, "Registration should require authentication"
        data = response.get_json()
        assert data['success'] is False
        assert 'admin' in data['message'].lower()

    def test_registration_requires_admin_privilege(self, client, test_user, auth_headers):
        """Test that regular users cannot register new users."""
        response = client.post('/api/auth/register',
            json={
                'email': 'newuser@example.com',
                'password': 'NewPass123!',
                'display_name': 'New User'
            },
            headers=auth_headers
        )

        assert response.status_code == 403, "Regular users should not be able to register users"
        data = response.get_json()
        assert data['success'] is False
        assert 'admin' in data['message'].lower()

    def test_admin_can_register_users(self, client, admin_user, admin_headers):
        """Test that admin users can register new users."""
        response = client.post('/api/auth/register',
            json={
                'email': 'newuser@example.com',
                'password': 'NewPass123!',
                'display_name': 'New User'
            },
            headers=admin_headers
        )

        assert response.status_code == 201, "Admin should be able to register users"
        data = response.get_json()
        assert data['success'] is True

    def test_privilege_escalation_attempt(self, client, test_user, auth_headers):
        """Test that regular users cannot create admin accounts."""
        # Regular user trying to create an admin account
        response = client.post('/api/auth/register',
            json={
                'email': 'malicious@example.com',
                'password': 'MalPass123!',
                'display_name': 'Malicious Admin',
                'is_admin': True  # Attempting privilege escalation
            },
            headers=auth_headers
        )

        # Should be blocked at authorization check (403)
        assert response.status_code == 403, "Regular users should not reach user creation logic"

    def test_unauthenticated_admin_creation_attempt(self, client):
        """Test that unauthenticated requests cannot create admin accounts."""
        response = client.post('/api/auth/register', json={
            'email': 'malicious@example.com',
            'password': 'MalPass123!',
            'display_name': 'Malicious Admin',
            'is_admin': True
        })

        assert response.status_code == 403, "Unauthenticated requests should be rejected"

    def test_admin_creates_regular_user(self, client, admin_user, admin_headers):
        """Test that admin can create regular (non-admin) users."""
        response = client.post('/api/auth/register',
            json={
                'email': 'regular@example.com',
                'password': 'RegPass123!',
                'display_name': 'Regular User',
                'is_admin': False
            },
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['user']['is_admin'] is False

    def test_single_user_mode_registration_disabled(self, client, admin_headers, mocker):
        """Test that registration is disabled in single-user mode."""
        # Mock single-user mode
        mocker.patch('services.deployment_service.DeploymentService.is_single_user_mode', return_value=True)

        response = client.post('/api/auth/register',
            json={
                'email': 'newuser@example.com',
                'password': 'NewPass123!',
                'display_name': 'New User'
            },
            headers=admin_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'single-user' in data['message'].lower()
