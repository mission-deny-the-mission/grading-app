import os
import json
import requests
from celery import Celery
from docx import Document
import PyPDF2
import openai
from anthropic import Anthropic
from flask import Flask
from dotenv import load_dotenv
from models import db, GradingJob, Submission, MarkingScheme, SavedMarkingScheme

# Load environment variables from .env file
load_dotenv()

# Create Flask app for Celery
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    db.init_app(app)
    return app

# Initialize Celery
celery_app = Celery('grading_tasks')
celery_app.config_from_object('celeryconfig')

# API configurations
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')

# Initialize API clients
if OPENROUTER_API_KEY:
    openai.api_key = OPENROUTER_API_KEY
    openai.api_base = "https://openrouter.ai/api/v1"

anthropic = None
if CLAUDE_API_KEY:
    try:
        anthropic = Anthropic(api_key=CLAUDE_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Anthropic client: {e}")
        anthropic = None

def extract_text_from_docx(file_path):
    """Extract text from a Word document."""
    try:
        doc = Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        extracted_text = '\n'.join(text)
        
        if not extracted_text.strip():
            return "Error reading Word document: Document appears to be empty or contains no readable text."
        
        return extracted_text
    except Exception as e:
        return f"Error reading Word document: {str(e)}"

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            if len(pdf_reader.pages) == 0:
                return "Error reading PDF: Document appears to be empty or corrupted."
            
            text = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            
            extracted_text = '\n'.join(text)
            
            if not extracted_text.strip():
                return "Error reading PDF: Document appears to be empty or contains no readable text."
            
            return extracted_text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def grade_with_openrouter(text, prompt, model="anthropic/claude-3-5-sonnet-20241022", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Grade document using OpenRouter API."""
    try:
        # Configure OpenAI for OpenRouter
        openai.api_key = OPENROUTER_API_KEY
        openai.api_base = "https://openrouter.ai/api/v1"

        # Prepare the grading prompt with marking scheme if provided
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
            'grade': response.choices[0].message.content,
            'model': model,
            'provider': 'OpenRouter',
            'usage': response.usage
        }
    except openai.error.AuthenticationError:
        return {
            'success': False,
            'error': "OpenRouter API authentication failed. Please check your API key.",
            'provider': 'OpenRouter'
        }
    except openai.error.RateLimitError:
        return {
            'success': False,
            'error': "OpenRouter API rate limit exceeded. Please try again later.",
            'provider': 'OpenRouter'
        }
    except openai.error.APIError as e:
        return {
            'success': False,
            'error': f"OpenRouter API error: {str(e)}",
            'provider': 'OpenRouter'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error with OpenRouter API: {str(e)}",
            'provider': 'OpenRouter'
        }

def grade_with_claude(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Grade document using Claude API."""
    if not anthropic:
        return {
            'success': False,
            'error': "Claude API not configured or failed to initialize",
            'provider': 'Claude'
        }

    try:
        # Prepare the grading prompt with marking scheme if provided
        if marking_scheme_content:
            enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
        else:
            enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
            messages=[
                {
                    "role": "user",
                    "content": enhanced_prompt
                }
            ]
        )
        
        return {
            'success': True,
            'grade': response.content[0].text,
            'model': 'claude-3-5-sonnet-20241022',
            'provider': 'Claude',
            'usage': response.usage.dict() if response.usage else None
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
    """Grade document using LM Studio API."""
    try:
        # Prepare the grading prompt with marking scheme if provided
        if marking_scheme_content:
            enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
        else:
            enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

        response = requests.post(
            f"{LM_STUDIO_URL}/chat/completions",
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
            'error': f"Could not connect to LM Studio at {LM_STUDIO_URL}. Please check if LM Studio is running.",
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



# Global variable to track if a job is currently being processed
_currently_processing_job = None

@celery_app.task(bind=True)
def process_job(self, job_id):
    """Process all submissions in a job. Only one job can be processed at a time."""
    global _currently_processing_job
    
    app = create_app()
    with app.app_context():
        try:
            # Check if another job is currently being processed
            if _currently_processing_job is not None and _currently_processing_job != job_id:
                print(f"Job {job_id} is waiting - job {_currently_processing_job} is currently being processed")
                # Retry this task in 30 seconds
                self.retry(countdown=30, max_retries=10)
                return False
            
            # Set this job as the currently processing job
            _currently_processing_job = job_id
            
            job = GradingJob.query.get(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")
            
            print(f"Starting to process job: {job.job_name} (ID: {job_id})")
            
            # Update job status
            job.status = 'processing'
            db.session.commit()
            
            # Process each submission sequentially
            pending_submissions = [s for s in job.submissions if s.status == 'pending']
            
            if not pending_submissions:
                # No pending submissions, check if job should be completed
                job.update_progress()
                _currently_processing_job = None
                return True
            
            # Process submissions one by one (not in parallel)
            for submission in pending_submissions:
                print(f"Processing submission: {submission.original_filename}")
                result = process_submission_sync(submission.id)
                if not result:
                    print(f"Failed to process submission: {submission.original_filename}")
            
            # Update job progress after all submissions are processed
            job.update_progress()
            
            print(f"Completed processing job: {job.job_name} (ID: {job_id})")
            _currently_processing_job = None
            return True
            
        except Exception as e:
            print(f"Error processing job {job_id}: {str(e)}")
            job = GradingJob.query.get(job_id)
            if job:
                job.status = 'failed'
                db.session.commit()
            _currently_processing_job = None
            return False

def process_submission_sync(submission_id):
    """Process a single submission synchronously (without Celery)."""
    app = create_app()
    with app.app_context():
        try:
            # Get submission from database
            submission = Submission.query.get(submission_id)
            if not submission:
                raise Exception(f"Submission {submission_id} not found")
            
            # Update status to processing
            submission.set_status('processing')
            
            # Extract text from file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], submission.filename)
            
            if not os.path.exists(file_path):
                submission.set_status('failed', 'File not found on disk')
                return False
            
            # Extract text based on file type
            if submission.file_type == 'docx':
                text = extract_text_from_docx(file_path)
            elif submission.file_type == 'pdf':
                text = extract_text_from_pdf(file_path)
            elif submission.file_type == 'txt':
                # Read text file directly
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except Exception as e:
                    submission.set_status('failed', f'Error reading text file: {str(e)}')
                    return False
            else:
                submission.set_status('failed', 'Unsupported file type')
                return False
            
            if text.startswith('Error reading'):
                submission.set_status('failed', text)
                return False
            
            # Store extracted text
            submission.extracted_text = text
            
            # Grade the document
            job = submission.job
            
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
                saved_scheme = SavedMarkingScheme.query.get(job.saved_marking_scheme_id)
                if saved_scheme:
                    marking_scheme_content = saved_scheme.content
            elif job.marking_scheme_id:
                # Manually load uploaded marking scheme if ID is provided
                uploaded_scheme = MarkingScheme.query.get(job.marking_scheme_id)
                if uploaded_scheme:
                    marking_scheme_content = uploaded_scheme.content
            
            # Grade with each model
            for model in models_to_grade:
                # Check if provider is properly configured
                if job.provider == 'openrouter':
                    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'sk-or-your-key-here':
                        submission.set_status('failed', 'OpenRouter API key not configured. Please configure your API key in the settings.')
                        return False
                    result = grade_with_openrouter(text, job.prompt, model, marking_scheme_content, job.temperature, job.max_tokens)
                elif job.provider == 'claude':
                    if not CLAUDE_API_KEY or CLAUDE_API_KEY == 'sk-ant-your-key-here':
                        submission.set_status('failed', 'Claude API key not configured. Please configure your API key in the settings.')
                        return False
                    if not anthropic:
                        submission.set_status('failed', 'Claude API client failed to initialize. Please check your API key configuration.')
                        return False
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
                        provider=result['provider'],
                        model=result['model'],
                        status='completed',
                        metadata={
                            'provider': result['provider'],
                            'model': result['model'],
                            'usage': result.get('usage')
                        }
                    )
                    successful_results.append(result)
                else:
                    submission.add_grade_result(
                        grade='',
                        provider=result['provider'],
                        model=model,
                        status='failed',
                        error_message=result['error'],
                        metadata={'error': result['error']}
                    )
                    all_successful = False
            
            # Store legacy results for backward compatibility
            if successful_results:
                # Use the first successful result as the primary grade
                primary_result = successful_results[0]
                submission.grade = primary_result['grade']
                submission.grade_metadata = {
                    'provider': primary_result['provider'],
                    'model': primary_result['model'],
                    'usage': primary_result.get('usage'),
                    'total_models': len(models_to_grade),
                    'successful_models': len(successful_results)
                }
                submission.set_status('completed')
                
                # Clean up file only on successful completion
                try:
                    os.remove(file_path)
                except:
                    pass  # Don't fail if file cleanup fails
                    
                return True
            else:
                submission.set_status('failed', 'All models failed to grade the document')
                # Don't clean up file on failure - keep it for retry
                return False
                
        except Exception as e:
            # Update submission status
            submission = Submission.query.get(submission_id)
            if submission:
                submission.set_status('failed', str(e))
            return False

@celery_app.task(bind=True)
def process_batch(self, batch_id):
    """Process all jobs in a batch."""
    app = create_app()
    with app.app_context():
        try:
            from models import JobBatch
            batch = JobBatch.query.get(batch_id)
            if not batch:
                raise Exception(f"Batch {batch_id} not found")
            
            # Update batch status
            batch.status = 'processing'
            db.session.commit()
            
            # Process each job
            for job in batch.jobs:
                if job.status == 'pending':
                    process_job.delay(job.id)
            
            return True
            
        except Exception as e:
            batch = JobBatch.query.get(batch_id)
            if batch:
                batch.status = 'failed'
                db.session.commit()
            return False

@celery_app.task
def cleanup_old_files():
    """Clean up old uploaded files."""
    import glob
    from datetime import datetime, timedelta
    
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


