"""Validation utilities for grading schemes and criteria."""
from decimal import Decimal


def validate_point_range(points, max_points):
    """
    Validate that points are within the allowed range (0 to max_points).

    Args:
        points: Numeric value to validate
        max_points: Maximum allowed points

    Returns:
        tuple: (is_valid, error_message)

    Raises:
        ValueError: If validation fails with descriptive error message
    """
    try:
        pts = Decimal(str(points)) if points is not None else Decimal("0")
        max_pts = Decimal(str(max_points))
    except (ValueError, TypeError):
        raise ValueError("Points and max_points must be numeric values")

    if pts < 0:
        raise ValueError(f"Points ({pts}) cannot be negative")

    if pts > max_pts:
        raise ValueError(
            f"Points ({pts}) cannot exceed maximum ({max_pts})"
        )

    return (True, None)


def validate_hierarchy(scheme):
    """
    Validate referential integrity of scheme hierarchy.

    Checks:
    - Scheme has at least one question
    - Each question has at least one criterion
    - Display order is sequential and unique per parent
    - Points calculations are correct

    Args:
        scheme: GradingScheme model instance

    Returns:
        tuple: (is_valid, error_message)

    Raises:
        ValueError: If validation fails with descriptive error message
    """
    if not scheme:
        raise ValueError("Scheme cannot be None")

    if not scheme.questions:
        raise ValueError(
            "Scheme must have at least one question"
        )

    # Check questions
    for i, question in enumerate(scheme.questions):
        if not question.criteria:
            raise ValueError(
                f"Question '{question.title}' must have at least one criterion"
            )

        # Check display order is 1-based and unique
        if question.display_order != i + 1:
            raise ValueError(
                f"Question display order must be sequential (expected {i + 1}, got {question.display_order})"
            )

        # Check criterion totals match question total
        criterion_sum = sum(
            Decimal(str(c.max_points)) if c.max_points else Decimal("0")
            for c in question.criteria
        )
        question_total = Decimal(str(question.total_possible_points)) if question.total_possible_points else Decimal("0")

        if criterion_sum != question_total:
            raise ValueError(
                f"Question '{question.title}' criterion sum ({criterion_sum}) does not match total ({question_total})"
            )

        # Check criteria
        for j, criterion in enumerate(question.criteria):
            if not criterion.name or not criterion.name.strip():
                raise ValueError(
                    f"Criterion {j + 1} in question '{question.title}' must have a name"
                )

            if criterion.max_points <= 0:
                raise ValueError(
                    f"Criterion '{criterion.name}' must have max_points > 0"
                )

            if criterion.max_points > 1000:
                raise ValueError(
                    f"Criterion '{criterion.name}' exceeds maximum points (1000)"
                )

            # Check display order
            if criterion.display_order != j + 1:
                raise ValueError(
                    f"Criterion display order in '{question.title}' must be sequential (expected {j + 1}, got {criterion.display_order})"
                )

    # Check scheme total matches question sums
    question_sum = sum(
        Decimal(str(q.total_possible_points)) if q.total_possible_points else Decimal("0")
        for q in scheme.questions
    )
    scheme_total = Decimal(str(scheme.total_possible_points)) if scheme.total_possible_points else Decimal("0")

    if question_sum != scheme_total:
        raise ValueError(
            f"Scheme question sum ({question_sum}) does not match total ({scheme_total})"
        )

    return (True, None)


def validate_scheme_name(name):
    """
    Validate grading scheme name.

    Args:
        name: Scheme name string

    Returns:
        tuple: (is_valid, error_message)

    Raises:
        ValueError: If validation fails
    """
    if not name or not name.strip():
        raise ValueError("Scheme name cannot be empty")

    if len(name) > 255:
        raise ValueError("Scheme name cannot exceed 255 characters")

    return (True, None)


def validate_submission_points(submission):
    """
    Validate that submission totals are within valid ranges.

    Args:
        submission: GradedSubmission model instance

    Returns:
        tuple: (is_valid, error_message)

    Raises:
        ValueError: If validation fails
    """
    if not submission:
        raise ValueError("Submission cannot be None")

    earned = Decimal(str(submission.total_points_earned)) if submission.total_points_earned else Decimal("0")
    possible = Decimal(str(submission.total_points_possible)) if submission.total_points_possible else Decimal("0")

    if earned < 0:
        raise ValueError("Total points earned cannot be negative")

    if earned > possible:
        raise ValueError(
            f"Points earned ({earned}) cannot exceed possible ({possible})"
        )

    # If complete, percentage must be calculated
    if submission.is_complete and possible > 0:
        if submission.percentage_score is None:
            raise ValueError(
                "Complete submission must have percentage_score calculated"
            )

        percentage = Decimal(str(submission.percentage_score))
        if percentage < 0 or percentage > 100:
            raise ValueError(
                f"Percentage score must be between 0 and 100 (got {percentage})"
            )

    return (True, None)
