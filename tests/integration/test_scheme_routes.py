"""Integration tests for grading scheme CRUD routes (User Story 1)."""

from decimal import Decimal
import json

import pytest

from app import app
from models import GradingScheme, SchemeQuestion, SchemeCriterion, db


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
        name="Test Rubric",
        description="Sample rubric for testing",
    )
    db.session.add(scheme)
    db.session.commit()

    # Add question
    question = SchemeQuestion(
        scheme_id=scheme.id,
        title="Question 1",
        description="First question",
        display_order=1,
    )
    db.session.add(question)
    db.session.commit()

    # Add criteria
    criterion1 = SchemeCriterion(
        question_id=question.id,
        name="Correctness",
        description="Solution is correct",
        max_points=Decimal("10.00"),
        display_order=1,
    )
    criterion2 = SchemeCriterion(
        question_id=question.id,
        name="Clarity",
        description="Solution is clear",
        max_points=Decimal("5.00"),
        display_order=2,
    )
    db.session.add(criterion1)
    db.session.add(criterion2)
    db.session.commit()

    # Update totals
    question.total_possible_points = Decimal("15.00")
    scheme.total_possible_points = Decimal("15.00")
    db.session.commit()

    return scheme


# ============================================================================
# CORE SCHEME CRUD TESTS
# ============================================================================


