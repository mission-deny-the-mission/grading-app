"""
Cookie Security Configuration Tests

Tests for environment-based cookie security flags.
Ensures secure cookies in production, flexible cookies in development.
"""

import pytest
import os
from unittest.mock import patch


class TestCookieSecurityConfiguration:
    """Test cookie security flags adapt to environment."""

    def test_production_enforces_secure_cookies(self, monkeypatch):
        """Test that production environment enforces secure cookie flags."""
        monkeypatch.setenv('FLASK_ENV', 'production')
        monkeypatch.setenv('SECRET_KEY', 'a' * 32)  # Valid production key

        # Re-import app to apply environment changes
        import importlib
        import app as app_module
        importlib.reload(app_module)

        assert app_module.app.config['SESSION_COOKIE_SECURE'] is True, \
            "Production must enforce SESSION_COOKIE_SECURE"
        assert app_module.app.config['REMEMBER_COOKIE_SECURE'] is True, \
            "Production must enforce REMEMBER_COOKIE_SECURE"

    def test_development_allows_insecure_cookies(self, monkeypatch):
        """Test that development environment allows non-HTTPS cookies."""
        monkeypatch.setenv('FLASK_ENV', 'development')

        # Re-import app to apply environment changes
        import importlib
        import app as app_module
        importlib.reload(app_module)

        assert app_module.app.config['SESSION_COOKIE_SECURE'] is False, \
            "Development should allow non-HTTPS cookies for localhost"
        assert app_module.app.config['REMEMBER_COOKIE_SECURE'] is False, \
            "Development should allow non-HTTPS cookies for localhost"

    def test_httponly_flag_always_enforced(self, monkeypatch):
        """Test that HTTPONLY flag is enforced in all environments."""
        for env in ['production', 'development', 'testing']:
            monkeypatch.setenv('FLASK_ENV', env)
            if env == 'production':
                monkeypatch.setenv('SECRET_KEY', 'a' * 32)

            import importlib
            import app as app_module
            importlib.reload(app_module)

            assert app_module.app.config['SESSION_COOKIE_HTTPONLY'] is True, \
                f"{env} must enforce SESSION_COOKIE_HTTPONLY"
            assert app_module.app.config['REMEMBER_COOKIE_HTTPONLY'] is True, \
                f"{env} must enforce REMEMBER_COOKIE_HTTPONLY"

    def test_samesite_flag_always_enforced(self, monkeypatch):
        """Test that SameSite flag is enforced in all environments."""
        for env in ['production', 'development']:
            monkeypatch.setenv('FLASK_ENV', env)
            if env == 'production':
                monkeypatch.setenv('SECRET_KEY', 'a' * 32)

            import importlib
            import app as app_module
            importlib.reload(app_module)

            assert app_module.app.config['SESSION_COOKIE_SAMESITE'] == 'Lax', \
                f"{env} must set SESSION_COOKIE_SAMESITE to Lax"

    def test_session_timeout_configured(self):
        """Test that session timeout is properly configured."""
        import app as app_module

        assert 'PERMANENT_SESSION_LIFETIME' in app_module.app.config
        assert app_module.app.config['PERMANENT_SESSION_LIFETIME'] == 1800, \
            "Session timeout should be 30 minutes (1800 seconds)"

    def test_no_hardcoded_secure_flags(self):
        """Test that cookie secure flags are not hardcoded to True."""
        # Read app.py source to ensure no hardcoded True values
        with open('app.py', 'r') as f:
            app_source = f.read()

        # Find the cookie configuration section
        lines = app_source.split('\n')
        cookie_lines = [
            line for line in lines
            if 'COOKIE_SECURE' in line and '=' in line
        ]

        # Ensure not hardcoded to True (should use IS_PRODUCTION variable)
        for line in cookie_lines:
            if 'COOKIE_SECURE' in line and not 'HTTPONLY' in line:
                assert '= True' not in line or 'IS_PRODUCTION' in line, \
                    f"Cookie secure flag should not be hardcoded: {line}"

    def test_cookie_config_consistency(self, monkeypatch):
        """Test that cookie config is consistent across session and remember cookies."""
        monkeypatch.setenv('FLASK_ENV', 'production')
        monkeypatch.setenv('SECRET_KEY', 'a' * 32)

        import importlib
        import app as app_module
        importlib.reload(app_module)

        # Both session and remember cookies should have same security settings
        assert app_module.app.config['SESSION_COOKIE_SECURE'] == app_module.app.config['REMEMBER_COOKIE_SECURE']
        assert app_module.app.config['SESSION_COOKIE_HTTPONLY'] == app_module.app.config['REMEMBER_COOKIE_HTTPONLY']
