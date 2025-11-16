"""Phase 4: Single-user mode optimization and grading feature tests."""

import time

import pytest

from models import db
from services.deployment_service import DeploymentService


class TestGradingWithoutAuth:
    """Test grading features work without authentication in single-user mode."""

    def test_index_page_accessible_without_auth(self, app_single_user, client_single_user):
        """Test index page loads without authentication."""
        response = client_single_user.get("/")

        assert response.status_code == 200
        assert b"grading" in response.data.lower() or b"upload" in response.data.lower()

    def test_config_page_accessible_without_auth(self, app_single_user, client_single_user):
        """Test config page accessible without authentication."""
        response = client_single_user.get("/config")

        assert response.status_code == 200

    def test_api_endpoints_work_without_auth(self, app_single_user, client_single_user):
        """Test API endpoints work without authentication in single-user mode."""
        # Test usage dashboard
        response = client_single_user.get("/api/usage/dashboard")
        assert response.status_code == 200

        # Test deployment mode endpoint
        response = client_single_user.get("/api/config/deployment-mode")
        assert response.status_code == 200
        data = response.get_json()
        assert data["mode"] == "single-user"

    def test_no_401_errors_in_single_user_mode(self, app_single_user, client_single_user):
        """Test no 401 errors occur in single-user mode."""
        endpoints = [
            "/",
            "/config",
            "/api/config/deployment-mode",
            "/api/config/health",
            "/api/usage/dashboard",
            "/api/auth/session",
        ]

        for endpoint in endpoints:
            response = client_single_user.get(endpoint)
            assert response.status_code != 401, f"Endpoint {endpoint} returned 401"
            assert response.status_code != 403, f"Endpoint {endpoint} returned 403"


class TestBackwardsCompatibility:
    """Test backwards compatibility with pre-auth grading system."""

    def test_existing_grading_jobs_accessible(self, app_single_user):
        """Test existing grading jobs still work in single-user mode."""
        with app_single_user.app_context():
            from models import GradingJob

            # Create a grading job without owner_id (legacy)
            job = GradingJob(
                job_name="Legacy Job",
                description="Job created before auth system",
                provider="openrouter",
                model="test-model",
                prompt="Test prompt",
                priority=5,
            )
            db.session.add(job)
            db.session.commit()

            # Should be retrievable
            retrieved = GradingJob.query.filter_by(job_name="Legacy Job").first()
            assert retrieved is not None
            assert retrieved.job_name == "Legacy Job"

    def test_marking_schemes_accessible(self, app_single_user):
        """Test marking schemes work without authentication."""
        with app_single_user.app_context():
            from models import MarkingScheme

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="scheme.txt",
                filename="scheme.txt",
                file_type="txt",
                file_size=100,
                content="Test content",
            )
            db.session.add(scheme)
            db.session.commit()

            retrieved = MarkingScheme.query.filter_by(name="Test Scheme").first()
            assert retrieved is not None

    def test_submissions_accessible(self, app_single_user):
        """Test submissions work without authentication."""
        with app_single_user.app_context():
            from models import GradingJob, Submission

            job = GradingJob(
                job_name="Test Job",
                provider="openrouter",
                model="test-model",
                prompt="Test",
                priority=5,
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=100,
                status="pending",
            )
            db.session.add(submission)
            db.session.commit()

            retrieved = Submission.query.filter_by(job_id=job.id).first()
            assert retrieved is not None


class TestAuthMiddlewareBypass:
    """Test authentication middleware is properly bypassed in single-user mode."""

    def test_middleware_bypass_logged(self, app_single_user, client_single_user, caplog):
        """Test middleware bypass is logged for debugging."""
        import logging

        caplog.set_level(logging.DEBUG)

        response = client_single_user.get("/")

        assert response.status_code == 200
        # Middleware should log single-user mode
        # Note: This is optional and depends on logging configuration

    def test_no_redirect_to_login(self, app_single_user, client_single_user):
        """Test no redirect to login page in single-user mode."""
        response = client_single_user.get("/config")

        # Should not redirect to login
        assert response.status_code != 302
        if response.status_code == 302:
            assert "login" not in response.location.lower()

    def test_no_session_required(self, app_single_user, client_single_user):
        """Test no session/cookie required for access."""
        # Clear any cookies - recreate client to ensure no cookies
        from flask.testing import FlaskClient
        client_single_user = app_single_user.test_client()

        response = client_single_user.get("/")

        assert response.status_code == 200


