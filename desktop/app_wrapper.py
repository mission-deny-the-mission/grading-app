"""
Desktop application wrapper utilities.

This module provides utilities for configuring the Flask application for desktop deployment,
including user data directory management, port allocation, and SQLite database configuration.
"""

import os
import sys
import socket
import logging
from pathlib import Path
from sqlalchemy import event
from sqlalchemy.engine import Engine

from . import credentials

logger = logging.getLogger(__name__)


def get_user_data_dir() -> Path:
    """
    Get platform-specific user data directory for the grading application.

    Returns:
        Path: Platform-specific user data directory
            - Windows: %APPDATA%/GradingApp
            - macOS: ~/Library/Application Support/GradingApp
            - Linux: ~/.local/share/GradingApp (or $XDG_DATA_HOME/GradingApp)

    Example:
        >>> data_dir = get_user_data_dir()
        >>> print(data_dir)
        PosixPath('/home/user/.local/share/GradingApp')
    """
    if sys.platform == 'win32':
        base = Path(os.getenv('APPDATA'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux and other Unix-like systems
        base = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    
    return base / 'GradingApp'


def get_free_port() -> int:
    """
    Find an available port for the Flask server.

    This function creates a temporary socket, binds it to an available port,
    retrieves the port number, and then closes the socket. The port should
    be available immediately after this function returns, though there's a
    small race condition window.

    Returns:
        int: An available port number (typically in the ephemeral range)

    Example:
        >>> port = get_free_port()
        >>> print(port)
        54321
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    """
    Set SQLite pragmas for optimal desktop performance.

    This function is called automatically when a new database connection is created.
    It configures SQLite for single-user desktop usage with optimal performance and safety.

    Pragma settings:
        - journal_mode=WAL: Write-Ahead Logging for better concurrency
        - synchronous=NORMAL: Balance between safety and speed
        - foreign_keys=ON: Enforce foreign key constraints
        - cache_size=10000: 10MB cache for better performance

    Args:
        dbapi_conn: Database API connection object
        connection_record: SQLAlchemy connection record (unused)
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
    cursor.execute("PRAGMA foreign_keys=ON")  # Enforce FK constraints
    cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
    cursor.close()


def configure_app_for_desktop(app):
    """
    Configure Flask app for desktop deployment.

    This function performs the following configuration steps:
    1. Initializes the keyring for secure credential storage
    2. Loads API keys from the OS credential manager into environment variables
    3. Configures SQLite database path in the user data directory
    4. Sets up SQLite pragma configuration for optimal performance
    5. Creates necessary directories (user data dir, uploads, logs)

    Args:
        app: Flask application instance

    Returns:
        Flask app: The configured Flask application

    Example:
        >>> from app import app
        >>> from desktop.app_wrapper import configure_app_for_desktop
        >>> app = configure_app_for_desktop(app)
        >>> app.run()

    Note:
        This function should be called before running the Flask application
        in desktop mode. It modifies the app configuration and environment
        variables.
    """
    # Initialize keyring
    credentials.initialize_keyring()
    logger.info("Keyring initialized for desktop deployment")

    # List of API provider keys to load
    providers = [
        "openrouter_api_key",
        "claude_api_key",
        "openai_api_key",
        "gemini_api_key",
        "nanogpt_api_key",
        "chutes_api_key",
        "zai_api_key",
    ]

    # Load API keys from OS credential manager into environment
    for provider in providers:
        api_key = credentials.get_api_key(provider)
        if api_key:
            # Convert to uppercase for environment variable
            env_var_name = provider.upper()
            os.environ[env_var_name] = api_key
            logger.info(f"Loaded {provider} from credential manager")
    
    # Get user data directory
    user_data_dir = get_user_data_dir()

    # Create necessary directories
    user_data_dir.mkdir(parents=True, exist_ok=True)
    (user_data_dir / 'uploads').mkdir(parents=True, exist_ok=True)
    (user_data_dir / 'logs').mkdir(parents=True, exist_ok=True)
    logger.info(f"User data directory: {user_data_dir}")

    # Configure SQLite database path
    # IMPORTANT: Override DATABASE_URL environment variable to force SQLite usage
    db_path = user_data_dir / 'grading.db'
    sqlite_uri = f'sqlite:///{db_path}'
    os.environ['DATABASE_URL'] = sqlite_uri  # Override env var
    app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
    logger.info(f"Database path: {db_path}")
    
    # Configure upload folder
    app.config['UPLOAD_FOLDER'] = str(user_data_dir / 'uploads')
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Set up SQLite pragma event listener only if using SQLite
    # This will be called for every new database connection
    if sqlite_uri.startswith('sqlite'):
        event.listen(Engine, "connect", _set_sqlite_pragmas)
        logger.info("SQLite pragma configuration enabled")
    else:
        logger.info("Non-SQLite database detected, skipping pragma configuration")
    
    return app
