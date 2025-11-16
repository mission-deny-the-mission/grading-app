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
from desktop.crash_reporter import setup_crash_handler, cleanup_old_crash_logs


def setup_logging() -> None:
    """
    Configure application logging with rotating file handlers.

    Creates log files in user data directory:
    - app.log: Main application events
    - flask.log: Flask server and routing
    - updates.log: Update check and installation
    - errors.log: Error events only

    Each log file:
    - Max size: 5MB
    - Keeps 5 rotations
    - Rotates daily or by size
    """
    from logging.handlers import RotatingFileHandler

    # Get user data directory (inline to avoid import dependencies)
    if sys.platform == 'win32':
        user_data_dir = Path(os.getenv('APPDATA')) / 'GradingApp'
    elif sys.platform == 'darwin':
        user_data_dir = Path.home() / 'Library' / 'Application Support' / 'GradingApp'
    else:  # Linux
        user_data_dir = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'GradingApp'

    # Create logs directory
    log_dir = user_data_dir / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    root_logger.handlers.clear()

    # 1. Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Main app log (DEBUG and above)
    app_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=5_000_000,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # 3. Flask log (Flask and Werkzeug only)
    flask_handler = RotatingFileHandler(
        log_dir / 'flask.log',
        maxBytes=5_000_000,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    flask_handler.setLevel(logging.DEBUG)
    flask_handler.setFormatter(formatter)

    # Add to Flask loggers
    logging.getLogger('werkzeug').addHandler(flask_handler)
    logging.getLogger('flask').addHandler(flask_handler)

    # 4. Updates log (updater module only)
    updates_handler = RotatingFileHandler(
        log_dir / 'updates.log',
        maxBytes=5_000_000,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    updates_handler.setLevel(logging.DEBUG)
    updates_handler.setFormatter(formatter)
    logging.getLogger('desktop.updater').addHandler(updates_handler)

    # 5. Errors log (ERROR and above only)
    error_handler = RotatingFileHandler(
        log_dir / 'errors.log',
        maxBytes=5_000_000,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    logger.info(f"Logging configured - logs directory: {log_dir}")
    logger.debug("Log files created: app.log, flask.log, updates.log, errors.log")


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
                       width: int = 1280, height: int = 800,
                       start_hidden: bool = False) -> 'webview.Window':
    """
    Create the main PyWebView window.

    This function creates the window but does NOT start the webview event loop.
    The caller must call webview.start() to begin the event loop.

    Args:
        url: URL to display in the window (e.g., 'http://127.0.0.1:5050')
        title: Window title (default: "Grading App")
        width: Initial window width in pixels (default: 1280)
        height: Initial window height in pixels (default: 800)
        start_hidden: If True, window starts hidden (default: False)

    Returns:
        webview.Window: The created window instance

    Raises:
        ImportError: If PyWebView is not installed

    Note:
        This function creates the window but does not block.
        Call webview.start() separately to start the event loop.
    """
    try:
        import webview
        logger.info(f"Creating PyWebView window: {title} ({width}x{height})")
        logger.info(f"Window will start {'hidden' if start_hidden else 'visible'}")

        # Wait a moment for Flask to start before opening window
        time.sleep(0.5)

        # Create window (does not start event loop)
        window = webview.create_window(
            title=title,
            url=url,
            width=width,
            height=height,
            hidden=start_hidden
        )

        logger.info(f"PyWebView window created")
        return window

    except ImportError as e:
        logger.error(
            f"PyWebView not installed: {e}\n"
            "Install with: pip install pywebview>=4.0.0"
        )
        raise
    except Exception as e:
        logger.error(f"Error creating window: {e}")
        raise


def shutdown_gracefully(tray_icon=None) -> None:
    """
    Perform graceful shutdown of the application.

    This function:
    1. Stops the system tray icon (if running)
    2. Shuts down the task queue (waits for running tasks)
    3. Stops the periodic task scheduler
    4. Logs shutdown completion

    Args:
        tray_icon: Optional pystray.Icon instance to stop

    Note:
        Flask server will stop automatically when the main thread exits
        (since it's running in a daemon thread).
    """
    logger.info("Initiating graceful shutdown...")

    try:
        # Stop system tray icon first
        if tray_icon:
            logger.info("Stopping system tray icon...")
            tray_icon.stop()
            logger.info("System tray stopped")
    except Exception as e:
        logger.error(f"Error stopping system tray: {e}")

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
        1. Install crash handler
        2. Configure Flask app for desktop deployment
        3. Initialize database
        4. Start periodic task scheduler
        5. Get an available port
        6. Start Flask server in background thread
        7. Create PyWebView window
        8. Handle graceful shutdown on exit

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Install crash handler first (before any other code)
    setup_crash_handler()

    # Configure logging system
    setup_logging()

    try:
        logger.info("=" * 60)
        logger.info("Starting Grading App Desktop Application")
        logger.info(f"Version: {__version__}")
        logger.info("=" * 60)

        # Cleanup old crash logs (keep last 30 days)
        cleanup_old_crash_logs(days=30)

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

            # Schedule automatic backups based on settings
            from desktop.scheduler import schedule_automatic_backup
            schedule_automatic_backup()
            logger.info("Automatic backup scheduling configured")
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

        # Get UI settings
        start_minimized = settings.get('ui.start_minimized', False)
        show_tray = settings.get('ui.show_in_system_tray', True)

        # Create main window
        logger.info("Creating main window...")
        window = create_main_window(
            url=flask_url,
            title=f"Grading App v{__version__}",
            width=1280,
            height=800,
            start_hidden=start_minimized
        )

        # Create system tray if enabled
        tray_icon = None
        if show_tray:
            logger.info("Creating system tray icon...")
            try:
                from desktop.window_manager import create_system_tray

                def on_quit():
                    """Quit callback for system tray."""
                    logger.info("Quit requested from system tray")
                    import sys
                    sys.exit(0)

                # Build URLs for menu items
                settings_url = f"{flask_url}/desktop/settings"
                data_url = f"{flask_url}/desktop/data"

                # Create tray icon (doesn't block - returns icon instance)
                tray_icon = create_system_tray(
                    window=window,
                    on_quit=on_quit,
                    settings_url=settings_url,
                    data_url=data_url,
                    start_hidden=start_minimized
                )

                if tray_icon:
                    # Start tray in background thread
                    tray_thread = threading.Thread(
                        target=tray_icon.run,
                        daemon=True,
                        name="SystemTrayThread"
                    )
                    tray_thread.start()
                    logger.info("System tray icon started in background thread")
                else:
                    logger.warning("System tray icon creation failed, continuing without tray")

            except Exception as e:
                logger.error(f"Failed to create system tray: {e}")
                logger.warning("Continuing without system tray functionality")

        # Start webview event loop (blocks until window closed)
        import webview
        logger.info("Starting PyWebView event loop...")
        webview.start()
        logger.info("PyWebView window closed")

        # Window closed - perform graceful shutdown
        shutdown_gracefully(tray_icon=tray_icon)

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
