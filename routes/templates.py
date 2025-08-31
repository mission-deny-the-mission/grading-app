"""
Template management routes for the grading application.
Handles template management UI and related functionality.
"""

from flask import Blueprint, jsonify, render_template, request

from models import (BatchTemplate, JobTemplate, SavedMarkingScheme,
                    SavedPrompt, db)

templates_bp = Blueprint("templates", __name__)


@templates_bp.route("/templates")
def templates_page():
    """Template management page with filtering and search."""
    # Get filter parameters
    template_type = request.args.get("type", "all")  # 'all', 'batch', 'job'
    category_filter = request.args.get("category")
    search_query = request.args.get("search", "").strip()

    # Get all templates
    batch_templates = BatchTemplate.query.all()
    job_templates = JobTemplate.query.all()

    # Apply filters
    filtered_templates = []

    for template in batch_templates:
        if _template_matches_filter(
            template, template_type, category_filter, search_query
        ):
            filtered_templates.append(template)

    for template in job_templates:
        if _template_matches_filter(
            template, template_type, category_filter, search_query
        ):
            filtered_templates.append(template)

    # Get available filter options
    all_categories = set()
    for template in filtered_templates:
        if template.category:
            all_categories.add(template.category)

    # Get saved configurations for template creation
    saved_prompts = SavedPrompt.query.order_by(SavedPrompt.name).all()
    saved_marking_schemes = SavedMarkingScheme.query.order_by(
        SavedMarkingScheme.name
    ).all()

    return render_template(
        "templates.html",
        templates=filtered_templates,
        saved_prompts=[p.to_dict() for p in saved_prompts],
        saved_marking_schemes=[s.to_dict() for s in saved_marking_schemes],
        filter_options={
            "categories": sorted(list(all_categories)),
            "types": ["all", "batch", "job"],
        },
        current_filters={
            "type": template_type,
            "category": category_filter,
            "search": search_query,
        },
    )


@templates_bp.route("/create-template", methods=["POST"])
def create_template():
    """Create a new template via form submission."""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("name"):
            return (
                jsonify({"success": False, "error": "Template name is required"}),
                400,
            )

        # Determine template type based on provided fields
        if data.get("template_type") == "batch":
            template = BatchTemplate(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category"),
                default_settings=data.get("default_settings", {}),
                job_structure=data.get("job_structure", {}),
                processing_rules=data.get("processing_rules", {}),
                is_public=data.get("is_public", False),
                created_by=request.remote_addr,
            )
        else:  # job template
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
                "message": "Template created successfully",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


def _template_matches_filter(template, template_type, category_filter, search_query):
    """Helper function to check if a template matches filter criteria."""
    # Filter by type
    if template_type == "batch" and not isinstance(template, BatchTemplate):
        return False
    elif template_type == "job" and not isinstance(template, JobTemplate):
        return False

    # Filter by category
    if category_filter and template.category != category_filter:
        return False

    # Filter by search
    if search_query:
        search_lower = search_query.lower()
        name_match = (
            hasattr(template.name, "lower") and search_lower in template.name.lower()
        )
        desc_match = (
            hasattr(template.description, "lower")
            and template.description
            and search_lower in template.description.lower()
        )
        if not name_match and not desc_match:
            return False

    return True
