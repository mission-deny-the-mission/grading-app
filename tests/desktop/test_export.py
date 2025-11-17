"""
Tests for desktop data export and import functionality.

Tests cover:
- T064: export_data() creates valid ZIP
- T065: import_data() restores files correctly
- T066: validate_backup_bundle() catches invalid bundles
- Round-trip test (export → import → verify data integrity)
"""

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from desktop.data_export import (
    create_backup_metadata,
    export_data,
    import_data,
    validate_backup_bundle,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_database(temp_dir):
    """Create a sample SQLite database with test data."""
    db_path = temp_dir / "grading.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables matching the application schema (singular names)
    cursor.execute("""
        CREATE TABLE grading_scheme (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            is_deleted BOOLEAN DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE graded_submission (
            id TEXT PRIMARY KEY,
            student_name TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE grading_job (
            id TEXT PRIMARY KEY,
            job_name TEXT NOT NULL,
            status TEXT,
            created_at TEXT
        )
    """)

    # Insert test data
    cursor.execute(
        "INSERT INTO grading_scheme VALUES (?, ?, ?, 0, ?, ?)",
        ("scheme1", "Test Scheme", "A test grading scheme",
         datetime.now(timezone.utc).isoformat(),
         datetime.now(timezone.utc).isoformat())
    )

    cursor.execute(
        "INSERT INTO graded_submission VALUES (?, ?, ?, ?)",
        ("sub1", "John Doe",
         datetime.now(timezone.utc).isoformat(),
         datetime.now(timezone.utc).isoformat())
    )

    cursor.execute(
        "INSERT INTO grading_job VALUES (?, ?, ?, ?)",
        ("job1", "Test Job", "pending",
         datetime.now(timezone.utc).isoformat())
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def sample_uploads(temp_dir):
    """Create sample upload files."""
    uploads_dir = temp_dir / "uploads"
    uploads_dir.mkdir()

    # Create a submission directory with a file
    sub_dir = uploads_dir / "submission1"
    sub_dir.mkdir()

    test_file = sub_dir / "document.txt"
    test_file.write_text("This is a test submission document.")

    # Create another submission
    sub_dir2 = uploads_dir / "submission2"
    sub_dir2.mkdir()

    test_file2 = sub_dir2 / "essay.txt"
    test_file2.write_text("This is another test essay submission.")

    return uploads_dir


# T064: Unit test for export_data()
class TestExportData:
    """Tests for export_data() function (T064)."""

    def test_export_creates_valid_zip(self, sample_database, sample_uploads, temp_dir):
        """Test that export_data() creates a valid ZIP file with all components."""
        output_path = temp_dir / "backup.zip"

        # Export data
        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(output_path)
        )

        # Verify ZIP was created
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Verify ZIP is valid
        assert zipfile.is_zipfile(output_path)

        # Check ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zipf:
            namelist = zipf.namelist()

            # Required files
            assert 'metadata.json' in namelist
            assert 'grading.db' in namelist

            # Upload files
            assert 'uploads/submission1/document.txt' in namelist
            assert 'uploads/submission2/essay.txt' in namelist

    def test_export_metadata_structure(self, sample_database, sample_uploads, temp_dir):
        """Test that exported metadata follows the correct schema."""
        output_path = temp_dir / "backup.zip"

        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(output_path)
        )

        # Read metadata
        with zipfile.ZipFile(output_path, 'r') as zipf:
            metadata_content = zipf.read('metadata.json')
            metadata = json.loads(metadata_content)

        # Verify schema (data-model.md lines 210-237)
        assert metadata['backup_version'] == '1.0'
        assert 'created_at' in metadata
        assert metadata['app_version'] == '0.1.0'
        assert 'platform' in metadata
        assert 'hostname' in metadata
        assert 'database_schema_version' in metadata

        # Check includes
        assert metadata['includes']['database'] is True
        assert metadata['includes']['uploads'] is True
        assert metadata['includes']['settings'] is False
        assert metadata['includes']['credentials'] is False

        # Check statistics
        stats = metadata['statistics']
        assert stats['num_schemes'] == 1
        assert stats['num_submissions'] == 1
        assert stats['num_jobs'] == 1
        assert stats['database_size_bytes'] > 0
        assert stats['uploads_size_bytes'] > 0
        assert stats['total_size_bytes'] == stats['database_size_bytes'] + stats['uploads_size_bytes']

    def test_export_handles_missing_uploads(self, sample_database, temp_dir):
        """Test export works even if uploads directory doesn't exist."""
        output_path = temp_dir / "backup.zip"
        nonexistent_uploads = temp_dir / "nonexistent_uploads"

        # Should create the directory and export successfully
        export_data(
            database_path=str(sample_database),
            uploads_path=str(nonexistent_uploads),
            output_path=str(output_path)
        )

        assert output_path.exists()

    def test_export_raises_on_missing_database(self, temp_dir):
        """Test export raises FileNotFoundError if database doesn't exist."""
        with pytest.raises(FileNotFoundError):
            export_data(
                database_path=str(temp_dir / "nonexistent.db"),
                uploads_path=str(temp_dir / "uploads"),
                output_path=str(temp_dir / "backup.zip")
            )


