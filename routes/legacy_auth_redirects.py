"""Legacy auth route shims.

Provides /login and /register endpoints used by older templates and tests.
These now render the HTML auth templates directly so tests see HTTP 200.
"""

from flask import Blueprint, render_template


legacy_auth_bp = Blueprint("legacy_auth", __name__)


@legacy_auth_bp.route("/login", methods=["GET"])
def login_redirect():
    """Legacy /login route.

    Render the login page directly.
    """
    return render_template("auth/login.html")


@legacy_auth_bp.route("/register", methods=["GET"])
def register_redirect():
    """Legacy /register route.

    Render the registration page directly.
    """
    return render_template("auth/register.html")
