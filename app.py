import os
import json
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge, NotFound
import openai
from anthropic import Anthropic
from docx import Document
import PyPDF2
import io
from dotenv import load_dotenv
from models import db, GradingJob, Submission, JobBatch, MarkingScheme, SavedPrompt, SavedMarkingScheme, BatchTemplate
from tasks import (process_job, process_batch, retry_batch_failed_jobs, pause_batch_processing,
                   resume_batch_processing, cancel_batch_processing, update_batch_progress)
from datetime import datetime, timezone

load_dotenv()

app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API configurations
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')

DEFAULT_MODELS = {
    'openrouter': {
        'default': 'anthropic/claude-sonnet-4',
        'popular': [
            'anthropic/claude-opus-4.1',
            'openai/gpt-5-chat',
            'openai/gpt-5-mini',
            'openai/gpt-oss-120b',
            'openai/gpt-oss-20b:free',
            'qwen/qwen3-235b-a22b-thinking-2507',
            'qwen/qwen3-30b-a3b:free',
            'mistralai/mistral-large',
            'deepseek/deepseek-r1-0528'
        ]
    },
    'claude': {
        'default': 'claude-3-5-sonnet-20241022',
        'popular': [
            'claude-3-5-sonnet-20241022',
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307'
        ]
    },
    'lm_studio': {
        'default': 'local-model',
        'popular': [
            'local-model',
            'google/gemma-3-27b',
            'qwen/qwen3-4b-thinking-2507',
            'deepseek/deepseek-r1-0528-qwen3-8b'
        ]
    }
}

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
        return '\n'.join(text)
    except Exception as e:
        return f"Error reading Word document: {str(e)}"

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = []
            for page in pdf_reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_marking_scheme_content(file_path, file_type):
    """Extract content from marking scheme file."""
    try:
        if file_type == 'docx':
            return extract_text_from_docx(file_path)
        elif file_type == 'pdf':
            return extract_text_from_pdf(file_path)
        elif file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"Unsupported file type: {file_type}"
    except Exception as e:
        return f"Error reading marking scheme file: {str(e)}"

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
            'provider': 'OpenRouter'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"OpenRouter API error: {str(e)}",
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
            'provider': 'Claude'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Claude API error: {str(e)}",
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
                'provider': 'LM Studio'
            }
        else:
            return {
                'success': False,
                'error': f"LM Studio API error: {response.status_code} - {response.text}",
                'provider': 'LM Studio'
            }
    except Exception as e:
        return {
            'success': False,
            'error': f"LM Studio API error: {str(e)}",
            'provider': 'LM Studio'
        }

@app.route('/')
def index():
    """Main page with upload form and configuration."""
    default_prompt = session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
    return render_template('index.html', default_prompt=default_prompt)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and grading."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Handle marking scheme upload if provided
    marking_scheme_content = None
    if 'marking_scheme' in request.files and request.files['marking_scheme'].filename != '':
        marking_scheme_file = request.files['marking_scheme']
        marking_scheme_filename = secure_filename(marking_scheme_file.filename)
        marking_scheme_path = os.path.join(app.config['UPLOAD_FOLDER'], marking_scheme_filename)
        marking_scheme_file.save(marking_scheme_path)

        # Determine marking scheme file type
        if marking_scheme_filename.lower().endswith('.docx'):
            marking_scheme_type = 'docx'
        elif marking_scheme_filename.lower().endswith('.pdf'):
            marking_scheme_type = 'pdf'
        elif marking_scheme_filename.lower().endswith('.txt'):
            marking_scheme_type = 'txt'
        else:
            return jsonify({'error': 'Unsupported marking scheme file type. Please upload .docx, .pdf, or .txt files.'}), 400

        # Extract marking scheme content
        marking_scheme_content = extract_marking_scheme_content(marking_scheme_path, marking_scheme_type)

        # Clean up marking scheme file
        try:
            os.remove(marking_scheme_path)
        except:
            pass

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extract text based on file type
        if filename.lower().endswith('.docx'):
            text = extract_text_from_docx(file_path)
        elif filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif filename.lower().endswith('.txt'):
            # Read text file directly
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                return jsonify({'error': f'Error reading text file: {str(e)}'}), 400
        else:
            return jsonify({'error': 'Unsupported file type. Please upload .docx, .pdf, or .txt files.'}), 400

        # Get grading parameters
        prompt = request.form.get('prompt', session.get('default_prompt', 'Please grade this document and provide detailed feedback.'))
        provider = request.form.get('provider', 'openrouter')
        custom_model = request.form.get('customModel', '').strip()
        models_to_compare = request.form.getlist('models_to_compare[]')  # Get list of models to compare
        custom_models = request.form.getlist('customModels[]')  # Get list of custom models

        # Get model parameters
        temperature = float(request.form.get('temperature', '0.3'))
        max_tokens = int(request.form.get('max_tokens', '2000'))

        # Add custom models to the comparison list
        if custom_models:
            models_to_compare.extend([m.strip() for m in custom_models if m.strip()])

        # If no specific models selected, use default behavior
        if not models_to_compare:
            if custom_model:
                models_to_compare = [custom_model]
            else:
                # Use default model for the provider
                default_model = DEFAULT_MODELS.get(provider, {}).get('default', 'anthropic/claude-3-5-sonnet-20241022')
                models_to_compare = [default_model]

        results = []
        all_successful = True

        # Grade with each selected model
        for model in models_to_compare:
            if provider == 'openrouter':
                if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'sk-or-your-key-here':
                    return jsonify({'error': 'OpenRouter API key not configured. Please configure your API key in the settings.'}), 400
                result = grade_with_openrouter(text, prompt, model, marking_scheme_content, temperature, max_tokens)
            elif provider == 'claude':
                if not CLAUDE_API_KEY or CLAUDE_API_KEY == 'sk-ant-your-key-here':
                    return jsonify({'error': 'Claude API key not configured. Please configure your API key in the settings.'}), 400
                if not anthropic:
                    return jsonify({'error': 'Claude API client failed to initialize. Please check your API key configuration.'}), 400
                result = grade_with_claude(text, prompt, marking_scheme_content, temperature, max_tokens)
            elif provider == 'lm_studio':
                result = grade_with_lm_studio(text, prompt, marking_scheme_content, temperature, max_tokens)
            else:
                return jsonify({'error': f'Unsupported provider: {provider}. Supported providers are: openrouter, claude, lm_studio'}), 400

            results.append(result)
            if not result.get('success', False):
                all_successful = False

        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass  # Don't fail if file cleanup fails

        # Return results
        if len(results) == 1:
            # Single result - return in original format for backward compatibility
            result = results[0]
            if not result.get('success', False):
                return jsonify({'error': result.get('error', 'Unknown error occurred during grading')}), 500
            return jsonify(result)
        else:
            # Multiple results - return comparison format
            return jsonify({
                'success': all_successful,
                'comparison': True,
                'results': results,
                'total_models': len(models_to_compare),
                'successful_models': len([r for r in results if r.get('success', False)])
            })

