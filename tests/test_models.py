"""
Unit tests for database models.
"""

import pytest

from models import (
    GradingJob,
    JobBatch,
    MarkingScheme,
    SavedMarkingScheme,
    SavedPrompt,
    Submission,
    db,
)


class TestGradingJob:
    """Test cases for GradingJob model."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_job(self, app):
        """Test creating a new grading job."""
        with app.app_context():
            job = GradingJob(
                job_name="Test Job",
                description="A test job",
                provider="openrouter",
                model="anthropic/claude-3-5-sonnet-20241022",
                prompt="Please grade this document.",
                priority=5,
                temperature=0.7,
                max_tokens=2000,
            )

            # Add to session and commit to get default values
            db.session.add(job)
            db.session.commit()

            assert job.job_name == "Test Job"
            assert job.description == "A test job"
            assert job.provider == "openrouter"
            assert job.model == "anthropic/claude-3-5-sonnet-20241022"
            assert job.prompt == "Please grade this document."
            assert job.priority == 5
            assert job.temperature == 0.7
            assert job.max_tokens == 2000
            assert job.status == "pending"
            assert job.total_submissions == 0
            assert job.processed_submissions == 0
            assert job.failed_submissions == 0

    def test_job_to_dict(self, sample_job):
        """Test converting job to dictionary."""
        job_dict = sample_job.to_dict()

        assert "id" in job_dict
        assert "job_name" in job_dict
        assert "description" in job_dict
        assert "provider" in job_dict
        assert "model" in job_dict
        assert "prompt" in job_dict
        assert "status" in job_dict
        assert "progress" in job_dict
        assert "created_at" in job_dict
        assert "updated_at" in job_dict
        assert "temperature" in job_dict
        assert "max_tokens" in job_dict

    def test_job_progress_calculation(self, app, sample_job):
        """Test job progress calculation."""
        with app.app_context():
            # Create submissions with different statuses
            submission1 = Submission(
                job_id=sample_job.id,
                original_filename="test1.txt",
                filename="test1.txt",
                file_type="txt",
                status="completed",
            )
            submission2 = Submission(
                job_id=sample_job.id,
                original_filename="test2.txt",
                filename="test2.txt",
                file_type="txt",
                status="failed",
            )
            submission3 = Submission(
                job_id=sample_job.id,
                original_filename="test3.txt",
                filename="test3.txt",
                file_type="txt",
                status="pending",
            )

            db.session.add_all([submission1, submission2, submission3])
            db.session.commit()

            # Refresh the job to ensure it's attached to the current session
            db.session.add(sample_job)
            db.session.refresh(sample_job)

            # Update progress
            sample_job.update_progress()

            assert sample_job.total_submissions == 3
            assert sample_job.processed_submissions == 1
            assert sample_job.failed_submissions == 1
            assert sample_job.get_progress() == 66.67  # 2/3 * 100

    def test_job_status_updates(self, app, sample_job):
        """Test job status updates based on submissions."""
        with app.app_context():
            # Ensure job is attached to the current session
            sample_job = db.session.merge(sample_job)

            # Test with no submissions
            sample_job.update_status()
            assert sample_job.status == "pending"

            # Add a completed submission
            submission = Submission(
                job_id=sample_job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                status="completed",
            )
            db.session.add(submission)
            db.session.commit()

            sample_job.update_status()
            assert sample_job.status == "completed"

            # Add a failed submission
            submission2 = Submission(
                job_id=sample_job.id,
                original_filename="test2.txt",
                filename="test2.txt",
                file_type="txt",
                status="failed",
            )
            db.session.add(submission2)
            db.session.commit()

            sample_job.update_status()
            assert sample_job.status == "completed_with_errors"

    def test_job_retry_functionality(self, app, sample_job):
        """Test job retry functionality."""
        with app.app_context():
            # Ensure job is attached to the current session
            sample_job = db.session.merge(sample_job)
            # Create failed submissions
            submission1 = Submission(
                job_id=sample_job.id,
                original_filename="test1.txt",
                filename="test1.txt",
                file_type="txt",
                status="failed",
                error_message="Test error",
                retry_count=0,
            )
            submission2 = Submission(
                job_id=sample_job.id,
                original_filename="test2.txt",
                filename="test2.txt",
                file_type="txt",
                status="failed",
                error_message="Test error",
                retry_count=1,
            )

            db.session.add_all([submission1, submission2])
            db.session.commit()

            # Test retry functionality
            assert sample_job.can_retry_failed_submissions() is True

            retried_count = sample_job.retry_failed_submissions()
            assert retried_count == 2  # Both submissions can be retried (retry_count < 3)

            # Check that submission1 was reset
            db.session.refresh(submission1)
            assert submission1.status == "pending"
            assert submission1.retry_count == 1
            assert submission1.error_message is None


class TestSubmission:
    """Test cases for Submission model."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_submission(self, app, sample_job):
        """Test creating a new submission."""
        with app.app_context():
            # Ensure the job is in the current session
            db.session.add(sample_job)
            db.session.commit()

            submission = Submission(
                job_id=sample_job.id,
                original_filename="test_document.txt",
                filename="test_document.txt",
                file_type="txt",
                file_size=1024,
                status="pending",
            )

            # Add to session and commit to get default values
            db.session.add(submission)
            db.session.commit()

            assert submission.job_id == sample_job.id
            assert submission.original_filename == "test_document.txt"
            assert submission.filename == "test_document.txt"
            assert submission.file_type == "txt"
            assert submission.file_size == 1024
            assert submission.status == "pending"
            assert submission.retry_count == 0
            assert submission.error_message is None

    def test_submission_to_dict(self, sample_submission):
        """Test converting submission to dictionary."""
        submission_dict = sample_submission.to_dict()

        assert "id" in submission_dict
        assert "job_id" in submission_dict
        assert "original_filename" in submission_dict
        assert "filename" in submission_dict
        assert "file_type" in submission_dict
        assert "status" in submission_dict
        assert "created_at" in submission_dict
        assert "updated_at" in submission_dict

    def test_submission_retry_logic(self, app, sample_submission):
        """Test submission retry logic."""
        with app.app_context():
            # Ensure submission is attached to the current session
            sample_submission = db.session.merge(sample_submission)
            # Test initial state
            assert sample_submission.can_retry() is True

            # Test after 3 retries
            sample_submission.retry_count = 3
            assert sample_submission.can_retry() is False

            # Test retry method when retry_count < 3
            sample_submission.retry_count = 1
            result = sample_submission.retry()
            assert result is True
            assert sample_submission.status == "pending"
            assert sample_submission.retry_count == 2
            assert sample_submission.error_message is None

    def test_submission_status_transitions(self, app, sample_submission):
        """Test submission status transitions."""
        with app.app_context():
            # Test mark as processing
            sample_submission.mark_as_processing()
            assert sample_submission.status == "processing"
            assert sample_submission.started_at is not None

            # Test mark as completed
            sample_submission.mark_as_completed("Test grade")
            assert sample_submission.status == "completed"
            assert sample_submission.grade == "Test grade"
            assert sample_submission.completed_at is not None

            # Test mark as failed
            sample_submission.mark_as_failed("Test error")
            assert sample_submission.status == "failed"
            assert sample_submission.error_message == "Test error"


