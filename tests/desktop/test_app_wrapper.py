"""
Unit tests for desktop app wrapper utilities.

Tests cover:
- get_user_data_dir() platform-specific paths
- get_free_port() availability
- configure_app_for_desktop() Flask app configuration
- Directory creation
- SQLite pragma configuration
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from flask import Flask
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

# Mock keyring before importing desktop modules
sys.modules['keyring'] = MagicMock()
sys.modules['keyrings'] = MagicMock()
sys.modules['keyrings.cryptfile'] = MagicMock()
sys.modules['keyrings.cryptfile.cryptfile'] = MagicMock()

from desktop.app_wrapper import (
    get_user_data_dir,
    get_free_port,
    configure_app_for_desktop,
    _set_sqlite_pragmas,
)


class TestGetUserDataDir:
    """Test suite for get_user_data_dir() function."""

    @patch('sys.platform', 'win32')
    @patch.dict(os.environ, {'APPDATA': 'C:\\Users\\TestUser\\AppData\\Roaming'})
    def test_windows_path(self):
        """Test that Windows returns correct APPDATA path."""
        result = get_user_data_dir()
        expected = Path('C:\\Users\\TestUser\\AppData\\Roaming') / 'GradingApp'
        assert result == expected

    @patch('sys.platform', 'darwin')
    @patch('pathlib.Path.home')
    def test_macos_path(self, mock_home):
        """Test that macOS returns correct Application Support path."""
        mock_home.return_value = Path('/Users/testuser')
        result = get_user_data_dir()
        expected = Path('/Users/testuser/Library/Application Support/GradingApp')
        assert result == expected

    @patch('sys.platform', 'linux')
    @patch('pathlib.Path.home')
    @patch.dict(os.environ, {}, clear=True)
    def test_linux_path_default(self, mock_home):
        """Test that Linux returns correct ~/.local/share path by default."""
        mock_home.return_value = Path('/home/testuser')
        result = get_user_data_dir()
        expected = Path('/home/testuser/.local/share/GradingApp')
        assert result == expected

    @patch('sys.platform', 'linux')
    @patch.dict(os.environ, {'XDG_DATA_HOME': '/custom/data/dir'})
    def test_linux_path_xdg(self):
        """Test that Linux respects XDG_DATA_HOME when set."""
        result = get_user_data_dir()
        expected = Path('/custom/data/dir/GradingApp')
        assert result == expected

    @patch('sys.platform', 'freebsd')
    @patch('pathlib.Path.home')
    @patch.dict(os.environ, {}, clear=True)
    def test_unix_like_fallback(self, mock_home):
        """Test that other Unix-like systems use Linux path."""
        mock_home.return_value = Path('/usr/home/testuser')
        result = get_user_data_dir()
        expected = Path('/usr/home/testuser/.local/share/GradingApp')
        assert result == expected


class TestGetFreePort:
    """Test suite for get_free_port() function."""

    def test_returns_integer(self):
        """Test that get_free_port returns an integer."""
        port = get_free_port()
        assert isinstance(port, int)

    def test_port_in_valid_range(self):
        """Test that returned port is in valid range."""
        port = get_free_port()
        assert 1024 <= port <= 65535

    def test_port_is_available(self):
        """Test that returned port is actually available."""
        import socket
        
        port = get_free_port()
        
        # Try to bind to the port - should succeed if available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            s.listen(1)
            # If we get here, port was available

    def test_multiple_calls_return_different_ports(self):
        """Test that multiple calls return different ports."""
        ports = [get_free_port() for _ in range(5)]
        # At least some should be different (could be same by chance)
        assert len(set(ports)) > 1


class TestSetSqlitePragmas:
    """Test suite for _set_sqlite_pragmas() function."""

    def test_sets_all_pragmas(self):
        """Test that all required pragmas are set."""
        # Create a mock connection and cursor
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Call the function
        _set_sqlite_pragmas(mock_conn, None)
        
        # Verify all pragma commands were executed
        expected_calls = [
            call("PRAGMA journal_mode=WAL"),
            call("PRAGMA synchronous=NORMAL"),
            call("PRAGMA foreign_keys=ON"),
            call("PRAGMA cache_size=10000"),
        ]
        mock_cursor.execute.assert_has_calls(expected_calls)
        mock_cursor.close.assert_called_once()

    def test_pragma_execution_order(self):
        """Test that pragmas are executed in the correct order."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        _set_sqlite_pragmas(mock_conn, None)
        
        # Get the actual calls made
        calls = mock_cursor.execute.call_args_list
        
        # Extract the SQL commands
        sql_commands = [call[0][0] for call in calls]
        
        # Verify order
        assert sql_commands[0] == "PRAGMA journal_mode=WAL"
        assert sql_commands[1] == "PRAGMA synchronous=NORMAL"
        assert sql_commands[2] == "PRAGMA foreign_keys=ON"
        assert sql_commands[3] == "PRAGMA cache_size=10000"