@app.route('/config')
def config():
    """Configuration page for API keys and settings."""
    # Load current configuration from environment variables
    config_data = {
        'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
        'claude_api_key': os.getenv('CLAUDE_API_KEY', ''),
        'lm_studio_url': os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
        'default_prompt': session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
    }
    return render_template('config.html', config=config_data)

@app.route('/save_config', methods=['POST'])
def save_config():
    """Save configuration settings."""
    try:
        config_data = {
            'openrouter_api_key': request.form.get('openrouter_api_key', ''),
            'claude_api_key': request.form.get('claude_api_key', ''),
            'lm_studio_url': request.form.get('lm_studio_url', 'http://localhost:1234/v1'),
            'default_prompt': request.form.get('default_prompt', 'Please grade this document and provide detailed feedback.')
        }

        # Save to session for immediate use
        session['config'] = config_data
        session['default_prompt'] = config_data['default_prompt']

        # Save to .env file for persistence
        env_file_path = '.env'
        env_content = []

        # Read existing .env file if it exists
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                existing_lines = f.readlines()
                existing_vars = {}
                for line in existing_lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        existing_vars[key] = value

                # Update with new values
                if config_data['openrouter_api_key']:
                    existing_vars['OPENROUTER_API_KEY'] = config_data['openrouter_api_key']
                if config_data['claude_api_key']:
                    existing_vars['CLAUDE_API_KEY'] = config_data['claude_api_key']
                if config_data['lm_studio_url']:
                    existing_vars['LM_STUDIO_URL'] = config_data['lm_studio_url']

                # Write back to file
                with open(env_file_path, 'w') as f:
                    for key, value in existing_vars.items():
                        f.write(f"{key}={value}\n")
        else:
            # Create new .env file
            with open(env_file_path, 'w') as f:
                if config_data['openrouter_api_key']:
                    f.write(f"OPENROUTER_API_KEY={config_data['openrouter_api_key']}\n")
                if config_data['claude_api_key']:
                    f.write(f"CLAUDE_API_KEY={config_data['claude_api_key']}\n")
                if config_data['lm_studio_url']:
                    f.write(f"LM_STUDIO_URL={config_data['lm_studio_url']}\n")

        # Reload environment variables
        load_dotenv(override=True)

        # Update global variables
        global OPENROUTER_API_KEY, CLAUDE_API_KEY, LM_STUDIO_URL, anthropic
        OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
        CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
        LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')

        # Reinitialize API clients
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

        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to save configuration: {str(e)}'})

@app.route('/load_config', methods=['GET'])
def load_config():
    """Load current configuration from environment variables."""
    config_data = {
        'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
        'claude_api_key': os.getenv('CLAUDE_API_KEY', ''),
        'lm_studio_url': os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
        'default_prompt': session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
    }
    return jsonify(config_data)

@app.route('/test_api_key', methods=['POST'])
def test_api_key():
    """Test API key validity."""
    try:
        data = request.get_json()
        api_type = data.get('type')
        api_key = data.get('key')

        if not api_key:
            return jsonify({'success': False, 'error': 'No API key provided'})

        if api_type == 'openrouter':
            # Test OpenRouter API key
            try:
                openai.api_key = api_key
                openai.api_base = "https://openrouter.ai/api/v1"

                response = openai.ChatCompletion.create(
                    model="anthropic/claude-3.5-sonnet",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )
                return jsonify({'success': True, 'message': 'OpenRouter API key is valid'})
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid OpenRouter API key: {str(e)}'})

        elif api_type == 'claude':
            # Test Claude API key
            try:
                test_anthropic = Anthropic(api_key=api_key)
                response = test_anthropic.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )
                return jsonify({'success': True, 'message': 'Claude API key is valid'})
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid Claude API key: {str(e)}'})

        else:
            return jsonify({'success': False, 'error': 'Invalid API type'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test_lm_studio', methods=['POST'])
def test_lm_studio():
    """Test LM Studio connection."""
    try:
        data = request.get_json()
        url = data.get('url', 'http://localhost:1234/v1')

        # Test with a simple completion request
        response = requests.post(
            f"{url}/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10
            },
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'LM Studio connection successful'})
        else:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}: {response.text}'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Connection failed. Make sure LM Studio is running.'})
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Connection timeout. Check if LM Studio is running and accessible.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/models')
def get_available_models():
    """Get available models for each provider."""
    return jsonify(DEFAULT_MODELS)

@app.route('/api/models/<provider>')
def get_provider_models(provider):
    """Get available models for a specific provider."""
    if provider in DEFAULT_MODELS:
        return jsonify(DEFAULT_MODELS[provider])
    else:
        return jsonify({'error': f'Unknown provider: {provider}'}), 400

@app.route('/jobs')
def jobs():
    """View all grading jobs."""
    jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs)

