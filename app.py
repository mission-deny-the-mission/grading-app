import os
import json
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import openai
from anthropic import Anthropic
from docx import Document
import PyPDF2
import io
from dotenv import load_dotenv
from models import db, GradingJob, Submission, JobBatch, MarkingScheme
from tasks import process_job, process_batch

load_dotenv()

app = Flask(__name__)
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

# Default models (latest versions as of 2024)
DEFAULT_MODELS = {
    'openrouter': {
        'default': 'anthropic/claude-sonnet-4',
        'popular': [
            'anthropic/claude-opus-4.1',
            'openai/gpt-5',
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

def grade_with_openrouter(text, prompt, model="anthropic/claude-3-5-sonnet-20241022", marking_scheme_content=None):
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
            temperature=0.3,
            max_tokens=2000
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

def grade_with_claude(text, prompt, marking_scheme_content=None):
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
            max_tokens=2000,
            temperature=0.3,
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

def grade_with_lm_studio(text, prompt, marking_scheme_content=None):
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
                "temperature": 0.3,
                "max_tokens": 2000
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
                result = grade_with_openrouter(text, prompt, model, marking_scheme_content)
            elif provider == 'claude':
                if not CLAUDE_API_KEY or CLAUDE_API_KEY == 'sk-ant-your-key-here':
                    return jsonify({'error': 'Claude API key not configured. Please configure your API key in the settings.'}), 400
                if not anthropic:
                    return jsonify({'error': 'Claude API client failed to initialize. Please check your API key configuration.'}), 400
                result = grade_with_claude(text, prompt, marking_scheme_content)
            elif provider == 'lm_studio':
                result = grade_with_lm_studio(text, prompt, marking_scheme_content)
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
    from datetime import datetime
    
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
    """Bulk upload interface."""
    default_prompt = session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
    return render_template('bulk_upload.html', default_prompt=default_prompt)

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
            marking_scheme_id=data.get('marking_scheme_id')
        )
        
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'message': 'Job created successfully'
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
        
        if not job_id:
            return jsonify({'error': 'Job ID required'}), 400
        
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
    """Create a batch of jobs."""
    try:
        data = request.get_json()
        
        # Create batch
        batch = JobBatch(
            batch_name=data['batch_name'],
            description=data.get('description', ''),
            provider=data['provider'],
            prompt=data['prompt'],
            model=data.get('model')
        )
        
        db.session.add(batch)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'batch_id': batch.id,
            'message': 'Batch created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/batches')
def batches():
    """View all batches."""
    batches = JobBatch.query.order_by(JobBatch.created_at.desc()).all()
    return render_template('batches.html', batches=batches)

@app.route('/batches/<batch_id>')
def batch_detail(batch_id):
    """View batch details."""
    batch = JobBatch.query.get_or_404(batch_id)
    return render_template('batch_detail.html', batch=batch)

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
