"""Blueprint for grading scheme CRUD operations and management."""

from decimal import Decimal
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from flask import Blueprint, jsonify, request

from models import GradingScheme, SchemeQuestion, SchemeCriterion, db
from utils.scheme_calculator import calculate_scheme_total, calculate_question_total
from utils.scheme_validator import validate_scheme_name, validate_hierarchy
from middleware.permission_enforcement import require_scheme_permission, require_scheme_owner

schemes_bp = Blueprint("schemes", __name__, url_prefix="/api/schemes")


# ============================================================================
# CORE SCHEME CRUD ENDPOINTS
# ============================================================================


@schemes_bp.route("", methods=["POST"])
def create_scheme():
    """
    Create a new grading scheme.

    Request body:
    {
        "name": "Midterm Rubric",
        "description": "Grading for CS101 Midterm",
        "total_points": 50,
        "questions": [
            {
                "title": "Question 1",
                "max_points": 25,
                "criteria": [
                    {
                        "name": "Correctness",
                        "description": "Solution is correct",
                        "max_points": 10
                    },
                    ...
                ]
            },
            ...
        ]
    }

    Returns: 201 Created with scheme data
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("name"):
            return jsonify({"error": "name is required"}), 400

        # Validate name
        try:
            validate_scheme_name(data["name"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Check for duplicate name (among non-deleted schemes)
        existing = GradingScheme.query.filter_by(name=data["name"], is_deleted=False).first()
        if existing:
            return jsonify({"error": "Scheme name already exists"}), 409

        # Create scheme
        scheme = GradingScheme(
            name=data["name"],
            description=data.get("description"),
        )

        # Add questions if provided
        if data.get("questions"):
            for q_idx, question_data in enumerate(data["questions"], 1):
                if not question_data.get("title"):
                    return jsonify({"error": "Each question must have a title"}), 400

                question = SchemeQuestion(
                    scheme=scheme,
                    title=question_data["title"],
                    description=question_data.get("description"),
                    display_order=q_idx,
                )

                # Add criteria if provided
                if question_data.get("criteria"):
                    for c_idx, criterion_data in enumerate(question_data["criteria"], 1):
                        if not criterion_data.get("name"):
                            return jsonify({"error": "Each criterion must have a name"}), 400

                        try:
                            max_pts = Decimal(str(criterion_data.get("max_points", 0)))
                            if max_pts <= 0:
                                return jsonify({"error": "Criterion max_points must be > 0"}), 400
                        except (ValueError, TypeError):
                            return jsonify({"error": "Criterion max_points must be numeric"}), 400

                        criterion = SchemeCriterion(
                            question=question,
                            name=criterion_data["name"],
                            description=criterion_data.get("description"),
                            max_points=max_pts,
                            display_order=c_idx,
                        )
                        question.criteria.append(criterion)

                scheme.questions.append(question)

        db.session.add(scheme)
        db.session.flush()

        # Recalculate totals
        for question in scheme.questions:
            question.total_possible_points = calculate_question_total(question)
        scheme.total_possible_points = calculate_scheme_total(scheme)

        db.session.commit()

        return jsonify(scheme.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("", methods=["GET"])
def list_schemes():
    """
    List all grading schemes with pagination and filtering.

    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    - name: Filter by name (partial match, case-insensitive)
    - include_deleted: Include deleted schemes (default false)

    Returns: 200 OK with paginated scheme list
    """
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)
        name_filter = request.args.get("name", "").strip()
        include_deleted = request.args.get("include_deleted", "false").lower() == "true"

        # Build query
        query = GradingScheme.query

        # Filter by deletion status
        if not include_deleted:
            query = query.filter_by(is_deleted=False)

        # Filter by name
        if name_filter:
            query = query.filter(GradingScheme.name.ilike(f"%{name_filter}%"))

        # Sort by created date, newest first
        query = query.order_by(desc(GradingScheme.created_at))

        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            "schemes": [s.to_dict() for s in paginated.items],
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": page,
            "per_page": per_page,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/<scheme_id>", methods=["GET"])
@require_scheme_permission('VIEW_ONLY')
def get_scheme(scheme_id):
    """
    Get detailed scheme information including all questions and criteria.

    Permission: Requires VIEW_ONLY or higher

    Returns: 200 OK with full scheme data or 404 if not found
    """
    try:
        scheme = GradingScheme.query.options(
            joinedload(GradingScheme.questions).joinedload(SchemeQuestion.criteria)
        ).filter_by(id=scheme_id).first()

        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        return jsonify(scheme.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/<scheme_id>", methods=["PUT"])
@require_scheme_permission('EDITABLE')
def update_scheme(scheme_id):
    """
    Update scheme metadata (name, description).

    Permission: Requires EDITABLE permission or owner

    Request body:
    {
        "name": "Updated Name",
        "description": "Updated description"
    }

    Returns: 200 OK with updated scheme or 404/409 on error
    """
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        data = request.get_json()

        # Update name if provided
        if "name" in data:
            if not data["name"]:
                return jsonify({"error": "Scheme name cannot be empty"}), 400

            try:
                validate_scheme_name(data["name"])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400

            # Check for duplicate name
            if data["name"] != scheme.name:
                existing = GradingScheme.query.filter_by(
                    name=data["name"], is_deleted=False
                ).first()
                if existing:
                    return jsonify({"error": "Scheme name already exists"}), 409

            scheme.name = data["name"]

        # Update description if provided
        if "description" in data:
            scheme.description = data["description"]

        # Increment version number
        scheme.version_number += 1

        db.session.commit()

        return jsonify(scheme.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/<scheme_id>", methods=["DELETE"])
@require_scheme_owner()
def delete_scheme(scheme_id):
    """
    Soft delete a grading scheme (mark as deleted).

    Permission: Requires owner (EDITABLE permission holders cannot delete)

    Returns: 204 No Content on success or 404/409 on error
    """
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        if scheme.is_deleted:
            return jsonify({"error": "Scheme is already deleted"}), 409

        scheme.is_deleted = True
        db.session.commit()

        return "", 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# QUESTION MANAGEMENT ENDPOINTS
# ============================================================================


@schemes_bp.route("/<scheme_id>/questions", methods=["POST"])
def add_question(scheme_id):
    """
    Add a question to an existing scheme.

    Request body:
    {
        "title": "Question 1",
        "description": "Description of question",
        "max_points": 25
    }

    Returns: 201 Created with question data or 404/400 on error
    """
    try:
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        data = request.get_json()

        if not data.get("title"):
            return jsonify({"error": "title is required"}), 400

        # Determine display order (one more than current count)
        display_order = len(scheme.questions) + 1

        question = SchemeQuestion(
            scheme_id=scheme.id,
            title=data["title"],
            description=data.get("description"),
            display_order=display_order,
            total_possible_points=Decimal("0.00"),
        )

        db.session.add(question)
        db.session.commit()

        return jsonify(question.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/questions/<question_id>", methods=["PUT"])
def update_question(question_id):
    """
    Update a question.

    Request body:
    {
        "title": "Updated title",
        "description": "Updated description"
    }

    Returns: 200 OK with updated question or 404 on error
    """
    try:
        question = SchemeQuestion.query.filter_by(id=question_id).first()
        if not question:
            return jsonify({"error": "Question not found"}), 404

        data = request.get_json()

        if "title" in data:
            if not data["title"]:
                return jsonify({"error": "Question title cannot be empty"}), 400
            question.title = data["title"]

        if "description" in data:
            question.description = data["description"]

        db.session.commit()

        return jsonify(question.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/questions/<question_id>", methods=["DELETE"])
def delete_question(question_id):
    """
    Delete a question and cascade delete its criteria.

    Returns: 204 No Content on success or 404/409 on error
    """
    try:
        question = SchemeQuestion.query.filter_by(id=question_id).first()
        if not question:
            return jsonify({"error": "Question not found"}), 404

        scheme = question.scheme

        # Check if any criteria have evaluations
        from models import CriterionEvaluation
        has_evaluations = db.session.query(CriterionEvaluation).join(
            SchemeCriterion
        ).filter(SchemeCriterion.question_id == question_id).first()

        if has_evaluations:
            return jsonify({"error": "Cannot delete question with existing evaluations"}), 409

        # Get current position
        old_order = question.display_order

        # Delete the question (cascade will delete criteria)
        db.session.delete(question)

        # Reorder remaining questions
        remaining_questions = SchemeQuestion.query.filter(
            SchemeQuestion.scheme_id == scheme.id,
            SchemeQuestion.display_order > old_order,
        ).all()

        for q in remaining_questions:
            q.display_order -= 1

        # Recalculate scheme total
        scheme.total_possible_points = calculate_scheme_total(scheme)

        db.session.commit()

        return "", 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/questions/reorder", methods=["POST"])
def reorder_questions():
    """
    Reorder questions within a scheme.

    Request body:
    {
        "orders": [
            {"question_id": "uuid", "display_order": 1},
            {"question_id": "uuid", "display_order": 2},
            ...
        ]
    }

    Returns: 200 OK with updated questions
    """
    try:
        data = request.get_json()
        orders = data.get("orders", [])

        if not orders:
            return jsonify({"error": "orders is required"}), 400

        # Use temporary high values to avoid constraint violations during reordering
        temp_order = 10000
        for item in orders:
            question = SchemeQuestion.query.filter_by(id=item["question_id"]).first()
            if not question:
                return jsonify({"error": f"Question {item['question_id']} not found"}), 404

            question.display_order = temp_order
            temp_order += 1

        db.session.flush()

        # Now set final values
        for item in orders:
            question = SchemeQuestion.query.filter_by(id=item["question_id"]).first()
            question.display_order = item["display_order"]

        db.session.commit()

        # Return all updated questions
        question_ids = [item["question_id"] for item in orders]
        updated_questions = SchemeQuestion.query.filter(
            SchemeQuestion.id.in_(question_ids)
        ).all()

        return jsonify({
            "questions": [q.to_dict() for q in updated_questions]
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# CRITERIA MANAGEMENT ENDPOINTS
# ============================================================================


@schemes_bp.route("/questions/<question_id>/criteria", methods=["POST"])
def add_criterion(question_id):
    """
    Add a criterion to a question.

    Request body:
    {
        "name": "Correctness",
        "description": "Solution is correct",
        "max_points": 10
    }

    Returns: 201 Created with criterion data or 404/400 on error
    """
    try:
        question = SchemeQuestion.query.filter_by(id=question_id).first()
        if not question:
            return jsonify({"error": "Question not found"}), 404

        data = request.get_json()

        if not data.get("name"):
            return jsonify({"error": "name is required"}), 400

        if "max_points" not in data:
            return jsonify({"error": "max_points is required"}), 400

        # Validate points
        try:
            max_pts = Decimal(str(data["max_points"]))
            if max_pts <= 0:
                return jsonify({"error": "max_points must be > 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "max_points must be numeric"}), 400

        # Determine display order
        display_order = len(question.criteria) + 1

        criterion = SchemeCriterion(
            question_id=question.id,
            name=data["name"],
            description=data.get("description"),
            max_points=max_pts,
            display_order=display_order,
        )

        db.session.add(criterion)

        # Update question total
        question.total_possible_points = calculate_question_total(question) + max_pts

        # Update scheme total
        question.scheme.total_possible_points = calculate_scheme_total(question.scheme)

        db.session.commit()

        return jsonify(criterion.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/criteria/<criterion_id>", methods=["PUT"])
def update_criterion(criterion_id):
    """
    Update a criterion.

    Request body:
    {
        "name": "Updated name",
        "description": "Updated description",
        "max_points": 15
    }

    Returns: 200 OK with updated criterion or 404 on error
    """
    try:
        criterion = SchemeCriterion.query.filter_by(id=criterion_id).first()
        if not criterion:
            return jsonify({"error": "Criterion not found"}), 404

        data = request.get_json()
        question = criterion.question

        # Update name
        if "name" in data:
            if not data["name"]:
                return jsonify({"error": "Criterion name cannot be empty"}), 400
            criterion.name = data["name"]

        # Update description
        if "description" in data:
            criterion.description = data["description"]

        # Update max_points
        if "max_points" in data:
            try:
                new_max = Decimal(str(data["max_points"]))
                if new_max <= 0:
                    return jsonify({"error": "max_points must be > 0"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "max_points must be numeric"}), 400

            criterion.max_points = new_max

            # Recalculate question and scheme totals
            question.total_possible_points = calculate_question_total(question)
            question.scheme.total_possible_points = calculate_scheme_total(question.scheme)

        db.session.commit()

        return jsonify(criterion.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/criteria/<criterion_id>", methods=["DELETE"])
def delete_criterion(criterion_id):
    """
    Delete a criterion.

    Returns: 204 No Content on success or 404/409 on error
    """
    try:
        criterion = SchemeCriterion.query.filter_by(id=criterion_id).first()
        if not criterion:
            return jsonify({"error": "Criterion not found"}), 404

        # Check if criterion has evaluations
        from models import CriterionEvaluation
        has_evaluations = CriterionEvaluation.query.filter_by(
            criterion_id=criterion_id
        ).first()

        if has_evaluations:
            return jsonify({"error": "Cannot delete criterion with existing evaluations"}), 409

        question = criterion.question
        scheme = question.scheme
        old_order = criterion.display_order

        # Delete criterion
        db.session.delete(criterion)

        # Reorder remaining criteria in the question
        remaining_criteria = SchemeCriterion.query.filter(
            SchemeCriterion.question_id == question.id,
            SchemeCriterion.display_order > old_order,
        ).all()

        for c in remaining_criteria:
            c.display_order -= 1

        # Recalculate totals
        question.total_possible_points = calculate_question_total(question)
        scheme.total_possible_points = calculate_scheme_total(scheme)

        db.session.commit()

        return "", 204

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/criteria/reorder", methods=["POST"])
def reorder_criteria():
    """
    Reorder criteria within a question.

    Request body:
    {
        "orders": [
            {"criterion_id": "uuid", "display_order": 1},
            ...
        ]
    }

    Returns: 200 OK with updated criteria
    """
    try:
        data = request.get_json()
        orders = data.get("orders", [])

        if not orders:
            return jsonify({"error": "orders is required"}), 400

        # Use temporary high values to avoid constraint violations during reordering
        temp_order = 10000
        for item in orders:
            criterion = SchemeCriterion.query.filter_by(id=item["criterion_id"]).first()
            if not criterion:
                return jsonify({"error": f"Criterion {item['criterion_id']} not found"}), 404

            criterion.display_order = temp_order
            temp_order += 1

        db.session.flush()

        # Now set final values
        for item in orders:
            criterion = SchemeCriterion.query.filter_by(id=item["criterion_id"]).first()
            criterion.display_order = item["display_order"]

        db.session.commit()

        # Return all updated criteria
        criterion_ids = [item["criterion_id"] for item in orders]
        updated_criteria = SchemeCriterion.query.filter(
            SchemeCriterion.id.in_(criterion_ids)
        ).all()

        return jsonify({
            "criteria": [c.to_dict() for c in updated_criteria]
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================


@schemes_bp.route("/<scheme_id>/clone", methods=["POST"])
@require_scheme_permission('COPY')
def clone_scheme(scheme_id):
    """
    Clone an existing scheme with all its questions and criteria.

    Permission: Requires COPY permission or owner

    Request body:
    {
        "name": "Custom Name"  # Optional, will append " (Copy)" to original if not provided
    }

    Returns: 201 Created with new scheme data
    """
    try:
        from flask import session
        from flask_login import current_user

        # Get current user ID
        current_user_id = None
        try:
            if hasattr(current_user, 'id'):
                current_user_id = current_user.id
        except:
            pass

        if not current_user_id:
            current_user_id = session.get('user_id')

        original_scheme = GradingScheme.query.filter_by(id=scheme_id).first()

        if not original_scheme:
            return jsonify({"error": "Scheme not found"}), 404

        data = request.get_json(silent=True) or {}

        # Generate new name
        new_name = data.get("name") or f"{original_scheme.name} (Copy)"

        # Check name uniqueness
        existing = GradingScheme.query.filter_by(name=new_name, is_deleted=False).first()
        if existing:
            # Append number if needed
            counter = 1
            while True:
                new_name_candidate = f"{original_scheme.name} (Copy {counter})"
                if not GradingScheme.query.filter_by(name=new_name_candidate, is_deleted=False).first():
                    new_name = new_name_candidate
                    break
                counter += 1

        # Create new scheme with current user as creator
        new_scheme = GradingScheme(
            name=new_name,
            description=original_scheme.description,
            created_by=current_user_id,  # Set current user as creator of copy
        )

        # Clone all questions and criteria
        for orig_question in original_scheme.questions:
            new_question = SchemeQuestion(
                scheme=new_scheme,
                title=orig_question.title,
                description=orig_question.description,
                display_order=orig_question.display_order,
            )

            for orig_criterion in orig_question.criteria:
                new_criterion = SchemeCriterion(
                    question=new_question,
                    name=orig_criterion.name,
                    description=orig_criterion.description,
                    max_points=orig_criterion.max_points,
                    display_order=orig_criterion.display_order,
                )
                new_question.criteria.append(new_criterion)

            # Calculate question total
            new_question.total_possible_points = calculate_question_total(new_question)
            new_scheme.questions.append(new_question)

        # Calculate scheme total
        new_scheme.total_possible_points = calculate_scheme_total(new_scheme)

        db.session.add(new_scheme)
        db.session.commit()

        return jsonify(new_scheme.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/<scheme_id>/statistics", methods=["GET"])
def get_statistics(scheme_id):
    """
    Get usage statistics for a grading scheme.

    Returns: 200 OK with statistics or 404 if scheme not found
    """
    try:
        scheme = GradingScheme.query.options(
            joinedload(GradingScheme.questions).joinedload(SchemeQuestion.criteria)
        ).filter_by(id=scheme_id).first()

        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        # Get all submissions for this scheme
        from models import GradedSubmission, CriterionEvaluation

        submissions = GradedSubmission.query.filter_by(scheme_id=scheme_id).all()

        if not submissions:
            return jsonify({
                "scheme_id": scheme_id,
                "total_submissions": 0,
                "average_score": None,
                "average_percentage": None,
                "min_score": None,
                "max_score": None,
                "questions": [],
                "criteria": [],
            }), 200

        # Calculate statistics
        scores = [s.total_points_earned for s in submissions if s.total_points_earned is not None]
        percentages = [s.percentage_score for s in submissions if s.is_complete and s.percentage_score is not None]

        avg_score = sum(Decimal(str(s)) for s in scores) / len(scores) if scores else None
        avg_percentage = sum(Decimal(str(p)) for p in percentages) / len(percentages) if percentages else None
        min_score = min(Decimal(str(s)) for s in scores) if scores else None
        max_score = max(Decimal(str(s)) for s in scores) if scores else None

        # Question statistics
        question_stats = []
        for question in scheme.questions:
            # Sum of criterion evaluations for this question
            question_criteria_ids = [c.id for c in question.criteria]
            evaluations = CriterionEvaluation.query.filter(
                CriterionEvaluation.criterion_id.in_(question_criteria_ids),
                CriterionEvaluation.submission_id.in_([s.id for s in submissions]),
            ).all()

            if evaluations:
                avg_q_score = sum(Decimal(str(e.points_awarded)) for e in evaluations if e.points_awarded) / len(evaluations)
            else:
                avg_q_score = None

            question_stats.append({
                "question_id": question.id,
                "question_title": question.title,
                "average_score": float(avg_q_score) if avg_q_score else None,
                "max_points": float(question.total_possible_points) if question.total_possible_points else 0,
            })

        # Criterion statistics
        criterion_stats = []
        for question in scheme.questions:
            for criterion in question.criteria:
                evaluations = CriterionEvaluation.query.filter_by(
                    criterion_id=criterion.id
                ).filter(
                    CriterionEvaluation.submission_id.in_([s.id for s in submissions])
                ).all()

                if evaluations:
                    avg_c_score = sum(Decimal(str(e.points_awarded)) for e in evaluations if e.points_awarded) / len(evaluations)
                    count = len(evaluations)
                else:
                    avg_c_score = None
                    count = 0

                criterion_stats.append({
                    "criterion_id": criterion.id,
                    "criterion_name": criterion.name,
                    "question_id": question.id,
                    "question_title": question.title,
                    "average_score": float(avg_c_score) if avg_c_score else None,
                    "max_points": float(criterion.max_points) if criterion.max_points else 0,
                    "evaluations_count": count,
                })

        return jsonify({
            "scheme_id": scheme_id,
            "scheme_name": scheme.name,
            "total_submissions": len(submissions),
            "average_score": float(avg_score) if avg_score else None,
            "average_percentage": float(avg_percentage) if avg_percentage else None,
            "min_score": float(min_score) if min_score else None,
            "max_score": float(max_score) if max_score else None,
            "questions": question_stats,
            "criteria": criterion_stats,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@schemes_bp.route("/<scheme_id>/validate", methods=["POST"])
def validate_scheme_endpoint(scheme_id):
    """
    Validate scheme integrity and return validation report.

    Returns: 200 OK with validation results
    """
    try:
        scheme = GradingScheme.query.options(
            joinedload(GradingScheme.questions).joinedload(SchemeQuestion.criteria)
        ).filter_by(id=scheme_id).first()

        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        warnings = []
        errors = []

        # Validate hierarchy
        try:
            validate_hierarchy(scheme)
        except ValueError as e:
            errors.append(str(e))

        # Check if scheme has submissions (informational)
        from models import GradedSubmission
        submission_count = GradedSubmission.query.filter_by(scheme_id=scheme_id).count()

        if submission_count > 0:
            warnings.append(f"Scheme has {submission_count} submission(s) - modifications may affect grading")

        return jsonify({
            "scheme_id": scheme_id,
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "submission_count": submission_count,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
