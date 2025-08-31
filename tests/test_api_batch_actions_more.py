"""
More tests for batch action endpoints: start, pause, resume, cancel, retry.
"""

import json
from unittest.mock import MagicMock, patch


def _create_batch(client, app, **kwargs):
    """Create a test batch and return its ID."""
    with app.app_context():
        from models import JobBatch, db

        batch = JobBatch(batch_name=kwargs.get("name", "ActionBatch"))
        db.session.add(batch)
        db.session.commit()
        return batch.id


@patch("tasks.process_batch.delay")
def test_start_batch_success(mock_delay, client, app):
    """Test successful batch start via API."""
    mock_delay.return_value = MagicMock()
    bid = _create_batch(client, app)
    # Add a pending job to satisfy can_start()
    with app.app_context():
        from models import GradingJob, db

        job = GradingJob(
            job_name="BJob", provider="openrouter", prompt="p", batch_id=bid
        )
        db.session.add(job)
        db.session.commit()
    resp = client.post(f"/api/batches/{bid}/start")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["success"] is True


@patch("tasks.pause_batch_processing.delay")
def test_pause_batch_success(mock_delay, client, app):
    """Test successful batch pause via API."""
    mock_delay.return_value = MagicMock()
    bid = _create_batch(client, app)
    resp = client.post(f"/api/batches/{bid}/pause")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["success"] is True


@patch("tasks.resume_batch_processing.delay")
def test_resume_batch_success(mock_delay, client, app):
    """Test successful batch resume via API."""
    mock_delay.return_value = MagicMock()
    bid = _create_batch(client, app)
    resp = client.post(f"/api/batches/{bid}/resume")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["success"] is True


@patch("tasks.cancel_batch_processing.delay")
def test_cancel_batch_success(mock_delay, client, app):
    """Test successful batch cancel via API."""
    mock_delay.return_value = MagicMock()
    bid = _create_batch(client, app)
    resp = client.post(f"/api/batches/{bid}/cancel")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["success"] is True


@patch("tasks.retry_batch_failed_jobs.delay")
def test_retry_batch_no_failed(mock_delay, client, app):
    """Test batch retry when no failed jobs exist."""
    mock_delay.return_value = MagicMock()
    bid = _create_batch(client, app)
    # By default no failed jobs, expect 400
    resp = client.post(f"/api/batches/{bid}/retry")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["success"] is False
