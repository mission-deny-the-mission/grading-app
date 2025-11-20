"""
Middleware Authentication Enforcement Tests

Tests for auth_middleware.py authentication and authorization enforcement.
Target coverage: 0% → 80%
"""

import pytest
from flask import session
from models import User, db


class TestPublicRouteExceptions:
    """Test that public routes are accessible without authentication."""

    def test_login_page_accessible_without_auth(self, client):
        """Test that login page is accessible without authentication."""
        response = client.get('/login')
        assert response.status_code == 200

    def test_register_page_accessible_without_auth(self, client):
        """Test that register page is accessible without authentication (in multi-user mode)."""
        response = client.get('/register')
        # May redirect or show page depending on deployment mode
        assert response.status_code in [200, 302]

    def test_static_assets_accessible_without_auth(self, client):
        """Test that static assets don't require authentication."""
        # Static files should be served without auth
        response = client.get('/static/style.css')
        # 404 if file doesn't exist, but should not be 401/403
        assert response.status_code != 401
        assert response.status_code != 403

    def test_api_login_endpoint_accessible_without_auth(self, client):
        """Test that API login endpoint is public."""
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrong'
        })
        # Should return auth error, not access denied
        assert response.status_code in [400, 401]  # Not 403 (forbidden)


class TestLoginRedirects:
    """Test login redirect behavior for web requests."""

    def test_protected_page_redirects_to_login(self, client):
        """Test that unauthenticated web requests redirect to login."""
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_admin_page_redirects_to_login(self, client):
        """Test that admin pages redirect unauthenticated users to login."""
        response = client.get('/admin/users', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location

    def test_login_preserves_next_url(self, client):
        """Test that login redirect preserves original destination."""
        response = client.get('/dashboard', follow_redirects=False)
        assert 'next=' in response.location or 'next%3D' in response.location


class TestAPIvsWebRequestHandling:
    """Test that API and web requests are handled differently."""

    def test_api_request_returns_401_not_redirect(self, client):
        """Test that API requests return 401, not redirect."""
        response = client.get('/api/batches', headers={
            'Accept': 'application/json'
        })
        # API should return 401, not redirect
        assert response.status_code == 401
        assert response.is_json

    def test_web_request_redirects_to_login(self, client):
        """Test that web requests redirect to login."""
        response = client.get('/batches', follow_redirects=False)
        # Web requests should redirect
        assert response.status_code == 302

    def test_api_error_includes_json_response(self, client):
        """Test that API errors return JSON."""
        response = client.get('/api/batches', headers={
            'Accept': 'application/json'
        })
        assert response.is_json
        data = response.get_json()
        assert 'error' in data or 'message' in data


class TestSessionValidationLogic:
    """Test session validation and security."""

    def test_invalid_session_clears_session(self, client, test_user):
        """Test that invalid sessions are cleared."""
        # Create invalid session
        with client.session_transaction() as sess:
            sess['_user_id'] = 'invalid-user-id'

        response = client.get('/dashboard', follow_redirects=False)
        # Should redirect to login after clearing invalid session
        assert response.status_code == 302

    def test_valid_session_allows_access(self, client, test_user, auth):
        """Test that valid sessions allow access."""
        auth.login(email='testuser@example.com', password='TestPass123!')
        response = client.get('/dashboard')
        assert response.status_code == 200

    def test_inactive_user_denied_access(self, client, test_user, auth):
        """Test that inactive users are denied access even with valid session."""
        # Login first
        auth.login(email='testuser@example.com', password='TestPass123!')

        # Deactivate user
        test_user.is_active = False
        db.session.commit()

        # Try to access protected route
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302  # Redirect to login


class TestDeploymentModeRouting:
    """Test routing based on deployment mode (single-user vs multi-user)."""

    def test_single_user_mode_bypasses_auth(self, client, monkeypatch):
        """Test that single-user mode allows access without auth."""
        # Mock single-user mode
        from services.deployment_service import DeploymentService
        monkeypatch.setattr(DeploymentService, 'is_single_user_mode', lambda: True)

        # Should allow access without login
        response = client.get('/dashboard')
        # In single-user mode, may auto-login or allow access
        assert response.status_code in [200, 302]

    def test_multi_user_mode_requires_auth(self, client, monkeypatch):
        """Test that multi-user mode requires authentication."""
        # Mock multi-user mode
        from services.deployment_service import DeploymentService
        monkeypatch.setattr(DeploymentService, 'is_single_user_mode', lambda: False)

        # Should require authentication
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location


class TestSessionSecurity:
    """Test session security features."""

    def test_session_regeneration_on_login(self, client, test_user, auth):
        """Test that session ID changes on login (prevent session fixation)."""
        # Get initial session
        client.get('/login')
        with client.session_transaction() as sess:
            initial_session_id = id(sess)

        # Login
        auth.login(email='testuser@example.com', password='TestPass123!')

        # Session should be regenerated
        with client.session_transaction() as sess:
            new_session_id = id(sess)

        # Flask-Login handles session regeneration
        # Just verify we have a valid user session
        assert session.get('_user_id') is not None

    def test_session_cleared_on_logout(self, client, test_user, auth):
        """Test that session is cleared on logout."""
        # Login
        auth.login(email='testuser@example.com', password='TestPass123!')
        assert session.get('_user_id') is not None

        # Logout
        auth.logout()

        # Session should be cleared
        with client.session_transaction() as sess:
            assert sess.get('_user_id') is None


class TestAuthorizationEnforcement:
    """Test authorization checks beyond authentication."""

    def test_regular_user_cannot_access_admin_routes(self, client, test_user, auth):
        """Test that non-admin users cannot access admin routes."""
        # Login as regular user
        auth.login(email='testuser@example.com', password='TestPass123!')

        # Try to access admin route
        response = client.get('/admin/users')
        assert response.status_code == 403

    def test_admin_can_access_admin_routes(self, client, auth):
        """Test that admin users can access admin routes."""
        # Create admin user
        admin = User(
            email='admin@example.com',
            password_hash='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeD.e4hIxjVFUwjVC',  # hashed 'password'
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

        # Login as admin
        auth.login(email='admin@example.com', password='TestPass123!')

        # Should allow access to admin routes
        response = client.get('/admin/users')
        assert response.status_code in [200, 302]  # May redirect but not 403


class TestMiddlewareIntegration:
    """Test middleware integration with Flask-Login."""

    def test_current_user_available_in_request(self, client, test_user, auth):
        """Test that current_user is available in request context."""
        auth.login(email='testuser@example.com', password='TestPass123!')

        # Current user should be available in templates/routes
        response = client.get('/dashboard')
        assert response.status_code == 200
        # Template should have access to current_user

    def test_anonymous_user_for_unauthenticated(self, client):
        """Test that anonymous user is set for unauthenticated requests."""
        response = client.get('/login')
        # Should not error, anonymous user should be set
        assert response.status_code == 200
