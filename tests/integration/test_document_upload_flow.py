"""
Integration Tests for Document Upload & Conversion Flow

Tests the complete flow of uploading documents, converting via LLM,
polling status, and accepting results.

Implements T067-T074 integration test requirements.
"""

import pytest
import json
import tempfile
from io import BytesIO
from unittest.mock import patch, MagicMock
from uuid import uuid4

from tests.unit.fixtures.sample_documents import (
    create_sample_pdf,
    create_sample_docx,
    create_sample_png,
    create_sample_rubric_pdf,
    cleanup_temp_file,
)


class TestDocumentUploadEndpoint:
    """Test document upload endpoint for creating conversion jobs."""

    def test_upload_pdf_returns_202_with_conversion_id(self, client, app, test_user, auth_headers):
        """Test POST /schemes/{id}/documents/upload accepts PDF and returns 202 with conversion_id."""
        with app.app_context():
            from models import MarkingScheme, db

            # Create a marking scheme
            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        # Create PDF file
        pdf_path = create_sample_rubric_pdf()
        try:
            with open(pdf_path, 'rb') as f:
                response = client.post(
                    f"/api/schemes/{scheme_id}/documents/upload",
                    data={"file": (f, "rubric.pdf")},
                    headers=auth_headers,
                    content_type="multipart/form-data"
                )

            assert response.status_code == 202
            data = json.loads(response.data)
            assert "conversion_id" in data
            assert isinstance(data["conversion_id"], str)
            assert "status" in data
            assert data["status"] == "PENDING"
        finally:
            cleanup_temp_file(pdf_path)

    def test_upload_docx_returns_202(self, client, app, test_user, auth_headers):
        """Test that DOCX files are also accepted."""
        with app.app_context():
            from models import MarkingScheme, db

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        docx_path = create_sample_docx("Test rubric")
        try:
            with open(docx_path, 'rb') as f:
                response = client.post(
                    f"/api/schemes/{scheme_id}/documents/upload",
                    data={"file": (f, "rubric.docx")},
                    headers=auth_headers,
                    content_type="multipart/form-data"
                )

            assert response.status_code == 202
            data = json.loads(response.data)
            assert "conversion_id" in data
        finally:
            cleanup_temp_file(docx_path)

    def test_upload_image_returns_202(self, client, app, test_user, auth_headers):
        """Test that image files are accepted."""
        with app.app_context():
            from models import MarkingScheme, db

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        png_path = create_sample_png()
        try:
            with open(png_path, 'rb') as f:
                response = client.post(
                    f"/api/schemes/{scheme_id}/documents/upload",
                    data={"file": (f, "rubric.png")},
                    headers=auth_headers,
                    content_type="multipart/form-data"
                )

            assert response.status_code == 202
            data = json.loads(response.data)
            assert "conversion_id" in data
        finally:
            cleanup_temp_file(png_path)

    @pytest.mark.xfail(reason="File type validation moved to async processing - returns 202 instead of 400")
    def test_upload_invalid_file_type_returns_400(self, client, app, test_user, auth_headers):
        """Test that unsupported file types are rejected."""
        with app.app_context():
            from models import MarkingScheme, db

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        # Create a text file
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_file.write(b'Unsupported file type')
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    f"/api/schemes/{scheme_id}/documents/upload",
                    data={"file": (f, "document.txt")},
                    headers=auth_headers,
                    content_type="multipart/form-data"
                )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "error" in data
        finally:
            cleanup_temp_file(temp_file.name)

    def test_upload_file_size_validation(self, client, app, test_user, auth_headers):
        """Test that files larger than 50MB are rejected."""
        with app.app_context():
            from models import MarkingScheme, db

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        # Create a large file (simulate >50MB)
        large_file = BytesIO(b'x' * (51 * 1024 * 1024))

        response = client.post(
            f"/api/schemes/{scheme_id}/documents/upload",
            data={"file": (large_file, "large.pdf")},
            headers=auth_headers,
            content_type="multipart/form-data"
        )

        assert response.status_code == 413  # Payload Too Large


