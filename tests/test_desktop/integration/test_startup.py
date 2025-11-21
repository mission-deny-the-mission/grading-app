"""
Integration tests for application startup sequence.

Tests cover:
- Flask server startup in desktop window
- Database initialization on first run
- User data directory creation
- Settings file creation
- Full application startup sequence
- Port allocation and Flask server binding
"""

import sys
import threading
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call, Mock
import time

import pytest

# Mock webview, keyring, and apscheduler before importing desktop modules
mock_webview = MagicMock()
sys.modules['webview'] = mock_webview
sys.modules['keyring'] = MagicMock()
sys.modules['keyrings'] = MagicMock()
sys.modules['keyrings.cryptfile'] = MagicMock()
sys.modules['keyrings.cryptfile.cryptfile'] = MagicMock()
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()


class TestFullStartupSequence:
    """Test the complete application startup sequence."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.get_free_port')
    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_full_startup_creates_all_components(
        self, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_configure,
        mock_get_port, mock_create_window
    ):
        """Test that full startup creates all necessary components in correct order."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_get_port.return_value = 5050
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Mock database
        with patch.object(db, 'create_all') as mock_create_all:
            result = main()

        # Verify exit code
        assert result == 0

        # Verify call order
        # 1. Configure app
        mock_configure.assert_called_once_with(mock_app)

        # 2. Initialize database
        mock_create_all.assert_called_once()

        # 3. Get port
        mock_get_port.assert_called_once()

        # 4. Start Flask thread (and other background threads: system tray, update checker)
        assert mock_thread.start.call_count >= 1  # At least Flask thread started

        # 5. Create window
        mock_create_window.assert_called_once()

        # 6. Shutdown gracefully
        mock_shutdown.assert_called_once()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.get_free_port')
    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_startup_sequence_ordering(
        self, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_configure,
        mock_get_port, mock_create_window
    ):
        """Test that startup sequence follows correct order."""
        from desktop.main import main
        from models import db

        call_order = []

        # Track call order
        def track_configure(app):
            call_order.append('configure_app')
            return app

        def track_db_create():
            call_order.append('db_create_all')

        def track_get_port():
            call_order.append('get_port')
            return 5050

        def track_thread_create(*args, **kwargs):
            call_order.append('thread_create')
            mock_thread = MagicMock()
            def track_start():
                call_order.append('thread_start')
            mock_thread.start = track_start
            return mock_thread

        def track_create_window(*args, **kwargs):
            call_order.append('create_window')

        def track_shutdown():
            call_order.append('shutdown')

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_configure.side_effect = track_configure
        mock_get_port.side_effect = track_get_port
        mock_thread_class.side_effect = track_thread_create
        mock_create_window.side_effect = track_create_window
        mock_shutdown.side_effect = track_shutdown

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Mock database
        with patch.object(db, 'create_all', side_effect=track_db_create):
            main()

        # Verify correct order - key constraints (not exact order due to multiple threads)
        # 1. configure_app must be first
        assert call_order[0] == 'configure_app'
        # 2. db_create_all must come before window creation
        assert call_order.index('db_create_all') < call_order.index('create_window')
        # 3. get_port must come before window creation
        assert call_order.index('get_port') < call_order.index('create_window')
        # 4. At least one thread must be created and started before window
        thread_create_indices = [i for i, x in enumerate(call_order) if x == 'thread_create']
        thread_start_indices = [i for i, x in enumerate(call_order) if x == 'thread_start']
        assert len(thread_create_indices) >= 1
        assert len(thread_start_indices) >= 1
        assert min(thread_create_indices) < call_order.index('create_window')
        # 5. shutdown must be last
        assert call_order[-1] == 'shutdown'


class TestDatabaseInitialization:
    """Test database initialization during startup."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_database_created_on_first_run(
        self, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_create_window
    ):
        """Test that database is created on first run."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Mock database
        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=5050):
                with patch.object(db, 'create_all') as mock_create_all:
                    main()

        # Verify database initialization was called
        mock_create_all.assert_called_once()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.logger')
    def test_database_error_handling(
        self, mock_logger, mock_shutdown, mock_create_window
    ):
        """Test that database initialization errors are handled gracefully."""
        from desktop.main import main
        from models import db

        # Setup mocks to fail at database initialization
        with patch('desktop.main.app') as mock_app:
            mock_app_context = MagicMock()
            mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
            mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

            with patch('desktop.main.configure_app_for_desktop'):
                with patch.object(db, 'create_all', side_effect=RuntimeError("DB initialization failed")):
                    result = main()

        # Verify error code
        assert result == 1

        # Verify error was logged
        mock_logger.error.assert_called()

        # Verify shutdown was still called
        mock_shutdown.assert_called_once()


