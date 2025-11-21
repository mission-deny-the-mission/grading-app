"""
Deeper tasks.py grading loop branches: provider mapping errors
and model failures.
"""

import os
from unittest.mock import MagicMock, patch

from models import GradingJob, Submission, db
from tasks import process_batch, process_submission_sync


def test_process_submission_sync_provider_not_found(app, tmp_path):
    """Test submission processing fails with unknown provider."""
    with app.app_context():
        job = GradingJob(job_name="Bad Provider", provider="unknown", prompt="p")
        db.session.add(job)
        db.session.commit()

        # Create file in uploads
        upload_folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        file_name = "x.txt"
        with open(f"{upload_folder}/{file_name}", "w") as f:
            f.write("content")

        sub = Submission(
            job_id=job.id,
            filename=file_name,
            original_filename=file_name,
            file_type="txt",
            status="pending",
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # Should fail early due to unsupported provider mapping
    assert process_submission_sync(sid) is False


def test_process_submission_sync_all_models_fail(app, tmp_path):
    """Test submission processing when all model requests fail."""
    with app.app_context():
        job = GradingJob(job_name="All Fail", provider="lm_studio", prompt="p")
        db.session.add(job)
        db.session.commit()

        # Create file
        upload_folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        file_name = "y.txt"
        with open(f"{upload_folder}/{file_name}", "w") as f:
            f.write("content")

        sub = Submission(
            job_id=job.id,
            filename=file_name,
            original_filename=file_name,
            file_type="txt",
            status="pending",
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # Make LM Studio return non-200 so result['success'] is False
    fake_resp = MagicMock(status_code=500, text="err")
    with patch("utils.llm_providers.requests.post", return_value=fake_resp):
        assert process_submission_sync(sid) is False


def test_process_batch_with_completed_jobs(app, sample_batch):
    """Test processing a batch where all jobs are already completed"""
    with app.app_context():
        # Create jobs directly to avoid session issues
        job1 = GradingJob(
            job_name="Job 1",
            provider="openrouter",
            prompt="test",
            batch_id=sample_batch.id,
            status="completed",
        )
        job2 = GradingJob(
            job_name="Job 2",
            provider="openrouter",
            prompt="test",
            batch_id=sample_batch.id,
            status="completed",
        )
        db.session.add(job1)
        db.session.add(job2)
        db.session.commit()

        result = process_batch(sample_batch.id)
        # process_batch returns True when it successfully checks the batch
        assert result is True


def test_process_batch_mixed_status_jobs(app, sample_batch):
    """Test processing a batch with mixed job statuses"""
    with app.app_context():
        # Create jobs with different statuses
        completed_job = GradingJob(
            job_name="Completed",
            provider="openrouter",
            prompt="test",
            batch_id=sample_batch.id,
            status="completed",
        )
        pending_job = GradingJob(
            job_name="Pending",
            provider="openrouter",
            prompt="test",
            batch_id=sample_batch.id,
            status="pending",
        )
        db.session.add(completed_job)
        db.session.add(pending_job)
        db.session.commit()
        pending_job_id = pending_job.id

    # Track processed jobs in this test scope
    processed_jobs = []

    def mock_submit(func, job_id, **kwargs):
        processed_jobs.append(job_id)
        return f"task-{job_id}"

    # Patch task_queue.submit and run the batch processing
    with patch("desktop.task_queue.task_queue.submit", side_effect=mock_submit):
        result = process_batch(sample_batch.id)

    # process_batch should return True and process the pending job
    assert result is True
    # The pending job should be processed exactly once
    assert len(processed_jobs) == 1
    assert processed_jobs[0] == pending_job_id