class TestJobBatch:
    """Test cases for JobBatch model."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_batch(self, app):
        """Test creating a new batch."""
        with app.app_context():
            batch = JobBatch(
                batch_name="Test Batch",
                description="A test batch",
                status="pending",
                priority=5,
            )

            # Add to session and commit to get default values
            db.session.add(batch)
            db.session.commit()

            assert batch.batch_name == "Test Batch"
            assert batch.description == "A test batch"
            assert batch.status == "pending"
            assert batch.priority == 5
            assert batch.total_jobs == 0
            assert batch.completed_jobs == 0
            assert batch.failed_jobs == 0

    def test_batch_to_dict(self, sample_batch):
        """Test converting batch to dictionary."""
        batch_dict = sample_batch.to_dict()

        assert "id" in batch_dict
        assert "batch_name" in batch_dict
        assert "description" in batch_dict
        assert "status" in batch_dict
        assert "priority" in batch_dict
        assert "created_at" in batch_dict
        assert "updated_at" in batch_dict

    def test_batch_progress_calculation(self, app, sample_batch):
        """Test batch progress calculation."""
        with app.app_context():
            # Ensure batch is attached to the current session
            sample_batch = db.session.merge(sample_batch)
            # Create jobs with different statuses
            job1 = GradingJob(
                job_name="Job 1",
                description="Test job 1",
                provider="openrouter",
                prompt="Test prompt",
                status="completed",
            )
            job2 = GradingJob(
                job_name="Job 2",
                description="Test job 2",
                provider="openrouter",
                prompt="Test prompt",
                status="failed",
            )
            job3 = GradingJob(
                job_name="Job 3",
                description="Test job 3",
                provider="openrouter",
                prompt="Test prompt",
                status="pending",
            )

            db.session.add_all([job1, job2, job3])
            db.session.commit()

            # Add jobs to batch
            sample_batch.jobs = [job1, job2, job3]
            db.session.commit()

            # Update progress
            sample_batch.update_progress()

            assert sample_batch.total_jobs == 3
            assert sample_batch.completed_jobs == 1
            assert sample_batch.failed_jobs == 1
            assert sample_batch.get_progress() == 66.67  # 2/3 * 100 (completed + failed)

    def test_add_job_to_batch(self, app, sample_batch):
        """Test adding a job to a batch."""
        with app.app_context():
            sample_batch = db.session.merge(sample_batch)

            # Create a standalone job
            job = GradingJob(
                job_name="Standalone Job",
                description="A job to be added to batch",
                provider="openrouter",
                prompt="Test prompt",
            )
            db.session.add(job)
            db.session.commit()

            # Add job to batch
            sample_batch.add_job(job)

            assert job.batch_id == sample_batch.id
            assert job in sample_batch.jobs

    def test_add_job_inherits_batch_settings(self, app):
        """Test that adding a job inherits batch settings where appropriate."""
        with app.app_context():
            # Create batch with specific settings
            batch = JobBatch(
                batch_name="Test Batch",
                provider="claude",
                prompt="Batch prompt",
                model="claude-3-sonnet",
                temperature=0.8,
                max_tokens=1500,
            )
            db.session.add(batch)
            db.session.commit()

            # Create job with minimal settings
            job = GradingJob(
                job_name="Test Job",
                description="Test description",
                provider="",  # Empty to test inheritance
                prompt="",  # Empty to test inheritance
            )
            db.session.add(job)
            db.session.commit()

            # Add job to batch
            batch.add_job(job)

            # Check that job inherited batch settings for empty fields
            assert job.provider == "claude"
            assert job.prompt == "Batch prompt"
            assert job.model == "claude-3-sonnet"
            # temperature and max_tokens inherit only if None
            # Test with values that allow inheritance

    def test_add_job_inherits_none_values(self, app):
        """Test that adding a job with None values inherits from batch."""
        with app.app_context():
            # Create batch with specific settings
            batch = JobBatch(
                batch_name="Test Batch",
                provider="claude",
                prompt="Batch prompt",
                model="claude-3-sonnet",
                temperature=0.8,
                max_tokens=1500,
            )
            db.session.add(batch)
            db.session.commit()

            # Create job with None values for temperature and max_tokens
            # We'll test this through the create_job_with_batch_settings method
            # which properly handles None values
            job = batch.create_job_with_batch_settings(
                job_name="Test Job",
                description="Test description",
                # No temperature or max_tokens specified, should inherit
            )

            # Check that job inherited all batch settings
            assert job.provider == "claude"
            assert job.prompt == "Batch prompt"
            assert job.model == "claude-3-sonnet"
            assert job.temperature == 0.8
            assert job.max_tokens == 1500

    def test_create_job_with_batch_settings(self, app):
        """Test creating a new job within a batch."""
        with app.app_context():
            # Create batch with specific settings
            batch = JobBatch(
                batch_name="Test Batch",
                provider="claude",
                prompt="Batch prompt",
                model="claude-3-sonnet",
                temperature=0.8,
                max_tokens=1500,
            )
            db.session.add(batch)
            db.session.commit()

            # Create job using batch method
            job = batch.create_job_with_batch_settings(job_name="New Job", description="Job created in batch")

            # Check that job was created with batch settings
            assert job.job_name == "New Job"
            assert job.description == "Job created in batch"
            assert job.provider == "claude"
            assert job.prompt == "Batch prompt"
            assert job.model == "claude-3-sonnet"
            assert job.temperature == 0.8
            assert job.max_tokens == 1500
            assert job.batch_id == batch.id

    def test_create_job_with_override_settings(self, app):
        """Test creating a job with settings that override batch defaults."""
        with app.app_context():
            # Create batch with specific settings
            batch = JobBatch(
                batch_name="Test Batch",
                provider="claude",
                prompt="Batch prompt",
                model="claude-3-sonnet",
                temperature=0.8,
                max_tokens=1500,
            )
            db.session.add(batch)
            db.session.commit()

            # Create job with override settings
            job = batch.create_job_with_batch_settings(
                job_name="Override Job",
                description="Job with overrides",
                provider="openrouter",
                prompt="Custom prompt",
                temperature=0.3,
            )

            # Check that overrides took precedence
            assert job.provider == "openrouter"
            assert job.prompt == "Custom prompt"
            assert job.temperature == 0.3
            # But inherited settings should still apply
            assert job.model == "claude-3-sonnet"
            assert job.max_tokens == 1500
            assert job.batch_id == batch.id

    def test_cannot_add_job_to_processing_batch(self, app):
        """Test that jobs cannot be added to a processing batch."""
        with app.app_context():
            # Create batch with processing status
            batch = JobBatch(batch_name="Processing Batch", status="processing")
            db.session.add(batch)
            db.session.commit()

            # Create a job
            job = GradingJob(job_name="Test Job", provider="openrouter", prompt="Test prompt")
            db.session.add(job)
            db.session.commit()

            # Try to add job to processing batch
            with pytest.raises(ValueError, match="Cannot add jobs to batch with status 'processing'"):
                batch.add_job(job)

    def test_cannot_create_job_in_processing_batch(self, app):
        """Test that jobs cannot be created in a processing batch."""
        with app.app_context():
            # Create batch with processing status
            batch = JobBatch(batch_name="Processing Batch", status="processing")
            db.session.add(batch)
            db.session.commit()

            # Try to create job in processing batch
            with pytest.raises(ValueError, match="Cannot create jobs in batch with status 'processing'"):
                batch.create_job_with_batch_settings(job_name="Test Job", description="This should fail")

    def test_batch_settings_summary(self, app):
        """Test getting batch settings summary."""
        with app.app_context():
            # Create batch with various settings
            batch = JobBatch(
                batch_name="Test Batch",
                provider="claude",
                prompt="Batch prompt",
                model="claude-3-sonnet",
                temperature=0.8,
                max_tokens=1500,
            )
            db.session.add(batch)
            db.session.commit()

            settings = batch.get_batch_settings_summary()

            assert settings["provider"] == "claude"
            assert settings["prompt"] == "Batch prompt"
            assert settings["model"] == "claude-3-sonnet"
            assert settings["temperature"] == 0.8
            assert settings["max_tokens"] == 1500

    def test_can_add_jobs_status_check(self, app):
        """Test can_add_jobs method for different batch statuses."""
        with app.app_context():
            # Test different statuses
            test_cases = [
                ("draft", True),
                ("pending", True),
                ("paused", True),
                ("processing", False),
                ("completed", False),
                ("failed", False),
                ("cancelled", False),
                ("archived", False),
            ]

            for status, expected in test_cases:
                batch = JobBatch(batch_name=f"Batch {status}", status=status)
                db.session.add(batch)
                db.session.commit()

                assert batch.can_add_jobs() == expected

                # Clean up for next iteration
                db.session.delete(batch)
                db.session.commit()


class TestMarkingScheme:
    """Test cases for MarkingScheme model."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_marking_scheme(self, app):
        """Test creating a new marking scheme."""
        with app.app_context():
            marking_scheme = MarkingScheme(
                name="Test Marking Scheme",
                original_filename="test_rubric.txt",
                filename="test_rubric.txt",
                file_type="txt",
                file_size=2048,
                content="Test marking scheme content",
            )

            assert marking_scheme.original_filename == "test_rubric.txt"
            assert marking_scheme.filename == "test_rubric.txt"
            assert marking_scheme.file_type == "txt"
            assert marking_scheme.file_size == 2048
            assert marking_scheme.content == "Test marking scheme content"

    def test_marking_scheme_to_dict(self, sample_marking_scheme):
        """Test converting marking scheme to dictionary."""
        scheme_dict = sample_marking_scheme.to_dict()

        assert "id" in scheme_dict
        assert "original_filename" in scheme_dict
        assert "filename" in scheme_dict
        assert "file_type" in scheme_dict
        assert "file_size" in scheme_dict
        assert "content" in scheme_dict
        assert "created_at" in scheme_dict


