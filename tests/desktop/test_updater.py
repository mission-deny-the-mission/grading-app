"""Tests for desktop/updater.py - Auto-update mechanism.

This test suite validates the DesktopUpdater class including:
- Update checking and version comparison
- Download with progress tracking
- Backup creation before updates
- Error handling for network failures
- Signature verification (via mocked tufup)

Note: tufup library is mocked to avoid requiring actual installation
and to enable testing without network access.
"""

import logging
import os
import shutil
import sys
from datetime import datetime
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
    """Create temporary user data directory."""
    data_dir = tmp_path / 'GradingApp'
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create sample database and settings files
    (data_dir / 'grading.db').write_text('sample database')
    (data_dir / 'settings.json').write_text('{"theme": "light"}')

    return data_dir


class TestDesktopUpdaterInit:
    """Tests for DesktopUpdater.__init__()."""

    def test_init_with_valid_semver(self, mock_tufup):
        """Test initialization with valid semver version."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        assert updater.app_name == "grading-app"
        assert updater.current_version == "1.0.0"
        assert updater.update_url == "https://github.com/user/repo"
        assert updater.app_dir == Path.cwd()
        assert updater._client is None  # Lazy initialization

    def test_init_with_prerelease_version(self, mock_tufup):
        """Test initialization with pre-release version."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0-beta.1",
            update_url="https://github.com/user/repo"
        )

        assert updater.current_version == "1.0.0-beta.1"

    def test_init_with_invalid_semver_raises_error(self, mock_tufup):
        """Test initialization with invalid semver raises ValueError."""
        from desktop.updater import DesktopUpdater

        with pytest.raises(ValueError, match="Invalid semver format"):
            DesktopUpdater(
                app_name="grading-app",
                current_version="1.0",  # Missing PATCH
                update_url="https://github.com/user/repo"
            )

        with pytest.raises(ValueError, match="Invalid semver format"):
            DesktopUpdater(
                app_name="grading-app",
                current_version="v1.0.0",  # Should not have 'v' prefix
                update_url="https://github.com/user/repo"
            )

    def test_init_logs_initialization(self, mock_tufup, caplog):
        """Test initialization logs configuration."""
        from desktop.updater import DesktopUpdater

        with caplog.at_level(logging.INFO):
            DesktopUpdater(
                app_name="grading-app",
                current_version="1.0.0",
                update_url="https://github.com/user/repo"
            )

        assert "Updater initialized" in caplog.text
        assert "app=grading-app" in caplog.text
        assert "version=1.0.0" in caplog.text


class TestDesktopUpdaterClient:
    """Tests for DesktopUpdater.client property (lazy initialization)."""

    def test_client_lazy_initialization(self, mock_tufup):
        """Test client is lazily initialized on first access."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Client not initialized yet
        assert updater._client is None

        # Access client property
        client = updater.client

        # Now it's initialized
        assert client is not None
        mock_tufup.assert_called_once()

    def test_client_initialization_parameters(self, mock_tufup):
        """Test client is initialized with correct parameters."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Access client to trigger initialization
        _ = updater.client

        mock_tufup.assert_called_once_with(
            app_name="grading-app",
            app_install_dir=str(Path.cwd()),
            current_version="1.0.0",
            metadata_base_url="https://github.com/user/repo",
            target_base_url="https://github.com/user/repo",
        )

    def test_client_raises_error_if_tufup_not_installed(self):
        """Test client raises RuntimeError if tufup not installed."""
        # Temporarily remove tufup from sys.modules
        with patch.dict('sys.modules', {'tufup': None, 'tufup.client': None}):
            from desktop.updater import DesktopUpdater

            updater = DesktopUpdater(
                app_name="grading-app",
                current_version="1.0.0",
                update_url="https://github.com/user/repo"
            )

            with pytest.raises(RuntimeError, match="tufup library not found"):
                _ = updater.client


