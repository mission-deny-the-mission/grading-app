"""
Desktop application main entry point.

This module provides the main entry point for the desktop grading application.
It launches a Flask server in a background thread and displays it in a PyWebView window.

Architecture:
    1. Configure Flask app for desktop using configure_app_for_desktop()
    2. Get a free port using get_free_port()
    3. Start Flask server in background thread (daemon=True)
    4. Create PyWebView window pointing to Flask URL
    5. Handle graceful shutdown (cleanup task queue, close Flask)

Usage:
    python desktop/main.py

    Or as a PyInstaller executable:
    ./dist/GradingApp/GradingApp
"""

# Application version (semver format)
__version__ = "1.0.0"

import logging
import sys
import threading
import time
from pathlib import Path

# Configure logging before importing other modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

# IMPORTANT: Set DATABASE_URL to SQLite BEFORE importing the app
# The app.py module reads DATABASE_URL at import time, so we must override it first
import os

# Get user data directory (inline to avoid import dependencies)
if sys.platform == 'win32':
    user_data_dir = Path(os.getenv('APPDATA')) / 'GradingApp'
elif sys.platform == 'darwin':
    user_data_dir = Path.home() / 'Library' / 'Application Support' / 'GradingApp'
else:  # Linux
    user_data_dir = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'GradingApp'

user_data_dir.mkdir(parents=True, exist_ok=True)
db_path = user_data_dir / 'grading.db'
os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
logger.info(f"Set DATABASE_URL to: sqlite:///{db_path}")

# Import Flask app from repository root
try:
    # Add parent directory to path if not already there
    parent_dir = Path(__file__).parent.parent.resolve()
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from app import app
    logger.info("Successfully imported Flask app")
except ImportError as e:
    logger.error(f"Failed to import Flask app: {e}")
    sys.exit(1)

# Import desktop utilities
from desktop.app_wrapper import configure_app_for_desktop, get_free_port, get_user_data_dir
from desktop.task_queue import task_queue
from desktop.scheduler import start as start_scheduler, stop as stop_scheduler
from desktop.settings import Settings


def check_for_updates_async(settings: Settings) -> None:
    """
    Check for updates in a background thread.

    This function runs asynchronously to avoid blocking application startup.
    If an update is available and auto_check is enabled in settings, it will
    show a notification to the user.

    Args:
        settings: Settings instance to read update preferences

    Note:
        This function runs in a background thread and should not block.
    """
    try:
        # Check if auto-check is enabled
        if not settings.get('updates.auto_check', True):
            logger.debug("Auto-check for updates is disabled")
            return

        # Check if we should defer this version
        deferred_version = settings.get('updates.deferred_version')

        # Import updater (late import to avoid startup delay if not needed)
        from desktop.updater import DesktopUpdater
        from desktop.window_manager import show_update_notification
        from datetime import datetime, timedelta

        # Check last update check time to avoid too frequent checks
        last_check = settings.get('updates.last_check')
        if last_check:
            try:
                last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                # Don't check more than once per day
                if datetime.utcnow() - last_check_dt < timedelta(hours=24):
                    logger.debug("Update check skipped - checked less than 24 hours ago")
                    return
            except (ValueError, AttributeError):
                # Invalid timestamp, proceed with check
                pass

        logger.info("Checking for updates...")

        # Create updater instance
        updater = DesktopUpdater(
            app_name="grading-app",
            current_version=__version__,
            update_url="https://github.com/user/grading-app"  # TODO: Update with actual repo URL
        )

        # Check for updates
        update_info = updater.check_for_updates()

        # Update last check time
        settings.set('updates.last_check', datetime.utcnow().isoformat() + 'Z')
        settings.save()

        if not update_info.get('available'):
            logger.info("No updates available")
            return

        new_version = update_info.get('version')

        # Check if user deferred this version
        if deferred_version == new_version:
            logger.info(f"Update to {new_version} was deferred by user")
            return

        logger.info(f"Update available: {new_version}")

        # Show notification to user (this might need to be on main thread)
        # For now, just log it - actual notification would need coordination with main thread
        logger.info(f"Update notification: New version {new_version} is available")

        # Note: Actual notification UI would need to be called from main thread
        # This is a background thread, so we can't directly show UI

    except Exception as e:
        logger.error(f"Update check failed: {e}", exc_info=True)


def start_flask(host: str = '127.0.0.1', port: int = 5050, debug: bool = False) -> None:
    """
    Start Flask server in the current thread.

    This function is meant to be run in a background daemon thread.
    It will block until the Flask server is stopped.

    Args:
        host: Host address to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 5050)
        debug: Enable Flask debug mode (default: False)

    Note:
        This function should be called from a daemon thread so it doesn't
        prevent the application from exiting.
    """
    try:
        logger.info(f"Starting Flask server on {host}:{port}")
        # Disable Flask's default logging to prevent duplicate logs
        import logging as flask_logging
        flask_log = flask_logging.getLogger('werkzeug')
        flask_log.setLevel(logging.WARNING)

        # Run Flask server (blocks until stopped)
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # Disable reloader in desktop mode
            threaded=True  # Enable threading for concurrent requests
        )
    except Exception as e:
        logger.error(f"Flask server error: {e}")
        raise


