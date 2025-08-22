"""
File upload routes for the grading application.
Handles file uploads, marking scheme uploads, and bulk uploads.
"""
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from models import db, GradingJob, Submission, MarkingScheme
from utils.llm_providers import get_llm_provider
from utils.text_extraction import extract_marking_scheme_content, extract_text_by_file_type
from utils.file_utils import determine_file_type, validate_file_upload, cleanup_file
import os
from datetime import datetime


upload_bp = Blueprint('upload', __name__)


# DEFAULT_MODELS configuration (shared from main app)
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
    },
    'ollama': {
        'default': 'llama2',
        'popular': [
            'llama2',
            'llama3',
            'codellama',
            'mistral',
            'gemma',
            'phi'
        ]
    }
}


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and grading."""
    from flask import current_app
    
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
        marking_scheme_path = os.path.join(current_app.config['UPLOAD_FOLDER'], marking_scheme_filename)
        marking_scheme_file.save(marking_scheme_path)

        # Determine marking scheme file type
        marking_scheme_type = determine_file_type(marking_scheme_filename)
        if not marking_scheme_type:
            return jsonify({'error': 'Unsupported marking scheme file type. Please upload .docx, .pdf, or .txt files.'}), 400

        # Extract marking scheme content
        marking_scheme_content = extract_marking_scheme_content(marking_scheme_path, marking_scheme_type)

        # Clean up marking scheme file
        cleanup_file(marking_scheme_path)

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Determine file type
        file_type = determine_file_type(filename)
        if not file_type:
            return jsonify({'error': 'Unsupported file type. Please upload .docx, .pdf, or .txt files.'}), 400

        # Extract text based on file type
        text = extract_text_by_file_type(file_path, file_type)
        
        if text.startswith('Error reading'):
            return jsonify({'error': text}), 400

        # Get grading parameters
        prompt = request.form.get('prompt', session.get('default_prompt', 'Please grade this document and provide detailed feedback.'))
        provider = request.form.get('provider', 'openrouter')
        custom_model = request.form.get('customModel', '').strip()
        models_to_compare = request.form.getlist('models_to_compare[]')
        custom_models = request.form.getlist('customModels[]')

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
            try:
                # Get the LLM provider instance (map provider name)
                provider_mapping = {
                    'openrouter': 'OpenRouter',
                    'claude': 'Claude',
                    'lm_studio': 'LM Studio', 
                    'ollama': 'Ollama'
                }
                provider_name = provider_mapping.get(provider, provider.title())
                if provider_name == 'Lm Studio':
                    provider_name = 'LM Studio'
                llm_provider = get_llm_provider(provider_name)
                
                # Check API key configuration for providers that need it
                if provider == 'openrouter':
                    if not os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY') == 'sk-or-your-key-here':
                        return jsonify({'error': 'OpenRouter API key not configured. Please configure your API key in the settings.'}), 400
                    result = llm_provider.grade_document(text, prompt, model, marking_scheme_content, temperature, max_tokens)
                elif provider == 'claude':
                    if not os.getenv('CLAUDE_API_KEY') or os.getenv('CLAUDE_API_KEY') == 'sk-ant-your-key-here':
                        return jsonify({'error': 'Claude API key not configured. Please configure your API key in the settings.'}), 400
                    result = llm_provider.grade_document(text, prompt, marking_scheme_content, temperature, max_tokens)
                elif provider == 'lm_studio':
                    result = llm_provider.grade_document(text, prompt, marking_scheme_content, temperature, max_tokens)
                elif provider == 'ollama':
                    result = llm_provider.grade_document(text, prompt, model, marking_scheme_content, temperature, max_tokens)
                else:
                    return jsonify({'error': f'Unsupported provider: {provider}. Supported providers are: openrouter, claude, lm_studio, ollama'}), 400
            except ValueError as e:
                return jsonify({'error': f'Provider error: {str(e)}'}), 400

            results.append(result)
            if not result.get('success', False):
                all_successful = False

        # Clean up uploaded file
        cleanup_file(file_path)

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


@upload_bp.route('/upload_marking_scheme', methods=['POST'])
def upload_marking_scheme():
    """Handle marking scheme upload."""
    from flask import current_app
    
    try:
        if 'marking_scheme' not in request.files:
            return jsonify({'error': 'No marking scheme file provided'}), 400

        file = request.files['marking_scheme']
        if file.filename == '':
            return jsonify({'error': 'No marking scheme file selected'}), 400

        # Validate file type
        filename = secure_filename(file.filename)
        file_type = determine_file_type(filename)
        if not file_type:
            return jsonify({'error': 'Unsupported file type. Please upload .docx, .pdf, or .txt files.'}), 400

        # Save file temporarily
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

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
        cleanup_file(file_path)

        return jsonify({
            'success': True,
            'marking_scheme_id': marking_scheme.id,
            'name': marking_scheme.name,
            'message': 'Marking scheme uploaded successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@upload_bp.route('/upload_bulk', methods=['POST'])
def upload_bulk():
    """Handle bulk file upload and create submissions."""
    from flask import current_app
    
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
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Determine file type
                file_type = determine_file_type(filename) or 'pdf'  # Default to PDF for unknown types

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
        from tasks import process_job
        process_job.delay(job.id)

        return jsonify({
            'success': True,
            'message': f'Uploaded {len(uploaded_files)} files',
            'job_id': job.id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400