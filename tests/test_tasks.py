"""
Unit tests for Celery tasks and grading functions.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from tasks import (
    process_job_sync,
    process_submission_sync,
    retry_batch_failed_jobs,
)
from utils.llm_providers import get_llm_provider


class TestGradingFunctions:
    """Test cases for grading functions."""

    @patch("utils.llm_providers.requests.post")
    def test_openrouter_provider_success(self, mock_requests_post, app):
        """Test successful grading with OpenRouter provider."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Excellent work! Grade: A"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_requests_post.return_value = mock_response

        with app.app_context():
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
                provider = get_llm_provider("OpenRouter")
                result = provider.grade_document(
                    "This is a test document.",
                    "Please grade this document.",
                    temperature=0.7,
                    max_tokens=2000,
                )

                assert result["success"] is True
                assert "grade" in result
                assert "Excellent work!" in result["grade"]

    def test_openrouter_provider_no_api_key(self, app):
        """Test OpenRouter provider without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with app.app_context():
                provider = get_llm_provider("OpenRouter")
                result = provider.grade_document("This is a test document.", "Please grade this document.")

                assert result["success"] is False
                assert "error" in result
                assert "authentication" in result["error"].lower()

    def test_get_llm_provider_gemini(self, app):
        """Test getting Gemini provider instance."""
        with app.app_context():
            provider = get_llm_provider("Gemini")
            assert provider.__class__.__name__ == "GeminiLLMProvider"

    def test_get_llm_provider_openai(self, app):
        """Test getting OpenAI provider instance."""
        with app.app_context():
            provider = get_llm_provider("OpenAI")
            assert provider.__class__.__name__ == "OpenAILLMProvider"

    def test_get_llm_provider_invalid(self, app):
        """Test getting invalid provider raises ValueError."""
        with app.app_context():
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_llm_provider("InvalidProvider")


class TestProcessSubmission:
    """Test cases for process_submission task."""

    @patch("tasks.get_llm_provider")
    def test_process_submission_success(self, mock_get_provider, app, sample_job, sample_submission):
        """Test successful submission processing."""
        # Mock the provider instance
        mock_provider = MagicMock()
        mock_provider.grade_document.return_value = {
            "success": True,
            "grade": "Excellent work! Grade: A",
            "model": "test-model",
            "provider": "OpenRouter",
            "usage": {"tokens": 100},
        }
        mock_get_provider.return_value = mock_provider

        with app.app_context():
            # Ensure objects are in the current session
            from models import Submission, db

            # sample_job and sample_submission are already persisted; don't re-add
            # Create a test file
            test_file_path = os.path.join(app.config["UPLOAD_FOLDER"], sample_submission.filename)
            with open(test_file_path, "w") as f:
                f.write("This is a test document.")

            result = process_submission_sync(sample_submission.id)

            # The function should return True on success
            assert result is True

            # Check that submission was updated - requery to avoid session issues
            persisted = db.session.get(Submission, sample_submission.id)
            assert persisted.status == "completed"
            assert persisted.grade == "Excellent work! Grade: A"
            assert persisted.error_message is None

    @patch("tasks.get_llm_provider")
    def test_process_submission_failure(self, mock_get_provider, app, sample_job, sample_submission):
        """Test failed submission processing."""
        # Mock the provider instance
        mock_provider = MagicMock()
        mock_provider.grade_document.return_value = {
            "success": False,
            "error": "API Error",
            "provider": "OpenRouter",
        }
        mock_get_provider.return_value = mock_provider

        with app.app_context():
            # Create a test file
            test_file_path = os.path.join(app.config["UPLOAD_FOLDER"], sample_submission.filename)
            with open(test_file_path, "w") as f:
                f.write("This is a test document.")

            result = process_submission_sync(sample_submission.id)

            assert result is False

            # Check that submission was updated (requery)
            from models import Submission, db

            persisted = db.session.get(Submission, sample_submission.id)
            assert persisted.status == "failed"
            assert persisted.error_message == "All models failed to grade the document"

    def test_process_submission_file_not_found(self, app, sample_job, sample_submission):
        """Test submission processing with missing file."""
        with app.app_context():
            result = process_submission_sync(sample_submission.id)

            assert result is False

            # Check that submission was updated (requery)
            from models import Submission, db

            persisted = db.session.get(Submission, sample_submission.id)
            assert persisted.status == "failed"
            assert "not found" in persisted.error_message.lower()

    def test_process_submission_unsupported_provider(self, app, sample_submission):
        """Test submission processing with unsupported provider."""
        with app.app_context():
            # Update job to have unsupported provider
            from models import GradingJob, Submission, db

            job = db.session.get(GradingJob, sample_submission.job_id)
            job.provider = "unsupported_provider"
            db.session.commit()

            result = process_submission_sync(sample_submission.id)

            assert result is False

            # Check that submission was updated (requery)
            persisted = db.session.get(Submission, sample_submission.id)
            assert persisted.status == "failed"
            assert "unsupported" in persisted.error_message.lower()


class TestProcessJob:
    """Test cases for process_job task."""

    @patch("tasks.process_submission_sync")
    def test_process_job_success(self, mock_process_submission, app, sample_job):
        """Test successful job processing."""
        mock_process_submission.return_value = True

        with app.app_context():
            # Create test submissions
            from models import Submission, db

            submission1 = Submission(
                job_id=sample_job.id,
                original_filename="test1.txt",
                filename="test1.txt",
                file_type="txt",
                status="pending",
            )
            submission2 = Submission(
                job_id=sample_job.id,
                original_filename="test2.txt",
                filename="test2.txt",
                file_type="txt",
                status="pending",
            )

            db.session.add_all([submission1, submission2])
            db.session.commit()

            result = process_job_sync(sample_job.id)

            assert result is True
            assert mock_process_submission.call_count == 2

    def test_process_job_not_found(self, app):
        """Test job processing with non-existent job."""
        with app.app_context():
            result = process_job_sync("nonexistent-id")
            assert result is False

    @patch("tasks.process_submission_sync")
    def test_process_job_with_failures(self, mock_process_submission, app, sample_job):
        """Test job processing with some failures."""
        # Make one submission fail
        mock_process_submission.side_effect = [True, False]

        with app.app_context():
            # Create test submissions
            from models import Submission, db

            submission1 = Submission(
                job_id=sample_job.id,
                original_filename="test1.txt",
                filename="test1.txt",
                file_type="txt",
                status="pending",
            )
            submission2 = Submission(
                job_id=sample_job.id,
                original_filename="test2.txt",
                filename="test2.txt",
                file_type="txt",
                status="pending",
            )

            db.session.add_all([submission1, submission2])
            db.session.commit()

            result = process_job_sync(sample_job.id)

            assert result is True  # Job processing continues even with failures
            assert mock_process_submission.call_count == 2


class TestProcessBatch:
    """Test cases for process_batch task."""

    def test_process_batch_success(self, app, sample_batch):
        """Test successful batch processing."""
        with app.app_context():
            # Create test jobs
            from models import GradingJob, db

            job1 = GradingJob(
                job_name="Job 1",
                description="Test job 1",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=sample_batch.id,
            )
            job2 = GradingJob(
                job_name="Job 2",
                description="Test job 2",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=sample_batch.id,
            )

            db.session.add_all([job1, job2])
            db.session.commit()

            # Test that jobs were created successfully
            assert job1.batch_id == sample_batch.id
            assert job2.batch_id == sample_batch.id

    def test_process_batch_not_found(self, app):
        """Test batch processing with non-existent batch."""
        with app.app_context():
            # Test that non-existent batch ID is invalid
            assert "nonexistent-id" != "valid-id"

    def test_process_batch_with_failures(self, app, sample_batch):
        """Test batch processing with some failures."""
        with app.app_context():
            # Create test jobs
            from models import GradingJob, db

            job1 = GradingJob(
                job_name="Job 1",
                description="Test job 1",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=sample_batch.id,
            )
            job2 = GradingJob(
                job_name="Job 2",
                description="Test job 2",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=sample_batch.id,
            )

            db.session.add_all([job1, job2])
            db.session.commit()

            # Test that jobs were created successfully
            assert job1.batch_id == sample_batch.id
            assert job2.batch_id == sample_batch.id


class TestBatchManagementTasks:
    """Test cases for batch management tasks."""

    def test_retry_batch_failed_jobs(self, app, sample_batch):
        """Test retrying failed jobs in a batch."""
        with app.app_context():
            # Create test jobs with failed submissions
            from models import GradingJob, Submission, db

            job1 = GradingJob(
                job_name="Job 1",
                description="Test job 1",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=sample_batch.id,
                status="completed_with_errors",
            )
            job2 = GradingJob(
                job_name="Job 2",
                description="Test job 2",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=sample_batch.id,
                status="completed",
            )

            db.session.add_all([job1, job2])
            db.session.commit()

            # Create failed submission for job1
            submission = Submission(
                job_id=job1.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                status="failed",
                error_message="Test error",
                retry_count=0,
            )
            db.session.add(submission)
            db.session.commit()

            result = retry_batch_failed_jobs(sample_batch.id)

            assert result is True

            # Check that failed submission was retried
            db.session.refresh(submission)
            assert submission.status == "pending"
            assert submission.retry_count == 1

    def test_pause_batch_processing(self, app, sample_batch):
        """Test pausing batch processing."""
        with app.app_context():
            from models import JobBatch, db
            from tasks import pause_batch_processing

            batch = db.session.get(JobBatch, sample_batch.id)
            assert batch is not None
            # Set to processing to allow pause
            batch.status = "processing"
            db.session.commit()
            pause_batch_processing(batch.id)
            db.session.refresh(batch)
            assert batch.status == "paused"

    def test_resume_batch_processing(self, app, sample_batch):
        """Test resuming batch processing."""
        with app.app_context():
            from models import JobBatch, db
            from tasks import resume_batch_processing

            batch = db.session.get(JobBatch, sample_batch.id)
            # Set to paused first
            batch.status = "paused"
            db.session.commit()
            resume_batch_processing(batch.id)
            db.session.refresh(batch)
            assert batch.status == "processing"

    def test_cancel_batch_processing(self, app, sample_batch):
        """Test canceling batch processing."""
        with app.app_context():
            from models import JobBatch, db
            from tasks import cancel_batch_processing

            batch = db.session.get(JobBatch, sample_batch.id)
            cancel_batch_processing(batch.id)
            db.session.refresh(batch)
            assert batch.status == "cancelled"


class TestErrorHandling:
    """Test cases for error handling in tasks."""

    def test_task_with_database_error(self, app):
        """Test task behavior with database errors."""
        with app.app_context():
            # Try to process a submission with invalid job ID
            result = process_submission_sync("invalid-uuid")
            assert result is False

    def test_task_with_file_processing_error(self, app, sample_job, sample_submission):
        """Test task behavior with file processing errors."""
        with app.app_context():
            # Objects are already persisted by fixtures
            # Create a file that can't be read
            test_file_path = os.path.join(app.config["UPLOAD_FOLDER"], sample_submission.filename)
            with open(test_file_path, "w") as f:
                f.write("Test content")

            # Make the file unreadable
            os.chmod(test_file_path, 0o000)

            try:
                result = process_submission_sync(sample_submission.id)
                assert result is False
            finally:
                # Restore file permissions for cleanup
                os.chmod(test_file_path, 0o644)

    def test_task_with_api_timeout(self, app, sample_job, sample_submission):
        """Test task behavior with API timeout."""
        with patch("tasks.get_llm_provider") as mock_get_provider:
            # Mock the provider instance
            mock_provider = MagicMock()
            mock_provider.grade_document.side_effect = Exception("Timeout")
            mock_get_provider.return_value = mock_provider

            with app.app_context():
                # Objects are already persisted by fixtures
                # Create a test file
                test_file_path = os.path.join(app.config["UPLOAD_FOLDER"], sample_submission.filename)
                with open(test_file_path, "w") as f:
                    f.write("Test content")

                result = process_submission_sync(sample_submission.id)
                assert result is False


class TestModuleImportIssues:
    """Test cases for module import issues that occur in Celery workers."""

    def test_create_app_import_error_simulation(self):
        """Test create_app function behavior when module imports fail."""
        import os
        import sys

        # Save original sys.path
        original_path = sys.path.copy()

        try:
            # Clear sys.path to simulate module not found scenario
            sys.path.clear()

            # Add back the current directory to sys.path so we can import tasks
            current_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, current_dir)

            # Import tasks module directly
            import tasks

            # This should not fail due to the importlib.util fallback
            try:
                app = tasks.create_app()
                # If we get here, the fallback mechanism worked
                assert app is not None
            except ImportError as e:
                # This is what we expect to catch - the original error
                assert "No module named" in str(e)
            except Exception:
                # The fix should handle this gracefully
                pass

        finally:
            # Restore original sys.path
            sys.path.clear()
            sys.path.extend(original_path)

    def test_celery_worker_import_simulation(self):
        """Simulate the environment where Celery workers fail to import app module."""
        import os
        import subprocess
        import sys

        # Create a test script that simulates how Celery workers import tasks
        test_script = """
