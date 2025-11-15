"""Unit tests for grading scheme calculator utilities."""

from decimal import Decimal

import pytest

from utils.scheme_calculator import (
    calculate_aggregate_stats,
    calculate_percentage_score,
    calculate_question_total,
    calculate_scheme_total,
    calculate_submission_total,
)


class TestCalculateSchemeTotal:
    """Test calculate_scheme_total utility (T029, US1)."""

    def test_calculate_scheme_total_empty(self):
        """Empty scheme should return 0.00."""

        class MockScheme:
            questions = []

        scheme = MockScheme()
        total = calculate_scheme_total(scheme)

        assert total == Decimal("0.00")

    def test_calculate_scheme_total_single_question(self):
        """Scheme with one question should sum its total."""

        class MockQuestion:
            total_possible_points = Decimal("50.00")

        class MockScheme:
            questions = [MockQuestion()]

        scheme = MockScheme()
        total = calculate_scheme_total(scheme)

        assert total == Decimal("50.00")

    def test_calculate_scheme_total_multiple_questions(self):
        """Scheme with multiple questions should sum all."""

        class MockQuestion:
            def __init__(self, points):
                self.total_possible_points = points

        class MockScheme:
            questions = [
                MockQuestion(Decimal("25.00")),
                MockQuestion(Decimal("30.00")),
                MockQuestion(Decimal("45.00")),
            ]

        scheme = MockScheme()
        total = calculate_scheme_total(scheme)

        assert total == Decimal("100.00")

    def test_calculate_scheme_total_precision(self):
        """Result should maintain 2 decimal places."""

        class MockQuestion:
            def __init__(self, points):
                self.total_possible_points = points

        class MockScheme:
            questions = [
                MockQuestion(Decimal("10.33")),
                MockQuestion(Decimal("20.67")),
            ]

        scheme = MockScheme()
        total = calculate_scheme_total(scheme)

        assert total == Decimal("31.00")
        assert total.as_tuple().exponent == -2


class TestCalculateQuestionTotal:
    """Test calculate_question_total utility (T030, US1)."""

    def test_calculate_question_total_empty(self):
        """Question with no criteria should return 0.00."""

        class MockQuestion:
            criteria = []

        question = MockQuestion()
        total = calculate_question_total(question)

        assert total == Decimal("0.00")

    def test_calculate_question_total_single_criterion(self):
        """Question with one criterion."""

        class MockCriterion:
            max_points = Decimal("10.00")

        class MockQuestion:
            criteria = [MockCriterion()]

        question = MockQuestion()
        total = calculate_question_total(question)

        assert total == Decimal("10.00")

    def test_calculate_question_total_multiple_criteria(self):
        """Question with multiple criteria."""

        class MockCriterion:
            def __init__(self, points):
                self.max_points = points

        class MockQuestion:
            criteria = [
                MockCriterion(Decimal("5.00")),
                MockCriterion(Decimal("3.50")),
                MockCriterion(Decimal("1.50")),
            ]

        question = MockQuestion()
        total = calculate_question_total(question)

        assert total == Decimal("10.00")


class TestCalculateSubmissionTotal:
    """Test calculate_submission_total utility (US2)."""

    def test_calculate_submission_total_empty(self):
        """Submission with no evaluations."""

        class MockSubmission:
            evaluations = []

        submission = MockSubmission()
        total = calculate_submission_total(submission)

        assert total == Decimal("0.00")

    def test_calculate_submission_total_single_evaluation(self):
        """Submission with one evaluation."""

        class MockEvaluation:
            points_awarded = Decimal("8.00")

        class MockSubmission:
            evaluations = [MockEvaluation()]

        submission = MockSubmission()
        total = calculate_submission_total(submission)

        assert total == Decimal("8.00")

    def test_calculate_submission_total_multiple_evaluations(self):
        """Submission with multiple evaluations."""

        class MockEvaluation:
            def __init__(self, points):
                self.points_awarded = points

        class MockSubmission:
            evaluations = [
                MockEvaluation(Decimal("8.00")),
                MockEvaluation(Decimal("7.50")),
                MockEvaluation(Decimal("9.00")),
                MockEvaluation(Decimal("8.50")),
            ]

        submission = MockSubmission()
        total = calculate_submission_total(submission)

        assert total == Decimal("33.00")


