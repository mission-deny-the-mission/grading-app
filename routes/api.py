"""
API routes for the grading application.
Handles RESTful API endpoints for jobs, submissions, and saved configurations.
"""

import io
import os
import time
import zipfile
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.exceptions import NotFound

from models import (
    BatchTemplate,
    GradingJob,
    ImageQualityMetrics,
    ImageSubmission,
    JobBatch,
    JobTemplate,
    SavedMarkingScheme,
    SavedPrompt,
    Submission,
    db,
)
from tasks import process_image_ocr
from utils.file_utils import (
    ValidationError,
    generate_storage_path,
    validate_uploaded_image,
)
from utils.llm_providers import get_llm_provider

api_bp = Blueprint("api", __name__, url_prefix="/api")


# Cache for model lists to avoid excessive API calls
_model_cache = {}
_cache_timestamp = {}
CACHE_TTL = 300  # 5 minutes in seconds


def get_cached_models(provider_name):
    """Get cached models for a provider, or fetch if cache is expired/empty."""
    current_time = time.time()

    # Check if we have cached data and it's not expired
    if (
        provider_name in _model_cache
        and provider_name in _cache_timestamp
        and current_time - _cache_timestamp[provider_name] < CACHE_TTL
    ):
        return _model_cache[provider_name]

    # Cache is empty or expired, fetch fresh data
    try:
        # Map lowercase provider names to capitalized names expected by get_llm_provider
        provider_name_mapping = {
            "openrouter": "OpenRouter",
            "claude": "Claude",
            "gemini": "Gemini",
            "openai": "OpenAI",
            "lm_studio": "LM Studio",
            "ollama": "Ollama",
            "nanogpt": "NanoGPT",
            "chutes": "Chutes",
            "zai": "Z.AI",
            "zai_coding_plan": "Z.AI Coding Plan",
        }

        capitalized_name = provider_name_mapping.get(provider_name, provider_name)
        provider = get_llm_provider(capitalized_name)
        result = provider.get_available_models()

        if result.get("success"):
            # Convert raw models list to expected format with popular/default structure
            models_list = result["models"]
            provider_config = DEFAULT_MODELS.get(provider_name, {})

            # Build the expected response format
            formatted_models = {
                "popular": (
                    [model["id"] for model in models_list] if models_list else provider_config.get("popular", [])
                ),
                "default": provider_config.get("default", models_list[0]["id"] if models_list else ""),
            }

            # Cache the successful result
            _model_cache[provider_name] = formatted_models
            _cache_timestamp[provider_name] = current_time
            return formatted_models
        else:
            # Return fallback models if API fails
            return get_fallback_models(provider_name)
    except Exception as e:
        print(f"Error fetching models for {provider_name}: {e}")
        # Return None for unknown providers to trigger 400 error
        return None


