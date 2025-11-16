"""
Unit tests for desktop/scheduler.py

Tests periodic task scheduling functionality using APScheduler.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import importlib
import sys

# Mock APScheduler before importing scheduler module
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()


class TestSchedulerInitialization:
    """Test scheduler initialization and configuration."""

    @patch('desktop.scheduler.BackgroundScheduler')
    @patch('desktop.scheduler.cleanup_old_files')
    @patch('desktop.scheduler.cleanup_completed_batches')
    def test_scheduler_instance_created(
        self,
        mock_cleanup_batches,
        mock_cleanup_files,
        mock_scheduler_class
    ):
        """Test that scheduler instance is created on module import."""
        # Reset module to force re-import
        if 'desktop.scheduler' in sys.modules:
            del sys.modules['desktop.scheduler']

        # Mock the scheduler instance
        mock_scheduler_instance = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler_instance

        # Import module (triggers initialization)
        import desktop.scheduler as scheduler_module

        # Verify BackgroundScheduler was instantiated
        mock_scheduler_class.assert_called_once()

        # Verify scheduler instance is accessible
        assert scheduler_module.scheduler is not None

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.cleanup_old_files')
    @patch('desktop.scheduler.cleanup_completed_batches')
    def test_initialize_scheduler_adds_jobs(
        self,
        mock_cleanup_batches,
        mock_cleanup_files,
        mock_scheduler
    ):
        """Test that initialize_scheduler adds both periodic jobs."""
        from desktop.scheduler import initialize_scheduler

        # Reset mock to clear any previous calls
        mock_scheduler.add_job.reset_mock()

        # Call initialization
        initialize_scheduler()

        # Verify add_job was called twice
        assert mock_scheduler.add_job.call_count == 2

        # Verify cleanup_old_files job configuration
        calls = mock_scheduler.add_job.call_args_list
        cleanup_files_call = calls[0]
        assert cleanup_files_call[0][0] == mock_cleanup_files
        assert cleanup_files_call[0][1] == 'interval'
        assert cleanup_files_call[1]['hours'] == 24
        assert cleanup_files_call[1]['id'] == 'cleanup_old_files'

        # Verify cleanup_completed_batches job configuration
        cleanup_batches_call = calls[1]
        assert cleanup_batches_call[0][0] == mock_cleanup_batches
        assert cleanup_batches_call[0][1] == 'interval'
        assert cleanup_batches_call[1]['hours'] == 6
        assert cleanup_batches_call[1]['id'] == 'cleanup_completed_batches'

    @patch('desktop.scheduler.scheduler')
    def test_initialize_scheduler_error_handling(self, mock_scheduler):
        """Test that initialization errors are properly logged and raised."""
        from desktop.scheduler import initialize_scheduler

        # Make add_job raise an exception
        mock_scheduler.add_job.side_effect = Exception("Job registration failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Job registration failed"):
            initialize_scheduler()


class TestSchedulerLifecycle:
    """Test scheduler start and stop functionality."""

    @patch('desktop.scheduler.scheduler')
    def test_start_scheduler(self, mock_scheduler):
        """Test starting the scheduler."""
        from desktop.scheduler import start

        # Mock scheduler as not running
        mock_scheduler.running = False

        # Start scheduler
        start()

        # Verify start was called
        mock_scheduler.start.assert_called_once()

    @patch('desktop.scheduler.scheduler')
    def test_start_scheduler_already_running(self, mock_scheduler):
        """Test starting scheduler when already running."""
        from desktop.scheduler import start

        # Mock scheduler as already running
        mock_scheduler.running = True

        # Start scheduler
        start()

        # Verify start was not called
        mock_scheduler.start.assert_not_called()

    @patch('desktop.scheduler.scheduler')
    def test_start_scheduler_error_handling(self, mock_scheduler):
        """Test error handling when starting scheduler."""
        from desktop.scheduler import start

        # Mock scheduler as not running
        mock_scheduler.running = False
        mock_scheduler.start.side_effect = Exception("Start failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Start failed"):
            start()

    @patch('desktop.scheduler.scheduler')
    def test_stop_scheduler(self, mock_scheduler):
        """Test stopping the scheduler."""
        from desktop.scheduler import stop

        # Mock scheduler as running
        mock_scheduler.running = True

        # Stop scheduler
        stop()

        # Verify shutdown was called with wait=True
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @patch('desktop.scheduler.scheduler')
    def test_stop_scheduler_not_running(self, mock_scheduler):
        """Test stopping scheduler when not running."""
        from desktop.scheduler import stop

        # Mock scheduler as not running
        mock_scheduler.running = False

        # Stop scheduler
        stop()

        # Verify shutdown was not called
        mock_scheduler.shutdown.assert_not_called()

    @patch('desktop.scheduler.scheduler')
    def test_stop_scheduler_error_handling(self, mock_scheduler):
        """Test error handling when stopping scheduler."""
        from desktop.scheduler import stop

        # Mock scheduler as running
        mock_scheduler.running = True
        mock_scheduler.shutdown.side_effect = Exception("Shutdown failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Shutdown failed"):
            stop()


class TestJobExecution:
    """Test periodic job execution (mocked)."""

    @patch('desktop.scheduler.cleanup_old_files')
    @patch('desktop.scheduler.cleanup_completed_batches')
    def test_cleanup_functions_are_callable(
        self,
        mock_cleanup_batches,
        mock_cleanup_files
    ):
        """Test that cleanup functions are properly imported and callable."""
        from desktop.scheduler import initialize_scheduler

        # Mock the scheduler to capture job functions
        with patch('desktop.scheduler.scheduler') as mock_scheduler:
            # Reset mock
            mock_scheduler.add_job.reset_mock()

            # Initialize
            initialize_scheduler()

            # Get the functions that were registered
            calls = mock_scheduler.add_job.call_args_list

            # Extract and call the job functions
            cleanup_files_func = calls[0][0][0]
            cleanup_batches_func = calls[1][0][0]

            # Call the functions
            cleanup_files_func()
            cleanup_batches_func()

            # Verify they were called
            mock_cleanup_files.assert_called_once()
            mock_cleanup_batches.assert_called_once()

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.cleanup_old_files')
    @patch('desktop.scheduler.cleanup_completed_batches')
    def test_job_registration_with_correct_intervals(
        self,
        mock_cleanup_batches,
        mock_cleanup_files,
        mock_scheduler
    ):
        """Test that jobs are registered with correct interval parameters."""
        from desktop.scheduler import initialize_scheduler

        # Reset mock
        mock_scheduler.add_job.reset_mock()

        # Initialize
        initialize_scheduler()

        # Verify job intervals
        calls = mock_scheduler.add_job.call_args_list

        # cleanup_old_files should run every 24 hours
        assert calls[0][1]['hours'] == 24

        # cleanup_completed_batches should run every 6 hours
        assert calls[1][1]['hours'] == 6

    @patch('desktop.scheduler.scheduler')
    def test_job_ids_are_unique(self, mock_scheduler):
        """Test that each job has a unique ID."""
        from desktop.scheduler import initialize_scheduler

        # Reset mock
        mock_scheduler.add_job.reset_mock()

        # Initialize
        initialize_scheduler()

        # Get job IDs
        calls = mock_scheduler.add_job.call_args_list
        job_ids = [call[1]['id'] for call in calls]

        # Verify IDs are unique
        assert len(job_ids) == len(set(job_ids))
        assert 'cleanup_old_files' in job_ids
        assert 'cleanup_completed_batches' in job_ids

    @patch('desktop.scheduler.scheduler')
    def test_jobs_configured_with_replace_existing(self, mock_scheduler):
        """Test that jobs are configured with replace_existing=True."""
        from desktop.scheduler import initialize_scheduler

        # Reset mock
        mock_scheduler.add_job.reset_mock()

        # Initialize
        initialize_scheduler()

        # Verify all jobs have replace_existing=True
        calls = mock_scheduler.add_job.call_args_list
        for call in calls:
            assert call[1].get('replace_existing') is True


class TestAutomaticBackups:
    """Test automatic backup scheduling and execution."""

    @patch('desktop.scheduler.export_data')
    @patch('desktop.scheduler.Settings')
    @patch('desktop.scheduler.cleanup_old_backups')
    def test_create_automatic_backup_success(
        self,
        mock_cleanup,
        mock_settings_class,
        mock_export
    ):
        """Test successful automatic backup creation."""
        from desktop.scheduler import create_automatic_backup
        from pathlib import Path

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.database_path': '/path/to/grading.db',
            'data.uploads_path': '/path/to/uploads',
            'app_version': '0.1.0'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings
        mock_settings_class._get_user_data_dir.return_value = Path('/tmp/user_data')

        # Create backup
        create_automatic_backup()

        # Verify export_data was called with correct parameters
        mock_export.assert_called_once()
        args = mock_export.call_args
        assert args[1]['database_path'] == '/path/to/grading.db'
        assert args[1]['uploads_path'] == '/path/to/uploads'
        assert args[1]['app_version'] == '0.1.0'
        assert 'auto-backup-' in args[1]['output_path']
        assert args[1]['output_path'].endswith('.zip')

        # Verify cleanup was called
        mock_cleanup.assert_called_once()

    @patch('desktop.scheduler.export_data')
    @patch('desktop.scheduler.Settings')
    def test_create_automatic_backup_with_defaults(
        self,
        mock_settings_class,
        mock_export
    ):
        """Test backup creation with default paths."""
        from desktop.scheduler import create_automatic_backup
        from pathlib import Path

        # Mock settings with no paths configured
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'app_version': '0.2.0'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings
        mock_settings_class._get_user_data_dir.return_value = Path('/tmp/user_data')

        # Create backup
        create_automatic_backup()

        # Verify defaults were used
        args = mock_export.call_args
        assert '/tmp/user_data/grading.db' in args[1]['database_path']
        assert '/tmp/user_data/uploads' in args[1]['uploads_path']

    @patch('desktop.scheduler.Settings')
    def test_cleanup_old_backups(self, mock_settings_class):
        """Test cleanup of old backup files."""
        from desktop.scheduler import cleanup_old_backups
        from pathlib import Path
        import tempfile
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir) / 'backups'
            backups_dir.mkdir()

            # Mock settings
            mock_settings = MagicMock()
            mock_settings.get.return_value = 30  # 30 days retention
            mock_settings_class.return_value = mock_settings
            mock_settings_class._get_user_data_dir.return_value = Path(tmpdir)

            # Create test backup files
            old_backup = backups_dir / 'auto-backup-20231101-020000.zip'
            recent_backup = backups_dir / 'auto-backup-20251116-020000.zip'

            old_backup.touch()
            recent_backup.touch()

            # Set old file modification time to 40 days ago
            old_time = time.time() - (40 * 24 * 60 * 60)
            os.utime(old_backup, (old_time, old_time))

            # Run cleanup
            cleanup_old_backups()

            # Verify old backup was deleted, recent kept
            assert not old_backup.exists()
            assert recent_backup.exists()

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.Settings')
    def test_schedule_automatic_backup_daily(self, mock_settings_class, mock_scheduler):
        """Test scheduling daily backups."""
        from desktop.scheduler import schedule_automatic_backup

        # Mock settings - backups enabled, daily frequency
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'daily'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings
        mock_settings_class._get_user_data_dir.return_value = Path('/tmp/user_data')

        # Schedule backups
        schedule_automatic_backup()

        # Verify job was added with cron trigger
        mock_scheduler.add_job.assert_called()
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs['id'] == 'automatic_backup'
        assert call_kwargs['hour'] == 2
        assert call_kwargs['minute'] == 0

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.Settings')
    def test_schedule_automatic_backup_weekly(self, mock_settings_class, mock_scheduler):
        """Test scheduling weekly backups."""
        from desktop.scheduler import schedule_automatic_backup

        # Mock settings - backups enabled, weekly frequency
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'weekly'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings
        mock_settings_class._get_user_data_dir.return_value = Path('/tmp/user_data')

        # Schedule backups
        schedule_automatic_backup()

        # Verify job was added with weekly schedule
        mock_scheduler.add_job.assert_called()
        call_kwargs = mock_scheduler.add_job.call_args[1]
        assert call_kwargs['id'] == 'automatic_backup'
        assert call_kwargs['day_of_week'] == 'sun'
        assert call_kwargs['hour'] == 2

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.Settings')
    def test_schedule_automatic_backup_disabled(self, mock_settings_class, mock_scheduler):
        """Test that backups are not scheduled when disabled."""
        from desktop.scheduler import schedule_automatic_backup

        # Mock settings - backups disabled
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': False,
            'data.backup_frequency': 'daily'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings
        mock_settings_class._get_user_data_dir.return_value = Path('/tmp/user_data')

        # Schedule backups
        schedule_automatic_backup()

        # Verify job was NOT added
        mock_scheduler.add_job.assert_not_called()

    @patch('desktop.scheduler.scheduler')
    @patch('desktop.scheduler.Settings')
    def test_schedule_automatic_backup_never(self, mock_settings_class, mock_scheduler):
        """Test that backups are not scheduled when frequency is 'never'."""
        from desktop.scheduler import schedule_automatic_backup

        # Mock settings - frequency set to never
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda key, default=None: {
            'data.backups_enabled': True,
            'data.backup_frequency': 'never'
        }.get(key, default)
        mock_settings_class.return_value = mock_settings
        mock_settings_class._get_user_data_dir.return_value = Path('/tmp/user_data')

        # Schedule backups
        schedule_automatic_backup()

        # Verify job was NOT added
        mock_scheduler.add_job.assert_not_called()


class TestSchedulerIntegration:
    """Integration tests for scheduler module."""

    @patch('desktop.scheduler.BackgroundScheduler')
    @patch('desktop.scheduler.cleanup_old_files')
    @patch('desktop.scheduler.cleanup_completed_batches')
    def test_full_lifecycle(
        self,
        mock_cleanup_batches,
        mock_cleanup_files,
        mock_scheduler_class
    ):
        """Test full scheduler lifecycle: initialize -> start -> stop."""
        # Reset module
        if 'desktop.scheduler' in sys.modules:
            del sys.modules['desktop.scheduler']

        # Mock scheduler instance
        mock_scheduler_instance = MagicMock()
        mock_scheduler_instance.running = False
        mock_scheduler_class.return_value = mock_scheduler_instance

        # Import module (triggers initialization)
        import desktop.scheduler as scheduler_module

        # Verify initialization
        assert mock_scheduler_instance.add_job.call_count == 2

        # Start scheduler
        mock_scheduler_instance.running = False
        scheduler_module.start()
        mock_scheduler_instance.start.assert_called_once()

        # Stop scheduler
        mock_scheduler_instance.running = True
        scheduler_module.stop()
        mock_scheduler_instance.shutdown.assert_called_once_with(wait=True)

    @patch('desktop.scheduler.scheduler')
    def test_module_level_scheduler_access(self, mock_scheduler):
        """Test that scheduler instance is accessible at module level."""
        import desktop.scheduler

        # Verify scheduler is accessible
        assert hasattr(desktop.scheduler, 'scheduler')
        assert desktop.scheduler.scheduler is not None

    @patch('desktop.scheduler.scheduler')
    def test_job_count(self, mock_scheduler):
        """Test that exactly 2 jobs are registered."""
        from desktop.scheduler import initialize_scheduler

        # Reset mock
        mock_scheduler.add_job.reset_mock()

        # Initialize
        initialize_scheduler()

        # Verify exactly 2 jobs were added
        assert mock_scheduler.add_job.call_count == 2
