"""
SECRET_KEY Validation Tests

Tests for SECRET_KEY security validation at application startup.
Ensures production deployments cannot start with insecure keys.
"""

import os
import pytest
from unittest.mock import patch


class TestSecretKeyValidation:
    """Test SECRET_KEY validation enforces secure configuration."""

    def test_production_rejects_default_secret_key(self):
        """Test that production environment rejects default SECRET_KEY."""
        valid_encryption_key = "b" * 44  # Fernet key is 44 chars base64
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "SECRET_KEY": "your-secret-key-here",
                "DB_ENCRYPTION_KEY": valid_encryption_key,
            },
        ):
            with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
                # Re-import app to trigger startup validation
                import importlib
                import app as app_module

                importlib.reload(app_module)

    def test_production_rejects_empty_secret_key(self):
        """Test that production environment rejects empty SECRET_KEY."""
        valid_encryption_key = "b" * 44  # Fernet key is 44 chars base64
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "SECRET_KEY": "",
                "DB_ENCRYPTION_KEY": valid_encryption_key,
            },
        ):
            with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
                import importlib
                import app as app_module

                importlib.reload(app_module)

    def test_production_rejects_short_secret_key(self):
        """Test that production environment rejects short SECRET_KEY (<32 chars)."""
        valid_encryption_key = "b" * 44  # Fernet key is 44 chars base64
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "SECRET_KEY": "short_key",
                "DB_ENCRYPTION_KEY": valid_encryption_key,
            },
        ):
            with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
                import importlib
                import app as app_module

                importlib.reload(app_module)

    def test_production_accepts_valid_secret_key(self):
        """Test that production environment accepts valid SECRET_KEY (>=32 chars)."""
        valid_key = "a" * 32  # 32 character minimum
        # Generate a valid Fernet key
        from cryptography.fernet import Fernet

        valid_encryption_key = Fernet.generate_key().decode()
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "SECRET_KEY": valid_key,
                "DB_ENCRYPTION_KEY": valid_encryption_key,
            },
        ):
            try:
                import importlib
                import app as app_module

                importlib.reload(app_module)
                assert app_module.app.secret_key == valid_key
            except ValueError:
                pytest.fail("Production should accept valid SECRET_KEY >= 32 chars")

    def test_development_allows_default_secret_key_with_warning(self, capsys):
        """Test that development environment allows default key with warning."""
        with patch.dict(
            os.environ,
            {"FLASK_ENV": "development", "SECRET_KEY": "your-secret-key-here"},
        ):
            import importlib
            import app as app_module

            importlib.reload(app_module)

            # Capture printed warning
            captured = capsys.readouterr()
            assert "WARNING" in captured.out or "WARNING" in captured.err

    def test_development_accepts_any_secret_key(self):
        """Test that development environment generates secure key even if short key provided."""
        with patch.dict(os.environ, {"FLASK_ENV": "development", "SECRET_KEY": "test"}):
            import importlib
            import app as app_module

            importlib.reload(app_module)
            # Short keys should be rejected and a secure key generated
            assert app_module.app.secret_key != "test"
            assert len(app_module.app.secret_key) >= 32

    def test_error_message_includes_generation_command(self):
        """Test that error message includes SECRET_KEY generation command."""
        valid_encryption_key = "b" * 44  # Fernet key is 44 chars base64
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "SECRET_KEY": "bad",
                "DB_ENCRYPTION_KEY": valid_encryption_key,
            },
        ):
            try:
                import importlib
                import app as app_module

                importlib.reload(app_module)
                pytest.fail("Should raise ValueError for bad SECRET_KEY")
            except ValueError as e:
                assert "python -c 'import secrets" in str(e), (
                    "Error message should include key generation command"
                )
                assert "secrets.token_hex(32)" in str(e)
