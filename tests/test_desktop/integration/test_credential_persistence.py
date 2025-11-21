"""
Integration tests for credential persistence across application restarts.

Tests cover:
- T035: Credential persistence across Flask app restarts
- T036: API key loading from keyring into Flask environment
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Import credentials module - we'll mock keyring within each test
from desktop.credentials import (
    SERVICE_NAME
)


class TestCredentialPersistence:
    """Tests for credential persistence across application restarts (T035)."""

    @patch('desktop.credentials.keyring')
    def test_credential_persistence_across_restarts(self, mock_keyring):
        """
        Test that credentials persist across simulated app restarts.

        This test simulates:
        1. First app session: Store API keys
        2. App restart (keyring instance reset)
        3. Second app session: Retrieve stored API keys
        4. Third app session: Delete and verify removal
        """
        # Import functions within test to use mocked keyring
        from desktop.credentials import set_api_key, get_api_key, delete_api_key
        # Simulate persistent storage
        persistent_storage = {}

        def mock_set_password(service, key, value):
            persistent_storage[f"{service}:{key}"] = value

        def mock_get_password(service, key):
            return persistent_storage.get(f"{service}:{key}")

        def mock_delete_password(service, key):
            storage_key = f"{service}:{key}"
            if storage_key in persistent_storage:
                del persistent_storage[storage_key]
            else:
                raise Exception("Password not found")

        mock_keyring.set_password.side_effect = mock_set_password
        mock_keyring.get_password.side_effect = mock_get_password
        mock_keyring.delete_password.side_effect = mock_delete_password

        # ===== First App Session: Store credentials =====
        providers = {
            'openrouter_api_key': 'sk-or-test-session1-12345',
            'claude_api_key': 'sk-ant-test-session1-67890',
            'openai_api_key': 'sk-openai-test-session1-abcdef'
        }

        # Store all API keys
        for provider_key, api_key in providers.items():
            result = set_api_key(provider_key, api_key)
            assert result is True, f"Failed to store {provider_key}"

        # Verify storage was called
        assert len(persistent_storage) == 3

        # ===== Simulate App Restart (keyring instance persists) =====
        # In real scenario, the keyring backend maintains the data
        # We simulate this by keeping persistent_storage intact

        # ===== Second App Session: Retrieve credentials =====
        # Retrieve all API keys and verify they match
        for provider_key, expected_key in providers.items():
            retrieved_key = get_api_key(provider_key)
            assert retrieved_key == expected_key, \
                f"Retrieved key for {provider_key} doesn't match stored key"

        # ===== Third App Session: Delete credentials =====
        # Delete one credential
        result = delete_api_key('claude_api_key')
        assert result is True

        # Verify it's gone (get_api_key returns empty string for missing keys)
        retrieved_key = get_api_key('claude_api_key')
        assert retrieved_key == "" or retrieved_key is None, "Deleted key should not be retrievable"

        # Verify others still exist
        assert get_api_key('openrouter_api_key') == providers['openrouter_api_key']
        assert get_api_key('openai_api_key') == providers['openai_api_key']

        # Verify storage state
        assert len(persistent_storage) == 2

    @patch('desktop.credentials.keyring')
    def test_persistence_with_all_providers(self, mock_keyring):
        """Test that all 7 supported providers persist correctly."""
        from desktop.credentials import set_api_key, get_api_key
        persistent_storage = {}

        def mock_set_password(service, key, value):
            persistent_storage[f"{service}:{key}"] = value

        def mock_get_password(service, key):
            return persistent_storage.get(f"{service}:{key}")

        mock_keyring.set_password.side_effect = mock_set_password
        mock_keyring.get_password.side_effect = mock_get_password

        # All 7 supported providers
        all_providers = {
            'openrouter_api_key': 'sk-or-key-123',
            'claude_api_key': 'sk-ant-key-456',
            'openai_api_key': 'sk-openai-key-789',
            'gemini_api_key': 'gemini-key-abc',
            'nanogpt_api_key': 'nano-key-def',
            'chutes_api_key': 'chutes-key-ghi',
            'zai_api_key': 'zai-key-jkl'
        }

        # Store all
        for provider_key, api_key in all_providers.items():
            result = set_api_key(provider_key, api_key)
            assert result is True

        # Simulate restart
        # (persistent_storage remains intact)

        # Retrieve all and verify
        for provider_key, expected_key in all_providers.items():
            retrieved_key = get_api_key(provider_key)
            assert retrieved_key == expected_key

    @patch('desktop.credentials.keyring')
    def test_persistence_with_empty_values(self, mock_keyring):
        """Test that empty/None values are handled correctly across restarts."""
        from desktop.credentials import set_api_key, get_api_key
        persistent_storage = {}

        def mock_set_password(service, key, value):
            persistent_storage[f"{service}:{key}"] = value

        def mock_get_password(service, key):
            return persistent_storage.get(f"{service}:{key}")

        mock_keyring.set_password.side_effect = mock_set_password
        mock_keyring.get_password.side_effect = mock_get_password

        # Store a key
        set_api_key('openrouter_api_key', 'sk-test-key')

        # Retrieve non-existent key
        retrieved = get_api_key('nonexistent_key')
        assert retrieved == "" or retrieved is None

        # Verify existing key still works
        assert get_api_key('openrouter_api_key') == 'sk-test-key'


class TestFlaskEnvironmentIntegration:
    """Tests for API key loading into Flask environment (T036)."""

    @patch('desktop.credentials.keyring')
    @patch.dict(os.environ, {}, clear=True)
    def test_api_key_loading_into_flask_environment(self, mock_keyring):
        """
        Test that API keys can be loaded from keyring into Flask environment.

        Simulates the pattern:
        1. Retrieve API keys from keyring
        2. Set them as environment variables
        3. Flask app can access them via os.getenv()
        """
        from desktop.credentials import get_api_key
        # Setup mock keyring storage
        stored_keys = {
            f"{SERVICE_NAME}:openrouter_api_key": "sk-or-flask-test-123",
            f"{SERVICE_NAME}:claude_api_key": "sk-ant-flask-test-456",
            f"{SERVICE_NAME}:openai_api_key": "sk-openai-flask-test-789"
        }

        mock_keyring.get_password.side_effect = lambda service, key: \
            stored_keys.get(f"{service}:{key}")

        # Simulate loading API keys into environment (as desktop app would do)
        provider_mappings = {
            'openrouter_api_key': 'OPENROUTER_API_KEY',
            'claude_api_key': 'CLAUDE_API_KEY',
            'openai_api_key': 'OPENAI_API_KEY'
        }

        for provider_key, env_var in provider_mappings.items():
            api_key = get_api_key(provider_key)
            if api_key:
                os.environ[env_var] = api_key

        # Verify environment variables are set
        assert os.getenv('OPENROUTER_API_KEY') == "sk-or-flask-test-123"
        assert os.getenv('CLAUDE_API_KEY') == "sk-ant-flask-test-456"
        assert os.getenv('OPENAI_API_KEY') == "sk-openai-flask-test-789"

        # Verify Flask app can access them (simulated)
        # In real scenario, Flask would use: os.getenv('OPENROUTER_API_KEY')
        flask_accessible_key = os.getenv('OPENROUTER_API_KEY')
        assert flask_accessible_key == "sk-or-flask-test-123"

    @patch('desktop.credentials.keyring')
    @patch.dict(os.environ, {}, clear=True)
    def test_environment_loading_with_missing_keys(self, mock_keyring):
        """Test that missing keys don't break environment loading."""
        from desktop.credentials import get_api_key
        # Setup mock keyring with only some keys
        stored_keys = {
            f"{SERVICE_NAME}:openrouter_api_key": "sk-or-key",
            # claude_api_key intentionally missing
        }

        mock_keyring.get_password.side_effect = lambda service, key: \
            stored_keys.get(f"{service}:{key}")

        # Load keys into environment
        provider_mappings = {
            'openrouter_api_key': 'OPENROUTER_API_KEY',
            'claude_api_key': 'CLAUDE_API_KEY'
        }

        for provider_key, env_var in provider_mappings.items():
            api_key = get_api_key(provider_key)
            if api_key:
                os.environ[env_var] = api_key

        # Verify only available key is set
        assert os.getenv('OPENROUTER_API_KEY') == "sk-or-key"
        assert os.getenv('CLAUDE_API_KEY') is None

    @patch('desktop.credentials.keyring')
    @patch.dict(os.environ, {}, clear=True)
    def test_environment_loading_all_providers(self, mock_keyring):
        """Test environment loading for all 7 supported providers."""
        from desktop.credentials import get_api_key
        # Setup mock keyring with all providers
        stored_keys = {
            f"{SERVICE_NAME}:openrouter_api_key": "sk-or-key",
            f"{SERVICE_NAME}:claude_api_key": "sk-ant-key",
            f"{SERVICE_NAME}:openai_api_key": "sk-openai-key",
            f"{SERVICE_NAME}:gemini_api_key": "gemini-key",
            f"{SERVICE_NAME}:nanogpt_api_key": "nano-key",
            f"{SERVICE_NAME}:chutes_api_key": "chutes-key",
            f"{SERVICE_NAME}:zai_api_key": "zai-key"
        }

        mock_keyring.get_password.side_effect = lambda service, key: \
            stored_keys.get(f"{service}:{key}")

        # Load all keys into environment
        provider_mappings = {
            'openrouter_api_key': 'OPENROUTER_API_KEY',
            'claude_api_key': 'CLAUDE_API_KEY',
            'openai_api_key': 'OPENAI_API_KEY',
            'gemini_api_key': 'GEMINI_API_KEY',
            'nanogpt_api_key': 'NANOGPT_API_KEY',
            'chutes_api_key': 'CHUTES_API_KEY',
            'zai_api_key': 'ZAI_API_KEY'
        }

        for provider_key, env_var in provider_mappings.items():
            api_key = get_api_key(provider_key)
            if api_key:
                os.environ[env_var] = api_key

        # Verify all environment variables
        assert os.getenv('OPENROUTER_API_KEY') == "sk-or-key"
        assert os.getenv('CLAUDE_API_KEY') == "sk-ant-key"
        assert os.getenv('OPENAI_API_KEY') == "sk-openai-key"
        assert os.getenv('GEMINI_API_KEY') == "gemini-key"
        assert os.getenv('NANOGPT_API_KEY') == "nano-key"
        assert os.getenv('CHUTES_API_KEY') == "chutes-key"
        assert os.getenv('ZAI_API_KEY') == "zai-key"

    @patch('desktop.credentials.keyring')
    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'existing-env-key'}, clear=True)
    def test_environment_override_behavior(self, mock_keyring):
        """Test that keyring keys can override existing environment variables."""
        from desktop.credentials import get_api_key
        # Setup mock keyring
        stored_keys = {
            f"{SERVICE_NAME}:openrouter_api_key": "sk-or-keyring-override"
        }

        mock_keyring.get_password.side_effect = lambda service, key: \
            stored_keys.get(f"{service}:{key}")

        # Verify existing env var
        assert os.getenv('OPENROUTER_API_KEY') == 'existing-env-key'

        # Load from keyring (should override)
        api_key = get_api_key('openrouter_api_key')
        if api_key:
            os.environ['OPENROUTER_API_KEY'] = api_key

        # Verify override
        assert os.getenv('OPENROUTER_API_KEY') == "sk-or-keyring-override"


