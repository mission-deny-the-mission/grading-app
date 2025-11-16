"""
Unit tests for desktop main entry point.

Tests cover:
- start_flask() function starts Flask correctly
- create_main_window() is called with correct parameters
- Graceful shutdown handling
- Integration with app_wrapper configuration
- Error handling and logging
"""

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call, Mock

import pytest

# Mock webview and keyring before importing desktop modules
mock_webview = MagicMock()
sys.modules['webview'] = mock_webview
sys.modules['keyring'] = MagicMock()
sys.modules['keyrings'] = MagicMock()
sys.modules['keyrings.cryptfile'] = MagicMock()
sys.modules['keyrings.cryptfile.cryptfile'] = MagicMock()


class TestStartFlask:
    """Test suite for start_flask() function."""

    @patch('desktop.main.app')
    def test_start_flask_with_defaults(self, mock_app):
        """Test that start_flask() calls app.run() with default parameters."""
        from desktop.main import start_flask

        # Create a mock that will stop Flask quickly
        def mock_run(*args, **kwargs):
            # Verify parameters
            assert kwargs['host'] == '127.0.0.1'
            assert kwargs['port'] == 5050
            assert kwargs['debug'] is False
            assert kwargs['use_reloader'] is False
            assert kwargs['threaded'] is True

        mock_app.run.side_effect = mock_run

        # Run in a thread with timeout to prevent hanging
        thread = threading.Thread(target=start_flask)
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)

        # Verify app.run was called
        mock_app.run.assert_called_once()

    @patch('desktop.main.app')
    def test_start_flask_with_custom_params(self, mock_app):
        """Test that start_flask() accepts custom host, port, and debug parameters."""
        from desktop.main import start_flask

        def mock_run(*args, **kwargs):
            assert kwargs['host'] == '0.0.0.0'
            assert kwargs['port'] == 8080
            assert kwargs['debug'] is True

        mock_app.run.side_effect = mock_run

        thread = threading.Thread(target=start_flask, args=('0.0.0.0', 8080, True))
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)

        mock_app.run.assert_called_once()

    @patch('desktop.main.app')
    @patch('desktop.main.logger')
    def test_start_flask_logs_startup(self, mock_logger, mock_app):
        """Test that start_flask() logs startup message."""
        from desktop.main import start_flask

        mock_app.run.side_effect = lambda **kwargs: None

        thread = threading.Thread(target=start_flask)
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)

        # Verify startup message was logged
        mock_logger.info.assert_any_call('Starting Flask server on 127.0.0.1:5050')

    @patch('desktop.main.app')
    @patch('desktop.main.logger')
    def test_start_flask_handles_errors(self, mock_logger, mock_app):
        """Test that start_flask() logs errors and raises them."""
        from desktop.main import start_flask

        test_error = RuntimeError("Test error")
        mock_app.run.side_effect = test_error

        with pytest.raises(RuntimeError, match="Test error"):
            start_flask()

        # Verify error was logged
        mock_logger.error.assert_called_once()


class TestCreateMainWindow:
    """Test suite for create_main_window() function."""

    @patch('time.sleep')
    def test_create_window_with_defaults(self, mock_sleep):
        """Test that create_main_window() creates window with default parameters."""
        from desktop.main import create_main_window
        import webview

        # Reset the mock
        webview.create_window.reset_mock()
        webview.start.reset_mock()

        create_main_window('http://127.0.0.1:5050')

        # Verify sleep was called to wait for Flask
        mock_sleep.assert_called_once_with(0.5)

        # Verify window was created with defaults
        webview.create_window.assert_called_once_with(
            title='Grading App',
            url='http://127.0.0.1:5050',
            width=1280,
            height=800
        )

        # Verify webview was started
        webview.start.assert_called_once()

    @patch('time.sleep')
    def test_create_window_with_custom_params(self, mock_sleep):
        """Test that create_main_window() accepts custom parameters."""
        from desktop.main import create_main_window
        import webview

        webview.create_window.reset_mock()
        webview.start.reset_mock()

        create_main_window(
            url='http://localhost:8080',
            title='Custom App',
            width=1920,
            height=1080
        )

        webview.create_window.assert_called_once_with(
            title='Custom App',
            url='http://localhost:8080',
            width=1920,
            height=1080
        )

    @patch('desktop.main.logger')
    def test_create_window_logs_creation(self, mock_logger):
        """Test that create_main_window() logs window creation."""
        from desktop.main import create_main_window
        import webview

        webview.create_window.reset_mock()
        webview.start.reset_mock()

        create_main_window('http://127.0.0.1:5050', title='Test App', width=1024, height=768)

        # Verify creation was logged
        mock_logger.info.assert_any_call('Creating PyWebView window: Test App (1024x768)')
        mock_logger.info.assert_any_call('PyWebView window closed')

    @patch('desktop.main.logger')
    def test_create_window_handles_webview_errors(self, mock_logger):
        """Test that create_main_window() handles webview errors."""
        from desktop.main import create_main_window
        import webview

        # Make webview.start() raise an error
        test_error = RuntimeError("Window creation failed")
        webview.create_window.reset_mock()
        webview.start.reset_mock()
        webview.start.side_effect = test_error

        with pytest.raises(RuntimeError, match="Window creation failed"):
            create_main_window('http://127.0.0.1:5050')

        # Verify error was logged
        mock_logger.error.assert_called()

        # Reset side effect for other tests
        webview.start.side_effect = None


