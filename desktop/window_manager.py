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
    on_show: Callable[[], None],
    on_hide: Callable[[], None],
    on_quit: Callable[[], None]
) -> None:
    """
    Create system tray icon with menu items.

    This function creates a system tray icon with a menu containing:
    - Show: Callback to show the main window
    - Hide: Callback to hide the main window
    - Quit: Callback to quit the application

    Args:
        on_show: Callback function to show the window
        on_hide: Callback function to hide the window
        on_quit: Callback function to quit the application

    Note:
        This function blocks until the tray icon is removed.
        Run in a separate thread if needed.

    Example:
        >>> def show():
        ...     print("Showing window")
        >>> def hide():
        ...     print("Hiding window")
        >>> def quit_app():
        ...     print("Quitting")
        >>> # Run in separate thread
        >>> thread = threading.Thread(
        ...     target=create_system_tray,
        ...     args=(show, hide, quit_app),
        ...     daemon=True
        ... )
        >>> thread.start()
    """
    try:
        import pystray
        from PIL import Image
        from pathlib import Path

        logger.info("Creating system tray icon")

        # Try to load icon from resources, fall back to creating a default one
        icon_path = Path(__file__).parent / 'resources' / 'icon.png'

        if icon_path.exists():
            logger.debug(f"Loading icon from {icon_path}")
            icon_image = Image.open(icon_path)
        else:
            logger.warning(f"Icon not found at {icon_path}, creating default icon")
            # Create a simple default icon (64x64 white square with "GA" text)
            icon_image = Image.new('RGB', (64, 64), color='white')

        # Create menu items
        menu_items = [
            pystray.MenuItem("Show", on_show),
            pystray.MenuItem("Hide", on_hide),
            pystray.MenuItem("Quit", on_quit)
        ]

        # Create tray icon
        icon = pystray.Icon(
            name="Grading App",
            icon=icon_image,
            title="Grading App",
            menu=pystray.Menu(*menu_items)
        )

        logger.info("System tray icon created, starting...")
        # This blocks until icon.stop() is called
        icon.run()

    except ImportError as e:
        logger.error(f"pystray library not available: {e}")
        logger.warning("System tray functionality will not be available")
        logger.info("Install with: pip install pystray>=0.19.0")
        raise RuntimeError("pystray library not installed") from e

    except Exception as e:
        logger.error(f"Failed to create system tray: {e}")
        raise RuntimeError(f"System tray creation failed: {e}") from e


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