class TestSavedPrompt:
    """Test cases for SavedPrompt model."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_saved_prompt(self, app):
        """Test creating a new saved prompt."""
        with app.app_context():
            prompt = SavedPrompt(
                name="Test Prompt",
                description="A test prompt",
                category="essay",
                prompt_text="Please grade this essay.",
            )

            # Add to session and commit to get default values
            db.session.add(prompt)
            db.session.commit()

            assert prompt.name == "Test Prompt"
            assert prompt.description == "A test prompt"
            assert prompt.category == "essay"
            assert prompt.prompt_text == "Please grade this essay."
            assert prompt.usage_count == 0
            assert prompt.last_used is None

    def test_saved_prompt_to_dict(self, app):
        """Test converting saved prompt to dictionary."""
        with app.app_context():
            prompt = SavedPrompt(
                name="Test Prompt",
                description="A test prompt",
                category="essay",
                prompt_text="Please grade this essay.",
            )

            prompt_dict = prompt.to_dict()

            assert "id" in prompt_dict
            assert "name" in prompt_dict
            assert "description" in prompt_dict
            assert "category" in prompt_dict
            assert "prompt_text" in prompt_dict
            assert "usage_count" in prompt_dict
            assert "created_at" in prompt_dict
            assert "updated_at" in prompt_dict

    def test_increment_usage(self, app):
        """Test incrementing usage count."""
        with app.app_context():
            prompt = SavedPrompt(
                name="Test Prompt",
                description="A test prompt",
                category="essay",
                prompt_text="Please grade this essay.",
            )

            db.session.add(prompt)
            db.session.commit()

            initial_count = prompt.usage_count
            initial_last_used = prompt.last_used

            prompt.increment_usage()

            assert prompt.usage_count == initial_count + 1
            assert prompt.last_used is not None
            assert prompt.last_used > initial_last_used if initial_last_used else True


class TestSavedMarkingScheme:
    """Test cases for SavedMarkingScheme model."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_saved_marking_scheme(self, app):
        """Test creating a new saved marking scheme."""
        with app.app_context():
            scheme = SavedMarkingScheme(
                name="Test Scheme",
                description="A test marking scheme",
                category="essay",
                filename="test_scheme.txt",
                original_filename="test_scheme.txt",
                file_size=2048,
                file_type="txt",
                content="Test marking scheme content",
            )

            # Add to session and commit to get default values
            db.session.add(scheme)
            db.session.commit()

            assert scheme.name == "Test Scheme"
            assert scheme.description == "A test marking scheme"
            assert scheme.category == "essay"
            assert scheme.filename == "test_scheme.txt"
            assert scheme.original_filename == "test_scheme.txt"
            assert scheme.file_size == 2048
            assert scheme.file_type == "txt"
            assert scheme.content == "Test marking scheme content"
            assert scheme.usage_count == 0
            assert scheme.last_used is None

    def test_saved_marking_scheme_to_dict(self, app):
        """Test converting saved marking scheme to dictionary."""
        with app.app_context():
            scheme = SavedMarkingScheme(
                name="Test Scheme",
                description="A test marking scheme",
                category="essay",
                filename="test_scheme.txt",
                original_filename="test_scheme.txt",
                file_size=2048,
                file_type="txt",
                content="Test marking scheme content",
            )

            scheme_dict = scheme.to_dict()

            assert "id" in scheme_dict
            assert "name" in scheme_dict
            assert "description" in scheme_dict
            assert "category" in scheme_dict
            assert "filename" in scheme_dict
            assert "original_filename" in scheme_dict
            assert "file_size" in scheme_dict
            assert "file_type" in scheme_dict
            assert "content" in scheme_dict
            assert "usage_count" in scheme_dict
            assert "created_at" in scheme_dict
            assert "updated_at" in scheme_dict
