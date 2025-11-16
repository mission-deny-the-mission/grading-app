"""
Credential storage module for the grading application.

This module provides secure storage and retrieval of API keys using the OS credential manager.
It uses the keyring library with keyrings.cryptfile as a fallback for systems without a native
credential storage system.

Supported provider keys:
- openrouter_api_key
- claude_api_key
- openai_api_key
- gemini_api_key
- nanogpt_api_key
- chutes_api_key
- zai_api_key
"""

import keyring
from keyrings.cryptfile.cryptfile import CryptFileKeyring
import logging

logger = logging.getLogger(__name__)

SERVICE_NAME = "grading-app"


def initialize_keyring():
    """Initialize keyring backend, fallback to encrypted file if needed."""
    try:
        keyring.get_keyring()
        logger.info(f"Using keyring backend: {keyring.get_keyring().__class__.__name__}")
    except Exception as e:
        logger.warning(f"System keyring unavailable: {e}")
        logger.info("Falling back to encrypted file storage")
        keyring.set_keyring(CryptFileKeyring())


def set_api_key(provider_key: str, api_key: str) -> bool:
    """Store API key in OS credential manager."""
    try:
        keyring.set_password(SERVICE_NAME, provider_key, api_key)
        logger.info(f"Stored API key for {provider_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to store API key for {provider_key}: {e}")
        return False


def get_api_key(provider_key: str) -> str:
    """Retrieve API key from OS credential manager."""
    try:
        api_key = keyring.get_password(SERVICE_NAME, provider_key)
        return api_key if api_key else ""
    except Exception as e:
        logger.error(f"Failed to retrieve API key for {provider_key}: {e}")
        return ""


def delete_api_key(provider_key: str) -> bool:
    """Delete API key from OS credential manager."""
    try:
        keyring.delete_password(SERVICE_NAME, provider_key)
        logger.info(f"Deleted API key for {provider_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete API key for {provider_key}: {e}")
        return False


def detect_keyring_backend():
    """Detect available keyring backend."""
    backend = keyring.get_keyring()
    backend_name = backend.__class__.__name__

    native_backends = {
        'WinVaultKeyring',
        'Keyring',  # macOS
        'SecretServiceKeyring',
        'KWallet5Keyring',
    }

    is_native = backend_name in native_backends
    is_cryptfile = 'CryptFile' in backend_name

    return {
        'backend': backend_name,
        'type': 'native' if is_native else 'fallback',
        'secure': is_native or is_cryptfile,
        'requires_password': is_cryptfile
    }
