"""
Integration tests for update workflow.

Tests cover:
- T050: Full update workflow (check → download → apply → verify new version)
- T051: Update with data preservation (verify database/settings preserved after update)
- Complete end-to-end update scenarios
- Data integrity across updates
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# Mock tufup before importing updater
@pytest.fixture(autouse=True)
def mock_tufup():
    """Mock tufup library for all tests."""
    mock_tufup = MagicMock()
    mock_client_class = MagicMock()
    mock_tufup.client.Client = mock_client_class

    with patch.dict('sys.modules', {'tufup': mock_tufup, 'tufup.client': mock_tufup.client}):
        yield mock_client_class


@pytest.fixture
def temp_user_data_dir(tmp_path):
    """Create temporary user data directory with sample data."""
    data_dir = tmp_path / 'GradingApp'
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create sample database with realistic content
    (data_dir / 'grading.db').write_text('SQLite database with assignments and grades')

    # Create sample settings with realistic structure
    settings_content = '''{
        "version": "1.0.0",
        "ui": {
            "theme": "dark",
            "language": "en"
        },
        "api": {
            "provider": "anthropic"
        }
    }'''
    (data_dir / 'settings.json').write_text(settings_content)

    # Create uploads directory with a sample file
    uploads_dir = data_dir / 'uploads'
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / 'sample_submission.pdf').write_text('Sample PDF content')

    return data_dir


class TestFullUpdateWorkflow:
    """Test T050: Complete update workflow from check to apply."""

    def test_full_update_workflow_success(self, mock_tufup, temp_user_data_dir):
        """Test complete update workflow: check → download → apply → verify.

        This test verifies the entire update process including:
        1. Checking for updates and finding new version
        2. Downloading the update with progress tracking
        3. Creating backup before applying
        4. Applying update and triggering restart
        5. Verifying all steps completed successfully
        """
        from desktop.updater import DesktopUpdater

        # Mock client with update available
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.2.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Step 1: Check for updates
        update_info = updater.check_for_updates()
        assert update_info['available'] is True
        assert update_info['version'] == "1.2.0"
        assert update_info['current'] == "1.0.0"
        assert update_info['url'] == "https://github.com/user/grading-app/releases/tag/1.2.0"

        # Verify metadata was refreshed
        mock_client_instance.refresh.assert_called_once()
        mock_client_instance.get_latest_version.assert_called_once()

        # Step 2: Download update with progress tracking
        progress_calls = []

        def on_progress(downloaded, total):
            progress_calls.append((downloaded, total))

        download_success = updater.download_update(progress_callback=on_progress)
        assert download_success is True

        # Verify download method was called with progress callback
        mock_client_instance.download_and_apply_update.assert_called_once_with(
            progress_hook=on_progress
        )

        # Step 3: Apply update (creates backup and restarts)
        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl') as mock_execl:
                updater.apply_update()

                # Verify backup was created
                backups_dir = temp_user_data_dir / 'backups'
                assert backups_dir.exists()
                backups = list(backups_dir.iterdir())
                assert len(backups) == 1

                # Verify backup contains data
                backup_dir = backups[0]
                assert (backup_dir / 'grading.db').exists()
                assert (backup_dir / 'settings.json').exists()

                # Verify restart was triggered
                mock_execl.assert_called_once_with(
                    sys.executable,
                    sys.executable,
                    *sys.argv
                )

    def test_workflow_with_progress_tracking(self, mock_tufup, temp_user_data_dir):
        """Test update workflow with detailed progress tracking."""
        from desktop.updater import DesktopUpdater

        # Mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "2.0.0"

        # Simulate progress updates during download
        def simulate_download(progress_hook=None):
            if progress_hook:
                # Simulate download progress: 0%, 50%, 100%
                progress_hook(0, 1024 * 1024 * 10)  # 0 of 10 MB
                progress_hook(1024 * 1024 * 5, 1024 * 1024 * 10)  # 5 of 10 MB
                progress_hook(1024 * 1024 * 10, 1024 * 1024 * 10)  # 10 of 10 MB

        mock_client_instance.download_and_apply_update.side_effect = simulate_download
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.5.0",
            update_url="https://github.com/user/grading-app"
        )

        # Track progress
        progress_updates = []

        def track_progress(downloaded, total):
            percent = (downloaded / total) * 100
            progress_updates.append({
                'downloaded': downloaded,
                'total': total,
                'percent': percent
            })

        # Check and download update
        update_info = updater.check_for_updates()
        assert update_info['available'] is True

        download_success = updater.download_update(progress_callback=track_progress)
        assert download_success is True

        # Verify progress was tracked
        assert len(progress_updates) == 3
        assert progress_updates[0]['percent'] == 0.0
        assert progress_updates[1]['percent'] == 50.0
        assert progress_updates[2]['percent'] == 100.0

    def test_workflow_handles_no_update_available(self, mock_tufup):
        """Test workflow gracefully handles when no update is available."""
        from desktop.updater import DesktopUpdater

        # Mock client - same version
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.0.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Check for updates
        update_info = updater.check_for_updates()
        assert update_info['available'] is False
        assert update_info['current'] == "1.0.0"
        assert 'version' not in update_info
        assert 'url' not in update_info

    def test_workflow_handles_check_failure(self, mock_tufup):
        """Test workflow handles update check failures gracefully."""
        from desktop.updater import DesktopUpdater

        # Mock client to raise network error
        mock_client_instance = MagicMock()
        mock_client_instance.refresh.side_effect = ConnectionError("Network unavailable")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Check for updates
        update_info = updater.check_for_updates()
        assert update_info['available'] is False
        assert 'error' in update_info
        assert "Network unavailable" in update_info['error']

    def test_workflow_handles_download_failure(self, mock_tufup):
        """Test workflow handles download failures gracefully."""
        from desktop.updater import DesktopUpdater

        # Mock client with update available but download fails
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_client_instance.download_and_apply_update.side_effect = ConnectionError("Download interrupted")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Check shows update available
        update_info = updater.check_for_updates()
        assert update_info['available'] is True

        # Download fails
        download_success = updater.download_update()
        assert download_success is False

    def test_workflow_handles_verification_failure(self, mock_tufup):
        """Test workflow handles signature verification failures."""
        from desktop.updater import DesktopUpdater

        # Mock client with verification failure
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_client_instance.download_and_apply_update.side_effect = ValueError("Invalid signature")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Update check succeeds
        update_info = updater.check_for_updates()
        assert update_info['available'] is True

        # Download fails due to verification
        download_success = updater.download_update()
        assert download_success is False


class TestUpdateWithDataPreservation:
    """Test T051: Update with data preservation across versions."""

    def test_database_preserved_after_update(self, mock_tufup, temp_user_data_dir):
        """Test that database is preserved after update.

        Verifies that:
        1. Original database content is backed up
        2. Database file persists after update
        3. Database content remains intact
        """
        from desktop.updater import DesktopUpdater

        # Mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Get original database content
        db_path = temp_user_data_dir / 'grading.db'
        original_db_content = db_path.read_text()

        # Download and apply update
        updater.download_update()

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):  # Prevent actual restart
                updater.apply_update()

        # Verify database still exists
        assert db_path.exists()

        # Verify database content is unchanged
        assert db_path.read_text() == original_db_content

        # Verify backup was created
        backups = list((temp_user_data_dir / 'backups').iterdir())
        assert len(backups) == 1
        backup_db = backups[0] / 'grading.db'
        assert backup_db.exists()
        assert backup_db.read_text() == original_db_content

    def test_settings_preserved_after_update(self, mock_tufup, temp_user_data_dir):
        """Test that settings are preserved after update.

        Verifies that:
        1. Original settings are backed up
        2. Settings file persists after update
        3. User preferences remain intact
        """
        from desktop.updater import DesktopUpdater

        # Mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Get original settings content
        settings_path = temp_user_data_dir / 'settings.json'
        original_settings = settings_path.read_text()

        # Download and apply update
        updater.download_update()

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):
                updater.apply_update()

        # Verify settings still exist
        assert settings_path.exists()

        # Verify settings content is unchanged
        assert settings_path.read_text() == original_settings

        # Verify backup was created
        backups = list((temp_user_data_dir / 'backups').iterdir())
        assert len(backups) == 1
        backup_settings = backups[0] / 'settings.json'
        assert backup_settings.exists()
        assert backup_settings.read_text() == original_settings

    def test_uploads_directory_preserved(self, mock_tufup, temp_user_data_dir):
        """Test that uploads directory is preserved after update.

        Verifies that:
        1. User uploaded files persist
        2. Directory structure remains intact
        """
        from desktop.updater import DesktopUpdater

        # Mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Verify uploads exist before update
        uploads_dir = temp_user_data_dir / 'uploads'
        sample_file = uploads_dir / 'sample_submission.pdf'
        assert uploads_dir.exists()
        assert sample_file.exists()
        original_content = sample_file.read_text()

        # Download and apply update
        updater.download_update()

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):
                updater.apply_update()

        # Verify uploads directory still exists
        assert uploads_dir.exists()
        assert sample_file.exists()
        assert sample_file.read_text() == original_content

    def test_multiple_backups_created(self, mock_tufup, temp_user_data_dir):
        """Test that multiple updates create separate backups."""
        from desktop.updater import DesktopUpdater
        import time

        # Mock client
        mock_client_instance = MagicMock()
        mock_tufup.return_value = mock_client_instance

        # First update
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):
                updater.download_update()
                updater.apply_update()

        # Wait to ensure different timestamp (need at least 1 second for YYYYMMDD_HHMMSS format)
        time.sleep(1.1)

        # Second update
        mock_client_instance.get_latest_version.return_value = "1.2.0"
        updater2 = DesktopUpdater(
            app_name="grading-app",
            current_version="1.1.0",
            update_url="https://github.com/user/grading-app"
        )

        with patch.object(updater2, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):
                updater2.download_update()
                updater2.apply_update()

        # Verify two separate backups exist
        backups = list((temp_user_data_dir / 'backups').iterdir())
        assert len(backups) == 2, f"Expected 2 backups but found {len(backups)}: {[b.name for b in backups]}"

        # Verify both backups have different timestamps
        backup_names = sorted([b.name for b in backups])
        assert backup_names[0] != backup_names[1], f"Backup timestamps should differ: {backup_names[0]} vs {backup_names[1]}"

    def test_backup_failure_prevents_update(self, mock_tufup, temp_user_data_dir):
        """Test that backup failure prevents update from being applied.

        Ensures data safety by requiring successful backup before update.
        """
        from desktop.updater import DesktopUpdater

        # Mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Download update
        updater.download_update()

        # Mock backup failure
        with patch.object(updater, 'backup_before_update', side_effect=OSError("Disk full")):
            with pytest.raises(RuntimeError, match="Failed to apply update"):
                updater.apply_update()

    def test_data_integrity_across_version_increment(self, mock_tufup, temp_user_data_dir):
        """Test complete data integrity through version increment.

        This test verifies the complete update flow:
        1. Start with version 1.0.0 with data
        2. Update to 1.1.0
        3. Verify all data preserved
        4. Verify version incremented
        """
        from desktop.updater import DesktopUpdater

        # Mock client
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        # Initial state: version 1.0.0
        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/grading-app"
        )

        # Capture original data
        db_content = (temp_user_data_dir / 'grading.db').read_text()
        settings_content = (temp_user_data_dir / 'settings.json').read_text()
        uploads_content = (temp_user_data_dir / 'uploads' / 'sample_submission.pdf').read_text()

        # Perform update
        update_info = updater.check_for_updates()
        assert update_info['available'] is True
        assert update_info['version'] == "1.1.0"

        updater.download_update()

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):
                updater.apply_update()

        # Verify all data preserved
        assert (temp_user_data_dir / 'grading.db').read_text() == db_content
        assert (temp_user_data_dir / 'settings.json').read_text() == settings_content
        assert (temp_user_data_dir / 'uploads' / 'sample_submission.pdf').read_text() == uploads_content

        # Verify backup created with all data
        backups = list((temp_user_data_dir / 'backups').iterdir())
        assert len(backups) == 1
        backup_dir = backups[0]
        assert (backup_dir / 'grading.db').read_text() == db_content
        assert (backup_dir / 'settings.json').read_text() == settings_content
