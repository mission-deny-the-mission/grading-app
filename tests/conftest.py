"""
Pytest configuration and fixtures for the grading app tests.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Import the app and models
from app import app as flask_app
from models import GradingJob, JobBatch, MarkingScheme, Submission, db


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Configure the app for testing
    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": tempfile.mkdtemp(),
        }
    )

    # Create the database tables
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

    # Clean up
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask app."""
    return app.test_cli_runner()


@pytest.fixture
def sample_job(app):
    """Create a sample grading job for testing."""
    with app.app_context():
        job = GradingJob(
            job_name="Test Job",
            description="A test job for unit testing",
            provider="openrouter",
            model="anthropic/claude-3-5-sonnet-20241022",
            prompt="Please grade this document.",
            priority=5,
            temperature=0.7,
            max_tokens=2000,
        )
        db.session.add(job)
        db.session.commit()

        # Store the ID and return a fresh object each time it's accessed

        # Store the ID for later retrieval
        return job


@pytest.fixture
def sample_submission(app, sample_job):
    """Create a sample submission for testing."""
    with app.app_context():
        submission = Submission(
            job_id=sample_job.id,
            original_filename="test_document.txt",
            filename="test_document.txt",
            file_type="txt",
            file_size=1024,
            status="failed",
        )
        db.session.add(submission)
        db.session.commit()

        # Store the ID for later retrieval
        return submission


@pytest.fixture
def sample_marking_scheme(app):
    """Create a sample marking scheme for testing."""
    with app.app_context():
        marking_scheme = MarkingScheme(
            name="Test Marking Scheme",
            original_filename="test_rubric.txt",
            filename="test_rubric.txt",
            file_type="txt",
            file_size=2048,
            content="Test marking scheme content",
        )
        db.session.add(marking_scheme)
        db.session.commit()
        db.session.refresh(marking_scheme)
        return marking_scheme


@pytest.fixture
def sample_batch(app):
    """Create a sample batch for testing."""
    with app.app_context():
        batch = JobBatch(
            batch_name="Test Batch",
            description="A test batch for unit testing",
            status="pending",
            priority=5,
        )
        db.session.add(batch)
        db.session.commit()

        # Store the ID and return a fresh object each time it's accessed
        batch_id = batch.id

        # Clear the session to ensure fresh object retrieval in tests
        db.session.expunge(batch)

        # Return a fresh instance
        fresh_batch = db.session.get(JobBatch, batch_id)
        return fresh_batch


@pytest.fixture
def mock_api_keys():
    """Mock API keys for testing."""
    with patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test-openrouter-key",
            "CLAUDE_API_KEY": "test-claude-key",
            "LM_STUDIO_URL": "http://localhost:1234/v1",
        },
    ):
        yield


@pytest.fixture
def mock_celery():
    """Mock Celery for testing."""
    with patch("tasks.celery_app") as mock_celery_app:
        mock_celery_app.send_task.return_value = MagicMock(id="test-task-id")
        yield mock_celery_app


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    content = "This is a test document for grading. It contains sample text to evaluate."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Clean up
    os.unlink(temp_path)


@pytest.fixture
def sample_docx_file():
    """Create a sample DOCX file for testing."""
    from docx import Document

    doc = Document()
    doc.add_paragraph("This is a test document for grading.")
    doc.add_paragraph("It contains multiple paragraphs to evaluate.")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc.save(f.name)
        temp_path = f.name

    yield temp_path

    # Clean up
    os.unlink(temp_path)


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""

    from PyPDF2 import PdfWriter

    # Create a simple PDF
    PdfWriter()
    # Note: This is a simplified PDF creation - in real tests you might want to use a pre-made PDF

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # For testing purposes, we'll create an empty PDF file
        pdf_content = (
            b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n"
            b"/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids []\n"
            b"/Count 0\n>>\nendobj\nxref\n0 3\n0000000000 65535 f \n"
            b"0000000009 00000 n \n0000000058 00000 n \ntrailer\n<<\n/Size 3\n"
            b"/Root 1 0 R\n>>\nstartxref\n108\n%%EOF\n"
        )
        f.write(pdf_content)
        temp_path = f.name

    yield temp_path

    # Clean up
    os.unlink(temp_path)
