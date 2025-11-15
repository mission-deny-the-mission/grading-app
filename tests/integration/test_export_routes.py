"""Integration tests for export API endpoints.

Tests for exporting grading data in CSV and JSON formats.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from models import (
    CriterionEvaluation,
    GradedSubmission,
    GradingScheme,
    SchemeCriterion,
    SchemeQuestion,
    db,
)


@pytest.fixture
def app_with_grading_data(app):
    """Create app with complete grading scheme and submissions."""
    with app.app_context():
        db.create_all()

        # Create scheme
        scheme = GradingScheme(
            name="Export Test Scheme",
            category="essay",
            total_possible_points=Decimal("100.00"),
        )
        db.session.add(scheme)
        db.session.commit()

        # Create questions
        q1 = SchemeQuestion(scheme_id=scheme.id, title="Question 1", display_order=1)
        q2 = SchemeQuestion(scheme_id=scheme.id, title="Question 2", display_order=2)
        db.session.add_all([q1, q2])
        db.session.commit()

        # Create criteria
        criteria = []
        for q_idx, q in enumerate([q1, q2]):
            for c_idx in range(2):
                criterion = SchemeCriterion(
                    question_id=q.id,
                    name=f"Question {q_idx + 1} Criterion {c_idx + 1}",
                    max_points=Decimal("25.00"),
                    display_order=c_idx + 1,
                )
                criteria.append(criterion)
                db.session.add(criterion)
        db.session.commit()

        # Create submissions with evaluations
        for s_idx in range(2):
            submission = GradedSubmission(
                scheme_id=scheme.id,
                scheme_version=1,
                student_id=f"STU{1000 + s_idx}",
                student_name=f"Student {s_idx + 1}",
                submission_reference=f"file_{s_idx}",
                graded_by="prof@example.com",
                total_points_possible=Decimal("100.00"),
                is_complete=True,
                graded_at=datetime.now(timezone.utc),
            )
            db.session.add(submission)
            db.session.commit()

            # Create evaluations for all criteria
            total_earned = Decimal("0.00")
            for c_idx, criterion in enumerate(criteria):
                points = Decimal(str(20 + s_idx * 2))  # Vary points by submission
                evaluation = CriterionEvaluation(
                    submission_id=submission.id,
                    criterion_id=criterion.id,
                    points_awarded=points,
                    max_points=Decimal("25.00"),
                    criterion_name=criterion.name,
                    question_title=criterion.question.title,
                    feedback=f"Feedback for {criterion.name}",
                )
                db.session.add(evaluation)
                total_earned += points
            db.session.commit()

            # Update submission totals
            submission.total_points_earned = total_earned
            submission.percentage_score = ((total_earned / submission.total_points_possible) * 100).quantize(
                Decimal("0.01")
            )
            db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


class TestExportCSV:
    """Test CSV export endpoint."""

    def test_export_csv_success(self, client, app_with_grading_data):
        """Verify CSV export returns valid CSV data."""
        # Get scheme ID first
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(
            f"/api/export/schemes/{scheme_id}?format=csv",
            headers={"Accept": "text/csv"},
        )

        assert response.status_code == 200
        assert response.content_type == "text/csv"
        assert "Student ID" in response.data.decode()
        assert "STU1000" in response.data.decode()
        assert "STU1001" in response.data.decode()

    def test_export_csv_invalid_scheme(self, client, app_with_grading_data):
        """Verify CSV export returns 404 for invalid scheme."""
        response = client.get(
            "/api/export/schemes/nonexistent?format=csv",
            headers={"Accept": "text/csv"},
        )

        assert response.status_code == 404

    def test_export_csv_column_headers(self, client, app_with_grading_data):
        """Verify CSV contains expected column headers."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(f"/api/export/schemes/{scheme_id}?format=csv")

        csv_content = response.data.decode()
        lines = csv_content.strip().split("\n")
        header = lines[0]

        # Verify key columns
        assert "Student ID" in header
        assert "Student Name" in header
        assert "Question" in header or "question" in header.lower()
        assert "Criterion" in header or "criterion" in header.lower()

    def test_export_csv_data_rows(self, client, app_with_grading_data):
        """Verify CSV contains data rows for all evaluations."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(f"/api/export/schemes/{scheme_id}?format=csv")

        csv_content = response.data.decode()
        lines = csv_content.strip().split("\n")

        # Should have header + at least 8 data rows (2 submissions * 4 criteria)
        assert len(lines) >= 9


class TestExportJSON:
    """Test JSON export endpoint."""

    def test_export_json_success(self, client, app_with_grading_data):
        """Verify JSON export returns valid JSON data."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(
            f"/api/export/schemes/{scheme_id}?format=json",
            headers={"Accept": "application/json"},
        )

        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert "submissions" in data
        assert "metadata" in data
        assert len(data["submissions"]) == 2

    def test_export_json_invalid_scheme(self, client, app_with_grading_data):
        """Verify JSON export returns 404 for invalid scheme."""
        response = client.get(
            "/api/export/schemes/nonexistent?format=json",
            headers={"Accept": "application/json"},
        )

        assert response.status_code == 404

    def test_export_json_hierarchy_preserved(self, client, app_with_grading_data):
        """Verify JSON preserves hierarchical structure."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(f"/api/export/schemes/{scheme_id}?format=json")

        data = json.loads(response.data)
        submission = data["submissions"][0]

        assert "student_id" in submission
        assert "evaluations" in submission
        assert len(submission["evaluations"]) == 4  # 2 questions * 2 criteria

    def test_export_json_metadata_complete(self, client, app_with_grading_data):
        """Verify JSON includes complete metadata."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(f"/api/export/schemes/{scheme_id}?format=json")

        data = json.loads(response.data)
        metadata = data["metadata"]

        assert "export_date" in metadata
        assert "total_submissions" in metadata
        assert "scheme_name" in metadata
        assert metadata["total_submissions"] == 2


