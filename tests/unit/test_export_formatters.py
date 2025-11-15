"""Unit tests for export formatters (CSV and JSON).

Tests for formatting grading data into standardized export formats.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from utils.export_formatters import format_csv, format_json


class TestFormatCSV:
    """Test CSV export formatting."""

    def test_format_csv_empty_submissions(self):
        """Verify CSV formatter handles empty submission list."""
        result = format_csv([])

        # Should have only headers
        lines = result.strip().split("\n")
        assert len(lines) >= 1
        assert "Student ID" in lines[0] or "student_id" in lines[0].lower()

    def test_format_csv_single_submission(self):
        """Verify CSV output for single submission with multiple evaluations."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "John Doe",
                "scheme_id": "scheme_001",
                "scheme_name": "Essay Rubric",
                "is_complete": True,
                "percentage_score": Decimal("85.00"),
                "total_points_earned": Decimal("85.00"),
                "total_points_possible": Decimal("100.00"),
                "graded_by": "prof@example.com",
                "graded_at": datetime(2025, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
                "evaluations": [
                    {
                        "criterion_name": "Clarity",
                        "question_title": "Question 1",
                        "points_awarded": Decimal("8.5"),
                        "max_points": Decimal("10.00"),
                        "feedback": "Well written",
                    },
                    {
                        "criterion_name": "Argument",
                        "question_title": "Question 1",
                        "points_awarded": Decimal("9.0"),
                        "max_points": Decimal("10.00"),
                        "feedback": "Strong arguments",
                    },
                ],
            }
        ]

        result = format_csv(submissions)
        lines = result.strip().split("\n")

        # Should have headers + 2 evaluation rows
        assert len(lines) >= 3
        assert "STU001" in result
        assert "John Doe" in result
        assert "Clarity" in result
        assert "Argument" in result

    def test_format_csv_column_structure(self):
        """Verify CSV has correct columns in expected order."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "Jane Doe",
                "scheme_name": "Test Scheme",
                "is_complete": True,
                "total_points_earned": Decimal("50.00"),
                "total_points_possible": Decimal("100.00"),
                "percentage_score": Decimal("50.00"),
                "graded_by": "instructor@example.com",
                "graded_at": datetime(2025, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
                "evaluations": [
                    {
                        "criterion_name": "Test Criterion",
                        "question_title": "Q1",
                        "points_awarded": Decimal("5.0"),
                        "max_points": Decimal("10.0"),
                        "feedback": "Good",
                    }
                ],
            }
        ]

        result = format_csv(submissions)
        lines = result.strip().split("\n")
        headers = lines[0]

        # Verify key columns exist
        assert "Student ID" in headers or "student_id" in headers.lower()
        assert "Student Name" in headers or "student_name" in headers.lower()
        assert "Question" in headers or "question" in headers.lower()
        assert "Criterion" in headers or "criterion" in headers.lower()
        assert "Points Earned" in headers or "points_earned" in headers.lower()
        assert "Max Points" in headers or "max_points" in headers.lower()

    def test_format_csv_with_partial_feedback(self):
        """Verify CSV handles missing feedback gracefully."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "Test",
                "scheme_name": "Scheme",
                "is_complete": True,
                "total_points_earned": Decimal("10.00"),
                "total_points_possible": Decimal("20.00"),
                "percentage_score": Decimal("50.00"),
                "graded_by": "prof",
                "graded_at": datetime.now(timezone.utc),
                "evaluations": [
                    {
                        "criterion_name": "Criterion 1",
                        "question_title": "Q1",
                        "points_awarded": Decimal("10.0"),
                        "max_points": Decimal("20.0"),
                        "feedback": None,  # Missing feedback
                    }
                ],
            }
        ]

        result = format_csv(submissions)
        # Should not raise error and should handle None gracefully
        assert result is not None
        assert len(result) > 0


class TestFormatJSON:
    """Test JSON export formatting."""

    def test_format_json_empty_submissions(self):
        """Verify JSON formatter handles empty submission list."""
        result = format_json([])
        data = json.loads(result)

        assert "submissions" in data
        assert "metadata" in data
        assert data["submissions"] == []

    def test_format_json_hierarchical_structure(self):
        """Verify JSON preserves hierarchical structure."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "John Doe",
                "scheme_name": "Essay Rubric",
                "is_complete": True,
                "percentage_score": Decimal("85.00"),
                "total_points_earned": Decimal("85.00"),
                "total_points_possible": Decimal("100.00"),
                "graded_by": "prof@example.com",
                "graded_at": datetime(2025, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
                "evaluations": [
                    {
                        "criterion_name": "Clarity",
                        "question_title": "Question 1",
                        "points_awarded": Decimal("8.5"),
                        "max_points": Decimal("10.00"),
                        "feedback": "Well written",
                    }
                ],
            }
        ]

        result = format_json(submissions)
        data = json.loads(result)

        assert "submissions" in data
        assert len(data["submissions"]) == 1
        submission = data["submissions"][0]
        assert submission["student_id"] == "STU001"
        assert "evaluations" in submission
        assert len(submission["evaluations"]) == 1

    def test_format_json_includes_metadata(self):
        """Verify JSON export includes required metadata."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "Test",
                "scheme_name": "Scheme",
                "is_complete": True,
                "total_points_earned": Decimal("50.00"),
                "total_points_possible": Decimal("100.00"),
                "percentage_score": Decimal("50.00"),
                "graded_by": "prof@example.com",
                "graded_at": datetime.now(timezone.utc),
                "evaluations": [],
            }
        ]

        result = format_json(submissions)
        data = json.loads(result)

        assert "metadata" in data
        metadata = data["metadata"]
        assert "export_date" in metadata
        assert "total_submissions" in metadata
        assert metadata["total_submissions"] == 1

    def test_format_json_decimal_serialization(self):
        """Verify JSON properly serializes Decimal values."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "Test",
                "scheme_name": "Scheme",
                "is_complete": True,
                "total_points_earned": Decimal("87.50"),
                "total_points_possible": Decimal("100.00"),
                "percentage_score": Decimal("87.50"),
                "graded_by": "prof",
                "graded_at": datetime.now(timezone.utc),
                "evaluations": [
                    {
                        "criterion_name": "Test",
                        "question_title": "Q1",
                        "points_awarded": Decimal("8.75"),
                        "max_points": Decimal("10.00"),
                        "feedback": "Good",
                    }
                ],
            }
        ]

        result = format_json(submissions)
        # Should be valid JSON without Decimal serialization errors
        data = json.loads(result)
        assert data["submissions"][0]["total_points_earned"] == 87.5
        assert data["submissions"][0]["evaluations"][0]["points_awarded"] == 8.75

    def test_format_json_datetime_serialization(self):
        """Verify JSON properly serializes datetime values."""
        submissions = [
            {
                "id": "sub_001",
                "student_id": "STU001",
                "student_name": "Test",
                "scheme_name": "Scheme",
                "is_complete": True,
                "total_points_earned": Decimal("50.00"),
                "total_points_possible": Decimal("100.00"),
                "percentage_score": Decimal("50.00"),
                "graded_by": "prof",
                "graded_at": datetime(2025, 11, 15, 12, 30, 45, tzinfo=timezone.utc),
                "evaluations": [],
            }
        ]

        result = format_json(submissions)
        data = json.loads(result)
        # Should be ISO format string
        assert isinstance(data["submissions"][0]["graded_at"], str)
        assert "2025-11-15" in data["submissions"][0]["graded_at"]
