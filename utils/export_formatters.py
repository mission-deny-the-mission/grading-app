"""Formatters for exporting grading results in CSV and JSON formats."""
import csv
import json
from datetime import datetime, timezone
from io import StringIO


def format_csv(submissions, scheme):
    """
    Format grading submissions as denormalized CSV rows.

    CSV structure (one row per criterion evaluation):
    - Student info (id, name)
    - Question title
    - Criterion name
    - Points awarded and max
    - Feedback
    - Grading metadata

    Args:
        submissions: List of GradedSubmission instances
        scheme: GradingScheme instance

    Returns:
        str: CSV content
    """
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    headers = [
        "Student ID",
        "Student Name",
        "Question Title",
        "Criterion Name",
        "Points Awarded",
        "Max Points",
        "Feedback",
        "Graded By",
        "Graded Date",
        "Submission Reference",
    ]
    writer.writerow(headers)

    # Write rows (denormalized - one row per criterion evaluation)
    for submission in submissions:
        student_id = submission.student_id
        student_name = submission.student_name or ""
        graded_by = submission.graded_by or ""
        graded_date = (
            submission.graded_at.isoformat() if submission.graded_at else ""
        )
        submission_ref = submission.submission_reference or ""

        if submission.evaluations:
            for eval in submission.evaluations:
                writer.writerow([
                    student_id,
                    student_name,
                    eval.question_title,
                    eval.criterion_name,
                    float(eval.points_awarded),
                    float(eval.max_points),
                    eval.feedback or "",
                    graded_by,
                    graded_date,
                    submission_ref,
                ])
        else:
            # Write a single row even if no evaluations (incomplete submission)
            writer.writerow([
                student_id,
                student_name,
                "",
                "",
                "",
                "",
                "",
                graded_by,
                graded_date,
                submission_ref,
            ])

    return output.getvalue()


def format_json(submissions, scheme):
    """
    Format grading submissions as hierarchical JSON.

    JSON structure:
    {
        "metadata": {
            "scheme_id": "...",
            "scheme_name": "...",
            "exported_at": "...",
            "total_submissions": N,
            "complete_submissions": N,
        },
        "submissions": [
            {
                "student_id": "...",
                "student_name": "...",
                "graded_at": "...",
                "total_points_earned": X,
                "total_points_possible": Y,
                "percentage_score": Z,
                "questions": [
                    {
                        "title": "...",
                        "total_possible_points": X,
                        "criteria": [
                            {
                                "name": "...",
                                "points_awarded": X,
                                "max_points": Y,
                                "feedback": "..."
                            }
                        ]
                    }
                ]
            }
        ]
    }

    Args:
        submissions: List of GradedSubmission instances
        scheme: GradingScheme instance

    Returns:
        dict: JSON-serializable dictionary
    """
    complete_count = sum(1 for s in submissions if s.is_complete)

    data = {
        "metadata": {
            "scheme_id": scheme.id,
            "scheme_name": scheme.name,
            "scheme_version": scheme.version_number,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_submissions": len(submissions),
            "complete_submissions": complete_count,
        },
        "submissions": [],
    }

    for submission in submissions:
        # Organize evaluations by question
        eval_by_question = {}  # question_id -> [evaluations]
        for eval in submission.evaluations:
            if eval.criterion:
                q_id = eval.criterion.question_id
                if q_id not in eval_by_question:
                    eval_by_question[q_id] = []
                eval_by_question[q_id].append(eval)

        # Build questions section following scheme structure
        questions_data = []
        for question in scheme.questions:
            q_data = {
                "id": question.id,
                "title": question.title,
                "display_order": question.display_order,
                "total_possible_points": float(question.total_possible_points),
                "criteria": [],
            }

            # Add evaluations for this question (maintaining order from schema)
            evaluations = eval_by_question.get(question.id, [])
            eval_by_criterion = {e.criterion_id: e for e in evaluations}

            for criterion in question.criteria:
                eval = eval_by_criterion.get(criterion.id)
                c_data = {
                    "id": criterion.id,
                    "name": criterion.name,
                    "display_order": criterion.display_order,
                    "max_points": float(criterion.max_points),
                }

                if eval:
                    c_data["points_awarded"] = float(eval.points_awarded)
                    c_data["feedback"] = eval.feedback or ""
                else:
                    c_data["points_awarded"] = None
                    c_data["feedback"] = ""

                q_data["criteria"].append(c_data)

            questions_data.append(q_data)

        submission_data = {
            "id": submission.id,
            "student_id": submission.student_id,
            "student_name": submission.student_name or "",
            "submission_reference": submission.submission_reference or "",
            "graded_by": submission.graded_by,
            "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
            "is_complete": submission.is_complete,
            "total_points_earned": float(submission.total_points_earned),
            "total_points_possible": float(submission.total_points_possible),
            "percentage_score": float(submission.percentage_score) if submission.percentage_score else None,
            "questions": questions_data,
        }

        data["submissions"].append(submission_data)

    return data


def format_json_string(submissions, scheme):
    """
    Format grading submissions as JSON string.

    Args:
        submissions: List of GradedSubmission instances
        scheme: GradingScheme instance

    Returns:
        str: JSON string
    """
    json_data = format_json(submissions, scheme)
    return json.dumps(json_data, indent=2, default=str)
