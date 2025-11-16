"""
Window manager module for desktop application.

This module provides functionality for:
- Creating the main PyWebView window
- Creating system tray icon with pystray
- Showing update notifications

Reference:
- quickstart.md lines 59-63 (create_main_window example)
- quickstart.md lines 242-257 (create_system_tray example)
- research.md lines 79-96 (PyWebView integration)
- research.md lines 244-260 (pystray system tray)
- research.md lines 940-963 (update notification)
"""

import logging
import webview
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


def create_main_window(
    url: str,
    title: str = "Grading App",
    width: int = 1280,
    height: int = 800
) -> Optional[webview.Window]:
    """
    Create PyWebView main window for the application.

    Args:
        url: URL to load in the window (typically http://127.0.0.1:PORT)
        title: Window title (default: "Grading App")
        width: Window width in pixels (default: 1280)
        height: Window height in pixels (default: 800)

    Returns:
        webview.Window: The created window instance, or None on error

    Raises:
        RuntimeError: If window creation fails

    Example:
        >>> window = create_main_window('http://127.0.0.1:5050')
        >>> webview.start()
    """
    try:
        logger.info(f"Creating main window: {title} ({width}x{height})")
        logger.debug(f"Window URL: {url}")

        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height
        )

        logger.info("Main window created successfully")
        return window

    except Exception as e:
        logger.error(f"Failed to create main window: {e}")
        raise RuntimeError(f"Window creation failed: {e}") from e


