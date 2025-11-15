"""
Unit tests for batch job management UI endpoints.
Tests the API endpoints that the batch job management UI uses.
"""

import pytest


class TestBatchUIEndpoints:
    """Test cases for batch job management UI endpoints."""

    @pytest.mark.api
    @pytest.mark.integration
    def test_get_available_jobs_for_batch_endpoint(self, client, sample_batch):
        """Test GET /api/batches/{batch_id}/available-jobs endpoint."""
        response = client.get(f"/api/batches/{sample_batch.id}/available-jobs")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert "available_jobs" in data
        assert "pagination" in data
        assert isinstance(data["available_jobs"], list)

    @pytest.mark.api
    @pytest.mark.integration
    def test_get_batch_settings_endpoint(self, client, sample_batch):
        """Test GET /api/batches/{batch_id}/settings endpoint."""
        response = client.get(f"/api/batches/{sample_batch.id}/settings")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert "settings" in data
        settings = data["settings"]
        assert "can_add_jobs" in settings
        assert "batch_name" in settings
        assert "batch_status" in settings

    @pytest.mark.api
    @pytest.mark.integration
    def test_create_job_in_batch_endpoint(self, client, sample_batch):
        """Test POST /api/batches/{batch_id}/jobs/create endpoint."""
        json_data = {
            "job_name": "Test UI Job",
            "description": "A job created via UI endpoint",
            "provider": "openrouter",
            "prompt": "Please grade this document.",
        }
        response = client.post(f"/api/batches/{sample_batch.id}/jobs/create", json=json_data)
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert "job" in data
        job = data["job"]
        assert job["job_name"] == "Test UI Job"
        assert job["description"] == "A job created via UI endpoint"
        assert job["provider"] == "openrouter"
        assert job["prompt"] == "Please grade this document."

    @pytest.mark.api
    @pytest.mark.integration
    def test_add_jobs_to_batch_endpoint(self, client, sample_batch, sample_job):
        """Test POST /api/batches/{batch_id}/jobs endpoint."""
        response = client.post(f"/api/batches/{sample_batch.id}/jobs", json={"job_ids": [sample_job.id]})
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert "added_jobs" in data
        assert len(data["added_jobs"]) == 1
        assert data["added_jobs"][0]["id"] == sample_job.id

    @pytest.mark.api
    @pytest.mark.integration
    def test_create_job_in_batch_missing_name(self, client, sample_batch):
        """Test creating job in batch without job name fails."""
        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create",
            json={"description": "Missing job name"},
        )
        assert response.status_code == 400

        data = response.get_json()
        assert data["success"] is False
        assert "Job name is required" in data["error"]

    @pytest.mark.api
    @pytest.mark.integration
    def test_add_jobs_to_batch_no_job_ids(self, client, sample_batch):
        """Test adding jobs to batch with no job IDs fails."""
        response = client.post(f"/api/batches/{sample_batch.id}/jobs", json={})
        assert response.status_code == 400

        data = response.get_json()
        assert data["success"] is False
        assert "No job IDs provided" in data["error"]

    @pytest.mark.api
    @pytest.mark.integration
    def test_batch_endpoints_with_nonexistent_batch(self, client):
        """Test batch endpoints with nonexistent batch ID."""
        # Test available jobs endpoint
        response = client.get("/api/batches/99999/available-jobs")
        assert response.status_code in [400, 404]

        # Test settings endpoint
        response = client.get("/api/batches/99999/settings")
        assert response.status_code in [400, 404]

        # Test create job endpoint
        response = client.post("/api/batches/99999/jobs/create", json={"job_name": "Test Job"})
        assert response.status_code in [400, 404]

        # Test add jobs endpoint
        response = client.post("/api/batches/99999/jobs", json={"job_ids": [1]})
        assert response.status_code in [400, 404]

    @pytest.mark.api
    @pytest.mark.integration
    def test_batch_endpoints_with_invalid_batch_id(self, client):
        """Test batch endpoints with invalid batch ID format."""
        # Test available jobs endpoint
        response = client.get("/api/batches/invalid-id/available-jobs")
        assert response.status_code == 400

        # Test settings endpoint
        response = client.get("/api/batches/invalid-id/settings")
        assert response.status_code == 400

        # Test create job endpoint
        response = client.post("/api/batches/invalid-id/jobs/create", json={"job_name": "Test Job"})
        assert response.status_code == 400

        # Test add jobs endpoint
        response = client.post("/api/batches/invalid-id/jobs", json={"job_ids": [1]})
        assert response.status_code == 400

    @pytest.mark.api
    @pytest.mark.integration
    def test_batch_endpoints_pagination(self, client, sample_batch):
        """Test batch endpoints support pagination parameters."""
        # Test available jobs with pagination
        response = client.get(f"/api/batches/{sample_batch.id}/available-jobs?page=1&per_page=10")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert "pagination" in data
        pagination = data["pagination"]
        assert "page" in pagination
        assert "per_page" in pagination
        assert "total" in pagination
        # The API uses 'pages' instead of 'total_pages'
        assert "pages" in pagination

    @pytest.mark.api
    @pytest.mark.integration
    def test_batch_endpoints_error_handling(self, client, sample_batch):
        """Test batch endpoints handle errors gracefully."""
        # Test with invalid JSON
        response = client.post(
            f"/api/batches/{sample_batch.id}/jobs/create",
            data="invalid json",
            content_type="application/json",
        )
        assert response.status_code == 400

        # Test with empty JSON
        response = client.post(f"/api/batches/{sample_batch.id}/jobs/create", json={})
        assert response.status_code == 400
