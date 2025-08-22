"""
API routes for the grading application.
Handles RESTful API endpoints for jobs, submissions, and saved configurations.
"""
from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import NotFound
from models import db, GradingJob, Submission, SavedPrompt, SavedMarkingScheme
from datetime import datetime, timezone
import zipfile
import io
import os


api_bp = Blueprint('api', __name__, url_prefix='/api')


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
    }
}


@api_bp.route('/models')
def get_available_models():
    """Get available models for each provider."""
    return jsonify(DEFAULT_MODELS)


@api_bp.route('/models/<provider>')
def get_provider_models(provider):
    """Get available models for a specific provider."""
    if provider in DEFAULT_MODELS:
        return jsonify(DEFAULT_MODELS[provider])
    else:
        return jsonify({'error': f'Unknown provider: {provider}'}), 400


@api_bp.route('/jobs')
def api_jobs():
    """API endpoint for all jobs."""
    jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).all()
    return jsonify([job.to_dict() for job in jobs])


@api_bp.route('/jobs/<job_id>')
def api_job_detail(job_id):
    """API endpoint for job details."""
    job = GradingJob.query.get_or_404(job_id)
    return jsonify(job.to_dict())


@api_bp.route('/jobs/<job_id>/submissions')
def api_job_submissions(job_id):
    """API endpoint for job submissions."""
    job = GradingJob.query.get_or_404(job_id)
    submissions = [s.to_dict() for s in job.submissions]
    return jsonify(submissions)


@api_bp.route('/submissions/<submission_id>')
def api_submission_detail(submission_id):
    """API endpoint for submission details."""
    submission = Submission.query.get_or_404(submission_id)
    return jsonify(submission.to_dict())


@api_bp.route('/jobs/<job_id>/export')
def export_job_results(job_id):
    """Export job results as a ZIP file."""
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

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"job_{job_id}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    )


@api_bp.route('/jobs/<job_id>/process', methods=['POST'])
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


@api_bp.route('/jobs/<job_id>/retry', methods=['POST'])
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


@api_bp.route('/submissions/<submission_id>/retry', methods=['POST'])
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
@api_bp.route('/saved-prompts', methods=['GET'])
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


@api_bp.route('/saved-prompts', methods=['POST'])
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


@api_bp.route('/saved-prompts/<prompt_id>', methods=['GET'])
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


@api_bp.route('/saved-prompts/<prompt_id>', methods=['PUT'])
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


@api_bp.route('/saved-prompts/<prompt_id>', methods=['DELETE'])
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
@api_bp.route('/saved-marking-schemes', methods=['GET'])
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


@api_bp.route('/saved-marking-schemes', methods=['POST'])
def create_saved_marking_scheme():
    """Create a new saved marking scheme."""
    try:
        from werkzeug.utils import secure_filename
        from utils.text_extraction import extract_marking_scheme_content
        from utils.file_utils import determine_file_type
        from flask import current_app
        
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
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Determine file type
        file_type = determine_file_type(filename) or 'txt'

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


@api_bp.route('/saved-marking-schemes/<scheme_id>', methods=['GET'])
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


@api_bp.route('/saved-marking-schemes/<scheme_id>', methods=['PUT'])
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


@api_bp.route('/saved-marking-schemes/<scheme_id>', methods=['DELETE'])
def delete_saved_marking_scheme(scheme_id):
    """Delete a saved marking scheme."""
    try:
        from flask import current_app
        from utils.file_utils import cleanup_file
        
        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)

        # Delete the file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], scheme.filename)
        cleanup_file(file_path)

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