class TestErrorRecovery:
    """Tests for error recovery in credential persistence."""

    @patch('desktop.credentials.keyring')
    def test_recovery_from_corrupted_keyring(self, mock_keyring):
        """Test that app handles corrupted keyring gracefully."""
        from desktop.credentials import get_api_key
        # Simulate keyring error
        mock_keyring.get_password.side_effect = Exception("Keyring corrupted")

        # Should return empty string instead of crashing
        result = get_api_key('openrouter_api_key')
        assert result == ""

    @patch('desktop.credentials.keyring')
    def test_recovery_from_permission_error(self, mock_keyring):
        """Test that app handles permission errors gracefully."""
        from desktop.credentials import set_api_key
        # Simulate permission error
        mock_keyring.set_password.side_effect = PermissionError("Access denied")

        # Should return False instead of crashing
        result = set_api_key('openrouter_api_key', 'test-key')
        assert result is False

    @patch('desktop.credentials.keyring')
    def test_persistence_after_failed_write(self, mock_keyring):
        """Test that failed write doesn't corrupt existing data."""
        from desktop.credentials import set_api_key, get_api_key
        persistent_storage = {
            f"{SERVICE_NAME}:openrouter_api_key": "existing-key"
        }

        def mock_get_password(service, key):
            return persistent_storage.get(f"{service}:{key}")

        # First call succeeds, second fails
        call_count = {'count': 0}

        def mock_set_password(service, key, value):
            call_count['count'] += 1
            if call_count['count'] == 1:
                persistent_storage[f"{service}:{key}"] = value
            else:
                raise Exception("Write failed")

        mock_keyring.get_password.side_effect = mock_get_password
        mock_keyring.set_password.side_effect = mock_set_password

        # First write succeeds
        result = set_api_key('claude_api_key', 'new-key')
        assert result is True

        # Second write fails
        result = set_api_key('openai_api_key', 'another-key')
        assert result is False

        # Verify existing data intact
        assert get_api_key('openrouter_api_key') == "existing-key"
        assert get_api_key('claude_api_key') == "new-key"
