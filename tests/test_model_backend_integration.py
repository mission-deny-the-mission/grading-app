"""
Unit tests for backend model integration and validation.
Tests model name resolution, format validation, and backend integration.
"""

import pytest


class TestModelBackendIntegration:
    """Test cases for backend model integration and validation."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_backend_model_resolution(self, app):
        """Test that Config.get_default_model() method works correctly."""
        from models import Config, db

        with app.app_context():
            # Create test configuration
            config = Config.get_or_create()

            # Set test default models
            config.openrouter_default_model = "anthropic/claude-4-sonnet"
            config.claude_default_model = "claude-4-opus"
            config.gemini_default_model = "gemini-2.0-flash-exp"
            config.openai_default_model = "gpt-5-mini"
            config.lm_studio_default_model = "local-model"
            config.ollama_default_model = "llama3"

            db.session.commit()

            # Test model resolution
            test_cases = [
                ("openrouter", "anthropic/claude-4-sonnet"),
                ("claude", "claude-4-opus"),
                ("gemini", "gemini-2.0-flash-exp"),
                ("openai", "gpt-5-mini"),
                ("lm_studio", "local-model"),
                ("ollama", "llama3"),
                ("unknown_provider", "anthropic/claude-3-5-sonnet-20241022"),
            ]

            success_count = 0
            for provider, expected_model in test_cases:
                actual_model = config.get_default_model(provider)
                if actual_model == expected_model:
                    success_count += 1
                else:
                    pytest.fail(
                        f"{provider}: expected '{expected_model}' "
                        f"but got '{actual_model}'"
                    )

            assert success_count == len(test_cases)

    @pytest.mark.unit
    def test_upload_route_model_selection(self, app):
        """Test that upload route properly handles model selection."""
        from routes.upload import DEFAULT_MODELS

        with app.app_context():
            # Test the DEFAULT_MODELS structure
            required_providers = [
                "openrouter",
                "claude",
                "gemini",
                "openai",
                "lm_studio",
                "ollama",
            ]

            success_count = 0
            for provider in required_providers:
                if provider in DEFAULT_MODELS:
                    default_model = DEFAULT_MODELS[provider].get("default")
                    # Check popular models exists but don't use the variable
                    DEFAULT_MODELS[provider].get("popular", [])

                    if default_model:
                        success_count += 1
                    else:
                        pytest.fail(f"{provider}: no default model specified")
                else:
                    pytest.fail(f"{provider}: not found in DEFAULT_MODELS")

            assert success_count == len(required_providers)

    @pytest.mark.unit
    def test_model_name_formats(self):
        """Test model names follow expected formats for providers."""
        format_tests = [
            # OpenRouter models (provider/model format)
            ("openai/gpt-5", "openrouter", True),
            ("anthropic/claude-4-sonnet", "openrouter", True),
            ("google/gemini-2.5-pro", "openrouter", True),
            ("invalid-format", "openrouter", False),
            # Direct provider models (no prefix)
            ("claude-4-opus", "claude", True),
            ("gpt-5-mini", "openai", True),
            ("gemini-2.0-flash-exp", "gemini", True),
            ("llama3", "ollama", True),
            ("local-model", "lm_studio", True),
            # Invalid formats
            ("claude-4-opus", "openrouter", False),
            ("anthropic/claude-4-opus", "claude", False),
        ]

        success_count = 0
        for model_name, provider, should_be_valid in format_tests:
            is_valid = self._validate_model_format(model_name, provider)

            if is_valid == should_be_valid:
                success_count += 1
            else:
                expected_str = "valid" if should_be_valid else "invalid"
                actual_str = "valid" if is_valid else "invalid"
                pytest.fail(
                    f"'{model_name}' for {provider}: "
                    f"expected {expected_str} but was {actual_str}"
                )

        assert success_count == len(format_tests)

    def _validate_model_format(self, model_name, provider):
        """Validate model name format for a provider."""
        # Empty string is invalid for all providers
        if not model_name or model_name.strip() == "":
            return False

        if provider == "openrouter":
            # Should have provider/model format with both parts non-empty
            if "/" not in model_name:
                return False
            parts = model_name.split("/")
            if len(parts) != 2:
                return False
            # Both provider and model parts should be non-empty
            return bool(parts[0].strip()) and bool(parts[1].strip())

        elif provider in ["claude", "openai", "gemini", "ollama", "lm_studio"]:
            # Should NOT have provider prefix and should not be empty
            return "/" not in model_name and bool(model_name.strip())

        return False

    @pytest.mark.unit
    @pytest.mark.database
    def test_config_model_persistence(self, app):
        """Test that model configuration is properly persisted."""
        from models import Config, db

        with app.app_context():
            config = Config.get_or_create()

            # Set model values
            test_models = {
                "openrouter_default_model": "anthropic/claude-4-sonnet",
                "claude_default_model": "claude-4-opus",
                "gemini_default_model": "gemini-2.0-flash-exp",
                "openai_default_model": "gpt-5-mini",
                "lm_studio_default_model": "local-model",
                "ollama_default_model": "llama3",
            }

            for attr, value in test_models.items():
                setattr(config, attr, value)

            db.session.commit()

            # Reload from database
            db.session.expunge(config)
            fresh_config = Config.get_or_create()

            # Verify persistence
            for attr, expected_value in test_models.items():
                actual_value = getattr(fresh_config, attr)
                error_msg = f"{attr}: expected '{expected_value}', got '{actual_value}'"
                assert actual_value == expected_value, error_msg

    @pytest.mark.unit
    def test_model_name_edge_cases(self):
        """Test edge cases for model name validation."""
        edge_cases = [
            # Empty strings
            ("", "openrouter", False),
            ("", "claude", False),
            # Just slashes
            ("/", "openrouter", False),
            ("provider/", "openrouter", False),
            ("/model", "openrouter", False),
            # Multiple slashes
            ("provider/sub/model", "openrouter", False),
            # Special characters - empty string should be invalid for claude
            ("model@name", "claude", True),  # Should be valid
            ("model-name", "claude", True),  # Should be valid
            ("model_name", "claude", True),  # Should be valid
        ]

        for model_name, provider, expected_valid in edge_cases:
            is_valid = self._validate_model_format(model_name, provider)
            assert is_valid == expected_valid, (
                f"'{model_name}' for {provider}: "
                f"expected {expected_valid}, got {is_valid}"
            )

    @pytest.mark.unit
    @pytest.mark.database
    def test_fallback_model_logic(self, app):
        """Test fallback model logic for unknown providers."""
        from models import Config

        with app.app_context():
            config = Config.get_or_create()

            # Test fallback for unknown provider
            fallback_model = config.get_default_model("unknown_provider")
            expected_fallback = "anthropic/claude-3-5-sonnet-20241022"

            assert fallback_model == expected_fallback, (
                f"Fallback model: expected '{expected_fallback}', "
                f"got '{fallback_model}'"
            )

    @pytest.mark.unit
    def test_default_models_structure(self):
        """Test that DEFAULT_MODELS has proper structure for all providers."""
        from routes.upload import DEFAULT_MODELS

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
                provider in DEFAULT_MODELS
            ), f"Provider '{provider}' missing from DEFAULT_MODELS"

            provider_config = DEFAULT_MODELS[provider]
            assert (
                "default" in provider_config
            ), f"Provider '{provider}' missing default model"
            assert (
                "popular" in provider_config
            ), f"Provider '{provider}' missing popular models list"
            assert isinstance(
                provider_config["popular"], list
            ), f"Provider '{provider}' popular models should be a list"

    @pytest.mark.unit
    @pytest.mark.database
    def test_config_model_inheritance(self, app):
        """Test that model configuration inheritance works correctly."""
        from models import Config, db

        with app.app_context():
            config = Config.get_or_create()

            # Test inheritance when values are None/empty
            config.openrouter_default_model = None
            config.claude_default_model = ""

            db.session.commit()

            # Should use fallback values
            openrouter_model = config.get_default_model("openrouter")
            claude_model = config.get_default_model("claude")

            assert openrouter_model is not None
            assert claude_model is not None
            assert openrouter_model != ""
            assert claude_model != ""