# T065: Unit test for create_backup_metadata()
class TestCreateBackupMetadata:
    """Tests for create_backup_metadata() function (T065)."""

    def test_metadata_schema_compliance(self, sample_database, sample_uploads):
        """Test that metadata follows exact schema from data-model.md."""
        metadata = create_backup_metadata(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads)
        )

        # Required fields from data-model.md lines 210-237
        assert metadata['backup_version'] == '1.0'
        assert 'created_at' in metadata
        assert metadata['app_version'] == '0.1.0'
        assert metadata['platform'] in ['linux', 'darwin', 'windows']
        assert isinstance(metadata['hostname'], str)
        assert 'database_schema_version' in metadata

        # Includes dict
        assert set(metadata['includes'].keys()) == {'database', 'uploads', 'settings', 'credentials'}

        # Statistics dict
        required_stats = ['num_schemes', 'num_submissions', 'num_jobs',
                         'database_size_bytes', 'uploads_size_bytes', 'total_size_bytes']
        assert set(metadata['statistics'].keys()) == set(required_stats)

    def test_metadata_statistics_accuracy(self, sample_database, sample_uploads):
        """Test that statistics are calculated correctly."""
        metadata = create_backup_metadata(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads)
        )

        stats = metadata['statistics']

        # Check database counts
        assert stats['num_schemes'] == 1
        assert stats['num_submissions'] == 1
        assert stats['num_jobs'] == 1

        # Check file sizes
        actual_db_size = Path(sample_database).stat().st_size
        assert stats['database_size_bytes'] == actual_db_size

        # Check total size calculation
        assert stats['total_size_bytes'] == stats['database_size_bytes'] + stats['uploads_size_bytes']

    def test_metadata_timestamp_format(self, sample_database, sample_uploads):
        """Test that created_at is in ISO 8601 format with Z suffix."""
        metadata = create_backup_metadata(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads)
        )

        # Should be ISO 8601 with Z suffix
        assert metadata['created_at'].endswith('Z')

        # Should be parseable as datetime
        # Remove Z and parse
        timestamp_str = metadata['created_at'].replace('Z', '+00:00')
        parsed = datetime.fromisoformat(timestamp_str)
        assert isinstance(parsed, datetime)


