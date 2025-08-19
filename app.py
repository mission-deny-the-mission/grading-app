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
from models import db, GradingJob, Submission, JobBatch
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

def grade_with_openrouter(text, prompt, model="anthropic/claude-3.5-sonnet"):
    """Grade document using OpenRouter API."""
    try:
        # Configure OpenAI for OpenRouter
        openai.api_key = OPENROUTER_API_KEY
        openai.api_base = "https://openrouter.ai/api/v1"
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback."},
                {"role": "user", "content": f"{prompt}\n\nDocument to grade:\n{text}"}
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

def grade_with_claude(text, prompt):
    """Grade document using Claude API."""
    if not anthropic:
        return {
            'success': False,
            'error': "Claude API not configured or failed to initialize",
            'provider': 'Claude'
        }
    
    try:
        response = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.3,
            system="You are a professional document grader. Provide detailed, constructive feedback.",
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nDocument to grade:\n{text}"
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

def grade_with_lm_studio(text, prompt):
    """Grade document using LM Studio API."""
    try:
        response = requests.post(
            f"{LM_STUDIO_URL}/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback."},
                    {"role": "user", "content": f"{prompt}\n\nDocument to grade:\n{text}"}
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
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and grading."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract text based on file type
        if filename.lower().endswith('.docx'):
            text = extract_text_from_docx(file_path)
        elif filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            return jsonify({'error': 'Unsupported file type. Please upload .docx or .pdf files.'}), 400
        
        # Get grading parameters
        prompt = request.form.get('prompt', 'Please grade this document and provide detailed feedback.')
        provider = request.form.get('provider', 'openrouter')
        
        # Grade the document
        if provider == 'openrouter':
            if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'sk-or-your-key-here':
                return jsonify({'error': 'OpenRouter API key not configured. Please configure your API key in the settings.'}), 400
            result = grade_with_openrouter(text, prompt)
        elif provider == 'claude':
            if not CLAUDE_API_KEY or CLAUDE_API_KEY == 'sk-ant-your-key-here':
                return jsonify({'error': 'Claude API key not configured. Please configure your API key in the settings.'}), 400
            if not anthropic:
                return jsonify({'error': 'Claude API client failed to initialize. Please check your API key configuration.'}), 400
            result = grade_with_claude(text, prompt)
        elif provider == 'lm_studio':
            result = grade_with_lm_studio(text, prompt)
        else:
            return jsonify({'error': f'Unsupported provider: {provider}. Supported providers are: openrouter, claude, lm_studio'}), 400
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass  # Don't fail if file cleanup fails
        
        # Check if grading was successful
        if not result.get('success', False):
            return jsonify({'error': result.get('error', 'Unknown error occurred during grading')}), 500
        
        return jsonify(result)

@app.route('/config')
def config():
    """Configuration page for API keys and settings."""
    return render_template('config.html')

@app.route('/save_config', methods=['POST'])
def save_config():
    """Save configuration settings."""
    config_data = {
        'openrouter_api_key': request.form.get('openrouter_api_key', ''),
        'claude_api_key': request.form.get('claude_api_key', ''),
        'lm_studio_url': request.form.get('lm_studio_url', 'http://localhost:1234/v1'),
        'default_prompt': request.form.get('default_prompt', 'Please grade this document and provide detailed feedback.')
    }
    
    # Save to session for now (in production, use a database)
    session['config'] = config_data
    
    return jsonify({'success': True, 'message': 'Configuration saved successfully'})

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
    return render_template('bulk_upload.html')

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
            priority=data.get('priority', 5)
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

@app.route('/test_lm_studio', methods=['POST'])
def test_lm_studio():
    """Test LM Studio connection."""
    try:
        data = request.get_json()
        url = data.get('url', 'http://localhost:1234/v1')
        
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
            return jsonify({'success': True, 'message': 'Connection successful'})
        else:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
