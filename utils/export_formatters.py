"""Export formatters for grading data.

Provides CSV and JSON formatting for grading results with support for
hierarchical structure preservation and metadata inclusion.
"""

import csv
import json
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO


def format_csv(submissions):
    """
    Format grading submissions as CSV with denormalized rows.

    Each row represents one criterion evaluation for one student, with
    columns for student info, question/category, criterion, and grades.

    Args:
        submissions: List of GradedSubmission.to_dict() objects

    Returns:
        str: CSV-formatted string with headers and data rows
    """
    output = StringIO()
    writer = csv.writer(output)

    # Write headers
    headers = [
        "Student ID",
        "Student Name",
        "Scheme",
        "Question/Category",
        "Criterion",
        "Points Earned",
        "Max Points",
        "Feedback",
        "Percentage Score",
        "Graded By",
        "Graded At",
        "Submission Date",
    ]
    writer.writerow(headers)

    # Write data rows (one row per evaluation)
    for submission in submissions:
        student_id = submission.get("student_id", "")
        student_name = submission.get("student_name", "")
        scheme_name = submission.get("scheme_name", "")
        percentage_score = submission.get("percentage_score", "")
        graded_by = submission.get("graded_by", "")
        graded_at = submission.get("graded_at", "")

        evaluations = submission.get("evaluations", [])

        if not evaluations:
            # Write submission row even with no evaluations
            writer.writerow(
                [
                    student_id,
                    student_name,
                    scheme_name,
                    "",
                    "",
                    "",
                    "",
                    "",
                    _format_decimal(percentage_score),
                    graded_by,
                    _format_datetime(graded_at),
                    _format_datetime(submission.get("created_at", "")),
                ]
            )
        else:
            # Write one row per evaluation
            for evaluation in evaluations:
                writer.writerow(
                    [
                        student_id,
                        student_name,
                        scheme_name,
                        evaluation.get("question_title", ""),
                        evaluation.get("criterion_name", ""),
                        _format_decimal(evaluation.get("points_awarded", "")),
                        _format_decimal(evaluation.get("max_points", "")),
                        evaluation.get("feedback", ""),
                        _format_decimal(percentage_score),
                        graded_by,
                        _format_datetime(graded_at),
                        _format_datetime(submission.get("created_at", "")),
                    ]
                )

    return output.getvalue()


def format_json(submissions):
    """
    Format grading submissions as JSON with hierarchical structure.

    Preserves the question → criterion → evaluation hierarchy and includes
    metadata about the export.

    Args:
        submissions: List of GradedSubmission.to_dict() objects

    Returns:
        str: JSON-formatted string with submissions and metadata
    """
    # Prepare submissions data
    submissions_data = []

    for submission in submissions:
        submission_data = {
            "submission_id": submission.get("id", ""),
            "student_id": submission.get("student_id", ""),
            "student_name": submission.get("student_name", ""),
            "scheme_id": submission.get("scheme_id", ""),
            "scheme_version": submission.get("scheme_version", ""),
            "total_points_earned": _decimal_to_float(submission.get("total_points_earned", 0)),
            "total_points_possible": _decimal_to_float(submission.get("total_points_possible", 0)),
            "percentage_score": _decimal_to_float(submission.get("percentage_score")),
            "is_complete": submission.get("is_complete", False),
            "graded_by": submission.get("graded_by", ""),
            "graded_at": _format_datetime(submission.get("graded_at", "")),
            "created_at": _format_datetime(submission.get("created_at", "")),
            "evaluations": [],
        }

        # Add evaluations
        evaluations = submission.get("evaluations", [])
        for evaluation in evaluations:
            eval_data = {
                "criterion_name": evaluation.get("criterion_name", ""),
                "question_title": evaluation.get("question_title", ""),
                "points_awarded": _decimal_to_float(evaluation.get("points_awarded", 0)),
                "max_points": _decimal_to_float(evaluation.get("max_points", 0)),
                "feedback": evaluation.get("feedback"),
            }
            submission_data["evaluations"].append(eval_data)

        submissions_data.append(submission_data)

    # Build export structure with metadata
    export_data = {
        "metadata": {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "total_submissions": len(submissions_data),
            "scheme_name": (submissions[0].get("scheme_name", "") if submissions else ""),
        },
        "submissions": submissions_data,
    }

    return json.dumps(export_data, indent=2)


def _format_decimal(value):
    """Format Decimal value as string for CSV output."""
    if value is None or value == "":
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _decimal_to_float(value):
    """Convert Decimal to float for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value != "" else None


def _format_datetime(value):
    """Format datetime for export output."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