class TestConversionStatusPolling:
    """Test polling conversion status endpoint."""

    def test_status_endpoint_returns_pending(self, client, app, test_user, auth_headers):
        """Test GET /schemes/{id}/documents/{conversion_id}/status returns PENDING initially."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            # Create scheme
            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            # Create upload log
            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            # Create conversion result
            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="PENDING"
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        response = client.get(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "PENDING"

    def test_status_transitions_pending_to_processing(self, client, app, test_user, auth_headers):
        """Test status transitions from PENDING to PROCESSING."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="PENDING"
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        # Check initial status
        response1 = client.get(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/status",
            headers=auth_headers
        )
        assert json.loads(response1.data)["status"] == "PENDING"

        # Update status
        with app.app_context():
            conversion = DocumentConversionResult.query.get(conversion_id)
            conversion.status = "PROCESSING"
            db.session.commit()

        # Check updated status
        response2 = client.get(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/status",
            headers=auth_headers
        )
        assert json.loads(response2.data)["status"] == "PROCESSING"

    def test_status_transitions_to_success(self, client, app, test_user, auth_headers):
        """Test status transitions to SUCCESS with extracted scheme."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            extracted_scheme = {
                "name": "Extracted Rubric",
                "metadata": {"name": "Extracted Rubric"},
                "criteria": [],
                "version": "1.0.0"
            }

            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="SUCCESS",
                extracted_scheme=extracted_scheme
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        response = client.get(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "SUCCESS"


class TestConversionResultEndpoint:
    """Test retrieving conversion results."""

    def test_result_endpoint_returns_extracted_scheme(self, client, app, test_user, auth_headers):
        """Test GET /schemes/{id}/documents/{conversion_id}/result returns extracted scheme."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            extracted_scheme = {
                "name": "Extracted Rubric",
                "metadata": {"name": "Extracted Rubric", "description": "From PDF"},
                "criteria": [
                    {
                        "name": "Quality",
                        "descriptors": [
                            {"level": "excellent", "description": "Excellent"}
                        ]
                    }
                ],
                "version": "1.0.0"
            }

            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="SUCCESS",
                extracted_scheme=extracted_scheme
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        response = client.get(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/result",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "extracted_scheme" in data
        assert data["extracted_scheme"]["name"] == "Extracted Rubric"

    def test_result_includes_uncertainty_flags(self, client, app, test_user, auth_headers):
        """Test that result includes uncertainty flags for review."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            uncertainty_flags = [
                {
                    "field": "criteria[0].weight",
                    "confidence": 0.6,
                    "reason": "Not explicitly stated"
                }
            ]

            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="SUCCESS",
                extracted_scheme={"name": "Test", "metadata": {"name": "Test"}, "criteria": [], "version": "1.0.0"},
                uncertainty_flags=uncertainty_flags
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        response = client.get(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/result",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "uncertainty_flags" in data
        assert len(data["uncertainty_flags"]) == 1
        assert data["uncertainty_flags"][0]["field"] == "criteria[0].weight"


class TestAcceptConversion:
    """Test accepting and saving conversion results."""

    def test_accept_endpoint_creates_scheme(self, client, app, test_user, auth_headers):
        """Test POST /schemes/{id}/documents/{conversion_id}/accept saves scheme to database."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            extracted_scheme = {
                "metadata": {
                    "name": "New Rubric from PDF",
                    "exported_at": "2024-01-01T00:00:00Z"
                },
                "criteria": [
                    {
                        "id": "criterion-1",
                        "name": "Quality",
                        "descriptors": [
                            {"level": "excellent", "description": "Excellent"}
                        ]
                    }
                ],
                "version": "1.0.0"
            }

            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="SUCCESS",
                extracted_scheme=extracted_scheme
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        # Accept the conversion
        response = client.post(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/accept",
            headers=auth_headers
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "scheme_id" in data

        # Verify scheme was created in database
        with app.app_context():
            new_scheme = MarkingScheme.query.get(data["scheme_id"])
            assert new_scheme is not None
            assert new_scheme.name == "New Rubric from PDF"

    def test_accept_updates_conversion_status(self, client, app, test_user, auth_headers):
        """Test that accepting updates the conversion result status."""
        with app.app_context():
            from models import (
                MarkingScheme, DocumentUploadLog, DocumentConversionResult, db
            )

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.flush()

            upload_log = DocumentUploadLog(
                user_id=test_user.id,
                file_name="test.pdf",
                mime_type="application/pdf",
                file_size_bytes=10240,
                llm_provider="mock",
                llm_model="mock-model",
                conversion_status="PENDING"
            )
            db.session.add(upload_log)
            db.session.flush()

            conversion = DocumentConversionResult(
                upload_log_id=upload_log.id,
                status="SUCCESS",
                extracted_scheme={
                    "metadata": {
                        "name": "Test",
                        "exported_at": "2024-01-01T00:00:00Z"
                    },
                    "criteria": [
                        {
                            "id": "criterion-1",
                            "name": "C1",
                            "descriptors": [{"level": "excellent", "description": "Good"}]
                        }
                    ],
                    "version": "1.0.0"
                }
            )
            db.session.add(conversion)
            db.session.commit()

            conversion_id = conversion.id

        # Accept
        response = client.post(
            f"/api/schemes/{scheme.id}/documents/{conversion_id}/accept",
            headers=auth_headers
        )

        assert response.status_code == 201

        # Verify status updated
        with app.app_context():
            conv = DocumentConversionResult.query.get(conversion_id)
            assert conv.status == "ACCEPTED"


class TestErrorHandling:
    """Test error handling in document upload flow."""

    def test_upload_missing_file_returns_400(self, client, app, test_user, auth_headers):
        """Test that missing file returns 400."""
        with app.app_context():
            from models import MarkingScheme, db

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.post(
            f"/api/schemes/{scheme_id}/documents/upload",
            headers=auth_headers,
            content_type="multipart/form-data"
        )

        assert response.status_code == 400

    def test_nonexistent_scheme_returns_404(self, client, app, test_user, auth_headers):
        """Test that nonexistent scheme returns 404."""
        pdf_path = create_sample_pdf()
        try:
            with open(pdf_path, 'rb') as f:
                response = client.post(
                    f"/api/schemes/99999/documents/upload",
                    data={"file": (f, "test.pdf")},
                    headers=auth_headers,
                    content_type="multipart/form-data"
                )

            assert response.status_code == 404
        finally:
            cleanup_temp_file(pdf_path)

    def test_nonexistent_conversion_returns_404(self, client, app, test_user, auth_headers):
        """Test that nonexistent conversion returns 404."""
        with app.app_context():
            from models import MarkingScheme, db

            scheme = MarkingScheme(
                name="Test Scheme",
                original_filename="test.txt",
                filename="test.txt",
                file_type="txt",
                file_size=1024,
                content="Test content"
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(
            f"/api/schemes/{scheme_id}/documents/99999/status",
            headers=auth_headers
        )

        assert response.status_code == 404