def create_main_window(url: str, title: str = "Grading App",
                       width: int = 1280, height: int = 800) -> None:
    """
    Create and display the main PyWebView window.

    This function will block until the window is closed by the user.

    Args:
        url: URL to display in the window (e.g., 'http://127.0.0.1:5050')
        title: Window title (default: "Grading App")
        width: Initial window width in pixels (default: 1280)
        height: Initial window height in pixels (default: 800)

    Raises:
        ImportError: If PyWebView is not installed

    Note:
        This function blocks until the window is closed.
    """
    try:
        import webview
        logger.info(f"Creating PyWebView window: {title} ({width}x{height})")

        # Wait a moment for Flask to start before opening window
        time.sleep(0.5)

        # Create and start the window (blocks until closed)
        webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height
        )
        webview.start()

        logger.info("PyWebView window closed")

    except ImportError as e:
        logger.error(
            f"PyWebView not installed: {e}\n"
            "Install with: pip install pywebview>=4.0.0"
        )
        raise
    except Exception as e:
        logger.error(f"Error creating window: {e}")
        raise


def shutdown_gracefully() -> None:
    """
    Perform graceful shutdown of the application.

    This function:
    1. Shuts down the task queue (waits for running tasks)
    2. Stops the periodic task scheduler
    3. Logs shutdown completion

    Note:
        Flask server will stop automatically when the main thread exits
        (since it's running in a daemon thread).
    """
    logger.info("Initiating graceful shutdown...")

    try:
        # Shutdown task queue with timeout
        logger.info("Shutting down task queue...")
        task_queue.shutdown(wait=True, timeout=30)
        logger.info("Task queue shutdown complete")
    except Exception as e:
        logger.error(f"Error during task queue shutdown: {e}")

    try:
        # Shutdown scheduler
        logger.info("Stopping periodic task scheduler...")
        stop_scheduler()
        logger.info("Scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error during scheduler shutdown: {e}")

    logger.info("Graceful shutdown complete")


def main() -> int:
    """
    Main entry point for the desktop application.

    Workflow:
        1. Configure Flask app for desktop deployment
        2. Initialize database
        3. Start periodic task scheduler
        4. Get an available port
        5. Start Flask server in background thread
        6. Create PyWebView window
        7. Handle graceful shutdown on exit

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info("=" * 60)
        logger.info("Starting Grading App Desktop Application")
        logger.info("=" * 60)

        # Configure Flask app for desktop
        logger.info("Configuring Flask app for desktop deployment...")
        configure_app_for_desktop(app)
        logger.info("Flask app configured successfully")

        # Initialize database
        logger.info("Initializing database...")
        with app.app_context():
            from models import db
            db.create_all()
            logger.info("Database initialized successfully")

        # Get user data directory for logging
        user_data_dir = get_user_data_dir()
        logger.info(f"User data directory: {user_data_dir}")

        # Load settings
        logger.info("Loading application settings...")
        settings_path = user_data_dir / 'settings.json'
        settings = Settings(settings_path)
        settings.load()
        logger.info("Settings loaded successfully")

        # Start the periodic task scheduler
        logger.info("Starting periodic task scheduler...")
        try:
            start_scheduler()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise

        # Check for updates in background thread (non-blocking)
        if settings.get('updates.auto_check', True):
            logger.info("Starting background update check...")
            update_thread = threading.Thread(
                target=check_for_updates_async,
                args=(settings,),
                daemon=True,
                name="UpdateCheckThread"
            )
            update_thread.start()
            logger.debug("Update check thread started")

        # Get a free port
        port = get_free_port()
        host = '127.0.0.1'
        logger.info(f"Using port: {port}")

        # Start Flask in background thread
        flask_thread = threading.Thread(
            target=start_flask,
            args=(host, port, False),  # host, port, debug
            daemon=True,  # Thread will exit when main thread exits
            name="FlaskServerThread"
        )
        flask_thread.start()
        logger.info("Flask server thread started")

        # Build Flask URL
        flask_url = f'http://{host}:{port}'
        logger.info(f"Flask URL: {flask_url}")

        # Create and show main window (blocks until closed)
        logger.info("Creating main window...")
        create_main_window(
            url=flask_url,
            title="Grading App",
            width=1280,
            height=800
        )

        # Window closed - perform graceful shutdown
        shutdown_gracefully()

        logger.info("Application exited successfully")
        return 0

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        shutdown_gracefully()
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        shutdown_gracefully()
        return 1


if __name__ == '__main__':
    sys.exit(main())