# T066: Unit test for validate_backup_bundle()
class TestValidateBackupBundle:
    """Tests for validate_backup_bundle() function (T066)."""

    def test_validates_good_bundle(self, sample_database, sample_uploads, temp_dir):
        """Test that valid bundles pass validation."""
        output_path = temp_dir / "backup.zip"

        # Create a valid bundle
        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(output_path)
        )

        # Validate it
        is_valid, error_msg = validate_backup_bundle(str(output_path))

        assert is_valid is True
        assert error_msg == ""

    def test_rejects_nonexistent_file(self, temp_dir):
        """Test validation fails for nonexistent file."""
        is_valid, error_msg = validate_backup_bundle(str(temp_dir / "nonexistent.zip"))

        assert is_valid is False
        assert "not found" in error_msg.lower()

    def test_rejects_non_zip_file(self, temp_dir):
        """Test validation fails for non-ZIP files."""
        not_a_zip = temp_dir / "not_a_zip.zip"
        not_a_zip.write_text("This is not a ZIP file")

        is_valid, error_msg = validate_backup_bundle(str(not_a_zip))

        assert is_valid is False
        assert "not a valid zip" in error_msg.lower() or "zip archive" in error_msg.lower()

    def test_rejects_missing_metadata(self, sample_database, sample_uploads, temp_dir):
        """Test validation fails if metadata.json is missing."""
        bundle_path = temp_dir / "bad_bundle.zip"

        # Create ZIP without metadata
        with zipfile.ZipFile(bundle_path, 'w') as zipf:
            zipf.write(sample_database, 'grading.db')

        is_valid, error_msg = validate_backup_bundle(str(bundle_path))

        assert is_valid is False
        assert "metadata.json" in error_msg

    def test_rejects_missing_database(self, temp_dir):
        """Test validation fails if grading.db is missing."""
        bundle_path = temp_dir / "bad_bundle.zip"

        # Create ZIP without database
        metadata = {
            "backup_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app_version": "0.1.0",
            "platform": "linux",
            "hostname": "test",
            "database_schema_version": "003",
            "includes": {"database": True, "uploads": True, "settings": False, "credentials": False},
            "statistics": {
                "num_schemes": 0,
                "num_submissions": 0,
                "num_jobs": 0,
                "database_size_bytes": 0,
                "uploads_size_bytes": 0,
                "total_size_bytes": 0
            }
        }

        with zipfile.ZipFile(bundle_path, 'w') as zipf:
            zipf.writestr('metadata.json', json.dumps(metadata))

        is_valid, error_msg = validate_backup_bundle(str(bundle_path))

        assert is_valid is False
        assert "grading.db" in error_msg

    def test_rejects_invalid_json_metadata(self, temp_dir):
        """Test validation fails if metadata is not valid JSON."""
        bundle_path = temp_dir / "bad_bundle.zip"

        with zipfile.ZipFile(bundle_path, 'w') as zipf:
            zipf.writestr('metadata.json', "This is not JSON")
            zipf.writestr('grading.db', b"fake db")

        is_valid, error_msg = validate_backup_bundle(str(bundle_path))

        assert is_valid is False
        assert "JSON" in error_msg or "json" in error_msg

    def test_rejects_unsupported_backup_version(self, sample_database, temp_dir):
        """Test validation fails for unsupported backup versions."""
        bundle_path = temp_dir / "bad_bundle.zip"

        metadata = {
            "backup_version": "99.0",  # Unsupported version
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app_version": "0.1.0",
            "platform": "linux",
            "hostname": "test",
            "includes": {"database": True, "uploads": True, "settings": False, "credentials": False},
            "statistics": {
                "num_schemes": 0,
                "num_submissions": 0,
                "num_jobs": 0,
                "database_size_bytes": 1000,
                "uploads_size_bytes": 0,
                "total_size_bytes": 1000
            }
        }

        with zipfile.ZipFile(bundle_path, 'w') as zipf:
            zipf.writestr('metadata.json', json.dumps(metadata))
            zipf.write(sample_database, 'grading.db')

        is_valid, error_msg = validate_backup_bundle(str(bundle_path))

        assert is_valid is False
        assert "version" in error_msg.lower()

    def test_validates_non_sqlite_database(self, temp_dir):
        """Test validation checks database is valid SQLite format."""
        bundle_path = temp_dir / "bad_bundle.zip"

        metadata = {
            "backup_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "app_version": "0.1.0",
            "platform": "linux",
            "hostname": "test",
            "database_schema_version": "003",
            "includes": {"database": True, "uploads": True, "settings": False, "credentials": False},
            "statistics": {
                "num_schemes": 0,
                "num_submissions": 0,
                "num_jobs": 0,
                "database_size_bytes": 100,
                "uploads_size_bytes": 0,
                "total_size_bytes": 100
            }
        }

        with zipfile.ZipFile(bundle_path, 'w') as zipf:
            zipf.writestr('metadata.json', json.dumps(metadata))
            zipf.writestr('grading.db', b"Not a SQLite database")

        is_valid, error_msg = validate_backup_bundle(str(bundle_path))

        assert is_valid is False
        assert "SQLite" in error_msg