class TestCalculatePercentageScore:
    """Test percentage score calculation (T067, US2)."""

    def test_percentage_basic(self):
        """Basic percentage calculation."""
        percentage = calculate_percentage_score(Decimal("85"), Decimal("100"))
        assert percentage == Decimal("85.00")

    def test_percentage_with_decimals(self):
        """Percentage with decimal points."""
        percentage = calculate_percentage_score(Decimal("17.50"), Decimal("50.00"))
        assert percentage == Decimal("35.00")

    def test_percentage_high_precision(self):
        """Precision to 2 decimal places."""
        percentage = calculate_percentage_score(Decimal("1"), Decimal("3"))
        # 1/3 * 100 = 33.33...
        assert percentage == Decimal("33.33")

    def test_percentage_perfect_score(self):
        """Perfect score is 100%."""
        percentage = calculate_percentage_score(Decimal("100"), Decimal("100"))
        assert percentage == Decimal("100.00")

    def test_percentage_zero_score(self):
        """Zero earned points is 0%."""
        percentage = calculate_percentage_score(Decimal("0"), Decimal("100"))
        assert percentage == Decimal("0.00")

    def test_percentage_zero_possible(self):
        """Zero possible points returns None."""
        percentage = calculate_percentage_score(Decimal("0"), Decimal("0"))
        assert percentage is None

    def test_percentage_none_possible(self):
        """None possible points returns None."""
        percentage = calculate_percentage_score(Decimal("10"), None)
        assert percentage is None

    def test_percentage_result_precision(self):
        """Result always has 2 decimal places."""
        percentage = calculate_percentage_score(Decimal("1"), Decimal("2"))
        # 1/2 * 100 = 50.00
        assert percentage == Decimal("50.00")
        assert percentage.as_tuple().exponent == -2


class TestAggregateStats:
    """Test aggregate statistics calculation (US3 export)."""

    def test_aggregate_stats_empty_list(self):
        """Empty submission list."""
        stats = calculate_aggregate_stats([])

        assert stats["total_submissions"] == 0
        assert stats["average_percentage"] is None
        assert stats["average_points"] is None
        assert stats["criteria_averages"] == {}
        assert stats["question_averages"] == {}

    def test_aggregate_stats_incomplete_only(self):
        """Only incomplete submissions."""

        class MockSubmission:
            def __init__(self):
                self.is_complete = False

        submissions = [MockSubmission(), MockSubmission()]
        stats = calculate_aggregate_stats(submissions)

        assert stats["total_submissions"] == 2
        assert stats["complete_submissions"] == 0
        assert stats["average_percentage"] is None

    def test_aggregate_stats_single_complete(self):
        """Single complete submission."""

        class MockEvaluation:
            def __init__(self, criterion_id, question_id, points):
                self.criterion_id = criterion_id
                self.points_awarded = Decimal(str(points))
                self.criterion = type("obj", (object,), {"question_id": question_id})()

        class MockSubmission:
            def __init__(self):
                self.is_complete = True
                self.total_points_earned = Decimal("80.00")
                self.total_points_possible = Decimal("100.00")
                self.percentage_score = Decimal("80.00")
                self.evaluations = [
                    MockEvaluation("c1", "q1", 8),
                    MockEvaluation("c2", "q1", 10),
                ]

        submissions = [MockSubmission()]
        stats = calculate_aggregate_stats(submissions)

        assert stats["total_submissions"] == 1
        assert stats["complete_submissions"] == 1
        assert stats["average_percentage"] == Decimal("80.00")
        assert stats["average_points"] == Decimal("80.00")
        assert "c1" in stats["criteria_averages"]
        assert "q1" in stats["question_averages"]

    def test_aggregate_stats_multiple_complete(self):
        """Multiple complete submissions."""

        class MockEvaluation:
            def __init__(self, criterion_id, question_id, points):
                self.criterion_id = criterion_id
                self.points_awarded = Decimal(str(points))
                self.criterion = type("obj", (object,), {"question_id": question_id})()

        class MockSubmission:
            def __init__(self, earned, possible, percentage):
                self.is_complete = True
                self.total_points_earned = Decimal(str(earned))
                self.total_points_possible = Decimal(str(possible))
                self.percentage_score = Decimal(str(percentage))
                self.evaluations = [
                    MockEvaluation("c1", "q1", earned / 2),
                    MockEvaluation("c2", "q1", earned / 2),
                ]

        submissions = [
            MockSubmission(80, 100, 80),
            MockSubmission(90, 100, 90),
            MockSubmission(70, 100, 70),
        ]
        stats = calculate_aggregate_stats(submissions)

        assert stats["total_submissions"] == 3
        assert stats["complete_submissions"] == 3
        assert stats["average_percentage"] == Decimal("80.00")
        assert stats["average_points"] == Decimal("80.00")


