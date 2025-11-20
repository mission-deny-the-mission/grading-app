"""
Unit tests for application settings management.

Tests cover:
- Loading settings from existing file
- Creating default settings when file missing
- Saving settings atomically
- get/set operations
- Schema validation
- Backup creation
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Provide a temporary directory for settings files."""
    settings_dir = tmp_path / "test_settings"
    settings_dir.mkdir()
    return settings_dir


@pytest.fixture
def settings_path(temp_settings_dir):
    """Provide a path to a settings file."""
    return temp_settings_dir / "settings.json"


@pytest.fixture
def settings(settings_path):
    """Provide a Settings instance."""
    from desktop.settings import Settings
    return Settings(settings_path)


class TestSettingsInitialization:
    """Test settings initialization and loading."""

    def test_init_creates_settings_object(self, settings_path):
        """Test that Settings object can be initialized."""
        from desktop.settings import Settings
        s = Settings(settings_path)
        assert s.settings_path == settings_path
        assert s._settings == {}

    def test_load_creates_default_settings_when_file_missing(self, settings, settings_path):
        """Test that load() creates default settings when file doesn't exist."""
        from desktop.settings import Settings
        settings.load()

        # File should now exist
        assert settings_path.exists()

        # Should have default structure
        assert settings.get('version') == Settings.SETTINGS_VERSION
        assert settings.get('ui.theme') == 'system'
        assert settings.get('ui.start_minimized') is False
        assert settings.get('updates.auto_check') is True
        assert settings.get('data.backups_enabled') is True

    def test_load_sets_platform_specific_paths(self, settings):
        """Test that load() sets appropriate platform-specific default paths."""
        settings.load()

        db_path = settings.get('data.database_path')
        uploads_path = settings.get('data.uploads_path')

        assert db_path is not None
        assert uploads_path is not None
        assert 'GradingApp' in db_path
        assert 'grading.db' in db_path
        assert 'uploads' in uploads_path

    def test_load_reads_existing_valid_file(self, settings, settings_path):
        """Test that load() correctly reads an existing valid settings file."""
        # Create a valid settings file
        test_settings = {
            "version": "1.0.0",
            "app_version": "0.1.0",
            "last_updated": "2025-11-16T10:00:00Z",
            "ui": {
                "theme": "dark",
                "start_minimized": True,
                "show_in_system_tray": False,
                "window_geometry": {
                    "width": 1920,
                    "height": 1080,
                    "x": 0,
                    "y": 0,
                    "maximized": True
                }
            },
            "updates": {
                "auto_check": False,
                "check_frequency": "weekly",
                "auto_download": False,
                "last_check": "2025-11-15T08:00:00Z",
                "deferred_version": "1.1.0"
            },
            "data": {
                "database_path": "/custom/path/grading.db",
                "uploads_path": "/custom/path/uploads",
                "backups_enabled": False,
                "backup_frequency": "weekly",
                "backup_retention_days": 60
            },
            "advanced": {
                "flask_port": 5000,
                "log_level": "DEBUG",
                "enable_telemetry": True
            }
        }

        with open(settings_path, 'w') as f:
            json.dump(test_settings, f)

        # Load settings
        settings.load()

        # Verify values were loaded
        assert settings.get('ui.theme') == 'dark'
        assert settings.get('ui.start_minimized') is True
        assert settings.get('ui.window_geometry.width') == 1920
        assert settings.get('updates.check_frequency') == 'weekly'
        assert settings.get('data.database_path') == '/custom/path/grading.db'
        assert settings.get('advanced.flask_port') == 5000

    def test_load_raises_error_on_invalid_json(self, settings, settings_path):
        """Test that load() raises ValueError on invalid JSON."""
        # Create invalid JSON file
        with open(settings_path, 'w') as f:
            f.write("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid JSON"):
            settings.load()

    def test_load_merges_with_defaults(self, settings, settings_path):
        """Test that load() merges loaded settings with defaults for missing keys."""
        # Create settings file missing some keys
        minimal_settings = {
            "version": "1.0.0",
            "app_version": "0.1.0",
            "ui": {
                "theme": "dark"
            }
        }

        with open(settings_path, 'w') as f:
            json.dump(minimal_settings, f)

        settings.load()

        # Should have loaded value
        assert settings.get('ui.theme') == 'dark'

        # Should have default values for missing keys
        assert settings.get('ui.start_minimized') is False
        assert settings.get('updates.auto_check') is True
        assert settings.get('data.backups_enabled') is True