# T067: Unit test for import_data()
class TestImportData:
    """Tests for import_data() function (T067)."""

    def test_import_restores_database(self, sample_database, sample_uploads, temp_dir):
        """Test that import correctly restores the database file."""
        # Create a backup
        backup_path = temp_dir / "backup.zip"
        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(backup_path)
        )

        # Import to a new location
        new_db = temp_dir / "restored" / "grading.db"
        new_uploads = temp_dir / "restored" / "uploads"

        import_data(
            bundle_path=str(backup_path),
            database_path=str(new_db),
            uploads_path=str(new_uploads),
            backup_existing=False
        )

        # Verify database was restored
        assert new_db.exists()

        # Verify database contents
        conn = sqlite3.connect(str(new_db))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM grading_scheme")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM graded_submission")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM grading_job")
        assert cursor.fetchone()[0] == 1

        conn.close()

    def test_import_restores_uploads(self, sample_database, sample_uploads, temp_dir):
        """Test that import correctly restores upload files."""
        # Create a backup
        backup_path = temp_dir / "backup.zip"
        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(backup_path)
        )

        # Import to a new location
        new_db = temp_dir / "restored" / "grading.db"
        new_uploads = temp_dir / "restored" / "uploads"

        import_data(
            bundle_path=str(backup_path),
            database_path=str(new_db),
            uploads_path=str(new_uploads),
            backup_existing=False
        )

        # Verify uploads were restored
        assert new_uploads.exists()
        assert (new_uploads / "submission1" / "document.txt").exists()
        assert (new_uploads / "submission2" / "essay.txt").exists()

        # Verify file contents
        content1 = (new_uploads / "submission1" / "document.txt").read_text()
        assert content1 == "This is a test submission document."

        content2 = (new_uploads / "submission2" / "essay.txt").read_text()
        assert content2 == "This is another test essay submission."

    def test_import_validates_bundle_first(self, temp_dir):
        """Test that import validates bundle before attempting to import."""
        # Create an invalid bundle
        bad_bundle = temp_dir / "bad.zip"
        bad_bundle.write_text("Not a ZIP file")

        new_db = temp_dir / "restored" / "grading.db"
        new_uploads = temp_dir / "restored" / "uploads"

        # Should raise ValueError due to validation failure
        with pytest.raises(ValueError, match="Invalid backup bundle"):
            import_data(
                bundle_path=str(bad_bundle),
                database_path=str(new_db),
                uploads_path=str(new_uploads),
                backup_existing=False
            )

    def test_import_creates_backup_of_existing_data(self, sample_database, sample_uploads, temp_dir):
        """Test that import backs up existing data when backup_existing=True."""
        # Create a backup
        backup_path = temp_dir / "backup.zip"
        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(backup_path)
        )

        # Create some existing data
        existing_db = temp_dir / "existing" / "grading.db"
        existing_db.parent.mkdir()
        existing_db.write_text("Existing database content")

        existing_uploads = temp_dir / "existing" / "uploads"
        existing_uploads.mkdir()
        (existing_uploads / "old_file.txt").write_text("Old upload")

        # Import with backup_existing=True
        import_data(
            bundle_path=str(backup_path),
            database_path=str(existing_db),
            uploads_path=str(existing_uploads),
            backup_existing=True
        )

        # Verify backup was created
        backup_db = existing_db.with_suffix('.db.pre-import-backup')
        assert backup_db.exists()

        backup_uploads = existing_uploads.parent / 'uploads.pre-import-backup'
        assert backup_uploads.exists()


