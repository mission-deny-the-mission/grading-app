"""
File upload routes for the grading application.
Handles file uploads, marking scheme uploads, and bulk uploads.
"""

import os

from flask import Blueprint, jsonify, request, session
from werkzeug.utils import secure_filename

from models import GradingJob, MarkingScheme, Submission, GradingScheme, db
from utils.file_utils import cleanup_file, determine_file_type
from utils.llm_providers import get_llm_provider
from utils.text_extraction import (
    extract_marking_scheme_content,
    extract_text_by_file_type,
)

upload_bp = Blueprint("upload", __name__)


# DEFAULT_MODELS configuration (shared from main app)
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


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload and grading."""
    from flask import current_app

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Handle marking scheme upload if provided
    marking_scheme_content = None
    if "marking_scheme" in request.files and request.files["marking_scheme"].filename != "":
        marking_scheme_file = request.files["marking_scheme"]
        marking_scheme_filename = secure_filename(marking_scheme_file.filename)
        marking_scheme_path = os.path.join(current_app.config["UPLOAD_FOLDER"], marking_scheme_filename)
        marking_scheme_file.save(marking_scheme_path)

        # Determine marking scheme file type
        marking_scheme_type = determine_file_type(marking_scheme_filename)
        if not marking_scheme_type:
            return (
                jsonify({"error": "Unsupported marking scheme file type. Please upload .docx, .pdf, or .txt files."}),
                400,
            )

        # Extract marking scheme content
        marking_scheme_content = extract_marking_scheme_content(marking_scheme_path, marking_scheme_type)

        # Clean up marking scheme file
        cleanup_file(marking_scheme_path)

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Determine file type
        file_type = determine_file_type(filename)
        if not file_type:
            return (
                jsonify({"error": "Unsupported file type. Please upload .docx, .pdf, or .txt files."}),
                400,
            )

        # Extract text based on file type
        text = extract_text_by_file_type(file_path, file_type)

        if text.startswith("Error reading"):
            return jsonify({"error": text}), 400

        # Get grading parameters
        prompt = request.form.get(
            "prompt",
            session.get(
                "default_prompt",
                "Please grade this document and provide detailed feedback.",
            ),
        )
        provider = request.form.get("provider", "openrouter")

        # Temperature and max_tokens (parse from the form, fall back to sensible defaults)
        try:
            temperature = float(request.form.get("temperature", session.get("temperature", 0.3) or 0.3))
        except Exception:
            temperature = 0.3
        try:
            max_tokens = int(request.form.get("max_tokens", session.get("max_tokens", 2000) or 2000))
        except Exception:
            max_tokens = 2000

        # Handle model selection from dropdown
        model_select = request.form.get("modelSelect", "default").strip()
        custom_model_input = request.form.get("customModel", "").strip()

        # Determine the selected model (handle custom vs dropdown)
        if model_select == "custom":
            custom_model = custom_model_input
        elif model_select == "default":
            custom_model = ""
        else:
            custom_model = model_select

        # Helper to ensure entries are provider-prefixed (short provider key)
        def _ensure_prefixed(model_entry, default_provider_short):
            if not model_entry:
                return None
            model_entry = model_entry.strip()
            if ":" in model_entry:
                return model_entry
            return f"{default_provider_short}:{model_entry}"

        # Collect requested comparison models (may be provider-prefixed 'provider:model' or plain model names)
        models_to_compare = request.form.getlist("models_to_compare[]")
        custom_models = request.form.getlist("customModels[]") or []

        selected_provider_short = provider  # e.g., 'openrouter', 'claude', etc.

        # Add custom models to the comparison list (prefix when necessary)
        for cm in custom_models:
            if cm and cm.strip():
                models_to_compare.append(_ensure_prefixed(cm.strip(), selected_provider_short))

        # If no specific models selected, use default behavior
        if not models_to_compare:
            if custom_model:
                models_to_compare = [_ensure_prefixed(custom_model, selected_provider_short)]
            else:
                # Use configured default model for the provider, fallback to hardcoded defaults
                try:
                    from models import Config

                    config = Config.get_or_create()
                    configured_default = config.get_default_model(provider)
                except Exception:
                    configured_default = DEFAULT_MODELS.get(provider, {}).get(
                        "default", "anthropic/claude-3-5-sonnet-20241022"
                    )

                # configured_default may or may not include a provider prefix. If it doesn't, prefix with selected provider.
                if ":" in configured_default:
                    models_to_compare = [configured_default]
                else:
                    models_to_compare = [_ensure_prefixed(configured_default, selected_provider_short)]

        results = []
        all_successful = True

        # Helper to map short provider token to canonical provider name used by get_llm_provider
        def _canonical_provider(short_key):
            mapping = {
                "openrouter": "OpenRouter",
                "claude": "Claude",
                "lm_studio": "LM Studio",
                "ollama": "Ollama",
                "gemini": "Gemini",
                "openai": "OpenAI",
                "nanogpt": "NanoGPT",
                "chutes": "Chutes",
                "zai": "Z.AI",
                "zai_coding_plan": "Z.AI Coding Plan",
            }
            if not short_key:
                return None
            return mapping.get(short_key.lower(), short_key.title())

        # Grade with each selected model specification (supports cross-provider comparison)
        for spec in models_to_compare:
            if not spec:
                continue
            if ":" in spec:
                prov_short, model_name = spec.split(":", 1)
            else:
                prov_short, model_name = selected_provider_short, spec
            prov_canonical = _canonical_provider(prov_short)

            try:
                llm_provider = get_llm_provider(prov_canonical)
            except ValueError as e:
                return (
                    jsonify({"error": f'Unsupported provider in model spec "{spec}": {str(e)}'}),
                    400,
                )

            # Provider-specific API key checks (fail fast with helpful message)
            if prov_canonical == "OpenRouter":
                if not os.getenv("OPENROUTER_API_KEY"):
                    return (
                        jsonify(
                            {
                                "error": "OpenRouter API key not configured. Please configure your API key in the settings."
                            }
                        ),
                        400,
                    )
            elif prov_canonical == "Claude":
                if not os.getenv("CLAUDE_API_KEY"):
                    return (
                        jsonify(
                            {"error": "Claude API key not configured. Please configure your API key in the settings."}
                        ),
                        400,
                    )
            elif prov_canonical == "Gemini":
                if not os.getenv("GEMINI_API_KEY"):
                    return (
                        jsonify(
                            {"error": "Gemini API key not configured. Please configure your API key in the settings."}
                        ),
                        400,
                    )
            elif prov_canonical == "OpenAI":
                if not os.getenv("OPENAI_API_KEY"):
                    return (
                        jsonify(
                            {"error": "OpenAI API key not configured. Please configure your API key in the settings."}
                        ),
                        400,
                    )
            elif prov_canonical == "NanoGPT":
                if not os.getenv("NANOGPT_API_KEY"):
                    return (
                        jsonify(
                            {"error": "NanoGPT API key not configured. Please configure your API key in the settings."}
                        ),
                        400,
                    )
            elif prov_canonical == "Chutes":
                if not os.getenv("CHUTES_API_KEY"):
                    return (
                        jsonify(
                            {"error": "Chutes API key not configured. Please configure your API key in the settings."}
                        ),
                        400,
                    )
            elif prov_canonical == "Z.AI":
                if not os.getenv("ZAI_API_KEY"):
                    return (
                        jsonify(
                            {"error": "Z.AI API key not configured. Please configure your API key in the settings."}
                        ),
                        400,
                    )
            elif prov_canonical == "Z.AI Coding Plan":
                if not os.getenv("ZAI_API_KEY"):
                    return (
                        jsonify(
                            {
                                "error": "Z.AI Coding Plan API key not configured. Please configure your API key in the settings."
                            }
                        ),
                        400,
                    )

            try:
                # Call provider with the specific model name
                result = llm_provider.grade_document(
                    text,
                    prompt,
                    model_name,
                    marking_scheme_content,
                    temperature,
                    max_tokens,
                )
            except Exception as e:
                return (
                    jsonify({"error": f"Provider error for {prov_canonical}: {str(e)}"}),
                    400,
                )

            results.append(result)
            if not result.get("success", False):
                all_successful = False

        # Clean up uploaded file
        cleanup_file(file_path)

        # Return results
        if len(results) == 1:
            # Single result - return in original format for backward compatibility
            result = results[0]
            if not result.get("success", False):
                return (
                    jsonify({"error": result.get("error", "Unknown error occurred during grading")}),
                    500,
                )
            return jsonify(result)
        else:
            # Multiple results - return comparison format
            return jsonify(
                {
                    "success": all_successful,
                    "comparison": True,
                    "results": results,
                    "total_models": len(models_to_compare),
                    "successful_models": len([r for r in results if r.get("success", False)]),
                }
            )


@upload_bp.route("/upload_marking_scheme", methods=["POST"])
def upload_marking_scheme():
    """Handle marking scheme upload."""
    from flask import current_app

    try:
        if "marking_scheme" not in request.files:
            return jsonify({"error": "No marking scheme file provided"}), 400

        file = request.files["marking_scheme"]
        if file.filename == "":
            return jsonify({"error": "No marking scheme file selected"}), 400

        # Validate file type
        filename = secure_filename(file.filename)
        file_type = determine_file_type(filename)
        if not file_type:
            return (
                jsonify({"error": "Unsupported file type. Please upload .docx, .pdf, or .txt files."}),
                400,
            )

        # Save file temporarily
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Extract content
        content = extract_marking_scheme_content(file_path, file_type)

        # Create marking scheme record
        marking_scheme = MarkingScheme(
            name=request.form.get("name", filename),
            description=request.form.get("description", ""),
            filename=filename,
            original_filename=file.filename,
            file_size=os.path.getsize(file_path),
            file_type=file_type,
            content=content,
        )

        db.session.add(marking_scheme)
        db.session.commit()

        # Clean up temporary file
        cleanup_file(file_path)

        return jsonify(
            {
                "success": True,
                "marking_scheme_id": marking_scheme.id,
                "name": marking_scheme.name,
                "message": "Marking scheme uploaded successfully",
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@upload_bp.route("/upload_bulk", methods=["POST"])
def upload_bulk():
    """Handle bulk file upload and create submissions."""
    from flask import current_app

    try:
        if "files[]" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files[]")
        job_id = request.form.get("job_id")
        job_template_id = request.form.get("job_template_id")  # Track template usage

        # If no job provided, create one from form data
        if not job_id:
            job = GradingJob(
                job_name=request.form.get("job_name", "Bulk Upload Job"),
                description=request.form.get("description", ""),
                provider=request.form.get("provider", "openrouter"),
                prompt=request.form.get(
                    "prompt",
                    session.get("default_prompt", "Please grade these documents."),
                ),
                model=request.form.get("customModel") or None,
                temperature=float(request.form.get("temperature", "0.3")),
                max_tokens=int(request.form.get("max_tokens", "2000")),
                scheme_id=request.form.get("scheme_id"),
            )
            db.session.add(job)
            db.session.commit()

            # Track template usage if a template was used
            if job_template_id:
                from models import JobTemplate

                template = JobTemplate.query.get(job_template_id)
                if template:
                    template.increment_usage()
        else:
            job = GradingJob.query.get_or_404(job_id)

        uploaded_files = []
        for file in files:
            if file.filename == "":
                continue

            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)

                # Determine file type
                file_type = determine_file_type(filename) or "pdf"  # Default to PDF for unknown types

                # Create submission
                submission = Submission(
                    filename=filename,
                    original_filename=file.filename,
                    file_size=os.path.getsize(file_path),
                    file_type=file_type,
                    job_id=job.id,
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

        return jsonify(
            {
                "success": True,
                "message": f"Uploaded {len(uploaded_files)} files",
                "job_id": job.id,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 400