class TestSettingsSaving:
    """Test settings saving functionality."""

    def test_save_creates_file_atomically(self, settings, settings_path):
        """Test that save() creates the settings file."""
        settings.load()
        settings.set('ui.theme', 'dark')
        settings.save()

        assert settings_path.exists()

        # Verify file contents
        with open(settings_path, 'r') as f:
            saved_settings = json.load(f)

        assert saved_settings['ui']['theme'] == 'dark'

    def test_save_creates_backup(self, settings, settings_path):
        """Test that save() creates a backup of existing settings."""
        # Create initial settings
        settings.load()
        settings.save()

        # Modify and save again
        settings.set('ui.theme', 'dark')
        settings.save()

        # Backup should exist
        backup_path = settings_path.with_suffix('.json.bak')
        assert backup_path.exists()

        # Backup should contain original settings
        with open(backup_path, 'r') as f:
            backup_settings = json.load(f)

        assert backup_settings['ui']['theme'] == 'system'  # Original default value

    def test_save_updates_last_updated_timestamp(self, settings):
        """Test that save() updates the last_updated timestamp."""
        settings.load()

        # Save
        before = datetime.utcnow()
        settings.save()
        after = datetime.utcnow()

        last_updated = settings.get('last_updated')
        assert last_updated is not None

        # Parse timestamp and verify it's between before and after
        timestamp = datetime.fromisoformat(last_updated.rstrip('Z'))
        assert before <= timestamp <= after

    def test_save_is_atomic(self, settings, settings_path):
        """Test that save() is atomic (uses temp file then rename)."""
        settings.load()
        settings.set('ui.theme', 'dark')

        # Patch os.replace to verify it's called
        original_replace = Path.replace

        replace_called = []

        def mock_replace(self, target):
            replace_called.append((str(self), str(target)))
            return original_replace(self, target)

        with patch.object(Path, 'replace', mock_replace):
            settings.save()

        # Verify replace was called with temp file
        assert len(replace_called) == 1
        temp_file, target_file = replace_called[0]
        assert temp_file.endswith('.json.tmp')
        assert target_file == str(settings_path)

    def test_save_cleans_up_temp_file_on_error(self, settings, settings_path):
        """Test that save() cleans up temp file if an error occurs."""
        settings.load()

        # Create a scenario where fsync fails
        with patch('os.fsync', side_effect=OSError("Mock error")):
            with pytest.raises(OSError):
                settings.save()

        # Temp file should be cleaned up
        temp_path = settings_path.with_suffix('.json.tmp')
        assert not temp_path.exists()

    def test_save_creates_directory_if_missing(self, temp_settings_dir):
        """Test that save() creates parent directory if it doesn't exist."""
        nested_path = temp_settings_dir / "nested" / "dir" / "settings.json"
        from desktop.settings import Settings
        settings = Settings(nested_path)
        settings.load()
        settings.save()

        assert nested_path.exists()
        assert nested_path.parent.exists()


class TestGetSet:
    """Test get() and set() operations."""

    def test_get_simple_value(self, settings):
        """Test get() with a simple top-level key."""
        from desktop.settings import Settings
        settings.load()
        assert settings.get('version') == Settings.SETTINGS_VERSION

    def test_get_nested_value(self, settings):
        """Test get() with nested keys using dot notation."""
        settings.load()
        assert settings.get('ui.theme') == 'system'
        assert settings.get('ui.window_geometry.width') == 1280

    def test_get_missing_key_returns_default(self, settings):
        """Test get() returns default value for missing keys."""
        settings.load()
        assert settings.get('nonexistent.key') is None
        assert settings.get('nonexistent.key', 'default') == 'default'

    def test_get_nested_missing_key_returns_default(self, settings):
        """Test get() returns default for missing nested keys."""
        settings.load()
        assert settings.get('ui.nonexistent') is None
        assert settings.get('ui.nested.nonexistent', 42) == 42

    def test_set_simple_value(self, settings):
        """Test set() with a simple top-level key."""
        settings.load()
        settings.set('app_version', '0.2.0')
        assert settings.get('app_version') == '0.2.0'

    def test_set_nested_value(self, settings):
        """Test set() with nested keys using dot notation."""
        settings.load()
        settings.set('ui.theme', 'dark')
        assert settings.get('ui.theme') == 'dark'

        settings.set('ui.window_geometry.width', 1920)
        assert settings.get('ui.window_geometry.width') == 1920

    def test_set_creates_nested_structure(self, settings):
        """Test set() creates nested structure for new keys."""
        settings.load()
        settings.set('new.nested.key', 'value')
        assert settings.get('new.nested.key') == 'value'

    def test_set_and_save_persists_changes(self, settings, settings_path):
        """Test that set() + save() persists changes to disk."""
        settings.load()
        settings.set('ui.theme', 'dark')
        settings.save()

        # Load fresh instance
        from desktop.settings import Settings
        new_settings = Settings(settings_path)
        new_settings.load()
        assert new_settings.get('ui.theme') == 'dark'


