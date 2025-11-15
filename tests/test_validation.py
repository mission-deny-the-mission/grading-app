"""
Unit tests for API key validation (validate_api_key_format).

Following TDD approach: Write tests FIRST (RED), verify they FAIL,
then implement to make them PASS.
"""

import pytest
from utils.llm_providers import validate_api_key_format


class TestValidateOpenRouterKey:
    """Tests for OpenRouter API key validation."""

    def test_valid_openrouter_key(self):
        """Test that valid OpenRouter key passes validation."""
        valid_key = "sk-or-v1-" + ("a" * 64)
        is_valid, error = validate_api_key_format("openrouter", valid_key)

        assert is_valid is True
        assert error is None

    def test_invalid_openrouter_key_wrong_prefix(self):
        """Test that OpenRouter key with wrong prefix fails validation."""
        invalid_key = "sk-test-" + ("a" * 64)
        is_valid, error = validate_api_key_format("openrouter", invalid_key)

        assert is_valid is False
        assert "Invalid" in error

    def test_invalid_openrouter_key_wrong_length(self):
        """Test that OpenRouter key with wrong suffix length fails validation."""
        invalid_key = "sk-or-v1-" + ("a" * 32)  # Too short
        is_valid, error = validate_api_key_format("openrouter", invalid_key)

        assert is_valid is False
        assert "Invalid" in error

    def test_invalid_openrouter_key_special_chars(self):
        """Test that OpenRouter key with special characters fails validation."""
        invalid_key = "sk-or-v1-" + ("a" * 60) + "@#$"
        is_valid, error = validate_api_key_format("openrouter", invalid_key)

        assert is_valid is False


class TestValidateClaudeKey:
    """Tests for Claude API key validation."""

    def test_valid_claude_key(self):
        """Test that valid Claude key passes validation."""
        valid_key = "sk-ant-api03-" + ("A" * 95)
        is_valid, error = validate_api_key_format("claude", valid_key)

        assert is_valid is True
        assert error is None

    def test_valid_claude_key_with_underscore(self):
        """Test that Claude key with underscore passes validation."""
        valid_key = "sk-ant-api03-" + ("A" * 50) + "_" + ("B" * 44)
        is_valid, error = validate_api_key_format("claude", valid_key)

        assert is_valid is True

    def test_valid_claude_key_with_dash(self):
        """Test that Claude key with dash passes validation."""
        valid_key = "sk-ant-api03-" + ("A" * 50) + "-" + ("B" * 44)
        is_valid, error = validate_api_key_format("claude", valid_key)

        assert is_valid is True

    def test_invalid_claude_key_wrong_prefix(self):
        """Test that Claude key with wrong prefix fails validation."""
        invalid_key = "sk-test-" + ("a" * 95)
        is_valid, error = validate_api_key_format("claude", invalid_key)

        assert is_valid is False

    def test_invalid_claude_key_wrong_length(self):
        """Test that Claude key with wrong length fails validation."""
        invalid_key = "sk-ant-api03-" + ("a" * 50)  # Too short
        is_valid, error = validate_api_key_format("claude", invalid_key)

        assert is_valid is False


class TestValidateOpenAIKey:
    """Tests for OpenAI API key validation."""

    def test_valid_openai_key(self):
        """Test that valid OpenAI key passes validation."""
        valid_key = "sk-" + ("a" * 48)
        is_valid, error = validate_api_key_format("openai", valid_key)

        assert is_valid is True
        assert error is None

    def test_invalid_openai_key_wrong_prefix(self):
        """Test that OpenAI key with wrong prefix fails validation."""
        invalid_key = "api-" + ("a" * 48)
        is_valid, error = validate_api_key_format("openai", invalid_key)

        assert is_valid is False

    def test_invalid_openai_key_wrong_length(self):
        """Test that OpenAI key with wrong length fails validation."""
        invalid_key = "sk-" + ("a" * 32)  # Too short
        is_valid, error = validate_api_key_format("openai", invalid_key)

        assert is_valid is False


class TestValidateGeminiKey:
    """Tests for Gemini API key validation."""

    def test_valid_gemini_key(self):
        """Test that valid Gemini key passes validation."""
        valid_key = "a" * 39
        is_valid, error = validate_api_key_format("gemini", valid_key)

        assert is_valid is True
        assert error is None

    def test_valid_gemini_key_with_underscore(self):
        """Test that Gemini key with underscore passes validation."""
        valid_key = "a" * 20 + "_" + "b" * 18
        is_valid, error = validate_api_key_format("gemini", valid_key)

        assert is_valid is True

    def test_valid_gemini_key_with_dash(self):
        """Test that Gemini key with dash passes validation."""
        valid_key = "a" * 20 + "-" + "b" * 18
        is_valid, error = validate_api_key_format("gemini", valid_key)

        assert is_valid is True

    def test_invalid_gemini_key_wrong_length(self):
        """Test that Gemini key with wrong length fails validation."""
        invalid_key = "a" * 20  # Too short
        is_valid, error = validate_api_key_format("gemini", invalid_key)

        assert is_valid is False


