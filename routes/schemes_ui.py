"""
UI Routes for Grading Scheme Management

Handles rendering HTML templates for scheme CRUD operations.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models import db, GradingScheme, SchemeQuestion, SchemeCriterion
from decimal import Decimal

schemes_ui_bp = Blueprint("schemes_ui", __name__, url_prefix="/schemes")


@schemes_ui_bp.route("/", methods=["GET"])
def list_schemes():
    """
    Display all grading schemes with pagination and search.

    Query Parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    - search: Search by scheme name (case-insensitive)
    - sort: Sort by 'name', 'created', 'total_points' (default 'created')
    - order: 'asc' or 'desc' (default 'desc')
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        search = request.args.get("search", "", type=str)
        sort = request.args.get("sort", "created_at", type=str)
        order = request.args.get("order", "desc", type=str)

        # Build query
        query = GradingScheme.query.filter_by(is_deleted=False)

        # Search filter
        if search:
            query = query.filter(
                GradingScheme.name.ilike(f"%{search}%")
            )

        # Sorting
        if sort == "name":
            query = query.order_by(GradingScheme.name)
        elif sort == "total_points":
            query = query.order_by(GradingScheme.total_possible_points)
        else:  # created_at (default)
            query = query.order_by(GradingScheme.created_at)

        if order == "asc":
            query = query  # Already ascending
        else:
            query = query.desc() if hasattr(query, "desc") else query.order_by(
                GradingScheme.created_at.desc()
            )

        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            "schemes/index.html",
            schemes=paginated.items,
            pagination=paginated,
            search=search,
            sort=sort,
            order=order,
            per_page=per_page,
        )

    except Exception as e:
        flash(f"Error loading schemes: {str(e)}", "danger")
        return render_template("schemes/index.html", schemes=[], pagination=None)


@schemes_ui_bp.route("/<scheme_id>", methods=["GET"])
def view_scheme(scheme_id):
    """Display detailed view of a grading scheme."""
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id, is_deleted=False).first()
        if not scheme:
            flash("Scheme not found", "danger")
            return redirect(url_for("schemes_ui.list_schemes"))

        return render_template("schemes/detail.html", scheme=scheme)

    except Exception as e:
        flash(f"Error loading scheme: {str(e)}", "danger")
        return redirect(url_for("schemes_ui.list_schemes"))


@schemes_ui_bp.route("/create", methods=["GET"])
def create_scheme():
    """Display form to create a new grading scheme."""
    return render_template("schemes/builder.html", scheme=None, mode="create")


@schemes_ui_bp.route("/<scheme_id>/edit", methods=["GET"])
def edit_scheme(scheme_id):
    """Display form to edit an existing scheme."""
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id, is_deleted=False).first()
        if not scheme:
            flash("Scheme not found", "danger")
            return redirect(url_for("schemes_ui.list_schemes"))

        return render_template("schemes/builder.html", scheme=scheme, mode="edit")

    except Exception as e:
        flash(f"Error loading scheme: {str(e)}", "danger")
        return redirect(url_for("schemes_ui.list_schemes"))


@schemes_ui_bp.route("/<scheme_id>/statistics", methods=["GET"])
def view_statistics(scheme_id):
    """Display statistics for a grading scheme."""
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id, is_deleted=False).first()
        if not scheme:
            flash("Scheme not found", "danger")
            return redirect(url_for("schemes_ui.list_schemes"))

        # Statistics will be fetched via AJAX from /api/schemes/<id>/statistics
        return render_template("schemes/statistics.html", scheme=scheme)

    except Exception as e:
        flash(f"Error loading statistics: {str(e)}", "danger")
        return redirect(url_for("schemes_ui.list_schemes"))


@schemes_ui_bp.route("/<scheme_id>/clone", methods=["GET"])
def clone_scheme_form(scheme_id):
    """Display form to clone a scheme."""
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id, is_deleted=False).first()
        if not scheme:
            flash("Scheme not found", "danger")
            return redirect(url_for("schemes_ui.list_schemes"))

        return render_template("schemes/clone_form.html", original_scheme=scheme)

    except Exception as e:
        flash(f"Error loading scheme: {str(e)}", "danger")
        return redirect(url_for("schemes_ui.list_schemes"))


@schemes_ui_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    flash("Page not found", "danger")
    return redirect(url_for("schemes_ui.list_schemes")), 404


@schemes_ui_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    flash("An internal error occurred", "danger")
    return redirect(url_for("schemes_ui.list_schemes")), 500