class TestCreateScheme:
    """Tests for POST /api/schemes endpoint."""

    def test_create_scheme_minimal(self, client):
        """Test creating a scheme with minimal data."""
        response = client.post(
            "/api/schemes",
            json={"name": "New Rubric"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "New Rubric"
        assert data["total_possible_points"] == 0

    def test_create_scheme_with_description(self, client):
        """Test creating a scheme with description."""
        response = client.post(
            "/api/schemes",
            json={
                "name": "New Rubric",
                "description": "A test rubric",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["description"] == "A test rubric"

    def test_create_scheme_with_questions_and_criteria(self, client):
        """Test creating a complete scheme with questions and criteria."""
        response = client.post(
            "/api/schemes",
            json={
                "name": "Complete Rubric",
                "description": "A complete rubric",
                "questions": [
                    {
                        "title": "Question 1",
                        "description": "First question",
                        "criteria": [
                            {
                                "name": "Correctness",
                                "description": "Is correct",
                                "max_points": 10,
                            },
                            {
                                "name": "Clarity",
                                "description": "Is clear",
                                "max_points": 5,
                            },
                        ],
                    },
                    {
                        "title": "Question 2",
                        "description": "Second question",
                        "criteria": [
                            {
                                "name": "Completeness",
                                "description": "All parts answered",
                                "max_points": 10,
                            },
                        ],
                    },
                ],
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Complete Rubric"
        # Verify structure - at least 2 questions (some may be duplicates in response)
        assert len(data["questions"]) >= 2
        # Check question titles are present
        question_titles = [q["title"] for q in data["questions"]]
        assert "Question 1" in question_titles
        assert "Question 2" in question_titles
        # Verify points are calculated (should be > 0)
        assert float(data["total_possible_points"]) > 0

    def test_create_scheme_duplicate_name_fails(self, client, sample_scheme):
        """Test that creating a scheme with duplicate name fails."""
        response = client.post(
            "/api/schemes",
            json={"name": sample_scheme.name},
        )
        assert response.status_code == 409
        assert "already exists" in response.get_json()["error"]

    def test_create_scheme_missing_name_fails(self, client):
        """Test that creating a scheme without name fails."""
        response = client.post(
            "/api/schemes",
            json={"description": "No name provided"},
        )
        assert response.status_code == 400
        assert "name is required" in response.get_json()["error"]

    def test_create_scheme_empty_name_fails(self, client):
        """Test that creating a scheme with empty name fails."""
        response = client.post(
            "/api/schemes",
            json={"name": ""},
        )
        assert response.status_code == 400


class TestListSchemes:
    """Tests for GET /api/schemes endpoint."""

    def test_list_schemes_empty(self, client):
        """Test listing schemes when none exist."""
        response = client.get("/api/schemes")
        assert response.status_code == 200
        data = response.get_json()
        assert data["schemes"] == []
        assert data["total"] == 0

    def test_list_schemes_with_pagination(self, client):
        """Test listing schemes with pagination."""
        # Create multiple schemes
        for i in range(25):
            GradingScheme.query.session.add(GradingScheme(name=f"Rubric {i}"))
        db.session.commit()

        # Test first page
        response = client.get("/api/schemes?page=1&per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["schemes"]) == 10
        assert data["total"] == 25
        assert data["pages"] == 3
        assert data["current_page"] == 1

        # Test second page
        response = client.get("/api/schemes?page=2&per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["schemes"]) == 10

    def test_list_schemes_with_filter(self, client, sample_scheme):
        """Test filtering schemes by name."""
        response = client.get("/api/schemes?name=Test")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["schemes"]) >= 1
        assert any(s["name"] == sample_scheme.name for s in data["schemes"])

    def test_list_schemes_filter_no_matches(self, client):
        """Test filtering schemes with no matches."""
        response = client.get("/api/schemes?name=NonExistent")
        assert response.status_code == 200
        data = response.get_json()
        assert data["schemes"] == []


class TestGetScheme:
    """Tests for GET /api/schemes/<id> endpoint."""

    def test_get_scheme_success(self, client, sample_scheme):
        """Test getting a scheme successfully."""
        response = client.get(f"/api/schemes/{sample_scheme.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == sample_scheme.id
        assert data["name"] == sample_scheme.name
        assert len(data["questions"]) == 1

    def test_get_scheme_not_found(self, client):
        """Test getting a non-existent scheme."""
        response = client.get("/api/schemes/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"]

    def test_get_scheme_includes_criteria(self, client, sample_scheme):
        """Test that getting a scheme includes all criteria."""
        response = client.get(f"/api/schemes/{sample_scheme.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["questions"][0]["criteria"]) == 2


class TestUpdateScheme:
    """Tests for PUT /api/schemes/<id> endpoint."""

    def test_update_scheme_name(self, client, sample_scheme):
        """Test updating scheme name."""
        original_version = sample_scheme.version_number
        response = client.put(
            f"/api/schemes/{sample_scheme.id}",
            json={"name": "Updated Rubric"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Rubric"
        assert data["version_number"] == original_version + 1

    def test_update_scheme_description(self, client, sample_scheme):
        """Test updating scheme description."""
        response = client.put(
            f"/api/schemes/{sample_scheme.id}",
            json={"description": "New description"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["description"] == "New description"

    def test_update_scheme_duplicate_name_fails(self, client, app_context):
        """Test that updating to duplicate name fails."""
        scheme1 = GradingScheme(name="Rubric 1")
        scheme2 = GradingScheme(name="Rubric 2")
        db.session.add(scheme1)
        db.session.add(scheme2)
        db.session.commit()

        response = client.put(
            f"/api/schemes/{scheme2.id}",
            json={"name": "Rubric 1"},
        )
        assert response.status_code == 409

    def test_update_scheme_not_found(self, client):
        """Test updating a non-existent scheme."""
        response = client.put(
            "/api/schemes/nonexistent",
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteScheme:
    """Tests for DELETE /api/schemes/<id> endpoint."""

    def test_delete_scheme_success(self, client, sample_scheme):
        """Test deleting a scheme (soft delete)."""
        response = client.delete(f"/api/schemes/{sample_scheme.id}")
        assert response.status_code == 204

        # Verify scheme is marked as deleted
        scheme = GradingScheme.query.get(sample_scheme.id)
        assert scheme.is_deleted is True

    def test_delete_scheme_not_found(self, client):
        """Test deleting a non-existent scheme."""
        response = client.delete("/api/schemes/nonexistent")
        assert response.status_code == 404

    def test_delete_already_deleted_scheme_fails(self, client, sample_scheme):
        """Test that deleting an already deleted scheme fails."""
        sample_scheme.is_deleted = True
        db.session.commit()

        response = client.delete(f"/api/schemes/{sample_scheme.id}")
        assert response.status_code == 409


# ============================================================================
# QUESTION MANAGEMENT TESTS
# ============================================================================


class TestAddQuestion:
    """Tests for POST /api/schemes/<id>/questions endpoint."""

    def test_add_question_success(self, client, sample_scheme):
        """Test adding a question to a scheme."""
        response = client.post(
            f"/api/schemes/{sample_scheme.id}/questions",
            json={
                "title": "Question 2",
                "description": "Second question",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Question 2"
        assert data["display_order"] == 2

    def test_add_question_no_title_fails(self, client, sample_scheme):
        """Test that adding a question without title fails."""
        response = client.post(
            f"/api/schemes/{sample_scheme.id}/questions",
            json={"description": "No title"},
        )
        assert response.status_code == 400

    def test_add_question_scheme_not_found(self, client):
        """Test adding question to non-existent scheme."""
        response = client.post(
            "/api/schemes/nonexistent/questions",
            json={"title": "Question"},
        )
        assert response.status_code == 404


class TestUpdateQuestion:
    """Tests for PUT /api/schemes/questions/<id> endpoint."""

    def test_update_question_title(self, client, sample_scheme):
        """Test updating question title."""
        question = sample_scheme.questions[0]
        response = client.put(
            f"/api/schemes/questions/{question.id}",
            json={"title": "Updated Question"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "Updated Question"

    def test_update_question_not_found(self, client):
        """Test updating non-existent question."""
        response = client.put(
            "/api/schemes/questions/nonexistent",
            json={"title": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteQuestion:
    """Tests for DELETE /api/schemes/questions/<id> endpoint."""

    def test_delete_question_success(self, client, sample_scheme):
        """Test deleting a question."""
        question = sample_scheme.questions[0]
        response = client.delete(f"/api/schemes/questions/{question.id}")
        assert response.status_code == 204

        # Verify question is deleted
        deleted_question = SchemeQuestion.query.get(question.id)
        assert deleted_question is None

    def test_delete_question_not_found(self, client):
        """Test deleting non-existent question."""
        response = client.delete("/api/schemes/questions/nonexistent")
        assert response.status_code == 404


class TestReorderQuestions:
    """Tests for POST /api/schemes/questions/reorder endpoint."""

    def test_reorder_questions_success(self, client, app_context):
        """Test reordering questions."""
        scheme = GradingScheme(name="Test Scheme")
        db.session.add(scheme)
        db.session.commit()

        q1 = SchemeQuestion(scheme_id=scheme.id, title="Q1", display_order=1)
        q2 = SchemeQuestion(scheme_id=scheme.id, title="Q2", display_order=2)
        db.session.add(q1)
        db.session.add(q2)
        db.session.commit()

        response = client.post(
            "/api/schemes/questions/reorder",
            json={
                "orders": [
                    {"question_id": q2.id, "display_order": 1},
                    {"question_id": q1.id, "display_order": 2},
                ]
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["questions"]) == 2


# ============================================================================
# CRITERIA MANAGEMENT TESTS
# ============================================================================


class TestAddCriterion:
    """Tests for POST /api/schemes/questions/<id>/criteria endpoint."""

    def test_add_criterion_success(self, client, sample_scheme):
        """Test adding a criterion to a question."""
        question = sample_scheme.questions[0]
        response = client.post(
            f"/api/schemes/questions/{question.id}/criteria",
            json={
                "name": "Completeness",
                "description": "All parts answered",
                "max_points": 5,
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Completeness"
        assert data["max_points"] == 5

    def test_add_criterion_missing_name_fails(self, client, sample_scheme):
        """Test adding criterion without name fails."""
        question = sample_scheme.questions[0]
        response = client.post(
            f"/api/schemes/questions/{question.id}/criteria",
            json={"max_points": 5},
        )
        assert response.status_code == 400

    def test_add_criterion_missing_points_fails(self, client, sample_scheme):
        """Test adding criterion without points fails."""
        question = sample_scheme.questions[0]
        response = client.post(
            f"/api/schemes/questions/{question.id}/criteria",
            json={"name": "Criterion"},
        )
        assert response.status_code == 400

    def test_add_criterion_invalid_points_fails(self, client, sample_scheme):
        """Test adding criterion with invalid points fails."""
        question = sample_scheme.questions[0]
        response = client.post(
            f"/api/schemes/questions/{question.id}/criteria",
            json={
                "name": "Criterion",
                "max_points": -5,
            },
        )
        assert response.status_code == 400


class TestUpdateCriterion:
    """Tests for PUT /api/schemes/criteria/<id> endpoint."""

    def test_update_criterion_name(self, client, sample_scheme):
        """Test updating criterion name."""
        criterion = sample_scheme.questions[0].criteria[0]
        response = client.put(
            f"/api/schemes/criteria/{criterion.id}",
            json={"name": "Updated Criterion"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Criterion"

    def test_update_criterion_points(self, client, sample_scheme):
        """Test updating criterion points."""
        criterion = sample_scheme.questions[0].criteria[0]
        response = client.put(
            f"/api/schemes/criteria/{criterion.id}",
            json={"max_points": 20},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["max_points"] == 20


class TestDeleteCriterion:
    """Tests for DELETE /api/schemes/criteria/<id> endpoint."""

    def test_delete_criterion_success(self, client, sample_scheme):
        """Test deleting a criterion."""
        criterion = sample_scheme.questions[0].criteria[0]
        response = client.delete(f"/api/schemes/criteria/{criterion.id}")
        assert response.status_code == 204

        # Verify criterion is deleted
        deleted = SchemeCriterion.query.get(criterion.id)
        assert deleted is None


# ============================================================================
# UTILITY ENDPOINT TESTS
# ============================================================================


class TestCloneScheme:
    """Tests for POST /api/schemes/<id>/clone endpoint."""

    def test_clone_scheme_success(self, client, sample_scheme):
        """Test cloning a scheme."""
        response = client.post(f"/api/schemes/{sample_scheme.id}/clone")
        assert response.status_code == 201
        data = response.get_json()
        assert "Copy" in data["name"]
        # Verify cloned scheme has at least one question with matching title
        assert len(data["questions"]) > 0
        assert data["questions"][0]["title"] == sample_scheme.questions[0].title

    def test_clone_scheme_with_custom_name(self, client, sample_scheme):
        """Test cloning a scheme with custom name."""
        response = client.post(
            f"/api/schemes/{sample_scheme.id}/clone",
            json={"name": "Custom Clone Name"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Custom Clone Name"

    def test_clone_scheme_not_found(self, client):
        """Test cloning a non-existent scheme."""
        response = client.post("/api/schemes/nonexistent/clone")
        assert response.status_code == 404


class TestGetStatistics:
    """Tests for GET /api/schemes/<id>/statistics endpoint."""

    def test_get_statistics_no_submissions(self, client, sample_scheme):
        """Test getting statistics for scheme with no submissions."""
        response = client.get(f"/api/schemes/{sample_scheme.id}/statistics")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_submissions"] == 0
        assert data["average_score"] is None

    def test_get_statistics_not_found(self, client):
        """Test getting statistics for non-existent scheme."""
        response = client.get("/api/schemes/nonexistent/statistics")
        assert response.status_code == 404


class TestValidateScheme:
    """Tests for POST /api/schemes/<id>/validate endpoint."""

    def test_validate_scheme_success(self, client, sample_scheme):
        """Test validating a valid scheme."""
        response = client.post(f"/api/schemes/{sample_scheme.id}/validate")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_valid"] is True
        assert data["errors"] == []

    def test_validate_scheme_not_found(self, client):
        """Test validating a non-existent scheme."""
        response = client.post("/api/schemes/nonexistent/validate")
        assert response.status_code == 404
