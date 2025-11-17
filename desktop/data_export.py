"""
Data Export and Import for Desktop Application

Provides functionality to export all application data (database + uploads) into
a portable ZIP bundle for backup and migration purposes.
"""

import json
import logging
import os
import platform
import shutil
import socket
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def export_data(
    database_path: str,
    uploads_path: str,
    output_path: str,
    app_version: str = "0.1.0"
) -> None:
    """
    Export all application data to a ZIP bundle.

    Creates a backup bundle containing:
    - SQLite database file
    - All uploaded submission files
    - metadata.json with backup information

    Args:
        database_path: Path to the SQLite database file
        uploads_path: Path to the uploads directory
        output_path: Path where the ZIP bundle should be created
        app_version: Current application version (default: "0.1.0")

    Raises:
        FileNotFoundError: If database or uploads directory doesn't exist
        IOError: If unable to create ZIP file
    """
    db_path = Path(database_path)
    uploads_dir = Path(uploads_path)
    output_file = Path(output_path)

    # Validate inputs
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    if not uploads_dir.exists():
        logger.warning(f"Uploads directory not found: {uploads_path}")
        uploads_dir.mkdir(parents=True, exist_ok=True)

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Create metadata
    metadata = create_backup_metadata(
        database_path=str(db_path),
        uploads_path=str(uploads_dir),
        app_version=app_version
    )

    # Create ZIP bundle
    logger.info(f"Creating backup bundle at {output_path}")

    try:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database file
            zipf.write(db_path, 'grading.db')
            logger.debug(f"Added database: {db_path}")

            # Add all files in uploads directory
            if uploads_dir.exists() and any(uploads_dir.iterdir()):
                for item in uploads_dir.rglob('*'):
                    if item.is_file():
                        # Preserve directory structure under uploads/
                        arcname = Path('uploads') / item.relative_to(uploads_dir)
                        zipf.write(item, arcname)
                        logger.debug(f"Added file: {arcname}")

            # Add metadata
            metadata_json = json.dumps(metadata, indent=2)
            zipf.writestr('metadata.json', metadata_json)
            logger.debug("Added metadata.json")

        logger.info(f"Successfully created backup bundle: {output_path}")
        logger.info(f"Total size: {output_file.stat().st_size / (1024*1024):.2f} MB")

    except Exception as e:
        # Clean up partial file on error
        if output_file.exists():
            output_file.unlink()
        logger.error(f"Failed to create backup bundle: {e}")
        raise IOError(f"Failed to create backup bundle: {e}")


def create_backup_metadata(
    database_path: str,
    uploads_path: str,
    app_version: str = "0.1.0"
) -> Dict:
    """
    Create backup metadata dictionary per data-model.md schema.

    Args:
        database_path: Path to the SQLite database file
        uploads_path: Path to the uploads directory
        app_version: Current application version

    Returns:
        Dictionary containing backup metadata
    """
    db_path = Path(database_path)
    uploads_dir = Path(uploads_path)

    # Calculate database size
    db_size = db_path.stat().st_size if db_path.exists() else 0

    # Calculate uploads size
    uploads_size = 0
    if uploads_dir.exists():
        for item in uploads_dir.rglob('*'):
            if item.is_file():
                uploads_size += item.stat().st_size

    # Count statistics from database
    statistics = _get_database_statistics(database_path)

    metadata = {
        "backup_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "app_version": app_version,
        "platform": platform.system().lower(),
        "hostname": socket.gethostname(),
        "database_schema_version": "003",  # Current Flask-Migrate revision
        "includes": {
            "database": True,
            "uploads": True,
            "settings": False,  # Settings excluded by default for security
            "credentials": False  # API keys NEVER included for security
        },
        "statistics": {
            "num_schemes": statistics.get("num_schemes", 0),
            "num_submissions": statistics.get("num_submissions", 0),
            "num_jobs": statistics.get("num_jobs", 0),
            "database_size_bytes": db_size,
            "uploads_size_bytes": uploads_size,
            "total_size_bytes": db_size + uploads_size
        }
    }

    return metadata


def _get_database_statistics(database_path: str) -> Dict:
    """
    Get statistics from the database for backup metadata.

    Args:
        database_path: Path to the SQLite database file

    Returns:
        Dictionary with database statistics
    """
    try:
        import sqlite3

        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Count grading schemes
        cursor.execute("SELECT COUNT(*) FROM grading_scheme")
        num_schemes = cursor.fetchone()[0]

        # Count submissions
        cursor.execute("SELECT COUNT(*) FROM graded_submission")
        num_submissions = cursor.fetchone()[0]

        # Count grading jobs
        cursor.execute("SELECT COUNT(*) FROM grading_job")
        num_jobs = cursor.fetchone()[0]

        conn.close()

        return {
            "num_schemes": num_schemes,
            "num_submissions": num_submissions,
            "num_jobs": num_jobs
        }

    except Exception as e:
        logger.warning(f"Failed to get database statistics: {e}")
        return {
            "num_schemes": 0,
            "num_submissions": 0,
            "num_jobs": 0
        }


