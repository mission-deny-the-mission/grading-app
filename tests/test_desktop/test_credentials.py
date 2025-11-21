"""
Unit tests for the credential storage module.

This module tests the credential storage functionality including:
- Keyring initialization with fallback
- API key storage, retrieval, and deletion
- Backend detection logic
- Error handling for various failure scenarios
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock the required modules before importing desktop.credentials
mock_keyring = MagicMock()
mock_keyrings = MagicMock()
mock_cryptfile_module = MagicMock()
mock_cryptfile_class = MagicMock()
mock_cryptfile_module.CryptFileKeyring = mock_cryptfile_class

# Store original modules to restore later
_original_modules = {}
for mod_name in ['keyring', 'keyrings', 'keyrings.cryptfile', 'keyrings.cryptfile.cryptfile']:
    _original_modules[mod_name] = sys.modules.get(mod_name)

sys.modules['keyring'] = mock_keyring
sys.modules['keyrings'] = mock_keyrings
sys.modules['keyrings.cryptfile'] = mock_cryptfile_module
sys.modules['keyrings.cryptfile.cryptfile'] = mock_cryptfile_module

# Import the module under test
from desktop.credentials import (
    initialize_keyring,
    set_api_key,
    get_api_key,
    delete_api_key,
    detect_keyring_backend,
    SERVICE_NAME
)


# Fixture to cleanup sys.modules after all tests in this module
@pytest.fixture(scope='module', autouse=True)
def cleanup_module_mocks():
    """Cleanup sys.modules mocks after all tests complete to prevent test isolation issues."""
    yield  # Run all tests first
    # Restore original modules or remove mocks
    for mod_name, original_mod in _original_modules.items():
        if original_mod is None:
            # Module didn't exist before, remove it
            sys.modules.pop(mod_name, None)
        else:
            # Restore original module
            sys.modules[mod_name] = original_mod


class TestInitializeKeyring:
    """Tests for initialize_keyring function."""

    @patch('desktop.credentials.keyring')
    def test_initialize_with_system_keyring_success(self, mock_keyring):
        """Test successful initialization with system keyring."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'WinVaultKeyring'
        mock_keyring.get_keyring.return_value = mock_backend

        initialize_keyring()

        # get_keyring is called twice: once to check, once for logging
        assert mock_keyring.get_keyring.call_count == 2
        mock_keyring.set_keyring.assert_not_called()

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.CryptFileKeyring')
    def test_initialize_fallback_to_cryptfile(self, mock_cryptfile, mock_keyring):
        """Test fallback to CryptFileKeyring when system keyring unavailable."""
        mock_keyring.get_keyring.side_effect = Exception("No keyring available")
        mock_cryptfile_instance = Mock()
        mock_cryptfile.return_value = mock_cryptfile_instance

        initialize_keyring()

        mock_keyring.get_keyring.assert_called_once()
        mock_keyring.set_keyring.assert_called_once()
        # Check that CryptFileKeyring was instantiated and set
        mock_cryptfile.assert_called_once()
        mock_keyring.set_keyring.assert_called_once_with(mock_cryptfile_instance)

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_initialize_logs_system_keyring(self, mock_logger, mock_keyring):
        """Test that initialization logs the keyring backend being used."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'SecretServiceKeyring'
        mock_keyring.get_keyring.return_value = mock_backend

        initialize_keyring()

        mock_logger.info.assert_called_once()
        assert 'SecretServiceKeyring' in str(mock_logger.info.call_args)

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_initialize_logs_fallback(self, mock_logger, mock_keyring):
        """Test that initialization logs when falling back to encrypted file."""
        mock_keyring.get_keyring.side_effect = RuntimeError("D-Bus not available")

        initialize_keyring()

        # Should log warning and info messages
        assert mock_logger.warning.called
        assert mock_logger.info.called
        warning_msg = str(mock_logger.warning.call_args)
        assert 'unavailable' in warning_msg.lower()


class TestSetApiKey:
    """Tests for set_api_key function."""

    @patch('desktop.credentials.keyring')
    def test_set_api_key_success(self, mock_keyring):
        """Test successful API key storage."""
        result = set_api_key('openrouter_api_key', 'test-key-12345')

        assert result is True
        mock_keyring.set_password.assert_called_once_with(
            SERVICE_NAME, 'openrouter_api_key', 'test-key-12345'
        )

    @patch('desktop.credentials.keyring')
    def test_set_api_key_various_providers(self, mock_keyring):
        """Test storing API keys for various providers."""
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
            result = set_api_key(provider, f'{provider}-value')
            assert result is True

        assert mock_keyring.set_password.call_count == len(providers)

    @patch('desktop.credentials.keyring')
    def test_set_api_key_failure(self, mock_keyring):
        """Test API key storage failure handling."""
        mock_keyring.set_password.side_effect = Exception("Keyring locked")

        result = set_api_key('openrouter_api_key', 'test-key-12345')

        assert result is False
        mock_keyring.set_password.assert_called_once()

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_set_api_key_logs_success(self, mock_logger, mock_keyring):
        """Test that successful storage is logged."""
        set_api_key('claude_api_key', 'sk-test-123')

        mock_logger.info.assert_called_once()
        info_msg = str(mock_logger.info.call_args)
        assert 'claude_api_key' in info_msg

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_set_api_key_logs_error(self, mock_logger, mock_keyring):
        """Test that storage errors are logged."""
        mock_keyring.set_password.side_effect = PermissionError("Access denied")

        set_api_key('openai_api_key', 'sk-test-456')

        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert 'openai_api_key' in error_msg
        assert 'Failed' in error_msg


class TestGetApiKey:
    """Tests for get_api_key function."""

    @patch('desktop.credentials.keyring')
    def test_get_api_key_success(self, mock_keyring):
        """Test successful API key retrieval."""
        mock_keyring.get_password.return_value = 'test-key-12345'

        result = get_api_key('openrouter_api_key')

        assert result == 'test-key-12345'
        mock_keyring.get_password.assert_called_once_with(
            SERVICE_NAME, 'openrouter_api_key'
        )

    @patch('desktop.credentials.keyring')
    def test_get_api_key_missing(self, mock_keyring):
        """Test retrieval when key doesn't exist (returns None)."""
        mock_keyring.get_password.return_value = None

        result = get_api_key('nonexistent_api_key')

        assert result == ""
        mock_keyring.get_password.assert_called_once()

    @patch('desktop.credentials.keyring')
    def test_get_api_key_empty_string(self, mock_keyring):
        """Test retrieval when key exists but is empty string."""
        mock_keyring.get_password.return_value = ""

        result = get_api_key('openrouter_api_key')

        assert result == ""

    @patch('desktop.credentials.keyring')
    def test_get_api_key_failure(self, mock_keyring):
        """Test API key retrieval failure handling."""
        mock_keyring.get_password.side_effect = Exception("Keyring unavailable")

        result = get_api_key('claude_api_key')

        assert result == ""
        mock_keyring.get_password.assert_called_once()

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_get_api_key_logs_error(self, mock_logger, mock_keyring):
        """Test that retrieval errors are logged."""
        mock_keyring.get_password.side_effect = RuntimeError("Backend error")

        get_api_key('gemini_api_key')

        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert 'gemini_api_key' in error_msg
        assert 'Failed' in error_msg


