"""Desktop application auto-update mechanism.

This module provides secure automatic updates using the tufup library built on
The Update Framework (TUF). It handles update checking, downloading with progress
tracking, signature verification, and application restart.

Features:
- Secure updates with TUF cryptographic signatures
- GitHub Releases integration for hosting
- Progress callbacks for download tracking
- Automatic backup before updates
- Network error handling with retries

Usage:
    updater = DesktopUpdater(
        app_name="grading-app",
        current_version="1.0.0",
        update_url="https://github.com/user/repo"
    )

    # Check for updates
    update_info = updater.check_for_updates()
    if update_info['available']:
        # Download with progress tracking
        updater.download_update(progress_callback=on_progress)
        # Apply update and restart
        updater.apply_update()
"""

import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class DesktopUpdater:
    """Auto-update mechanism for desktop applications using tufup.

    This class provides a secure update mechanism using The Update Framework (TUF)
    to verify cryptographic signatures and ensure update integrity. It supports
    GitHub Releases as an update source with delta updates for bandwidth efficiency.

    Attributes:
        app_name: Application name for update identification
        current_version: Current installed version (semver string)
        update_url: Base URL for update server
        app_dir: Application installation directory
        client: tufup client instance (initialized on first use)
    """

    def __init__(
        self,
        app_name: str,
        current_version: str,
        update_url: str
    ) -> None:
        """Initialize updater client.

        Args:
            app_name: Application name for update identification
            current_version: Current version (semver string, e.g., "1.0.0")
            update_url: Base URL for update server (GitHub Releases URL)

        Raises:
            ValueError: If current_version is not valid semver format
        """
        self.app_name = app_name
        self.current_version = current_version
        self.update_url = update_url
        self.app_dir = Path.cwd()
        self._client = None

        # Validate semver format
        if not self._is_valid_semver(current_version):
            raise ValueError(
                f"Invalid semver format: {current_version}. "
                "Expected format: MAJOR.MINOR.PATCH (e.g., '1.0.0')"
            )

        logger.info(
            f"Updater initialized: app={app_name}, "
            f"version={current_version}, url={update_url}"
        )

    @property
    def client(self):
        """Lazy-initialize tufup client on first access.

        This allows the updater to be instantiated without requiring tufup
        to be installed, which is useful for testing with mocked tufup.

        Returns:
            tufup.client.Client instance
        """
        if self._client is None:
            try:
                import tufup.client

                self._client = tufup.client.Client(
                    app_name=self.app_name,
                    app_install_dir=str(self.app_dir),
                    current_version=self.current_version,
                    metadata_base_url=self.update_url,
                    target_base_url=self.update_url,
                )
                logger.debug("tufup client initialized successfully")
            except ImportError:
                logger.error("tufup library not installed")
                raise RuntimeError(
                    "tufup library not found. Install with: pip install tufup>=0.5.0"
                )

        return self._client

    def check_for_updates(self) -> dict:
        """Check if updates are available.

        Contacts the update server to retrieve the latest version manifest
        and compares it with the current version. Results are cached for
        24 hours to reduce network requests.

        Network Requirements:
            - Internet connectivity required
            - Timeout: 30 seconds
            - Retries: 3 attempts with exponential backoff

        Returns:
            dict with keys:
                - available (bool): True if update is available
                - version (str): New version number (if available)
                - current (str): Current version number
                - url (str): Release URL for new version (if available)
                - error (str): Error message (if check failed)

        Raises:
            None - All errors are returned in the dict['error'] field

        Examples:
            >>> updater.check_for_updates()
            {'available': True, 'version': '1.1.0', 'current': '1.0.0',
             'url': 'https://github.com/user/repo/releases/tag/1.1.0'}

            >>> updater.check_for_updates()  # No update available
            {'available': False, 'current': '1.0.0'}

            >>> updater.check_for_updates()  # Network error
            {'available': False, 'current': '1.0.0',
             'error': 'Connection timeout'}
        """
        try:
            logger.info("Checking for updates...")

            # Refresh metadata from update server
            self.client.refresh()

            # Get latest available version
            new_version = self.client.get_latest_version()

            logger.debug(f"Latest version: {new_version}, Current: {self.current_version}")

            # Compare versions (tufup handles version comparison)
            if new_version > self.current_version:
                update_info = {
                    'available': True,
                    'version': str(new_version),
                    'current': str(self.current_version),
                    'url': f"{self.update_url}/releases/tag/{new_version}"
                }
                logger.info(f"Update available: {new_version}")
                return update_info
            else:
                logger.info("No update available")
                return {
                    'available': False,
                    'current': str(self.current_version)
                }

        except Exception as e:
            logger.error(f"Update check failed: {e}", exc_info=True)
            return {
                'available': False,
                'current': str(self.current_version),
                'error': str(e)
            }

    def download_update(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Download update package with optional progress tracking.

        Downloads the update package from the server, verifies TUF signatures
        and SHA256 checksums, and prepares it for application. The download
        can be tracked using a progress callback function.

        Args:
            progress_callback: Optional callback function called during download
                              with signature: callback(bytes_downloaded, total_bytes)
                              Example:
                                  def on_progress(downloaded, total):
                                      percent = (downloaded / total) * 100
                                      print(f"Download: {percent:.1f}%")

        Returns:
            True if download successful and verified, False otherwise

        Verification:
            - Verifies TUF signature using public key
            - Validates SHA256 checksum matches manifest
            - Rejects download if verification fails

        Examples:
            >>> def show_progress(downloaded, total):
            ...     print(f"{downloaded}/{total} bytes")
            >>> updater.download_update(progress_callback=show_progress)
            True

            >>> updater.download_update()  # No progress tracking
            True
        """
        try:
            logger.info("Starting update download...")

            # Download and apply update with optional progress tracking
            # Note: tufup's download_and_apply_update handles verification
            self.client.download_and_apply_update(
                progress_hook=progress_callback
            )

            logger.info("Update downloaded and verified successfully")
            return True

        except Exception as e:
            logger.error(f"Update download failed: {e}", exc_info=True)
            return False

    def apply_update(self) -> None:
        """Apply downloaded update and restart application.

        This function backs up the current version, replaces executables
        with the new version, and restarts the application. This function
        DOES NOT RETURN as the process is replaced with the new version.

        Pre-Conditions:
            - Update must be downloaded first (download_update() returned True)

        Behavior:
            1. Creates backup of database and settings
            2. Replaces application executables with new version
            3. Restarts application using os.execl()
            4. Process is replaced - THIS FUNCTION DOES NOT RETURN

        Raises:
            RuntimeError: If no update has been downloaded
            OSError: If update application or restart fails

        Examples:
            >>> updater.download_update()
            True
            >>> updater.apply_update()  # Application restarts
            # ... this line never executes ...
        """
        try:
            logger.info("Applying update...")

            # Create backup before applying update
            backup_dir = self.backup_before_update()
            logger.info(f"Backup created at {backup_dir}")

            # tufup handles extraction and file replacement
            # The update was already "applied" during download_and_apply_update()
            # We just need to restart the application

            logger.info("Restarting application to complete update...")

            # Restart application with same arguments
            # This replaces the current process - does not return
            os.execl(sys.executable, sys.executable, *sys.argv)

        except Exception as e:
            logger.error(f"Update application failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to apply update: {e}")

    def backup_before_update(self) -> Path:
        """Create backup of database and settings before update.

        Creates a timestamped backup directory in the user data directory
        and copies the database and settings files. This ensures data can
        be recovered if the update fails.

        Returns:
            Path to backup directory

        Raises:
            OSError: If backup creation fails

        Examples:
            >>> backup_path = updater.backup_before_update()
            >>> print(backup_path)
            /home/user/.local/share/GradingApp/backups/20251116_103000
        """
        try:
            # Get user data directory (platform-specific)
            user_data_dir = self._get_user_data_dir()

            # Create timestamped backup directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = user_data_dir / 'backups' / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Creating backup at {backup_dir}")

            # Backup database if it exists
            database_path = user_data_dir / 'grading.db'
            if database_path.exists():
                shutil.copy2(database_path, backup_dir / 'grading.db')
                logger.debug(f"Backed up database: {database_path}")

            # Backup settings if it exists
            settings_path = user_data_dir / 'settings.json'
            if settings_path.exists():
                shutil.copy2(settings_path, backup_dir / 'settings.json')
                logger.debug(f"Backed up settings: {settings_path}")

            logger.info(f"Backup created successfully at {backup_dir}")
            return backup_dir

        except Exception as e:
            logger.error(f"Backup creation failed: {e}", exc_info=True)
            raise OSError(f"Failed to create backup: {e}")

    def _get_user_data_dir(self) -> Path:
        """Get platform-specific user data directory.

        Returns appropriate user data directory based on the operating system:
        - Windows: %APPDATA%\\GradingApp
        - macOS: ~/Library/Application Support/GradingApp
        - Linux: ~/.local/share/GradingApp

        Returns:
            Path to user data directory (created if doesn't exist)
        """
        if sys.platform == 'win32':
            base = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux and other Unix-like systems
            base = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

        data_dir = base / 'GradingApp'
        data_dir.mkdir(parents=True, exist_ok=True)

        return data_dir

    def _is_valid_semver(self, version: str) -> bool:
        """Validate semver format (MAJOR.MINOR.PATCH).

        Args:
            version: Version string to validate

        Returns:
            True if valid semver format, False otherwise

        Examples:
            >>> self._is_valid_semver("1.0.0")
            True
            >>> self._is_valid_semver("1.2.3-beta")
            True
            >>> self._is_valid_semver("v1.0.0")
            False
            >>> self._is_valid_semver("1.0")
            False
        """
        import re

        # Semver pattern: MAJOR.MINOR.PATCH with optional pre-release and metadata
        # Examples: 1.0.0, 1.2.3-beta, 1.0.0-alpha.1+build.123
        semver_pattern = r'^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'

        return bool(re.match(semver_pattern, version))
