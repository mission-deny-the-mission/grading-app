import os
import json
import requests
from celery import Celery
from flask import Flask
from dotenv import load_dotenv

from utils.llm_providers import get_llm_provider, grade_with_openrouter, grade_with_claude, grade_with_lm_studio
from models import db, GradingJob, Submission, MarkingScheme, SavedMarkingScheme, JobBatch, BatchTemplate
from utils.text_extraction import extract_text_from_docx, extract_text_from_pdf, extract_text_by_file_type
from utils.file_utils import cleanup_file

anthropic = None # Keep for compatibility, though not directly used now

# Load environment variables from .env file
load_dotenv()

# Create Flask app for Celery
def create_app():
    """Return the main Flask app to share DB/session/config with web routes and tests."""
    # Import here to avoid circular import at module load time
    import sys
    import os
    
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
            app_path = os.path.join(current_dir, 'app.py')
            spec = importlib.util.spec_from_file_location("app", app_path)
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)
            flask_app = app_module.app
    return flask_app

# Initialize Celery
celery_app = Celery('grading_tasks')
celery_app.config_from_object('celeryconfig')









# Remove the global variable to track processing job
# _currently_processing_job = None  <-- Remove this line

@celery_app.task(bind=True)
def process_job(self, job_id):
    """Process all submissions in a job."""
    app = create_app()
    with app.app_context():
        try:
            # Remove the global lock check and retry logic
            # if _currently_processing_job is not None and _currently_processing_job != job_id:
            #     print(f"Job {job_id} is waiting - job {_currently_processing_job} is currently being processed")
            #     self.retry(countdown=30, max_retries=10)
            #     return False
            #
            # _currently_processing_job = job_id  <-- Remove this
            
            job = db.session.get(GradingJob, job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")
            
            print(f"Starting to process job: {job.job_name} (ID: {job_id})")
            
            # Update job status when processing begins
            job.status = 'processing'
            db.session.commit()
            
            # Process each submission sequentially
            pending_submissions = [s for s in job.submissions if s.status == 'pending']
            
            if not pending_submissions:
                job.update_progress()
                return True
            
            for submission in pending_submissions:
                print(f"Processing submission: {submission.original_filename}")
                result = process_submission_sync(submission.id)
                if not result:
                    print(f"Failed to process submission: {submission.original_filename}")
            
            job.update_progress()
            
            if job.batch_id:
                batch = db.session.get(JobBatch, job.batch_id)
                if batch:
                    batch.update_progress()
            
            print(f"Completed processing job: {job.job_name} (ID: {job_id})")
            return True
        
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            job = db.session.get(GradingJob, job_id)
            if job:
                job.status = 'failed'
                db.session.commit()
            return False


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
        submission.set_status('pending')
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
            job.status = 'processing'
            db.session.commit()
            
            # Process each submission sequentially
            pending_submissions = [s for s in job.submissions if s.status == 'pending']
            
            if not pending_submissions:
                # No pending submissions, check if job should be completed
                job.update_progress()
                return True
            
            # Process submissions one by one (not in parallel)
            for submission in pending_submissions:
                print(f"Processing submission: {submission.original_filename}")
                result = process_submission_sync(submission.id)
                if not result:
                    print(f"Failed to process submission: {submission.original_filename}")
            
            # Update job progress after all submissions are processed
            job.update_progress()
            
            # Update batch progress if job belongs to a batch
            if job.batch_id:
                batch = db.session.get(JobBatch, job.batch_id)
                if batch:
                    batch.update_progress()
            
            print(f"Completed processing job: {job.job_name} (ID: {job_id})")
            return True
            
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            job = db.session.get(GradingJob, job_id)
            if job:
                job.status = 'failed'
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
                raise Exception(f"Submission {submission_id} not found")
            
            # Update status to processing
            submission.set_status('processing')

            # Grade the document
            job = submission.job


            # Validate provider early so tests expecting provider errors don't fail due to missing file
            supported_providers = {'openrouter', 'claude', 'lm_studio', 'ollama', 'OpenRouter', 'Claude', 'LM Studio', 'Ollama'}
            if job.provider not in supported_providers:
                submission.set_status('failed', f'Unsupported provider: {job.provider}. Supported providers are: {", ".join(supported_providers)}')
                return False

            # Extract text from file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], submission.filename)

            if not os.path.exists(file_path):
                submission.set_status('failed', 'File not found on disk')
                return False
            
            # Extract text based on file type
            text = extract_text_by_file_type(file_path, submission.file_type)
            
            if text.startswith('Error reading'):
                submission.set_status('failed', text)
                return False
            
            # Store extracted text
            submission.extracted_text = text
            
            # Determine which models to use
            models_to_grade = []
            if job.models_to_compare:
                models_to_grade = job.models_to_compare
            else:
                # Fallback to single model (backward compatibility)
                if job.provider == 'OpenRouter':
                    models_to_grade = [job.model if job.model else "anthropic/claude-3-5-sonnet-20241022"]
                else:
                    models_to_grade = [job.model if job.model else "default"]
            
            all_successful = True
            successful_results = []
            
            # Get marking scheme content if available
            marking_scheme_content = None
            
            # Manually load saved marking scheme if ID is provided
            if job.saved_marking_scheme_id:
                saved_scheme = db.session.get(SavedMarkingScheme, job.saved_marking_scheme_id)
                if saved_scheme:
                    marking_scheme_content = saved_scheme.content
            elif job.marking_scheme_id:
                # Manually load uploaded marking scheme if ID is provided
                uploaded_scheme = db.session.get(MarkingScheme, job.marking_scheme_id)
                if uploaded_scheme:
                    marking_scheme_content = uploaded_scheme.content
            
            # Grade with each model using the new provider system
            for model in models_to_grade:
                try:
                    # Get the LLM provider instance (map provider name)
                    provider_mapping = {
                        'openrouter': 'OpenRouter',
                        'claude': 'Claude',
                        'lm_studio': 'LM Studio', 
                        'ollama': 'Ollama'
                    }
                    provider_name = provider_mapping.get(job.provider, job.provider)
                    llm_provider = get_llm_provider(provider_name)
                    
                    # For OpenRouter and Ollama, pass the model parameter
                    if job.provider.lower() in ['openrouter', 'ollama']:
                        result = llm_provider.grade_document(
                            text, job.prompt, model, marking_scheme_content, 
                            job.temperature, job.max_tokens
                        )
                    else:
                        # For Claude and LM Studio, model is handled internally
                        result = llm_provider.grade_document(
                            text, job.prompt, marking_scheme_content, 
                            job.temperature, job.max_tokens
                        )
                except ValueError as e:
                    # Provider not found
                    submission.set_status('failed', f'Unsupported provider: {job.provider}. Error: {str(e)}')
                    return False
                except Exception as e:
                    # Other errors during grading
                    submission.set_status('failed', f'Grading error: {str(e)}')
                    return False
                
                # Store individual grade result
                if result['success']:
                    submission.add_grade_result(
                        grade=result['grade'],
                        provider=result.get('provider', job.provider or 'OpenRouter'),
                        model=result.get('model', model),
                        status='completed',
                        metadata={
                            'provider': result.get('provider', job.provider or 'OpenRouter'),
                            'model': result.get('model', model),
                            'usage': result.get('usage')
                        }
                    )

                    successful_results.append(result)
                else:
                    submission.add_grade_result(
                        grade='',
                        provider=result.get('provider', job.provider or 'OpenRouter'),
                        model=result.get('model', model),
                        status='failed',
                        error_message=result['error'],
                        metadata={'error': result['error']}
                    )
                    all_successful = False
                    last_error_message = result['error']
            
            # Store legacy results for backward compatibility
            if successful_results:
                # Use the first successful result as the primary grade
                primary_result = successful_results[0]
                submission.grade = primary_result['grade']
                submission.grade_metadata = {
                    'provider': primary_result.get('provider', job.provider or 'OpenRouter'),
                    'model': primary_result.get('model', models_to_grade[0] if models_to_grade else 'default'),
                    'usage': primary_result.get('usage'),
                    'total_models': len(models_to_grade),
                    'successful_models': len(successful_results)
                }
                submission.set_status('completed')
                
                # Clean up file only on successful completion
                cleanup_file(file_path)
                # Return True to indicate successful completion
                return True
            else:
                # Use the last error message from model grading if available
                try:
                    submission.set_status('failed', last_error_message)
                except Exception:
                    submission.set_status('failed', 'All models failed to grade the document')
                # Don't clean up file on failure - keep it for retry
                return False
                
        except Exception as e:
            # Update submission status
            submission = db.session.get(Submission, submission_id)
            if submission:
                submission.set_status('failed', str(e))
            return False


@celery_app.task(bind=True)
def process_batch(self, batch_id, priority_override=None):
    """Process all jobs in a batch with intelligent scheduling."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise Exception(f"Batch {batch_id} not found")
            
            print(f"Starting to process batch: {batch.batch_name} (ID: {batch_id})")
            
            # Check if batch can be started
            if not batch.can_start():
                print(f"Batch {batch_id} cannot be started. Status: {batch.status}")
                return False
            
            # Start the batch
            batch.start_batch()
            
            # Get pending jobs sorted by priority
            pending_jobs = [job for job in batch.jobs if job.status == 'pending']
            
            if not pending_jobs:
                print(f"No pending jobs in batch {batch_id}")
                batch.update_progress()
                return True
            
            # Sort jobs by priority (higher priority first)
            pending_jobs.sort(key=lambda x: x.priority, reverse=True)
            
            print(f"Queuing {len(pending_jobs)} jobs for processing")
            
            # Queue jobs for processing with staggered delays for better resource management
            for i, job in enumerate(pending_jobs):
                # Add small delay between job starts to prevent overwhelming the system
                delay = i * 5  # 5 second intervals
                process_job.apply_async(args=[job.id], countdown=delay)
                print(f"Queued job {job.job_name} with {delay}s delay")
            
            return True
            
        except Exception as e:
            print(f"Error processing batch {batch_id}: {str(e)}")
            batch = db.session.get(JobBatch, batch_id)
            if batch:
                batch.status = 'failed'
                db.session.commit()
            return False


@celery_app.task
def process_batch_with_priority():
    """Process batches in priority order."""
    app = create_app()
    with app.app_context():
        try:
            # Get all pending batches sorted by priority
            pending_batches = JobBatch.query.filter_by(status='pending').order_by(JobBatch.priority.desc()).all()
            
            for batch in pending_batches:
                if batch.can_start():
                    print(f"Auto-starting high priority batch: {batch.batch_name}")
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
                raise Exception(f"Batch {batch_id} not found")
            
            retried_count = batch.retry_failed_jobs()
            
            if retried_count > 0:
                # Start processing the batch again
                process_batch.delay(batch_id)
                print(f"Retried {retried_count} failed jobs in batch {batch.batch_name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error retrying batch {batch_id}: {str(e)}")
            return 0


@celery_app.task
def pause_batch_processing(batch_id):
    """Pause batch processing."""
    app = create_app()
    with app.app_context():
        try:
            batch = db.session.get(JobBatch, batch_id)
            if not batch:
                raise Exception(f"Batch {batch_id} not found")
            
            if batch.pause_batch():
                print(f"Paused batch: {batch.batch_name}")
                return True
            else:
                print(f"Could not pause batch: {batch.batch_name} (status: {batch.status})")
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
                raise Exception(f"Batch {batch_id} not found")
            
            if batch.resume_batch():
                print(f"Resumed batch: {batch.batch_name}")
                return True
            else:
                print(f"Could not resume batch: {batch.batch_name} (status: {batch.status})")
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
                raise Exception(f"Batch {batch_id} not found")
            
            if batch.cancel_batch():
                print(f"Cancelled batch: {batch.batch_name}")
                return True
            else:
                print(f"Could not cancel batch: {batch.batch_name} (status: {batch.status})")
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
    from datetime import datetime, timedelta, timezone
    
    app = create_app()
    with app.app_context():
        try:
            # Archive batches completed more than 30 days ago
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            old_batches = JobBatch.query.filter(
                JobBatch.status == 'completed',
                JobBatch.completed_at < cutoff_date
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
    import glob
    from datetime import datetime, timedelta, timezone
    
    app = create_app()
    with app.app_context():
        upload_folder = app.config['UPLOAD_FOLDER']
        cutoff_time = datetime.now() - timedelta(hours=72)  # Keep files for 72 hours (3 days)
        
        # Find files older than 72 hours
        for file_path in glob.glob(os.path.join(upload_folder, '*')):
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff_time:
                    # Check if this file is associated with any failed submissions
                    filename = os.path.basename(file_path)
                    submission = Submission.query.filter_by(filename=filename).first()
                    
                    # Only delete if no failed submissions are using this file
                    if not submission or submission.status != 'failed':
                        try:
                            os.remove(file_path)
                        except:
                            pass  # Don't fail if cleanup fails

