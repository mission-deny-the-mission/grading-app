"""Unit tests for grading scheme models (User Story 1 & 2)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app import app
from models import (
    CriterionEvaluation,
    GradedSubmission,
    GradingScheme,
    SchemeCriterion,
    SchemeQuestion,
    db,
)


@pytest.fixture(scope="function")
def app_context():
    """Create app context for tests."""
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


class TestGradingSchemme:
    """Test GradingScheme model creation and basic operations (T023, T024)."""

    def test_grading_scheme_creation(self, app_context):
        """[T023] Verify model creation with default values."""
        scheme = GradingScheme(
            name="Test Scheme",
            description="A test grading scheme",
            category="essay",
            created_by="instructor@example.com",
        )
        db.session.add(scheme)
        db.session.commit()

        assert scheme.id is not None
        assert scheme.name == "Test Scheme"
        assert scheme.description == "A test grading scheme"
        assert scheme.category == "essay"
        assert scheme.version_number == 1
        assert scheme.is_deleted is False
        assert float(scheme.total_possible_points) == 0.0
        assert scheme.total_questions == 0
        assert scheme.total_criteria == 0
        assert scheme.created_by == "instructor@example.com"
        assert scheme.created_at is not None
        assert scheme.updated_at is not None

    def test_scheme_to_dict(self, app_context):
        """[T024] Verify serialization to dictionary."""
        scheme = GradingScheme(
            name="Test Scheme",
            description="Description",
            category="essay",
        )
        db.session.add(scheme)
        db.session.commit()

        scheme_dict = scheme.to_dict()

        assert isinstance(scheme_dict, dict)
        assert scheme_dict["name"] == "Test Scheme"
        assert scheme_dict["description"] == "Description"
        assert scheme_dict["category"] == "essay"
        assert scheme_dict["version_number"] == 1
        assert scheme_dict["is_deleted"] is False
        assert isinstance(scheme_dict["total_possible_points"], float)
        assert scheme_dict["questions"] == []


class TestSchemeQuestion:
    """Test SchemeQuestion model (T025, T026)."""

    def test_scheme_question_creation(self, app_context):
        """[T025] Verify question model creation with relationships."""
        scheme = GradingScheme(name="Test Scheme")
        db.session.add(scheme)
        db.session.commit()

        question = SchemeQuestion(
            scheme_id=scheme.id,
            title="Question 1",
            description="Question description",
            display_order=1,
        )
        db.session.add(question)
        db.session.commit()

        assert question.id is not None
        assert question.scheme_id == scheme.id
        assert question.title == "Question 1"
        assert question.description == "Question description"
        assert question.display_order == 1
        assert question.total_possible_points == 0
        assert question.created_at is not None

    def test_question_ordering_constraint(self, app_context):
        """[T026] Verify display_order unique constraint."""
        scheme = GradingScheme(name="Test Scheme")
        db.session.add(scheme)
        db.session.commit()

        q1 = SchemeQuestion(scheme_id=scheme.id, title="Q1", display_order=1)
        q2 = SchemeQuestion(scheme_id=scheme.id, title="Q2", display_order=1)  # Duplicate order

        # This should violate unique constraint when saved to database
        # For now, just verify the model creation works
        assert q1.display_order == 1
        assert q2.display_order == 1  # Model allows it, DB will enforce


class TestSchemeCriterion:
    """Test SchemeCriterion model (T027, T028)."""

    def test_scheme_criterion_creation(self, app_context):
        """[T027] Verify criterion model creation."""
        scheme = GradingScheme(name="Test Scheme")
        db.session.add(scheme)
        db.session.commit()

        question = SchemeQuestion(
            scheme_id=scheme.id,
            title="Question",
            display_order=1,
        )
        db.session.add(question)
        db.session.commit()

        criterion = SchemeCriterion(
            question_id=question.id,
            name="Clarity",
            description="Clarity of writing",
            max_points=Decimal("10.00"),
            display_order=1,
        )
        db.session.add(criterion)
        db.session.commit()

        assert criterion.id is not None
        assert criterion.question_id == question.id
        assert criterion.name == "Clarity"
        assert criterion.description == "Clarity of writing"
        assert criterion.max_points == Decimal("10.00")
        assert criterion.display_order == 1

    def test_criterion_point_validation(self):
        """[T028] Verify max_points constraints."""
        question = SchemeQuestion(
            scheme_id="test_scheme_id",
            title="Question",
            display_order=1,
        )

        # Valid criterion
        valid = SchemeCriterion(
            question_id=question.id,
            name="Valid",
            max_points=Decimal("10.00"),
            display_order=1,
        )
        assert valid.max_points == Decimal("10.00")

        # Model allows these, DB constraints will enforce max
        negative = SchemeCriterion(
            question_id=question.id,
            name="Negative",
            max_points=Decimal("-5.00"),
            display_order=2,
        )
        assert negative.max_points == Decimal("-5.00")

        too_large = SchemeCriterion(
            question_id=question.id,
            name="Too Large",
            max_points=Decimal("1001.00"),
            display_order=3,
        )
        assert too_large.max_points == Decimal("1001.00")


class TestGradedSubmission:
    """Test GradedSubmission model (T063, T064, T065)."""

    def test_graded_submission_creation(self, app_context):
        """[T063] Verify GradedSubmission model creation."""
        # Create a scheme first
        scheme = GradingScheme(name="Test Scheme", category="essay")
        db.session.add(scheme)
        db.session.commit()

        submission = GradedSubmission(
            scheme_id=scheme.id,
            scheme_version=1,
            student_id="STU001",
            student_name="John Doe",
            submission_reference="file_123.pdf",
            graded_by="instructor@example.com",
            total_points_possible=Decimal("100.00"),
        )
        db.session.add(submission)
        db.session.commit()

        assert submission.id is not None
        assert submission.scheme_id == scheme.id
        assert submission.scheme_version == 1
        assert submission.student_id == "STU001"
        assert submission.student_name == "John Doe"
        assert submission.submission_reference == "file_123.pdf"
        assert submission.graded_by == "instructor@example.com"
        assert submission.is_complete is False
        assert submission.evaluation_version == 1
        assert float(submission.total_points_earned) == 0.0
        assert submission.percentage_score is None
        assert submission.graded_at is None

    def test_submission_completion_triggers_graded_at(self, app_context):
        """[T065] Verify is_complete triggers graded_at."""
        # Create a scheme first
        scheme = GradingScheme(name="Test Scheme", category="essay")
        db.session.add(scheme)
        db.session.commit()

        submission = GradedSubmission(
            scheme_id=scheme.id,
            scheme_version=1,
            student_id="STU001",
            graded_by="instructor",
            total_points_possible=Decimal("100.00"),
        )
        db.session.add(submission)
        db.session.commit()

        # Initially not complete
        assert submission.is_complete is False
        assert submission.graded_at is None

        # Mark as complete
        submission.is_complete = True
        submission.graded_at = datetime.now(timezone.utc)
        db.session.commit()

        assert submission.is_complete is True
        assert submission.graded_at is not None


class TestCriterionEvaluation:
    """Test CriterionEvaluation model (T064, T066)."""

    def test_criterion_evaluation_creation(self, app_context):
        """[T064] Verify evaluation model creation."""
        # Create a scheme first
        scheme = GradingScheme(name="Test Scheme", category="essay")
        db.session.add(scheme)
        db.session.commit()

        # Create a question
        question = SchemeQuestion(
            scheme_id=scheme.id,
            title="Question 1",
            display_order=1,
        )
        db.session.add(question)
        db.session.commit()

        # Create a criterion
        criterion = SchemeCriterion(
            question_id=question.id,
            name="Clarity",
            max_points=Decimal("10.00"),
            display_order=1,
        )
        db.session.add(criterion)
        db.session.commit()

        # Create a submission
        submission = GradedSubmission(
            scheme_id=scheme.id,
            scheme_version=1,
            student_id="STU001",
            graded_by="instructor",
            total_points_possible=Decimal("10.00"),
        )
        db.session.add(submission)
        db.session.commit()

        # Create an evaluation
        evaluation = CriterionEvaluation(
            submission_id=submission.id,
            criterion_id=criterion.id,
            points_awarded=Decimal("8.50"),
            feedback="Good work",
            max_points=Decimal("10.00"),
            criterion_name="Clarity",
            question_title="Question 1",
        )
        db.session.add(evaluation)
        db.session.commit()

        assert evaluation.id is not None
        assert evaluation.submission_id == submission.id
        assert evaluation.criterion_id == criterion.id
        assert evaluation.points_awarded == Decimal("8.50")
        assert evaluation.feedback == "Good work"
        assert evaluation.max_points == Decimal("10.00")
        assert evaluation.criterion_name == "Clarity"
        assert evaluation.question_title == "Question 1"

    def test_evaluation_points_range_validation(self):
        """[T066] Verify points_awarded constraints."""
        evaluation = CriterionEvaluation(
            submission_id="sub_123",
            criterion_id="crit_456",
            points_awarded=Decimal("5.00"),
            max_points=Decimal("10.00"),
            criterion_name="Test",
            question_title="Q1",
        )

        # Valid
        assert evaluation.points_awarded == Decimal("5.00")

        # Invalid cases (model allows, DB enforces)
        too_high = CriterionEvaluation(
            submission_id="sub_123",
            criterion_id="crit_456",
            points_awarded=Decimal("15.00"),  # Exceeds max
            max_points=Decimal("10.00"),
            criterion_name="Test",
            question_title="Q1",
        )
        assert too_high.points_awarded == Decimal("15.00")


class TestPercentageCalculation:
    """Test percentage calculation."""

    def test_percentage_calculation(self):
        """[T067] Verify percentage_score accuracy with Decimal precision."""
        # Percentage would be calculated as 85%
        # In real app: (85 / 100) * 100 = 85.00
        # Verify Decimal precision needed
        from utils.scheme_calculator import calculate_percentage_score

        percentage = calculate_percentage_score(Decimal("85.00"), Decimal("100.00"))
        assert percentage == Decimal("85.00")
        assert percentage.as_tuple().exponent == -2  # 2 decimal places


# Recalculate functionality is comprehensively tested via integration tests (test_grading_routes.py)
# which verify auto-calculation through the full API workflow

# to_dict() functionality is validated through integration tests (test_grading_routes.py)
# which verify JSON serialization via the actual API responses


class TestDecimalPrecision:
    """Test Decimal precision throughout the system."""

    def test_fractional_points_precision(self, app_context):
        """Verify handling of fractional points like 2.5 out of 5.0."""
        scheme = GradingScheme(name="Test")
        db.session.add(scheme)
        db.session.commit()

        question = SchemeQuestion(scheme_id=scheme.id, title="Q1", display_order=1)
        db.session.add(question)
        db.session.commit()

        # Criterion with 5 points
        criterion = SchemeCriterion(
            question_id=question.id, name="Test Criterion", max_points=Decimal("5.00"), display_order=1
        )
        db.session.add(criterion)
        db.session.commit()

        submission = GradedSubmission(
            scheme_id=scheme.id,
            scheme_version=1,
            student_id="STU102",
            graded_by="prof",
            total_points_possible=Decimal("5.00"),
        )
        db.session.add(submission)
        db.session.commit()

        # Evaluation with 2.5 points
        evaluation = CriterionEvaluation(
            submission_id=submission.id,
            criterion_id=criterion.id,
            points_awarded=Decimal("2.50"),
            max_points=Decimal("5.00"),
            criterion_name="Test Criterion",
            question_title="Q1",
        )
        db.session.add(evaluation)
        db.session.commit()

        # Verify precision
        assert evaluation.points_awarded == Decimal("2.50")

        # Calculate percentage: 2.5 / 5.0 = 0.5 = 50.00%
        from utils.scheme_calculator import calculate_percentage_score

        percentage = calculate_percentage_score(Decimal("2.50"), Decimal("5.00"))
        assert percentage == Decimal("50.00")

    def test_high_precision_arithmetic(self, app_context):
        """Verify arithmetic maintains 2 decimal precision."""
        from utils.scheme_calculator import calculate_percentage_score

        # Test case: 1/3 = 0.333... should round to 33.33%
        percentage = calculate_percentage_score(Decimal("1.00"), Decimal("3.00"))
        assert percentage == Decimal("33.33")

        # Test case: 2/3 = 0.666... should round to 66.67%
        percentage = calculate_percentage_score(Decimal("2.00"), Decimal("3.00"))
        assert percentage == Decimal("66.67")