class TestDeleteApiKey:
    """Tests for delete_api_key function."""

    @patch('desktop.credentials.keyring')
    def test_delete_api_key_success(self, mock_keyring):
        """Test successful API key deletion."""
        result = delete_api_key('openrouter_api_key')

        assert result is True
        mock_keyring.delete_password.assert_called_once_with(
            SERVICE_NAME, 'openrouter_api_key'
        )

    @patch('desktop.credentials.keyring')
    def test_delete_api_key_failure(self, mock_keyring):
        """Test API key deletion failure handling."""
        mock_keyring.delete_password.side_effect = Exception("Key not found")

        result = delete_api_key('nonexistent_api_key')

        assert result is False
        mock_keyring.delete_password.assert_called_once()

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_delete_api_key_logs_success(self, mock_logger, mock_keyring):
        """Test that successful deletion is logged."""
        delete_api_key('chutes_api_key')

        mock_logger.info.assert_called_once()
        info_msg = str(mock_logger.info.call_args)
        assert 'chutes_api_key' in info_msg
        assert 'Deleted' in info_msg

    @patch('desktop.credentials.keyring')
    @patch('desktop.credentials.logger')
    def test_delete_api_key_logs_error(self, mock_logger, mock_keyring):
        """Test that deletion errors are logged."""
        mock_keyring.delete_password.side_effect = PermissionError("Access denied")

        delete_api_key('zai_api_key')

        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert 'zai_api_key' in error_msg
        assert 'Failed' in error_msg


