"""Unit tests for grading scheme calculator utilities."""
import pytest
from decimal import Decimal
from utils.scheme_calculator import (
    calculate_scheme_total,
    calculate_question_total,
    calculate_submission_total,
    calculate_percentage_score,
    calculate_aggregate_stats,
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
                self.criterion = type('obj', (object,), {
                    'question_id': question_id
                })()

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
                self.criterion = type('obj', (object,), {
                    'question_id': question_id
                })()

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