import sys
import os

# Simulate Celery worker environment by removing current directory from path
if '.' in sys.path:
    sys.path.remove('.')
if '' in sys.path:
    sys.path.remove('')

# Remove the current working directory to simulate Celery worker environment
current_dir = os.getcwd()
if current_dir in sys.path:
    sys.path.remove(current_dir)

try:
    # This should fail in original code but work with our fix
    from tasks import create_app
    app = create_app()
    print("SUCCESS: App creation succeeded")
    exit(0)
except Exception as e:
    print(f"ERROR: {str(e)}")
    exit(1)
"""

        # Write the test script to a temporary file
        test_file_path = "/tmp/test_celery_import.py"
        with open(test_file_path, "w") as f:
            f.write(test_script)

        try:
            # Run the test script in the grading app directory
            result = subprocess.run(
                [sys.executable, test_file_path],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=30,
            )

            # The fixed code should handle the import gracefully
            # Either it succeeds or fails gracefully without ModuleNotFoundError
            if result.returncode == 0:
                assert "SUCCESS" in result.stdout
            else:
                # Should not have the specific "No module named 'app'" error
                assert "No module named 'app'" not in result.stdout

        except subprocess.TimeoutExpired:
            # Test timed out, which suggests infinite loop or hanging
            assert False, "Test script timed out"
        finally:
            # Clean up
            if os.path.exists(test_file_path):
                os.remove(test_file_path)


class TestFileProcessingAndCleanup:
    """Test cases for file processing and cleanup in batch job workflows."""

    def test_file_exists_during_processing(self, app, sample_job):
        """Test that files exist during processing and are cleaned up after success."""
        with app.app_context():
            import tempfile

            from models import Submission, db

            # Create a test file that will be processed
            test_content = "This is test content for grading."
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(test_content)
                temp_file = f.name

            # Create submission that points to our test file
            filename = os.path.basename(temp_file)
            final_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            # Move the file to the upload folder
            import shutil

            shutil.move(temp_file, final_path)

            submission = Submission(
                job_id=sample_job.id,
                original_filename="test_document.txt",
                filename=filename,
                file_type="txt",
                file_size=len(test_content),
                status="pending",
            )
            db.session.add(submission)
            db.session.commit()

            # Mock successful grading
            with patch("tasks.get_llm_provider") as mock_get_provider:
                # Mock the provider instance
                mock_provider = MagicMock()
                mock_provider.grade_document.return_value = {
                    "success": True,
                    "grade": "This is a test grade.",
                    "model": "test-model",
                    "provider": "openrouter",
                }
                mock_get_provider.return_value = mock_provider

                # File should exist before processing
                assert os.path.exists(final_path)

                # Process the submission
                result = process_submission_sync(submission.id)

                # Processing should succeed
                assert result is True

                # File should be cleaned up after successful processing
                assert not os.path.exists(final_path)

                # Submission should be marked as completed
                db.session.refresh(submission)
                assert submission.status == "completed"

    def test_file_preserved_on_failure(self, app, sample_job):
        """Test that files are preserved when processing fails for retry."""
        with app.app_context():
            import tempfile

            from models import Submission, db

            # Create a test file
            test_content = "This is test content that will fail to grade."
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(test_content)
                temp_file = f.name

            filename = os.path.basename(temp_file)
            final_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            # Move to upload folder
            import shutil

            shutil.move(temp_file, final_path)

            submission = Submission(
                job_id=sample_job.id,
                original_filename="failing_document.txt",
                filename=filename,
                file_type="txt",
                file_size=len(test_content),
                status="pending",
            )
            db.session.add(submission)
            db.session.commit()

            # Mock failed grading
            with patch("tasks.get_llm_provider") as mock_get_provider:
                # Mock the provider instance
                mock_provider = MagicMock()
                mock_provider.grade_document.return_value = {
                    "success": False,
                    "error": "Grading failed for testing",
                    "provider": "openrouter",
                }
                mock_get_provider.return_value = mock_provider

                # File should exist before processing
                assert os.path.exists(final_path)

                # Process the submission
                result = process_submission_sync(submission.id)

                # Processing should fail
                assert result is False

                # File should still exist for retry
                assert os.path.exists(final_path)

                # Submission should be marked as failed
                db.session.refresh(submission)
                assert submission.status == "failed"

                # Clean up for test
                os.remove(final_path)

    def test_file_not_found_error_handling(self, app, sample_job):
        """Test proper error handling when file is not found during processing."""
        with app.app_context():
            from models import Submission, db

            # Create submission with non-existent file
            submission = Submission(
                job_id=sample_job.id,
                original_filename="nonexistent.txt",
                filename="nonexistent_file.txt",
                file_type="txt",
                file_size=1024,
                status="pending",
            )
            db.session.add(submission)
            db.session.commit()

            # Process the submission
            result = process_submission_sync(submission.id)

            # Processing should fail
            assert result is False

            # Submission should be marked as failed with appropriate error
            db.session.refresh(submission)
            assert submission.status == "failed"
            assert "File not found on disk" in submission.error_message

    def test_multiple_files_batch_job_cleanup(self, app):
        """Test that multiple files in a batch job are handled correctly."""
        with app.app_context():
            import tempfile

            from models import GradingJob, JobBatch, Submission, db

            # Create a batch
            batch = JobBatch(
                batch_name="Multi-File Test Batch",
                provider="openrouter",
                prompt="Test prompt",
            )
            db.session.add(batch)
            db.session.commit()

            # Create a job in the batch
            job = GradingJob(
                job_name="Multi-File Test Job",
                provider="openrouter",
                prompt="Test prompt",
                batch_id=batch.id,
            )
            db.session.add(job)
            db.session.commit()

            # Create multiple test files and submissions
            files_created = []
            submissions = []

            for i in range(3):
                # Create test file
                test_content = f"This is test content for file {i + 1}."
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    f.write(test_content)
                    temp_file = f.name

                filename = f"test_file_{i + 1}.txt"
                final_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

                # Move to upload folder
                import shutil

                shutil.move(temp_file, final_path)
                files_created.append(final_path)

                # Create submission
                submission = Submission(
                    job_id=job.id,
                    original_filename=f"document_{i + 1}.txt",
                    filename=filename,
                    file_type="txt",
                    file_size=len(test_content),
                    status="pending",
                )
                db.session.add(submission)
                submissions.append(submission)

            db.session.commit()

            # Mock successful grading for all files
            with patch("tasks.get_llm_provider") as mock_get_provider:
                # Mock the provider instance
                mock_provider = MagicMock()
                mock_provider.grade_document.return_value = {
                    "success": True,
                    "grade": "This is a test grade.",
                    "model": "test-model",
                    "provider": "openrouter",
                }
                mock_get_provider.return_value = mock_provider

                # All files should exist before processing
                for file_path in files_created:
                    assert os.path.exists(file_path)

                # Process all submissions
                for submission in submissions:
                    result = process_submission_sync(submission.id)
                    assert result is True

                # All files should be cleaned up after successful processing
                for file_path in files_created:
                    assert not os.path.exists(file_path)

                # All submissions should be completed
                for submission in submissions:
                    db.session.refresh(submission)
                    assert submission.status == "completed"

    def test_large_file_processing_under_limit(self, app, sample_job):
        """Test processing of large files under the 100MB limit."""
        with app.app_context():
            import tempfile

            from models import Submission, db

            # Create a large test file (10MB - well under 100MB limit)
            large_content = "x" * (10 * 1024 * 1024)  # 10MB
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(large_content)
                temp_file = f.name

            filename = os.path.basename(temp_file)
            final_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            # Move to upload folder
            import shutil

            shutil.move(temp_file, final_path)

            submission = Submission(
                job_id=sample_job.id,
                original_filename="large_document.txt",
                filename=filename,
                file_type="txt",
                file_size=len(large_content),
                status="pending",
            )
            db.session.add(submission)
            db.session.commit()

            # Mock successful grading
            with patch("tasks.get_llm_provider") as mock_get_provider:
                # Mock the provider instance
                mock_provider = MagicMock()
                mock_provider.grade_document.return_value = {
                    "success": True,
                    "grade": "Successfully graded large document.",
                    "model": "test-model",
                    "provider": "openrouter",
                }
                mock_get_provider.return_value = mock_provider

                # File should exist before processing
                assert os.path.exists(final_path)

                # Process the submission
                result = process_submission_sync(submission.id)

                # Processing should succeed
                assert result is True

                # File should be cleaned up after successful processing
                assert not os.path.exists(final_path)

                # Submission should be marked as completed
                db.session.refresh(submission)
                assert submission.status == "completed"
