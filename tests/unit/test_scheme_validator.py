"""Unit tests for grading scheme validation utilities."""

from decimal import Decimal

import pytest

from utils.scheme_validator import (
    validate_hierarchy,
    validate_scheme_name,
)


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