class TestValidateNanoGPTKey:
    """Tests for NanoGPT API key validation."""

    def test_valid_nanogpt_key_min_length(self):
        """Test that NanoGPT key at minimum length passes validation."""
        valid_key = "a" * 32
        is_valid, error = validate_api_key_format("nanogpt", valid_key)

        assert is_valid is True
        assert error is None

    def test_valid_nanogpt_key_max_length(self):
        """Test that NanoGPT key at maximum length passes validation."""
        valid_key = "a" * 64
        is_valid, error = validate_api_key_format("nanogpt", valid_key)

        assert is_valid is True

    def test_invalid_nanogpt_key_too_short(self):
        """Test that NanoGPT key below minimum length fails validation."""
        invalid_key = "a" * 20  # Too short
        is_valid, error = validate_api_key_format("nanogpt", invalid_key)

        assert is_valid is False

    def test_invalid_nanogpt_key_too_long(self):
        """Test that NanoGPT key above maximum length fails validation."""
        invalid_key = "a" * 100  # Too long
        is_valid, error = validate_api_key_format("nanogpt", invalid_key)

        assert is_valid is False


class TestValidateChutesKey:
    """Tests for Chutes API key validation."""

    def test_valid_chutes_key(self):
        """Test that valid Chutes key passes validation."""
        valid_key = "chutes_" + ("a" * 32)
        is_valid, error = validate_api_key_format("chutes", valid_key)

        assert is_valid is True
        assert error is None

    def test_invalid_chutes_key_wrong_prefix(self):
        """Test that Chutes key with wrong prefix fails validation."""
        invalid_key = "test_" + ("a" * 32)
        is_valid, error = validate_api_key_format("chutes", invalid_key)

        assert is_valid is False

    def test_invalid_chutes_key_wrong_suffix_length(self):
        """Test that Chutes key with wrong suffix length fails validation."""
        invalid_key = "chutes_" + ("a" * 16)  # Too short
        is_valid, error = validate_api_key_format("chutes", invalid_key)

        assert is_valid is False


class TestValidateZAIKey:
    """Tests for Z.AI API key validation."""

    def test_valid_zai_key_min_length(self):
        """Test that Z.AI key at minimum length passes validation."""
        valid_key = "a" * 32
        is_valid, error = validate_api_key_format("zai", valid_key)

        assert is_valid is True
        assert error is None

    def test_valid_zai_key_long(self):
        """Test that Z.AI key with long length passes validation."""
        valid_key = "a" * 100
        is_valid, error = validate_api_key_format("zai", valid_key)

        assert is_valid is True

    def test_invalid_zai_key_too_short(self):
        """Test that Z.AI key below minimum length fails validation."""
        invalid_key = "a" * 20  # Too short
        is_valid, error = validate_api_key_format("zai", invalid_key)

        assert is_valid is False


class TestValidateLocalProviders:
    """Tests for local provider keys (LM Studio, Ollama)."""

    def test_lm_studio_accepts_any_value(self):
        """Test that LM Studio accepts any key value."""
        is_valid, error = validate_api_key_format("lm_studio", "any-value")
        assert is_valid is True

        is_valid, error = validate_api_key_format("lm_studio", "")
        assert is_valid is True

        is_valid, error = validate_api_key_format("lm_studio", "12345")
        assert is_valid is True

    def test_ollama_accepts_any_value(self):
        """Test that Ollama accepts any key value."""
        is_valid, error = validate_api_key_format("ollama", "any-value")
        assert is_valid is True

        is_valid, error = validate_api_key_format("ollama", "")
        assert is_valid is True


class TestValidateEmptyAndNoneValues:
    """Tests for empty and None values across all providers."""

    def test_empty_string_is_valid(self):
        """Test that empty string is considered valid for all providers."""
        providers = ["openrouter", "claude", "openai", "gemini", "nanogpt", "chutes", "zai"]

        for provider in providers:
            is_valid, error = validate_api_key_format(provider, "")
            assert is_valid is True, f"{provider} should accept empty string"

    def test_none_is_valid(self):
        """Test that None is considered valid for all providers."""
        providers = ["openrouter", "claude", "openai", "gemini", "nanogpt", "chutes", "zai"]

        for provider in providers:
            is_valid, error = validate_api_key_format(provider, None)
            assert is_valid is True, f"{provider} should accept None"


class TestValidateUnknownProvider:
    """Tests for unknown provider validation."""

    def test_unknown_provider_accepts_any_value(self):
        """Test that unknown provider accepts any key value."""
        is_valid, error = validate_api_key_format("unknown_provider", "any-value")
        assert is_valid is True
        assert error is None


class TestValidateErrorMessages:
    """Tests for error message clarity."""

    def test_error_message_includes_provider_name(self):
        """Test that error message includes provider name."""
        invalid_key = "wrong-key-format"
        is_valid, error = validate_api_key_format("claude", invalid_key)

        assert is_valid is False
        assert "claude" in error.lower()

    def test_error_message_indicates_validation_failure(self):
        """Test that error message indicates validation failure."""
        invalid_key = "wrong-key-format"
        is_valid, error = validate_api_key_format("openai", invalid_key)

        assert is_valid is False
        assert "invalid" in error.lower() or "format" in error.lower()