class TestCheckForUpdates:
    """Tests for DesktopUpdater.check_for_updates()."""

    def test_check_for_updates_when_available(self, mock_tufup):
        """Test check_for_updates returns update info when available."""
        from desktop.updater import DesktopUpdater

        # Mock client methods
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        result = updater.check_for_updates()

        assert result['available'] is True
        assert result['version'] == "1.1.0"
        assert result['current'] == "1.0.0"
        assert result['url'] == "https://github.com/user/repo/releases/tag/1.1.0"
        assert 'error' not in result

        # Verify client methods were called
        mock_client_instance.refresh.assert_called_once()
        mock_client_instance.get_latest_version.assert_called_once()

    def test_check_for_updates_when_not_available(self, mock_tufup):
        """Test check_for_updates when no update available."""
        from desktop.updater import DesktopUpdater

        # Mock client - same version
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.0.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        result = updater.check_for_updates()

        assert result['available'] is False
        assert result['current'] == "1.0.0"
        assert 'version' not in result
        assert 'error' not in result

    def test_check_for_updates_handles_network_error(self, mock_tufup, caplog):
        """Test check_for_updates handles network errors gracefully."""
        from desktop.updater import DesktopUpdater

        # Mock client to raise exception
        mock_client_instance = MagicMock()
        mock_client_instance.refresh.side_effect = ConnectionError("Network timeout")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with caplog.at_level(logging.ERROR):
            result = updater.check_for_updates()

        assert result['available'] is False
        assert result['current'] == "1.0.0"
        assert 'error' in result
        assert "Network timeout" in result['error']
        assert "Update check failed" in caplog.text

    def test_check_for_updates_handles_signature_verification_error(self, mock_tufup):
        """Test check_for_updates handles signature verification errors."""
        from desktop.updater import DesktopUpdater

        # Mock client to raise signature error
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.side_effect = ValueError("Invalid signature")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        result = updater.check_for_updates()

        assert result['available'] is False
        assert 'error' in result
        assert "Invalid signature" in result['error']

    def test_check_for_updates_logs_result(self, mock_tufup, caplog):
        """Test check_for_updates logs appropriate messages."""
        from desktop.updater import DesktopUpdater

        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with caplog.at_level(logging.INFO):
            updater.check_for_updates()

        assert "Checking for updates" in caplog.text
        assert "Update available: 1.1.0" in caplog.text


class TestDownloadUpdate:
    """Tests for DesktopUpdater.download_update()."""

    def test_download_update_success(self, mock_tufup):
        """Test download_update successfully downloads and verifies update."""
        from desktop.updater import DesktopUpdater

        mock_client_instance = MagicMock()
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        result = updater.download_update()

        assert result is True
        mock_client_instance.download_and_apply_update.assert_called_once()

    def test_download_update_with_progress_callback(self, mock_tufup):
        """Test download_update calls progress callback."""
        from desktop.updater import DesktopUpdater

        mock_client_instance = MagicMock()
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Create progress callback
        progress_callback = Mock()

        result = updater.download_update(progress_callback=progress_callback)

        assert result is True
        mock_client_instance.download_and_apply_update.assert_called_once_with(
            progress_hook=progress_callback
        )

    def test_download_update_handles_network_error(self, mock_tufup, caplog):
        """Test download_update handles network errors."""
        from desktop.updater import DesktopUpdater

        mock_client_instance = MagicMock()
        mock_client_instance.download_and_apply_update.side_effect = ConnectionError("Download failed")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with caplog.at_level(logging.ERROR):
            result = updater.download_update()

        assert result is False
        assert "Update download failed" in caplog.text

    def test_download_update_handles_verification_error(self, mock_tufup):
        """Test download_update fails on signature verification error."""
        from desktop.updater import DesktopUpdater

        mock_client_instance = MagicMock()
        mock_client_instance.download_and_apply_update.side_effect = ValueError("Signature mismatch")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        result = updater.download_update()

        assert result is False

    def test_download_update_logs_progress(self, mock_tufup, caplog):
        """Test download_update logs download progress."""
        from desktop.updater import DesktopUpdater

        mock_client_instance = MagicMock()
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with caplog.at_level(logging.INFO):
            updater.download_update()

        assert "Starting update download" in caplog.text
        assert "Update downloaded and verified successfully" in caplog.text