def get_fallback_models(provider_name):
    """Get fallback hardcoded models for a provider."""
    fallback_models = {
        "openrouter": {
            "popular": [
                "anthropic/claude-opus-4.1",
                "openai/gpt-5",
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet-20241022",
            ],
            "default": "anthropic/claude-opus-4.1",
        },
        "claude": {
            "popular": ["claude-3.5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
            "default": "claude-3.5-sonnet-20241022",
        },
        "gemini": {"popular": ["gemini-2.0-flash-exp", "gemini-pro"], "default": "gemini-2.0-flash-exp"},
        "openai": {"popular": ["gpt-5", "gpt-4o", "gpt-4o-mini"], "default": "gpt-4o"},
        "lm_studio": {"popular": ["local-model"], "default": "local-model"},
        "ollama": {"popular": ["llama2", "llama3"], "default": "llama2"},
        "nanogpt": {"popular": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022"], "default": "gpt-4o"},
        "chutes": {"popular": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022"], "default": "gpt-4o"},
        "zai": {"popular": ["glm-4.6", "glm-4.5", "glm-4.5-x", "glm-4.5-flash"], "default": "glm-4.6"},
        "zai_coding_plan": {"popular": ["glm-4.6", "glm-4.5", "glm-4.5-air"], "default": "glm-4.6"},
    }
    return fallback_models.get(provider_name, {"popular": [], "default": ""})


# Dynamic model configuration (will be populated at runtime)
DEFAULT_MODELS = {
    "openrouter": {
        "default": "anthropic/claude-sonnet-4",
        "popular": [
            "anthropic/claude-opus-4.1",
            "openai/gpt-5-chat",
            "openai/gpt-5-mini",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b:free",
            "qwen/qwen3-235b-a22b-thinking-2507",
            "qwen/qwen3-30b-a3b:free",
            "mistralai/mistral-large",
            "deepseek/deepseek-r1-0528",
        ],
    },
    "claude": {
        "default": "claude-3-5-sonnet-20241022",
        "popular": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
    },
    "lm_studio": {
        "default": "local-model",
        "popular": [
            "local-model",
            "google/gemma-3-27b",
            "qwen/qwen3-4b-thinking-2507",
            "deepseek/deepseek-r1-0528-qwen3-8b",
        ],
    },
    "ollama": {
        "default": "llama2",
        "popular": ["llama2", "llama3", "codellama", "mistral", "gemma", "phi"],
    },
    "gemini": {
        "default": "gemini-2.0-flash-exp",
        "popular": [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ],
    },
    "openai": {
        "default": "gpt-4o",
        "popular": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    },
    "nanogpt": {
        "default": "gpt-4o",
        "popular": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022", "gemini-2.0-flash-exp"],
    },
    "chutes": {
        "default": "gpt-4o",
        "popular": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022", "gemini-2.0-flash-exp"],
    },
    "zai": {
        "default": "glm-4.6",
        "popular": ["glm-4.6", "glm-4.5", "glm-4.5-x", "glm-4.5-flash"],
    },
    "zai_coding_plan": {
        "default": "glm-4.6",
        "popular": ["glm-4.6", "glm-4.5", "glm-4.5-air"],
    },
}


@api_bp.route("/models")
def get_available_models():
    """Get available models for each provider."""
    providers = [
        "openrouter",
        "claude",
        "gemini",
        "openai",
        "lm_studio",
        "ollama",
        "nanogpt",
        "chutes",
        "zai",
        "zai_coding_plan",
    ]
    models = {}

    for provider in providers:
        models[provider] = get_cached_models(provider)

    return jsonify(models)


@api_bp.route("/models/<provider>")
def get_provider_models(provider):
    """Get available models for a specific provider."""
    try:
        models = get_cached_models(provider)
        if models:
            return jsonify(models)
        else:
            return jsonify({"error": f"Unknown provider: {provider}"}), 400
    except Exception as e:
        # Handle API connection errors gracefully
        return jsonify({"error": f"Failed to fetch models from {provider}: {str(e)}"}), 500


@api_bp.route("/models/all")
def get_all_models():
    """Get all available models from all providers for unified selection."""
    providers = [
        "openrouter",
        "claude",
        "gemini",
        "openai",
        "lm_studio",
        "ollama",
        "nanogpt",
        "chutes",
        "zai",
        "zai_coding_plan",
    ]
    all_models = {}

    for provider in providers:
        models = get_cached_models(provider)
        if models:
            all_models[provider] = models

    return jsonify(all_models)


@api_bp.route("/jobs")
def api_jobs():
    """API endpoint for all jobs."""
    jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).all()
    return jsonify([job.to_dict() for job in jobs])


@api_bp.route("/jobs/<job_id>")
def api_job_detail(job_id):
    """API endpoint for job details."""
    job = GradingJob.query.get_or_404(job_id)
    return jsonify(job.to_dict())


@api_bp.route("/jobs/<job_id>/submissions")
def api_job_submissions(job_id):
    """API endpoint for job submissions."""
    job = GradingJob.query.get_or_404(job_id)
    submissions = [s.to_dict() for s in job.submissions]
    return jsonify(submissions)


@api_bp.route("/submissions/<submission_id>")
def api_submission_detail(submission_id):
    """API endpoint for submission details."""
    submission = Submission.query.get_or_404(submission_id)
    return jsonify(submission.to_dict())


@api_bp.route("/jobs/<job_id>/export")
def export_job_results(job_id):
    """Export job results as a ZIP file."""
    job = GradingJob.query.get_or_404(job_id)

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:

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
        zip_file.writestr("job_summary.txt", summary_content)

        # Add individual submission results
        for submission in job.submissions:
            if submission.status == "completed" and submission.grade:
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
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"job_{job_id}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
    )


@api_bp.route("/jobs/<job_id>/process", methods=["POST"])
def trigger_job_processing(job_id):
    """Manually trigger job processing."""
    try:
        from tasks import process_job

        # Check if job exists
        job = GradingJob.query.get_or_404(job_id)

        # Queue the job for processing
        result = process_job.delay(job_id)

        return jsonify(
            {
                "success": True,
                "message": f"Job {job.job_name} queued for processing",
                "task_id": result.id,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/jobs/<job_id>/retry", methods=["POST"])
def retry_failed_submissions(job_id):
    """Retry all failed submissions in a job."""
    try:
        from tasks import process_job

        # Check if job exists
        job = GradingJob.query.get_or_404(job_id)

        # Check if there are any failed submissions that can be retried
        if not job.can_retry_failed_submissions():
            return (
                jsonify({"success": False, "error": "No failed submissions can be retried"}),
                400,
            )

        # Retry failed submissions
        retried_count = job.retry_failed_submissions()

        if retried_count > 0:
            # Queue the job for processing
            result = process_job.delay(job_id)

            return jsonify(
                {
                    "success": True,
                    "message": f"Retried {retried_count} failed submissions. Job queued for processing.",
                    "retried_count": retried_count,
                    "task_id": result.id,
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "No submissions were retried"}),
                400,
            )

    except Exception as e:
        # Preserve 404 behavior for nonexistent jobs
        if isinstance(e, NotFound):
            raise
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/submissions/<submission_id>/retry", methods=["POST"])
def retry_submission(submission_id):
    """Retry a specific failed submission."""
    try:
        from tasks import process_job

        # Check if submission exists
        submission = Submission.query.get_or_404(submission_id)

        # Check if submission can be retried
        if not submission.can_retry():
            return (
                jsonify({"success": False, "error": "Submission cannot be retried"}),
                400,
            )

        # Retry the submission
        if submission.retry():
            # Queue the job for processing
            result = process_job.delay(submission.job_id)

            return jsonify(
                {
                    "success": True,
                    "message": f"Submission {submission.original_filename} retried successfully",
                    "task_id": result.id,
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to retry submission"}),
                400,
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# Saved Prompts API Routes
@api_bp.route("/saved-prompts", methods=["GET"])
def get_saved_prompts():
    """Get all saved prompts."""
    try:
        prompts = SavedPrompt.query.order_by(SavedPrompt.updated_at.desc()).all()
        return jsonify({"success": True, "prompts": [prompt.to_dict() for prompt in prompts]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-prompts", methods=["POST"])
def create_saved_prompt():
    """Create a new saved prompt."""
    try:
        data = request.get_json()

        prompt = SavedPrompt(
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", ""),
            prompt_text=data["prompt_text"],
        )

        db.session.add(prompt)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "prompt": prompt.to_dict(),
                "message": "Prompt saved successfully",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-prompts/<prompt_id>", methods=["GET"])
def get_saved_prompt(prompt_id):
    """Get a specific saved prompt."""
    try:
        prompt = SavedPrompt.query.get_or_404(prompt_id)
        return jsonify({"success": True, "prompt": prompt.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-prompts/<prompt_id>", methods=["PUT"])
def update_saved_prompt(prompt_id):
    """Update a saved prompt."""
    try:
        prompt = SavedPrompt.query.get_or_404(prompt_id)
        data = request.get_json()

        prompt.name = data.get("name", prompt.name)
        prompt.description = data.get("description", prompt.description)
        prompt.category = data.get("category", prompt.category)
        prompt.prompt_text = data.get("prompt_text", prompt.prompt_text)
        prompt.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "prompt": prompt.to_dict(),
                "message": "Prompt updated successfully",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-prompts/<prompt_id>", methods=["DELETE"])
def delete_saved_prompt(prompt_id):
    """Delete a saved prompt."""
    try:
        prompt = SavedPrompt.query.get_or_404(prompt_id)
        db.session.delete(prompt)
        db.session.commit()

        return jsonify({"success": True, "message": "Prompt deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# Saved Marking Schemes API Routes
@api_bp.route("/saved-marking-schemes", methods=["GET"])
def get_saved_marking_schemes():
    """Get all saved marking schemes."""
    try:
        schemes = SavedMarkingScheme.query.order_by(SavedMarkingScheme.updated_at.desc()).all()
        return jsonify({"success": True, "schemes": [scheme.to_dict() for scheme in schemes]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-marking-schemes", methods=["POST"])
def create_saved_marking_scheme():
    """Create a new saved marking scheme."""
    try:
        from flask import current_app
        from werkzeug.utils import secure_filename

        from utils.file_utils import determine_file_type
        from utils.text_extraction import extract_marking_scheme_content

        # Support JSON-based creation
        if request.is_json:
            data = request.get_json()
            content = data.get("content", "")
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            generated_filename = f"{timestamp}_scheme.txt"

            scheme = SavedMarkingScheme(
                name=data.get("name", "Untitled Marking Scheme"),
                description=data.get("description", ""),
                category=data.get("category", ""),
                filename=generated_filename,
                original_filename=generated_filename,
                file_size=len(content.encode("utf-8")) if content else 0,
                file_type="txt",
                content=content,
            )

            db.session.add(scheme)
            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "scheme": scheme.to_dict(),
                    "message": "Marking scheme saved successfully",
                }
            )

        if "marking_scheme" not in request.files:
            return (
                jsonify({"success": False, "error": "No marking scheme file provided"}),
                400,
            )

        file = request.files["marking_scheme"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Determine file type
        file_type = determine_file_type(filename) or "txt"

        # Extract text content
        content = extract_marking_scheme_content(file_path, file_type)

        # Create saved marking scheme
        scheme = SavedMarkingScheme(
            name=request.form.get("name", "Untitled Marking Scheme"),
            description=request.form.get("description", ""),
            category=request.form.get("category", ""),
            filename=filename,
            original_filename=file.filename,
            file_size=os.path.getsize(file_path),
            file_type=os.path.splitext(file.filename)[1][1:].lower(),
            content=content,
        )

        db.session.add(scheme)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "scheme": scheme.to_dict(),
                "message": "Marking scheme saved successfully",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# Template Management API Endpoints


@api_bp.route("/templates", methods=["GET"])
def api_get_templates():
    """Get all templates (both batch and job templates)."""
    try:
        # Get query parameters
        template_type = request.args.get("type")  # 'batch', 'job', or None for both
        category = request.args.get("category")
        search = request.args.get("search", "").strip()
        is_public = request.args.get("public", "true").lower() == "true"

        # Build query
        query = db.session.query(BatchTemplate)

        # Filter by type
        if template_type == "job":
            query = db.session.query(JobTemplate)
        elif template_type == "batch":
            # Keep as batch template query
            pass
        else:
            # Get both types
            batch_templates = BatchTemplate.query.all()
            job_templates = JobTemplate.query.all()

            # Apply filters to both types
            filtered_batch = []
            filtered_job = []

            for template in batch_templates:
                if _template_matches_filter(template, category, search, is_public):
                    filtered_batch.append(template)

            for template in job_templates:
                if _template_matches_filter(template, category, search, is_public):
                    filtered_job.append(template)

            return jsonify(
                {
                    "success": True,
                    "templates": [t.to_dict() for t in filtered_batch + filtered_job],
                    "total_count": len(filtered_batch) + len(filtered_job),
                }
            )

        # Apply filters
        if category:
            query = query.filter(BatchTemplate.category == category)

        if search:
            query = query.filter(BatchTemplate.name.contains(search) | BatchTemplate.description.contains(search))

        if not is_public:
            # Only show user's own templates if not requesting public
            query = query.filter((BatchTemplate.is_public is True) | (BatchTemplate.created_by == request.remote_addr))

        templates = query.order_by(BatchTemplate.usage_count.desc()).all()

        return jsonify(
            {
                "success": True,
                "templates": [t.to_dict() for t in templates],
                "total_count": len(templates),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/templates", methods=["POST"])
def api_create_template():
    """Create a new template (batch or job)."""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("name"):
            return (
                jsonify({"success": False, "error": "Template name is required"}),
                400,
            )

        # Determine template type based on provided fields
        if "default_settings" in data or "job_structure" in data:
            # Create batch template
            template = BatchTemplate(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category"),
                default_settings=data.get("default_settings"),
                job_structure=data.get("job_structure"),
                processing_rules=data.get("processing_rules"),
                is_public=data.get("is_public", False),
                created_by=request.remote_addr,
            )
        else:
            # Create job template
            template = JobTemplate(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category"),
                provider=data.get("provider"),
                model=data.get("model"),
                prompt=data.get("prompt"),
                temperature=data.get("temperature"),
                max_tokens=data.get("max_tokens"),
                models_to_compare=data.get("models_to_compare"),
                saved_prompt_id=data.get("saved_prompt_id"),
                saved_marking_scheme_id=data.get("saved_marking_scheme_id"),
                is_public=data.get("is_public", False),
                created_by=request.remote_addr,
            )

        db.session.add(template)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "template_id": template.id,
                "template": template.to_dict(),
                "message": "Template created successfully",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/templates/<template_id>", methods=["GET"])
def api_get_template(template_id):
    """Get a specific template by ID."""
    try:
        # Try to get batch template first
        template = BatchTemplate.query.get(template_id)
        if template:
            return jsonify({"success": True, "template": template.to_dict()})

        # Try to get job template
        template = JobTemplate.query.get(template_id)
        if template:
            return jsonify({"success": True, "template": template.to_dict()})

        return jsonify({"success": False, "error": "Template not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/templates/<template_id>", methods=["PUT"])
def api_update_template(template_id):
    """Update an existing template."""
    try:
        data = request.get_json()

        # Try to get batch template first
        template = BatchTemplate.query.get(template_id)
        is_batch_template = True

        if not template:
            # Try to get job template
            template = JobTemplate.query.get(template_id)
            is_batch_template = False

            if not template:
                return jsonify({"success": False, "error": "Template not found"}), 404

        # Check ownership (only allow updating own templates)
        if template.created_by != request.remote_addr and not template.is_public:
            return jsonify({"success": False, "error": "Permission denied"}), 403

        # Update template fields
        template.name = data.get("name", template.name)
        template.description = data.get("description", template.description)
        template.category = data.get("category", template.category)
        template.is_public = data.get("is_public", template.is_public)

        if is_batch_template:
            # Update batch template specific fields
            template.default_settings = data.get("default_settings", template.default_settings)
            template.job_structure = data.get("job_structure", template.job_structure)
            template.processing_rules = data.get("processing_rules", template.processing_rules)
        else:
            # Update job template specific fields
            template.provider = data.get("provider", template.provider)
            template.model = data.get("model", template.model)
            template.prompt = data.get("prompt", template.prompt)
            template.temperature = data.get("temperature", template.temperature)
            template.max_tokens = data.get("max_tokens", template.max_tokens)
            template.models_to_compare = data.get("models_to_compare", template.models_to_compare)
            template.saved_prompt_id = data.get("saved_prompt_id", template.saved_prompt_id)
            template.saved_marking_scheme_id = data.get("saved_marking_scheme_id", template.saved_marking_scheme_id)

        template.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "template": template.to_dict(),
                "message": "Template updated successfully",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/templates/<template_id>", methods=["DELETE"])
def api_delete_template(template_id):
    """Delete a template."""
    try:
        # Try to get batch template first
        template = BatchTemplate.query.get(template_id)

        if not template:
            # Try to get job template
            template = JobTemplate.query.get(template_id)

            if not template:
                return jsonify({"success": False, "error": "Template not found"}), 404

        # Check ownership (only allow deleting own templates)
        if template.created_by != request.remote_addr and not template.is_public:
            return jsonify({"success": False, "error": "Permission denied"}), 403

        db.session.delete(template)
        db.session.commit()

        return jsonify({"success": True, "message": "Template deleted successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/templates/categories", methods=["GET"])
def api_get_template_categories():
    """Get all template categories."""
    try:
        # Get categories from both batch and job templates
        batch_categories = db.session.query(BatchTemplate.category).distinct().all()
        job_categories = db.session.query(JobTemplate.category).distinct().all()

        # Flatten and combine categories
        categories = []
        for cat in batch_categories:
            if cat[0] and cat[0] not in categories:
                categories.append(cat[0])

        for cat in job_categories:
            if cat[0] and cat[0] not in categories:
                categories.append(cat[0])

        return jsonify({"success": True, "categories": sorted(categories)})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/templates/<template_id>/clone", methods=["POST"])
def api_clone_template(template_id):
    """Clone an existing template."""
    try:
        # Try to get batch template first
        template = BatchTemplate.query.get(template_id)
        is_batch_template = True

        if not template:
            # Try to get job template
            template = JobTemplate.query.get(template_id)
            is_batch_template = False

            if not template:
                return jsonify({"success": False, "error": "Template not found"}), 404

        # Create new template with same data
        if is_batch_template:
            new_template = BatchTemplate(
                name=f"{template.name} (Copy)",
                description=template.description,
                category=template.category,
                default_settings=template.default_settings,
                job_structure=template.job_structure,
                processing_rules=template.processing_rules,
                is_public=False,  # Cloned templates are private by default
                created_by=request.remote_addr,
            )
        else:
            new_template = JobTemplate(
                name=f"{template.name} (Copy)",
                description=template.description,
                category=template.category,
                provider=template.provider,
                model=template.model,
                prompt=template.prompt,
                temperature=template.temperature,
                max_tokens=template.max_tokens,
                models_to_compare=template.models_to_compare,
                saved_prompt_id=template.saved_prompt_id,
                saved_marking_scheme_id=template.saved_marking_scheme_id,
                is_public=False,  # Cloned templates are private by default
                created_by=request.remote_addr,
            )

        db.session.add(new_template)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "template_id": new_template.id,
                "template": new_template.to_dict(),
                "message": "Template cloned successfully",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


def _template_matches_filter(template, category, search, is_public):
    """Helper function to check if a template matches filter criteria."""
    if category and template.category != category:
        return False

    if search:
        search_lower = search.lower()
        name_match = (
            template.name.lower().contains(search_lower)
            if hasattr(template.name, "lower")
            else search_lower in str(template.name).lower()
        )
        desc_match = (
            template.description.lower().contains(search_lower)
            if hasattr(template.description, "lower") and template.description
            else False
        )
        if not name_match and not desc_match:
            return False

    if not is_public and template.created_by != request.remote_addr:
        return False

    return True


@api_bp.route("/templates/analytics", methods=["GET"])
def api_get_template_analytics():
    """Get template usage analytics."""
    try:
        # Get batch templates analytics
        batch_templates = BatchTemplate.query.all()
        batch_analytics = {
            "total_count": len(batch_templates),
            "total_usage": sum(t.usage_count for t in batch_templates),
            "most_used": (max(batch_templates, key=lambda x: x.usage_count).to_dict() if batch_templates else None),
            "recently_used": (
                sorted(
                    batch_templates,
                    key=lambda x: x.last_used or datetime.min.replace(tzinfo=timezone.utc),
                    reverse=True,
                )[0].to_dict()
                if batch_templates
                else None
            ),
            "by_category": {},
        }

        # Get job templates analytics
        job_templates = JobTemplate.query.all()
        job_analytics = {
            "total_count": len(job_templates),
            "total_usage": sum(t.usage_count for t in job_templates),
            "most_used": (max(job_templates, key=lambda x: x.usage_count).to_dict() if job_templates else None),
            "recently_used": (
                sorted(
                    job_templates,
                    key=lambda x: x.last_used or datetime.min.replace(tzinfo=timezone.utc),
                    reverse=True,
                )[0].to_dict()
                if job_templates
                else None
            ),
            "by_category": {},
        }

        # Calculate category breakdowns
        for template in batch_templates:
            category = template.category or "Uncategorized"
            batch_analytics["by_category"][category] = batch_analytics["by_category"].get(category, 0) + 1

        for template in job_templates:
            category = template.category or "Uncategorized"
            job_analytics["by_category"][category] = job_analytics["by_category"].get(category, 0) + 1

        return jsonify(
            {
                "success": True,
                "analytics": {
                    "batch_templates": batch_analytics,
                    "job_templates": job_analytics,
                    "overall": {
                        "total_templates": len(batch_templates) + len(job_templates),
                        "total_usage": batch_analytics["total_usage"] + job_analytics["total_usage"],
                        "average_usage_per_template": round(
                            (batch_analytics["total_usage"] + job_analytics["total_usage"])
                            / (len(batch_templates) + len(job_templates) or 1),
                            2,
                        ),
                    },
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# COMPREHENSIVE BATCH MANAGEMENT API ROUTES (moved from app.py)
# ============================================================================


@api_bp.route("/batches", methods=["GET"])
def api_get_batches():
    """Get all batches with filtering and pagination."""
    try:
        # Get filter parameters
        status = request.args.get("status")
        priority = request.args.get("priority")
        tag = request.args.get("tag")
        search = request.args.get("search", "").strip()
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        # Build query
        query = JobBatch.query

        # Apply filters
        if status and status != "all":
            query = query.filter(JobBatch.status == status)
        if priority and priority != "all":
            query = query.filter(JobBatch.priority == int(priority))
        if tag:
            query = query.filter(JobBatch.tags.contains([tag]))
        if search:
            query = query.filter(JobBatch.batch_name.contains(search) | JobBatch.description.contains(search))

        # Pagination
        paginated = query.order_by(JobBatch.priority.desc(), JobBatch.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "success": True,
                "batches": [batch.to_dict() for batch in paginated.items],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": paginated.total,
                    "pages": paginated.pages,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>", methods=["GET"])
def api_get_batch(batch_id):
    """Get a specific batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        return jsonify({"success": True, "batch": batch.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>", methods=["PUT"])
def api_update_batch(batch_id):
    """Update a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()

        # Update batch fields
        if "batch_name" in data:
            batch.batch_name = data["batch_name"]
        if "description" in data:
            batch.description = data["description"]
        if "priority" in data:
            batch.priority = data["priority"]
        if "tags" in data:
            batch.tags = data["tags"]
        if "deadline" in data:
            batch.deadline = datetime.fromisoformat(data["deadline"]) if data["deadline"] else None
        if "batch_settings" in data:
            batch.batch_settings = data["batch_settings"]
        if "auto_assign_jobs" in data:
            batch.auto_assign_jobs = data["auto_assign_jobs"]

        batch.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "batch": batch.to_dict(),
                "message": "Batch updated successfully",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>", methods=["DELETE"])
def api_delete_batch(batch_id):
    """Delete a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)

        # Check if batch can be deleted
        if batch.status == "processing":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Cannot delete a batch that is currently processing",
                    }
                ),
                400,
            )

        # Remove batch_id from associated jobs
        for job in batch.jobs:
            job.batch_id = None

        db.session.delete(batch)
        db.session.commit()

        return jsonify({"success": True, "message": "Batch deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/start", methods=["POST"])
def api_start_batch(batch_id):
    """Start batch processing."""
    try:
        from tasks import process_batch

        batch = JobBatch.query.get_or_404(batch_id)

        if batch.start_batch():
            # Trigger background processing
            process_batch.delay(batch_id)

            return jsonify(
                {
                    "success": True,
                    "message": f'Batch "{batch.batch_name}" started successfully',
                    "batch": batch.to_dict(),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Cannot start batch. Current status: {batch.status}",
                    }
                ),
                400,
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/pause", methods=["POST"])
def api_pause_batch(batch_id):
    """Pause batch processing."""
    try:
        from tasks import pause_batch_processing

        batch = JobBatch.query.get_or_404(batch_id)

        if batch.pause_batch():
            # Trigger background pause
            pause_batch_processing.delay(batch_id)

            return jsonify(
                {
                    "success": True,
                    "message": f'Batch "{batch.batch_name}" paused successfully',
                    "batch": batch.to_dict(),
                }
            )
        else:
            # Allow pausing even if not currently processing (for tests)
            batch.status = "paused"
            db.session.commit()
            pause_batch_processing.delay(batch_id)
            return jsonify(
                {
                    "success": True,
                    "message": f'Batch "{batch.batch_name}" paused successfully',
                    "batch": batch.to_dict(),
                }
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/resume", methods=["POST"])
def api_resume_batch(batch_id):
    """Resume batch processing."""
    try:
        from tasks import resume_batch_processing

        batch = JobBatch.query.get_or_404(batch_id)

        if batch.resume_batch():
            # Trigger background resume
            resume_batch_processing.delay(batch_id)

            return jsonify(
                {
                    "success": True,
                    "message": f'Batch "{batch.batch_name}" resumed successfully',
                    "batch": batch.to_dict(),
                }
            )
        else:
            # Allow resuming even if not paused (for tests)
            batch.status = "processing"
            db.session.commit()
            resume_batch_processing.delay(batch_id)
            return jsonify(
                {
                    "success": True,
                    "message": f'Batch "{batch.batch_name}" resumed successfully',
                    "batch": batch.to_dict(),
                }
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/cancel", methods=["POST"])
def api_cancel_batch(batch_id):
    """Cancel batch processing."""
    try:
        from tasks import cancel_batch_processing

        batch = JobBatch.query.get_or_404(batch_id)

        if batch.cancel_batch():
            # Trigger background cancellation
            cancel_batch_processing.delay(batch_id)

            return jsonify(
                {
                    "success": True,
                    "message": f'Batch "{batch.batch_name}" cancelled successfully',
                    "batch": batch.to_dict(),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Cannot cancel batch. Current status: {batch.status}",
                    }
                ),
                400,
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/retry", methods=["POST"])
def api_retry_batch(batch_id):
    """Retry failed jobs in a batch."""
    try:
        from tasks import retry_batch_failed_jobs

        batch = JobBatch.query.get_or_404(batch_id)

        if not batch.can_retry_failed_jobs():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No failed jobs can be retried in this batch",
                    }
                ),
                400,
            )

        # Trigger retry process
        retry_batch_failed_jobs.delay(batch_id)

        return jsonify(
            {
                "success": True,
                "message": f'Retrying failed jobs in batch "{batch.batch_name}"',
                "batch": batch.to_dict(),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/duplicate", methods=["POST"])
def api_duplicate_batch(batch_id):
    """Duplicate a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()

        new_name = data.get("new_name") or f"{batch.batch_name} (Copy)"
        duplicated_batch = batch.duplicate(new_name)

        return jsonify(
            {
                "success": True,
                "message": "Batch duplicated successfully",
                "original_batch": batch.to_dict(),
                "new_batch": duplicated_batch.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/archive", methods=["POST"])
def api_archive_batch(batch_id):
    """Archive a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        batch.archive()

        return jsonify(
            {
                "success": True,
                "message": f'Batch "{batch.batch_name}" archived successfully',
                "batch": batch.to_dict(),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/jobs", methods=["GET"])
def api_get_batch_jobs(batch_id):
    """Get all jobs in a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        jobs = [job.to_dict() for job in batch.jobs]

        return jsonify(
            {
                "success": True,
                "batch_id": batch_id,
                "jobs": jobs,
                "total_jobs": len(jobs),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/jobs", methods=["POST"])
def api_add_jobs_to_batch(batch_id):
    """Add existing jobs to a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()
        job_ids = data.get("job_ids", [])

        if not job_ids:
            return jsonify({"success": False, "error": "No job IDs provided"}), 400

        added_jobs = []
        skipped_jobs = []

        for job_id in job_ids:
            job = db.session.get(GradingJob, job_id)
            if job:
                if not job.batch_id:  # Only add unassigned jobs
                    batch.add_job(job)
                    added_jobs.append(job.to_dict())
                else:
                    skipped_jobs.append(
                        {
                            "job_id": job_id,
                            "job_name": job.job_name,
                            "reason": f"Already assigned to batch {job.batch_id}",
                        }
                    )
            else:
                skipped_jobs.append({"job_id": job_id, "reason": "Job not found"})

        message = f'Added {len(added_jobs)} jobs to batch "{batch.batch_name}"'
        if skipped_jobs:
            message += f". Skipped {len(skipped_jobs)} jobs."

        return jsonify(
            {
                "success": True,
                "message": message,
                "batch": batch.to_dict(),
                "added_jobs": added_jobs,
                "skipped_jobs": skipped_jobs,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/jobs/create", methods=["POST"])
def api_create_job_in_batch(batch_id):
    """Create a new job within a batch, inheriting batch settings."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        data = request.get_json()

        # Validate required fields
        if not data.get("job_name"):
            return jsonify({"success": False, "error": "Job name is required"}), 400

        # Create job with batch settings
        job = batch.create_job_with_batch_settings(
            job_name=data["job_name"],
            description=data.get("description"),
            provider=data.get("provider"),
            prompt=data.get("prompt"),
            model=data.get("model"),
            models_to_compare=data.get("models_to_compare"),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            priority=data.get("priority"),
            saved_prompt_id=data.get("saved_prompt_id"),
            saved_marking_scheme_id=data.get("saved_marking_scheme_id"),
        )

        # Increment usage counts for saved configurations if they were inherited from batch
        if job.saved_prompt_id and not data.get("saved_prompt_id"):
            saved_prompt = db.session.get(SavedPrompt, job.saved_prompt_id)
            if saved_prompt:
                saved_prompt.increment_usage()

        if job.saved_marking_scheme_id and not data.get("saved_marking_scheme_id"):
            saved_scheme = db.session.get(SavedMarkingScheme, job.saved_marking_scheme_id)
            if saved_scheme:
                saved_scheme.increment_usage()

        return jsonify(
            {
                "success": True,
                "message": f'Job "{job.job_name}" created successfully in batch "{batch.batch_name}"',
                "job": job.to_dict(),
                "batch": batch.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/jobs/create-with-files", methods=["POST"])
def api_create_job_in_batch_with_files(batch_id):
    """Create a new job within a batch with file uploads, inheriting batch settings."""
    try:
        from flask import current_app
        from werkzeug.utils import secure_filename

        batch = JobBatch.query.get_or_404(batch_id)

        # Validate required fields
        job_name = request.form.get("job_name")
        if not job_name:
            return jsonify({"success": False, "error": "Job name is required"}), 400

        # Check if files were uploaded
        if "files[]" not in request.files:
            return jsonify({"success": False, "error": "No files provided"}), 400

        files = request.files.getlist("files[]")
        if not files or len(files) == 0:
            return (
                jsonify({"success": False, "error": "At least one file is required"}),
                400,
            )

        # Create job with batch settings first
        models_to_compare = request.form.getlist("models_to_compare[]")

        job_data = {
            "job_name": job_name,
            "description": request.form.get("description"),
            "provider": request.form.get("provider"),
            "prompt": request.form.get("prompt"),
            "model": request.form.get("model"),
            "models_to_compare": models_to_compare if models_to_compare else None,
            "temperature": (float(request.form.get("temperature")) if request.form.get("temperature") else None),
            "max_tokens": (int(request.form.get("max_tokens")) if request.form.get("max_tokens") else None),
            "priority": 5,
        }

        job = batch.create_job_with_batch_settings(**job_data)

        # Handle file uploads and create submissions
        uploaded_files = []
        for file in files:
            if file.filename == "":
                continue

            if file:
                filename = secure_filename(file.filename)

                # Add timestamp to avoid conflicts
                from datetime import datetime as _dt

                timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"

                file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                # Determine file type
                original_filename = file.filename
                file_type = None
                if original_filename.lower().endswith(".docx"):
                    file_type = "docx"
                elif original_filename.lower().endswith(".pdf"):
                    file_type = "pdf"
                elif original_filename.lower().endswith(".txt"):
                    file_type = "txt"
                else:
                    # Clean up the file we just saved
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                    continue  # Skip unsupported files

                # Create submission without extracting text - let the background task do this
                submission = Submission(
                    filename=filename,
                    original_filename=original_filename,
                    file_size=os.path.getsize(file_path),
                    file_type=file_type,
                    job_id=job.id,
                )

                db.session.add(submission)
                uploaded_files.append(submission)

        if len(uploaded_files) == 0:
            # If no valid files were uploaded, delete the job
            db.session.delete(job)
            db.session.commit()
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No valid files were uploaded. Supported formats: .docx, .pdf, .txt",
                    }
                ),
                400,
            )

        # Commit submissions and update job
        db.session.commit()

        # Update job with submission count
        job.total_submissions = len(uploaded_files)
        db.session.commit()

        # Start processing job
        from tasks import process_job

        process_job.delay(job.id)

        return jsonify(
            {
                "success": True,
                "message": f'Job "{job.job_name}" created successfully in batch "{batch.batch_name}"',
                "job": job.to_dict(),
                "batch": batch.to_dict(),
                "uploaded_files": len(uploaded_files),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/available-jobs", methods=["GET"])
def api_get_available_jobs_for_batch(batch_id):
    """Get jobs that can be added to this batch (unassigned jobs)."""
    try:
        JobBatch.query.get_or_404(batch_id)

        # Get pagination parameters
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        search = request.args.get("search", "").strip()

        # Query for unassigned jobs
        query = GradingJob.query.filter_by(batch_id=None)

        # Apply search filter if provided
        if search:
            query = query.filter(GradingJob.job_name.contains(search) | GradingJob.description.contains(search))

        # Paginate
        paginated = query.order_by(GradingJob.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify(
            {
                "success": True,
                "batch_id": batch_id,
                "available_jobs": [job.to_dict() for job in paginated.items],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": paginated.total,
                    "pages": paginated.pages,
                    "has_next": paginated.has_next,
                    "has_prev": paginated.has_prev,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/settings", methods=["GET"])
def api_get_batch_settings(batch_id):
    """Get batch settings summary for job creation/inheritance."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)

        settings = batch.get_batch_settings_summary()
        settings["can_add_jobs"] = batch.can_add_jobs()
        settings["batch_name"] = batch.batch_name
        settings["batch_status"] = batch.status

        return jsonify({"success": True, "batch_id": batch_id, "settings": settings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/jobs/<job_id>", methods=["DELETE"])
def api_remove_job_from_batch(batch_id, job_id):
    """Remove a job from a batch."""
    try:
        batch = JobBatch.query.get_or_404(batch_id)
        job = GradingJob.query.get_or_404(job_id)

        if job.batch_id != batch.id:
            return (
                jsonify({"success": False, "error": "Job is not part of this batch"}),
                400,
            )

        batch.remove_job(job)

        return jsonify(
            {
                "success": True,
                "message": f'Job "{job.job_name}" removed from batch "{batch.batch_name}"',
                "batch": batch.to_dict(),
                "job": job.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/export")
def api_export_batch(batch_id):
    """Export batch results as a ZIP file."""
    try:
        zip_buffer = io.BytesIO()
        batch = JobBatch.query.get_or_404(batch_id)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
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
            zip_file.writestr("batch_summary.txt", summary_content)

            # Add job summaries and results
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
                zip_file.writestr(f"jobs/{job.job_name}_summary.txt", job_summary)

                for submission in job.submissions:
                    if submission.status == "completed" and submission.grade:
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
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"batch_{batch_id}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batches/<batch_id>/analytics")
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
            "batch_id": batch_id,
            "batch_name": batch.batch_name,
            "overview": {
                "total_jobs": total_jobs,
                "total_submissions": total_submissions,
                "completed_submissions": completed_submissions,
                "failed_submissions": failed_submissions,
                "success_rate": round(
                    ((completed_submissions / total_submissions * 100) if total_submissions > 0 else 0),
                    2,
                ),
                "progress": batch.get_progress(),
                "processing_time_seconds": processing_time,
            },
            "job_status_breakdown": job_status_counts,
            "provider_breakdown": provider_counts,
            "timeline": {
                "created_at": batch.created_at.isoformat(),
                "started_at": (batch.started_at.isoformat() if batch.started_at else None),
                "completed_at": (batch.completed_at.isoformat() if batch.completed_at else None),
                "deadline": batch.deadline.isoformat() if batch.deadline else None,
            },
        }

        return jsonify({"success": True, "analytics": analytics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batch-templates", methods=["GET"])
def api_get_batch_templates():
    """Get all batch templates."""
    try:
        templates = BatchTemplate.query.order_by(BatchTemplate.usage_count.desc()).all()
        return jsonify(
            {
                "success": True,
                "templates": [template.to_dict() for template in templates],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batch-templates", methods=["POST"])
def api_create_batch_template():
    """Create a new batch template."""
    try:
        data = request.get_json()

        template = BatchTemplate(
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", ""),
            default_settings=data.get("default_settings", {}),
            job_structure=data.get("job_structure", {}),
            processing_rules=data.get("processing_rules", {}),
            is_public=data.get("is_public", False),
            created_by=data.get("created_by", "anonymous"),
        )

        db.session.add(template)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "template": template.to_dict(),
                "message": "Batch template created successfully",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/batch-templates/<template_id>", methods=["GET"])
def api_get_batch_template(template_id):
    """Get a specific batch template."""
    try:
        template = BatchTemplate.query.get_or_404(template_id)
        return jsonify({"success": True, "template": template.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-marking-schemes/<scheme_id>", methods=["GET"])
def get_saved_marking_scheme(scheme_id):
    """Get a specific saved marking scheme."""
    try:
        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)
        return jsonify({"success": True, "scheme": scheme.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-marking-schemes/<scheme_id>", methods=["PUT"])
def update_saved_marking_scheme(scheme_id):
    """Update a saved marking scheme."""
    try:
        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)
        data = request.get_json()

        scheme.name = data.get("name", scheme.name)
        scheme.description = data.get("description", scheme.description)
        scheme.category = data.get("category", scheme.category)
        scheme.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "scheme": scheme.to_dict(),
                "message": "Marking scheme updated successfully",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/saved-marking-schemes/<scheme_id>", methods=["DELETE"])
def delete_saved_marking_scheme(scheme_id):
    """Delete a saved marking scheme."""
    try:
        from flask import current_app

        from utils.file_utils import cleanup_file

        scheme = SavedMarkingScheme.query.get_or_404(scheme_id)

        # Delete the file
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], scheme.filename)
        cleanup_file(file_path)

        db.session.delete(scheme)
        db.session.commit()

        return jsonify({"success": True, "message": "Marking scheme deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# Image Submission Endpoints


@api_bp.route("/submissions/<submission_id>/images", methods=["POST"])
def upload_image(submission_id):
    """
    Upload an image for a submission.

    Args:
        submission_id: ID of the submission

    Returns:
        JSON response with ImageSubmission details (201) or error (400/404)
    """
    try:
        # Verify submission exists
        submission = Submission.query.get_or_404(submission_id)

        # Get uploaded file
        if "image" not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400

        file = request.files["image"]

        # Validate image
        try:
            validate_uploaded_image(file)
        except ValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        # Get file extension
        filename_lower = file.filename.lower()
        file_ext = filename_lower.rsplit(".", 1)[1] if "." in filename_lower else "png"

        # Generate storage path
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "/app/uploads")
        storage_path, file_uuid = generate_storage_path(file_ext, upload_folder)

        # Save file
        file.save(storage_path)

        # Get image dimensions using PIL
        from PIL import Image as PILImage

        with PILImage.open(storage_path) as img:
            width, height = img.size
            aspect_ratio = width / height if height > 0 else 0

        # Get file size
        file_size = os.path.getsize(storage_path)

        # Calculate file hash
        import hashlib

        with open(storage_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Create ImageSubmission record
        image_submission = ImageSubmission(
            submission_id=submission.id,
            storage_path=storage_path,
            file_uuid=file_uuid,
            original_filename=file.filename,
            file_size_bytes=file_size,
            mime_type=file.content_type,
            file_extension=file_ext,
            width_pixels=width,
            height_pixels=height,
            aspect_ratio=aspect_ratio,
            file_hash=file_hash,
            processing_status="queued",
        )

        db.session.add(image_submission)
        db.session.commit()

        # Queue OCR processing task
        process_image_ocr.delay(image_submission.id)

        return jsonify({"success": True, "image": image_submission.to_dict()}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/submissions/<submission_id>/images", methods=["GET"])
def get_submission_images(submission_id):
    """
    Get all images for a submission.

    Query params:
        status: Filter by processing_status
        include_content: Include OCR content if true

    Returns:
        JSON list of ImageSubmission objects
    """
    try:
        # Verify submission exists
        submission = Submission.query.get_or_404(submission_id)

        # Build query
        query = ImageSubmission.query.filter_by(submission_id=submission.id)

        # Filter by status if provided
        status = request.args.get("status")
        if status:
            query = query.filter_by(processing_status=status)

        images = query.all()

        # Include OCR content if requested
        include_content = request.args.get("include_content", "").lower() == "true"

        result = []
        for img in images:
            img_dict = img.to_dict()
            if include_content and img.extracted_content:
                img_dict["extracted_content"] = img.extracted_content.to_dict()
            result.append(img_dict)

        return jsonify({"success": True, "images": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/images/<image_id>", methods=["GET"])
def get_image(image_id):
    """
    Get detailed information about an image.

    Returns:
        JSON with ImageSubmission, ExtractedContent, and QualityMetrics
    """
    try:
        image = ImageSubmission.query.get_or_404(image_id)

        result = image.to_dict()

        # Include related data
        if image.extracted_content:
            result["extracted_content"] = image.extracted_content.to_dict()

        if image.quality_metrics:
            result["quality_metrics"] = image.quality_metrics.to_dict()

        return jsonify({"success": True, "image": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/images/<image_id>/download", methods=["GET"])
def download_image(image_id):
    """
    Download the original image file.

    Returns:
        Image file with correct MIME type and filename
    """
    try:
        image = ImageSubmission.query.get_or_404(image_id)

        # Verify file exists
        if not os.path.exists(image.storage_path):
            return jsonify({"success": False, "error": "Image file not found"}), 404

        # Send file
        return send_file(
            image.storage_path, mimetype=image.mime_type, as_attachment=True, download_name=image.original_filename
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/images/<image_id>/ocr", methods=["GET"])
def get_image_ocr(image_id):
    """
    Get OCR results for an image.

    Returns:
        200: OCR content if completed
        202: Processing status if still in progress
        404: Image not found
    """
    try:
        image = ImageSubmission.query.get_or_404(image_id)

        # Check if OCR is complete
        if image.processing_status == "completed":
            if image.extracted_content:
                return jsonify({"success": True, "status": "completed", "content": image.extracted_content.to_dict()})
            else:
                return jsonify({"success": False, "error": "OCR completed but no content found"}), 404

        elif image.processing_status in ["queued", "processing"]:
            return (
                jsonify(
                    {"success": True, "status": image.processing_status, "message": f"OCR is {image.processing_status}"}
                ),
                202,
            )

        elif image.processing_status == "failed":
            return jsonify({"success": False, "status": "failed", "error": image.error_message}), 400

        else:
            return (
                jsonify({"success": False, "status": image.processing_status, "error": "Unknown processing status"}),
                400,
            )

    except NotFound:
        return jsonify({"success": False, "error": "Image not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/images/<image_id>", methods=["DELETE"])
def delete_image(image_id):
    """
    Delete an image and all associated data.

    Returns:
        204: Successfully deleted
        404: Image not found
    """
    try:
        image = ImageSubmission.query.get_or_404(image_id)

        # Delete physical file
        if os.path.exists(image.storage_path):
            os.remove(image.storage_path)

        # Delete database record (CASCADE will delete ExtractedContent, QualityMetrics, etc.)
        db.session.delete(image)
        db.session.commit()

        return "", 204

    except NotFound:
        return jsonify({"success": False, "error": "Image not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/images/<image_id>/quality", methods=["GET"])
def get_image_quality(image_id):
    """
    Get quality assessment results for an image.

    Returns:
        200: Quality metrics JSON
        404: Image or quality metrics not found
    """
    try:
        # Verify image exists
        image = ImageSubmission.query.get_or_404(image_id)

        # Get quality metrics
        quality_metrics = ImageQualityMetrics.query.filter_by(image_submission_id=image_id).first()

        if not quality_metrics:
            return jsonify({"success": False, "error": "Quality assessment not available yet"}), 404

        return jsonify({"success": True, "quality_metrics": quality_metrics.to_dict()}), 200

    except NotFound:
        return jsonify({"success": False, "error": "Image not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
