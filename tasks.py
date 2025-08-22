import os
import json
import requests
from celery import Celery
from flask import Flask
from dotenv import load_dotenv

# Add module-level LLM client imports so tests can patch tasks.openai and tasks.anthropic
import openai
from anthropic import Anthropic

from models import db, GradingJob, Submission, MarkingScheme, SavedMarkingScheme, JobBatch, BatchTemplate
from utils.llm_providers import grade_with_openrouter, grade_with_claude, grade_with_lm_studio
from utils.text_extraction import extract_text_from_docx, extract_text_from_pdf, extract_text_by_file_type
from utils.file_utils import cleanup_file

# Ensure a module-level anthropic variable exists for tests to patch
anthropic = None

# Provide local wrapper functions so tests can patch module-level clients (tasks.openai/tasks.anthropic)
def grade_with_openrouter(text, prompt, model="anthropic/claude-3-5-sonnet-20241022", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Wrapper to grade via OpenRouter using module-level openai so tests can patch tasks.openai."""
    try:
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if not openrouter_key:
            return {
                'success': False,
                'error': "OpenRouter API authentication failed. Please check your API key configuration.",
                'provider': 'OpenRouter'
            }
        # Configure module-level openai
        openai.api_key = openrouter_key
        openai.api_base = "https://openrouter.ai/api/v1"

        if marking_scheme_content:
            enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
        else:
            enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria."},
                {"role": "user", "content": enhanced_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            'success': True,
            'grade': getattr(response.choices[0].message, 'content', None) or str(response.choices[0]),
            'model': model,
            'provider': 'OpenRouter',
            'usage': getattr(response, 'usage', None)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"OpenRouter API error: {str(e)}",
            'provider': 'OpenRouter'
        }

def grade_with_claude(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Wrapper to grade via Claude using module-level anthropic so tests can patch tasks.anthropic."""
    claude_key = os.getenv('CLAUDE_API_KEY')
    if not claude_key:
        return {
            'success': False,
            'error': "Claude API not configured or failed to initialize",
            'provider': 'Claude'
        }

    # Use the module-level anthropic if available (tests patch this), else create a client
    client = anthropic if anthropic is not None else None
    if client is None:
        try:
            client = Anthropic(api_key=claude_key)
        except Exception:
            return {
                'success': False,
                'error': "Claude API not configured or failed to initialize",
                'provider': 'Claude'
            }

    try:
        if marking_scheme_content:
            enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
        else:
            enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
            messages=[{"role": "user", "content": enhanced_prompt}]
        )

        # Some clients return content differently; normalize
        grade_text = None
        if hasattr(response, 'content') and getattr(response, 'content'):
            # response.content may be a list-like
            try:
                grade_text = response.content[0].text
            except Exception:
                grade_text = str(response.content)
        elif hasattr(response, 'text'):
            grade_text = response.text
        else:
            grade_text = str(response)

        usage = None
        if hasattr(response, 'usage'):
            try:
                usage = response.usage.dict() if hasattr(response.usage, 'dict') else response.usage
            except Exception:
                usage = response.usage

        return {
            'success': True,
            'grade': grade_text,
            'model': 'claude-3-5-sonnet-20241022',
            'provider': 'Claude',
            'usage': usage
        }
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            return {
                'success': False,
                'error': "Claude API authentication failed. Please check your API key.",
                'provider': 'Claude'
            }
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            return {
                'success': False,
                'error': "Claude API rate limit exceeded. Please try again later.",
                'provider': 'Claude'
            }
        elif "timeout" in error_msg.lower():
            return {
                'success': False,
                'error': "Claude API request timed out. Please try again.",
                'provider': 'Claude'
            }
        else:
            return {
                'success': False,
                'error': f"Claude API error: {error_msg}",
                'provider': 'Claude'
            }

def grade_with_lm_studio(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Wrapper for LM Studio that uses module-level requests so tests can patch tasks.requests."""
    lm_studio_url = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')

    try:
        if marking_scheme_content:
            enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
        else:
            enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

        response = requests.post(
            f"{lm_studio_url}/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'grade': result['choices'][0]['message']['content'],
                'model': 'local-model',
                'provider': 'LM Studio',
                'usage': result.get('usage')
            }
        elif response.status_code == 404:
            return {
                'success': False,
                'error': "LM Studio endpoint not found. Please check if LM Studio is running and the URL is correct.",
                'provider': 'LM Studio'
            }
        elif response.status_code == 500:
            return {
                'success': False,
                'error': "LM Studio internal server error. Please check LM Studio logs.",
                'provider': 'LM Studio'
            }
        else:
            return {
                'success': False,
                'error': f"LM Studio API error: {response.status_code} - {response.text}",
                'provider': 'LM Studio'
            }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': f"Could not connect to LM Studio at {lm_studio_url}. Please check if LM Studio is running.",
            'provider': 'LM Studio'
        }
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': "LM Studio request timed out. Please try again.",
            'provider': 'LM Studio'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"LM Studio API error: {str(e)}",
            'provider': 'LM Studio'
        }


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
            try:
                print(f"DBG: UPLOAD_FOLDER={app.config.get('UPLOAD_FOLDER')}, filename={submission.filename}")
                print(f"DBG: Job provider before validation: {getattr(job, 'provider', None)}")
            except Exception:
                pass

            # Validate provider early so tests expecting provider errors don't fail due to missing file
            supported_providers = {'openrouter', 'claude', 'lm_studio'}
            if job.provider not in supported_providers:
                submission.set_status('failed', f'Unsupported provider: {job.provider}. Supported providers are: openrouter, claude, lm_studio')
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
                if job.provider == 'openrouter':
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
            
            # Grade with each model
            for model in models_to_grade:
                # Check if provider is properly configured
                if job.provider == 'openrouter':
                    # Allow grading path to proceed in tests because grade function is mocked
                    result = grade_with_openrouter(text, job.prompt, model, marking_scheme_content, job.temperature, job.max_tokens)
                elif job.provider == 'claude':
                    # Allow grading path; function handles env checks
                    result = grade_with_claude(text, job.prompt, marking_scheme_content, job.temperature, job.max_tokens)
                elif job.provider == 'lm_studio':
                    result = grade_with_lm_studio(text, job.prompt, marking_scheme_content, job.temperature, job.max_tokens)
                else:
                    submission.set_status('failed', f'Unsupported provider: {job.provider}. Supported providers are: openrouter, claude, lm_studio')
                    return False
                
                # Store individual grade result
                if result['success']:
                    submission.add_grade_result(
                        grade=result['grade'],
                        provider=result.get('provider', job.provider or 'openrouter'),
                        model=result.get('model', model),
                        status='completed',
                        metadata={
                            'provider': result.get('provider', job.provider or 'openrouter'),
                            'model': result.get('model', model),
                            'usage': result.get('usage')
                        }
                    )
                    try:
                        print("DBG: Grading success path executed")
                    except Exception:
                        pass
                    successful_results.append(result)
                else:
                    submission.add_grade_result(
                        grade='',
                        provider=result.get('provider', job.provider or 'openrouter'),
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
                    'provider': primary_result.get('provider', job.provider or 'openrouter'),
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
            
            return retried_count
            
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


