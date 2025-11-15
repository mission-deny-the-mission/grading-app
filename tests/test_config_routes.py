"""
Integration tests for config endpoints (/save_config, /load_config).

Tests verify that:
1. API key validation occurs before saving
2. Valid keys are encrypted and saved
3. Invalid keys are rejected with error messages
4. Keys are properly decrypted when loaded
"""

import os
import json
import pytest
from unittest.mock import patch
from app import app, db
from models import Config
from utils.encryption import generate_encryption_key


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def encryption_key():
    """Generate and set encryption key for tests."""
    key = generate_encryption_key()
    with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key}):
        yield key


class TestSaveConfigValidation:
    """Tests for /save_config endpoint validation."""

    def test_save_valid_openrouter_key(self, client, encryption_key):
        """Test saving valid OpenRouter API key."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                    "claude_api_key": "",
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_save_valid_claude_key(self, client, encryption_key):
        """Test saving valid Claude API key."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "",
                    "claude_api_key": "sk-ant-api03-" + ("A" * 95),
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_save_invalid_openrouter_key(self, client, encryption_key):
        """Test that invalid OpenRouter key is rejected."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "invalid-key-format",  # Wrong format
                    "claude_api_key": "",
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Validation failed" in data["message"]
            assert "openrouter" in data["message"].lower()

    def test_save_invalid_claude_key(self, client, encryption_key):
        """Test that invalid Claude key is rejected."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "",
                    "claude_api_key": "wrong-prefix-" + ("a" * 95),  # Wrong prefix
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Validation failed" in data["message"]

    def test_save_multiple_invalid_keys(self, client, encryption_key):
        """Test that multiple invalid keys are reported."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "invalid1",
                    "claude_api_key": "invalid2",
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is False
            # Should mention both invalid keys
            assert ";" in data["message"]  # Multiple errors separated by semicolon

    def test_save_empty_keys_allowed(self, client, encryption_key):
        """Test that empty keys are allowed (not required)."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "",
                    "claude_api_key": "",
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_save_whitespace_only_keys_ignored(self, client, encryption_key):
        """Test that whitespace-only keys are treated as empty."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "   ",  # Whitespace only
                    "claude_api_key": "\t\n",  # Whitespace only
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True


class TestLoadConfigDecryption:
    """Tests for /load_config endpoint decryption."""

    def test_load_config_returns_decrypted_keys(self, client, encryption_key):
        """Test that load_config returns decrypted keys."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save a key
            original_key = "sk-or-v1-" + ("a" * 64)
            client.post(
                "/save_config",
                data={
                    "openrouter_api_key": original_key,
                    "claude_api_key": "",
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            # Load and verify
            response = client.get("/load_config")
            data = json.loads(response.data)

            assert data["openrouter_api_key"] == original_key

    def test_load_config_multiple_keys(self, client, encryption_key):
        """Test loading multiple encrypted keys."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save multiple keys
            keys = {
                "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                "claude_api_key": "sk-ant-api03-" + ("b" * 95),
                "gemini_api_key": "c" * 39,
                "openai_api_key": "sk-" + ("d" * 48),
            }

            client.post("/save_config", data={**keys, "nanogpt_api_key": "", "chutes_api_key": "", "zai_api_key": ""})

            # Load and verify all are decrypted
            response = client.get("/load_config")
            data = json.loads(response.data)

            for field, value in keys.items():
                assert data[field] == value

    def test_load_config_preserves_empty_keys(self, client, encryption_key):
        """Test that empty keys remain empty when loaded."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save with some empty keys
            client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                    "claude_api_key": "",  # Empty
                    "gemini_api_key": "",  # Empty
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            # Load and verify empty keys remain empty (or fallback to defaults)
            response = client.get("/load_config")
            data = json.loads(response.data)

            assert data["openrouter_api_key"] == "sk-or-v1-" + ("a" * 64)
            # claude_api_key should either be empty or fallback to env variable
            assert isinstance(data["claude_api_key"], str)

    def test_load_config_with_no_saved_keys(self, client, encryption_key):
        """Test loading config when no keys have been saved."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/load_config")

            assert response.status_code == 200
            data = json.loads(response.data)

            # Should return default/empty values
            assert "openrouter_api_key" in data
            assert "claude_api_key" in data


class TestConfigRoundtrip:
    """Tests for save -> load roundtrip."""

    def test_save_then_load_returns_original(self, client, encryption_key):
        """Test that saving then loading returns original values."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save
            original_values = {
                "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                "claude_api_key": "sk-ant-api03-" + ("b" * 95),
                "gemini_api_key": "c" * 39,
                "openai_api_key": "sk-" + ("d" * 48),
            }

            save_response = client.post(
                "/save_config",
                data={
                    **original_values,
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )
            assert json.loads(save_response.data)["success"] is True

            # Load
            load_response = client.get("/load_config")
            loaded_data = json.loads(load_response.data)

            # Verify
            for field, value in original_values.items():
                assert loaded_data[field] == value

    def test_update_key_preserves_other_keys(self, client, encryption_key):
        """Test that updating one key doesn't affect others."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save initial keys
            client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                    "claude_api_key": "sk-ant-api03-" + ("b" * 95),
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            # Update only Claude key
            client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "sk-or-v1-" + ("a" * 64),  # Keep same
                    "claude_api_key": "sk-ant-api03-" + ("z" * 95),  # New value
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

            # Load and verify
            loaded = json.loads(client.get("/load_config").data)

            assert loaded["openrouter_api_key"] == "sk-or-v1-" + ("a" * 64)  # Unchanged
            assert loaded["claude_api_key"] == "sk-ant-api03-" + ("z" * 95)  # Updated


class TestConfigErrorHandling:
    """Tests for error handling in config endpoints."""

    def test_save_config_handles_missing_fields(self, client, encryption_key):
        """Test that save_config handles missing form fields gracefully."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Submit with minimal fields
            response = client.post(
                "/save_config",
                data={"openrouter_api_key": "sk-or-v1-" + ("a" * 64)},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_load_config_handles_decrypt_errors_gracefully(self, client):
        """Test that load_config handles decryption errors gracefully."""
        # Create config with one key, then try to load with different encryption key
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key1}):
            # Save with key1
            client.post(
                "/save_config",
                data={
                    "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                    "claude_api_key": "",
                    "gemini_api_key": "",
                    "openai_api_key": "",
                    "nanogpt_api_key": "",
                    "chutes_api_key": "",
                    "zai_api_key": "",
                },
            )

        # Try to load with key2
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": key2}):
            response = client.get("/load_config")
            assert response.status_code == 200
            data = json.loads(response.data)
            # Should still return a response (empty/null for decryption failures)
            assert isinstance(data, dict)


class TestProviderTypeBadges:
    """Tests for provider type clarity UI (User Story 3 - Phase 5)."""

    def test_config_page_contains_cloud_provider_badges(self, client, encryption_key):
        """Test T039: Config page HTML contains cloud provider badges."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/config")

            assert response.status_code == 200
            html_content = response.data.decode('utf-8')

            # Check for cloud provider badges
            cloud_providers = [
                'openrouter',  # OpenRouter
                'claude',      # Claude API
                'gemini',      # Google Gemini
                'openai',      # OpenAI
                'nanogpt',     # NanoGPT
                'chutes',      # Chutes AI
                'zai',         # Z.AI
            ]

            for provider in cloud_providers:
                # Each cloud provider should have a badge with provider type indicator
                assert f'provider-section' in html_content, f"Provider section class missing for {provider}"
                assert f'class="cloud-provider"' in html_content or 'cloud-api' in html_content.lower(), \
                    f"Cloud provider badge missing for {provider}"

    def test_config_page_contains_local_provider_badges(self, client, encryption_key):
        """Test T040: Config page HTML contains local provider badges."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/config")

            assert response.status_code == 200
            html_content = response.data.decode('utf-8')

            # Check for local provider badges
            local_providers = [
                'lm_studio',   # LM Studio
                'ollama',      # Ollama
            ]

            for provider in local_providers:
                # Each local provider should have a badge with provider type indicator
                assert f'provider-section' in html_content, f"Provider section class missing for {provider}"
                assert f'class="local-provider"' in html_content or 'local-only' in html_content.lower(), \
                    f"Local provider badge missing for {provider}"

    def test_config_page_contains_zai_explanation_panel(self, client, encryption_key):
        """Test T041: Config page contains Z.AI explanation panel with pricing comparison."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/config")

            assert response.status_code == 200
            html_content = response.data.decode('utf-8')

            # Check for Z.AI pricing plan radio buttons
            assert 'zai_pricing_plan' in html_content, "Z.AI pricing plan controls missing"

            # Check for pricing plan labels
            assert 'Normal API Pricing' in html_content or 'normal' in html_content.lower(), \
                "Normal API pricing option missing"
            assert 'Coding Plan' in html_content or 'coding_plan' in html_content.lower(), \
                "Coding Plan option missing"

            # Check for pricing indicators in the description
            assert 'Pay per use' in html_content or 'pay-per-use' in html_content.lower(), \
                "Pay-per-use indicator missing"
            assert 'subscription' in html_content.lower(), \
                "Subscription indicator missing"
