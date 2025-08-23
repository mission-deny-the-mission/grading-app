"""
Additional tests for routes.main to cover configuration endpoints and error paths.
"""

import json
from unittest.mock import patch, MagicMock

import pytest


class TestConfigEndpoints:
    def test_load_config_endpoint(self, client):
        resp = client.get('/load_config')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'lm_studio_url' in data and 'ollama_url' in data

    def test_save_config_writes_env_and_session(self, client):
        payload = {
            'openrouter_api_key': 'or_key',
            'claude_api_key': 'c_key',
            'gemini_api_key': 'g_key',
            'openai_api_key': 'oa_key',
            'lm_studio_url': 'http://localhost:5555/v1',
            'ollama_url': 'http://localhost:2233/api/generate',
            'default_prompt': 'New default prompt'
        }
        # Avoid actually touching user .env
        with patch('routes.main.os.path.exists', return_value=False), \
             patch('routes.main.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            resp = client.post('/save_config', data=payload)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'success' in data


class TestAPIKeyTests:
    def test_test_api_key_missing_key(self, client):
        resp = client.post('/test_api_key', json={'type': 'openrouter'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_test_api_key_invalid_type(self, client):
        resp = client.post('/test_api_key', json={'type': 'invalid', 'key': 'x'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False


class TestExternalServiceTests:
    def test_test_lm_studio_connection_error(self, client):
        with patch('requests.post', side_effect=Exception('boom')):
            resp = client.post('/test_lm_studio', json={'url': 'http://localhost:9'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_test_ollama_connection_error(self, client):
        with patch('requests.post', side_effect=Exception('boom')):
            resp = client.post('/test_ollama', json={'url': 'http://localhost:9'})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False