class TestBackupBeforeUpdate:
    """Tests for DesktopUpdater.backup_before_update()."""

    def test_backup_creates_timestamped_directory(self, mock_tufup, temp_user_data_dir):
        """Test backup creates timestamped directory."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            backup_dir = updater.backup_before_update()

        assert backup_dir.exists()
        assert backup_dir.parent == temp_user_data_dir / 'backups'
        # Check timestamp format: YYYYMMDD_HHMMSS
        assert len(backup_dir.name) == 15
        assert backup_dir.name[8] == '_'

    def test_backup_copies_database(self, mock_tufup, temp_user_data_dir):
        """Test backup copies database file."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            backup_dir = updater.backup_before_update()

        backup_db = backup_dir / 'grading.db'
        assert backup_db.exists()
        assert backup_db.read_text() == 'sample database'

    def test_backup_copies_settings(self, mock_tufup, temp_user_data_dir):
        """Test backup copies settings file."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            backup_dir = updater.backup_before_update()

        backup_settings = backup_dir / 'settings.json'
        assert backup_settings.exists()
        assert backup_settings.read_text() == '{"theme": "light"}'

    def test_backup_handles_missing_database(self, mock_tufup, temp_user_data_dir):
        """Test backup succeeds even if database doesn't exist."""
        from desktop.updater import DesktopUpdater

        # Remove database
        (temp_user_data_dir / 'grading.db').unlink()

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            backup_dir = updater.backup_before_update()

        # Backup succeeds but no database file
        assert backup_dir.exists()
        assert not (backup_dir / 'grading.db').exists()
        # Settings should still be backed up
        assert (backup_dir / 'settings.json').exists()

    def test_backup_handles_missing_settings(self, mock_tufup, temp_user_data_dir):
        """Test backup succeeds even if settings don't exist."""
        from desktop.updater import DesktopUpdater

        # Remove settings
        (temp_user_data_dir / 'settings.json').unlink()

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            backup_dir = updater.backup_before_update()

        # Backup succeeds but no settings file
        assert backup_dir.exists()
        assert (backup_dir / 'grading.db').exists()
        assert not (backup_dir / 'settings.json').exists()

    def test_backup_raises_error_on_permission_denied(self, mock_tufup, temp_user_data_dir):
        """Test backup raises OSError on permission error."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Mock shutil.copy2 to raise permission error
        with patch('shutil.copy2', side_effect=PermissionError("Access denied")):
            with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
                with pytest.raises(OSError, match="Failed to create backup"):
                    updater.backup_before_update()

    def test_backup_logs_creation(self, mock_tufup, temp_user_data_dir, caplog):
        """Test backup logs creation process."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with caplog.at_level(logging.INFO):
            with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
                updater.backup_before_update()

        assert "Creating backup at" in caplog.text
        assert "Backup created successfully" in caplog.text


class TestApplyUpdate:
    """Tests for DesktopUpdater.apply_update()."""

    def test_apply_update_creates_backup(self, mock_tufup, temp_user_data_dir):
        """Test apply_update creates backup before applying."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl'):  # Prevent actual restart
                updater.apply_update()

        # Check backup was created
        backups = list((temp_user_data_dir / 'backups').iterdir())
        assert len(backups) == 1
        assert (backups[0] / 'grading.db').exists()

    def test_apply_update_restarts_application(self, mock_tufup, temp_user_data_dir):
        """Test apply_update calls os.execl to restart application."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl') as mock_execl:
                updater.apply_update()

                # Verify os.execl was called with correct arguments
                mock_execl.assert_called_once_with(
                    sys.executable,
                    sys.executable,
                    *sys.argv
                )

    def test_apply_update_raises_error_on_backup_failure(self, mock_tufup, temp_user_data_dir):
        """Test apply_update raises error if backup fails."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, 'backup_before_update', side_effect=OSError("Backup failed")):
            with pytest.raises(RuntimeError, match="Failed to apply update"):
                updater.apply_update()

    def test_apply_update_raises_error_on_restart_failure(self, mock_tufup, temp_user_data_dir):
        """Test apply_update raises error if restart fails."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl', side_effect=OSError("Exec failed")):
                with pytest.raises(RuntimeError, match="Failed to apply update"):
                    updater.apply_update()

    def test_apply_update_logs_process(self, mock_tufup, temp_user_data_dir, caplog):
        """Test apply_update logs the update process."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with caplog.at_level(logging.INFO):
            with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
                with patch('os.execl'):
                    updater.apply_update()

        assert "Applying update" in caplog.text
        assert "Backup created at" in caplog.text
        assert "Restarting application" in caplog.text


class TestGetUserDataDir:
    """Tests for DesktopUpdater._get_user_data_dir()."""

    def test_user_data_dir_on_windows(self, mock_tufup, tmp_path):
        """Test user data directory path on Windows."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch('sys.platform', 'win32'):
            with patch.dict('os.environ', {'APPDATA': str(tmp_path)}):
                data_dir = updater._get_user_data_dir()

        assert data_dir == tmp_path / 'GradingApp'
        assert data_dir.exists()

    def test_user_data_dir_on_macos(self, mock_tufup, tmp_path):
        """Test user data directory path on macOS."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        with patch('sys.platform', 'darwin'):
            with patch('pathlib.Path.home', return_value=tmp_path):
                data_dir = updater._get_user_data_dir()

        assert data_dir == tmp_path / 'Library' / 'Application Support' / 'GradingApp'
        assert data_dir.exists()

    def test_user_data_dir_on_linux(self, mock_tufup, tmp_path):
        """Test user data directory path on Linux."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Mock all the necessary paths for Linux
        with patch('sys.platform', 'linux'):
            # Remove XDG_DATA_HOME from environment so it uses default
            env_without_xdg = {k: v for k, v in os.environ.items() if k != 'XDG_DATA_HOME'}
            with patch.dict('os.environ', env_without_xdg, clear=True):
                with patch('pathlib.Path.home', return_value=tmp_path):
                    data_dir = updater._get_user_data_dir()

        assert data_dir == tmp_path / '.local' / 'share' / 'GradingApp'
        assert data_dir.exists()

    def test_user_data_dir_with_xdg_data_home(self, mock_tufup, tmp_path):
        """Test user data directory respects XDG_DATA_HOME on Linux."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        xdg_dir = tmp_path / 'custom_xdg'

        with patch('sys.platform', 'linux'):
            with patch.dict('os.environ', {'XDG_DATA_HOME': str(xdg_dir)}):
                data_dir = updater._get_user_data_dir()

        assert data_dir == xdg_dir / 'GradingApp'
        assert data_dir.exists()


class TestIsValidSemver:
    """Tests for DesktopUpdater._is_valid_semver()."""

    def test_valid_semver_basic(self, mock_tufup):
        """Test validation of basic semver versions."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        assert updater._is_valid_semver("1.0.0") is True
        assert updater._is_valid_semver("0.0.1") is True
        assert updater._is_valid_semver("10.20.30") is True

    def test_valid_semver_with_prerelease(self, mock_tufup):
        """Test validation of semver with pre-release."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        assert updater._is_valid_semver("1.0.0-alpha") is True
        assert updater._is_valid_semver("1.0.0-beta.1") is True
        assert updater._is_valid_semver("1.0.0-rc.1") is True

    def test_valid_semver_with_build_metadata(self, mock_tufup):
        """Test validation of semver with build metadata."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        assert updater._is_valid_semver("1.0.0+build.123") is True
        assert updater._is_valid_semver("1.0.0-beta+exp.sha.5114f85") is True

    def test_invalid_semver_formats(self, mock_tufup):
        """Test validation rejects invalid semver formats."""
        from desktop.updater import DesktopUpdater

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        assert updater._is_valid_semver("1.0") is False  # Missing PATCH
        assert updater._is_valid_semver("1") is False  # Missing MINOR and PATCH
        assert updater._is_valid_semver("v1.0.0") is False  # 'v' prefix not allowed
        assert updater._is_valid_semver("1.0.0.0") is False  # Too many parts
        assert updater._is_valid_semver("") is False  # Empty string
        assert updater._is_valid_semver("latest") is False  # Not a version


