"""
Main page routes for the grading application.
Handles index, jobs, config, and other main navigation routes.
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from models import db, GradingJob, JobBatch, SavedPrompt, SavedMarkingScheme, BatchTemplate
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
    # Load current configuration from environment variables
    config_data = {
        'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
        'claude_api_key': os.getenv('CLAUDE_API_KEY', ''),
        'lm_studio_url': os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
        'default_prompt': session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
    }
    return render_template('config.html', config=config_data)


@main_bp.route('/save_config', methods=['POST'])
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

        # Update global variables in the main app (this needs to be handled in app.py)
        from flask import current_app
        with current_app.app_context():
            # These will be handled by the main app after import
            pass

        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to save configuration: {str(e)}'})


@main_bp.route('/load_config', methods=['GET'])
def load_config():
    """Load current configuration from environment variables."""
    config_data = {
        'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
        'claude_api_key': os.getenv('CLAUDE_API_KEY', ''),
        'lm_studio_url': os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1'),
        'default_prompt': session.get('default_prompt', 'Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.')
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