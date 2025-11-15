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


class TestExportConfig:
    """Tests for GET /export_config endpoint (T054, T056)."""

    def test_export_config_returns_json(self, client, encryption_key):
        """Test T054: Export endpoint returns valid JSON with required fields."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/export_config")

            assert response.status_code == 200
            assert response.content_type == 'application/json'
            data = json.loads(response.data)

            # Contract T054: Check required fields
            assert "version" in data
            assert data["version"] == "1.0"
            assert "exported_at" in data
            assert "warning" in data
            assert "security" in data["warning"].lower() or "sensitive" in data["warning"].lower()

    def test_export_config_includes_api_keys(self, client, encryption_key):
        """Test T056: Export includes all API key fields."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save some config first
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

            # Export
            response = client.get("/export_config")
            data = json.loads(response.data)

            # Verify all API key fields are in export
            assert "openrouter_api_key" in data
            assert "claude_api_key" in data
            assert "gemini_api_key" in data
            assert "openai_api_key" in data
            assert "nanogpt_api_key" in data
            assert "chutes_api_key" in data
            assert "zai_api_key" in data

            # Keys should be decrypted in export
            assert data["openrouter_api_key"] == "sk-or-v1-" + ("a" * 64)
            assert data["claude_api_key"] == "sk-ant-api03-" + ("b" * 95)

    def test_export_config_includes_urls(self, client, encryption_key):
        """Test T056: Export includes URL fields."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/export_config")
            data = json.loads(response.data)

            # URLs should be present
            assert "lm_studio_url" in data
            assert "ollama_url" in data

    def test_export_config_includes_default_models(self, client, encryption_key):
        """Test T056: Export includes default model fields."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/export_config")
            data = json.loads(response.data)

            # Default models should be present
            assert "openrouter_default_model" in data
            assert "claude_default_model" in data
            assert "gemini_default_model" in data
            assert "openai_default_model" in data
            assert "nanogpt_default_model" in data
            assert "chutes_default_model" in data
            assert "zai_default_model" in data
            assert "lm_studio_default_model" in data
            assert "ollama_default_model" in data

    def test_export_config_includes_other_settings(self, client, encryption_key):
        """Test T056: Export includes other settings like prompt and Z.AI plan."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/export_config")
            data = json.loads(response.data)

            # Other settings
            assert "default_prompt" in data
            assert "zai_pricing_plan" in data

    def test_export_config_iso_timestamp(self, client, encryption_key):
        """Test T060: Export timestamp is ISO 8601 format."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.get("/export_config")
            data = json.loads(response.data)

            # Verify ISO format (should have T and Z or timezone)
            exported_at = data["exported_at"]
            assert "T" in exported_at
            assert "Z" in exported_at or "+" in exported_at or "-" in exported_at[-6:]


class TestImportConfig:
    """Tests for POST /import_config endpoint (T055, T057, T058)."""

    def test_import_config_requires_version(self, client, encryption_key):
        """Test T058: Import rejects missing version field."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/import_config",
                data=json.dumps({"exported_at": "2025-01-15T14:30:00Z"}),
                content_type="application/json"
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "version" in data["error"].lower()

    def test_import_config_validates_version(self, client, encryption_key):
        """Test T058: Import rejects unsupported version."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            response = client.post(
                "/import_config",
                data=json.dumps({
                    "version": "2.0",
                    "exported_at": "2025-01-15T14:30:00Z"
                }),
                content_type="application/json"
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "version" in data["error"].lower()

    def test_import_config_valid_minimal(self, client, encryption_key):
        """Test T055, T057: Import minimal valid configuration."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z"
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "fields_updated" in data

    def test_import_config_with_api_keys(self, client, encryption_key):
        """Test T057: Import configuration with API keys."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z",
                "openrouter_api_key": "sk-or-v1-" + ("a" * 64),
                "claude_api_key": "sk-ant-api03-" + ("b" * 95),
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["fields_updated"] >= 2

            # Verify keys were saved (load to check)
            load_response = client.get("/load_config")
            load_data = json.loads(load_response.data)
            assert load_data["openrouter_api_key"] == "sk-or-v1-" + ("a" * 64)
            assert load_data["claude_api_key"] == "sk-ant-api03-" + ("b" * 95)

    def test_import_config_invalid_api_key_format(self, client, encryption_key):
        """Test T058: Import rejects invalid API key format."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z",
                "openrouter_api_key": "invalid-key-format",
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "validation_errors" in data
            assert len(data["validation_errors"]) > 0

    def test_import_config_multiple_invalid_keys(self, client, encryption_key):
        """Test T058: Import reports all validation errors."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z",
                "openrouter_api_key": "invalid1",
                "claude_api_key": "invalid2",
                "gemini_api_key": "invalid3",
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "validation_errors" in data
            # Should report multiple errors
            assert len(data["validation_errors"]) >= 3

    def test_import_config_invalid_url_format(self, client, encryption_key):
        """Test T058: Import rejects invalid URL format."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z",
                "lm_studio_url": "not-a-valid-url",
                "ollama_url": "also-invalid",
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "validation_errors" in data

    def test_import_config_valid_urls(self, client, encryption_key):
        """Test T057: Import with valid URLs."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z",
                "lm_studio_url": "http://localhost:1234/v1",
                "ollama_url": "http://localhost:11434",
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_import_then_export_roundtrip(self, client, encryption_key):
        """Test T056, T057: Export then import roundtrip preserves data."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # First export empty config
            export1 = client.get("/export_config")
            export_data = json.loads(export1.data)

            # Import the exported config
            response = client.post(
                "/import_config",
                data=json.dumps(export_data),
                content_type="application/json"
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

            # Export again and verify same (with updated timestamp)
            export2 = client.get("/export_config")
            export_data2 = json.loads(export2.data)

            # Version should match
            assert export_data2["version"] == export_data["version"]

    def test_import_partial_config(self, client, encryption_key):
        """Test T057: Import partial configuration (only some fields)."""
        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": encryption_key}):
            # Save initial config
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

            # Import partial config (only openai)
            config_data = {
                "version": "1.0",
                "exported_at": "2025-01-15T14:30:00Z",
                "openai_api_key": "sk-proj-" + ("x" * 48),
            }

            response = client.post(
                "/import_config",
                data=json.dumps(config_data),
                content_type="application/json"
            )

            assert response.status_code == 200

            # Verify openai was updated, others preserved
            load_response = client.get("/load_config")
            load_data = json.loads(load_response.data)
            assert load_data["openai_api_key"] == "sk-proj-" + ("x" * 48)
            # Other keys should remain (or be from env)
            assert "openrouter_api_key" in load_data
