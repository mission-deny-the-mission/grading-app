"""
Comprehensive tests for desktop settings routes (T037-T042).
Tests API key management with OS credential manager integration.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock the desktop module and its submodules before importing app
mock_credentials = MagicMock()
mock_desktop = MagicMock()
mock_desktop.credentials = mock_credentials
sys.modules['desktop'] = mock_desktop
sys.modules['desktop.credentials'] = mock_credentials

from app import app


@pytest.fixture
def test_app():
    """Create a test Flask app."""
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key"
    })
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return test_app.test_client()


class TestShowSettings:
    """Tests for GET /desktop/settings route."""

    @patch('routes.desktop_settings.credentials')
    def test_show_settings_renders_correctly(self, mock_credentials, client):
        """Test that the settings page renders with correct template and data."""
        # Mock credential storage
        mock_credentials.get_api_key.return_value = "sk-test-1234567890abcdef"
        mock_credentials.detect_keyring_backend.return_value = {
            'backend': 'TestKeyring',
            'type': 'native',
            'secure': True,
            'requires_password': False
        }

        response = client.get('/desktop/settings')

        assert response.status_code == 200
        assert b'Desktop Settings' in response.data
        assert b'AI Provider API Keys' in response.data
        assert b'Credential Storage Information' in response.data

    @patch('routes.desktop_settings.credentials')
    def test_show_settings_displays_masked_keys(self, mock_credentials, client):
        """Test that API keys are masked (only last 4 characters shown)."""
        # Mock API keys
        mock_credentials.get_api_key.side_effect = lambda key: {
            'openrouter_api_key': 'sk-or-1234567890abcdef',
            'claude_api_key': 'sk-ant-9876543210fedcba',
            'openai_api_key': '',
        }.get(key, '')

        mock_credentials.detect_keyring_backend.return_value = {
            'backend': 'TestKeyring',
            'type': 'native',
            'secure': True,
            'requires_password': False
        }

        response = client.get('/desktop/settings')

        assert response.status_code == 200
        # Check that masked keys are displayed
        assert b'cdef' in response.data  # Last 4 of OpenRouter key
        assert b'dcba' in response.data  # Last 4 of Claude key
        # Full keys should NOT be in response
        assert b'sk-or-1234567890abcdef' not in response.data
        assert b'sk-ant-9876543210fedcba' not in response.data

    @patch('routes.desktop_settings.credentials')
    def test_show_settings_displays_backend_info(self, mock_credentials, client):
        """Test that keyring backend information is displayed."""
        mock_credentials.get_api_key.return_value = ""
        mock_credentials.detect_keyring_backend.return_value = {
            'backend': 'SecretServiceKeyring',
            'type': 'native',
            'secure': True,
            'requires_password': False
        }

        response = client.get('/desktop/settings')

        assert response.status_code == 200
        assert b'SecretServiceKeyring' in response.data
        assert b'Native OS Storage' in response.data

    @patch('routes.desktop_settings.credentials')
    def test_show_settings_handles_error_gracefully(self, mock_credentials, client):
        """Test that errors in loading settings are handled gracefully."""
        mock_credentials.get_api_key.side_effect = Exception("Keyring error")
        mock_credentials.detect_keyring_backend.side_effect = Exception("Backend error")

        response = client.get('/desktop/settings')

        # Should still render page, just with error message
        assert response.status_code == 200
        assert b'Desktop Settings' in response.data


class TestUpdateApiKeys:
    """Tests for POST /desktop/settings/api-keys route."""

    @patch('routes.desktop_settings.credentials')
    def test_update_api_keys_saves_credentials(self, mock_credentials, client):
        """Test that API keys are saved to credential manager."""
        mock_credentials.set_api_key.return_value = True

        data = {
            'openrouter_api_key': 'sk-or-new-key-123',
            'claude_api_key': 'sk-ant-new-key-456'
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert result['updated_count'] == 2
        assert 'Successfully updated 2 API key(s)' in result['message']

        # Verify credentials.set_api_key was called correctly
        assert mock_credentials.set_api_key.call_count == 2
        mock_credentials.set_api_key.assert_any_call('openrouter_api_key', 'sk-or-new-key-123')
        mock_credentials.set_api_key.assert_any_call('claude_api_key', 'sk-ant-new-key-456')

    @patch('routes.desktop_settings.credentials')
    def test_update_api_keys_accepts_form_data(self, mock_credentials, client):
        """Test that route accepts both JSON and form data."""
        mock_credentials.set_api_key.return_value = True

        data = {
            'openai_api_key': 'sk-test-openai-key'
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=data,
            content_type='application/x-www-form-urlencoded'
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert result['updated_count'] == 1

    @patch('routes.desktop_settings.credentials')
    def test_update_api_keys_handles_empty_values(self, mock_credentials, client):
        """Test that empty API key values are skipped."""
        mock_credentials.set_api_key.return_value = True

        data = {
            'openrouter_api_key': 'sk-or-key',
            'claude_api_key': '',  # Empty - should be skipped
            'openai_api_key': '   '  # Whitespace - should be skipped
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert result['updated_count'] == 1  # Only one key updated

        # Verify only non-empty key was saved
        mock_credentials.set_api_key.assert_called_once_with('openrouter_api_key', 'sk-or-key')

    @patch('routes.desktop_settings.credentials')
    def test_update_api_keys_returns_error_if_no_data(self, mock_credentials, client):
        """Test that error is returned if no data provided."""
        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert result['success'] is False

    @patch('routes.desktop_settings.credentials')
    def test_update_api_keys_handles_save_failure(self, mock_credentials, client):
        """Test that save failures are handled and reported."""
        mock_credentials.set_api_key.return_value = False

        data = {
            'openrouter_api_key': 'sk-or-key',
            'claude_api_key': 'sk-ant-key'
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 500
        result = json.loads(response.data)
        assert result['success'] is False
        assert 'failed to save' in result['message'].lower()

    @patch('routes.desktop_settings.credentials')
    def test_update_api_keys_handles_exception(self, mock_credentials, client):
        """Test that exceptions are caught and reported."""
        mock_credentials.set_api_key.side_effect = Exception("Storage error")

        data = {
            'openrouter_api_key': 'sk-or-key'
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 500
        result = json.loads(response.data)
        assert result['success'] is False
        assert 'Failed to update API keys' in result['message']


class TestDeleteApiKey:
    """Tests for DELETE /desktop/settings/api-keys/<provider> route."""

    @patch('routes.desktop_settings.credentials')
    def test_delete_api_key_removes_credential(self, mock_credentials, client):
        """Test that API key is deleted from credential manager."""
        mock_credentials.delete_api_key.return_value = True

        response = client.delete('/desktop/settings/api-keys/openrouter_api_key')

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'deleted' in result['message'].lower()
        assert 'OpenRouter' in result['message']

        # Verify credentials.delete_api_key was called
        mock_credentials.delete_api_key.assert_called_once_with('openrouter_api_key')

    @patch('routes.desktop_settings.credentials')
    def test_delete_api_key_validates_provider(self, mock_credentials, client):
        """Test that invalid provider names are rejected."""
        response = client.delete('/desktop/settings/api-keys/invalid_provider_key')

        assert response.status_code == 400
        result = json.loads(response.data)
        assert result['success'] is False
        assert 'Unknown provider' in result['message']

        # Verify delete was NOT called
        mock_credentials.delete_api_key.assert_not_called()

    @patch('routes.desktop_settings.credentials')
    def test_delete_api_key_handles_delete_failure(self, mock_credentials, client):
        """Test that delete failures are handled."""
        mock_credentials.delete_api_key.return_value = False

        response = client.delete('/desktop/settings/api-keys/claude_api_key')

        assert response.status_code == 500
        result = json.loads(response.data)
        assert result['success'] is False
        assert 'Failed to delete' in result['message']

    @patch('routes.desktop_settings.credentials')
    def test_delete_api_key_handles_exception(self, mock_credentials, client):
        """Test that exceptions are caught and reported."""
        mock_credentials.delete_api_key.side_effect = Exception("Keyring error")

        response = client.delete('/desktop/settings/api-keys/openai_api_key')

        assert response.status_code == 500
        result = json.loads(response.data)
        assert result['success'] is False
        assert 'Failed to delete API key' in result['message']

    @patch('routes.desktop_settings.credentials')
    def test_delete_api_key_works_for_all_providers(self, mock_credentials, client):
        """Test that all supported providers can be deleted."""
        mock_credentials.delete_api_key.return_value = True

        providers = [
            'openrouter_api_key',
            'claude_api_key',
            'openai_api_key',
            'gemini_api_key',
            'nanogpt_api_key',
            'chutes_api_key',
            'zai_api_key'
        ]

        for provider in providers:
            response = client.delete(f'/desktop/settings/api-keys/{provider}')
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True


class TestApiKeyMasking:
    """Tests for API key masking functionality."""

    def test_mask_api_key_shows_last_4_chars(self):
        """Test that masking shows only last 4 characters."""
        from routes.desktop_settings import mask_api_key

        key = "sk-or-1234567890abcdef"
        masked = mask_api_key(key)

        assert masked.endswith("cdef")
        assert len(masked) == len(key)
        assert masked.count("*") == len(key) - 4

    def test_mask_api_key_handles_short_keys(self):
        """Test that short keys are handled correctly."""
        from routes.desktop_settings import mask_api_key

        assert mask_api_key("abc") == ""
        assert mask_api_key("abcd") == "abcd"
        assert mask_api_key("abcde") == "*bcde"  # Masks all but last 4

    def test_mask_api_key_handles_empty_input(self):
        """Test that empty/None input returns empty string."""
        from routes.desktop_settings import mask_api_key

        assert mask_api_key("") == ""
        assert mask_api_key(None) == ""

    def test_mask_api_key_preserves_length(self):
        """Test that masked key has same length as original."""
        from routes.desktop_settings import mask_api_key

        keys = [
            "sk-or-short",
            "sk-ant-medium-length-key",
            "sk-openai-very-long-api-key-with-many-characters"
        ]

        for key in keys:
            masked = mask_api_key(key)
            if len(key) >= 4:
                assert len(masked) == len(key)


class TestErrorHandling:
    """Tests for error handling across all routes."""

    @patch('routes.desktop_settings.credentials')
    def test_invalid_json_in_post_request(self, mock_credentials, client):
        """Test that invalid JSON is handled gracefully."""
        response = client.post(
            '/desktop/settings/api-keys',
            data='invalid json{',
            content_type='application/json'
        )

        # Should handle the error
        assert response.status_code in [400, 500]

    @patch('routes.desktop_settings.credentials')
    def test_missing_content_type(self, mock_credentials, client):
        """Test that missing content-type header is handled."""
        mock_credentials.set_api_key.return_value = True

        response = client.post(
            '/desktop/settings/api-keys',
            data={'openrouter_api_key': 'test-key'}
        )

        # Should still work with form data
        assert response.status_code == 200

    @patch('routes.desktop_settings.credentials')
    def test_special_characters_in_api_keys(self, mock_credentials, client):
        """Test that API keys with special characters are handled."""
        mock_credentials.set_api_key.return_value = True

        data = {
            'openrouter_api_key': 'sk-or-key!@#$%^&*()',
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True


class TestIntegration:
    """Integration tests for complete workflows."""

    @patch('routes.desktop_settings.credentials')
    def test_save_and_delete_workflow(self, mock_credentials, client):
        """Test complete workflow: save API key, verify, delete, verify."""
        # Mock initial state - no key
        mock_credentials.get_api_key.return_value = ""
        mock_credentials.set_api_key.return_value = True
        mock_credentials.delete_api_key.return_value = True
        mock_credentials.detect_keyring_backend.return_value = {
            'backend': 'TestKeyring',
            'type': 'native',
            'secure': True,
            'requires_password': False
        }

        # Step 1: Save API key
        save_response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps({'openrouter_api_key': 'sk-or-test-key'}),
            content_type='application/json'
        )
        assert save_response.status_code == 200
        save_result = json.loads(save_response.data)
        assert save_result['success'] is True

        # Step 2: Delete API key
        delete_response = client.delete('/desktop/settings/api-keys/openrouter_api_key')
        assert delete_response.status_code == 200
        delete_result = json.loads(delete_response.data)
        assert delete_result['success'] is True

    @patch('routes.desktop_settings.credentials')
    def test_update_multiple_providers_simultaneously(self, mock_credentials, client):
        """Test updating multiple provider keys in one request."""
        mock_credentials.set_api_key.return_value = True

        data = {
            'openrouter_api_key': 'sk-or-key',
            'claude_api_key': 'sk-ant-key',
            'openai_api_key': 'sk-openai-key',
            'gemini_api_key': 'gemini-key'
        }

        response = client.post(
            '/desktop/settings/api-keys',
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert result['updated_count'] == 4
        assert mock_credentials.set_api_key.call_count == 4
