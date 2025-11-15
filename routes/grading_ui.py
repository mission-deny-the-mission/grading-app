"""
UI Routes for Grading Interface

Handles rendering HTML templates for applying schemes to submissions and grading.
All grade data access goes through the /api/submissions/<id>/grade endpoints.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, Submission, GradingScheme

grading_ui_bp = Blueprint("grading_ui", __name__, url_prefix="/submissions")


@grading_ui_bp.route("/<submission_id>/grade", methods=["GET"])
def grade_submission(submission_id):
    """
    Display grading form for a submission.

    Query Parameters:
    - scheme_id: Scheme to use for grading (optional, falls back to job.scheme_id)
    """
    try:
        scheme_id = request.args.get("scheme_id")

        # Validate submission exists
        submission = Submission.query.filter_by(id=submission_id).first()
        if not submission:
            flash("Submission not found", "danger")
            return redirect(request.referrer or "/")

        # If scheme_id not provided, try to get from job
        if not scheme_id and submission.job and submission.job.scheme_id:
            scheme_id = submission.job.scheme_id

        # Validate scheme if provided
        if scheme_id:
            scheme = GradingScheme.query.filter_by(id=scheme_id, is_deleted=False).first()
            if not scheme:
                flash("Grading scheme not found", "danger")
                return redirect(request.referrer or "/")

        return render_template(
            "grading/grade_submission.html",
            submission=submission,
            scheme_id=scheme_id,
        )

    except Exception as e:
        flash(f"Error loading grading form: {str(e)}", "danger")
        return redirect(request.referrer or "/")


@grading_ui_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    flash("Page not found", "danger")
    return redirect(request.referrer or "/"), 404


@grading_ui_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    flash("An internal error occurred", "danger")
    return redirect(request.referrer or "/"), 500
