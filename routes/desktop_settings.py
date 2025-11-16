"""
Desktop settings routes for managing API keys in OS credential manager.
Handles configuration of AI provider credentials with secure storage.
"""

from flask import Blueprint, jsonify, render_template, request
from desktop import credentials, __version__
from desktop.app_wrapper import get_user_data_dir
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

desktop_settings_bp = Blueprint("desktop_settings", __name__)

# Supported AI providers
SUPPORTED_PROVIDERS = [
    {
        "key": "openrouter_api_key",
        "name": "OpenRouter",
        "placeholder": "sk-or-...",
        "description": "OpenRouter API for multiple AI models"
    },
    {
        "key": "claude_api_key",
        "name": "Claude",
        "placeholder": "sk-ant-...",
        "description": "Anthropic Claude API"
    },
    {
        "key": "openai_api_key",
        "name": "OpenAI",
        "placeholder": "sk-...",
        "description": "OpenAI API (GPT models)"
    },
    {
        "key": "gemini_api_key",
        "name": "Gemini",
        "placeholder": "AI...",
        "description": "Google Gemini API"
    },
    {
        "key": "nanogpt_api_key",
        "name": "NanoGPT",
        "placeholder": "nano-...",
        "description": "NanoGPT API"
    },
    {
        "key": "chutes_api_key",
        "name": "Chutes AI",
        "placeholder": "chutes-...",
        "description": "Chutes AI API"
    },
    {
        "key": "zai_api_key",
        "name": "Z.AI",
        "placeholder": "zai-...",
        "description": "Z.AI API"
    }
]


def mask_api_key(api_key):
    """
    Mask API key to show only last 4 characters for security.

    Args:
        api_key: The full API key string

    Returns:
        Masked string showing only last 4 characters (e.g., "****1234")
        or empty string if no key provided
    """
    if not api_key or len(api_key) < 4:
        return ""
    return "*" * (len(api_key) - 4) + api_key[-4:]


@desktop_settings_bp.route("/desktop/settings")
def show_settings():
    """
    Display desktop settings page with API key forms.

    Retrieves API keys from OS credential manager and displays them
    with masking (only last 4 characters visible).

    Returns:
        Rendered template with provider configuration forms
    """
    try:
        # Get current API keys from credential manager
        providers_with_keys = []
        for provider in SUPPORTED_PROVIDERS:
            provider_key = provider["key"]
            api_key = credentials.get_api_key(provider_key)

            providers_with_keys.append({
                "key": provider_key,
                "name": provider["name"],
                "placeholder": provider["placeholder"],
                "description": provider["description"],
                "masked_key": mask_api_key(api_key),
                "has_key": bool(api_key)
            })

        # Detect keyring backend for display
        backend_info = credentials.detect_keyring_backend()

        return render_template(
            "desktop_settings.html",
            providers=providers_with_keys,
            backend_info=backend_info,
            app_version=__version__
        )
    except Exception as e:
        logger.error(f"Error loading desktop settings: {e}")
        return render_template(
            "desktop_settings.html",
            providers=SUPPORTED_PROVIDERS,
            backend_info={"backend": "Unknown", "type": "unknown", "secure": False},
            error="Failed to load current settings",
            app_version=__version__
        )


@desktop_settings_bp.route("/desktop/settings/api-keys", methods=["POST"])
def update_api_keys():
    """
    Update API keys in OS credential manager.

    Accepts form data with API keys for multiple providers and stores them
    securely in the OS credential manager.

    Request JSON:
        {
            "openrouter_api_key": "sk-or-...",
            "claude_api_key": "sk-ant-...",
            ...
        }

    Returns:
        JSON response with success status and message
    """
    try:
        data = request.get_json() if request.is_json else request.form

        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400

        updated_count = 0
        errors = []

        # Process each supported provider
        for provider in SUPPORTED_PROVIDERS:
            provider_key = provider["key"]

            # Get API key from request
            api_key = data.get(provider_key, "").strip()

            # Skip if empty
            if not api_key:
                continue

            # Store in credential manager
            if credentials.set_api_key(provider_key, api_key):
                updated_count += 1
                logger.info(f"Updated API key for {provider['name']}")
            else:
                errors.append(f"Failed to store {provider['name']} API key")
                logger.error(f"Failed to store API key for {provider_key}")

        if errors:
            return jsonify({
                "success": False,
                "message": f"Some keys failed to save: {'; '.join(errors)}",
                "updated_count": updated_count
            }), 500

        if updated_count == 0:
            return jsonify({
                "success": False,
                "message": "No API keys provided to update"
            }), 400

        return jsonify({
            "success": True,
            "message": f"Successfully updated {updated_count} API key(s)",
            "updated_count": updated_count
        })

    except Exception as e:
        logger.error(f"Error updating API keys: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to update API keys: {str(e)}"
        }), 500


@desktop_settings_bp.route("/desktop/settings/api-keys/<provider>", methods=["DELETE"])
def delete_api_key_route(provider):
    """
    Delete specific API key from OS credential manager.

    Args:
        provider: Provider key name (e.g., "openrouter_api_key")

    Returns:
        JSON response with success status and message
    """
    try:
        # Validate provider is supported
        valid_providers = [p["key"] for p in SUPPORTED_PROVIDERS]
        if provider not in valid_providers:
            return jsonify({
                "success": False,
                "message": f"Unknown provider: {provider}"
            }), 400

        # Delete from credential manager
        if credentials.delete_api_key(provider):
            provider_name = next(
                (p["name"] for p in SUPPORTED_PROVIDERS if p["key"] == provider),
                provider
            )
            logger.info(f"Deleted API key for {provider_name}")
            return jsonify({
                "success": True,
                "message": f"Successfully deleted {provider_name} API key"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Failed to delete {provider} API key"
            }), 500

    except Exception as e:
        logger.error(f"Error deleting API key for {provider}: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to delete API key: {str(e)}"
        }), 500


@desktop_settings_bp.route("/desktop/logs/open", methods=["POST"])
def open_logs_folder():
    """
    Open logs folder in system file explorer.

    Returns:
        JSON response with success status
    """
    try:
        logs_dir = get_user_data_dir() / "logs"

        # Ensure logs directory exists
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Open folder in file explorer
        if sys.platform == 'win32':
            # Windows: explorer
            subprocess.Popen(['explorer', str(logs_dir)])
        elif sys.platform == 'darwin':
            # macOS: Finder
            subprocess.Popen(['open', str(logs_dir)])
        else:
            # Linux: xdg-open
            subprocess.Popen(['xdg-open', str(logs_dir)])

        logger.info(f"Opened logs folder: {logs_dir}")

        return jsonify({
            "success": True,
            "message": "Logs folder opened",
            "path": str(logs_dir)
        })

    except Exception as e:
        logger.error(f"Failed to open logs folder: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to open logs folder: {str(e)}"
        }), 500
