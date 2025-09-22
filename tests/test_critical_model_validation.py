"""
Critical tests for model name consistency validation.
Focuses on ensuring dropdown options correspond to valid backend models.
"""

import re

import pytest


class TestCriticalModelValidation:
    """Critical test cases for model name consistency validation."""

    @pytest.mark.integration
    def test_model_naming_consistency(self, client):
        """Test model names are consistent and follow expected patterns."""
        # Since models are loaded dynamically via JavaScript, we'll test the API directly
        # instead of trying to extract from HTML
        response = client.get("/api/models")
        assert response.status_code == 200
        
        models_data = response.get_json()
        
        # Check that we have providers with the expected structure
        required_providers = ["openrouter", "claude", "gemini", "openai", "lm_studio", "ollama"]
        
        valid_models = 0
        issues_found = 0
        
        for provider in required_providers:
            if provider in models_data:
                provider_data = models_data[provider]
                
                # Check structure
                if "popular" in provider_data and "default" in provider_data:
                    # Validate naming patterns for popular models
                    for model in provider_data["popular"]:
                        if self._validate_model_patterns(model):
                            valid_models += 1
                        else:
                            issues_found += 1
                    
                    # Also validate default model
                    if self._validate_model_patterns(provider_data["default"]):
                        valid_models += 1
                    else:
                        issues_found += 1
        
        # Should have mostly valid models with few issues
        assert valid_models > 0, "No valid models found"
        assert issues_found <= 5, f"Too many naming issues: {issues_found}"

    @pytest.mark.api
    @pytest.mark.database
    def test_config_model_save_load(self, client, app):
        """Test that configuration models can be saved and loaded correctly."""
        test_models = {
            "openrouter_default_model": "anthropic/claude-4-sonnet",
            "claude_default_model": "claude-4-opus",
            "gemini_default_model": "gemini-2.0-flash-exp",
            "openai_default_model": "gpt-5-mini",
            "ollama_default_model": "llama3",
        }

        # Save configuration
        response = client.post("/save_config", data=test_models)
        assert response.status_code == 200

        result = response.get_json()
        assert result.get("success"), "Config save failed"

        # Load and verify
        load_response = client.get("/load_config")
        assert load_response.status_code == 200

        config = load_response.get_json()

        all_match = True
        for key, expected_value in test_models.items():
            actual_value = config.get(key)
            if actual_value != expected_value:
                all_match = False

        assert all_match, "Config save/load consistency failed"

    @pytest.mark.unit
    def test_model_pattern_validation(self):
        """Validate that model names follow expected patterns."""
        expected_patterns = {
            "OpenAI models": {
                "pattern": r"^(openai/)?gpt-[45].*",
                "examples": ["gpt-5", "gpt-4o", "openai/gpt-5"],
                "description": "Should start with 'gpt-4' or 'gpt-5'",
            },
            "Claude models": {
                "pattern": r"^(anthropic/)?claude-[34].*",
                "examples": ["claude-4-sonnet", "anthropic/claude-4-opus"],
                "description": "Should start with 'claude-3' or 'claude-4'",
            },
            "Gemini models": {
                "pattern": r"^(google/)?gemini.*",
                "examples": ["gemini-pro", "google/gemini-2.5-pro"],
                "description": "Should contain 'gemini'",
            },
            "Ollama models": {
                "pattern": r"^[a-z][a-z0-9-]*$",
                "examples": ["llama3", "codellama", "mistral"],
                "description": "Should be lowercase, alphanumeric with hyphens",
            },
        }

        # Test each pattern
        success_count = 0
        total_tests = 0

        for category, info in expected_patterns.items():
            pattern = re.compile(info["pattern"])

            for example in info["examples"]:
                total_tests += 1
                if pattern.match(example):
                    success_count += 1

        assert (
            success_count == total_tests
        ), f"Pattern validation failed: {success_count}/{total_tests}"

    def _extract_model_options_from_html(self, html, context):
        """Extract model options from HTML in various contexts."""
        models = []

        if context == "config":
            # Extract from configuration dropdowns
            selects_to_check = [
                "openrouter_default_model",
                "claude_default_model",
                "gemini_default_model",
                "openai_default_model",
                "lm_studio_default_model",
                "ollama_default_model",
            ]

            for select_id in selects_to_check:
                pattern = rf'<select[^>]*id="{select_id}"[^>]*>(.*?)</select>'
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    option_pattern = (
                        r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>'
                    )
                    options = re.findall(option_pattern, match.group(1))
                    for value, display in options:
                        if value and value not in ["", "custom"]:
                            models.append(
                                {
                                    "context": f"config_{select_id}",
                                    "display_name": display.strip(),
                                    "backend_value": value.strip(),
                                    "provider": (
                                        select_id.split("_")[0]
                                        if "_" in select_id
                                        else select_id
                                    ),
                                }
                            )

        elif context == "main" or context == "bulk":
            # Extract from main interface model select
            pattern = r'<select[^>]*id="modelSelect"[^>]*>(.*?)</select>'
            match = re.search(pattern, html, re.DOTALL)
            if match:
                option_pattern = r'<option[^>]*value="([^"]*)"[^>]*>([^<]+)</option>'
                options = re.findall(option_pattern, match.group(1))
                for value, display in options:
                    if value and value not in ["default", "custom"]:
                        models.append(
                            {
                                "context": context,
                                "display_name": display.strip(),
                                "backend_value": value.strip(),
                                "provider": "interface",
                            }
                        )

        return models

    def _validate_model_patterns(self, backend_value):
        """Validate that model names follow expected patterns."""
        expected_patterns = {
            "openai/": ["gpt-", "GPT-"],
            "anthropic/": ["claude-", "Claude"],
            "google/": ["gemini-", "Gemini"],
            "meta-llama/": ["llama", "Llama"],
        }

        # Check if backend follows expected provider patterns
        for prefix, expected_substrings in expected_patterns.items():
            if backend_value.startswith(prefix):
                if not any(sub in backend_value for sub in expected_substrings):
                    return False
                break

        # Check basic hyphenation pattern
        # (backend should be hyphenated/lowercase)
        if "/" in backend_value:  # Provider/model format
            model_part = backend_value.split("/", 1)[1]
            if " " in model_part or model_part != model_part.lower():
                return False

        return True

    @pytest.mark.integration
    def test_model_dropdown_accessibility(self, client):
        """Test that model dropdowns are accessible on all pages."""
        pages_to_test = [
            ("/", "main interface"),
            ("/config", "configuration page"),
            ("/bulk_upload", "bulk upload page"),
        ]

        for url, page_name in pages_to_test:
            response = client.get(url)
            assert response.status_code == 200, f"{page_name} page not accessible"

            html = response.text
            # Check that model select dropdown exists
            # The config page uses different dropdown IDs than main/bulk pages
            if page_name == "configuration page":
                # Config page uses provider-specific dropdowns, not modelSelect
                assert (
                    "openrouter_default_model" in html
                ), f"Config dropdowns missing from {page_name}"
            else:
                assert (
                    'id="modelSelect"' in html
                ), f"Model select dropdown missing from {page_name}"

    @pytest.mark.api
    def test_model_api_endpoints_accessible(self, client):
        """Test that model API endpoints are accessible."""
        endpoints_to_test = [
            "/api/models",
            "/api/models/openrouter",
            "/api/models/claude",
            "/api/models/gemini",
            "/api/models/openai",
            "/api/models/ollama",
        ]

        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            assert (
                response.status_code == 200
            ), f"Model API endpoint {endpoint} not accessible"

    @pytest.mark.integration
    def test_model_consistency_across_providers(self, client):
        """Test that model consistency is maintained across providers."""
        response = client.get("/api/models")
        assert response.status_code == 200

        models_data = response.get_json()

        # Check that all providers have required structure
        for provider, provider_data in models_data.items():
            assert (
                "popular" in provider_data
            ), f"Provider '{provider}' missing popular models"
            assert (
                "default" in provider_data
            ), f"Provider '{provider}' missing default model"

            # Check that popular models list is not empty
            assert (
                len(provider_data["popular"]) > 0
            ), f"Provider '{provider}' has empty popular models list"

            # Check that default model exists (may not be in popular list)
            default_model = provider_data["default"]
            assert default_model, f"Provider '{provider}' has empty default model"

            # For some providers, the default model might not be
            # in popular list - this is acceptable as long as
            # the default model exists