class TestUpdateWorkflow:
    """Integration tests for complete update workflow."""

    def test_full_update_workflow(self, mock_tufup, temp_user_data_dir):
        """Test complete update workflow: check → download → apply."""
        from desktop.updater import DesktopUpdater

        # Mock client with update available
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Step 1: Check for updates
        update_info = updater.check_for_updates()
        assert update_info['available'] is True
        assert update_info['version'] == "1.1.0"

        # Step 2: Download update
        download_success = updater.download_update()
        assert download_success is True

        # Step 3: Apply update (mock restart)
        with patch.object(updater, '_get_user_data_dir', return_value=temp_user_data_dir):
            with patch('os.execl') as mock_execl:
                updater.apply_update()

                # Verify backup was created
                backups = list((temp_user_data_dir / 'backups').iterdir())
                assert len(backups) == 1

                # Verify restart was triggered
                mock_execl.assert_called_once()

    def test_workflow_handles_no_update_available(self, mock_tufup):
        """Test workflow when no update is available."""
        from desktop.updater import DesktopUpdater

        # Mock client with same version
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.0.0"
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        update_info = updater.check_for_updates()
        assert update_info['available'] is False

    def test_workflow_handles_download_failure(self, mock_tufup):
        """Test workflow handles download failure gracefully."""
        from desktop.updater import DesktopUpdater

        # Mock client with download failure
        mock_client_instance = MagicMock()
        mock_client_instance.get_latest_version.return_value = "1.1.0"
        mock_client_instance.download_and_apply_update.side_effect = ConnectionError("Download failed")
        mock_tufup.return_value = mock_client_instance

        updater = DesktopUpdater(
            app_name="grading-app",
            current_version="1.0.0",
            update_url="https://github.com/user/repo"
        )

        # Check shows update available
        update_info = updater.check_for_updates()
        assert update_info['available'] is True

        # Download fails
        download_success = updater.download_update()
        assert download_success is False