class TestFractionalPointsEdgeCases:
    """Test edge cases with fractional points (T129)."""

    def test_fractional_points_basic(self):
        """Test calculation with fractional criterion points (2.5 out of 5.0)."""

        class MockCriterion:
            def __init__(self):
                self.max_points = Decimal("2.50")

        class MockQuestion:
            def __init__(self):
                self.criteria = [MockCriterion(), MockCriterion()]
                self.total_possible_points = Decimal("5.00")

        class MockScheme:
            def __init__(self):
                self.questions = [MockQuestion()]
                self.total_possible_points = Decimal("5.00")

        scheme = MockScheme()
        total = calculate_scheme_total(scheme)
        assert total == Decimal("5.00")

    def test_fractional_points_quarter_values(self):
        """Test calculations with quarter-point increments (0.25)."""

        class MockCriterion:
            def __init__(self):
                self.max_points = Decimal("0.25")

        class MockQuestion:
            def __init__(self):
                # 4 criteria × 0.25 = 1.00
                self.criteria = [MockCriterion() for _ in range(4)]
                self.total_possible_points = Decimal("1.00")

        class MockScheme:
            def __init__(self):
                self.questions = [MockQuestion()]
                self.total_possible_points = Decimal("1.00")

        scheme = MockScheme()
        total = calculate_scheme_total(scheme)
        assert total == Decimal("1.00")

    def test_percentage_with_fractional_earned_points(self):
        """Test percentage calculation with fractional earned points (3.75 out of 5.0)."""
        earned = Decimal("3.75")
        possible = Decimal("5.00")

        percentage = calculate_percentage_score(earned, possible)

        # 3.75 / 5.0 * 100 = 75.00
        assert percentage == Decimal("75.00")

    def test_percentage_with_many_decimal_places_rounds_correctly(self):
        """Test that percentage rounds to 2 decimal places with repeating decimals."""
        earned = Decimal("10")
        possible = Decimal("3")  # 10/3 = 3.333... * 100 = 333.333...

        percentage = calculate_percentage_score(earned, possible)

        # Should be rounded/truncated to 2 decimal places
        assert percentage == Decimal("333.33")

    def test_submission_total_with_mixed_fractional_evaluations(self):
        """Test submission total with mixed fractional evaluated points."""

        class MockEvaluation:
            def __init__(self, points):
                self.points_awarded = Decimal(str(points))

        class MockSubmission:
            def __init__(self):
                self.evaluations = [
                    MockEvaluation("2.50"),
                    MockEvaluation("1.75"),
                    MockEvaluation("0.33"),
                ]

        submission = MockSubmission()
        total = calculate_submission_total(submission)

        # 2.50 + 1.75 + 0.33 = 4.58
        assert total == Decimal("4.58")

    def test_fractional_points_precision_maintained(self):
        """Test that Decimal precision is maintained through calculations."""
        earned = Decimal("2.33")
        possible = Decimal("7.00")

        percentage = calculate_percentage_score(earned, possible)

        # 2.33 / 7.00 * 100 = 33.28571... → should round to 33.29
        assert percentage == Decimal("33.29")

    def test_very_small_fractional_points(self):
        """Test calculations with very small point values (0.01)."""

        class MockEvaluation:
            def __init__(self):
                self.points_awarded = Decimal("0.01")

        class MockSubmission:
            def __init__(self):
                self.evaluations = [MockEvaluation() for _ in range(100)]

        submission = MockSubmission()
        total = calculate_submission_total(submission)

        # 0.01 * 100 = 1.00
        assert total == Decimal("1.00")