class TestDetectKeyringBackend:
    """Tests for detect_keyring_backend function."""

    @patch('desktop.credentials.keyring')
    def test_detect_windows_native_backend(self, mock_keyring):
        """Test detection of Windows native keyring."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'WinVaultKeyring'
        mock_keyring.get_keyring.return_value = mock_backend

        result = detect_keyring_backend()

        assert result['backend'] == 'WinVaultKeyring'
        assert result['type'] == 'native'
        assert result['secure'] is True
        assert result['requires_password'] is False

    @patch('desktop.credentials.keyring')
    def test_detect_macos_native_backend(self, mock_keyring):
        """Test detection of macOS native keyring."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'Keyring'
        mock_keyring.get_keyring.return_value = mock_backend

        result = detect_keyring_backend()

        assert result['backend'] == 'Keyring'
        assert result['type'] == 'native'
        assert result['secure'] is True
        assert result['requires_password'] is False

    @patch('desktop.credentials.keyring')
    def test_detect_linux_secret_service_backend(self, mock_keyring):
        """Test detection of Linux Secret Service keyring."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'SecretServiceKeyring'
        mock_keyring.get_keyring.return_value = mock_backend

        result = detect_keyring_backend()

        assert result['backend'] == 'SecretServiceKeyring'
        assert result['type'] == 'native'
        assert result['secure'] is True
        assert result['requires_password'] is False

    @patch('desktop.credentials.keyring')
    def test_detect_linux_kwallet_backend(self, mock_keyring):
        """Test detection of KDE KWallet backend."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'KWallet5Keyring'
        mock_keyring.get_keyring.return_value = mock_backend

        result = detect_keyring_backend()

        assert result['backend'] == 'KWallet5Keyring'
        assert result['type'] == 'native'
        assert result['secure'] is True
        assert result['requires_password'] is False

    @patch('desktop.credentials.keyring')
    def test_detect_cryptfile_fallback_backend(self, mock_keyring):
        """Test detection of CryptFile fallback backend."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'CryptFileKeyring'
        mock_keyring.get_keyring.return_value = mock_backend

        result = detect_keyring_backend()

        assert result['backend'] == 'CryptFileKeyring'
        assert result['type'] == 'fallback'
        assert result['secure'] is True
        assert result['requires_password'] is True

    @patch('desktop.credentials.keyring')
    def test_detect_insecure_backend(self, mock_keyring):
        """Test detection of insecure fallback backend."""
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'PlaintextKeyring'
        mock_keyring.get_keyring.return_value = mock_backend

        result = detect_keyring_backend()

        assert result['backend'] == 'PlaintextKeyring'
        assert result['type'] == 'fallback'
        assert result['secure'] is False
        assert result['requires_password'] is False


class TestServiceName:
    """Tests for SERVICE_NAME constant."""

    def test_service_name_constant(self):
        """Test that SERVICE_NAME is correctly defined."""
        assert SERVICE_NAME == "grading-app"


class TestIntegration:
    """Integration tests for credential storage workflow."""

    @patch('desktop.credentials.keyring')
    def test_full_credential_lifecycle(self, mock_keyring):
        """Test complete lifecycle: initialize, set, get, delete."""
        # Initialize
        mock_backend = Mock()
        mock_backend.__class__.__name__ = 'SecretServiceKeyring'
        mock_keyring.get_keyring.return_value = mock_backend
        initialize_keyring()

        # Set
        result = set_api_key('openrouter_api_key', 'sk-test-12345')
        assert result is True

        # Get
        mock_keyring.get_password.return_value = 'sk-test-12345'
        api_key = get_api_key('openrouter_api_key')
        assert api_key == 'sk-test-12345'

        # Delete
        result = delete_api_key('openrouter_api_key')
        assert result is True

        # Verify get returns empty after deletion
        mock_keyring.get_password.return_value = None
        api_key = get_api_key('openrouter_api_key')
        assert api_key == ""

    @patch('desktop.credentials.keyring')
    def test_multiple_providers_management(self, mock_keyring):
        """Test managing multiple provider API keys simultaneously."""
        providers = {
            'openrouter_api_key': 'or-key-123',
            'claude_api_key': 'claude-key-456',
            'openai_api_key': 'openai-key-789',
        }

        # Set all keys
        for provider, key in providers.items():
            result = set_api_key(provider, key)
            assert result is True

        # Retrieve all keys
        for provider, expected_key in providers.items():
            mock_keyring.get_password.return_value = expected_key
            actual_key = get_api_key(provider)
            assert actual_key == expected_key

        # Delete all keys
        for provider in providers.keys():
            result = delete_api_key(provider)
            assert result is True

        assert mock_keyring.set_password.call_count == 3
        assert mock_keyring.get_password.call_count == 3
        assert mock_keyring.delete_password.call_count == 3
