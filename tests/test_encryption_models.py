"""
Unit tests for Config model encryption properties.

Tests verify that API keys are properly encrypted when saved to the database
and decrypted when loaded from the database.
"""

import os
import pytest
from unittest.mock import patch
from app import app, db
from models import Config
from utils.encryption import encrypt_value, decrypt_value, generate_encryption_key


@pytest.fixture
def app_context():
    """Create an application context for database tests."""
    with app.app_context():
        # Create tables
        db.create_all()
        yield
        # Cleanup after test
        db.session.remove()
        db.drop_all()


@pytest.fixture
def encryption_key():
    """Generate a valid encryption key for testing."""
    key = generate_encryption_key()
    with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key}):
        yield key


class TestConfigEncryptionProperties:
    """Test Config model encryption/decryption properties."""

    def test_openrouter_key_encrypted_on_save(self, app_context, encryption_key):
        """Test that OpenRouter API key is encrypted when saved to database."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            plaintext_key = "sk-or-v1-" + ("a" * 64)

            # Set the key via property
            config.openrouter_api_key = plaintext_key
            db.session.add(config)
            db.session.commit()

            # Verify the underlying encrypted field contains ciphertext
            assert config._openrouter_api_key is not None
            assert config._openrouter_api_key != plaintext_key
            assert config._openrouter_api_key.startswith("gAAAAA")

    def test_openrouter_key_decrypted_on_load(self, app_context, encryption_key):
        """Test that OpenRouter API key is decrypted when retrieved from database."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            plaintext_key = "sk-or-v1-" + ("a" * 64)

            # Create and save config
            config = Config()
            config.openrouter_api_key = plaintext_key
            db.session.add(config)
            db.session.commit()
            config_id = config.id

            # Clear session to force database read
            db.session.expunge_all()

            # Load config from database
            loaded_config = Config.query.get(config_id)

            # Verify the property returns decrypted value
            assert loaded_config.openrouter_api_key == plaintext_key

    def test_claude_key_encrypted_on_save(self, app_context, encryption_key):
        """Test that Claude API key is encrypted when saved to database."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            plaintext_key = "sk-ant-api03-" + ("A" * 95)

            config.claude_api_key = plaintext_key
            db.session.add(config)
            db.session.commit()

            # Verify encryption
            assert config._claude_api_key is not None
            assert config._claude_api_key != plaintext_key
            assert config._claude_api_key.startswith("gAAAAA")

    def test_multiple_keys_all_encrypted(self, app_context, encryption_key):
        """Test that multiple API keys are all encrypted independently."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()

            # Set multiple keys
            config.openrouter_api_key = "sk-or-v1-" + ("a" * 64)
            config.claude_api_key = "sk-ant-api03-" + ("b" * 95)
            config.gemini_api_key = "c" * 39
            config.openai_api_key = "sk-" + ("d" * 48)

            db.session.add(config)
            db.session.commit()

            # Verify all are encrypted
            assert config._openrouter_api_key.startswith("gAAAAA")
            assert config._claude_api_key.startswith("gAAAAA")
            assert config._gemini_api_key.startswith("gAAAAA")
            assert config._openai_api_key.startswith("gAAAAA")

            # Verify all are different ciphertexts (due to random IV)
            encrypted_values = [
                config._openrouter_api_key,
                config._claude_api_key,
                config._gemini_api_key,
                config._openai_api_key,
            ]
            assert len(set(encrypted_values)) == 4  # All unique

    def test_none_key_remains_none(self, app_context, encryption_key):
        """Test that None API keys remain None (not encrypted)."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            config.openrouter_api_key = None

            db.session.add(config)
            db.session.commit()

            # Verify None is stored as None
            assert config._openrouter_api_key is None
            assert config.openrouter_api_key is None

    def test_empty_string_key_remains_none(self, app_context, encryption_key):
        """Test that empty string API keys are stored as None."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            config.openrouter_api_key = ""

            db.session.add(config)
            db.session.commit()

            # Verify empty string is stored as None
            assert config._openrouter_api_key is None

    def test_roundtrip_encryption_preserves_value(self, app_context, encryption_key):
        """Test complete roundtrip: save with encryption, load with decryption."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            original_keys = {
                "openrouter": "sk-or-v1-" + ("a" * 64),
                "claude": "sk-ant-api03-" + ("b" * 95),
                "gemini": "c" * 39,
                "openai": "sk-" + ("d" * 48),
            }

            # Save
            config = Config()
            config.openrouter_api_key = original_keys["openrouter"]
            config.claude_api_key = original_keys["claude"]
            config.gemini_api_key = original_keys["gemini"]
            config.openai_api_key = original_keys["openai"]
            db.session.add(config)
            db.session.commit()
            config_id = config.id

            # Load from fresh session
            db.session.expunge_all()
            loaded = Config.query.get(config_id)

            # Verify all keys decrypted to original values
            assert loaded.openrouter_api_key == original_keys["openrouter"]
            assert loaded.claude_api_key == original_keys["claude"]
            assert loaded.gemini_api_key == original_keys["gemini"]
            assert loaded.openai_api_key == original_keys["openai"]


class TestConfigEncryptionWithWrongKey:
    """Test Config model behavior with wrong encryption keys."""

    def test_decryption_fails_with_wrong_key(self, app_context):
        """Test that decryption fails if wrong encryption key is used."""
        key1 = generate_encryption_key()

        # Encrypt with key1
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key1}):
            config = Config()
            config.openrouter_api_key = "sk-or-v1-" + ("a" * 64)
            db.session.add(config)
            db.session.commit()
            config_id = config.id

        # Try to load with key2
        key2 = generate_encryption_key()
        db.session.expunge_all()

        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key2}):
            loaded = Config.query.get(config_id)
            # Property should return None when decryption fails (graceful degradation)
            assert loaded.openrouter_api_key is None


class TestConfigEncryptionEdgeCases:
    """Test edge cases in Config encryption."""

    def test_special_characters_in_api_key(self, app_context, encryption_key):
        """Test that special characters in API keys are preserved."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            special_key = "sk-ant-api03-" + ("A" * 50) + "_-" + ("B" * 43)

            config.claude_api_key = special_key
            db.session.add(config)
            db.session.commit()
            config_id = config.id

            db.session.expunge_all()
            loaded = Config.query.get(config_id)

            assert loaded.claude_api_key == special_key

    def test_very_long_api_key(self, app_context, encryption_key):
        """Test that very long API keys can be encrypted and stored."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            # Fernet ciphertext is longer than plaintext, so test within limits
            # 300 chars plaintext → ~484 chars encrypted (fits in VARCHAR(500))
            long_key = "x" * 300

            config.openrouter_api_key = long_key
            db.session.add(config)
            db.session.commit()
            config_id = config.id

            # Verify it was stored (DB column is VARCHAR(500))
            assert len(config._openrouter_api_key) <= 500

            db.session.expunge_all()
            loaded = Config.query.get(config_id)

            assert loaded.openrouter_api_key == long_key

    def test_update_api_key_re_encrypts(self, app_context, encryption_key):
        """Test that updating an API key re-encrypts with new IV."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            key1 = "sk-or-v1-" + ("a" * 64)
            key2 = "sk-or-v1-" + ("b" * 64)

            # Set initial key
            config.openrouter_api_key = key1
            db.session.add(config)
            db.session.commit()
            encrypted1 = config._openrouter_api_key

            # Update key
            config.openrouter_api_key = key2
            db.session.commit()
            encrypted2 = config._openrouter_api_key

            # Ciphertexts should be different (due to random IV)
            assert encrypted1 != encrypted2
            # But both should decrypt correctly
            assert decrypt_value(encrypted1) == key1
            assert decrypt_value(encrypted2) == key2


class TestConfigDefaultValues:
    """Test Config model default values work with encryption."""

    def test_new_config_has_none_keys(self, app_context, encryption_key):
        """Test that new Config instance has None keys."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()

            assert config.openrouter_api_key is None
            assert config.claude_api_key is None
            assert config.gemini_api_key is None

    def test_config_with_partial_keys(self, app_context, encryption_key):
        """Test Config with some keys set and others None."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config = Config()
            config.openrouter_api_key = "sk-or-v1-" + ("a" * 64)
            config.claude_api_key = None
            config.gemini_api_key = "g" * 39

            db.session.add(config)
            db.session.commit()
            config_id = config.id

            db.session.expunge_all()
            loaded = Config.query.get(config_id)

            assert loaded.openrouter_api_key == "sk-or-v1-" + ("a" * 64)
            assert loaded.claude_api_key is None
            assert loaded.gemini_api_key == "g" * 39
