"""Unit tests for grading scheme validation utilities."""
import pytest
from decimal import Decimal
from utils.scheme_validator import (
    validate_point_range,
    validate_hierarchy,
    validate_scheme_name,
    validate_submission_points,
)


class TestValidatePointRange:
    """Test point range validation (T031, US1)."""

    def test_valid_point_range(self):
        """Valid points within range."""
        is_valid, error = validate_point_range(Decimal("5.00"), Decimal("10.00"))
        assert is_valid is True
        assert error is None

    def test_zero_points_valid(self):
        """Zero points is valid."""
        is_valid, error = validate_point_range(Decimal("0"), Decimal("10.00"))
        assert is_valid is True

    def test_equal_to_max(self):
        """Points equal to max is valid."""
        is_valid, error = validate_point_range(Decimal("10.00"), Decimal("10.00"))
        assert is_valid is True

    def test_negative_points_invalid(self):
        """Negative points should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_point_range(Decimal("-1.00"), Decimal("10.00"))

    def test_points_exceed_max_invalid(self):
        """Points exceeding max should raise ValueError."""
        with pytest.raises(ValueError, match="cannot exceed maximum"):
            validate_point_range(Decimal("15.00"), Decimal("10.00"))

    def test_non_numeric_points_invalid(self):
        """Non-numeric points should raise ValueError."""
        with pytest.raises(ValueError, match="must be numeric values"):
            validate_point_range("abc", Decimal("10.00"))

    def test_none_points_treated_as_zero(self):
        """None points should be treated as 0."""
        is_valid, error = validate_point_range(None, Decimal("10.00"))
        assert is_valid is True


class TestValidateHierarchy:
    """Test scheme hierarchy validation (T020, US1)."""

    def test_valid_hierarchy(self):
        """Valid complete hierarchy."""
        class MockCriterion:
            def __init__(self, name, max_points, display_order):
                self.name = name
                self.max_points = Decimal(str(max_points))
                self.display_order = display_order

        class MockQuestion:
            def __init__(self, title, total, display_order, criteria):
                self.title = title
                self.total_possible_points = Decimal(str(total))
                self.display_order = display_order
                self.criteria = criteria

        class MockScheme:
            def __init__(self, total, questions):
                self.total_possible_points = Decimal(str(total))
                self.questions = questions

        criteria = [
            MockCriterion("C1", 5, 1),
            MockCriterion("C2", 5, 2),
        ]
        questions = [
            MockQuestion("Q1", 10, 1, criteria),
        ]
        scheme = MockScheme(10, questions)

        is_valid, error = validate_hierarchy(scheme)
        assert is_valid is True
        assert error is None

    def test_none_scheme_invalid(self):
        """None scheme should raise ValueError."""
        with pytest.raises(ValueError, match="Scheme cannot be None"):
            validate_hierarchy(None)

    def test_no_questions_invalid(self):
        """Scheme without questions should raise ValueError."""
        class MockScheme:
            questions = []

        with pytest.raises(ValueError, match="must have at least one question"):
            validate_hierarchy(MockScheme())

    def test_question_without_criteria_invalid(self):
        """Question without criteria should raise ValueError."""
        class MockQuestion:
            title = "Q1"
            criteria = []
            display_order = 1

        class MockScheme:
            questions = [MockQuestion()]

        with pytest.raises(ValueError, match="must have at least one criterion"):
            validate_hierarchy(MockScheme())

    def test_invalid_question_order(self):
        """Non-sequential display order should raise ValueError."""
        class MockCriterion:
            def __init__(self):
                self.name = "C1"
                self.max_points = Decimal("10.00")
                self.display_order = 1

        class MockQuestion:
            def __init__(self):
                self.title = "Q1"
                self.total_possible_points = Decimal("10.00")
                self.display_order = 2  # Should be 1
                self.criteria = [MockCriterion()]

        class MockScheme:
            def __init__(self):
                self.total_possible_points = Decimal("10.00")
                self.questions = [MockQuestion()]

        with pytest.raises(ValueError, match="display order must be sequential"):
            validate_hierarchy(MockScheme())

    def test_criterion_sum_mismatch(self):
        """Criterion sum not matching question total."""
        class MockCriterion:
            def __init__(self, name, max_points, display_order):
                self.name = name
                self.max_points = Decimal(str(max_points))
                self.display_order = display_order

        class MockQuestion:
            def __init__(self):
                self.title = "Q1"
                self.total_possible_points = Decimal("15.00")  # Doesn't match criteria sum
                self.display_order = 1
                self.criteria = [
                    MockCriterion("C1", 5, 1),
                    MockCriterion("C2", 5, 2),  # Sum = 10, not 15
                ]

        class MockScheme:
            def __init__(self):
                self.total_possible_points = Decimal("15.00")
                self.questions = [MockQuestion()]

        with pytest.raises(ValueError, match="does not match total"):
            validate_hierarchy(MockScheme())

    def test_negative_criterion_points(self):
        """Negative criterion points should raise ValueError."""
        class MockCriterion:
            def __init__(self):
                self.name = "C1"
                self.max_points = Decimal("-5.00")
                self.display_order = 1

        class MockQuestion:
            def __init__(self):
                self.title = "Q1"
                self.total_possible_points = Decimal("-5.00")
                self.display_order = 1
                self.criteria = [MockCriterion()]

        class MockScheme:
            def __init__(self):
                self.total_possible_points = Decimal("-5.00")
                self.questions = [MockQuestion()]

        with pytest.raises(ValueError, match="must have max_points > 0"):
            validate_hierarchy(MockScheme())

    def test_criterion_exceeds_max(self):
        """Criterion exceeding 1000 points."""
        class MockCriterion:
            def __init__(self):
                self.name = "C1"
                self.max_points = Decimal("1001.00")
                self.display_order = 1

        class MockQuestion:
            def __init__(self):
                self.title = "Q1"
                self.total_possible_points = Decimal("1001.00")
                self.display_order = 1
                self.criteria = [MockCriterion()]

        class MockScheme:
            def __init__(self):
                self.total_possible_points = Decimal("1001.00")
                self.questions = [MockQuestion()]

        with pytest.raises(ValueError, match="exceeds maximum points"):
            validate_hierarchy(MockScheme())


class TestValidateSchemeName:
    """Test scheme name validation."""

    def test_valid_name(self):
        """Valid scheme name."""
        is_valid, error = validate_scheme_name("Essay Rubric Fall 2024")
        assert is_valid is True

    def test_empty_name_invalid(self):
        """Empty name should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_scheme_name("")

    def test_whitespace_only_invalid(self):
        """Whitespace-only name should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_scheme_name("   ")

    def test_name_too_long_invalid(self):
        """Name exceeding 255 characters."""
        long_name = "A" * 256
        with pytest.raises(ValueError, match="cannot exceed 255"):
            validate_scheme_name(long_name)


class TestValidateSubmissionPoints:
    """Test submission points validation."""

    def test_valid_submission(self):
        """Valid submission points."""
        class MockSubmission:
            def __init__(self):
                self.total_points_earned = Decimal("85.00")
                self.total_points_possible = Decimal("100.00")
                self.percentage_score = Decimal("85.00")
                self.is_complete = True

        is_valid, error = validate_submission_points(MockSubmission())
        assert is_valid is True

    def test_none_submission_invalid(self):
        """None submission should raise ValueError."""
        with pytest.raises(ValueError, match="Submission cannot be None"):
            validate_submission_points(None)

    def test_negative_earned_points_invalid(self):
        """Negative earned points."""
        class MockSubmission:
            def __init__(self):
                self.total_points_earned = Decimal("-10.00")
                self.total_points_possible = Decimal("100.00")
                self.percentage_score = None
                self.is_complete = False

        with pytest.raises(ValueError, match="cannot be negative"):
            validate_submission_points(MockSubmission())

    def test_earned_exceeds_possible_invalid(self):
        """Earned points exceeding possible."""
        class MockSubmission:
            def __init__(self):
                self.total_points_earned = Decimal("150.00")
                self.total_points_possible = Decimal("100.00")
                self.percentage_score = None
                self.is_complete = False

        with pytest.raises(ValueError, match="cannot exceed possible"):
            validate_submission_points(MockSubmission())

    def test_complete_without_percentage_invalid(self):
        """Complete submission without percentage score."""
        class MockSubmission:
            def __init__(self):
                self.total_points_earned = Decimal("50.00")
                self.total_points_possible = Decimal("100.00")
                self.percentage_score = None
                self.is_complete = True

        with pytest.raises(ValueError, match="must have percentage_score"):
            validate_submission_points(MockSubmission())

    def test_invalid_percentage_range(self):
        """Percentage score outside 0-100 range."""
        class MockSubmission:
            def __init__(self):
                self.total_points_earned = Decimal("50.00")
                self.total_points_possible = Decimal("100.00")
                self.percentage_score = Decimal("150.00")
                self.is_complete = True

        with pytest.raises(ValueError, match="between 0 and 100"):
            validate_submission_points(MockSubmission())
