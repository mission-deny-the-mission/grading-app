"""
Encryption utilities for securing API keys at rest in the database.

This module provides symmetric encryption using Fernet from the cryptography library.
All API keys are encrypted with a single DB_ENCRYPTION_KEY stored in environment variables.
"""

import os
from cryptography.fernet import Fernet, InvalidToken


def get_encryption_key() -> bytes:
    """
    Get the encryption key from environment variable.

    Returns:
        bytes: The Fernet encryption key (base64-encoded 32-byte value)

    Raises:
        ValueError: If DB_ENCRYPTION_KEY is not set or invalid
    """
    key_str = os.getenv("DB_ENCRYPTION_KEY")

    if not key_str:
        raise ValueError(
            "DB_ENCRYPTION_KEY environment variable not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )

    try:
        # Verify it's a valid Fernet key by attempting to create a cipher
        Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
        return key_str.encode() if isinstance(key_str, str) else key_str
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"DB_ENCRYPTION_KEY is invalid: {str(e)}. "
            "Generate a new one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext value using Fernet symmetric encryption.

    Args:
        plaintext: The plaintext string to encrypt (e.g., API key)

    Returns:
        str: The encrypted ciphertext (URL-safe base64 encoded)

    Raises:
        ValueError: If encryption key is not configured
    """
    if not plaintext:
        return None

    try:
        key = get_encryption_key()
        cipher = Fernet(key)
        ciphertext = cipher.encrypt(plaintext.encode())
        return ciphertext.decode()
    except Exception as e:
        raise ValueError(f"Encryption failed: {str(e)}")


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt a ciphertext value using Fernet symmetric encryption.

    Args:
        ciphertext: The encrypted ciphertext (URL-safe base64 encoded)

    Returns:
        str: The decrypted plaintext

    Raises:
        ValueError: If decryption fails or key is not configured
    """
    if not ciphertext:
        return None

    try:
        key = get_encryption_key()
        cipher = Fernet(key)
        plaintext = cipher.decrypt(ciphertext.encode())
        return plaintext.decode()
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt value: Invalid encryption key or corrupted data. "
            "Verify DB_ENCRYPTION_KEY matches the key used to encrypt the data."
        )
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key for DB_ENCRYPTION_KEY.

    This should be run once during initial setup and the result stored
    securely in the .env file.

    Returns:
        str: A base64-encoded Fernet key (can be used as DB_ENCRYPTION_KEY)
    """
    key = Fernet.generate_key()
    return key.decode()
