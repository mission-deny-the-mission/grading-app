"""
Unit tests for new LLM providers: Chutes, Z.AI, Z.AI Coding Plan, and NanoGPT.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from utils.llm_providers import get_llm_provider


class TestNewProviders:
    """Test new LLM provider implementations."""

    def test_chutes_provider_get_available_models_no_key(self, app):
        """Test Chutes provider models endpoint without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Chutes")
                result = provider.get_available_models()

                assert result["success"] is False
                assert "error" in result
                assert "not configured" in result["error"].lower()

    def test_zai_coding_plan_provider_get_available_models(self, app):
        """Test Z.AI Coding Plan provider models endpoint."""
        with app.app_context():
            provider = get_llm_provider("Z.AI Coding Plan")
            result = provider.get_available_models()

            assert result["success"] is True
            assert "models" in result
            assert len(result["models"]) == 3
            # Check for known models
            model_ids = [model["id"] for model in result["models"]]
            assert "glm-4.6" in model_ids
            assert "glm-4.5" in model_ids
            assert "glm-4.5-air" in model_ids

    @patch("utils.llm_providers.requests.post")
    def test_zai_coding_plan_provider_grade_success(self, mock_requests_post, app):
        """Test successful grading with Z.AI Coding Plan provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Excellent coding work! Grade: A+"}],
            "usage": {"input_tokens": 15, "output_tokens": 10},
        }
        mock_requests_post.return_value = mock_response

        with patch.dict(os.environ, {"Z_AI_CODING_PLAN_API_KEY": "test-zai-coding-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Z.AI Coding Plan")
                result = provider.grade_document(
                    "This is a test document.",
                    "Please grade this document.",
                    model="glm-4.6",
                    temperature=0.7,
                    max_tokens=2000,
                )

                assert result["success"] is True
                assert "grade" in result
                assert "Excellent coding work!" in result["grade"]
                assert result["provider"] == "Z.AI Coding Plan"
                assert result["model"] == "glm-4.6"

    def test_zai_coding_plan_provider_no_api_key(self, app):
        """Test Z.AI Coding Plan provider without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Z.AI Coding Plan")
                result = provider.grade_document(
                    "This is a test document.", "Please grade this document."
                )

                assert result["success"] is False
                assert "error" in result
                assert "authentication" in result["error"].lower()
                assert "coding plan" in result["error"].lower()

    @patch("utils.llm_providers.requests.get")
    def test_chutes_provider_get_available_models_success(self, mock_requests_get, app):
        """Test successful models fetch from Chutes provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "microsoft/DialoGPT-medium",
                    "name": "DialoGPT Medium",
                    "description": "A conversational AI model",
                    "context_length": 2048
                }
            ]
        }
        mock_requests_get.return_value = mock_response

        with patch.dict(os.environ, {"CHUTES_API_KEY": "test-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Chutes")
                result = provider.get_available_models()

                assert result["success"] is True
                assert "models" in result
                assert len(result["models"]) == 1
                assert result["models"][0]["id"] == "microsoft/DialoGPT-medium"

    @patch("utils.llm_providers.requests.post")
    def test_chutes_provider_grade_success(self, mock_requests_post, app):
        """Test successful grading with Chutes provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Excellent work! Grade: A"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_requests_post.return_value = mock_response

        with patch.dict(os.environ, {"CHUTES_API_KEY": "test-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Chutes")
                result = provider.grade_document(
                    "This is a test document.",
                    "Please grade this document.",
                    temperature=0.7,
                    max_tokens=2000,
                )

                assert result["success"] is True
                assert "grade" in result
                assert "Excellent work!" in result["grade"]
                assert result["provider"] == "Chutes"

    def test_chutes_provider_no_api_key(self, app):
        """Test Chutes provider without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Chutes")
                result = provider.grade_document(
                    "This is a test document.", "Please grade this document."
                )

                assert result["success"] is False
                assert "error" in result
                assert "authentication" in result["error"].lower()

    def test_zai_provider_get_available_models(self, app):
        """Test Z.AI provider models endpoint."""
        with app.app_context():
            provider = get_llm_provider("Z.AI")
            result = provider.get_available_models()

            assert result["success"] is True
            assert "models" in result
            assert len(result["models"]) > 0
            # Check for known models
            model_ids = [model["id"] for model in result["models"]]
            assert "glm-4.6" in model_ids
            assert "glm-4.5" in model_ids

    @patch("utils.llm_providers.requests.post")
    def test_zai_provider_grade_success(self, mock_requests_post, app):
        """Test successful grading with Z.AI provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Great essay! Grade: B+"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }
        mock_requests_post.return_value = mock_response

        with patch.dict(os.environ, {"Z_AI_API_KEY": "test-zai-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Z.AI")
                result = provider.grade_document(
                    "This is a test document.",
                    "Please grade this document.",
                    model="glm-4.6",
                    temperature=0.7,
                    max_tokens=2000,
                )

                assert result["success"] is True
                assert "grade" in result
                assert "Great essay!" in result["grade"]
                assert result["provider"] == "Z.AI"
                assert result["model"] == "glm-4.6"

    def test_zai_provider_no_api_key(self, app):
        """Test Z.AI provider without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Z.AI")
                result = provider.grade_document(
                    "This is a test document.", "Please grade this document."
                )

                assert result["success"] is False
                assert "error" in result
                assert "authentication" in result["error"].lower()

    @patch("utils.llm_providers.requests.post")
    def test_zai_coding_plan_provider_auth_error(self, mock_requests_post, app):
        """Test Z.AI Coding Plan provider authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests_post.return_value = mock_response

        with patch.dict(os.environ, {"Z_AI_CODING_PLAN_API_KEY": "invalid-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("Z.AI Coding Plan")
                result = provider.grade_document(
                    "This is a test document.", "Please grade this document."
                )

                assert result["success"] is False
                assert "error" in result
                assert "401" in result["error"]
                assert "Z.AI Coding Plan" in result["provider"]

    @patch("utils.llm_providers.requests.get")
    def test_nanogpt_provider_get_available_models_success(self, mock_requests_get, app):
        """Test successful models fetch from NanoGPT provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "chatgpt-4o-latest",
                    "name": "GPT-4O Latest",
                    "description": "Latest GPT-4O model",
                    "max_tokens": 128000
                }
            ]
        }
        mock_requests_get.return_value = mock_response

        with patch.dict(os.environ, {"NANOGPT_API_KEY": "test-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("NanoGPT")
                result = provider.get_available_models()

                assert result["success"] is True
                assert "models" in result
                assert len(result["models"]) == 1
                assert result["models"][0]["id"] == "chatgpt-4o-latest"

    @patch("utils.llm_providers.requests.post")
    def test_nanogpt_provider_grade_success(self, mock_requests_post, app):
        """Test successful grading with NanoGPT provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Good work! Grade: B"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
        }
        mock_requests_post.return_value = mock_response

        with patch.dict(os.environ, {"NANOGPT_API_KEY": "test-nano-key"}, clear=True):
            with app.app_context():
                provider = get_llm_provider("NanoGPT")
                result = provider.grade_document(
                    "This is a test document.",
                    "Please grade this document.",
                    model="chatgpt-4o-latest",
                    temperature=0.7,
                    max_tokens=2000,
                )

                assert result["success"] is True
                assert "grade" in result
                assert "Good work!" in result["grade"]
                assert result["provider"] == "NanoGPT"
                assert result["model"] == "chatgpt-4o-latest"

    def test_nanogpt_provider_no_api_key(self, app):
        """Test NanoGPT provider without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with app.app_context():
                provider = get_llm_provider("NanoGPT")
                result = provider.grade_document(
                    "This is a test document.", "Please grade this document."
                )

                assert result["success"] is False
                assert "error" in result
                assert "authentication" in result["error"].lower()

    def test_provider_factory_functions(self, app):
        """Test that factory function returns correct provider instances."""
        with app.app_context():
            chutes_provider = get_llm_provider("Chutes")
            zai_provider = get_llm_provider("Z.AI")
            zai_coding_provider = get_llm_provider("Z.AI Coding Plan")
            nanogpt_provider = get_llm_provider("NanoGPT")

            # Check that providers are of correct type
            assert chutes_provider.__class__.__name__ == "ChutesLLMProvider"
            assert zai_provider.__class__.__name__ == "ZAILLMProvider"
            assert zai_coding_provider.__class__.__name__ == "ZAICodingPlanLLMProvider"
            assert nanogpt_provider.__class__.__name__ == "NanoGPTLLMProvider"

    def test_unknown_provider_raises_error(self, app):
        """Test that requesting an unknown provider raises ValueError."""
        with app.app_context():
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_llm_provider("UnknownProvider")

    def test_zai_coding_plan_vs_normal_api_distinction(self, app):
        """Test that Z.AI Coding Plan and Z.AI Normal API are different providers."""
        with app.app_context():
            normal_provider = get_llm_provider("Z.AI")
            coding_plan_provider = get_llm_provider("Z.AI Coding Plan")

            # They should be different instances
            assert normal_provider is not coding_plan_provider
            assert normal_provider.__class__.__name__ == "ZAILLMProvider"
            assert coding_plan_provider.__class__.__name__ == "ZAICodingPlanLLMProvider"

            # Test their model lists are different
            normal_models = normal_provider.get_available_models()
            coding_models = coding_plan_provider.get_available_models()

            assert normal_models["success"] is True
            assert coding_models["success"] is True
            # Coding plan should have fewer models (limited selection)
            assert len(coding_models["models"]) < len(normal_models["models"])
