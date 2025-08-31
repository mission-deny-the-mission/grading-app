import glob
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from celery import Celery
from dotenv import load_dotenv

from models import (
    GradingJob,
    JobBatch,
    MarkingScheme,
    SavedMarkingScheme,
    Submission,
    db,
)
from utils.file_utils import cleanup_file
from utils.llm_providers import get_llm_provider, provider_semaphore
from utils.text_extraction import extract_text_by_file_type

anthropic = None  # Keep for compatibility, though not directly used now

# Load environment variables from .env file
load_dotenv()


# Create Flask app for Celery
def create_app():
    """Return the main Flask app to share DB/session/config with web routes and tests."""
    # Import here to avoid circular import at module load time
    import os
    import sys

    # Add the current directory to Python path if not already there
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        from .app import app as flask_app
    except ImportError:
        try:
            from app import app as flask_app
        except ImportError:
            # Last resort: try importing with explicit path manipulation
            import importlib.util

            app_path = os.path.join(current_dir, "app.py")
            spec = importlib.util.spec_from_file_location("app", app_path)
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)
            flask_app = app_module.app
    return flask_app


# Initialize Celery
celery_app = Celery("grading_tasks")
celery_app.config_from_object("celeryconfig")


@celery_app.task(bind=True)
def process_job(self, job_id):
    """Process all submissions in a job."""
    app = create_app()
    with app.app_context():
        try:
            job = db.session.get(GradingJob, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            print(f"Starting to process job: {job.job_name} (ID: {job_id})")

            # Update job status when processing begins
            job.status = "processing"
            db.session.commit()

            # Process each submission sequentially
            pending_submissions = [s for s in job.submissions if s.status == "pending"]

            if not pending_submissions:
                job.update_progress()
                return True

            # Determine number of worker threads to use
            max_workers = _get_max_workers(job)
            workers = max(1, min(max_workers, len(pending_submissions)))
            print(
                f"Processing {len(pending_submissions)} submissions using {workers} worker(s)"
            )

            _process_submissions_parallel(pending_submissions, workers)

            job.update_progress()

            if job.batch_id:
                batch = db.session.get(JobBatch, job.batch_id)
                if batch:
                    batch.update_progress()

            print(f"Completed processing job: {job.job_name} (ID: {job_id})")
            return True

        except ValueError as e:
            print(f"Validation error processing job {job_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            job = db.session.get(GradingJob, job_id)
            if job:
                job.status = "failed"
                db.session.commit()
            return False


def _get_max_workers(job):
    """Get maximum number of workers for a job."""
    try:
        max_workers = int(os.getenv("JOB_MAX_PARALLEL", "4"))
    except ValueError:
        max_workers = 4

    # Allow batch-level override if provided
    if job.batch and getattr(job.batch, "batch_settings", None):
        bs = job.batch.batch_settings
        if isinstance(bs, dict) and "job_parallelism" in bs:
            max_workers = int(bs.get("job_parallelism") or max_workers)

    return max_workers


def _process_submissions_parallel(pending_submissions, workers):
    """Process submissions in parallel using ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(process_submission_sync, s.id): s
            for s in pending_submissions
        }
        for fut in as_completed(future_map):
            submission_obj = future_map[fut]
            try:
                result = fut.result()
                if not result:
                    failure_reason = (
                        submission_obj.error_message
                        if hasattr(submission_obj, "error_message")
                        else None
                    )
                    if failure_reason:
                        print(
                            f"Failed to process submission: {submission_obj.original_filename} | Reason: {failure_reason}"
                        )
                    else:
                        print(
                            f"Failed to process submission: {submission_obj.original_filename}"
                        )
            except Exception as e:
                print(
                    f"Unhandled exception processing submission {submission_obj.original_filename}: {e}"
                )


@celery_app.task(bind=True)
def retry_submission_task(self, submission_id):
    """
    Task to retry a single submission.
    Resets status to 'pending' and re-triggers job processing.
    """
    app = create_app()
    with app.app_context():
        submission = db.session.get(Submission, submission_id)
        if not submission:
            print(f"Retry task: Submission {submission_id} not found.")
            return

        job_id = submission.job_id
        submission.set_status("pending")
        db.session.commit()

        # Re-trigger the main job processing task
        process_job.delay(job_id)


def process_job_sync(job_id):
    """Process all submissions in a job synchronously (for testing)."""
    app = create_app()
    with app.app_context():
        try:
            job = db.session.get(GradingJob, job_id)
            if not job:
                return False

            print(f"Starting to process job: {job.job_name} (ID: {job_id})")

            # Update job status
            job.status = "processing"
            db.session.commit()

            # Process each submission sequentially
            pending_submissions = [s for s in job.submissions if s.status == "pending"]

            if not pending_submissions:
                # No pending submissions, check if job should be completed
                job.update_progress()
                return True

            # Process submissions in parallel
            max_workers = _get_max_workers(job)
            workers = max(1, min(max_workers, len(pending_submissions)))
            print(
                f"Processing {len(pending_submissions)} submissions "
                f"using {workers} worker(s)"
            )

            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(process_submission_sync, s.id): s
                    for s in pending_submissions
                }
                for fut in as_completed(future_map):
                    submission_obj = future_map[fut]
                    try:
                        result = fut.result()
                        if not result:
                            failure_reason = (
                                submission_obj.error_message
                                if hasattr(submission_obj, "error_message")
                                else None
                            )
                            if failure_reason:
                                print(
                                    f"Failed to process submission: "
                                    f"{submission_obj.original_filename} | "
                                    f"Reason: {failure_reason}"
                                )
                            else:
                                print(
                                    f"Failed to process submission: "
                                    f"{submission_obj.original_filename}"
                                )
                    except Exception as e:
                        print(
                            f"Unhandled exception processing submission "
                            f"{submission_obj.original_filename}: {e}"
                        )

            # Update job progress after all submissions are processed
            job.update_progress()

            # Update batch progress if job belongs to a batch
            if job.batch_id:
                batch = db.session.get(JobBatch, job.batch_id)
                if batch:
                    batch.update_progress()

            print(f"Completed processing job: {job.job_name} (ID: {job_id})")
            return True

        except ValueError as e:
            print(f"Validation error processing job {job_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            job = db.session.get(GradingJob, job_id)
            if job:
                job.status = "failed"
                db.session.commit()
            return False


def process_submission_sync(submission_id):
    """Process a single submission synchronously (without Celery)."""
    app = create_app()
    with app.app_context():
        try:
            # Get submission from database
            submission = db.session.get(Submission, submission_id)
            if not submission:
                raise ValueError(f"Submission {submission_id} not found")

            # Update status to processing
            submission.set_status("processing")

            # Grade the document
            job = submission.job

            # Validate provider early
            if not _is_provider_supported(job.provider):
                error_msg = (
                    f"Unsupported provider: {job.provider}. "
                    f'Supported providers are: {", ".join(_get_supported_providers())}'
                )
                submission.set_status("failed", error_msg)
                return False

            # Extract text from file
            file_path = _get_submission_file_path(app, submission)
            if not file_path:
                submission.set_status("failed", "File not found on disk")
                return False

            # Extract text based on file type
            text = extract_text_by_file_type(file_path, submission.file_type)
            if text.startswith("Error reading"):
                submission.set_status("failed", text)
                return False

            # Store extracted text
            submission.extracted_text = text

            # Determine which models to use
            models_to_grade = _get_models_to_grade(job)
            successful_results = []

            # Get marking scheme content if available
            marking_scheme_content = _get_marking_scheme_content(job)

            # Grade with each model
            for model in models_to_grade:
                result = _grade_with_model(
                    submission, job, model, marking_scheme_content
                )
                if result["success"]:
                    _store_successful_grade(submission, job, result, model)
                    successful_results.append(result)
                else:
                    _store_failed_grade(submission, job, result, model)

            # Store legacy results for backward compatibility
            if successful_results:
                _store_legacy_results(
                    submission, job, successful_results, models_to_grade
                )
                submission.set_status("completed")
                cleanup_file(file_path)
                return True
            else:
                # Use the last error message from model grading if available
                last_error = _get_last_error_message()
                submission.set_status("failed", last_error)
                return False

        except ValueError as e:
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.set_status("failed", str(e))
            return False
        except Exception as e:
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.set_status("failed", str(e))
            return False


def _is_provider_supported(provider):
    """Check if provider is supported."""
    supported_providers = _get_supported_providers()
    return provider in supported_providers


def _get_supported_providers():
    """Get list of supported providers."""
    return {
        "openrouter",
        "claude",
        "lm_studio",
        "ollama",
        "gemini",
        "openai",
        "OpenRouter",
        "Claude",
        "LM Studio",
        "Ollama",
        "Gemini",
        "OpenAI",
    }


def _get_submission_file_path(app, submission):
    """Get file path for submission."""
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], submission.filename)
    return file_path if os.path.exists(file_path) else None


def _get_models_to_grade(job):
    """Determine which models to use for grading."""
    if job.models_to_compare:
        return job.models_to_compare

    # Fallback to single model (backward compatibility)
    provider_name = (job.provider or "").lower()
    provider_defaults = {
        "openrouter": "anthropic/claude-3-5-sonnet-20241022",
        "claude": "claude-3-5-sonnet-20241022",
        "lm_studio": "local-model",
        "ollama": "llama2",
        "gemini": "gemini-2.5-pro",
        "openai": "gpt-5",
    }
    default_model = provider_defaults.get(
        provider_name, provider_defaults["openrouter"]
    )
    return [job.model if job.model else default_model]


def _get_marking_scheme_content(job):
    """Get marking scheme content if available."""
    if job.saved_marking_scheme_id:
        saved_scheme = db.session.get(SavedMarkingScheme, job.saved_marking_scheme_id)
        if saved_scheme:
            return saved_scheme.content
    elif job.marking_scheme_id:
        uploaded_scheme = db.session.get(MarkingScheme, job.marking_scheme_id)
        if uploaded_scheme:
            return uploaded_scheme.content
    return None


def _grade_with_model(submission, job, model, marking_scheme_content):
    """Grade submission with a specific model."""
    try:
        provider_mapping = {
            "openrouter": "OpenRouter",
            "claude": "Claude",
            "lm_studio": "LM Studio",
            "ollama": "Ollama",
            "gemini": "Gemini",
            "openai": "OpenAI",
        }
        provider_name = provider_mapping.get(job.provider, job.provider)
        llm_provider = get_llm_provider(provider_name)

        with provider_semaphore(provider_name):
            if job.provider.lower() in ["openrouter", "ollama", "gemini", "openai"]:
                return llm_provider.grade_document(
                    text=submission.extracted_text,
                    prompt=job.prompt,
                    model=model,
                    marking_scheme=marking_scheme_content,
                    temperature=job.temperature,
                    max_tokens=job.max_tokens,
                )
            else:
                return llm_provider.grade_document(
                    text=submission.extracted_text,
                    prompt=job.prompt,
                    marking_scheme=marking_scheme_content,
                    temperature=job.temperature,
                    max_tokens=job.max_tokens,
                )
    except TimeoutError as te:
        return {"success": False, "error": f"Grading timeout: {str(te)}"}
    except ValueError as e:
        return {
            "success": False,
            "error": f"Unsupported provider: {job.provider}. Error: {str(e)}",
        }
    except Exception as e:
        return {"success": False, "error": f"Grading error: {str(e)}"}


def _store_successful_grade(submission, job, result, model):
    """Store successful grade result."""
    result_model = result.get("model", model)
    if result_model is None:
        result_model = "unknown-model"

    submission.add_grade_result(
        grade=result["grade"],
        provider=result.get("provider", job.provider or "OpenRouter"),
        model=result_model,
        status="completed",
        metadata={
            "provider": result.get("provider", job.provider or "OpenRouter"),
            "model": result_model,
            "usage": result.get("usage"),
        },
    )


def _store_failed_grade(submission, job, result, model):
    """Store failed grade result."""
    result_model = result.get("model", model)
    if result_model is None:
        result_model = "unknown-model"

    submission.add_grade_result(
        grade="",
        provider=result.get("provider", job.provider or "OpenRouter"),
        model=result_model,
        status="failed",
        error_message=result["error"],
        metadata={"error": result["error"]},
    )


def _store_legacy_results(submission, job, successful_results, models_to_grade):
    """Store legacy results for backward compatibility."""
    primary_result = successful_results[0]
    submission.grade = primary_result["grade"]
    submission.grade_metadata = {
        "provider": primary_result.get("provider", job.provider or "OpenRouter"),
        "model": primary_result.get(
            "model", models_to_grade[0] if models_to_grade else "default"
        ),
        "usage": primary_result.get("usage"),
        "total_models": len(models_to_grade),
        "successful_models": len(successful_results),
    }


def _get_last_error_message():
    """Get the last error message from model grading."""
    # This would need to be implemented with proper error tracking
    return "All models failed to grade the document"


@celery_app.task
def process_batch(batch_id):
    """Process all jobs in a batch with intelligent scheduling."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            print(f"Starting to process batch: {batch.batch_name} " f"(ID: {batch_id})")

            # Check if batch can be started
            if not batch.can_start():
                print(f"Batch {batch_id} cannot be started. " f"Status: {batch.status}")
                return False

            # Start the batch
            batch.start_batch()

            # Get pending jobs sorted by priority
            pending_jobs = [job for job in batch.jobs if job.status == "pending"]

            if not pending_jobs:
                print(f"No pending jobs in batch {batch_id}")
                batch.update_progress()
                return True

            # Sort jobs by priority (higher priority first)
            pending_jobs.sort(key=lambda x: x.priority, reverse=True)

            print(f"Queuing {len(pending_jobs)} jobs for processing")

            # Queue jobs for processing with staggered delays
            for i, job in enumerate(pending_jobs):
                # Add small delay between job starts
                delay = i * 5  # 5 second intervals
                process_job.apply_async(args=[job.id], countdown=delay)
                print(f"Queued job {job.job_name} with {delay}s delay")

            return True

        except ValueError as e:
            print(f"Validation error processing batch {batch_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error processing batch {batch_id}: {str(e)}")
            batch = db.session.get(JobBatch, batch_id)
            if batch:
                batch.status = "failed"
                db.session.commit()
            return False


@celery_app.task
def process_batch_with_priority():
    """Process batches in priority order."""
    app = create_app()
    with app.app_context():
        try:
            # Get all pending batches sorted by priority
            pending_batches = (
                JobBatch.query.filter_by(status="pending")
                .order_by(JobBatch.priority.desc())
                .all()
            )

            for batch in pending_batches:
                if batch.can_start():
                    print(f"Auto-starting high priority batch: " f"{batch.batch_name}")
                    process_batch.delay(batch.id)

        except Exception as e:
            print(f"Error in priority batch processing: {str(e)}")


@celery_app.task
def retry_batch_failed_jobs(batch_id):
    """Retry all failed jobs in a batch."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            retried_count = batch.retry_failed_jobs()

            if retried_count > 0:
                # Start processing the batch again
                process_batch.delay(batch_id)
                print(
                    f"Retried {retried_count} failed jobs in batch "
                    f"{batch.batch_name}"
                )
                return True

            return False

        except ValueError as e:
            print(f"Validation error retrying batch {batch_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error retrying batch {batch_id}: {str(e)}")
            return False


@celery_app.task
def pause_batch_processing(batch_id):
    """Pause batch processing."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            if batch.pause_batch():
                print(f"Paused batch: {batch.batch_name}")
                return True
            else:
                print(
                    f"Could not pause batch: {batch.batch_name} "
                    f"(status: {batch.status})"
                )
                return False

        except ValueError as e:
            print(f"Validation error pausing batch {batch_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error pausing batch {batch_id}: {str(e)}")
            return False


@celery_app.task
def resume_batch_processing(batch_id):
    """Resume batch processing."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            if batch.resume_batch():
                print(f"Resumed batch: {batch.batch_name}")
                return True
            else:
                print(
                    f"Could not resume batch: {batch.batch_name} "
                    f"(status: {batch.status})"
                )
                return False

        except ValueError as e:
            print(f"Validation error resuming batch {batch_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error resuming batch {batch_id}: {str(e)}")
            return False


@celery_app.task
def cancel_batch_processing(batch_id):
    """Cancel batch processing."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            if batch.cancel_batch():
                print(f"Cancelled batch: {batch.batch_name}")
                return True
            else:
                print(
                    f"Could not cancel batch: {batch.batch_name} "
                    f"(status: {batch.status})"
                )
                return False

        except ValueError as e:
            print(f"Validation error cancelling batch {batch_id}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error cancelling batch {batch_id}: {str(e)}")
            return False


@celery_app.task
def update_batch_progress(batch_id):
    """Update batch progress and status."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                return False

            batch.update_progress()
            return True

        except Exception as e:
            print(f"Error updating batch progress {batch_id}: {str(e)}")
            return False


@celery_app.task
def cleanup_completed_batches():
    """Archive old completed batches."""
    app = create_app()
    with app.app_context():
        try:
            # Archive batches completed more than 30 days ago
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

            old_batches = JobBatch.query.filter(
                JobBatch.status == "completed", JobBatch.completed_at < cutoff_date
            ).all()

            archived_count = 0
            for batch in old_batches:
                batch.archive()
                archived_count += 1

            print(f"Archived {archived_count} old batches")
            return archived_count

        except Exception as e:
            print(f"Error in batch cleanup: {str(e)}")
            return 0


@celery_app.task
def cleanup_old_files():
    """Clean up old uploaded files."""
    app = create_app()
    with app.app_context():
        upload_folder = app.config["UPLOAD_FOLDER"]
        cutoff_time = datetime.now() - timedelta(hours=72)

        # Find files older than 72 hours
        for file_path in glob.glob(os.path.join(upload_folder, "*")):
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff_time:
                    # Check if this file is associated with any failed
                    # submissions
                    filename = os.path.basename(file_path)
                    submission = Submission.query.filter_by(filename=filename).first()

                    # Only delete if no failed submissions are using this file
                    if not submission or submission.status != "failed":
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass  # Don't fail if cleanup fails