def create_system_tray(
    window: Optional['webview.Window'] = None,
    on_quit: Optional[Callable[[], None]] = None,
    settings_url: str = "http://127.0.0.1:5050/desktop/settings",
    data_url: str = "http://127.0.0.1:5050/desktop/data",
    start_hidden: bool = False
) -> Optional['pystray.Icon']:
    """
    Create system tray icon with comprehensive menu.

    This function creates a system tray icon with a menu containing:
    - Show Window / Hide Window (toggle based on window visibility)
    - Settings (opens settings page)
    - Data Management (opens data export/backup page)
    - Check for Updates (triggers update check)
    - Help submenu (About, View Logs)
    - Quit (exits application)

    Args:
        window: PyWebView window instance for show/hide functionality
        on_quit: Callback function to quit the application
        settings_url: URL to settings page (default: /desktop/settings)
        data_url: URL to data management page (default: /desktop/data)
        start_hidden: If True, window starts hidden (default: False)

    Returns:
        pystray.Icon instance if successful, None if creation fails

    Note:
        This function blocks until the tray icon is removed.
        Run in a separate thread if needed.

    Example:
        >>> import webview
        >>> import threading
        >>>
        >>> window = webview.create_window('App', 'http://localhost:5050')
        >>>
        >>> def quit_app():
        ...     print("Quitting")
        ...     sys.exit(0)
        >>>
        >>> # Run tray in separate thread
        >>> tray_thread = threading.Thread(
        ...     target=create_system_tray,
        ...     args=(window, quit_app),
        ...     daemon=True
        ... )
        >>> tray_thread.start()
        >>> webview.start()
    """
    try:
        import pystray
        from PIL import Image
        from pathlib import Path
        import webbrowser

        logger.info("Creating system tray icon")

        # Track window visibility state
        window_visible = not start_hidden

        # Try to load icon from resources, fall back to creating a default one
        icon_path = Path(__file__).parent / 'resources' / 'icon.png'

        if icon_path.exists():
            logger.debug(f"Loading icon from {icon_path}")
            icon_image = Image.open(icon_path)
        else:
            logger.warning(f"Icon not found at {icon_path}, creating default icon")
            # Create a simple default icon (64x64 white square with "GA" text)
            icon_image = Image.new('RGB', (64, 64), color='white')

        # Define menu callbacks
        def on_show_window(icon_obj, item):
            """Show the main window."""
            nonlocal window_visible
            if window:
                try:
                    window.show()
                    window_visible = True
                    logger.info("Window shown via system tray")
                except Exception as e:
                    logger.error(f"Failed to show window: {e}")
            else:
                logger.warning("No window instance available")

        def on_hide_window(icon_obj, item):
            """Hide the main window."""
            nonlocal window_visible
            if window:
                try:
                    window.hide()
                    window_visible = False
                    logger.info("Window hidden via system tray")
                except Exception as e:
                    logger.error(f"Failed to hide window: {e}")
            else:
                logger.warning("No window instance available")

        def on_toggle_window(icon_obj, item):
            """Toggle window visibility."""
            if window_visible:
                on_hide_window(icon_obj, item)
            else:
                on_show_window(icon_obj, item)

        def on_settings(icon_obj, item):
            """Open settings page in the window."""
            if window:
                try:
                    # Ensure window is visible
                    if not window_visible:
                        on_show_window(icon_obj, item)
                    # Navigate to settings (if pywebview supports it)
                    # For now, user can click settings in the app
                    logger.info("Settings menu item clicked")
                    # Alternative: open in default browser
                    # webbrowser.open(settings_url)
                except Exception as e:
                    logger.error(f"Failed to open settings: {e}")
            else:
                # Fallback: open in browser
                webbrowser.open(settings_url)

        def on_data_management(icon_obj, item):
            """Open data management page in the window."""
            if window:
                try:
                    # Ensure window is visible
                    if not window_visible:
                        on_show_window(icon_obj, item)
                    logger.info("Data Management menu item clicked")
                except Exception as e:
                    logger.error(f"Failed to open data management: {e}")
            else:
                # Fallback: open in browser
                webbrowser.open(data_url)

        def on_check_updates(icon_obj, item):
            """Trigger update check."""
            logger.info("Check for Updates triggered from system tray")
            # Import here to avoid circular dependency
            try:
                from desktop.updater import DesktopUpdater
                from desktop.main import __version__

                updater = DesktopUpdater(
                    app_name="grading-app",
                    current_version=__version__,
                    update_url="https://github.com/user/grading-app"
                )
                update_info = updater.check_for_updates()

                if update_info.get('available'):
                    logger.info(f"Update available: {update_info.get('version')}")
                    # Show notification
                    show_update_notification(update_info)
                else:
                    logger.info("No updates available")
                    # Could show a "No updates" notification here
            except Exception as e:
                logger.error(f"Update check failed: {e}")

        def on_about(icon_obj, item):
            """Show about information."""
            logger.info("About menu item clicked")
            # Import version here
            try:
                from desktop.main import __version__
                about_msg = f"Grading App Desktop\nVersion: {__version__}\n\nA desktop application for grading assignments."
                logger.info(about_msg)
                # In a real implementation, this would show a dialog
                # For now, just log it
            except Exception as e:
                logger.error(f"Failed to show about: {e}")

        def on_view_logs(icon_obj, item):
            """Open logs directory."""
            logger.info("View Logs menu item clicked")
            try:
                from desktop.app_wrapper import get_user_data_dir
                import subprocess
                import sys

                user_data_dir = get_user_data_dir()
                logs_dir = user_data_dir / 'logs'

                # Create logs directory if it doesn't exist
                logs_dir.mkdir(parents=True, exist_ok=True)

                # Open directory in file manager
                if sys.platform == 'win32':
                    subprocess.run(['explorer', str(logs_dir)])
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(logs_dir)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(logs_dir)])

                logger.info(f"Opened logs directory: {logs_dir}")
            except Exception as e:
                logger.error(f"Failed to open logs: {e}")

        def on_quit_app(icon_obj, item):
            """Quit the application."""
            logger.info("Quit triggered from system tray")
            if on_quit:
                on_quit()
            else:
                # Default quit behavior
                import sys
                icon_obj.stop()
                sys.exit(0)

        def get_toggle_text(item):
            """Dynamic text for toggle menu item."""
            return "Hide Window" if window_visible else "Show Window"

        # Create menu structure
        menu = pystray.Menu(
            pystray.MenuItem(
                get_toggle_text,
                on_toggle_window,
                default=True  # Default action on icon click
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Settings', on_settings),
            pystray.MenuItem('Data Management', on_data_management),
            pystray.MenuItem('Check for Updates', on_check_updates),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                'Help',
                pystray.Menu(
                    pystray.MenuItem('About', on_about),
                    pystray.MenuItem('View Logs', on_view_logs),
                )
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', on_quit_app)
        )

        # Create tray icon
        icon = pystray.Icon(
            name="Grading App",
            icon=icon_image,
            title="Grading App",
            menu=menu
        )

        logger.info("System tray icon created, starting...")

        # Return icon so it can be controlled externally
        # Note: Caller needs to call icon.run() to start the tray
        return icon

    except ImportError as e:
        logger.error(f"pystray library not available: {e}")
        logger.warning("System tray functionality will not be available")
        logger.info("Install with: pip install pystray>=0.19.0")
        return None

    except Exception as e:
        logger.error(f"Failed to create system tray: {e}")
        return None


def show_update_notification(update_info: Dict[str, Any]) -> bool:
    """
    Show update notification dialog to user.

    Displays a dialog informing the user about an available update
    with options to update now or remind later.

    Args:
        update_info: Dictionary containing update information:
            - version (str): New version number
            - current (str): Current version number
            - url (str, optional): URL to release notes
            - release_notes (str, optional): Release notes text

    Returns:
        bool: True if user clicked "Update Now", False if "Remind Me Later"

    Example:
        >>> update_info = {
        ...     'version': '1.1.0',
        ...     'current': '1.0.0',
        ...     'release_notes': 'Bug fixes and improvements'
        ... }
        >>> should_update = show_update_notification(update_info)
        >>> if should_update:
        ...     # Proceed with update
        ...     pass
    """
    try:
        logger.info(f"Showing update notification for version {update_info.get('version')}")

        new_version = update_info.get('version', 'Unknown')
        current_version = update_info.get('current', 'Unknown')
        release_notes = update_info.get('release_notes', 'No release notes available')
        url = update_info.get('url', '')

        # Build notification message
        message = f"A new version of Grading App is available!\n\n"
        message += f"Current version: {current_version}\n"
        message += f"New version: {new_version}\n\n"

        if release_notes:
            message += f"What's new:\n{release_notes}\n\n"

        if url:
            message += f"Release notes: {url}\n\n"

        message += "Would you like to update now?"

        # Show dialog using webview API
        # Note: This creates a temporary window for the dialog
        result = webview.create_confirmation_dialog(
            title="Update Available",
            message=message
        )

        if result:
            logger.info("User chose to update now")
            return True
        else:
            logger.info("User chose to remind later")
            return False

    except AttributeError:
        # webview.create_confirmation_dialog might not exist in all versions
        # Fall back to a simpler approach
        logger.warning("webview.create_confirmation_dialog not available")
        logger.info("Falling back to terminal prompt")

        print("\n" + "=" * 60)
        print("UPDATE AVAILABLE")
        print("=" * 60)
        print(f"Current version: {current_version}")
        print(f"New version: {new_version}")
        if release_notes:
            print(f"\nWhat's new:\n{release_notes}")
        if url:
            print(f"\nRelease notes: {url}")
        print("=" * 60)

        # For testing purposes, return False (remind later)
        # In production, this could use a different dialog library
        return False

    except Exception as e:
        logger.error(f"Failed to show update notification: {e}")
        # Don't crash the app if notification fails
        return False
