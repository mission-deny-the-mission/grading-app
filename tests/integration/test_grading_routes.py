"""Integration tests for grading routes (User Story 2)."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from app import app
from models import (
    db,
    GradingScheme,
    SchemeQuestion,
    SchemeCriterion,
    GradedSubmission,
    CriterionEvaluation,
)


@pytest.fixture(scope="function")
def app_context():
    """Create app context for tests."""
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_context):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_scheme(app_context):
    """Create a sample grading scheme for testing."""
    scheme = GradingScheme(
        name="Test Essay Rubric",
        description="Sample rubric for essay grading",
        category="essay",
        created_by="instructor@example.com"
    )
    db.session.add(scheme)
    db.session.commit()

    # Add question
    question = SchemeQuestion(
        scheme_id=scheme.id,
        title="Question 1: Argument Quality",
        description="Evaluate the quality and clarity of arguments",
        display_order=1
    )
    db.session.add(question)
    db.session.commit()

    # Add criteria
    criteria = [
        SchemeCriterion(
            question_id=question.id,
            name="Thesis Clarity",
            description="Is the thesis clear and well-stated?",
            max_points=Decimal("10.00"),
            display_order=1
        ),
        SchemeCriterion(
            question_id=question.id,
            name="Argument Support",
            description="Are arguments well-supported?",
            max_points=Decimal("10.00"),
            display_order=2
        ),
        SchemeCriterion(
            question_id=question.id,
            name="Grammar and Clarity",
            description="Grammar and writing clarity",
            max_points=Decimal("5.00"),
            display_order=3
        ),
    ]
    for criterion in criteria:
        db.session.add(criterion)
    db.session.commit()

    # Recalculate scheme totals
    question.total_possible_points = Decimal("25.00")
    scheme.total_possible_points = Decimal("25.00")
    scheme.total_questions = 1
    scheme.total_criteria = 3
    db.session.commit()

    return scheme


class TestCreateSubmission:
    """Test submission creation endpoint (T068)."""

    def test_create_submission_success(self, client, sample_scheme):
        """[T068] Verify submission creation with valid data."""
        response = client.post("/api/grading/submissions", json={
            "scheme_id": sample_scheme.id,
            "student_id": "STU001",
            "student_name": "Alice Smith",
            "submission_reference": "essay_001.pdf",
            "graded_by": "prof@example.com"
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data["student_id"] == "STU001"
        assert data["student_name"] == "Alice Smith"
        assert data["is_complete"] is False
        assert data["evaluation_version"] == 1
        assert float(data["total_points_earned"]) == 0.0
        assert float(data["total_points_possible"]) == 25.0

    def test_create_submission_missing_required_fields(self, client, sample_scheme):
        """Verify error handling for missing required fields."""
        # Missing scheme_id
        response = client.post("/api/grading/submissions", json={
            "student_id": "STU001",
            "graded_by": "prof@example.com"
        })
        assert response.status_code == 400
        assert "scheme_id" in response.get_json()["error"]

        # Missing student_id
        response = client.post("/api/grading/submissions", json={
            "scheme_id": sample_scheme.id,
            "graded_by": "prof@example.com"
        })
        assert response.status_code == 400
        assert "student_id" in response.get_json()["error"]

        # Missing graded_by
        response = client.post("/api/grading/submissions", json={
            "scheme_id": sample_scheme.id,
            "student_id": "STU001"
        })
        assert response.status_code == 400
        assert "graded_by" in response.get_json()["error"]

    def test_create_submission_invalid_scheme(self, client):
        """Verify error handling for non-existent scheme."""
        response = client.post("/api/grading/submissions", json={
            "scheme_id": "invalid-uuid",
            "student_id": "STU001",
            "graded_by": "prof@example.com"
        })
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"].lower()

    def test_create_submission_deleted_scheme(self, client, sample_scheme):
        """Verify error handling for deleted schemes."""
        sample_scheme.is_deleted = True
        db.session.commit()

        response = client.post("/api/grading/submissions", json={
            "scheme_id": sample_scheme.id,
            "student_id": "STU001",
            "graded_by": "prof@example.com"
        })
        assert response.status_code == 404


class TestGetSubmission:
    """Test submission retrieval endpoint."""

    def test_get_submission_success(self, client, sample_scheme):
        """Verify successful submission retrieval."""
        # Create submission first
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU002",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()

        response = client.get(f"/api/grading/submissions/{submission.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == submission.id
        assert data["student_id"] == "STU002"

    def test_get_submission_not_found(self, client):
        """Verify error handling for non-existent submission."""
        response = client.get("/api/grading/submissions/invalid-uuid")
        assert response.status_code == 404


class TestCreateEvaluation:
    """Test criterion evaluation creation endpoint (T069)."""

    def test_create_evaluation_success(self, client, sample_scheme):
        """[T069] Verify evaluation creation with valid data."""
        # Create submission
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU003",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()

        # Get first criterion
        criterion = SchemeCriterion.query.first()

        # Create evaluation
        response = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 8.5,
            "feedback": "Good arguments but needs more support"
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data["submission_id"] == submission.id
        assert data["criterion_id"] == criterion.id
        assert float(data["points_awarded"]) == 8.5
        assert data["feedback"] == "Good arguments but needs more support"

    def test_create_evaluation_missing_fields(self, client, sample_scheme):
        """Verify error handling for missing required fields."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU004",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()
        criterion = SchemeCriterion.query.first()

        # Missing criterion_id
        response = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "points_awarded": 8.5
        })
        assert response.status_code == 400

        # Missing points_awarded
        response = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id
        })
        assert response.status_code == 400

    def test_create_evaluation_invalid_points_range(self, client, sample_scheme):
        """Verify validation of points range."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU005",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()
        criterion = SchemeCriterion.query.first()  # max_points = 10.00

        # Points too high
        response = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 15.0  # Exceeds max of 10
        })
        assert response.status_code == 400
        assert "must be between" in response.get_json()["error"]

        # Negative points
        response = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": -1.0
        })
        assert response.status_code == 400

    def test_create_evaluation_duplicate_criterion(self, client, sample_scheme):
        """Verify unique constraint on (submission_id, criterion_id)."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU006",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()
        criterion = SchemeCriterion.query.first()

        # Create first evaluation
        response1 = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 8.0
        })
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 9.0
        })
        assert response2.status_code == 409
        assert "already exists" in response2.get_json()["error"].lower()

    def test_create_evaluation_auto_calculates_total(self, client, sample_scheme):
        """Verify submission total is auto-calculated after evaluation creation."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU007",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()

        criteria = SchemeCriterion.query.order_by(
            SchemeCriterion.display_order
        ).all()

        # Create multiple evaluations
        client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criteria[0].id,
            "points_awarded": 8.0
        })
        client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criteria[1].id,
            "points_awarded": 9.0
        })
        client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criteria[2].id,
            "points_awarded": 4.0
        })

        # Verify submission total was auto-calculated
        submission_check = GradedSubmission.query.filter_by(
            id=submission.id
        ).first()
        assert float(submission_check.total_points_earned) == 21.0


class TestUpdateEvaluation:
    """Test criterion evaluation update endpoint (T070)."""

    def test_update_evaluation_success(self, client, sample_scheme):
        """[T070] Verify evaluation update with valid data."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU008",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()
        criterion = SchemeCriterion.query.first()

        # Create evaluation
        eval_resp = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 7.0,
            "feedback": "Needs improvement"
        })
        eval_id = eval_resp.get_json()["id"]

        # Update evaluation
        response = client.put(f"/api/grading/evaluations/{eval_id}", json={
            "points_awarded": 8.5,
            "feedback": "Better work this time"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert float(data["points_awarded"]) == 8.5
        assert data["feedback"] == "Better work this time"

    def test_update_evaluation_invalid_points(self, client, sample_scheme):
        """Verify point validation in update."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU009",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()
        criterion = SchemeCriterion.query.first()

        eval_resp = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 5.0
        })
        eval_id = eval_resp.get_json()["id"]

        # Try to update with invalid points
        response = client.put(f"/api/grading/evaluations/{eval_id}", json={
            "points_awarded": 20.0  # Exceeds max of 10
        })
        assert response.status_code == 400

    def test_update_evaluation_not_found(self, client):
        """Verify error handling for non-existent evaluation."""
        response = client.put("/api/grading/evaluations/invalid-uuid", json={
            "points_awarded": 8.0
        })
        assert response.status_code == 404


class TestCompleteSubmission:
    """Test submission completion endpoint (T071)."""

    def test_complete_submission_success(self, client, sample_scheme):
        """[T071] Verify marking submission as complete."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU010",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()

        # Add evaluations
        criteria = SchemeCriterion.query.order_by(
            SchemeCriterion.display_order
        ).all()
        for i, criterion in enumerate(criteria):
            evaluation = CriterionEvaluation(
                submission_id=submission.id,
                criterion_id=criterion.id,
                points_awarded=Decimal(str(float(criterion.max_points) * 0.8)),
                max_points=criterion.max_points,
                criterion_name=criterion.name,
                question_title="Question 1"
            )
            db.session.add(evaluation)
        db.session.commit()

        # Auto-calculate total
        from models import recalculate_submission_total
        recalculate_submission_total(submission.id)
        db.session.commit()

        # Complete submission
        response = client.patch(f"/api/grading/submissions/{submission.id}", json={
            "is_complete": True,
            "evaluation_version": 1
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_complete"] is True
        assert data["graded_at"] is not None
        assert data["percentage_score"] is not None
        assert float(data["percentage_score"]) == 80.0

    def test_complete_submission_calculates_percentage(self, client, sample_scheme):
        """Verify percentage calculation on completion."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU011",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()

        # Add evaluation for 50% score
        criterion = SchemeCriterion.query.first()
        evaluation = CriterionEvaluation(
            submission_id=submission.id,
            criterion_id=criterion.id,
            points_awarded=Decimal("5.00"),  # 5 out of 10
            max_points=criterion.max_points,
            criterion_name=criterion.name,
            question_title="Question 1"
        )
        db.session.add(evaluation)
        db.session.commit()

        from models import recalculate_submission_total
        recalculate_submission_total(submission.id)
        db.session.commit()

        response = client.patch(f"/api/grading/submissions/{submission.id}", json={
            "is_complete": True,
            "evaluation_version": 1
        })

        data = response.get_json()
        # 5 points earned out of 25 possible = 20%
        assert float(data["percentage_score"]) == 20.0

    def test_reopen_submission(self, client, sample_scheme):
        """Verify reopening a completed submission."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU012",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00"),
            is_complete=True,
            graded_at=datetime.now(timezone.utc),
            percentage_score=Decimal("75.00")
        )
        db.session.add(submission)
        db.session.commit()

        response = client.patch(f"/api/grading/submissions/{submission.id}", json={
            "is_complete": False,
            "evaluation_version": 1
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_complete"] is False
        assert data["graded_at"] is None
        assert data["percentage_score"] is None


class TestPartialGrading:
    """Test partial grading and resume workflow (T072)."""

    def test_save_partial_and_resume(self, client, sample_scheme):
        """[T072] Verify saving incomplete submission and resuming later."""
        # Create submission
        submit_resp = client.post("/api/grading/submissions", json={
            "scheme_id": sample_scheme.id,
            "student_id": "STU013",
            "graded_by": "prof@example.com"
        })
        submission_id = submit_resp.get_json()["id"]

        # Grade first criterion
        criteria = SchemeCriterion.query.order_by(
            SchemeCriterion.display_order
        ).all()
        client.post("/api/grading/evaluations", json={
            "submission_id": submission_id,
            "criterion_id": criteria[0].id,
            "points_awarded": 8.0
        })

        # Check submission is still incomplete
        get_resp = client.get(f"/api/grading/submissions/{submission_id}")
        assert get_resp.get_json()["is_complete"] is False

        # Later, grade remaining criteria
        client.post("/api/grading/evaluations", json={
            "submission_id": submission_id,
            "criterion_id": criteria[1].id,
            "points_awarded": 9.0
        })
        client.post("/api/grading/evaluations", json={
            "submission_id": submission_id,
            "criterion_id": criteria[2].id,
            "points_awarded": 4.5
        })

        # Now complete submission
        complete_resp = client.patch(f"/api/grading/submissions/{submission_id}", json={
            "is_complete": True,
            "evaluation_version": 1
        })
        assert complete_resp.status_code == 200
        assert complete_resp.get_json()["is_complete"] is True


class TestConcurrentEvaluation:
    """Test concurrent evaluation handling (T073)."""

    def test_concurrent_evaluation_conflict(self, client, sample_scheme):
        """[T073] Verify optimistic locking detection for concurrent edits."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU014",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00"),
            evaluation_version=1
        )
        db.session.add(submission)
        db.session.commit()

        # Simulate version mismatch (user B has newer version)
        response = client.patch(f"/api/grading/submissions/{submission.id}", json={
            "is_complete": True,
            "evaluation_version": 2  # Version mismatch
        })

        assert response.status_code == 409
        assert "modified by another user" in response.get_json()["error"].lower()

    def test_allow_duplicate_feedback_updates(self, client, sample_scheme):
        """Verify multiple feedback updates to same evaluation are allowed."""
        submission = GradedSubmission(
            scheme_id=sample_scheme.id,
            scheme_version=1,
            student_id="STU015",
            graded_by="prof@example.com",
            total_points_possible=Decimal("25.00")
        )
        db.session.add(submission)
        db.session.commit()
        criterion = SchemeCriterion.query.first()

        # Create evaluation
        eval_resp = client.post("/api/grading/evaluations", json={
            "submission_id": submission.id,
            "criterion_id": criterion.id,
            "points_awarded": 8.0,
            "feedback": "Initial feedback"
        })
        eval_id = eval_resp.get_json()["id"]

        # Update feedback multiple times
        response1 = client.put(f"/api/grading/evaluations/{eval_id}", json={
            "feedback": "Updated feedback v1"
        })
        assert response1.status_code == 200

        response2 = client.put(f"/api/grading/evaluations/{eval_id}", json={
            "feedback": "Updated feedback v2"
        })
        assert response2.status_code == 200
        assert response2.get_json()["feedback"] == "Updated feedback v2"
