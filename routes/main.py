"""
Main page routes for the grading application.
Handles index, jobs, config, and other main navigation routes.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, GradingJob, JobBatch, SavedPrompt, SavedMarkingScheme, BatchTemplate, Config
import os
from dotenv import load_dotenv
import openai
from anthropic import Anthropic


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main page with upload form and configuration."""
    default_prompt = session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
    return render_template('index.html', default_prompt=default_prompt)


@main_bp.route('/config')
def config():
    """Configuration page for API keys and settings."""
    try:
        # Get config from database
        config = Config.get_or_create()
        return render_template('config.html', config=config)
    except Exception as e:
        # Fallback to empty config if database fails
        return render_template('config.html', config=None)


@main_bp.route('/save_config', methods=['POST'])
def save_config():
    """Save configuration settings."""
    try:
        # Get or create config record
        config = Config.get_or_create()
        
        # Update all fields from form
        config.openrouter_api_key = request.form.get('openrouter_api_key', '').strip() or None
        config.claude_api_key = request.form.get('claude_api_key', '').strip() or None
        config.gemini_api_key = request.form.get('gemini_api_key', '').strip() or None
        config.openai_api_key = request.form.get('openai_api_key', '').strip() or None
        config.lm_studio_url = request.form.get('lm_studio_url', 'http://localhost:1234/v1').strip()
        config.ollama_url = request.form.get('ollama_url', 'http://localhost:11434/api/generate').strip()
        config.default_prompt = request.form.get('default_prompt', '').strip() or None
        
        # Update default model configurations
        config.openrouter_default_model = request.form.get('openrouter_default_model', '').strip() or None
        config.claude_default_model = request.form.get('claude_default_model', '').strip() or None
        config.gemini_default_model = request.form.get('gemini_default_model', '').strip() or None
        config.openai_default_model = request.form.get('openai_default_model', '').strip() or None
        config.lm_studio_default_model = request.form.get('lm_studio_default_model', '').strip() or None
        config.ollama_default_model = request.form.get('ollama_default_model', '').strip() or None
        
        # Save to database
        db.session.commit()

        # Save to session for immediate use (backward compatibility)
        session['default_prompt'] = config.default_prompt

        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to save configuration: {str(e)}'})


@main_bp.route('/load_config', methods=['GET'])
def load_config():
    """Load current configuration from database with environment variable fallback."""
    try:
        # Get config from database
        config = Config.get_or_create()
        
        # Use database values with environment variable fallbacks
        config_data = {
            'openrouter_api_key': config.openrouter_api_key or os.getenv('OPENROUTER_API_KEY', ''),
            'claude_api_key': config.claude_api_key or os.getenv('CLAUDE_API_KEY', ''),
            'gemini_api_key': config.gemini_api_key or os.getenv('GEMINI_API_KEY', ''),
            'openai_api_key': config.openai_api_key or os.getenv('OPENAI_API_KEY', ''),
            'lm_studio_url': config.lm_studio_url or os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
            'ollama_url': config.ollama_url or os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate'),
            'default_prompt': config.default_prompt or 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.',
            
            # Default model configurations
            'openrouter_default_model': config.openrouter_default_model or '',
            'claude_default_model': config.claude_default_model or '',
            'gemini_default_model': config.gemini_default_model or '',
            'openai_default_model': config.openai_default_model or '',
            'lm_studio_default_model': config.lm_studio_default_model or '',
            'ollama_default_model': config.ollama_default_model or ''
        }
        return jsonify(config_data)
    except Exception as e:
        # Fallback to environment variables if database fails
        config_data = {
            'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
            'claude_api_key': os.getenv('CLAUDE_API_KEY', ''),
            'gemini_api_key': os.getenv('GEMINI_API_KEY', ''),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'lm_studio_url': os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
            'ollama_url': os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate'),
            'default_prompt': 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.',
            
            # Default model configurations (empty for fallback)
            'openrouter_default_model': '',
            'claude_default_model': '',
            'gemini_default_model': '',
            'openai_default_model': '',
            'lm_studio_default_model': '',
            'ollama_default_model': ''
        }
        return jsonify(config_data)


@main_bp.route('/test_api_key', methods=['POST'])
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

        elif api_type == 'gemini':
            # Test Gemini API key
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(
                    "Hello",
                    generation_config=genai.types.GenerationConfig(max_output_tokens=10)
                )
                return jsonify({'success': True, 'message': 'Gemini API key is valid'})
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid Gemini API key: {str(e)}'})

        elif api_type == 'openai':
            # Test OpenAI API key
            try:
                test_client = openai.OpenAI(api_key=api_key)
                response = test_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )
                return jsonify({'success': True, 'message': 'OpenAI API key is valid'})
            except Exception as e:
                return jsonify({'success': False, 'error': f'Invalid OpenAI API key: {str(e)}'})

        else:
            return jsonify({'success': False, 'error': 'Invalid API type'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@main_bp.route('/test_lm_studio', methods=['POST'])
def test_lm_studio():
    """Test LM Studio connection."""
    try:
        import requests
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


@main_bp.route('/test_ollama', methods=['POST'])
def test_ollama():
    """Test Ollama connection."""
    try:
        import requests
        data = request.get_json()
        url = data.get('url', 'http://localhost:11434/api/generate')

        # Test with a simple generation request
        response = requests.post(
            url,
            json={
                "model": "llama2",
                "prompt": "Hello",
                "options": {"num_predict": 10}
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Ollama connection successful'})
        else:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}: {response.text}'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Connection failed. Make sure Ollama is running.'})
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Connection timeout. Check if Ollama is running and accessible.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@main_bp.route('/jobs')
def jobs():
    """View all grading jobs."""
    jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs)


@main_bp.route('/jobs/<job_id>')
def job_detail(job_id):
    """View job details and submissions."""
    job = GradingJob.query.get_or_404(job_id)
    return render_template('job_detail.html', job=job)


@main_bp.route('/bulk_upload')
def bulk_upload():
    """Bulk upload page."""
    from flask import current_app
    # Get default prompt from configuration
    default_prompt = current_app.config.get('DEFAULT_PROMPT', 'Please grade this document according to standard academic criteria.')

    # Get saved prompts and marking schemes for dropdowns
    saved_prompts = [prompt.to_dict() for prompt in SavedPrompt.query.order_by(SavedPrompt.name).all()]
    saved_marking_schemes = [scheme.to_dict() for scheme in SavedMarkingScheme.query.order_by(SavedMarkingScheme.name).all()]

    return render_template('bulk_upload.html',
                         default_prompt=default_prompt,
                         saved_prompts=saved_prompts,
                         saved_marking_schemes=saved_marking_schemes)


@main_bp.route('/saved-configurations')
def saved_configurations():
    """Page for managing saved prompts and marking schemes."""
    saved_prompts = SavedPrompt.query.order_by(SavedPrompt.updated_at.desc()).all()
    saved_marking_schemes = SavedMarkingScheme.query.order_by(SavedMarkingScheme.updated_at.desc()).all()

    return render_template('saved_configurations.html',
                         saved_prompts=saved_prompts,
                         saved_marking_schemes=saved_marking_schemes)