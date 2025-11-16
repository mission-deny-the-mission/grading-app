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
    2. Logs shutdown completion

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

    logger.info("Graceful shutdown complete")


def main() -> int:
    """
    Main entry point for the desktop application.

    Workflow:
        1. Configure Flask app for desktop deployment
        2. Initialize database
        3. Get an available port
        4. Start Flask server in background thread
        5. Create PyWebView window
        6. Handle graceful shutdown on exit

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
