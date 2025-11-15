"""Utilities for calculating grading scheme totals and percentages."""

from decimal import Decimal


def calculate_scheme_total(scheme):
    """
    Calculate total possible points for a grading scheme.

    Args:
        scheme: GradingScheme model instance

    Returns:
        Decimal: Sum of all question totals
    """
    if not scheme.questions:
        return Decimal("0.00")

    total = sum(
        Decimal(str(q.total_possible_points)) if q.total_possible_points else Decimal("0.00") for q in scheme.questions
    )
    return total.quantize(Decimal("0.01"))


def calculate_question_total(question):
    """
    Calculate total possible points for a scheme question.

    Args:
        question: SchemeQuestion model instance

    Returns:
        Decimal: Sum of all criterion max_points
    """
    if not question.criteria:
        return Decimal("0.00")

    total = sum(Decimal(str(c.max_points)) if c.max_points else Decimal("0.00") for c in question.criteria)
    return total.quantize(Decimal("0.01"))


def calculate_submission_total(submission):
    """
    Calculate total points earned for a graded submission.

    Args:
        submission: GradedSubmission model instance

    Returns:
        Decimal: Sum of all criterion evaluation points
    """
    if not submission.evaluations:
        return Decimal("0.00")

    total = sum(Decimal(str(e.points_awarded)) if e.points_awarded else Decimal("0.00") for e in submission.evaluations)
    return total.quantize(Decimal("0.01"))


def calculate_percentage_score(points_earned, points_possible):
    """
    Calculate percentage score with 2-decimal precision.

    Args:
        points_earned: Decimal or numeric points earned
        points_possible: Decimal or numeric points possible

    Returns:
        Decimal: Percentage score (0-100) or None if points_possible is 0
    """
    if not points_possible or Decimal(str(points_possible)) == 0:
        return None

    earned = Decimal(str(points_earned))
    possible = Decimal(str(points_possible))

    percentage = (earned / possible) * Decimal("100")
    return percentage.quantize(Decimal("0.01"))


def calculate_aggregate_stats(submissions):
    """
    Calculate aggregate statistics for a group of submissions.

    Args:
        submissions: List of GradedSubmission instances

    Returns:
        dict: Statistics including averages per criterion and question
    """
    if not submissions:
        return {
            "total_submissions": 0,
            "average_percentage": None,
            "average_points": None,
            "criteria_averages": {},
            "question_averages": {},
        }

    # Filter complete submissions
    complete = [s for s in submissions if s.is_complete]

    if not complete:
        return {
            "total_submissions": len(submissions),
            "complete_submissions": 0,
            "average_percentage": None,
            "average_points": None,
            "criteria_averages": {},
            "question_averages": {},
        }

    # Calculate submission-level averages
    percentages = [Decimal(str(s.percentage_score)) for s in complete if s.percentage_score]
    avg_percentage = sum(percentages) / len(percentages) if percentages else None
    if avg_percentage:
        avg_percentage = avg_percentage.quantize(Decimal("0.01"))

    points = [Decimal(str(s.total_points_earned)) for s in complete]
    avg_points = sum(points) / len(points) if points else None
    if avg_points:
        avg_points = avg_points.quantize(Decimal("0.01"))

    # Calculate criterion-level averages
    criteria_data = {}  # criterion_id -> [points_list]
    question_data = {}  # question_id -> [points_list]

    for submission in complete:
        for eval in submission.evaluations:
            criterion_id = eval.criterion_id
            if criterion_id not in criteria_data:
                criteria_data[criterion_id] = []
            criteria_data[criterion_id].append(Decimal(str(eval.points_awarded)))

            # Also track by question via criterion's question
            if eval.criterion:
                question_id = eval.criterion.question_id
                if question_id not in question_data:
                    question_data[question_id] = []
                question_data[question_id].append(Decimal(str(eval.points_awarded)))

    criteria_averages = {
        cid: float((sum(pts) / len(pts)).quantize(Decimal("0.01"))) for cid, pts in criteria_data.items()
    }

    question_averages = {
        qid: float((sum(pts) / len(pts)).quantize(Decimal("0.01"))) for qid, pts in question_data.items()
    }

    return {
        "total_submissions": len(submissions),
        "complete_submissions": len(complete),
        "average_percentage": float(avg_percentage) if avg_percentage else None,
        "average_points": float(avg_points) if avg_points else None,
        "criteria_averages": criteria_averages,
        "question_averages": question_averages,
    }
