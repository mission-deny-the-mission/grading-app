"""
Unit tests for Flask routes and API endpoints.
"""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


class TestMainRoutes:
    """Test cases for main application routes."""

    def test_index_route(self, client):
        """Test the index route."""
        response = client.get("/")
        assert response.status_code == 200

    def test_jobs_route(self, client):
        """Test the jobs listing route."""
        response = client.get("/jobs")
        assert response.status_code == 200

    def test_batches_route(self, client):
        """Test the batches listing route."""
        response = client.get("/batches")
        assert response.status_code == 200

    def test_config_route(self, client):
        """Test the configuration route."""
        response = client.get("/config")
        assert response.status_code == 200

    def test_saved_configurations_route(self, client):
        """Test the saved configurations route."""
        response = client.get("/saved-configurations")
        assert response.status_code == 200


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    @pytest.mark.api
    def test_get_jobs_api(self, client, sample_job):
        """Test getting jobs via API."""
        response = client.get("/api/jobs")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1

        job_data = data[0]
        assert "id" in job_data
        assert "job_name" in job_data
        assert "status" in job_data
        assert "progress" in job_data

    def test_get_job_details_api(self, client, sample_job):
        """Test getting job details via API."""
        response = client.get(f"/api/jobs/{sample_job.id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["id"] == sample_job.id
        assert data["job_name"] == sample_job.job_name
        assert data["status"] == sample_job.status

    def test_get_nonexistent_job_api(self, client):
        """Test getting a job that doesn't exist."""
        response = client.get("/api/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_get_job_submissions_api(self, client, sample_job, sample_submission):
        """Test getting job submissions via API."""
        response = client.get(f"/api/jobs/{sample_job.id}/submissions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1

        submission_data = data[0]
        assert "id" in submission_data
        assert "original_filename" in submission_data
        assert "status" in submission_data

    def test_get_submission_details_api(self, client, sample_submission):
        """Test getting submission details via API."""
        response = client.get(f"/api/submissions/{sample_submission.id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["id"] == sample_submission.id
        assert data["original_filename"] == sample_submission.original_filename
        assert data["status"] == sample_submission.status

    def test_get_batches_api(self, client, sample_batch):
        """Test getting batches via API."""
        response = client.get("/api/batches")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "batches" in data
        assert isinstance(data["batches"], list)
        assert len(data["batches"]) >= 1

        batch_data = data["batches"][0]
        assert "id" in batch_data
        assert "batch_name" in batch_data
        assert "status" in batch_data

    def test_get_batch_details_api(self, client, sample_batch):
        """Test getting batch details via API."""
        response = client.get(f"/api/batches/{sample_batch.id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "batch" in data
        assert data["batch"]["id"] == sample_batch.id
        assert data["batch"]["batch_name"] == sample_batch.batch_name
        assert data["batch"]["status"] == sample_batch.status

    def test_get_models_api(self, client):
        """Test getting available models via API."""
        response = client.get("/api/models")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "openrouter" in data
        assert "claude" in data
        assert "lm_studio" in data

    def test_get_models_by_provider_api(self, client):
        """Test getting models for a specific provider."""
        response = client.get("/api/models/openrouter")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "popular" in data
        assert "default" in data

    def test_get_saved_prompts_api(self, client):
        """Test getting saved prompts via API."""
        response = client.get("/api/saved-prompts")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "prompts" in data
        assert isinstance(data["prompts"], list)

    def test_get_saved_marking_schemes_api(self, client):
        """Test getting saved marking schemes via API."""
        response = client.get("/api/saved-marking-schemes")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "schemes" in data
        assert isinstance(data["schemes"], list)


class TestFileUpload:
    """Test cases for file upload functionality."""

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False)
    def test_single_file_upload(self, mock_process_job, client, sample_text_file):
        """Test uploading a single file."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        # Patch the app's OPENROUTER_API_KEY to simulate missing key
        with patch("app.OPENROUTER_API_KEY", ""):
            with open(sample_text_file, "rb") as f:
                response = client.post(
                    "/upload",
                    data={
                        "file": (f, "test_document.txt"),
                        "prompt": "Please grade this document.",
                        "provider": "openrouter",
                        "customModel": "anthropic/claude-3-5-sonnet-20241022",
                    },
                )

            # The upload will fail because API keys are not configured in test environment
            assert response.status_code == 400

            data = json.loads(response.data)
            assert "error" in data
            assert "API key" in data["error"]

    @patch("tasks.process_job.delay")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False)
    def test_file_upload_with_marking_scheme(self, mock_process_job, client, sample_text_file):
        """Test uploading a file with a marking scheme."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        # Create marking scheme content
        marking_scheme_content = "Test marking scheme content"

        # Patch the app's OPENROUTER_API_KEY to simulate missing key
        with patch("app.OPENROUTER_API_KEY", ""):
            with open(sample_text_file, "rb") as f:
                response = client.post(
                    "/upload",
                    data={
                        "file": (f, "test_document.txt"),
                        "prompt": "Please grade this document.",
                        "provider": "openrouter",
                        "customModel": "anthropic/claude-3-5-sonnet-20241022",
                        "marking_scheme": (
                            BytesIO(marking_scheme_content.encode()),
                            "rubric.txt",
                        ),
                    },
                )

            # The upload will fail because API keys are not configured in test environment
            assert response.status_code == 400

            data = json.loads(response.data)
            assert "error" in data
            assert "API key" in data["error"]

    def test_file_upload_invalid_file(self, client):
        """Test uploading an invalid file."""
        response = client.post(
            "/upload",
            data={
                "file": (BytesIO(b"invalid content"), ""),
                "prompt": "Please grade this document.",
                "provider": "openrouter",
            },
        )

        assert response.status_code == 400

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False)
    def test_file_upload_missing_required_fields(self, client, sample_text_file):
        """Test uploading a file with missing required fields."""
        # Patch the app's OPENROUTER_API_KEY to simulate missing key
        with patch("app.OPENROUTER_API_KEY", ""):
            with open(sample_text_file, "rb") as f:
                response = client.post(
                    "/upload",
                    data={
                        "file": (f, "test_document.txt")
                        # Missing prompt and provider
                    },
                )

            assert response.status_code == 400

    @patch("tasks.process_batch.delay")
    def test_bulk_upload(self, mock_process_batch, client, sample_text_file):
        """Test bulk file upload."""
        mock_process_batch.return_value = MagicMock(id="test-task-id")

        with open(sample_text_file, "rb") as f:
            response = client.post(
                "/upload_bulk",
                data={
                    "files[]": (f, "test_document.txt"),
                    "job_name": "Test Bulk Job",
                    "description": "A test bulk job",
                    "provider": "openrouter",
                    "customModel": "anthropic/claude-3-5-sonnet-20241022",
                    "prompt": "Please grade these documents.",
                },
            )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "job_id" in data


class TestJobManagement:
    """Test cases for job management functionality."""

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job(self, mock_process_job, client):
        """Test creating a new job."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        response = client.post(
            "/create_job",
            json={
                "job_name": "Test Job",
                "description": "A test job",
                "provider": "openrouter",
                "customModel": "anthropic/claude-3-5-sonnet-20241022",
                "prompt": "Please grade this document.",
                "priority": 5,
                "temperature": 0.7,
                "max_tokens": 2000,
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "job_id" in data

    def test_create_job_missing_fields(self, client):
        """Test creating a job with missing required fields."""
        response = client.post(
            "/create_job",
            json={
                "job_name": "Test Job"
                # Missing required fields
            },
        )

        assert response.status_code == 400

    @patch("tasks.process_job.delay")
    def test_retry_job(self, mock_process_job, client, sample_job):
        """Test retrying a job."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        # Create a failed submission
        from models import Submission, db

        with client.application.app_context():
            submission = Submission(
                job_id=sample_job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                status="failed",
                error_message="Test error",
            )
            db.session.add(submission)
            db.session.commit()

        response = client.post(f"/api/jobs/{sample_job.id}/retry")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    def test_retry_nonexistent_job(self, client):
        """Test retrying a job that doesn't exist."""
        response = client.post("/api/jobs/nonexistent-id/retry")
        assert response.status_code == 404


class TestBatchManagement:
    """Test cases for batch management functionality."""

    @pytest.mark.api
    @patch("tasks.process_batch.delay")
    def test_create_batch(self, mock_process_batch, client):
        """Test creating a new batch."""
        mock_process_batch.return_value = MagicMock(id="test-task-id")

        response = client.post(
            "/create_batch",
            json={
                "batch_name": "Test Batch",
                "description": "A test batch",
                "priority": 5,
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "batch_id" in data

    @patch("tasks.pause_batch_processing.delay")
    def test_pause_batch(self, mock_pause_batch, client, sample_batch):
        """Test pausing a batch."""
        mock_pause_batch.return_value = MagicMock(id="test-task-id")

        response = client.post(f"/api/batches/{sample_batch.id}/pause")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    @patch("tasks.resume_batch_processing.delay")
    def test_resume_batch(self, mock_resume_batch, client, sample_batch):
        """Test resuming a batch."""
        mock_resume_batch.return_value = MagicMock(id="test-task-id")

        response = client.post(f"/api/batches/{sample_batch.id}/resume")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    @patch("tasks.cancel_batch_processing.delay")
    def test_cancel_batch(self, mock_cancel_batch, client, sample_batch):
        """Test canceling a batch."""
        mock_cancel_batch.return_value = MagicMock(id="test-task-id")

        response = client.post(f"/api/batches/{sample_batch.id}/cancel")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    def test_add_jobs_to_batch(self, client, sample_batch, sample_job):
        """Test adding existing jobs to a batch."""
        response = client.post(f"/api/batches/{sample_batch.id}/jobs", json={"job_ids": [sample_job.id]})

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "added_jobs" in data
        assert len(data["added_jobs"]) == 1
        assert data["added_jobs"][0]["id"] == sample_job.id

    def test_add_jobs_to_batch_no_job_ids(self, client, sample_batch):
        """Test adding jobs to batch with no job IDs provided."""
        response = client.post(f"/api/batches/{sample_batch.id}/jobs", json={})

        assert response.status_code == 400

        data = json.loads(response.data)
        assert data["success"] is False
        assert "No job IDs provided" in data["error"]

    def test_create_job_in_batch(self, client, sample_batch):
        """Test creating a new job within a batch."""
        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create",
            json={
                "job_name": "New Batch Job",
                "description": "A job created in the batch",
                "provider": "openrouter",
                "prompt": "Custom prompt",
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "job" in data
        assert data["job"]["job_name"] == "New Batch Job"
        assert data["job"]["description"] == "A job created in the batch"
        assert data["job"]["provider"] == "openrouter"
        assert data["job"]["prompt"] == "Custom prompt"

    def test_create_job_in_batch_no_name(self, client, sample_batch):
        """Test creating a job in batch without job name."""
        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create",
            json={"description": "A job without name"},
        )

        assert response.status_code == 400

        data = json.loads(response.data)
        assert data["success"] is False
        assert "Job name is required" in data["error"]

    def test_get_available_jobs_for_batch(self, client, sample_batch):
        """Test getting available jobs that can be added to a batch."""
        # Create a standalone job (not in any batch)
        from models import GradingJob, db

        with client.application.app_context():
            standalone_job = GradingJob(job_name="Standalone Job", provider="openrouter", prompt="Test prompt")
            db.session.add(standalone_job)
            db.session.commit()
            standalone_job_id = standalone_job.id

        response = client.get(f"/api/batches/{sample_batch.id}/available-jobs")

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "available_jobs" in data
        assert "pagination" in data

        # Check that the standalone job is in the available jobs
        job_ids = [job["id"] for job in data["available_jobs"]]
        assert standalone_job_id in job_ids

    def test_get_batch_settings(self, client, sample_batch):
        """Test getting batch settings summary."""
        response = client.get(f"/api/batches/{sample_batch.id}/settings")

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "settings" in data
        settings = data["settings"]
        assert "can_add_jobs" in settings
        assert "batch_name" in settings
        assert "batch_status" in settings

    def test_remove_job_from_batch(self, client, sample_batch):
        """Test removing a job from a batch."""
        # First create and add a job to the batch
        from models import GradingJob, db

        with client.application.app_context():
            job = GradingJob(job_name="Job to Remove", provider="openrouter", prompt="Test prompt")
            db.session.add(job)
            db.session.commit()

            # Add job to batch
            sample_batch = db.session.merge(sample_batch)
            sample_batch.add_job(job)
            job_id = job.id

        # Remove job from batch
        response = client.delete(f"/api/batches/{sample_batch.id}/jobs/{job_id}")

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "message" in data

    def test_batch_analytics(self, client, sample_batch):
        """Test getting batch analytics."""
        response = client.get(f"/api/batches/{sample_batch.id}/analytics")

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "analytics" in data
        analytics = data["analytics"]
        assert "overview" in analytics
        assert "job_status_breakdown" in analytics
        assert "provider_breakdown" in analytics
        assert "timeline" in analytics


class TestSavedConfigurations:
    """Test cases for saved configurations functionality."""

    @pytest.mark.api
    def test_save_prompt(self, client):
        """Test saving a prompt."""
        response = client.post(
            "/api/saved-prompts",
            json={
                "name": "Test Prompt",
                "description": "A test prompt",
                "category": "essay",
                "prompt_text": "Please grade this essay.",
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "prompt" in data
        assert "id" in data["prompt"]

    def test_save_marking_scheme(self, client):
        """Test saving a marking scheme."""
        response = client.post(
            "/api/saved-marking-schemes",
            json={
                "name": "Test Scheme",
                "description": "A test marking scheme",
                "category": "essay",
                "content": "Test marking scheme content",
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "scheme" in data
        assert "id" in data["scheme"]

    def test_delete_saved_prompt(self, client):
        """Test deleting a saved prompt."""
        # First create a prompt
        create_response = client.post(
            "/api/saved-prompts",
            json={
                "name": "Test Prompt",
                "description": "A test prompt",
                "category": "essay",
                "prompt_text": "Please grade this essay.",
            },
        )

        prompt_data = json.loads(create_response.data)
        prompt_id = prompt_data["prompt"]["id"]

        # Then delete it
        response = client.delete(f"/api/saved-prompts/{prompt_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True

    def test_delete_saved_marking_scheme(self, client):
        """Test deleting a saved marking scheme."""
        # First create a marking scheme
        create_response = client.post(
            "/api/saved-marking-schemes",
            json={
                "name": "Test Scheme",
                "description": "A test marking scheme",
                "category": "essay",
                "content": "Test marking scheme content",
            },
        )

        scheme_data = json.loads(create_response.data)
        scheme_id = scheme_data["scheme"]["id"]

        # Then delete it
        response = client.delete(f"/api/saved-marking-schemes/{scheme_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True


class TestErrorHandling:
    """Test cases for error handling."""

    @pytest.mark.api
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_413_error(self, client):
        """Test 413 error handling for large files."""
        # Create a large file content (101MB, over the 100MB limit)
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB

        response = client.post(
            "/upload",
            data={
                "file": (BytesIO(large_content), "large_file.txt"),
                "prompt": "Please grade this document.",
                "provider": "openrouter",
            },
        )

        assert response.status_code == 413

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post("/create_job", data="invalid json", content_type="application/json")

        assert response.status_code == 400


class TestBatchJobCreationWithFiles:
    """Test cases for batch job creation with file uploads."""

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job_with_files_success(self, mock_process_job, client, sample_batch, sample_text_file):
        """Test successful job creation with file upload in batch."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "job_name": "Test Job with Files",
                    "description": "A test job with file uploads",
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["job"]["job_name"] == "Test Job with Files"
        assert data["uploaded_files"] == 1
        assert "job" in data
        assert "batch" in data

        # Verify the background task was queued
        mock_process_job.assert_called_once()

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job_with_multiple_files(
        self, mock_process_job, client, sample_batch, sample_text_file, sample_docx_file
    ):
        """Test job creation with multiple files."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        with open(sample_text_file, "rb") as f1, open(sample_docx_file, "rb") as f2:
            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "job_name": "Multi-File Test Job",
                    "files[]": [(f1, "document1.txt"), (f2, "document2.docx")],
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["uploaded_files"] == 2

        # Verify the background task was queued
        mock_process_job.assert_called_once()

    @pytest.mark.api
    def test_create_job_with_files_missing_job_name(self, client, sample_batch, sample_text_file):
        """Test job creation fails without job name."""
        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "description": "Missing job name",
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Job name is required" in data["error"]

    @pytest.mark.api
    def test_create_job_with_files_missing_files(self, client, sample_batch):
        """Test job creation fails without files."""
        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create-with-files",
            data={"job_name": "Job Without Files"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "No files provided" in data["error"]

    @pytest.mark.api
    def test_create_job_with_files_invalid_batch(self, client, sample_text_file):
        """Test job creation fails with invalid batch ID."""
        with open(sample_text_file, "rb") as f:
            response = client.post(
                "/api/batches/99999/jobs/create-with-files",
                data={"job_name": "Test Job", "files[]": (f, "test_document.txt")},
            )

        # Flask might return 400 for certain invalid ID formats
        assert response.status_code in [400, 404]

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job_with_files_inherits_batch_settings(self, mock_process_job, client, app, sample_text_file):
        """Test that job creation inherits batch settings correctly."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        with app.app_context():
            from models import JobBatch, db

            # Create a batch with specific settings
            batch = JobBatch(
                batch_name="Batch with Settings",
                provider="claude",
                model="claude-3-sonnet",
                temperature=0.8,
                max_tokens=1500,
                prompt="Custom batch prompt",
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{batch_id}/jobs/create-with-files",
                data={
                    "job_name": "Inheritance Test Job",
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check that job inherited batch settings
        job = data["job"]
        assert job["provider"] == "claude"
        assert job["model"] == "claude-3-sonnet"
        assert job["temperature"] == 0.8
        assert job["max_tokens"] == 1500
        assert job["prompt"] == "Custom batch prompt"

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job_with_files_override_batch_settings(self, mock_process_job, client, app, sample_text_file):
        """Test that job creation can override batch settings."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        with app.app_context():
            from models import JobBatch, db

            # Create a batch with default settings
            batch = JobBatch(batch_name="Default Batch", provider="openrouter", temperature=0.3)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{batch_id}/jobs/create-with-files",
                data={
                    "job_name": "Override Test Job",
                    "provider": "claude",  # Override batch setting
                    "temperature": "0.9",  # Override batch setting
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check that job used override settings
        job = data["job"]
        assert job["provider"] == "claude"
        assert job["temperature"] == 0.9

    @pytest.mark.api
    def test_create_job_with_unsupported_files(self, client, sample_batch):
        """Test job creation with unsupported file types."""
        # Create a fake image file
        image_content = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        )

        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create-with-files",
            data={
                "job_name": "Unsupported File Test",
                "files[]": (BytesIO(image_content), "test_image.png"),
            },
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "No valid files were uploaded" in data["error"]

    @pytest.mark.api
    def test_create_job_with_large_files_under_limit(self, client, sample_batch):
        """Test job creation with files under the 100MB limit."""
        # Create a 50MB file (under limit)
        large_content = b"x" * (50 * 1024 * 1024)

        with patch("tasks.process_job.delay") as mock_process_job:
            mock_process_job.return_value = MagicMock(id="test-task-id")

            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "job_name": "Large File Test",
                    "files[]": (BytesIO(large_content), "large_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["uploaded_files"] == 1

    @pytest.mark.api
    def test_create_job_with_files_over_limit(self, client, sample_batch):
        """Test job creation fails with files over 100MB limit."""
        # Create a 101MB file (over limit)
        large_content = b"x" * (101 * 1024 * 1024)

        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create-with-files",
            data={
                "job_name": "Oversized File Test",
                "files[]": (BytesIO(large_content), "oversized_document.txt"),
            },
        )

        # The request might be rejected at different levels
        # Either 413 (Flask level) or 400 (our endpoint level) is acceptable
        assert response.status_code in [400, 413]

        if response.status_code == 400:
            # If it's a 400, make sure it's due to file size
            data = json.loads(response.data)
            assert not data["success"]

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job_with_files_database_persistence(
        self, mock_process_job, client, app, sample_batch, sample_text_file
    ):
        """Test that job and submissions are properly persisted to database."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "job_name": "Persistence Test Job",
                    "description": "Testing database persistence",
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        job_id = data["job"]["id"]

        # Verify job was persisted to database
        with app.app_context():
            from models import GradingJob, db

            job = db.session.get(GradingJob, job_id)
            assert job is not None
            assert job.job_name == "Persistence Test Job"
            assert job.description == "Testing database persistence"
            assert job.batch_id == sample_batch.id
            assert len(job.submissions) == 1

            # Verify submission was created
            submission = job.submissions[0]
            assert submission.original_filename == "test_document.txt"
            assert submission.file_type == "txt"
            assert submission.status == "pending"

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_job_with_files_updates_batch_progress(
        self, mock_process_job, client, app, sample_batch, sample_text_file
    ):
        """Test that creating a job updates batch progress."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "job_name": "Progress Test Job",
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check that batch information is updated
        batch_data = data["batch"]
        assert batch_data["total_jobs"] >= 1
        assert "progress" in batch_data

    @pytest.mark.api
    @patch("werkzeug.datastructures.FileStorage.save")
    def test_create_job_with_files_handles_file_processing_errors(
        self, mock_save, client, sample_batch, sample_text_file
    ):
        """Test that file processing errors are handled gracefully."""
        # Mock file save to simulate errors
        mock_save.side_effect = OSError("Cannot save file")

        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{sample_batch.id}/jobs/create-with-files",
                data={
                    "job_name": "Error Handling Test",
                    "files[]": (f, "test_document.txt"),
                },
            )

        # Should return error status
        assert response.status_code == 400


class TestBatchMultiModelComparison:
    """Test cases for batch multi-model comparison functionality."""

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_create_batch_with_multi_model_comparison(self, mock_process_job, client, app):
        """Test creating a batch with multi-model comparison enabled."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        models_to_compare = ["anthropic/claude-3-5-sonnet-20241022", "openai/gpt-4o"]

        response = client.post(
            "/create_batch",
            json={
                "batch_name": "Multi-Model Test Batch",
                "description": "A batch with multi-model comparison",
                "provider": "openrouter",
                "models_to_compare": models_to_compare,
                "priority": 5,
            },
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify batch was created with multi-model settings
        with app.app_context():
            from models import JobBatch, db

            batch = db.session.get(JobBatch, data["batch_id"])
            assert batch is not None
            assert batch.models_to_compare == models_to_compare

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_batch_job_inherits_multi_model_settings(self, mock_process_job, client, app, sample_text_file):
        """Test that jobs created in multi-model batch inherit the multi-model settings."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        models_to_compare = ["anthropic/claude-3-5-sonnet-20241022", "openai/gpt-4o"]

        with app.app_context():
            from models import JobBatch, db

            # Create batch with multi-model comparison
            batch = JobBatch(
                batch_name="Multi-Model Batch",
                provider="openrouter",
                models_to_compare=models_to_compare,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        # Create job with files in the batch
        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{batch_id}/jobs/create-with-files",
                data={
                    "job_name": "Multi-Model Inheritance Test",
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify job inherited multi-model settings
        job = data["job"]
        assert job["models_to_compare"] == models_to_compare

    @pytest.mark.api
    @patch("tasks.process_job.delay")
    def test_batch_job_override_multi_model_settings(self, mock_process_job, client, app, sample_text_file):
        """Test that jobs can override batch multi-model settings."""
        mock_process_job.return_value = MagicMock(id="test-task-id")

        batch_models = ["anthropic/claude-3-5-sonnet-20241022", "openai/gpt-4o"]
        job_models = ["openai/gpt-4o", "meta-llama/llama-3.1-70b-instruct"]

        with app.app_context():
            from models import JobBatch, db

            # Create batch with multi-model comparison
            batch = JobBatch(
                batch_name="Multi-Model Batch",
                provider="openrouter",
                models_to_compare=batch_models,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        # Create job with different models
        with open(sample_text_file, "rb") as f:
            response = client.post(
                f"/api/batches/{batch_id}/jobs/create-with-files",
                data={
                    "job_name": "Override Test",
                    "models_to_compare[]": job_models,
                    "files[]": (f, "test_document.txt"),
                },
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify job used override models
        job = data["job"]
        assert job["models_to_compare"] == job_models
        assert job["models_to_compare"] != batch_models

    @pytest.mark.api
    def test_batch_displays_multi_model_info(self, client, app):
        """Test that batch detail page displays multi-model comparison information."""
        models_to_compare = [
            "anthropic/claude-3-5-sonnet-20241022",
            "openai/gpt-4o",
            "claude-3-5-sonnet-20241022",
        ]

        with app.app_context():
            from models import JobBatch, db

            # Create batch with multi-model comparison
            batch = JobBatch(
                batch_name="Display Test Batch",
                description="Testing multi-model display",
                provider="openrouter",
                models_to_compare=models_to_compare,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            # Debug: verify the batch data was saved correctly
            saved_batch = JobBatch.query.get(batch_id)
            print(f"Saved batch models_to_compare: {saved_batch.models_to_compare}")
            print(f"Length: {len(saved_batch.models_to_compare) if saved_batch.models_to_compare else 'None'}")

        # Get batch detail page
        response = client.get(f"/batches/{batch_id}")
        assert response.status_code == 200

        # Check that multi-model information is displayed
        html_content = response.data.decode("utf-8")
        assert "Multi-Model Comparison" in html_content

        # The template splits this text across lines, so we need to account for spacing
        enabled_patterns = [
            f"Enabled ({len(models_to_compare)}\nmodels)",
            f"Enabled ({len(models_to_compare)} models)",
            f"Enabled ({len(models_to_compare)}\n                            models)",
        ]

        found_pattern = False
        for pattern in enabled_patterns:
            if pattern in html_content:
                found_pattern = True
                break

        assert found_pattern, f"Could not find 'Enabled ({len(models_to_compare)} models)' or variants in HTML"

        # Check that individual models are displayed
        for model in models_to_compare:
            assert model in html_content