class TestExportWithFilters:
    """Test export endpoint with filtering options."""

    def test_export_filter_incomplete_submissions(self, client, app_with_grading_data):
        """Verify export can filter out incomplete submissions."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

            # Add incomplete submission
            incomplete = GradedSubmission(
                scheme_id=scheme.id,
                scheme_version=1,
                student_id="STU_INCOMPLETE",
                student_name="Incomplete Student",
                graded_by="prof@example.com",
                total_points_possible=Decimal("100.00"),
                is_complete=False,
            )
            db.session.add(incomplete)
            db.session.commit()

        response = client.get(f"/api/export/schemes/{scheme_id}?format=json&include_incomplete=false")

        data = json.loads(response.data)
        # Should exclude incomplete submission
        assert len(data["submissions"]) == 2
        for submission in data["submissions"]:
            assert submission["student_id"] != "STU_INCOMPLETE"

    def test_export_default_include_incomplete(self, client, app_with_grading_data):
        """Verify export includes incomplete submissions by default."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

            # Add incomplete submission
            incomplete = GradedSubmission(
                scheme_id=scheme.id,
                scheme_version=1,
                student_id="STU_INCOMPLETE",
                student_name="Incomplete Student",
                graded_by="prof@example.com",
                total_points_possible=Decimal("100.00"),
                is_complete=False,
            )
            db.session.add(incomplete)
            db.session.commit()

        response = client.get(f"/api/export/schemes/{scheme_id}?format=json")

        data = json.loads(response.data)
        # Should include all submissions (3 total: 2 complete + 1 incomplete)
        assert len(data["submissions"]) == 3

    def test_export_invalid_format(self, client, app_with_grading_data):
        """Verify export rejects invalid format parameter."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(f"/api/export/schemes/{scheme_id}?format=xml")

        assert response.status_code == 400

    def test_export_default_json_format(self, client, app_with_grading_data):
        """Verify export defaults to JSON format."""
        with app_with_grading_data.app_context():
            scheme = GradingScheme.query.first()
            scheme_id = scheme.id

        response = client.get(f"/api/export/schemes/{scheme_id}")

        # Should default to JSON
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "submissions" in data


class TestLargeExportPerformance:
    """Test export performance with large datasets (T252)."""

    def test_export_large_dataset_performance(self, client, app):
        """Test export with 100+ students × 50+ criteria completes within 30 seconds."""
        import time

        with app.app_context():
            db.create_all()

            # Create scheme with 50+ criteria
            scheme = GradingScheme(
                name="Large Export Test Scheme",
                category="comprehensive_exam",
                total_possible_points=Decimal("500.00"),
            )
            db.session.add(scheme)
            db.session.commit()

            # Create 10 questions
            questions = []
            for q_idx in range(10):
                question = SchemeQuestion(
                    scheme_id=scheme.id,
                    title=f"Question {q_idx + 1}",
                    display_order=q_idx + 1,
                )
                db.session.add(question)
                questions.append(question)
            db.session.commit()

            # Create 5 criteria per question (50 total)
            criteria = []
            for question in questions:
                for c_idx in range(5):
                    criterion = SchemeCriterion(
                        question_id=question.id,
                        name=f"Criterion {c_idx + 1}",
                        max_points=Decimal("10.00"),
                        display_order=c_idx + 1,
                    )
                    db.session.add(criterion)
                    criteria.append(criterion)
            db.session.commit()

            # Create 100 graded submissions
            for student_idx in range(100):
                submission = GradedSubmission(
                    scheme_id=scheme.id,
                    scheme_version=1,
                    student_id=f"STU_{student_idx:03d}",
                    student_name=f"Student {student_idx}",
                    graded_by="prof@example.com",
                    total_points_possible=Decimal("500.00"),
                    is_complete=True,
                    graded_at=datetime.now(timezone.utc),
                )
                db.session.add(submission)
            db.session.commit()

            # Create evaluations for each submission (100 students × 50 criteria = 5000 evaluations)
            submissions = GradedSubmission.query.all()
            for submission in submissions:
                total_earned = Decimal("0.00")
                for criterion in criteria:
                    # Award random points between 0 and max_points
                    points = Decimal(str(float(criterion.max_points) * 0.8))  # 80% average
                    eval = CriterionEvaluation(
                        submission_id=submission.id,
                        criterion_id=criterion.id,
                        points_awarded=points,
                        max_points=criterion.max_points,
                        criterion_name=criterion.name,
                        question_title="",  # Will be populated by fixture
                    )
                    db.session.add(eval)
                    total_earned += points

                submission.total_points_earned = total_earned
                submission.percentage_score = (total_earned / submission.total_points_possible) * 100

            db.session.commit()
            scheme_id = scheme.id

        # Measure export time for CSV
        start_time = time.time()
        response_csv = client.get(f"/api/export/schemes/{scheme_id}?format=csv")
        csv_duration = time.time() - start_time

        assert response_csv.status_code == 200
        assert csv_duration < 30, f"CSV export took {csv_duration:.2f}s, expected <30s"

        # Measure export time for JSON
        start_time = time.time()
        response_json = client.get(f"/api/export/schemes/{scheme_id}?format=json")
        json_duration = time.time() - start_time

        assert response_json.status_code == 200
        assert json_duration < 30, f"JSON export took {json_duration:.2f}s, expected <30s"

        # Verify data completeness
        data = json.loads(response_json.data)
        assert data["metadata"]["total_submissions"] == 100
        assert len(data["submissions"]) == 100

        # Print performance metrics
        print(f"\nLarge export performance (100 students × 50 criteria):")
        print(f"  CSV export: {csv_duration:.2f}s")
        print(f"  JSON export: {json_duration:.2f}s")