class TestUserDataDirectoryCreation:
    """Test user data directory creation during startup."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_user_data_directory_created(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_thread_class, mock_app, mock_shutdown, mock_create_window
    ):
        """Test that user data directory is created during startup."""
        from desktop.main import main
        from desktop.app_wrapper import configure_app_for_desktop
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        # Remove temp dir to test creation
        import shutil
        shutil.rmtree(temp_dir)

        mock_get_api_key.return_value = ""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Use real configure_app_for_desktop to test directory creation
        # Need to patch get_user_data_dir in app_wrapper where it's actually called
        with patch('desktop.app_wrapper.get_user_data_dir', return_value=temp_dir):
            with patch('desktop.main.get_user_data_dir', return_value=temp_dir):
                with patch('desktop.main.configure_app_for_desktop', wraps=configure_app_for_desktop):
                    with patch('desktop.main.get_free_port', return_value=5050):
                        with patch.object(db, 'create_all'):
                            main()

        # Verify directory was created
        assert temp_dir.exists()
        assert (temp_dir / 'uploads').exists()
        assert (temp_dir / 'logs').exists()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_subdirectories_created(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_thread_class, mock_app, mock_shutdown, mock_create_window
    ):
        """Test that all necessary subdirectories are created."""
        from desktop.main import main
        from desktop.app_wrapper import configure_app_for_desktop
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        import shutil
        shutil.rmtree(temp_dir)

        mock_get_api_key.return_value = ""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Need to patch get_user_data_dir in both locations
        with patch('desktop.app_wrapper.get_user_data_dir', return_value=temp_dir):
            with patch('desktop.main.get_user_data_dir', return_value=temp_dir):
                with patch('desktop.main.configure_app_for_desktop', wraps=configure_app_for_desktop):
                    with patch('desktop.main.get_free_port', return_value=5050):
                        with patch.object(db, 'create_all'):
                            main()

        # Verify all subdirectories exist
        assert temp_dir.exists()
        assert (temp_dir / 'uploads').exists()
        assert (temp_dir / 'logs').exists()


class TestSettingsFileCreation:
    """Test settings file creation during startup."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    def test_settings_file_created_on_first_run(
        self, mock_thread_class, mock_app, mock_shutdown, mock_create_window
    ):
        """Test that settings file is created on first run."""
        from desktop.settings import Settings
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        settings_path = temp_dir / 'settings.json'
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Create and load settings (simulating first run)
        settings = Settings(settings_path)
        settings.load()

        # Verify settings file was created
        assert settings_path.exists()

        # Verify default settings were written
        assert settings.get('version') is not None
        assert settings.get('ui.theme') == 'system'

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    def test_settings_file_loaded_on_subsequent_run(
        self, mock_thread_class, mock_app, mock_shutdown, mock_create_window
    ):
        """Test that existing settings file is loaded on subsequent runs."""
        from desktop.settings import Settings

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        settings_path = temp_dir / 'settings.json'
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # First run - create settings
        settings = Settings(settings_path)
        settings.load()
        settings.set('ui.theme', 'dark')
        settings.save()

        # Second run - load existing settings
        settings2 = Settings(settings_path)
        settings2.load()

        # Verify settings were loaded from file
        assert settings2.get('ui.theme') == 'dark'


