"""
Tests for grading_ui routes - covering grade_submission and error handlers.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGradingUIRoutes:
    """Test cases for grading UI routes."""

    def test_grade_submission_success(self, client, app):
        """Test the grade submission page loads successfully."""
        with app.app_context():
            from models import db, GradingScheme, Submission, GradingJob

            # Create a scheme
            scheme = GradingScheme(
                name="Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()

            # Create a job with the scheme
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Grade this submission",
                scheme_id=scheme.id
            )
            db.session.add(job)
            db.session.commit()

            # Create a submission
            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending"
            )
            db.session.add(submission)
            db.session.commit()

            # Test the route
            response = client.get(f"/submissions/{submission.id}/grade")
            assert response.status_code == 200

    def test_grade_submission_with_scheme_id_param(self, client, app):
        """Test the grade submission page with scheme_id query parameter."""
        with app.app_context():
            from models import db, GradingScheme, Submission, GradingJob

            # Create a scheme
            scheme = GradingScheme(
                name="Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()

            # Create a job
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Grade this submission"
            )
            db.session.add(job)
            db.session.commit()

            # Create a submission
            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending"
            )
            db.session.add(submission)
            db.session.commit()

            # Test the route with scheme_id parameter
            response = client.get(f"/submissions/{submission.id}/grade?scheme_id={scheme.id}")
            assert response.status_code == 200

    def test_grade_submission_not_found(self, client, app):
        """Test the grade submission page with non-existent submission."""
        response = client.get("/submissions/nonexistent-id/grade")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_grade_submission_invalid_scheme(self, client, app):
        """Test the grade submission page with invalid scheme_id."""
        with app.app_context():
            from models import db, Submission, GradingJob

            # Create a job
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Grade this submission"
            )
            db.session.add(job)
            db.session.commit()

            # Create a submission
            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending"
            )
            db.session.add(submission)
            db.session.commit()

            # Test with invalid scheme_id
            response = client.get(f"/submissions/{submission.id}/grade?scheme_id=invalid-scheme")
            # Should redirect with flash message
            assert response.status_code == 302

    def test_grade_submission_deleted_scheme(self, client, app):
        """Test the grade submission page with a soft-deleted scheme."""
        with app.app_context():
            from models import db, GradingScheme, Submission, GradingJob

            # Create a deleted scheme
            scheme = GradingScheme(
                name="Deleted Scheme",
                total_possible_points=100.0,
                is_deleted=True
            )
            db.session.add(scheme)
            db.session.commit()

            # Create a job
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Grade this submission"
            )
            db.session.add(job)
            db.session.commit()

            # Create a submission
            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending"
            )
            db.session.add(submission)
            db.session.commit()

            # Test with deleted scheme
            response = client.get(f"/submissions/{submission.id}/grade?scheme_id={scheme.id}")
            # Should redirect with flash message
            assert response.status_code == 302

    def test_grade_submission_with_job_scheme(self, client, app):
        """Test grade submission falls back to job's scheme_id."""
        with app.app_context():
            from models import db, GradingScheme, Submission, GradingJob

            # Create a scheme
            scheme = GradingScheme(
                name="Job Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()

            # Create a job with the scheme
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Grade this submission",
                scheme_id=scheme.id
            )
            db.session.add(job)
            db.session.commit()

            # Create a submission
            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending"
            )
            db.session.add(submission)
            db.session.commit()

            # Test without explicit scheme_id - should use job's scheme
            response = client.get(f"/submissions/{submission.id}/grade")
            assert response.status_code == 200

    def test_grade_submission_exception_handling(self, client, app):
        """Test exception handling in grade_submission route."""
        with app.app_context():
            from models import db, Submission, GradingJob

            # Create a job
            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Grade this submission"
            )
            db.session.add(job)
            db.session.commit()

            # Create a submission
            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending"
            )
            db.session.add(submission)
            db.session.commit()
            sub_id = submission.id

        # Patch render_template to raise an exception
        with patch("routes.grading_ui.render_template") as mock_render:
            mock_render.side_effect = Exception("Template error")
            response = client.get(f"/submissions/{sub_id}/grade")
            # Should redirect due to exception handling
            assert response.status_code == 302
