"""
Additional tests for tasks.py error paths and sync helpers.
"""

from tasks import (
    cancel_batch_processing,
    pause_batch_processing,
    process_batch,
    process_job_sync,
    process_submission_sync,
    resume_batch_processing,
    retry_batch_failed_jobs,
    update_batch_progress,
)


class TestTasksHelpers:
    def test_process_job_sync_nonexistent_job(self, app):
        """Test process_job_sync returns False for non-existent job."""
        assert process_job_sync("nonexistent") is False

    def test_process_submission_sync_nonexistent(self, app):
        """Test process_submission_sync returns False for non-existent
        submission."""
        assert process_submission_sync("nonexistent") is False

    def test_update_batch_progress_nonexistent(self, app):
        """Test update_batch_progress returns False for non-existent batch."""
        assert update_batch_progress("nonexistent") is False


class TestTasksBatchErrors:
    def test_process_batch_nonexistent(self, app):
        """Test process_batch returns False for non-existent batch."""
        assert process_batch.run("nonexistent") is False

    def test_retry_batch_failed_jobs_nonexistent(self, app):
        """Test retry_batch_failed_jobs returns 0 for non-existent batch."""
        assert retry_batch_failed_jobs.run("nonexistent") == 0

    def test_pause_resume_cancel_nonexistent(self, app):
        """Test pause/resume/cancel operations return False for non-existent
        batch."""
        assert pause_batch_processing.run("nonexistent") is False
        assert resume_batch_processing.run("nonexistent") is False
        assert cancel_batch_processing.run("nonexistent") is False
