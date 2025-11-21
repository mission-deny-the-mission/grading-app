"""
Integration tests for automatic backup functionality.

Tests automatic backup creation, scheduling, and retention cleanup
in a real environment with actual file operations.
"""

import os
import pytest
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def temp_user_data_dir():
    """Create a temporary user data directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        user_data = Path(tmpdir)

        # Create required subdirectories
        (user_data / 'backups').mkdir()
        (user_data / 'uploads').mkdir()

        # Create a minimal SQLite database
        db_path = user_data / 'grading.db'
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create minimal tables for statistics
        cursor.execute("""
            CREATE TABLE grading_scheme (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE graded_submission (
                id INTEGER PRIMARY KEY,
                student_id TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE grading_job (
                id INTEGER PRIMARY KEY,
                status TEXT
            )
        """)

        # Insert test data
        cursor.execute("INSERT INTO grading_scheme (name) VALUES ('Test Scheme')")
        cursor.execute("INSERT INTO graded_submission (student_id) VALUES ('student1')")
        cursor.execute("INSERT INTO grading_job (status) VALUES ('completed')")

        conn.commit()
        conn.close()

        # Create a test upload file
        test_upload = user_data / 'uploads' / 'test_submission'
        test_upload.mkdir()
        (test_upload / 'document.txt').write_text('Test submission content')

        yield user_data


class TestAutomaticBackupCreation:
    """Test automatic backup creation functionality."""

    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_create_backup_on_schedule(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        temp_user_data_dir
    ):
        """Test that automatic backup creates a valid ZIP file."""
        from desktop.scheduler import create_automatic_backup

        # Mock settings to use temp directory
        mock_get_user_data_dir.return_value = temp_user_data_dir

        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.database_path': str(temp_user_data_dir / 'grading.db'),
            'data.uploads_path': str(temp_user_data_dir / 'uploads'),
            'app_version': '0.1.0'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings

        # Create backup
        create_automatic_backup()

        # Verify backup was created
        backups_dir = temp_user_data_dir / 'backups'
        backup_files = list(backups_dir.glob('auto-backup-*.zip'))

        assert len(backup_files) == 1
        backup_file = backup_files[0]

        # Verify backup filename format
        assert backup_file.name.startswith('auto-backup-')
        assert backup_file.name.endswith('.zip')

        # Verify backup is a valid ZIP
        assert zipfile.is_zipfile(backup_file)

        # Verify backup contents
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            file_list = zipf.namelist()

            assert 'metadata.json' in file_list
            assert 'grading.db' in file_list
            assert 'uploads/test_submission/document.txt' in file_list

    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_multiple_backups_maintained(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        temp_user_data_dir
    ):
        """Test that multiple backups can be created and maintained."""
        from desktop.scheduler import create_automatic_backup

        # Mock settings
        mock_get_user_data_dir.return_value = temp_user_data_dir

        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.database_path': str(temp_user_data_dir / 'grading.db'),
            'data.uploads_path': str(temp_user_data_dir / 'uploads'),
            'data.backup_retention_days': 30,
            'app_version': '0.1.0'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings

        # Create multiple backups
        for i in range(3):
            create_automatic_backup()
            time.sleep(1.1)  # Ensure different timestamps

        # Verify all backups exist
        backups_dir = temp_user_data_dir / 'backups'
        backup_files = list(backups_dir.glob('auto-backup-*.zip'))

        assert len(backup_files) == 3

        # Verify all are valid ZIPs
        for backup_file in backup_files:
            assert zipfile.is_zipfile(backup_file)


class TestBackupRetention:
    """Test backup retention and cleanup functionality."""

    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_cleanup_old_backups(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        temp_user_data_dir
    ):
        """Test that old backups are deleted based on retention period."""
        from desktop.scheduler import cleanup_old_backups

        # Mock settings with 30 days retention
        mock_get_user_data_dir.return_value = temp_user_data_dir

        mock_settings = MagicMock()
        mock_settings.get.return_value = 30  # 30 days retention
        mock_settings_class.return_value = mock_settings

        backups_dir = temp_user_data_dir / 'backups'

        # Create old and recent backup files
        old_backup = backups_dir / 'auto-backup-20231101-020000.zip'
        mid_backup = backups_dir / 'auto-backup-20251015-020000.zip'
        recent_backup = backups_dir / 'auto-backup-20251116-020000.zip'

        for backup in [old_backup, mid_backup, recent_backup]:
            backup.write_text('fake backup content')

        # Set modification times
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days old
        mid_time = time.time() - (20 * 24 * 60 * 60)  # 20 days old
        recent_time = time.time()  # Now

        os.utime(old_backup, (old_time, old_time))
        os.utime(mid_backup, (mid_time, mid_time))
        os.utime(recent_backup, (recent_time, recent_time))

        # Run cleanup
        cleanup_old_backups()

        # Verify old backup deleted, recent ones kept
        assert not old_backup.exists()
        assert mid_backup.exists()
        assert recent_backup.exists()

    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_retention_respects_settings(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        temp_user_data_dir
    ):
        """Test that retention period from settings is respected."""
        from desktop.scheduler import cleanup_old_backups

        # Mock settings with 7 days retention
        mock_get_user_data_dir.return_value = temp_user_data_dir

        mock_settings = MagicMock()
        mock_settings.get.return_value = 7  # 7 days retention
        mock_settings_class.return_value = mock_settings

        backups_dir = temp_user_data_dir / 'backups'

        # Create backup files
        old_backup = backups_dir / 'auto-backup-old.zip'
        recent_backup = backups_dir / 'auto-backup-recent.zip'

        for backup in [old_backup, recent_backup]:
            backup.write_text('fake backup content')

        # Set modification times
        old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days old (should be deleted)
        recent_time = time.time() - (3 * 24 * 60 * 60)  # 3 days old (should be kept)

        os.utime(old_backup, (old_time, old_time))
        os.utime(recent_backup, (recent_time, recent_time))

        # Run cleanup
        cleanup_old_backups()

        # Verify retention period was respected
        assert not old_backup.exists()
        assert recent_backup.exists()


class TestBackupScheduling:
    """Test automatic backup scheduling based on settings."""

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_schedule_respects_enabled_setting(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        mock_scheduler,
        temp_user_data_dir
    ):
        """Test that backups are only scheduled when enabled."""
        from desktop.scheduler import schedule_automatic_backup

        mock_get_user_data_dir.return_value = temp_user_data_dir

        # Test with backups disabled
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': False,
            'data.backup_frequency': 'daily'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings

        schedule_automatic_backup()

        # Should not add job when disabled
        mock_scheduler.add_job.assert_not_called()

        # Reset mock
        mock_scheduler.reset_mock()

        # Test with backups enabled
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'daily'
        }.get(key, default)

        schedule_automatic_backup()

        # Should add job when enabled
        mock_scheduler.add_job.assert_called_once()

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_schedule_respects_frequency_setting(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        mock_scheduler,
        temp_user_data_dir
    ):
        """Test that backup frequency setting is respected."""
        from desktop.scheduler import schedule_automatic_backup

        mock_get_user_data_dir.return_value = temp_user_data_dir

        # Test 'never' frequency
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'never'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings

        schedule_automatic_backup()

        # Should not schedule when frequency is 'never'
        mock_scheduler.add_job.assert_not_called()

        # Reset and test 'daily'
        mock_scheduler.reset_mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'daily'
        }.get(key, default)

        schedule_automatic_backup()

        # Should schedule daily job
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs['id'] == 'automatic_backup'

        # Reset and test 'weekly'
        mock_scheduler.reset_mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'weekly'
        }.get(key, default)

        schedule_automatic_backup()

        # Should schedule weekly job
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs['id'] == 'automatic_backup'
        assert call_kwargs['day_of_week'] == 'sun'


class TestBackupIntegrity:
    """Test backup integrity and validation."""

    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_backup_contains_all_data(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        temp_user_data_dir
    ):
        """Test that backup contains complete data."""
        from desktop.scheduler import create_automatic_backup
        from desktop.data_export import validate_backup_bundle

        # Mock settings
        mock_get_user_data_dir.return_value = temp_user_data_dir

        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.database_path': str(temp_user_data_dir / 'grading.db'),
            'data.uploads_path': str(temp_user_data_dir / 'uploads'),
            'app_version': '0.1.0'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings

        # Create backup
        create_automatic_backup()

        # Get backup file
        backups_dir = temp_user_data_dir / 'backups'
        backup_file = list(backups_dir.glob('auto-backup-*.zip'))[0]

        # Validate backup
        is_valid, error_msg = validate_backup_bundle(str(backup_file))

        assert is_valid, f"Backup validation failed: {error_msg}"

        # Verify backup contents in detail
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            # Check all required files
            assert 'metadata.json' in zipf.namelist()
            assert 'grading.db' in zipf.namelist()

            # Verify metadata
            import json
            metadata = json.loads(zipf.read('metadata.json'))

            assert metadata['backup_version'] == '1.0'
            assert metadata['app_version'] == '0.1.0'
            assert metadata['includes']['database'] is True
            assert metadata['includes']['uploads'] is True
            assert metadata['statistics']['num_schemes'] == 1
            assert metadata['statistics']['num_submissions'] == 1
            assert metadata['statistics']['num_jobs'] == 1

    @patch('desktop.scheduler.Settings._get_user_data_dir')
    @patch('desktop.scheduler.Settings')
    def test_backup_cleanup_after_creation(
        self,
        mock_settings_class,
        mock_get_user_data_dir,
        temp_user_data_dir
    ):
        """Test that cleanup runs automatically after backup creation."""
        from desktop.scheduler import create_automatic_backup

        # Mock settings
        mock_get_user_data_dir.return_value = temp_user_data_dir

        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.database_path': str(temp_user_data_dir / 'grading.db'),
            'data.uploads_path': str(temp_user_data_dir / 'uploads'),
            'data.backup_retention_days': 7,
            'app_version': '0.1.0'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings

        backups_dir = temp_user_data_dir / 'backups'

        # Create an old backup manually
        old_backup = backups_dir / 'auto-backup-20231101-020000.zip'
        old_backup.write_text('old backup')
        old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days old
        os.utime(old_backup, (old_time, old_time))

        # Create new backup (should trigger cleanup)
        create_automatic_backup()

        # Verify old backup was cleaned up
        assert not old_backup.exists()

        # Verify new backup exists
        new_backups = list(backups_dir.glob('auto-backup-*.zip'))
        assert len(new_backups) == 1
