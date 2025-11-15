"""
Unit tests for encryption utilities (encrypt_value, decrypt_value).

Following TDD approach: Write tests FIRST (RED), verify they FAIL,
then implement to make them PASS.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Import encryption functions
from utils.encryption import (
    get_encryption_key,
    encrypt_value,
    decrypt_value,
    generate_encryption_key,
)


class TestGetEncryptionKey:
    """Tests for get_encryption_key() function."""

    def test_returns_bytes_when_key_configured(self):
        """Test that get_encryption_key returns bytes when DB_ENCRYPTION_KEY is set."""
        # Generate a valid key
        valid_key = generate_encryption_key()

        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            key = get_encryption_key()
            assert isinstance(key, bytes)
            assert len(key) > 0

    def test_raises_value_error_when_key_missing(self):
        """Test that get_encryption_key raises ValueError when DB_ENCRYPTION_KEY not set."""
        # Remove DB_ENCRYPTION_KEY if it exists
        with patch.dict(os.environ, {}, clear=False):
            if "DB_ENCRYPTION_KEY" in os.environ:
                del os.environ["DB_ENCRYPTION_KEY"]

            with pytest.raises(ValueError, match="DB_ENCRYPTION_KEY environment variable not set"):
                get_encryption_key()

    def test_raises_value_error_for_invalid_key(self):
        """Test that get_encryption_key raises ValueError for invalid key format."""
        invalid_key = "not-a-valid-fernet-key"

        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": invalid_key}):
            with pytest.raises(ValueError, match="DB_ENCRYPTION_KEY is invalid"):
                get_encryption_key()


class TestEncryptValue:
    """Tests for encrypt_value() function."""

    @pytest.fixture(autouse=True)
    def setup_encryption_key(self):
        """Setup valid encryption key for all tests."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            yield

    def test_encrypts_string_successfully(self):
        """Test that encrypt_value successfully encrypts a string."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            plaintext = "sk-ant-api03-test-key-12345"
            encrypted = encrypt_value(plaintext)

            # Encrypted value should be a string
            assert isinstance(encrypted, str)
            # Encrypted value should not equal plaintext
            assert encrypted != plaintext
            # Encrypted value should start with 'gAAAAA' (Fernet prefix)
            assert encrypted.startswith('gAAAAA')

    def test_returns_none_for_empty_string(self):
        """Test that encrypt_value returns None for empty string."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            assert encrypt_value("") is None
            assert encrypt_value(None) is None

    def test_encryption_roundtrip(self):
        """Test that encrypt -> decrypt returns original value."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            original = "sk-test-api-key-value"
            encrypted = encrypt_value(original)
            decrypted = decrypt_value(encrypted)

            assert decrypted == original

    def test_raises_error_when_key_missing(self):
        """Test that encrypt_value raises error when DB_ENCRYPTION_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            if "DB_ENCRYPTION_KEY" in os.environ:
                del os.environ["DB_ENCRYPTION_KEY"]

            with pytest.raises(ValueError, match="Encryption failed"):
                encrypt_value("test-value")


class TestDecryptValue:
    """Tests for decrypt_value() function."""

    @pytest.fixture(autouse=True)
    def setup_encryption_key(self):
        """Setup valid encryption key for all tests."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            yield

    def test_decrypts_encrypted_value_successfully(self):
        """Test that decrypt_value successfully decrypts an encrypted value."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            plaintext = "test-api-key-12345"
            encrypted = encrypt_value(plaintext)
            decrypted = decrypt_value(encrypted)

            assert decrypted == plaintext

    def test_returns_none_for_empty_ciphertext(self):
        """Test that decrypt_value returns None for empty ciphertext."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            assert decrypt_value("") is None
            assert decrypt_value(None) is None

    def test_raises_error_for_invalid_ciphertext(self):
        """Test that decrypt_value raises error for invalid ciphertext."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            invalid_ciphertext = "gAAAAA-invalid-ciphertext"

            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt_value(invalid_ciphertext)

    def test_raises_error_for_wrong_key(self):
        """Test that decrypt_value raises error when wrong encryption key is used."""
        # Encrypt with one key
        key1 = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key1}):
            plaintext = "test-value"
            encrypted = encrypt_value(plaintext)

        # Try to decrypt with different key
        key2 = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key2}):
            with pytest.raises(ValueError, match="Failed to decrypt value"):
                decrypt_value(encrypted)

    def test_raises_error_when_key_missing(self):
        """Test that decrypt_value raises error when DB_ENCRYPTION_KEY not set."""
        with patch.dict(os.environ, {}, clear=False):
            if "DB_ENCRYPTION_KEY" in os.environ:
                del os.environ["DB_ENCRYPTION_KEY"]

            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt_value("gAAAAA-some-encrypted-value")


class TestGenerateEncryptionKey:
    """Tests for generate_encryption_key() function."""

    def test_generates_valid_key(self):
        """Test that generate_encryption_key produces a valid Fernet key."""
        key = generate_encryption_key()

        # Should be a string
        assert isinstance(key, str)
        # Should be non-empty
        assert len(key) > 0
        # Should start with Fernet key prefix
        assert key.startswith(('gAAAAA', 'Fg'))  # Valid Fernet key formats

    def test_generates_different_keys(self):
        """Test that generate_encryption_key produces different keys each time."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        assert key1 != key2

    def test_generated_key_works_for_encryption(self):
        """Test that generated key can be used for encryption/decryption."""
        key = generate_encryption_key()

        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key}):
            plaintext = "test-value-123"
            encrypted = encrypt_value(plaintext)
            decrypted = decrypt_value(encrypted)

            assert decrypted == plaintext


class TestEncryptionSecurity:
    """Tests for encryption security properties."""

    @pytest.fixture(autouse=True)
    def setup_encryption_key(self):
        """Setup valid encryption key for all tests."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            yield

    def test_different_plaintexts_produce_different_ciphertexts(self):
        """Test that the same plaintext encrypted multiple times produces different ciphertexts."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            plaintext = "api-key-value"
            encrypted1 = encrypt_value(plaintext)
            encrypted2 = encrypt_value(plaintext)

            # Fernet includes timestamp and random IV, so same plaintext = different ciphertext
            assert encrypted1 != encrypted2
            # But both should decrypt to same plaintext
            assert decrypt_value(encrypted1) == plaintext
            assert decrypt_value(encrypted2) == plaintext

    def test_encrypted_value_not_in_plaintext(self):
        """Test that encrypted value doesn't contain the plaintext."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            plaintext = "super-secret-key-12345"
            encrypted = encrypt_value(plaintext)

            # Plaintext should not appear in encrypted value
            assert plaintext not in encrypted

    def test_handles_special_characters_in_api_key(self):
        """Test that encryption handles special characters correctly."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            special_key = "sk-ant-api03-abc_DEF-123!@#$%"
            encrypted = encrypt_value(special_key)
            decrypted = decrypt_value(encrypted)

            assert decrypted == special_key

    def test_handles_long_api_keys(self):
        """Test that encryption handles very long keys."""
        valid_key = generate_encryption_key()
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": valid_key}):
            long_key = "x" * 1000  # 1000 character key
            encrypted = encrypt_value(long_key)
            decrypted = decrypt_value(encrypted)

            assert decrypted == long_key
