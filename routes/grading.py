"""Blueprint for applying grading schemes to submissions."""

from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, jsonify, request

from models import (
    CriterionEvaluation,
    GradedSubmission,
    GradingScheme,
    SchemeCriterion,
    db,
    recalculate_submission_total,
)
from utils.scheme_calculator import calculate_percentage_score

grading_bp = Blueprint("grading", __name__, url_prefix="/api/grading")


@grading_bp.route("/submissions", methods=["POST"])
def create_submission():
    """
    Create a new graded submission for a student using a specific grading scheme.

    Request body:
    {
        "scheme_id": "uuid",
        "student_id": "STU001",
        "student_name": "John Doe",  # optional
        "submission_reference": "file_id",  # optional
        "graded_by": "instructor@example.com"
    }

    Returns: 201 Created with submission data including evaluations
    """
    try:
        data = request.get_json()

        # Validation
        if not data.get("scheme_id"):
            return jsonify({"error": "scheme_id is required"}), 400
        if not data.get("student_id"):
            return jsonify({"error": "student_id is required"}), 400
        if not data.get("graded_by"):
            return jsonify({"error": "graded_by is required"}), 400

        # Get the scheme
        scheme = GradingScheme.query.filter_by(id=data["scheme_id"]).first()
        if not scheme:
            return jsonify({"error": "Grading scheme not found"}), 404
        if scheme.is_deleted:
            return jsonify({"error": "Grading scheme has been deleted"}), 404

        # Create submission
        submission = GradedSubmission(
            scheme_id=scheme.id,
            scheme_version=scheme.version_number,
            student_id=data["student_id"],
            student_name=data.get("student_name"),
            submission_reference=data.get("submission_reference"),
            graded_by=data["graded_by"],
            total_points_possible=scheme.total_possible_points,
        )

        db.session.add(submission)
        db.session.commit()

        return jsonify(submission.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@grading_bp.route("/submissions/<submission_id>", methods=["GET"])
def get_submission(submission_id):
    """
    Get a graded submission with all its evaluations.

    Returns: 200 OK with submission data or 404 if not found
    """
    try:
        submission = GradedSubmission.query.filter_by(id=submission_id).first()
        if not submission:
            return jsonify({"error": "Submission not found"}), 404

        return jsonify(submission.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grading_bp.route("/submissions/<submission_id>", methods=["PATCH"])
def update_submission(submission_id):
    """
    Update submission status (complete/reopen) and calculate percentage score.

    Request body:
    {
        "is_complete": true/false
    }

    Returns: 200 OK with updated submission or 404/409 on error
    """
    try:
        submission = GradedSubmission.query.filter_by(id=submission_id).first()
        if not submission:
            return jsonify({"error": "Submission not found"}), 404

        data = request.get_json()

        # Check optimistic locking version
        if data.get("evaluation_version") != submission.evaluation_version:
            return (
                jsonify(
                    {
                        "error": "Submission was modified by another user",
                        "current_version": submission.evaluation_version,
                    }
                ),
                409,
            )

        # Mark as complete
        if data.get("is_complete"):
            submission.is_complete = True
            submission.graded_at = datetime.now(timezone.utc)

            # Calculate percentage score
            percentage = calculate_percentage_score(submission.total_points_earned, submission.total_points_possible)
            submission.percentage_score = percentage
        else:
            # Reopen submission
            submission.is_complete = False
            submission.graded_at = None
            submission.percentage_score = None

        db.session.commit()
        return jsonify(submission.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@grading_bp.route("/evaluations", methods=["POST"])
def create_evaluation():
    """
    Create a criterion evaluation for a submission.

    Request body:
    {
        "submission_id": "uuid",
        "criterion_id": "uuid",
        "points_awarded": 8.5,
        "feedback": "Good work on clarity"  # optional
    }

    Returns: 201 Created with evaluation data or 400/404/409 on error
    """
    try:
        data = request.get_json()

        # Validation
        if not data.get("submission_id"):
            return jsonify({"error": "submission_id is required"}), 400
        if not data.get("criterion_id"):
            return jsonify({"error": "criterion_id is required"}), 400
        if data.get("points_awarded") is None:
            return jsonify({"error": "points_awarded is required"}), 400

        # Get submission and criterion
        submission = GradedSubmission.query.filter_by(id=data["submission_id"]).first()
        if not submission:
            return jsonify({"error": "Submission not found"}), 404

        criterion = SchemeCriterion.query.filter_by(id=data["criterion_id"]).first()
        if not criterion:
            return jsonify({"error": "Criterion not found"}), 404

        # Validate points range
        points_awarded = Decimal(str(data["points_awarded"]))
        if points_awarded < 0 or points_awarded > criterion.max_points:
            return jsonify({"error": f"points_awarded must be between 0 and {criterion.max_points}"}), 400

        # Check if evaluation already exists (unique constraint)
        existing = CriterionEvaluation.query.filter_by(submission_id=submission.id, criterion_id=criterion.id).first()
        if existing:
            return jsonify({"error": "Evaluation already exists for this criterion"}), 409

        # Create evaluation
        evaluation = CriterionEvaluation(
            submission_id=submission.id,
            criterion_id=criterion.id,
            points_awarded=points_awarded,
            feedback=data.get("feedback"),
            max_points=criterion.max_points,
            criterion_name=criterion.name,
            question_title=criterion.question.title if criterion.question else "",
        )

        db.session.add(evaluation)
        db.session.commit()

        # Auto-calculate submission total
        recalculate_submission_total(submission.id)
        db.session.commit()

        return jsonify(evaluation.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@grading_bp.route("/evaluations/<evaluation_id>", methods=["PUT"])
def update_evaluation(evaluation_id):
    """
    Update a criterion evaluation (points and/or feedback).

    Request body:
    {
        "points_awarded": 9.0,
        "feedback": "Excellent clarity",
        "evaluation_version": 1  # for optimistic locking
    }

    Returns: 200 OK with updated evaluation or 404/409 on error
    """
    try:
        evaluation = CriterionEvaluation.query.filter_by(id=evaluation_id).first()
        if not evaluation:
            return jsonify({"error": "Evaluation not found"}), 404

        data = request.get_json()

        # Validate points range if provided
        if data.get("points_awarded") is not None:
            points_awarded = Decimal(str(data["points_awarded"]))
            if points_awarded < 0 or points_awarded > evaluation.max_points:
                return jsonify({"error": f"points_awarded must be between 0 and {evaluation.max_points}"}), 400
            evaluation.points_awarded = points_awarded

        # Update feedback if provided
        if data.get("feedback") is not None:
            evaluation.feedback = data["feedback"]

        # Update timestamp
        evaluation.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Auto-calculate submission total
        recalculate_submission_total(evaluation.submission_id)
        db.session.commit()

        return jsonify(evaluation.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