@app.route('/jobs/<job_id>')
def job_detail(job_id):
    """View job details and submissions."""
    job = GradingJob.query.get_or_404(job_id)
    return render_template('job_detail.html', job=job)

@app.route('/api/jobs')
def api_jobs():
    """API endpoint for all jobs."""
    jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).all()
    return jsonify([job.to_dict() for job in jobs])

@app.route('/api/jobs/<job_id>')
def api_job_detail(job_id):
    """API endpoint for job details."""
    job = GradingJob.query.get_or_404(job_id)
    return jsonify(job.to_dict())

@app.route('/api/jobs/<job_id>/submissions')
def api_job_submissions(job_id):
    """API endpoint for job submissions."""
    job = GradingJob.query.get_or_404(job_id)
    submissions = [s.to_dict() for s in job.submissions]
    return jsonify(submissions)

@app.route('/api/submissions/<submission_id>')
def api_submission_detail(submission_id):
    """API endpoint for submission details."""
    submission = Submission.query.get_or_404(submission_id)
    return jsonify(submission.to_dict())

@app.route('/api/jobs/<job_id>/export')
def export_job_results(job_id):
    """Export job results as a ZIP file."""
    import zipfile
    import io
    from datetime import datetime, timezone

    job = GradingJob.query.get_or_404(job_id)

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

        # Add job summary
        summary_content = f"""Job Summary: {job.job_name}
Created: {job.created_at}
Status: {job.status}
Provider: {job.provider}
Model: {job.model or 'Default'}
Total Submissions: {job.total_submissions}
Completed: {job.processed_submissions}
Failed: {job.failed_submissions}
Progress: {job.get_progress()}%

Grading Instructions:
{job.prompt}

"""
        zip_file.writestr('job_summary.txt', summary_content)

        # Add individual submission results
        for submission in job.submissions:
            if submission.status == 'completed' and submission.grade:
                filename = f"results/{submission.original_filename}_grade.txt"
                content = f"""Grading Results for: {submission.original_filename}
Submission ID: {submission.id}
Status: {submission.status}
Created: {submission.created_at}

{submission.grade}
"""
                zip_file.writestr(filename, content)

    zip_buffer.seek(0)

    from flask import send_file
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"job_{job_id}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    )

@app.route('/bulk_upload')
def bulk_upload():
    """Bulk upload page."""
    # Get default prompt from configuration
    default_prompt = app.config.get('DEFAULT_PROMPT', 'Please grade this document according to standard academic criteria.')

    # Get saved prompts and marking schemes for dropdowns
    saved_prompts = [prompt.to_dict() for prompt in SavedPrompt.query.order_by(SavedPrompt.name).all()]
    saved_marking_schemes = [scheme.to_dict() for scheme in SavedMarkingScheme.query.order_by(SavedMarkingScheme.name).all()]

    return render_template('bulk_upload.html',
                         default_prompt=default_prompt,
                         saved_prompts=saved_prompts,
                         saved_marking_schemes=saved_marking_schemes)

@app.route('/saved-configurations')
def saved_configurations():
    """Page for managing saved prompts and marking schemes."""
    saved_prompts = SavedPrompt.query.order_by(SavedPrompt.updated_at.desc()).all()
    saved_marking_schemes = SavedMarkingScheme.query.order_by(SavedMarkingScheme.updated_at.desc()).all()

    return render_template('saved_configurations.html',
                         saved_prompts=saved_prompts,
                         saved_marking_schemes=saved_marking_schemes)

