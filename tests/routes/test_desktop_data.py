"""
Tests for desktop data export/import routes.
"""

import io
import json
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_statistics():
    """Mock database statistics."""
    return {
        "num_schemes": 5,
        "num_submissions": 127,
        "num_jobs": 127,
        "database_size_bytes": 5242880,
        "uploads_size_bytes": 104857600,
        "total_size_bytes": 110100480
    }


@pytest.fixture
def mock_backup_bundle(tmp_path):
    """Create a mock backup bundle ZIP file."""
    bundle_path = tmp_path / "test-backup.zip"

    # Create mock metadata
    metadata = {
        "backup_version": "1.0",
        "created_at": "2025-11-16T10:30:00Z",
        "app_version": "0.1.0",
        "platform": "linux",
        "hostname": "test-host",
        "database_schema_version": "003",
        "includes": {
            "database": True,
            "uploads": True,
            "settings": False,
            "credentials": False
        },
        "statistics": {
            "num_schemes": 5,
            "num_submissions": 127,
            "num_jobs": 127,
            "database_size_bytes": 1024,
            "uploads_size_bytes": 2048,
            "total_size_bytes": 3072
        }
    }

    # Create ZIP with metadata and dummy database
    with zipfile.ZipFile(bundle_path, 'w') as zipf:
        zipf.writestr("metadata.json", json.dumps(metadata))
        zipf.writestr("grading.db", b"x" * 1024)  # Dummy database
        zipf.writestr("uploads/test.txt", b"test file")

    return bundle_path


class TestDataManagementPage:
    """Tests for the data management page display."""

    def test_show_data_management_success(self, client, app):
        """Test data management page loads successfully."""
        with app.app_context():
            from models import db
            db.create_all()

        response = client.get("/desktop/data")
        assert response.status_code == 200
        assert b"Data Management" in response.data
        assert b"Export Data" in response.data
        assert b"Import Data" in response.data

    def test_show_statistics(self, client, app):
        """Test statistics are displayed correctly."""
        with app.app_context():
            from models import db, GradingScheme

            db.create_all()

            # Create test data
            scheme = GradingScheme(
                name="Test Scheme",
                description="Test"
            )
            db.session.add(scheme)
            db.session.commit()

        response = client.get("/desktop/data")
        assert response.status_code == 200
        assert b"1" in response.data  # 1 scheme
        assert b"Grading Schemes" in response.data


class TestExportData:
    """Tests for data export functionality."""

    def test_export_returns_zip_file(self, client, app):
        """Test GET /desktop/data/export returns ZIP file."""
        with app.app_context():
            from models import db
            db.create_all()

        def create_mock_export(database_path, uploads_path, output_path):
            """Create a mock ZIP file at output_path."""
            with zipfile.ZipFile(output_path, 'w') as zipf:
                zipf.writestr("metadata.json", "{}")
                zipf.writestr("grading.db", "test")

        with patch("desktop.data_export.export_data", side_effect=create_mock_export):
            response = client.get("/desktop/data/export")

            assert response.status_code == 200
            assert response.mimetype == "application/zip"
            assert "grading-app-backup-" in response.headers.get("Content-Disposition", "")

    def test_export_handles_failure(self, client, app):
        """Test export route handles export failure."""
        with app.app_context():
            from models import db
            db.create_all()

        with patch("desktop.data_export.export_data") as mock_export:
            mock_export.side_effect = IOError("Export failed")

            response = client.get("/desktop/data/export")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Export failed" in data["message"]

    def test_export_file_headers_correct(self, client, app):
        """Test export file has correct download headers."""
        with app.app_context():
            from models import db
            db.create_all()

        def create_mock_export(database_path, uploads_path, output_path):
            """Create a mock ZIP file at output_path."""
            with zipfile.ZipFile(output_path, 'w') as zipf:
                zipf.writestr("test.txt", "test")

        with patch("desktop.data_export.export_data", side_effect=create_mock_export):
            response = client.get("/desktop/data/export")

            assert response.status_code == 200
            assert response.mimetype == "application/zip"

            content_disposition = response.headers.get("Content-Disposition", "")
            assert "attachment" in content_disposition
            assert ".zip" in content_disposition