def validate_backup_bundle(bundle_path: str) -> Tuple[bool, str]:
    """
    Validate a backup bundle before import.

    Checks:
    - ZIP integrity (no corruption)
    - Required files present (metadata.json, grading.db)
    - Metadata schema validity
    - Database is valid SQLite format
    - File sizes match metadata (±1% tolerance)

    Args:
        bundle_path: Path to the backup ZIP file

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, "error description") if invalid
    """
    bundle = Path(bundle_path)

    # Check file exists
    if not bundle.exists():
        return False, f"Bundle file not found: {bundle_path}"

    try:
        # Open and validate ZIP
        with zipfile.ZipFile(bundle, 'r') as zipf:
            # Test ZIP integrity
            bad_file = zipf.testzip()
            if bad_file:
                return False, f"Corrupted file in bundle: {bad_file}"

            # Get file list
            file_list = zipf.namelist()

            # Check required files
            if 'metadata.json' not in file_list:
                return False, "Missing required file: metadata.json"

            if 'grading.db' not in file_list:
                return False, "Missing required file: grading.db"

            # Read and validate metadata
            metadata_content = zipf.read('metadata.json')
            try:
                metadata = json.loads(metadata_content)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON in metadata.json: {e}"

            # Validate metadata schema
            required_fields = ['backup_version', 'created_at', 'app_version',
                             'platform', 'includes', 'statistics']
            for field in required_fields:
                if field not in metadata:
                    return False, f"Missing required metadata field: {field}"

            # Validate backup_version
            if metadata['backup_version'] not in ['1.0']:
                return False, f"Unsupported backup version: {metadata['backup_version']}"

            # Validate database file
            db_info = zipf.getinfo('grading.db')
            if db_info.file_size == 0:
                return False, "Database file is empty"

            # Validate database is SQLite format (magic number check)
            db_content = zipf.read('grading.db')
            if not db_content.startswith(b'SQLite format 3\x00'):
                return False, "Database file is not valid SQLite format"

            # Validate file sizes match metadata (±1% tolerance)
            actual_db_size = db_info.file_size
            expected_db_size = metadata['statistics']['database_size_bytes']

            if expected_db_size > 0:
                size_diff_pct = abs(actual_db_size - expected_db_size) / expected_db_size
                if size_diff_pct > 0.01:  # 1% tolerance
                    logger.warning(
                        f"Database size mismatch: expected {expected_db_size}, "
                        f"got {actual_db_size} ({size_diff_pct*100:.1f}% diff)"
                    )

            # Calculate actual uploads size
            actual_uploads_size = 0
            for name in file_list:
                if name.startswith('uploads/'):
                    actual_uploads_size += zipf.getinfo(name).file_size

            expected_uploads_size = metadata['statistics']['uploads_size_bytes']
            if expected_uploads_size > 0:
                size_diff_pct = abs(actual_uploads_size - expected_uploads_size) / expected_uploads_size
                if size_diff_pct > 0.01:  # 1% tolerance
                    logger.warning(
                        f"Uploads size mismatch: expected {expected_uploads_size}, "
                        f"got {actual_uploads_size} ({size_diff_pct*100:.1f}% diff)"
                    )

        return True, ""

    except zipfile.BadZipFile:
        return False, "File is not a valid ZIP archive"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def import_data(
    bundle_path: str,
    database_path: str,
    uploads_path: str,
    backup_existing: bool = True
) -> None:
    """
    Import data from a backup bundle.

    Extracts and restores:
    - SQLite database file
    - All uploaded submission files

    Args:
        bundle_path: Path to the backup ZIP file
        database_path: Path where database should be restored
        uploads_path: Path where uploads should be restored
        backup_existing: If True, backup existing data before import

    Raises:
        ValueError: If bundle validation fails
        IOError: If extraction fails
    """
    # Validate bundle first
    is_valid, error_msg = validate_backup_bundle(bundle_path)
    if not is_valid:
        raise ValueError(f"Invalid backup bundle: {error_msg}")

    db_path = Path(database_path)
    uploads_dir = Path(uploads_path)

    # Backup existing data if requested
    if backup_existing:
        if db_path.exists():
            backup_db = db_path.with_suffix('.db.pre-import-backup')
            shutil.copy2(db_path, backup_db)
            logger.info(f"Backed up existing database to {backup_db}")

        if uploads_dir.exists() and any(uploads_dir.iterdir()):
            backup_uploads = uploads_dir.parent / 'uploads.pre-import-backup'
            if backup_uploads.exists():
                shutil.rmtree(backup_uploads)
            shutil.copytree(uploads_dir, backup_uploads)
            logger.info(f"Backed up existing uploads to {backup_uploads}")

    logger.info(f"Importing data from {bundle_path}")

    try:
        with zipfile.ZipFile(bundle_path, 'r') as zipf:
            # Extract database
            db_path.parent.mkdir(parents=True, exist_ok=True)
            zipf.extract('grading.db', db_path.parent)
            extracted_db = db_path.parent / 'grading.db'
            if extracted_db != db_path:
                extracted_db.rename(db_path)
            logger.info(f"Restored database to {database_path}")

            # Extract uploads
            uploads_dir.mkdir(parents=True, exist_ok=True)

            # Remove existing uploads
            for item in uploads_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            # Extract all uploads
            for member in zipf.namelist():
                if member.startswith('uploads/') and member != 'uploads/':
                    target_path = db_path.parent / member
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    with zipf.open(member) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)

            logger.info(f"Restored uploads to {uploads_path}")

        logger.info("Data import completed successfully")

    except Exception as e:
        logger.error(f"Failed to import data: {e}")
        raise IOError(f"Failed to import data: {e}")