class TestValidation:
    """Test settings validation."""

    def test_validate_passes_for_default_settings(self, settings):
        """Test that validate() passes for default settings."""
        settings.load()
        settings.validate()  # Should not raise

    def test_validate_requires_version(self, settings):
        """Test that validate() requires version field."""
        settings._settings = {}
        with pytest.raises(ValueError, match="Missing required field: version"):
            settings.validate()

    def test_validate_theme_values(self, settings):
        """Test that validate() enforces valid theme values."""
        settings.load()

        # Valid themes
        for theme in ['light', 'dark', 'system']:
            settings.set('ui.theme', theme)
            settings.validate()  # Should not raise

        # Invalid theme
        settings.set('ui.theme', 'invalid')
        with pytest.raises(ValueError, match="Invalid theme"):
            settings.validate()

    def test_validate_check_frequency_values(self, settings):
        """Test that validate() enforces valid check_frequency values."""
        settings.load()

        # Valid frequencies
        for freq in ['startup', 'daily', 'weekly', 'never']:
            settings.set('updates.check_frequency', freq)
            settings.validate()  # Should not raise

        # Invalid frequency
        settings.set('updates.check_frequency', 'hourly')
        with pytest.raises(ValueError, match="Invalid check_frequency"):
            settings.validate()

    def test_validate_backup_frequency_values(self, settings):
        """Test that validate() enforces valid backup_frequency values."""
        settings.load()

        # Valid frequencies
        for freq in ['never', 'daily', 'weekly']:
            settings.set('data.backup_frequency', freq)
            settings.validate()  # Should not raise

        # Invalid frequency
        settings.set('data.backup_frequency', 'monthly')
        with pytest.raises(ValueError, match="Invalid backup_frequency"):
            settings.validate()

    def test_validate_window_geometry_positive_integers(self, settings):
        """Test that validate() requires positive integers for window geometry."""
        settings.load()

        # Valid values
        settings.set('ui.window_geometry.width', 1920)
        settings.validate()  # Should not raise

        # Negative value
        settings.set('ui.window_geometry.width', -100)
        with pytest.raises(ValueError, match="window_geometry.width"):
            settings.validate()

        # Reset to valid value before next test
        settings.set('ui.window_geometry.width', 1920)

        # Non-integer value (should be caught by schema)
        settings.set('ui.window_geometry.height', "not a number")
        with pytest.raises(ValueError, match="window_geometry.height"):
            settings.validate()

    def test_validate_backup_retention_days(self, settings):
        """Test that validate() requires positive backup_retention_days."""
        settings.load()

        # Valid value
        settings.set('data.backup_retention_days', 30)
        settings.validate()  # Should not raise

        # Zero
        settings.set('data.backup_retention_days', 0)
        with pytest.raises(ValueError, match="backup_retention_days must be > 0"):
            settings.validate()

        # Negative
        settings.set('data.backup_retention_days', -10)
        with pytest.raises(ValueError, match="backup_retention_days must be > 0"):
            settings.validate()

    def test_validate_flask_port_range(self, settings):
        """Test that validate() enforces valid port range for flask_port."""
        settings.load()

        # Null is valid (auto-select)
        settings.set('advanced.flask_port', None)
        settings.validate()  # Should not raise

        # Valid port
        settings.set('advanced.flask_port', 5000)
        settings.validate()  # Should not raise

        # Too low
        settings.set('advanced.flask_port', 1023)
        with pytest.raises(ValueError, match="flask_port must be between 1024 and 65535"):
            settings.validate()

        # Too high
        settings.set('advanced.flask_port', 65536)
        with pytest.raises(ValueError, match="flask_port must be between 1024 and 65535"):
            settings.validate()

    def test_validate_log_level_values(self, settings):
        """Test that validate() enforces valid log_level values."""
        settings.load()

        # Valid log levels
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            settings.set('advanced.log_level', level)
            settings.validate()  # Should not raise

        # Invalid log level
        settings.set('advanced.log_level', 'TRACE')
        with pytest.raises(ValueError, match="Invalid log_level"):
            settings.validate()

    def test_save_validates_before_writing(self, settings):
        """Test that save() validates settings before writing."""
        settings.load()
        settings.set('ui.theme', 'invalid_theme')

        with pytest.raises(ValueError, match="Invalid theme"):
            settings.save()


