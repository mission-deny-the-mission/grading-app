"""
Success-path tests for /test_api_key and external service checks in routes.main.
Also includes a success case for upload_marking_scheme.
"""

import io
import json
from unittest.mock import MagicMock, patch


class TestApiKeySuccess:
    def test_openrouter_key_success(self, client):
        # Since the requests patching is causing scoping issues, let's test this
        # by temporarily modifying the environment/behavior

        # Try a more targeted patch - patch the specific route function instead
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"choices": [{"message": {"content": "Hello"}}]}
        fake_resp.text = "OK"

        # Mock at the exact import location where requests is used in the function
        with patch("routes.main.requests.post", return_value=fake_resp):
            resp = client.post(
                "/test_api_key", json={"type": "openrouter", "key": "ok"}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)



        assert data["success"] is True

    def test_claude_key_success(self, client):
        """Test successful Claude API key validation."""
        fake = MagicMock()
        fake.messages.create.return_value = MagicMock()
        with patch("routes.main.Anthropic", return_value=fake):
            resp = client.post(
                "/test_api_key", json={"type": "claude", "key": "ok"}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_gemini_key_success(self, client):
        """Test successful Gemini API key validation."""
        fake_model = MagicMock()
        fake_model.generate_content.return_value = MagicMock()
        with patch("google.generativeai.configure"), patch(
            "google.generativeai.GenerativeModel", return_value=fake_model
        ):
            resp = client.post(
                "/test_api_key", json={"type": "gemini", "key": "ok"}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_openai_key_success(self, client):
        """Test successful OpenAI API key validation."""
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock()
        with patch("routes.main.openai.OpenAI", return_value=fake_client):
            resp = client.post(
                "/test_api_key", json={"type": "openai", "key": "ok"}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True


class TestExternalChecksSuccess:
    """Test successful external service checks."""
    def test_lm_studio_success(self, client):
        """Test successful LM Studio connection check."""
        fake_resp = MagicMock(status_code=200)
        with patch("requests.post", return_value=fake_resp):
            resp = client.post("/test_lm_studio", json={"url": "http://x"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True

    def test_ollama_success(self, client):
        """Test successful Ollama connection check."""
        # Mock the GET request to /api/tags (returns available models)
        fake_get_resp = MagicMock(status_code=200)
        fake_get_resp.json.return_value = {
            "models": [{"name": "llama2"}]  # A generative model
        }

        # Mock the POST request to /api/generate (successful generation)
        fake_post_resp = MagicMock(status_code=200)

        with patch("requests.get", return_value=fake_get_resp), \
             patch("requests.post", return_value=fake_post_resp):
            resp = client.post("/test_ollama", json={"url": "http://x"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True


class TestUploadMarkingSchemeSuccess:
    """Test successful marking scheme upload."""
    def test_upload_marking_scheme_success(self, client):
        """Test successful marking scheme upload endpoint."""
        data = {
            "marking_scheme": (
                io.BytesIO(b"RUBRIC: 1) Content 2) Structure"),
                "rubric.txt",
            ),
            "name": "Rubric",
            "description": "Test rubric",
        }
        resp = client.post("/upload_marking_scheme", data=data)
        assert resp.status_code == 200
        payload = json.loads(resp.data)
        assert payload["success"] is True and "marking_scheme_id" in payload