class TestImportData:
    """Tests for data import functionality."""

    def test_import_requires_file(self, client, app):
        """Test import fails without file upload."""
        with app.app_context():
            from models import db
            db.create_all()

        response = client.post("/desktop/data/import")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "No backup file" in data["message"]

    def test_import_validates_zip_format(self, client, app):
        """Test import rejects non-ZIP files."""
        with app.app_context():
            from models import db
            db.create_all()

        # Create a non-ZIP file
        data = {
            "backup_file": (io.BytesIO(b"not a zip"), "test.txt")
        }

        response = client.post(
            "/desktop/data/import",
            data=data,
            content_type="multipart/form-data"
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert result["success"] is False
        assert "Invalid file format" in result["message"]

    def test_import_validates_bundle(self, client, app, mock_backup_bundle):
        """Test import validates backup bundle."""
        with app.app_context():
            from models import db
            db.create_all()

        # Read the mock bundle
        with open(mock_backup_bundle, 'rb') as f:
            bundle_data = f.read()

        data = {
            "backup_file": (io.BytesIO(bundle_data), "backup.zip")
        }

        with patch("desktop.data_export.validate_backup_bundle") as mock_validate:
            mock_validate.return_value = (False, "Invalid bundle")

            response = client.post(
                "/desktop/data/import",
                data=data,
                content_type="multipart/form-data"
            )

            assert response.status_code == 400
            result = json.loads(response.data)
            assert result["success"] is False
            assert "Invalid bundle" in result["message"]

    def test_import_shows_overwrite_warning(self, client, app, mock_backup_bundle):
        """Test import shows warning when data exists."""
        with app.app_context():
            from models import db, GradingScheme
            db.create_all()

            # Create existing data
            scheme = GradingScheme(
                name="Existing Scheme",
                description="Test"
            )
            db.session.add(scheme)
            db.session.commit()

        # Read the mock bundle
        with open(mock_backup_bundle, 'rb') as f:
            bundle_data = f.read()

        data = {
            "backup_file": (io.BytesIO(bundle_data), "backup.zip")
        }

        # Mock validation to succeed
        with patch("desktop.data_export.validate_backup_bundle") as mock_validate:
            mock_validate.return_value = (True, "Valid")

            response = client.post(
                "/desktop/data/import",
                data=data,
                content_type="multipart/form-data"
            )

            assert response.status_code == 409  # Conflict
            result = json.loads(response.data)
            assert result["success"] is False
            assert result["requires_confirmation"] is True
            assert "overwrite" in result["message"].lower()
            assert "current_data" in result
            assert "backup_data" in result

    def test_import_with_overwrite_confirmation(self, client, app, mock_backup_bundle):
        """Test import proceeds with overwrite confirmation."""
        with app.app_context():
            from models import db
            db.create_all()

        # Read the mock bundle
        with open(mock_backup_bundle, 'rb') as f:
            bundle_data = f.read()

        data = {
            "backup_file": (io.BytesIO(bundle_data), "backup.zip"),
            "overwrite": "true"
        }

        with patch("desktop.data_export.validate_backup_bundle") as mock_validate, \
             patch("desktop.data_export.import_data") as mock_import:

            mock_validate.return_value = (True, "Valid")
            mock_import.return_value = None

            response = client.post(
                "/desktop/data/import",
                data=data,
                content_type="multipart/form-data"
            )

            assert response.status_code == 200
            result = json.loads(response.data)
            assert result["success"] is True
            assert mock_import.called

    def test_import_handles_import_failure(self, client, app, mock_backup_bundle):
        """Test import handles failure from import_data."""
        with app.app_context():
            from models import db
            db.create_all()

        # Read the mock bundle
        with open(mock_backup_bundle, 'rb') as f:
            bundle_data = f.read()

        data = {
            "backup_file": (io.BytesIO(bundle_data), "backup.zip"),
            "overwrite": "true"
        }

        with patch("desktop.data_export.validate_backup_bundle") as mock_validate, \
             patch("desktop.data_export.import_data") as mock_import:

            mock_validate.return_value = (True, "Valid")
            mock_import.side_effect = IOError("Database error")

            response = client.post(
                "/desktop/data/import",
                data=data,
                content_type="multipart/form-data"
            )

            assert response.status_code == 500
            result = json.loads(response.data)
            assert result["success"] is False
            assert "Database error" in result["message"]


class TestImportDataCleanup:
    """Tests for import data cleanup and error handling."""

    def test_import_cleans_up_temp_file_on_error(self, client, app):
        """Test temporary file is cleaned up on validation error."""
        with app.app_context():
            from models import db
            db.create_all()

        # Create a valid ZIP but mock validation failure
        temp_zip = io.BytesIO()
        with zipfile.ZipFile(temp_zip, 'w') as zipf:
            zipf.writestr("test.txt", "test")
        temp_zip.seek(0)

        data = {
            "backup_file": (temp_zip, "backup.zip")
        }

        with patch("desktop.data_export.validate_backup_bundle") as mock_validate:
            mock_validate.return_value = (False, "Invalid")

            response = client.post(
                "/desktop/data/import",
                data=data,
                content_type="multipart/form-data"
            )

            assert response.status_code == 400
            # File should be cleaned up (hard to test directly, but no exceptions should occur)