class TestPlatformSpecificPaths:
    """Test platform-specific user data directory detection."""

    def test_get_user_data_dir_windows(self, settings):
        """Test Windows user data directory path."""
        with patch('sys.platform', 'win32'):
            with patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
                user_dir = settings._get_user_data_dir()
                # On Windows, pathlib uses forward slashes in str representation on non-Windows platforms
                # Just check the important parts instead of exact string match
                assert 'AppData' in str(user_dir)
                assert 'Roaming' in str(user_dir)
                assert 'GradingApp' in str(user_dir)

    def test_get_user_data_dir_macos(self, settings):
        """Test macOS user data directory path."""
        with patch('sys.platform', 'darwin'):
            with patch('pathlib.Path.home', return_value=Path('/Users/test')):
                user_dir = settings._get_user_data_dir()
                assert str(user_dir) == '/Users/test/Library/Application Support/GradingApp'

    def test_get_user_data_dir_linux(self, settings):
        """Test Linux user data directory path."""
        with patch('sys.platform', 'linux'):
            with patch('pathlib.Path.home', return_value=Path('/home/test')):
                with patch.dict(os.environ, {}, clear=True):
                    user_dir = settings._get_user_data_dir()
                    assert str(user_dir) == '/home/test/.local/share/GradingApp'

    def test_get_user_data_dir_linux_xdg_override(self, settings):
        """Test Linux XDG_DATA_HOME override."""
        with patch('sys.platform', 'linux'):
            with patch.dict(os.environ, {'XDG_DATA_HOME': '/custom/data'}):
                user_dir = settings._get_user_data_dir()
                assert str(user_dir) == '/custom/data/GradingApp'


class TestSettingsRoundtrip:
    """Test complete roundtrip scenarios."""

    def test_create_modify_save_load_roundtrip(self, settings, settings_path):
        """Test complete roundtrip: create -> modify -> save -> load."""
        # Load (creates defaults)
        settings.load()

        # Modify multiple values
        settings.set('ui.theme', 'dark')
        settings.set('ui.window_geometry.width', 1920)
        settings.set('updates.check_frequency', 'weekly')
        settings.set('data.backup_retention_days', 60)
        settings.set('advanced.flask_port', 5555)

        # Save
        settings.save()

        # Create new instance and load
        from desktop.settings import Settings
        new_settings = Settings(settings_path)
        new_settings.load()

        # Verify all values persisted
        assert new_settings.get('ui.theme') == 'dark'
        assert new_settings.get('ui.window_geometry.width') == 1920
        assert new_settings.get('updates.check_frequency') == 'weekly'
        assert new_settings.get('data.backup_retention_days') == 60
        assert new_settings.get('advanced.flask_port') == 5555

    def test_multiple_save_operations_maintain_backup(self, settings, settings_path):
        """Test that multiple saves maintain backup of previous state."""
        settings.load()

        # First save
        settings.set('ui.theme', 'dark')
        settings.save()

        # Second save
        settings.set('ui.theme', 'light')
        settings.save()

        # Backup should have 'dark', current should have 'light'
        backup_path = settings_path.with_suffix('.json.bak')
        with open(backup_path, 'r') as f:
            backup = json.load(f)

        with open(settings_path, 'r') as f:
            current = json.load(f)

        assert backup['ui']['theme'] == 'dark'
        assert current['ui']['theme'] == 'light'
