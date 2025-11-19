"""Web page routes for authentication UI (login/register) and dashboard.

These provide HTML endpoints that wrap the existing API-based auth system
so that middleware and tests have concrete pages to redirect to.
"""

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from services.deployment_service import DeploymentService


auth_pages_bp = Blueprint("auth_pages", __name__)


@auth_pages_bp.route("/auth/login", methods=["GET"])
def login_page():
    """Render login page.

    In single-user mode, there is no login; redirect to index.
    """
    if DeploymentService.is_single_user_mode():
        return redirect(url_for("main.index"))
    # Optional message params used by base.html/logout flow
    message = request.args.get("message")
    message_type = request.args.get("type", "info")
    return render_template("auth/login.html", message=message, message_type=message_type)


@auth_pages_bp.route("/auth/register", methods=["GET"])
def register_page():
    """Render registration page (only meaningful in multi-user mode)."""
    if DeploymentService.is_single_user_mode():
        return redirect(url_for("main.index"))
    return render_template("auth/register.html")


@auth_pages_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Simple dashboard page used by auth/session tests.

    For now this just renders the main index with a different title/heading.
    """
    return render_template("index.html", default_prompt="", dashboard_mode=True)
