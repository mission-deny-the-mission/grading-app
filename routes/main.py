"""
Main page routes for the grading application.
Handles index, jobs, config, and other main navigation routes.
"""

import os
from datetime import datetime, timezone

import openai
import requests
from anthropic import Anthropic
from flask import Blueprint, jsonify, render_template, request, session

from models import (
    Config,
    GradingJob,
    ImageSubmission,
    SavedMarkingScheme,
    SavedPrompt,
    Submission,
    db,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Main page with upload form and configuration."""
    default_prompt_text = (
        "Please grade this document and provide detailed feedback on:\n"
        "1. Content quality and relevance\n"
        "2. Structure and organization\n"
        "3. Writing style and clarity\n"
        "4. Grammar and mechanics\n"
        "5. Overall assessment with specific suggestions for improvement\n\n"
        "Please provide a comprehensive evaluation with specific examples from the text."
    )
    default_prompt = session.get("default_prompt", default_prompt_text)
    return render_template("index.html", default_prompt=default_prompt)


@main_bp.route("/config")
def config():
    """Configuration page for API keys and settings."""
    try:
        # Get config from database
        config = Config.get_or_create()
        return render_template("config.html", config=config)
    except Exception:
        # Fallback to empty config if database fails
        return render_template("config.html", config=None)


@main_bp.route("/save_config", methods=["POST"])
def save_config():
    """Save configuration settings."""
    try:
        from utils.llm_providers import validate_api_key_format

        # Get or create config record
        config = Config.get_or_create()

        # Validate API key formats before saving
        api_key_fields = {
            "openrouter": "openrouter_api_key",
            "claude": "claude_api_key",
            "gemini": "gemini_api_key",
            "openai": "openai_api_key",
            "nanogpt": "nanogpt_api_key",
            "chutes": "chutes_api_key",
            "zai": "zai_api_key",
        }

        validation_errors = []
        for provider, form_field in api_key_fields.items():
            key = request.form.get(form_field, "").strip()
            if key:  # Only validate if key is provided
                is_valid, error = validate_api_key_format(provider, key)
                if not is_valid:
                    validation_errors.append(error)

        # Return validation errors if any
        if validation_errors:
            return jsonify(
                {"success": False, "message": "Validation failed: " + "; ".join(validation_errors)}
            )

        # Update all fields from form
        config.openrouter_api_key = request.form.get("openrouter_api_key", "").strip() or None
        config.claude_api_key = request.form.get("claude_api_key", "").strip() or None
        config.gemini_api_key = request.form.get("gemini_api_key", "").strip() or None
        config.openai_api_key = request.form.get("openai_api_key", "").strip() or None
        config.nanogpt_api_key = request.form.get("nanogpt_api_key", "").strip() or None
        config.chutes_api_key = request.form.get("chutes_api_key", "").strip() or None
        config.zai_api_key = request.form.get("zai_api_key", "").strip() or None
        config.lm_studio_url = request.form.get("lm_studio_url", "http://localhost:1234/v1").strip()
        config.ollama_url = request.form.get("ollama_url", "http://localhost:11434").strip()
        config.default_prompt = request.form.get("default_prompt", "").strip() or None
        config.zai_pricing_plan = request.form.get("zai_pricing_plan", "normal").strip() or "normal"

        # Update default model configurations
        config.openrouter_default_model = request.form.get("openrouter_default_model", "").strip() or None
        config.claude_default_model = request.form.get("claude_default_model", "").strip() or None
        config.gemini_default_model = request.form.get("gemini_default_model", "").strip() or None
        config.openai_default_model = request.form.get("openai_default_model", "").strip() or None
        config.nanogpt_default_model = request.form.get("nanogpt_default_model", "").strip() or None
        config.chutes_default_model = request.form.get("chutes_default_model", "").strip() or None
        config.zai_default_model = request.form.get("zai_default_model", "").strip() or None
        config.lm_studio_default_model = request.form.get("lm_studio_default_model", "").strip() or None
        config.ollama_default_model = request.form.get("ollama_default_model", "").strip() or None

        # Save to database
        db.session.commit()

        # Save to session for immediate use (backward compatibility)
        session["default_prompt"] = config.default_prompt

        return jsonify({"success": True, "message": "Configuration saved successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Failed to save configuration: {str(e)}"})


@main_bp.route("/load_config", methods=["GET"])
def load_config():
    """Load current configuration from database with environment variable fallback."""
    try:
        # Get config from database
        config = Config.get_or_create()

        # Use database values with environment variable fallbacks
        config_data = {
            "openrouter_api_key": config.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", ""),
            "claude_api_key": config.claude_api_key or os.getenv("CLAUDE_API_KEY", ""),
            "gemini_api_key": config.gemini_api_key or os.getenv("GEMINI_API_KEY", ""),
            "openai_api_key": config.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
            "nanogpt_api_key": config.nanogpt_api_key or os.getenv("NANOGPT_API_KEY", ""),
            "chutes_api_key": config.chutes_api_key or os.getenv("CHUTES_API_KEY", ""),
            "zai_api_key": config.zai_api_key or os.getenv("ZAI_API_KEY", ""),
            "zai_pricing_plan": config.zai_pricing_plan or "normal",
            "lm_studio_url": config.lm_studio_url or os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
            "ollama_url": config.ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434"),
            "default_prompt": config.default_prompt
            or "Please grade this document and provide detailed feedback on:\n1. Content quality and relevance\n2. Structure and organization\n3. Writing style and clarity\n4. Grammar and mechanics\n5. Overall assessment with specific suggestions for improvement\n\nPlease provide a comprehensive evaluation with specific examples from the text.",
            # Default model configurations
            "openrouter_default_model": config.openrouter_default_model or "",
            "claude_default_model": config.claude_default_model or "",
            "gemini_default_model": config.gemini_default_model or "",
            "openai_default_model": config.openai_default_model or "",
            "nanogpt_default_model": config.nanogpt_default_model or "",
            "chutes_default_model": config.chutes_default_model or "",
            "zai_default_model": config.zai_default_model or "",
            "lm_studio_default_model": config.lm_studio_default_model or "",
            "ollama_default_model": config.ollama_default_model or "",
        }
        return jsonify(config_data)
    except Exception:
        # Fallback to environment variables if database fails
        config_data = {
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "nanogpt_api_key": os.getenv("NANOGPT_API_KEY", ""),
            "chutes_api_key": os.getenv("CHUTES_API_KEY", ""),
            "zai_api_key": os.getenv("ZAI_API_KEY", ""),
            "lm_studio_url": os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
            "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
            "default_prompt": (
                "Please grade this document and provide detailed feedback on:\n"
                "1. Content quality and relevance\n"
                "2. Structure and organization\n"
                "3. Writing style and clarity\n"
                "4. Grammar and mechanics\n"
                "5. Overall assessment with specific suggestions for improvement\n\n"
                "Please provide a comprehensive evaluation with specific examples from the text."
            ),
            # Default model configurations (empty for fallback)
            "openrouter_default_model": "",
            "claude_default_model": "",
            "gemini_default_model": "",
            "openai_default_model": "",
            "lm_studio_default_model": "",
            "ollama_default_model": "",
        }
        return jsonify(config_data)


@main_bp.route("/export_config", methods=["GET"])
def export_config():
    """Export configuration as JSON with metadata (T059, T060)."""
    try:
        from utils.llm_providers import validate_api_key_format

        # Get config from database
        config = Config.get_or_create()

        # Build complete export with all fields
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "warning": "This file contains sensitive API keys. Protect it accordingly.",
            # API Keys (decrypted from database)
            "openrouter_api_key": config.openrouter_api_key or "",
            "claude_api_key": config.claude_api_key or "",
            "gemini_api_key": config.gemini_api_key or "",
            "openai_api_key": config.openai_api_key or "",
            "nanogpt_api_key": config.nanogpt_api_key or "",
            "chutes_api_key": config.chutes_api_key or "",
            "zai_api_key": config.zai_api_key or "",
            # URLs
            "lm_studio_url": config.lm_studio_url or "http://localhost:1234/v1",
            "ollama_url": config.ollama_url or "http://localhost:11434",
            # Default Models
            "openrouter_default_model": config.openrouter_default_model or "",
            "claude_default_model": config.claude_default_model or "",
            "gemini_default_model": config.gemini_default_model or "",
            "openai_default_model": config.openai_default_model or "",
            "nanogpt_default_model": config.nanogpt_default_model or "",
            "chutes_default_model": config.chutes_default_model or "",
            "zai_default_model": config.zai_default_model or "",
            "lm_studio_default_model": config.lm_studio_default_model or "",
            "ollama_default_model": config.ollama_default_model or "",
            # Other Settings
            "default_prompt": config.default_prompt or (
                "Please grade this document and provide detailed feedback on:\n"
                "1. Content quality and relevance\n"
                "2. Structure and organization\n"
                "3. Writing style and clarity\n"
                "4. Grammar and mechanics\n"
                "5. Overall assessment with specific suggestions for improvement\n\n"
                "Please provide a comprehensive evaluation with specific examples from the text."
            ),
            "zai_pricing_plan": config.zai_pricing_plan or "normal",
        }
        return jsonify(export_data)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to export configuration: {str(e)}"}), 500


@main_bp.route("/import_config", methods=["POST"])
def import_config():
    """Import configuration from JSON (T061, T062, T063, T064)."""
    try:
        from utils.llm_providers import validate_api_key_format

        # Parse JSON from request
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # T062: Validate version field is present and correct
        if "version" not in data:
            return jsonify({"success": False, "error": "Missing required field: version"}), 400

        if data.get("version") != "1.0":
            return jsonify({
                "success": False,
                "error": f"Unsupported configuration version: {data.get('version')}"
            }), 400

        # Validate all provided data
        validation_errors = []

        # T063: API key format validation
        api_key_fields = {
            "openrouter": "openrouter_api_key",
            "claude": "claude_api_key",
            "gemini": "gemini_api_key",
            "openai": "openai_api_key",
            "nanogpt": "nanogpt_api_key",
            "chutes": "chutes_api_key",
            "zai": "zai_api_key",
        }

        for provider, field in api_key_fields.items():
            if field in data and data[field]:
                is_valid, error = validate_api_key_format(provider, data[field])
                if not is_valid:
                    validation_errors.append(error)

        # T064: URL format validation
        url_fields = ["lm_studio_url", "ollama_url"]
        for field in url_fields:
            if field in data and data[field]:
                url = data[field]
                if not (url.startswith("http://") or url.startswith("https://")):
                    validation_errors.append(f"{field} must start with http:// or https://")

        # Return validation errors if any
        if validation_errors:
            return jsonify({
                "success": False,
                "error": "Configuration validation failed",
                "validation_errors": validation_errors
            }), 400

        # Get or create config
        config = Config.get_or_create()

        # Apply all fields (only update provided ones)
        fields_updated = 0

        # API Keys
        for provider, field in api_key_fields.items():
            if field in data:
                setattr(config, field, data[field] or None)
                fields_updated += 1

        # URLs
        if "lm_studio_url" in data:
            config.lm_studio_url = data["lm_studio_url"] or None
            fields_updated += 1
        if "ollama_url" in data:
            config.ollama_url = data["ollama_url"] or None
            fields_updated += 1

        # Default Models
        model_fields = [
            "openrouter_default_model",
            "claude_default_model",
            "gemini_default_model",
            "openai_default_model",
            "nanogpt_default_model",
            "chutes_default_model",
            "zai_default_model",
            "lm_studio_default_model",
            "ollama_default_model",
        ]
        for field in model_fields:
            if field in data:
                setattr(config, field, data[field] or None)
                fields_updated += 1

        # Other Settings
        if "default_prompt" in data:
            config.default_prompt = data["default_prompt"] or None
            fields_updated += 1
        if "zai_pricing_plan" in data:
            config.zai_pricing_plan = data["zai_pricing_plan"] or "normal"
            fields_updated += 1

        # Save to database
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Configuration imported successfully",
            "fields_updated": fields_updated
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to import configuration: {str(e)}"
        }), 500


@main_bp.route("/test_api_key", methods=["POST"])
def test_api_key():
    """Test API key validity."""
    try:
        data = request.get_json()
        api_type = data.get("type")
        api_key = data.get("key")

        if not api_key:
            return jsonify({"success": False, "error": "No API key provided"})

        if api_type == "openrouter":
            # Test OpenRouter API key
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10,
                }

                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

                if response.status_code == 200:
                    return jsonify({"success": True, "message": "OpenRouter API key is valid"})
                else:
                    try:
                        error_body = response.json()
                    except Exception:
                        error_body = response.text
                    return jsonify(
                        {"success": False, "error": f"OpenRouter API error: {response.status_code} - {error_body}"}
                    )
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid OpenRouter API key: {str(e)}"})

        elif api_type == "claude":
            # Test Claude API key
            try:
                test_anthropic = Anthropic(api_key=api_key)
                response = test_anthropic.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}],
                )
                return jsonify({"success": True, "message": "Claude API key is valid"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid Claude API key: {str(e)}"})

        elif api_type == "gemini":
            # Test Gemini API key
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(
                    "Hello",
                    generation_config=genai.types.GenerationConfig(max_output_tokens=10),
                )
                return jsonify({"success": True, "message": "Gemini API key is valid"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid Gemini API key: {str(e)}"})

        elif api_type == "openai":
            # Test OpenAI API key
            try:
                test_client = openai.OpenAI(api_key=api_key)
                response = test_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10,
                )
                return jsonify({"success": True, "message": "OpenAI API key is valid"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid OpenAI API key: {str(e)}"})

        elif api_type == "nanogpt":
            # Test NanoGPT API key
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                response = requests.get(
                    "https://nano-gpt.com/api/v1/models",
                    headers=headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    return jsonify({"success": True, "message": "NanoGPT API key is valid"})
                else:
                    return jsonify({"success": False, "error": f"NanoGPT API error: {response.status_code}"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid NanoGPT API key: {str(e)}"})

        elif api_type == "chutes":
            # Test Chutes AI API key
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                response = requests.get(
                    "https://api.chutes.ai/v1/models",
                    headers=headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    return jsonify({"success": True, "message": "Chutes AI API key is valid"})
                else:
                    return jsonify({"success": False, "error": f"Chutes AI API error: {response.status_code}"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid Chutes AI API key: {str(e)}"})

        elif api_type == "zai":
            # Test Z.AI API key (Normal API)
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                # Use a simple chat completion test
                payload = {
                    "model": "glm-4.5-flash",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10,
                }
                response = requests.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if response.status_code == 200:
                    return jsonify({"success": True, "message": "Z.AI API key is valid (Normal API)"})
                else:
                    return jsonify({"success": False, "error": f"Z.AI API error: {response.status_code}"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid Z.AI API key: {str(e)}"})

        elif api_type == "zai_coding_plan":
            # Test Z.AI Coding Plan API key
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                # Test models endpoint for coding plan
                response = requests.get(
                    "https://open.bigmodel.cn/api/paas/v4/models",
                    headers=headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    return jsonify({"success": True, "message": "Z.AI Coding Plan API key is valid"})
                else:
                    return jsonify({"success": False, "error": f"Z.AI Coding Plan API error: {response.status_code}"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid Z.AI Coding Plan API key: {str(e)}"})

        else:
            return jsonify({"success": False, "error": "Invalid API type"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@main_bp.route("/test_lm_studio", methods=["POST"])
def test_lm_studio():
    """Test LM Studio connection."""
    try:
        data = request.get_json()
        url = data.get("url", "http://localhost:1234/v1")

        # Test with a simple completion request
        response = requests.post(
            f"{url}/chat/completions",
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10,
            },
            headers={"Content-Type": "application/json"},
            timeout=5,
        )

        if response.status_code == 200:
            return jsonify({"success": True, "message": "LM Studio connection successful"})
        else:
            return jsonify(
                {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
            )
    except requests.exceptions.ConnectionError:
        return jsonify(
            {
                "success": False,
                "error": "Connection failed. Make sure LM Studio is running.",
            }
        )
    except requests.exceptions.Timeout:
        return jsonify(
            {
                "success": False,
                "error": "Connection timeout. Check if LM Studio is running and accessible.",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@main_bp.route("/test_ollama", methods=["POST"])
def test_ollama():
    """Test Ollama connection."""
    try:
        data = request.get_json()
        base_url = data.get("url", "http://localhost:11434")
        url = f"{base_url}/api/generate"

        # First, check if there are any models available
        models_response = requests.get(
            f"{base_url}/api/tags",
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if models_response.status_code != 200:
            return jsonify(
                {
                    "success": False,
                    "error": f"Ollama models endpoint not accessible: {models_response.status_code} - {models_response.text}",
                }
            )

        models_data = models_response.json()
        if not models_data.get("models"):
            return jsonify(
                {"success": False, "error": "No models found on Ollama server. Please install at least one model."}
            )

        # Find a model that supports generation (not embedding models)
        generative_models = [
            model
            for model in models_data["models"]
            if not any(keyword in model["name"].lower() for keyword in ["embed", "minilm", "bert"])
        ]

        if not generative_models:
            return jsonify(
                {
                    "success": False,
                    "error": "No generative models found on Ollama server. Please install a generative model like llama2, mistral, or qwen.",
                }
            )

        # Use the first generative model for testing
        test_model = generative_models[0]["name"]

        # Test with a simple generation request
        response = requests.post(
            url,
            json={
                "model": test_model,
                "prompt": "Hello",
                "stream": False,
                "options": {"num_predict": 10},
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            return jsonify({"success": True, "message": "Ollama connection successful"})
        else:
            return jsonify(
                {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
            )
    except requests.exceptions.ConnectionError:
        return jsonify(
            {
                "success": False,
                "error": "Connection failed. Make sure Ollama is running.",
            }
        )
    except requests.exceptions.Timeout:
        return jsonify(
            {
                "success": False,
                "error": "Connection timeout. Check if Ollama is running and accessible.",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@main_bp.route("/jobs")
def jobs():
    """View all grading jobs."""
    jobs = GradingJob.query.order_by(GradingJob.created_at.desc()).all()
    return render_template("jobs.html", jobs=jobs)


@main_bp.route("/jobs/<job_id>")
def job_detail(job_id):
    """View job details and submissions."""
    job = GradingJob.query.get_or_404(job_id)
    return render_template("job_detail.html", job=job)


@main_bp.route("/bulk_upload")
def bulk_upload():
    """Bulk upload page."""
    from flask import current_app

    # Get default prompt from configuration
    default_prompt = current_app.config.get(
        "DEFAULT_PROMPT",
        "Please grade this document according to standard academic criteria.",
    )

    # Get saved prompts and marking schemes for dropdowns
    saved_prompts = [prompt.to_dict() for prompt in SavedPrompt.query.order_by(SavedPrompt.name).all()]
    saved_marking_schemes = [
        scheme.to_dict() for scheme in SavedMarkingScheme.query.order_by(SavedMarkingScheme.name).all()
    ]

    # Get job templates for dropdown
    from models import JobTemplate, GradingScheme

    job_templates = [template.to_dict() for template in JobTemplate.query.order_by(JobTemplate.name).all()]
    grading_schemes = [scheme.to_dict() for scheme in GradingScheme.query.filter_by(is_deleted=False).order_by(GradingScheme.name).all()]

    return render_template(
        "bulk_upload.html",
        default_prompt=default_prompt,
        saved_prompts=saved_prompts,
        saved_marking_schemes=saved_marking_schemes,
        job_templates=job_templates,
        grading_schemes=grading_schemes,
    )


@main_bp.route("/saved-configurations")
def saved_configurations():
    """Page for managing saved prompts and marking schemes."""
    saved_prompts = SavedPrompt.query.order_by(SavedPrompt.updated_at.desc()).all()
    saved_marking_schemes = SavedMarkingScheme.query.order_by(SavedMarkingScheme.updated_at.desc()).all()

    return render_template(
        "saved_configurations.html",
        saved_prompts=saved_prompts,
        saved_marking_schemes=saved_marking_schemes,
    )


@main_bp.route("/submissions/<submission_id>/images")
def submission_images(submission_id):
    """Page for viewing and managing image submissions."""
    submission = Submission.query.get_or_404(submission_id)

    # Get all images for this submission with eager loading
    images = (
        ImageSubmission.query.filter_by(submission_id=submission_id)
        .options(
            db.joinedload(ImageSubmission.extracted_content),
            db.joinedload(ImageSubmission.quality_metrics),
        )
        .order_by(ImageSubmission.uploaded_at.desc())
        .all()
    )

    return render_template("image_submissions.html", submission=submission, images=images)
