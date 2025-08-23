"""
Tests for utils.llm_providers to cover factory and error branches without real API calls.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from utils import llm_providers as lp


class TestFactory:
    def test_get_llm_provider_valid(self):
        assert isinstance(lp.get_llm_provider('OpenRouter'), lp.OpenRouterLLMProvider)
        assert isinstance(lp.get_llm_provider('Claude'), lp.ClaudeLLMProvider)
        assert isinstance(lp.get_llm_provider('LM Studio'), lp.LMStudioLLMProvider)
        assert isinstance(lp.get_llm_provider('Ollama'), lp.OllamaLLMProvider)
        assert isinstance(lp.get_llm_provider('Gemini'), lp.GeminiLLMProvider)
        assert isinstance(lp.get_llm_provider('OpenAI'), lp.OpenAILLMProvider)

    def test_get_llm_provider_invalid(self):
        with pytest.raises(ValueError):
            lp.get_llm_provider('Unknown')


class TestOpenRouterProvider:
    def test_missing_api_key(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': ''}, clear=False):
            provider = lp.OpenRouterLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'authentication' in res['error'].lower()

    def test_generic_exception(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'x'}), \
             patch('utils.llm_providers.requests.post', side_effect=Exception('boom')):
            provider = lp.OpenRouterLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'Unexpected error' in res['error']


class TestClaudeProvider:
    def test_missing_api_key(self):
        with patch.dict(os.environ, {'CLAUDE_API_KEY': ''}, clear=False):
            provider = lp.ClaudeLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False

    def test_init_failure(self):
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'x'}), \
             patch('utils.llm_providers.Anthropic', side_effect=Exception('init fail')):
            provider = lp.ClaudeLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False

    def test_exception_paths(self):
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = Exception('rate limit')
        with patch.dict(os.environ, {'CLAUDE_API_KEY': 'x'}), \
             patch('utils.llm_providers.Anthropic', return_value=fake_client):
            provider = lp.ClaudeLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'rate' in res['error'].lower()


class TestLMStudioProvider:
    def test_connection_error(self):
        with patch('utils.llm_providers.requests.post', side_effect=lp.requests.exceptions.ConnectionError()):
            provider = lp.LMStudioLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'Could not connect' in res['error']

    def test_non_200_code(self):
        fake_resp = MagicMock(status_code=404, text='not found')
        with patch('utils.llm_providers.requests.post', return_value=fake_resp):
            provider = lp.LMStudioLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'endpoint not found' in res['error'].lower()


class TestOllamaProvider:
    def test_timeout(self):
        with patch('utils.llm_providers.requests.post', side_effect=lp.requests.exceptions.Timeout()):
            provider = lp.OllamaLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'timed out' in res['error'].lower()

    def test_success(self):
        fake_json = {
            'response': 'Grade: A',
            'prompt_eval_count': 10,
            'eval_count': 20
        }
        fake_resp = MagicMock(status_code=200)
        fake_resp.json.return_value = fake_json
        with patch('utils.llm_providers.requests.post', return_value=fake_resp):
            provider = lp.OllamaLLMProvider()
            res = provider.grade_document('t', 'p', model='llama2')
            assert res['success'] is True and res['grade'] == 'Grade: A'


class TestGeminiProvider:
    def test_missing_api_key(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}, clear=False):
            provider = lp.GeminiLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'authentication' in res['error'].lower()

    def test_exception_paths(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'x'}), \
             patch('utils.llm_providers.genai.configure'), \
             patch('utils.llm_providers.genai.GenerativeModel') as mock_model:
            instance = MagicMock()
            instance.generate_content.side_effect = Exception('quota exceeded')
            mock_model.return_value = instance
            provider = lp.GeminiLLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'rate' in res['error'].lower()


class TestOpenAIProvider:
    def test_missing_api_key(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=False):
            provider = lp.OpenAILLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'authentication' in res['error'].lower()

    def test_generic_exception(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'x'}), \
             patch('utils.llm_providers.OpenAI') as mock_openai:
            client = MagicMock()
            client.chat.completions.create.side_effect = Exception('API blew up')
            mock_openai.return_value = client
            provider = lp.OpenAILLMProvider()
            res = provider.grade_document('t', 'p')
            assert res['success'] is False and 'Unexpected error' in res['error']