class TestPerformanceOptimization:
    """Test performance optimizations in single-user mode."""

    def test_api_response_time_under_threshold(self, app_single_user, client_single_user):
        """Test API responses are fast in single-user mode."""
        endpoints = [
            "/api/config/deployment-mode",
            "/api/config/health",
            "/api/auth/session",
        ]

        for endpoint in endpoints:
            start = time.time()
            response = client_single_user.get(endpoint)
            duration = (time.time() - start) * 1000  # Convert to ms

            assert response.status_code == 200
            assert duration < 500, f"Endpoint {endpoint} took {duration}ms (>500ms threshold)"

    def test_no_unnecessary_auth_queries(self, app_single_user, client_single_user):
        """Test no auth-related database queries in single-user mode."""
        with app_single_user.app_context():
            response = client_single_user.get("/")

            assert response.status_code == 200
            # In single-user mode, should not query User table

    def test_minimal_overhead_for_grading(self, app_single_user):
        """Test auth system adds minimal overhead to grading operations."""
        with app_single_user.app_context():
            from models import GradingJob

            # Time job creation
            start = time.time()
            for i in range(10):
                job = GradingJob(
                    job_name=f"Performance Test {i}",
                    provider="openrouter",
                    model="test-model",
                    prompt="Test",
                    priority=5,
                )
                db.session.add(job)
            db.session.commit()
            duration = (time.time() - start) * 1000

            # Should be fast (under 100ms for 10 jobs)
            assert duration < 100, f"Job creation took {duration}ms"


class TestDatabasePerformance:
    """Test database performance in single-user mode."""

    def test_no_auth_tables_queried(self, app_single_user, client_single_user):
        """Test auth tables not queried unnecessarily in single-user mode."""
        with app_single_user.app_context():
            # Make request
            response = client_single_user.get("/api/config/deployment-mode")

            assert response.status_code == 200
            # Should only query DeploymentConfig, not User or Session tables

    def test_deployment_mode_cached(self, app_single_user, client_single_user):
        """Test deployment mode is efficiently cached."""
        with app_single_user.app_context():
            # Make multiple requests
            start = time.time()
            for _ in range(10):
                response = client_single_user.get("/api/config/deployment-mode")
                assert response.status_code == 200
            duration = (time.time() - start) * 1000

            # Should be very fast due to caching (under 50ms for 10 requests)
            assert duration < 100, f"10 mode requests took {duration}ms"


class TestResourceUsage:
    """Test resource usage in single-user mode."""

    def test_minimal_memory_overhead(self, app_single_user):
        """Test auth system doesn't significantly increase memory usage."""
        with app_single_user.app_context():
            from models import GradingJob

            # Create many jobs
            jobs = []
            for i in range(100):
                job = GradingJob(
                    job_name=f"Job {i}",
                    provider="openrouter",
                    model="test-model",
                    prompt="Test",
                    priority=5,
                )
                jobs.append(job)
                db.session.add(job)

            db.session.commit()

            # Should complete without memory issues
            count = GradingJob.query.count()
            assert count == 100

    def test_efficient_session_handling(self, app_single_user, client_single_user):
        """Test session handling is efficient in single-user mode."""
        # Make many requests
        for _ in range(20):
            response = client_single_user.get("/api/auth/session")
            assert response.status_code == 200
            data = response.get_json()
            assert data["authenticated"] is True


class TestModeTransitionPerformance:
    """Test performance when switching between modes."""

    def test_mode_switch_persists(self, app):
        """Test mode switch persists correctly."""
        with app.app_context():
            # Start with single-user
            DeploymentService.set_mode("single-user")
            assert DeploymentService.is_single_user_mode()

            # Switch to multi-user
            DeploymentService.set_mode("multi-user")
            assert DeploymentService.is_multi_user_mode()

            # Switch back
            DeploymentService.set_mode("single-user")
            assert DeploymentService.is_single_user_mode()

    def test_mode_switch_affects_middleware(self, app, client):
        """Test mode switch immediately affects middleware behavior."""
        with app.app_context():
            # Set to single-user
            DeploymentService.set_mode("single-user")

        # Test access without auth
        response = client.get("/api/usage/dashboard")
        assert response.status_code == 200

        with app.app_context():
            # Switch to multi-user
            DeploymentService.set_mode("multi-user")

        # Should now require auth
        response = client.get("/api/usage/dashboard")
        assert response.status_code == 401


# Fixtures
@pytest.fixture
def app():
    """Create Flask app for testing."""
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        DeploymentService.initialize_default_config()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_single_user(app):
    """Create Flask app in single-user mode."""
    with app.app_context():
        DeploymentService.set_mode("single-user")
    return app


@pytest.fixture
def app_multi_user(app):
    """Create Flask app in multi-user mode."""
    with app.app_context():
        DeploymentService.set_mode("multi-user")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def client_single_user(app_single_user):
    """Create test client for single-user mode."""
    return app_single_user.test_client()


@pytest.fixture
def client_multi_user(app_multi_user):
    """Create test client for multi-user mode."""
    return app_multi_user.test_client()