class TestPortAllocationAndBinding:
    """Test port allocation and Flask server binding."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_free_port_allocated(
        self, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_create_window
    ):
        """Test that a free port is allocated for Flask server."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port') as mock_get_port:
                mock_get_port.return_value = 12345
                with patch.object(db, 'create_all'):
                    main()

        # Verify port was allocated
        mock_get_port.assert_called_once()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.get_user_data_dir')
    def test_flask_server_bound_to_allocated_port(
        self, mock_get_user_data_dir, mock_app, mock_shutdown, mock_create_window
    ):
        """Test that Flask server is bound to the allocated port."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir

        # Track thread creation
        thread_args = []

        def capture_thread(*args, **kwargs):
            thread_args.append((args, kwargs))
            mock_thread = MagicMock()
            return mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=12345):
                with patch('desktop.main.threading.Thread', side_effect=capture_thread):
                    with patch.object(db, 'create_all'):
                        main()

        # Verify threads were created (should have Flask server and possibly others)
        assert len(thread_args) >= 1

        # Find the Flask server thread specifically (by checking for FlaskServerThread name or start_flask target)
        flask_thread = None
        for args, kwargs in thread_args:
            if kwargs.get('name') == 'FlaskServerThread' or 'start_flask' in str(kwargs.get('target', '')):
                flask_thread = (args, kwargs)
                break

        assert flask_thread is not None, "Flask server thread should be created"
        args, kwargs = flask_thread

        # Check that Flask thread receives correct port
        # target should be start_flask, args should be (host, port, debug)
        flask_args = kwargs.get('args', args)
        assert 12345 in flask_args  # Port should be in the arguments

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_window_created_with_correct_url(
        self, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_create_window
    ):
        """Test that window is created with correct Flask URL."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=54321):
                with patch.object(db, 'create_all'):
                    main()

        # Verify window was created with correct URL
        mock_create_window.assert_called_once()
        call_kwargs = mock_create_window.call_args[1]
        assert call_kwargs['url'] == 'http://127.0.0.1:54321'


class TestFlaskServerStartup:
    """Test Flask server startup in desktop window."""

    @patch('desktop.main.app')
    def test_flask_server_starts_with_correct_config(self, mock_app):
        """Test that Flask server starts with correct configuration."""
        from desktop.main import start_flask

        # Create a flag to verify app.run was called
        run_called = []

        def mock_run(*args, **kwargs):
            run_called.append(kwargs)

        mock_app.run.side_effect = mock_run

        # Run in thread with timeout
        thread = threading.Thread(target=start_flask, args=('127.0.0.1', 5050, False))
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)

        # Verify app.run was called with correct parameters
        assert len(run_called) == 1
        config = run_called[0]
        assert config['host'] == '127.0.0.1'
        assert config['port'] == 5050
        assert config['debug'] is False
        assert config['use_reloader'] is False
        assert config['threaded'] is True

    @patch('desktop.main.app')
    @patch('desktop.main.logger')
    def test_flask_server_startup_logged(self, mock_logger, mock_app):
        """Test that Flask server startup is logged."""
        from desktop.main import start_flask

        mock_app.run.side_effect = lambda **kwargs: None

        thread = threading.Thread(target=start_flask, args=('localhost', 8080, False))
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)

        # Verify startup was logged
        mock_logger.info.assert_any_call('Starting Flask server on localhost:8080')

    @patch('desktop.main.app')
    @patch('desktop.main.logger')
    def test_flask_server_binds_to_localhost_only(self, mock_logger, mock_app):
        """Test that Flask server binds to localhost only by default."""
        from desktop.main import start_flask

        run_config = []

        def capture_run(**kwargs):
            run_config.append(kwargs)

        mock_app.run.side_effect = capture_run

        thread = threading.Thread(target=start_flask)
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)

        # Verify host is localhost/127.0.0.1
        assert len(run_config) == 1
        assert run_config[0]['host'] == '127.0.0.1'


class TestStartupErrorHandling:
    """Test error handling during startup."""

    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.logger')
    def test_configuration_error_handled(
        self, mock_logger, mock_shutdown, mock_configure
    ):
        """Test that configuration errors are handled gracefully."""
        from desktop.main import main

        # Make configuration fail
        mock_configure.side_effect = RuntimeError("Config error")

        result = main()

        # Verify error code
        assert result == 1

        # Verify error was logged
        mock_logger.error.assert_called()

        # Verify shutdown was called
        mock_shutdown.assert_called_once()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.logger')
    def test_port_allocation_error_handled(
        self, mock_logger, mock_thread_class, mock_app,
        mock_shutdown, mock_create_window
    ):
        """Test that port allocation errors are handled gracefully."""
        from desktop.main import main
        from models import db

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', side_effect=RuntimeError("No ports available")):
                with patch.object(db, 'create_all'):
                    result = main()

        # Verify error code
        assert result == 1

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    @patch('desktop.main.logger')
    def test_window_creation_error_handled(
        self, mock_logger, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_create_window
    ):
        """Test that window creation errors are handled gracefully."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Make window creation fail
        mock_create_window.side_effect = RuntimeError("Window creation failed")

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=5050):
                with patch.object(db, 'create_all'):
                    result = main()

        # Verify error code
        assert result == 1

        # Verify error was logged
        mock_logger.error.assert_called()

        # Verify shutdown was called
        mock_shutdown.assert_called_once()
