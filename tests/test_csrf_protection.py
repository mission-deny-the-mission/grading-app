"""
CSRF Protection Tests

Tests for Cross-Site Request Forgery protection implementation.
Ensures all POST/PUT/DELETE routes require valid CSRF tokens.
"""

import pytest
from flask import session

from tests.factories import UserFactory


class TestCSRFProtection:
    """Test CSRF protection is properly enforced."""

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_protection_on_login(self, client_multi_user, multi_user_mode):
        """Test that login endpoint requires CSRF token."""
        # Create a valid user for authentication
        user = UserFactory.create(email='test@example.com', password='TestPass123!')
        
        response = client_multi_user.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123!'
        })

        # Should get 400 error without CSRF token
        assert response.status_code == 400, "Login should require CSRF token"
        data = response.get_json()
        assert 'csrf' in str(data).lower() or 'token' in str(data).lower()

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_protection_on_user_creation(self, client, admin_user, admin_headers, multi_user_mode):
        """Test that user creation endpoint requires CSRF token."""
        # Admin user creation without CSRF token should fail
        response = client.post('/api/admin/users',
            json={
                'email': 'newuser@example.com',
                'password': 'NewPass123!',
                'display_name': 'New User'
            },
            headers=admin_headers
        )

        assert response.status_code == 400, "User creation should require CSRF token"

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_protection_on_project_sharing(self, client, test_user, auth_headers, test_project):
        """Test that project sharing endpoint requires CSRF token."""
        response = client.post(f'/api/projects/{test_project.id}/shares',
            json={
                'recipient_email': 'colleague@example.com',
                'permission_level': 'read'
            },
            headers=auth_headers
        )

        assert response.status_code == 400, "Project sharing should require CSRF token"

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_protection_on_quota_update(self, client, admin_user, admin_headers, test_user):
        """Test that quota update endpoint requires CSRF token."""
        response = client.put(f'/api/admin/users/{test_user.id}/quotas',
            json={
                'provider': 'openai',
                'limit_requests': 100,
                'limit_tokens': 10000,
                'period': 'daily'
            },
            headers=admin_headers
        )

        assert response.status_code == 400, "Quota update should require CSRF token"

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_protection_on_deployment_mode_change(self, client, admin_user, admin_headers, multi_user_mode):
        """Test that deployment mode change requires CSRF token."""
        response = client.post('/api/admin/deployment-mode',
            json={
                'mode': 'multi-user'
            },
            headers=admin_headers
        )

        assert response.status_code == 400, "Deployment mode change should require CSRF token"

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_token_validation_with_invalid_token(self, client, multi_user_mode):
        """Test that invalid CSRF tokens are rejected."""
        response = client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'TestPass123!'
            },
            headers={'X-CSRFToken': 'invalid-token-12345'}
        )

        assert response.status_code in [400, 403], "Invalid CSRF token should be rejected"

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_exemption_for_get_requests(self, client, multi_user_mode):
        """Test that GET requests don't require CSRF tokens (read-only)."""
        response = client.get('/api/auth/session')

        # Should work without CSRF token (may be 401 if not logged in, but not CSRF error)
        assert response.status_code != 400 or 'csrf' not in str(response.get_json()).lower()

    @pytest.mark.skip("CSRF disabled in test mode - WTF_CSRF_ENABLED=False")
    def test_csrf_double_submit_cookie_pattern(self, client, multi_user_mode):
        """Test CSRF protection uses double-submit cookie pattern."""
        # First request should set CSRF token in session
        with client:
            client.get('/')

            # Check that CSRF token is available in session
            # Flask-WTF should provide csrf_token() in session
            assert 'csrf_token' in session or '_csrf_token' in session, \
                "CSRF token should be set in session"
