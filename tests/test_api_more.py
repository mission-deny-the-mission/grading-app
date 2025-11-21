"""
Additional API route tests to increase coverage for routes.api and routes.upload.
"""

import io
import json
from unittest.mock import MagicMock, patch


class TestApiModels:
    """Test API model-related endpoints."""

    def test_get_models_unknown_provider(self, client):
        """Test getting models for unknown provider."""
        resp = client.get("/api/models/unknown")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "Unknown provider" in data["error"]


class TestApiJobsExports:
    """Test API job export functionality."""

    def test_export_job_results_zip(self, client, app, sample_job, sample_submission, tmp_path):
        """Test exporting job results as ZIP file."""
        # mark submission as completed with a grade to include in ZIP
        with app.app_context():
            from models import db

            sample_submission.status = "completed"
            sample_submission.grade = "Grade: A"
            db.session.commit()

        resp = client.get(f"/api/jobs/{sample_job.id}/export")
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/zip"


class TestApiJobActions:
    """Test API job action endpoints."""

    @patch("desktop.task_queue.task_queue.submit")
    def test_trigger_job_processing_success(self, mock_submit, client, sample_job):
        """Test successful job processing trigger."""
        mock_submit.return_value = "task123"
        resp = client.post(f"/api/jobs/{sample_job.id}/process")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True and data["task_id"] == "task123"

    def test_retry_failed_submissions_no_failed(self, client, sample_job):
        """Test retry when no failed submissions exist."""
        # sample_job has no failed submissions in fixture
        resp = client.post(f"/api/jobs/{sample_job.id}/retry")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["success"] is False

    @patch("desktop.task_queue.task_queue.submit")
    def test_retry_submission_success_path(self, mock_submit, client, app, sample_job, sample_submission, tmp_path):
        """Test successful submission retry with real file."""
        mock_submit.return_value = "task123"
        # create a real file so tasks code finds it
        file_path = tmp_path / "test_document.txt"
        file_path.write_text("hello world")
        with app.app_context():
            from models import db

            # Ensure submission file points to the path we created
            sample_submission.filename = file_path.name
            db.session.commit()

        # Allow retry
        with app.app_context():
            sample_submission.status = "failed"
            from models import db

            db.session.commit()

        resp = client.post(f"/api/submissions/{sample_submission.id}/retry")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True


class TestUploadRoutes:
    """Test upload route endpoints."""

    def test_upload_marking_scheme_missing_file(self, client):
        """Test upload marking scheme with missing file."""
        resp = client.post("/upload_marking_scheme", data={})
        assert resp.status_code == 400

    def test_upload_marking_scheme_unsupported_type(self, client):
        """Test upload marking scheme with unsupported file type."""
        data = {"marking_scheme": (io.BytesIO(b"invalid"), "file.png")}
        resp = client.post("/upload_marking_scheme", data=data)
        assert resp.status_code == 400

    def test_upload_unsupported_file_type(self, client):
        """Test upload with unsupported file type."""
        data = {
            "file": (io.BytesIO(b"data"), "file.png"),
            "prompt": "p",
            "provider": "openrouter",
        }
        resp = client.post("/upload", data=data)
        assert resp.status_code == 400

    def test_upload_provider_unknown(self, client):
        """Test upload with unknown provider."""
        data = {
            "file": (io.BytesIO(b"hello"), "file.txt"),
            "prompt": "p",
            "provider": "unknown",
        }
        resp = client.post("/upload", data=data)
        assert resp.status_code == 400

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False)
    def test_upload_missing_openrouter_key(self, client):
        """Test upload with missing OpenRouter API key."""
        data = {
            "file": (io.BytesIO(b"hello"), "file.txt"),
            "prompt": "p",
            "provider": "openrouter",
        }
        resp = client.post("/upload", data=data)
        assert resp.status_code == 400