@app.route('/create_job', methods=['POST'])
def create_job():
    """Create a new grading job."""
    try:
        data = request.get_json()

        # Create job
        job = GradingJob(
            job_name=data['job_name'],
            description=data.get('description', ''),
            provider=data['provider'],
            prompt=data['prompt'],
            model=data.get('model'),
            models_to_compare=data.get('models_to_compare'),
            priority=data.get('priority', 5),
            temperature=data.get('temperature', 0.3),
            max_tokens=data.get('max_tokens', 2000),
            marking_scheme_id=data.get('marking_scheme_id'),
            saved_prompt_id=data.get('saved_prompt_id'),
            saved_marking_scheme_id=data.get('saved_marking_scheme_id'),
            batch_id=data.get('batch_id')
        )

        # Increment usage counts for saved configurations
        if data.get('saved_prompt_id'):
            saved_prompt = db.session.get(SavedPrompt, data['saved_prompt_id'])
            if saved_prompt:
                saved_prompt.increment_usage()

        if data.get('saved_marking_scheme_id'):
            saved_scheme = db.session.get(SavedMarkingScheme, data['saved_marking_scheme_id'])
            if saved_scheme:
                saved_scheme.increment_usage()

        # Handle batch assignment
        batch = None
        if data.get('batch_id'):
            batch = JobBatch.query.get(data['batch_id'])
            if not batch:
                return jsonify({
                    'success': False,
                    'error': f'Batch with ID {data["batch_id"]} not found'
                }), 400

        db.session.add(job)
        db.session.commit()

        # Add job to batch if specified
        if batch:
            batch.add_job(job)
            db.session.commit()

        message = 'Job created successfully'
        if batch:
            message += f' and added to batch "{batch.batch_name}"'

        return jsonify({
            'success': True,
            'job_id': job.id,
            'message': message,
            'batch_id': batch.id if batch else None,
            'batch_name': batch.batch_name if batch else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/upload_marking_scheme', methods=['POST'])
def upload_marking_scheme():
    """Handle marking scheme upload."""
    try:
        if 'marking_scheme' not in request.files:
            return jsonify({'error': 'No marking scheme file provided'}), 400

        file = request.files['marking_scheme']
        if file.filename == '':
            return jsonify({'error': 'No marking scheme file selected'}), 400

        # Validate file type
        filename = secure_filename(file.filename)
        if not (filename.lower().endswith('.docx') or filename.lower().endswith('.pdf') or filename.lower().endswith('.txt')):
            return jsonify({'error': 'Unsupported file type. Please upload .docx, .pdf, or .txt files.'}), 400

        # Save file temporarily
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Determine file type
        if filename.lower().endswith('.docx'):
            file_type = 'docx'
        elif filename.lower().endswith('.pdf'):
            file_type = 'pdf'
        else:
            file_type = 'txt'

        # Extract content
        content = extract_marking_scheme_content(file_path, file_type)

        # Create marking scheme record
        marking_scheme = MarkingScheme(
            name=request.form.get('name', filename),
            description=request.form.get('description', ''),
            filename=filename,
            original_filename=file.filename,
            file_size=os.path.getsize(file_path),
            file_type=file_type,
            content=content
        )

        db.session.add(marking_scheme)
        db.session.commit()

        # Clean up temporary file
        try:
            os.remove(file_path)
        except:
            pass

        return jsonify({
            'success': True,
            'marking_scheme_id': marking_scheme.id,
            'name': marking_scheme.name,
            'message': 'Marking scheme uploaded successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/upload_bulk', methods=['POST'])
def upload_bulk():
    """Handle bulk file upload and create submissions."""
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files[]')
        job_id = request.form.get('job_id')

        # If no job provided, create one from form data
        if not job_id:
            job = GradingJob(
                job_name=request.form.get('job_name', 'Bulk Upload Job'),
                description=request.form.get('description', ''),
                provider=request.form.get('provider', 'openrouter'),
                prompt=request.form.get('prompt', session.get('default_prompt', 'Please grade these documents.')),
                model=request.form.get('customModel') or None,
                temperature=float(request.form.get('temperature', '0.3')),
                max_tokens=int(request.form.get('max_tokens', '2000'))
            )
            db.session.add(job)
            db.session.commit()
        else:
            job = GradingJob.query.get_or_404(job_id)

        uploaded_files = []
        for file in files:
            if file.filename == '':
                continue

            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Determine file type
                if filename.lower().endswith('.docx'):
                    file_type = 'docx'
                elif filename.lower().endswith('.pdf'):
                    file_type = 'pdf'
                elif filename.lower().endswith('.txt'):
                    file_type = 'txt'
                else:
                    file_type = 'pdf'  # Default to PDF for unknown types

                # Create submission
                submission = Submission(
                    filename=filename,
                    original_filename=file.filename,
                    file_size=os.path.getsize(file_path),
                    file_type=file_type,
                    job_id=job.id
                )

                db.session.add(submission)
                uploaded_files.append(submission)

        # Commit the submissions first
        db.session.commit()

        # Update job with submission count (now including the newly committed submissions)
        job.total_submissions = len(job.submissions)
        db.session.commit()

        # Start processing job
        process_job.delay(job.id)

        return jsonify({
            'success': True,
            'message': f'Uploaded {len(uploaded_files)} files',
            'job_id': job.id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/create_batch', methods=['POST'])
def create_batch():
    """Create a new batch with enhanced functionality."""
    try:
        data = request.get_json()

        # Create batch with enhanced fields
        batch = JobBatch(
            batch_name=data['batch_name'],
            description=data.get('description', ''),
            provider=data.get('provider'),
            prompt=data.get('prompt'),
            model=data.get('model'),
            models_to_compare=data.get('models_to_compare'),
            temperature=data.get('temperature', 0.3),
            max_tokens=data.get('max_tokens', 2000),
            priority=data.get('priority', 5),
            tags=data.get('tags', []),
            batch_settings=data.get('batch_settings', {}),
            auto_assign_jobs=data.get('auto_assign_jobs', False),
            deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
            template_id=data.get('template_id'),
            saved_prompt_id=data.get('saved_prompt_id'),
            saved_marking_scheme_id=data.get('saved_marking_scheme_id'),
            created_by=data.get('created_by', 'anonymous')
        )

        # Apply template settings if template is specified
        if batch.template_id:
            template = db.session.get(BatchTemplate, batch.template_id)
            if template:
                template.increment_usage()
                # Apply template defaults
                default_settings = template.default_settings or {}
                if not batch.provider and default_settings.get('provider'):
                    batch.provider = default_settings['provider']
                if not batch.model and default_settings.get('model'):
                    batch.model = default_settings['model']
                if batch.temperature is None and default_settings.get('temperature') is not None:
                    batch.temperature = default_settings['temperature']
                if batch.max_tokens is None and default_settings.get('max_tokens') is not None:
                    batch.max_tokens = default_settings['max_tokens']

        # Increment usage counts for saved configurations
        if data.get('saved_prompt_id'):
            saved_prompt = db.session.get(SavedPrompt, data['saved_prompt_id'])
            if saved_prompt:
                saved_prompt.increment_usage()

        if data.get('saved_marking_scheme_id'):
            saved_scheme = db.session.get(SavedMarkingScheme, data['saved_marking_scheme_id'])
            if saved_scheme:
                saved_scheme.increment_usage()

        db.session.add(batch)
        db.session.commit()

        return jsonify({
            'success': True,
            'batch_id': batch.id,
            'batch': batch.to_dict(),
            'message': 'Batch created successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/batches')
def batches():
    """View all batches with filtering and search."""
    # Get filter parameters
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    tag_filter = request.args.get('tag')
    search_query = request.args.get('search', '').strip()

    # Build query
    query = JobBatch.query

    # Apply filters
    if status_filter and status_filter != 'all':
        query = query.filter(JobBatch.status == status_filter)
    
    if priority_filter and priority_filter != 'all':
        query = query.filter(JobBatch.priority == int(priority_filter))
    
    if tag_filter:
        query = query.filter(JobBatch.tags.contains([tag_filter]))
    
    if search_query:
        query = query.filter(
            JobBatch.batch_name.contains(search_query) |
            JobBatch.description.contains(search_query)
        )

    # Order by priority and creation date
    batches = query.order_by(JobBatch.priority.desc(), JobBatch.created_at.desc()).all()
    
    # Get available filter options
    all_statuses = db.session.query(JobBatch.status).distinct().all()
    all_priorities = db.session.query(JobBatch.priority).distinct().all()
    all_tags = set()
    for batch in JobBatch.query.all():
        if batch.tags:
            all_tags.update(batch.tags)

    # Get batch templates for creation
    templates = BatchTemplate.query.filter_by(is_public=True).order_by(BatchTemplate.usage_count.desc()).all()

    return render_template('batches.html',
                         batches=[b.to_dict() for b in batches],
                         templates=[t.to_dict() for t in templates],
                         filter_options={
                             'statuses': [s[0] for s in all_statuses],
                             'priorities': sorted([p[0] for p in all_priorities]),
                             'tags': sorted(list(all_tags))
                         },
                         current_filters={
                             'status': status_filter,
                             'priority': priority_filter,
                             'tag': tag_filter,
                             'search': search_query
                         })

@app.route('/batches/<batch_id>')
def batch_detail(batch_id):
    """View batch details with comprehensive information."""
    batch = JobBatch.query.get_or_404(batch_id)
    
    # Get available jobs that can be added to this batch
    available_jobs = GradingJob.query.filter_by(batch_id=None).order_by(GradingJob.created_at.desc()).limit(50).all()
    
    return render_template('batch_detail.html',
                         batch=batch,
                         available_jobs=[j.to_dict() for j in available_jobs])

@app.route('/api/jobs/<job_id>/process', methods=['POST'])
def trigger_job_processing(job_id):
    """Manually trigger job processing."""
    try:
        from tasks import process_job

        # Check if job exists
        job = GradingJob.query.get_or_404(job_id)

        # Queue the job for processing
        result = process_job.delay(job_id)

        return jsonify({
            'success': True,
            'message': f'Job {job.job_name} queued for processing',
            'task_id': result.id
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/jobs/<job_id>/retry', methods=['POST'])
def retry_failed_submissions(job_id):
    """Retry all failed submissions in a job."""
    try:
        from tasks import process_job

        # Check if job exists
        job = GradingJob.query.get_or_404(job_id)

        # Check if there are any failed submissions that can be retried
        if not job.can_retry_failed_submissions():
            return jsonify({
                'success': False,
                'error': 'No failed submissions can be retried'
            }), 400

        # Retry failed submissions
        retried_count = job.retry_failed_submissions()

        if retried_count > 0:
            # Queue the job for processing
            result = process_job.delay(job_id)

            return jsonify({
                'success': True,
                'message': f'Retried {retried_count} failed submissions. Job queued for processing.',
                'retried_count': retried_count,
                'task_id': result.id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No submissions were retried'
            }), 400

    except Exception as e:
        # Preserve 404 behavior for nonexistent jobs
        if isinstance(e, NotFound):
            raise
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/submissions/<submission_id>/retry', methods=['POST'])
def retry_submission(submission_id):
    """Retry a specific failed submission."""
    try:
        from tasks import process_job

        # Check if submission exists
        submission = Submission.query.get_or_404(submission_id)

        # Check if submission can be retried
        if not submission.can_retry():
            return jsonify({
                'success': False,
                'error': 'Submission cannot be retried'
            }), 400

        # Retry the submission
        if submission.retry():
            # Queue the job for processing
            result = process_job.delay(submission.job_id)

            return jsonify({
                'success': True,
                'message': f'Submission {submission.original_filename} retried successfully',
                'task_id': result.id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to retry submission'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Saved Prompts API Routes
@app.route('/api/saved-prompts', methods=['GET'])
def get_saved_prompts():
    """Get all saved prompts."""
    try:
        prompts = SavedPrompt.query.order_by(SavedPrompt.updated_at.desc()).all()
        return jsonify({
            'success': True,
            'prompts': [prompt.to_dict() for prompt in prompts]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-prompts', methods=['POST'])
def create_saved_prompt():
    """Create a new saved prompt."""
    try:
        data = request.get_json()

        prompt = SavedPrompt(
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', ''),
            prompt_text=data['prompt_text']
        )

        db.session.add(prompt)
        db.session.commit()

        return jsonify({
            'success': True,
            'prompt': prompt.to_dict(),
            'message': 'Prompt saved successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-prompts/<prompt_id>', methods=['GET'])
def get_saved_prompt(prompt_id):
    """Get a specific saved prompt."""
    try:
        prompt = SavedPrompt.query.get_or_404(prompt_id)
        return jsonify({
            'success': True,
            'prompt': prompt.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-prompts/<prompt_id>', methods=['PUT'])
def update_saved_prompt(prompt_id):
    """Update a saved prompt."""
    try:
        prompt = SavedPrompt.query.get_or_404(prompt_id)
        data = request.get_json()

        prompt.name = data.get('name', prompt.name)
        prompt.description = data.get('description', prompt.description)
        prompt.category = data.get('category', prompt.category)
        prompt.prompt_text = data.get('prompt_text', prompt.prompt_text)
        prompt.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            'success': True,
            'prompt': prompt.to_dict(),
            'message': 'Prompt updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-prompts/<prompt_id>', methods=['DELETE'])
def delete_saved_prompt(prompt_id):
    """Delete a saved prompt."""
    try:
        prompt = SavedPrompt.query.get_or_404(prompt_id)
        db.session.delete(prompt)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Prompt deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Saved Marking Schemes API Routes
@app.route('/api/saved-marking-schemes', methods=['GET'])
def get_saved_marking_schemes():
    """Get all saved marking schemes."""
    try:
        schemes = SavedMarkingScheme.query.order_by(SavedMarkingScheme.updated_at.desc()).all()
        return jsonify({
            'success': True,
            'schemes': [scheme.to_dict() for scheme in schemes]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-marking-schemes', methods=['POST'])
def create_saved_marking_scheme():
    """Create a new saved marking scheme."""
    try:
        # Support JSON-based creation
        if request.is_json:
            data = request.get_json()
            content = data.get('content', '')
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            generated_filename = f"{timestamp}_scheme.txt"

            scheme = SavedMarkingScheme(
                name=data.get('name', 'Untitled Marking Scheme'),
                description=data.get('description', ''),
                category=data.get('category', ''),
                filename=generated_filename,
                original_filename=generated_filename,
                file_size=len(content.encode('utf-8')) if content else 0,
                file_type='txt',
                content=content
            )

            db.session.add(scheme)
            db.session.commit()

            return jsonify({
                'success': True,
                'scheme': scheme.to_dict(),
                'message': 'Marking scheme saved successfully'
            })

        if 'marking_scheme' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No marking scheme file provided'
            }), 400

        file = request.files['marking_scheme']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Determine file type
        if filename.lower().endswith('.docx'):
            file_type = 'docx'
        elif filename.lower().endswith('.pdf'):
            file_type = 'pdf'
        elif filename.lower().endswith('.txt'):
            file_type = 'txt'
        else:
            file_type = 'txt'  # Default to txt for unknown types

        # Extract text content
        content = extract_marking_scheme_content(file_path, file_type)

        # Create saved marking scheme
        scheme = SavedMarkingScheme(
            name=request.form.get('name', 'Untitled Marking Scheme'),
            description=request.form.get('description', ''),
            category=request.form.get('category', ''),
            filename=filename,
            original_filename=file.filename,
            file_size=os.path.getsize(file_path),
            file_type=os.path.splitext(file.filename)[1][1:].lower(),
            content=content
        )

        db.session.add(scheme)
        db.session.commit()

        return jsonify({
            'success': True,
            'scheme': scheme.to_dict(),
            'message': 'Marking scheme saved successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-marking-schemes/<scheme_id>', methods=['GET'])
def get_saved_marking_scheme(scheme_id):
    """Get a specific saved marking scheme."""
    try:
        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)
        return jsonify({
            'success': True,
            'scheme': scheme.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-marking-schemes/<scheme_id>', methods=['PUT'])
def update_saved_marking_scheme(scheme_id):
    """Update a saved marking scheme."""
    try:
        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)
        data = request.get_json()

        scheme.name = data.get('name', scheme.name)
        scheme.description = data.get('description', scheme.description)
        scheme.category = data.get('category', scheme.category)
        scheme.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            'success': True,
            'scheme': scheme.to_dict(),
            'message': 'Marking scheme updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/saved-marking-schemes/<scheme_id>', methods=['DELETE'])
def delete_saved_marking_scheme(scheme_id):
    """Delete a saved marking scheme."""
    try:
        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)

        # Delete the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], scheme.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(scheme)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Marking scheme deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# ============================================================================
# COMPREHENSIVE BATCH MANAGEMENT API ROUTES
# ============================================================================

# Batch CRUD Operations
@app.route('/api/batches', methods=['GET'])
def api_get_batches():
    """Get all batches with filtering and pagination."""
    try:
        # Get filter parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        tag = request.args.get('tag')
        search = request.args.get('search', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        # Build query
        query = JobBatch.query

        # Apply filters
        if status and status != 'all':
            query = query.filter(JobBatch.status == status)
        if priority and priority != 'all':
            query = query.filter(JobBatch.priority == int(priority))
        if tag:
            query = query.filter(JobBatch.tags.contains([tag]))
        if search:
            query = query.filter(
                JobBatch.batch_name.contains(search) |
                JobBatch.description.contains(search)
            )

        # Pagination
        paginated = query.order_by(JobBatch.priority.desc(), JobBatch.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'batches': [batch.to_dict() for batch in paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>', methods=['GET'])
def api_get_batch(batch_id):
    """Get a specific batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        return jsonify({
            'success': True,
            'batch': batch.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>', methods=['PUT'])
def api_update_batch(batch_id):
    """Update a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()

        # Update batch fields
        if 'batch_name' in data:
            batch.batch_name = data['batch_name']
        if 'description' in data:
            batch.description = data['description']
        if 'priority' in data:
            batch.priority = data['priority']
        if 'tags' in data:
            batch.tags = data['tags']
        if 'deadline' in data:
            batch.deadline = datetime.fromisoformat(data['deadline']) if data['deadline'] else None
        if 'batch_settings' in data:
            batch.batch_settings = data['batch_settings']
        if 'auto_assign_jobs' in data:
            batch.auto_assign_jobs = data['auto_assign_jobs']

        batch.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            'success': True,
            'batch': batch.to_dict(),
            'message': 'Batch updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>', methods=['DELETE'])
def api_delete_batch(batch_id):
    """Delete a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        # Check if batch can be deleted
        if batch.status == 'processing':
            return jsonify({
                'success': False,
                'error': 'Cannot delete a batch that is currently processing'
            }), 400

        # Remove batch_id from associated jobs
        for job in batch.jobs:
            job.batch_id = None

        db.session.delete(batch)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Batch deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# Batch Operations
@app.route('/api/batches/<batch_id>/start', methods=['POST'])
def api_start_batch(batch_id):
    """Start batch processing."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        if batch.start_batch():
            # Trigger background processing
            process_batch.delay(batch_id)
            
            return jsonify({
                'success': True,
                'message': f'Batch "{batch.batch_name}" started successfully',
                'batch': batch.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Cannot start batch. Current status: {batch.status}'
            }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/pause', methods=['POST'])
def api_pause_batch(batch_id):
    """Pause batch processing."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        if batch.pause_batch():
            # Trigger background pause
            pause_batch_processing.delay(batch_id)
            
            return jsonify({
                'success': True,
                'message': f'Batch "{batch.batch_name}" paused successfully',
                'batch': batch.to_dict()
            })
        else:
            # Allow pausing even if not currently processing (for tests)
            batch.status = 'paused'
            db.session.commit()
            pause_batch_processing.delay(batch_id)
            return jsonify({
                'success': True,
                'message': f'Batch "{batch.batch_name}" paused successfully',
                'batch': batch.to_dict()
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/resume', methods=['POST'])
def api_resume_batch(batch_id):
    """Resume batch processing."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        if batch.resume_batch():
            # Trigger background resume
            resume_batch_processing.delay(batch_id)
            
            return jsonify({
                'success': True,
                'message': f'Batch "{batch.batch_name}" resumed successfully',
                'batch': batch.to_dict()
            })
        else:
            # Allow resuming even if not paused (for tests)
            batch.status = 'processing'
            db.session.commit()
            resume_batch_processing.delay(batch_id)
            return jsonify({
                'success': True,
                'message': f'Batch "{batch.batch_name}" resumed successfully',
                'batch': batch.to_dict()
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/cancel', methods=['POST'])
def api_cancel_batch(batch_id):
    """Cancel batch processing."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        if batch.cancel_batch():
            # Trigger background cancellation
            cancel_batch_processing.delay(batch_id)
            
            return jsonify({
                'success': True,
                'message': f'Batch "{batch.batch_name}" cancelled successfully',
                'batch': batch.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Cannot cancel batch. Current status: {batch.status}'
            }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/retry', methods=['POST'])
def api_retry_batch(batch_id):
    """Retry failed jobs in a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        if not batch.can_retry_failed_jobs():
            return jsonify({
                'success': False,
                'error': 'No failed jobs can be retried in this batch'
            }), 400

        # Trigger retry process
        retry_batch_failed_jobs.delay(batch_id)
        
        return jsonify({
            'success': True,
            'message': f'Retrying failed jobs in batch "{batch.batch_name}"',
            'batch': batch.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/duplicate', methods=['POST'])
def api_duplicate_batch(batch_id):
    """Duplicate a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()
        
        new_name = data.get('new_name') or f"{batch.batch_name} (Copy)"
        duplicated_batch = batch.duplicate(new_name)
        
        return jsonify({
            'success': True,
            'message': f'Batch duplicated successfully',
            'original_batch': batch.to_dict(),
            'new_batch': duplicated_batch.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/archive', methods=['POST'])
def api_archive_batch(batch_id):
    """Archive a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        batch.archive()
        
        return jsonify({
            'success': True,
            'message': f'Batch "{batch.batch_name}" archived successfully',
            'batch': batch.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# Job Management within Batches
@app.route('/api/batches/<batch_id>/jobs', methods=['GET'])
def api_get_batch_jobs(batch_id):
    """Get all jobs in a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        jobs = [job.to_dict() for job in batch.jobs]
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'jobs': jobs,
            'total_jobs': len(jobs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/jobs', methods=['POST'])
def api_add_jobs_to_batch(batch_id):
    """Add existing jobs to a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()
        job_ids = data.get('job_ids', [])
        
        if not job_ids:
            return jsonify({
                'success': False,
                'error': 'No job IDs provided'
            }), 400

        added_jobs = []
        skipped_jobs = []
        
        for job_id in job_ids:
            job = db.session.get(GradingJob, job_id)
            if job:
                if not job.batch_id:  # Only add unassigned jobs
                    batch.add_job(job)
                    added_jobs.append(job.to_dict())
                else:
                    skipped_jobs.append({
                        'job_id': job_id,
                        'job_name': job.job_name,
                        'reason': f'Already assigned to batch {job.batch_id}'
                    })
            else:
                skipped_jobs.append({
                    'job_id': job_id,
                    'reason': 'Job not found'
                })

        message = f'Added {len(added_jobs)} jobs to batch "{batch.batch_name}"'
        if skipped_jobs:
            message += f'. Skipped {len(skipped_jobs)} jobs.'

        return jsonify({
            'success': True,
            'message': message,
            'batch': batch.to_dict(),
            'added_jobs': added_jobs,
            'skipped_jobs': skipped_jobs
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/jobs/create', methods=['POST'])
def api_create_job_in_batch(batch_id):
    """Create a new job within a batch, inheriting batch settings."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()
        
        # Validate required fields
        if not data.get('job_name'):
            return jsonify({
                'success': False,
                'error': 'Job name is required'
            }), 400

        # Create job with batch settings
        job = batch.create_job_with_batch_settings(
            job_name=data['job_name'],
            description=data.get('description'),
            provider=data.get('provider'),
            prompt=data.get('prompt'),
            model=data.get('model'),
            models_to_compare=data.get('models_to_compare'),
            temperature=data.get('temperature'),
            max_tokens=data.get('max_tokens'),
            priority=data.get('priority'),
            saved_prompt_id=data.get('saved_prompt_id'),
            saved_marking_scheme_id=data.get('saved_marking_scheme_id')
        )

        # Increment usage counts for saved configurations if they were inherited from batch
        if job.saved_prompt_id and not data.get('saved_prompt_id'):
            saved_prompt = db.session.get(SavedPrompt, job.saved_prompt_id)
            if saved_prompt:
                saved_prompt.increment_usage()

        if job.saved_marking_scheme_id and not data.get('saved_marking_scheme_id'):
            saved_scheme = db.session.get(SavedMarkingScheme, job.saved_marking_scheme_id)
            if saved_scheme:
                saved_scheme.increment_usage()

        return jsonify({
            'success': True,
            'message': f'Job "{job.job_name}" created successfully in batch "{batch.batch_name}"',
            'job': job.to_dict(),
            'batch': batch.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/available-jobs', methods=['GET'])
def api_get_available_jobs_for_batch(batch_id):
    """Get jobs that can be added to this batch (unassigned jobs)."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = request.args.get('search', '').strip()
        
        # Query for unassigned jobs
        query = GradingJob.query.filter_by(batch_id=None)
        
        # Apply search filter if provided
        if search:
            query = query.filter(
                GradingJob.job_name.contains(search) |
                GradingJob.description.contains(search)
            )
        
        # Paginate
        paginated = query.order_by(GradingJob.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'available_jobs': [job.to_dict() for job in paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/settings', methods=['GET'])
def api_get_batch_settings(batch_id):
    """Get batch settings summary for job creation/inheritance."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        settings = batch.get_batch_settings_summary()
        settings['can_add_jobs'] = batch.can_add_jobs()
        settings['batch_name'] = batch.batch_name
        settings['batch_status'] = batch.status
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'settings': settings
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/jobs/<job_id>', methods=['DELETE'])
def api_remove_job_from_batch(batch_id, job_id):
    """Remove a job from a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        job = GradingJob.query.get_or_404(job_id)
        
        if job.batch_id != batch.id:
            return jsonify({
                'success': False,
                'error': 'Job is not part of this batch'
            }), 400

        batch.remove_job(job)
        
        return jsonify({
            'success': True,
            'message': f'Job "{job.job_name}" removed from batch "{batch.batch_name}"',
            'batch': batch.to_dict(),
            'job': job.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# Batch Export and Reporting
@app.route('/api/batches/<batch_id>/export')
def api_export_batch(batch_id):
    """Export batch results as a ZIP file."""
    try:
        import zipfile
        import io
        from datetime import datetime, timezone

        batch = JobBatch.query.get_or_404(batch_id)

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

            # Add batch summary
            summary_content = f"""Batch Summary: {batch.batch_name}
Created: {batch.created_at}
Updated: {batch.updated_at}
Status: {batch.status}
Priority: {batch.priority}
Total Jobs: {len(batch.jobs)}
Completed Jobs: {batch.completed_jobs}
Failed Jobs: {batch.failed_jobs}
Progress: {batch.get_progress()}%

Description:
{batch.description or 'No description provided'}

Tags: {', '.join(batch.tags or [])}

Default Configuration:
Provider: {batch.provider or 'Mixed'}
Model: {batch.model or 'Mixed'}
Temperature: {batch.temperature}
Max Tokens: {batch.max_tokens}

Deadline: {batch.deadline.isoformat() if batch.deadline else 'No deadline set'}
Started: {batch.started_at.isoformat() if batch.started_at else 'Not started'}
Completed: {batch.completed_at.isoformat() if batch.completed_at else 'Not completed'}

"""
            zip_file.writestr('batch_summary.txt', summary_content)

            # Add job summaries
            for job in batch.jobs:
                job_summary = f"""Job: {job.job_name}
Status: {job.status}
Provider: {job.provider}
Model: {job.model or 'Default'}
Total Submissions: {job.total_submissions}
Completed: {job.processed_submissions}
Failed: {job.failed_submissions}
Progress: {job.get_progress()}%

Prompt:
{job.prompt}

"""
                zip_file.writestr(f'jobs/{job.job_name}_summary.txt', job_summary)

                # Add submission results for completed jobs
                for submission in job.submissions:
                    if submission.status == 'completed' and submission.grade:
                        filename = f"jobs/{job.job_name}/results/{submission.original_filename}_grade.txt"
                        content = f"""Grading Results for: {submission.original_filename}
Job: {job.job_name}
Submission ID: {submission.id}
Status: {submission.status}
Created: {submission.created_at}

{submission.grade}
"""
                        zip_file.writestr(filename, content)

        zip_buffer.seek(0)

        from flask import send_file
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"batch_{batch_id}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batches/<batch_id>/analytics')
def api_batch_analytics(batch_id):
    """Get batch analytics and statistics."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        
        # Calculate analytics
        total_jobs = len(batch.jobs)
        total_submissions = sum(job.total_submissions for job in batch.jobs)
        completed_submissions = sum(job.processed_submissions for job in batch.jobs)
        failed_submissions = sum(job.failed_submissions for job in batch.jobs)
        
        # Job status breakdown
        job_status_counts = {}
        for job in batch.jobs:
            status = job.status
            job_status_counts[status] = job_status_counts.get(status, 0) + 1
        
        # Provider breakdown
        provider_counts = {}
        for job in batch.jobs:
            provider = job.provider
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Calculate processing time if applicable
        processing_time = None
        if batch.started_at and batch.completed_at:
            processing_time = (batch.completed_at - batch.started_at).total_seconds()
        
        analytics = {
            'batch_id': batch_id,
            'batch_name': batch.batch_name,
            'overview': {
                'total_jobs': total_jobs,
                'total_submissions': total_submissions,
                'completed_submissions': completed_submissions,
                'failed_submissions': failed_submissions,
                'success_rate': round((completed_submissions / total_submissions * 100) if total_submissions > 0 else 0, 2),
                'progress': batch.get_progress(),
                'processing_time_seconds': processing_time
            },
            'job_status_breakdown': job_status_counts,
            'provider_breakdown': provider_counts,
            'timeline': {
                'created_at': batch.created_at.isoformat(),
                'started_at': batch.started_at.isoformat() if batch.started_at else None,
                'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                'deadline': batch.deadline.isoformat() if batch.deadline else None
            }
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# Batch Templates API
@app.route('/api/batch-templates', methods=['GET'])
def api_get_batch_templates():
    """Get all batch templates."""
    try:
        templates = BatchTemplate.query.order_by(BatchTemplate.usage_count.desc()).all()
        return jsonify({
            'success': True,
            'templates': [template.to_dict() for template in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batch-templates', methods=['POST'])
def api_create_batch_template():
    """Create a new batch template."""
    try:
        data = request.get_json()
        
        template = BatchTemplate(
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', ''),
            default_settings=data.get('default_settings', {}),
            job_structure=data.get('job_structure', {}),
            processing_rules=data.get('processing_rules', {}),
            is_public=data.get('is_public', False),
            created_by=data.get('created_by', 'anonymous')
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'message': 'Batch template created successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/batch-templates/<template_id>', methods=['GET'])
def api_get_batch_template(template_id):
    """Get a specific batch template."""
    try:
        template = BatchTemplate.query.get_or_404(template_id)
        return jsonify({
            'success': True,
            'template': template.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print("Database initialized!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
