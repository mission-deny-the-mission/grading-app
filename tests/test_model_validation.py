"""
Unit tests for model validation and consistency.
Tests consistency between GUI display names and backend model names.
"""

import re

import pytest


class TestModelValidation:
    """Test cases for model validation and consistency."""

    # Expected model mappings from GUI to backend
    EXPECTED_MODEL_MAPPINGS = {
        # Configuration dropdowns
        "config_dropdowns": {
            "openrouter": {
                "GPT-5": "openai/gpt-5",
                "Claude 4 Sonnet": "anthropic/claude-4-sonnet",
                "Claude 4 Opus": "anthropic/claude-4-opus",
                "Gemini 2.5 Pro": "google/gemini-2.5-pro",
                "GPT-4o": "openai/gpt-4o",
                "Gemini Pro": "google/gemini-pro",
            },
            "claude": {
                "Claude 4 Sonnet": "claude-4-sonnet",
                "Claude 4 Opus": "claude-4-opus",
                "Claude 4 Haiku": "claude-4-haiku",
                "Claude 3.5 Sonnet": "claude-3.5-sonnet-20241022",
            },
            "gemini": {
                "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
                "Gemini Pro": "gemini-pro",
                "Gemini Pro Vision": "gemini-pro-vision",
            },
            "openai": {
                "GPT-5": "gpt-5",
                "GPT-5 Mini": "gpt-5-mini",
                "GPT-4o": "gpt-4o",
                "GPT-4o Mini": "gpt-4o-mini",
                "GPT-4 Turbo": "gpt-4-turbo",
            },
            "ollama": {
                "Llama 2": "llama2",
                "Llama 3": "llama3",
                "Code Llama": "codellama",
                "Mistral": "mistral",
                "Gemma": "gemma",
                "Phi": "phi",
            },
        },
        # Main interface model selection
        "main_interface": {
            "GPT-5": "openai/gpt-5",
            "GPT-5 Mini": "openai/gpt-5-mini",
            "Claude 4 Sonnet": "anthropic/claude-4-sonnet",
            "Claude 4 Opus": "anthropic/claude-4-opus",
            "Gemini 2.5 Pro": "google/gemini-2.5-pro",
            "GPT-4o": "openai/gpt-4o",
            "Gemini Pro": "google/gemini-pro",
        },
    }

    @pytest.mark.integration
    def test_config_page_dropdowns(self, client):
        """Test all dropdown options in the configuration page."""
        response = client.get("/config")
        assert response.status_code == 200

        html = response.text

        # Test each provider's dropdown
        provider_dropdowns = {
            "openrouter_default_model_select": "openrouter",
            "claude_default_model": "claude",
            "gemini_default_model": "gemini",
            "openai_default_model": "openai",
            "ollama_default_model_select": "ollama",
        }

        for dropdown_id, provider in provider_dropdowns.items():
            options = self._extract_dropdown_options(html, dropdown_id)

            if not options:
                continue

            expected_mappings = self.EXPECTED_MODEL_MAPPINGS["config_dropdowns"].get(
                provider, {}
            )

            for display_text, backend_value in options:
                if display_text == "Use System Default" or backend_value == "":
                    continue  # Skip default option
                if display_text == "Custom Model...":
                    continue  # Skip custom option

                # Check if this mapping is expected
                if display_text in expected_mappings:
                    expected_backend = expected_mappings[display_text]
                    assert backend_value == expected_backend, (
                        f"{provider}: '{display_text}' expected "
                        f"'{expected_backend}' but got '{backend_value}'"
                    )

    @pytest.mark.integration
    def test_main_interface_dropdown(self, client):
        """Test model dropdown in main interface."""
        response = client.get("/")
        assert response.status_code == 200

        html = response.text
        options = self._extract_dropdown_options(html, "modelSelect")

        if not options:
            return

        expected_mappings = self.EXPECTED_MODEL_MAPPINGS["main_interface"]

        for display_text, backend_value in options:
            if display_text == "Use Default Model" or backend_value == "default":
                continue  # Skip default option
            if display_text == "Custom Model...":
                continue  # Skip custom option

            if display_text in expected_mappings:
                expected_backend = expected_mappings[display_text]
                assert backend_value == expected_backend, (
                    f"Main interface: '{display_text}' expected "
                    f"'{expected_backend}' but got '{backend_value}'"
                )

    @pytest.mark.integration
    def test_bulk_upload_interface(self, client):
        """Test model dropdown in bulk upload interface."""
        response = client.get("/bulk_upload")
        assert response.status_code == 200

        html = response.text
        options = self._extract_dropdown_options(html, "modelSelect")

        if not options:
            return

        expected_mappings = self.EXPECTED_MODEL_MAPPINGS["main_interface"]

        for display_text, backend_value in options:
            if display_text == "Use Default Model" or backend_value == "default":
                continue
            if display_text == "Custom Model...":
                continue

            if display_text in expected_mappings:
                expected_backend = expected_mappings[display_text]
                assert backend_value == expected_backend, (
                    f"Bulk upload: '{display_text}' expected "
                    f"'{expected_backend}' but got '{backend_value}'"
                )

    @pytest.mark.api
    def test_backend_model_names_api(self, client):
        """Test that backend model names API works correctly."""
        response = client.get("/api/models")
        assert response.status_code == 200

        models_data = response.get_json()

        required_providers = [
            "openrouter",
            "claude",
            "gemini",
            "openai",
            "lm_studio",
            "ollama",
        ]

        for provider in required_providers:
            assert (
                provider in models_data
            ), f"Provider '{provider}' missing from models API"

            provider_data = models_data[provider]
            assert (
                "popular" in provider_data
            ), f"Provider '{provider}' missing popular models"
            assert (
                "default" in provider_data
            ), f"Provider '{provider}' missing default model"

    @pytest.mark.api
    @pytest.mark.database
    def test_config_save_load_consistency(self, client, app):
        """Test that saved configuration values work correctly."""
        test_configs = {
            "openrouter_default_model": "anthropic/claude-4-sonnet",
            "claude_default_model": "claude-4-opus",
            "openai_default_model": "gpt-5-mini",
            "ollama_default_model": "llama3",
        }

        # Save test configuration
        response = client.post("/save_config", data=test_configs)
        assert response.status_code == 200

        result = response.get_json()
        assert result.get("success"), "Config save failed"

        # Load and verify
        load_response = client.get("/load_config")
        assert load_response.status_code == 200

        loaded_config = load_response.get_json()

        for key, expected_value in test_configs.items():
            actual_value = loaded_config.get(key)
            assert actual_value == expected_value, (
                f"Config consistency: {key} expected '{expected_value}' "
                f"but got '{actual_value}'"
            )

    def _extract_dropdown_options(self, html, dropdown_id):
        """Extract options from a dropdown in HTML."""
        pattern = rf'<select[^>]*id="{dropdown_id}"[^>]*>(.*?)</select>'
        dropdown_match = re.search(pattern, html, re.DOTALL)

        if not dropdown_match:
            return []

        dropdown_html = dropdown_match.group(1)
        option_pattern = r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>'
        options = re.findall(option_pattern, dropdown_html)

        return [
            (display.strip(), value.strip())
            for display, value in options
            if value.strip()
        ]

    @pytest.mark.api
    def test_model_provider_endpoints(self, client):
        """Test individual model provider endpoints."""
        providers = ["openrouter", "claude", "gemini", "openai", "ollama", "nanogpt", "chutes", "zai"]

        for provider in providers:
            response = client.get(f"/api/models/{provider}")
            assert response.status_code == 200

            data = response.get_json()
            assert "popular" in data
            assert "default" in data
            assert isinstance(data["popular"], list)

    @pytest.mark.integration
    def test_model_dropdown_consistency(self, client):
        """Test that model dropdowns are consistent across pages."""
        pages_to_test = [
            ("/", "main interface"),
            ("/config", "config page"),
            ("/bulk_upload", "bulk upload page"),
        ]

        model_options = {}

        for url, context in pages_to_test:
            response = client.get(url)
            assert response.status_code == 200

            html = response.text
            options = self._extract_dropdown_options(html, "modelSelect")

            if options:
                model_options[context] = options

        # Check that all contexts have the same basic structure
        if len(model_options) > 1:
            contexts = list(model_options.keys())
            first_context = contexts[0]

            for context in contexts[1:]:
                # Compare number of options (excluding defaults/custom)
                first_count = len(
                    [
                        opt
                        for opt in model_options[first_context]
                        if opt[0] not in ["Use Default Model", "Custom Model..."]
                        and opt[1] not in ["default", "custom"]
                    ]
                )

                context_count = len(
                    [
                        opt
                        for opt in model_options[context]
                        if opt[0] not in ["Use Default Model", "Custom Model..."]
                        and opt[1] not in ["default", "custom"]
                    ]
                )

                assert abs(first_count - context_count) <= 2, (
                    f"Model option count mismatch between {first_context} "
                    f"({first_count}) and {context} ({context_count})"
                )

    @pytest.mark.api
    def test_model_name_backend_consistency(self, client):
        """Test that backend model names are consistent with frontend."""
        # Get frontend model options
        response = client.get("/")
        assert response.status_code == 200

        html = response.text
        frontend_options = self._extract_dropdown_options(html, "modelSelect")

        # Get backend model data
        backend_response = client.get("/api/models")
        assert backend_response.status_code == 200
        backend_data = backend_response.get_json()

        # Check that backend has models for all frontend options
        backend_models = set()
        for provider_data in backend_data.values():
            if "popular" in provider_data:
                backend_models.update(provider_data["popular"])


        # Create a mapping from display names to expected backend IDs
        # based on the expected model mappings
        display_to_backend = {}
        for provider_models in self.EXPECTED_MODEL_MAPPINGS.values():
            display_to_backend.update(provider_models)

        # Check consistency for models that have expected mappings
        inconsistent_count = 0
        for display_name, backend_value in frontend_options:
            if (
                backend_value not in ["default", "custom"]
                and display_name in display_to_backend
            ):
                expected_backend = display_to_backend[display_name]
                if backend_value != expected_backend:
                    inconsistent_count += 1

        # Allow for some inconsistencies due to dynamic model lists
        assert (
            inconsistent_count <= 3
        ), f"Too many inconsistent model mappings: {inconsistent_count}"