class TestShutdownGracefully:
    """Test suite for shutdown_gracefully() function."""

    @patch('desktop.main.task_queue')
    @patch('desktop.main.logger')
    def test_shutdown_calls_task_queue_shutdown(self, mock_logger, mock_task_queue):
        """Test that shutdown_gracefully() calls task_queue.shutdown()."""
        from desktop.main import shutdown_gracefully

        shutdown_gracefully()

        # Verify task queue shutdown was called with correct parameters
        mock_task_queue.shutdown.assert_called_once_with(wait=True, timeout=30)

        # Verify logging
        mock_logger.info.assert_any_call('Initiating graceful shutdown...')
        mock_logger.info.assert_any_call('Shutting down task queue...')
        mock_logger.info.assert_any_call('Task queue shutdown complete')
        mock_logger.info.assert_any_call('Graceful shutdown complete')

    @patch('desktop.main.task_queue')
    @patch('desktop.main.logger')
    def test_shutdown_handles_task_queue_errors(self, mock_logger, mock_task_queue):
        """Test that shutdown_gracefully() handles task queue errors gracefully."""
        from desktop.main import shutdown_gracefully

        # Make task_queue.shutdown raise an error
        test_error = RuntimeError("Task queue error")
        mock_task_queue.shutdown.side_effect = test_error

        # Should not raise, just log the error
        shutdown_gracefully()

        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert 'Error during task queue shutdown' in str(mock_logger.error.call_args)

        # Reset for other tests
        mock_task_queue.shutdown.side_effect = None


