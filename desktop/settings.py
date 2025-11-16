"""
Application Settings Management

Manages user-configurable preferences for the desktop application.
Settings are stored in JSON format in the user data directory and include
UI preferences, update configuration, data paths, and advanced options.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import sys


class Settings:
    """
    Manages application settings with atomic saves and schema validation.

    Settings are loaded from a JSON file in the user data directory and provide
    default values for missing settings. Changes are saved atomically using a
    write-to-temp-then-rename strategy, with automatic backup creation.
    """

    # Current settings schema version
    SETTINGS_VERSION = "1.0.0"

    # Default settings template
    DEFAULT_SETTINGS = {
        "version": SETTINGS_VERSION,
        "app_version": "0.1.0",
        "last_updated": None,  # Will be set on first save
        "ui": {
            "theme": "system",
            "start_minimized": False,
            "show_in_system_tray": True,
            "window_geometry": {
                "width": 1280,
                "height": 800,
                "x": 100,
                "y": 100,
                "maximized": False
            }
        },
        "updates": {
            "auto_check": True,
            "check_frequency": "startup",
            "auto_download": False,
            "last_check": None,
            "deferred_version": None
        },
        "data": {
            "database_path": None,  # Will be set to default user data dir path
            "uploads_path": None,  # Will be set to default user data dir path
            "backups_enabled": True,
            "backup_frequency": "daily",
            "backup_retention_days": 30
        },
        "advanced": {
            "flask_port": None,
            "log_level": "INFO",
            "enable_telemetry": False
        }
    }

    def __init__(self, settings_path: Path):
        """
        Initialize Settings manager.

        Args:
            settings_path: Path to the settings JSON file
        """
        self.settings_path = Path(settings_path)
        self._settings = {}

    def load(self) -> None:
        """
        Load settings from disk or create defaults if missing.

        If the settings file doesn't exist, creates default settings.
        If the file exists but is invalid, raises an exception.
        """
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)

                # Validate loaded settings
                self.validate()

                # Merge with defaults to ensure all keys exist
                self._merge_defaults()

            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in settings file: {e}")
        else:
            # Create default settings
            self._settings = self._create_default_settings()

            # Create directory if needed
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Save defaults to disk
            self.save()

    def save(self) -> None:
        """
        Save settings to disk atomically.

        Uses a write-to-temp-then-rename strategy to ensure atomicity.
        Creates a backup (.bak) of the existing settings before writing.
        """
        # Validate before saving
        self.validate()

        # Update last_updated timestamp
        self._settings['last_updated'] = datetime.utcnow().isoformat() + 'Z'

        # Ensure directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup of existing settings
        if self.settings_path.exists():
            backup_path = self.settings_path.with_suffix('.json.bak')
            shutil.copy2(self.settings_path, backup_path)

        # Write to temporary file
        temp_path = self.settings_path.with_suffix('.json.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            temp_path.replace(self.settings_path)

        except Exception:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.

        Supports nested keys using dot notation (e.g., "ui.theme").

        Args:
            key: Setting key (supports dot notation for nested values)
            default: Default value if key doesn't exist

        Returns:
            The setting value or default if not found
        """
        keys = key.split('.')
        value = self._settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value by key.

        Supports nested keys using dot notation (e.g., "ui.theme").

        Args:
            key: Setting key (supports dot notation for nested values)
            value: Value to set
        """
        keys = key.split('.')
        target = self._settings

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        # Set the value
        target[keys[-1]] = value

    def validate(self) -> None:
        """
        Validate settings schema.

        Raises:
            ValueError: If settings fail validation
        """
        # Check version exists and is valid semver
        if 'version' not in self._settings:
            raise ValueError("Missing required field: version")

        # Validate theme
        theme = self.get('ui.theme')
        if theme and theme not in ['light', 'dark', 'system']:
            raise ValueError(f"Invalid theme: {theme}. Must be one of: light, dark, system")

        # Validate check_frequency
        check_freq = self.get('updates.check_frequency')
        if check_freq and check_freq not in ['startup', 'daily', 'weekly', 'never']:
            raise ValueError(f"Invalid check_frequency: {check_freq}")

        # Validate backup_frequency
        backup_freq = self.get('data.backup_frequency')
        if backup_freq and backup_freq not in ['never', 'daily', 'weekly']:
            raise ValueError(f"Invalid backup_frequency: {backup_freq}")

        # Validate window geometry
        geometry = self.get('ui.window_geometry', {})
        for key in ['width', 'height', 'x', 'y']:
            value = geometry.get(key)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"Invalid window_geometry.{key}: must be a positive integer")

        # Validate backup retention days
        retention_days = self.get('data.backup_retention_days')
        if retention_days is not None and (not isinstance(retention_days, int) or retention_days <= 0):
            raise ValueError("backup_retention_days must be > 0")

        # Validate flask_port
        flask_port = self.get('advanced.flask_port')
        if flask_port is not None:
            if not isinstance(flask_port, int) or flask_port < 1024 or flask_port > 65535:
                raise ValueError("flask_port must be between 1024 and 65535")

        # Validate log_level
        log_level = self.get('advanced.log_level')
        if log_level and log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            raise ValueError(f"Invalid log_level: {log_level}")

    def _create_default_settings(self) -> dict:
        """
        Create default settings with platform-specific paths.

        Returns:
            Dictionary containing default settings
        """
        import copy
        settings = copy.deepcopy(self.DEFAULT_SETTINGS)

        # Set platform-specific paths
        user_data_dir = self._get_user_data_dir()
        settings['data']['database_path'] = str(user_data_dir / 'grading.db')
        settings['data']['uploads_path'] = str(user_data_dir / 'uploads')

        return settings

    def _merge_defaults(self) -> None:
        """
        Merge loaded settings with defaults to ensure all keys exist.

        This handles settings file upgrades where new keys might be added.
        """
        def merge_dicts(target: dict, source: dict) -> dict:
            """Recursively merge source into target, preserving target values."""
            for key, value in source.items():
                if key not in target:
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    merge_dicts(target[key], value)
            return target

        defaults = self._create_default_settings()
        self._settings = merge_dicts(self._settings, defaults)

    @staticmethod
    def _get_user_data_dir() -> Path:
        """
        Get platform-specific user data directory.

        Returns:
            Path to user data directory for the application
        """
        if sys.platform == 'win32':
            base = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux and other Unix-like systems
            base = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

        return base / 'GradingApp'