class TestConfigureAppForDesktop:
    """Test suite for configure_app_for_desktop() function."""

    @pytest.fixture
    def mock_flask_app(self):
        """Create a mock Flask app for testing."""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
        return app

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_initializes_keyring(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that keyring is initialized."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        configure_app_for_desktop(mock_flask_app)

        mock_init_keyring.assert_called_once()

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_loads_api_keys_to_environment(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that API keys are loaded into environment variables."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.side_effect = lambda key: f"test-{key}-value" if key == "openrouter_api_key" else ""

        configure_app_for_desktop(mock_flask_app)

        # Verify API keys were queried
        assert mock_get_api_key.call_count == 7  # 7 providers

        # Verify environment variable was set for openrouter
        assert os.environ.get('OPENROUTER_API_KEY') == 'test-openrouter_api_key-value'

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_creates_directories(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that necessary directories are created."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        configure_app_for_desktop(mock_flask_app)

        # Verify directories exist
        assert temp_data_dir.exists()
        assert (temp_data_dir / 'uploads').exists()
        assert (temp_data_dir / 'logs').exists()

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_configures_database_path(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that database path is configured correctly."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        configure_app_for_desktop(mock_flask_app)

        expected_db_path = temp_data_dir / 'grading.db'
        assert mock_flask_app.config['SQLALCHEMY_DATABASE_URI'] == f'sqlite:///{expected_db_path}'

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_configures_upload_folder(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that upload folder is configured correctly."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        configure_app_for_desktop(mock_flask_app)

        expected_upload_folder = str(temp_data_dir / 'uploads')
        assert mock_flask_app.config['UPLOAD_FOLDER'] == expected_upload_folder

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_sets_up_sqlite_pragma_listener(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that SQLite pragma event listener is registered."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        configure_app_for_desktop(mock_flask_app)

        # Verify event listener was registered
        mock_event_listen.assert_called_once()
        args = mock_event_listen.call_args[0]
        assert args[0] == Engine
        assert args[1] == "connect"
        assert args[2] == _set_sqlite_pragmas

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_returns_app(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that the function returns the app instance."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        result = configure_app_for_desktop(mock_flask_app)

        assert result is mock_flask_app

    @patch('desktop.app_wrapper.get_user_data_dir')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_handles_existing_directories(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_get_data_dir, mock_flask_app, temp_data_dir
    ):
        """Test that function handles already existing directories gracefully."""
        mock_get_data_dir.return_value = temp_data_dir
        mock_get_api_key.return_value = ""

        # Create directories beforehand
        (temp_data_dir / 'uploads').mkdir(parents=True)
        (temp_data_dir / 'logs').mkdir(parents=True)

        # Should not raise an error
        configure_app_for_desktop(mock_flask_app)

        # Directories should still exist
        assert (temp_data_dir / 'uploads').exists()
        assert (temp_data_dir / 'logs').exists()


class TestSqlitePragmaIntegration:
    """Integration tests for SQLite pragma configuration."""

    def test_pragmas_applied_to_real_connection(self):
        """Test that pragmas are actually applied to a real SQLite connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'

            # Create engine with event listener
            engine = create_engine(f'sqlite:///{db_path}')
            event.listen(Engine, "connect", _set_sqlite_pragmas)

            # Create a connection
            with engine.connect() as conn:
                # Check that pragmas were applied
                result = conn.execute(text("PRAGMA journal_mode")).fetchone()
                assert result[0].lower() == 'wal'

                result = conn.execute(text("PRAGMA synchronous")).fetchone()
                # NORMAL is typically represented as 1
                assert result[0] in (1, 'NORMAL', 'normal')

                result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
                assert result[0] == 1  # ON

                result = conn.execute(text("PRAGMA cache_size")).fetchone()
                # Should be 10000 or -10000 (negative means KB)
                assert abs(result[0]) == 10000