class TestMainFunction:
    """Test suite for main() function."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.get_free_port')
    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_main_success_flow(self, mock_get_user_data_dir, mock_thread_class,
                               mock_app, mock_shutdown, mock_configure,
                               mock_get_port, mock_create_window):
        """Test successful execution flow of main() function."""
        from desktop.main import main
        from models import db

        # Setup mocks
        mock_get_user_data_dir.return_value = Path('/tmp/test')
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

            # Verify database initialization
            mock_create_all.assert_called_once()

        # Verify exit code is 0 (success)
        assert result == 0

        # Verify configuration was called
        mock_configure.assert_called_once_with(mock_app)

        # Verify port was obtained
        mock_get_port.assert_called_once()

        # Verify Flask thread was created and started
        mock_thread_class.assert_called_once()
        thread_kwargs = mock_thread_class.call_args[1]
        assert thread_kwargs['daemon'] is True
        assert thread_kwargs['name'] == 'FlaskServerThread'
        mock_thread.start.assert_called_once()

        # Verify window was created
        mock_create_window.assert_called_once_with(
            url='http://127.0.0.1:5050',
            title='Grading App',
            width=1280,
            height=800
        )

        # Verify shutdown was called
        mock_shutdown.assert_called_once()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.get_free_port')
    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    def test_main_keyboard_interrupt(self, mock_thread_class, mock_app,
                                     mock_shutdown, mock_configure,
                                     mock_get_port, mock_create_window):
        """Test that main() handles KeyboardInterrupt gracefully."""
        from desktop.main import main
        from models import db

        # Setup mocks
        mock_get_port.return_value = 5050
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Make create_window raise KeyboardInterrupt
        mock_create_window.side_effect = KeyboardInterrupt()

        # Mock database and get_user_data_dir
        with patch.object(db, 'create_all'):
            with patch('desktop.main.get_user_data_dir'):
                result = main()

        # Verify exit code is 0 (clean exit)
        assert result == 0

        # Verify shutdown was called
        mock_shutdown.assert_called_once()

    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    def test_main_handles_fatal_errors(self, mock_app, mock_shutdown, mock_configure):
        """Test that main() handles fatal errors and returns error code."""
        from desktop.main import main

        # Make configuration raise an error
        test_error = RuntimeError("Configuration failed")
        mock_configure.side_effect = test_error

        result = main()

        # Verify exit code is 1 (error)
        assert result == 1

        # Verify shutdown was still called
        mock_shutdown.assert_called_once()

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.get_free_port')
    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.logger')
    @patch('desktop.main.get_user_data_dir')
    def test_main_logs_progress(self, mock_get_user_data_dir, mock_logger,
                                mock_thread_class, mock_app, mock_shutdown,
                                mock_configure, mock_get_port, mock_create_window):
        """Test that main() logs progress messages."""
        from desktop.main import main
        from models import db

        # Setup mocks
        mock_get_user_data_dir.return_value = Path('/tmp/test')
        mock_get_port.return_value = 5050
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Mock database
        with patch.object(db, 'create_all'):
            main()

        # Verify key log messages
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        log_text = ' '.join(log_calls)

        assert 'Starting Grading App Desktop Application' in log_text
        assert 'Configuring Flask app for desktop deployment' in log_text
        assert 'Initializing database' in log_text
        assert 'Flask server thread started' in log_text
        assert 'Creating main window' in log_text
        assert 'Application exited successfully' in log_text


class TestIntegrationWithAppWrapper:
    """Test suite for integration with app_wrapper module."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    def test_configure_app_called_before_flask_start(self, mock_thread_class,
                                                     mock_app, mock_shutdown,
                                                     mock_create_window):
        """Test that configure_app_for_desktop() is called before Flask starts."""
        from desktop.main import main
        from models import db

        # Track call order
        call_order = []

        def track_configure(app):
            call_order.append('configure')
            return app

        def track_thread(*args, **kwargs):
            call_order.append('thread_create')
            mock_thread = MagicMock()

            def track_start():
                call_order.append('thread_start')
            mock_thread.start = track_start

            return mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Setup mocks with tracking
        with patch('desktop.main.configure_app_for_desktop', side_effect=track_configure):
            with patch('desktop.main.get_free_port', return_value=5050):
                with patch('desktop.main.get_user_data_dir', return_value=Path('/tmp/test')):
                    with patch.object(db, 'create_all'):
                        mock_thread_class.side_effect = track_thread
                        main()

        # Verify configure was called before thread creation and start
        assert call_order.index('configure') < call_order.index('thread_create')
        assert call_order.index('thread_create') < call_order.index('thread_start')

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_user_data_dir_logged(self, mock_get_user_data_dir, mock_thread_class,
                                  mock_app, mock_shutdown, mock_create_window):
        """Test that user data directory is logged."""
        from desktop.main import main
        from models import db

        # Setup mocks
        test_path = Path('/home/testuser/.local/share/GradingApp')
        mock_get_user_data_dir.return_value = test_path
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=5050):
                with patch.object(db, 'create_all'):
                    with patch('desktop.main.logger') as mock_logger:
                        main()

        # Verify user data directory was logged
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        log_text = ' '.join(log_calls)
        assert str(test_path) in log_text


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.logger')
    def test_database_init_failure_logged(self, mock_logger, mock_configure):
        """Test that database initialization failures are logged."""
        from desktop.main import main
        from models import db

        # Make database initialization fail
        with patch('desktop.main.app') as mock_app:
            mock_app_context = MagicMock()
            mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
            mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

            with patch.object(db, 'create_all', side_effect=RuntimeError("DB error")):
                with patch('desktop.main.shutdown_gracefully'):
                    result = main()

        # Verify error code
        assert result == 1

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('desktop.main.get_free_port')
    @patch('desktop.main.configure_app_for_desktop')
    @patch('desktop.main.logger')
    def test_port_allocation_failure_logged(self, mock_logger, mock_configure, mock_get_port):
        """Test that port allocation failures are logged."""
        from desktop.main import main
        from models import db

        # Make port allocation fail
        mock_get_port.side_effect = RuntimeError("No ports available")

        with patch('desktop.main.app') as mock_app:
            mock_app_context = MagicMock()
            mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
            mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

            with patch.object(db, 'create_all'):
                with patch('desktop.main.shutdown_gracefully'):
                    result = main()

        # Verify error code
        assert result == 1

        # Verify error was logged
        mock_logger.error.assert_called()