# T068: Round-trip test (export → import → verify)
class TestRoundTrip:
    """Round-trip integration test for data portability (T068)."""

    def test_roundtrip_preserves_all_data(self, sample_database, sample_uploads, temp_dir):
        """Test that export → import preserves 100% data fidelity."""
        # Export data
        backup_path = temp_dir / "backup.zip"
        export_data(
            database_path=str(sample_database),
            uploads_path=str(sample_uploads),
            output_path=str(backup_path)
        )

        # Import to new location
        restored_db = temp_dir / "restored" / "grading.db"
        restored_uploads = temp_dir / "restored" / "uploads"

        import_data(
            bundle_path=str(backup_path),
            database_path=str(restored_db),
            uploads_path=str(restored_uploads),
            backup_existing=False
        )

        # Verify database integrity
        conn = sqlite3.connect(str(restored_db))
        cursor = conn.cursor()

        # Check schemes
        cursor.execute("SELECT id, name, description FROM grading_scheme WHERE is_deleted = 0")
        schemes = cursor.fetchall()
        assert len(schemes) == 1
        assert schemes[0][0] == "scheme1"
        assert schemes[0][1] == "Test Scheme"

        # Check submissions
        cursor.execute("SELECT id, student_name FROM graded_submission")
        submissions = cursor.fetchall()
        assert len(submissions) == 1
        assert submissions[0][0] == "sub1"
        assert submissions[0][1] == "John Doe"

        # Check jobs
        cursor.execute("SELECT id, job_name, status FROM grading_job")
        jobs = cursor.fetchall()
        assert len(jobs) == 1
        assert jobs[0][0] == "job1"
        assert jobs[0][1] == "Test Job"
        assert jobs[0][2] == "pending"

        conn.close()

        # Verify upload files
        doc1 = restored_uploads / "submission1" / "document.txt"
        assert doc1.exists()
        assert doc1.read_text() == "This is a test submission document."

        doc2 = restored_uploads / "submission2" / "essay.txt"
        assert doc2.exists()
        assert doc2.read_text() == "This is another test essay submission."

    def test_multiple_roundtrips_preserve_data(self, sample_database, sample_uploads, temp_dir):
        """Test that multiple export/import cycles don't corrupt data."""
        current_db = sample_database
        current_uploads = sample_uploads

        # Perform 3 export/import cycles
        for i in range(3):
            # Export
            backup_path = temp_dir / f"backup_{i}.zip"
            export_data(
                database_path=str(current_db),
                uploads_path=str(current_uploads),
                output_path=str(backup_path)
            )

            # Import to new location
            new_db = temp_dir / f"cycle_{i}" / "grading.db"
            new_uploads = temp_dir / f"cycle_{i}" / "uploads"

            import_data(
                bundle_path=str(backup_path),
                database_path=str(new_db),
                uploads_path=str(new_uploads),
                backup_existing=False
            )

            # Update current paths for next cycle
            current_db = new_db
            current_uploads = new_uploads

        # Verify final data is intact
        conn = sqlite3.connect(str(current_db))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM grading_scheme WHERE is_deleted = 0")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM graded_submission")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM grading_job")
        assert cursor.fetchone()[0] == 1

        conn.close()

        # Verify uploads still exist
        assert (current_uploads / "submission1" / "document.txt").exists()
        assert (current_uploads / "submission2" / "essay.txt").exists()
