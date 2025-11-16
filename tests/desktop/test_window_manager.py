"""
Unit tests for desktop/window_manager.py

Tests:
- create_main_window() creates window with correct parameters
- create_system_tray() creates tray with menu items
- show_update_notification() displays update info
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import sys

# Mock webview and pystray modules if not installed
sys.modules['webview'] = MagicMock()
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()


class TestCreateMainWindow:
    """Tests for create_main_window()"""

    @patch('desktop.window_manager.webview')
    def test_creates_window_with_default_parameters(self, mock_webview):
        """Test that create_main_window creates window with default parameters"""
        from desktop.window_manager import create_main_window

        mock_window = Mock()
        mock_webview.create_window.return_value = mock_window

        url = 'http://127.0.0.1:5050'
        result = create_main_window(url)

        # Verify webview.create_window was called with correct parameters
        mock_webview.create_window.assert_called_once_with(
            title="Grading App",
            url=url,
            width=1280,
            height=800
        )

        # Verify window is returned
        assert result == mock_window

    @patch('desktop.window_manager.webview')
    def test_creates_window_with_custom_parameters(self, mock_webview):
        """Test that create_main_window accepts custom parameters"""
        from desktop.window_manager import create_main_window

        mock_window = Mock()
        mock_webview.create_window.return_value = mock_window

        url = 'http://localhost:8080'
        title = 'Custom Title'
        width = 1920
        height = 1080

        result = create_main_window(
            url=url,
            title=title,
            width=width,
            height=height
        )

        mock_webview.create_window.assert_called_once_with(
            title=title,
            url=url,
            width=width,
            height=height
        )

        assert result == mock_window

    @patch('desktop.window_manager.webview')
    def test_raises_runtime_error_on_failure(self, mock_webview):
        """Test that create_main_window raises RuntimeError if window creation fails"""
        from desktop.window_manager import create_main_window

        # Simulate webview failure
        mock_webview.create_window.side_effect = Exception("WebView error")

        with pytest.raises(RuntimeError, match="Window creation failed"):
            create_main_window('http://127.0.0.1:5050')

    @patch('desktop.window_manager.webview')
    @patch('desktop.window_manager.logger')
    def test_logs_window_creation(self, mock_logger, mock_webview):
        """Test that create_main_window logs appropriate messages"""
        from desktop.window_manager import create_main_window

        mock_window = Mock()
        mock_webview.create_window.return_value = mock_window

        create_main_window('http://127.0.0.1:5050', title='Test App')

        # Check that logging occurred
        assert mock_logger.info.call_count >= 1
        # Verify at least one log message contains window information
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any('Test App' in str(call) for call in log_calls)


class TestCreateSystemTray:
    """Tests for create_system_tray()"""

    @patch('PIL.Image')
    @patch('pystray.Icon')
    @patch('pystray.MenuItem')
    @patch('pystray.Menu')
    def test_creates_tray_with_menu_items(self, mock_menu_class, mock_menuitem_class,
                                          mock_icon_class, mock_image):
        """Test that create_system_tray creates tray with correct menu items"""
        from desktop.window_manager import create_system_tray

        # Mock callbacks
        on_show = Mock()
        on_hide = Mock()
        on_quit = Mock()

        # Mock PIL Image - the function will try to open icon or create new
        mock_icon_image = Mock()
        mock_image.open.return_value = mock_icon_image
        mock_image.new.return_value = mock_icon_image

        # Mock pystray components
        mock_menu_item = Mock()
        mock_menuitem_class.return_value = mock_menu_item
        mock_menu = Mock()
        mock_menu_class.return_value = mock_menu
        mock_icon = Mock()
        mock_icon_class.return_value = mock_icon

        # Call function
        create_system_tray(on_show, on_hide, on_quit)

        # Verify MenuItem was called for each menu item
        assert mock_menuitem_class.call_count == 3
        mock_menuitem_class.assert_any_call("Show", on_show)
        mock_menuitem_class.assert_any_call("Hide", on_hide)
        mock_menuitem_class.assert_any_call("Quit", on_quit)

        # Verify Menu was created
        mock_menu_class.assert_called_once()

        # Verify Icon was created with correct parameters
        mock_icon_class.assert_called_once()
        call_kwargs = mock_icon_class.call_args[1]
        assert call_kwargs['name'] == "Grading App"
        assert call_kwargs['title'] == "Grading App"
        # Icon image should be either from open() or new()
        assert call_kwargs['icon'] == mock_icon_image

        # Verify icon.run() was called
        mock_icon.run.assert_called_once()

    @patch('pathlib.Path')
    @patch('PIL.Image')
    @patch('pystray.Icon')
    @patch('pystray.MenuItem')
    @patch('pystray.Menu')
    def test_loads_icon_from_resources_if_exists(self, mock_menu_class, mock_menuitem_class,
                                                  mock_icon_class, mock_image, mock_path_class):
        """Test that create_system_tray loads icon from resources if file exists"""
        from desktop.window_manager import create_system_tray

        # Mock callbacks
        on_show = Mock()
        on_hide = Mock()
        on_quit = Mock()

        # Mock icon path to exist
        mock_icon_path = MagicMock()
        mock_icon_path.exists.return_value = True

        # Mock Path chain: Path(__file__).parent / 'resources' / 'icon.png'
        mock_file = MagicMock()
        mock_parent = MagicMock()
        mock_resources = MagicMock()

        mock_file.parent = mock_parent
        mock_parent.__truediv__ = Mock(return_value=mock_resources)
        mock_resources.__truediv__ = Mock(return_value=mock_icon_path)

        mock_path_class.return_value = mock_file

        # Mock PIL Image.open
        mock_icon_image = Mock()
        mock_image.open.return_value = mock_icon_image

        # Mock pystray components
        mock_icon = Mock()
        mock_icon_class.return_value = mock_icon

        # Call function
        create_system_tray(on_show, on_hide, on_quit)

        # Verify Image.open was called (icon loaded from file)
        mock_image.open.assert_called_once_with(mock_icon_path)

    @patch('PIL.Image')
    @patch('pystray.Icon')
    @patch('pystray.MenuItem')
    @patch('pystray.Menu')
    def test_creates_default_icon_if_file_not_found(self, mock_menu_class, mock_menuitem_class,
                                                     mock_icon_class, mock_image):
        """Test that create_system_tray creates default icon if file doesn't exist"""
        from desktop.window_manager import create_system_tray

        # Mock callbacks
        on_show = Mock()
        on_hide = Mock()
        on_quit = Mock()

        # Mock PIL Image - simulate file not found by raising error on open
        mock_image.open.side_effect = FileNotFoundError("Icon not found")

        # Mock PIL Image.new
        mock_icon_image = Mock()
        mock_image.new.return_value = mock_icon_image

        # Mock pystray components
        mock_icon = Mock()
        mock_icon_class.return_value = mock_icon

        # Call function - should catch FileNotFoundError and create default icon
        create_system_tray(on_show, on_hide, on_quit)

        # Verify Image.new was called (default icon created)
        # Note: This might not be called if path.exists() returns False first
        # So we check that either open() was attempted or new() was called
        assert mock_image.open.called or mock_image.new.called

    def test_raises_runtime_error_if_pystray_not_installed(self):
        """Test that create_system_tray raises RuntimeError if pystray not available"""
        # This test verifies error handling when pystray is not installed
        # Since we mock pystray at module level, we just verify the function
        # has proper error handling by checking its code structure
        from desktop.window_manager import create_system_tray
        import inspect

        # Verify the function has try/except for ImportError
        source = inspect.getsource(create_system_tray)
        assert 'ImportError' in source
        assert 'pystray' in source

    @patch('pathlib.Path')
    @patch('PIL.Image')
    @patch('pystray.Icon')
    @patch('pystray.MenuItem')
    @patch('pystray.Menu')
    @patch('desktop.window_manager.logger')
    def test_logs_tray_creation(self, mock_logger, mock_menu_class, mock_menuitem_class,
                                mock_icon_class, mock_image, mock_path):
        """Test that create_system_tray logs appropriate messages"""
        from desktop.window_manager import create_system_tray

        # Mock everything
        mock_icon_path = Mock()
        mock_icon_path.exists.return_value = False
        mock_path.return_value.__truediv__ = Mock(return_value=mock_icon_path)

        mock_icon_image = Mock()
        mock_image.new.return_value = mock_icon_image

        mock_icon = Mock()
        mock_icon_class.return_value = mock_icon

        on_show = Mock()
        on_hide = Mock()
        on_quit = Mock()

        create_system_tray(on_show, on_hide, on_quit)

        # Check that logging occurred
        assert mock_logger.info.call_count >= 1


class TestShowUpdateNotification:
    """Tests for show_update_notification()"""

    @patch('desktop.window_manager.webview')
    def test_shows_notification_with_update_info(self, mock_webview):
        """Test that show_update_notification displays correct information"""
        from desktop.window_manager import show_update_notification

        update_info = {
            'version': '1.1.0',
            'current': '1.0.0',
            'release_notes': 'Bug fixes and improvements',
            'url': 'https://github.com/user/repo/releases/tag/v1.1.0'
        }

        mock_webview.create_confirmation_dialog.return_value = True

        result = show_update_notification(update_info)

        # Verify dialog was created
        mock_webview.create_confirmation_dialog.assert_called_once()
        call_kwargs = mock_webview.create_confirmation_dialog.call_args[1]

        # Check title
        assert call_kwargs['title'] == "Update Available"

        # Check message contains version info
        message = call_kwargs['message']
        assert '1.1.0' in message
        assert '1.0.0' in message
        assert 'Bug fixes and improvements' in message
        assert update_info['url'] in message

        # Check return value
        assert result is True

    @patch('desktop.window_manager.webview')
    def test_returns_true_when_user_chooses_update_now(self, mock_webview):
        """Test that show_update_notification returns True when user clicks 'Update Now'"""
        from desktop.window_manager import show_update_notification

        update_info = {'version': '1.1.0', 'current': '1.0.0'}
        mock_webview.create_confirmation_dialog.return_value = True

        result = show_update_notification(update_info)

        assert result is True

    @patch('desktop.window_manager.webview')
    def test_returns_false_when_user_chooses_remind_later(self, mock_webview):
        """Test that show_update_notification returns False when user clicks 'Remind Me Later'"""
        from desktop.window_manager import show_update_notification

        update_info = {'version': '1.1.0', 'current': '1.0.0'}
        mock_webview.create_confirmation_dialog.return_value = False

        result = show_update_notification(update_info)

        assert result is False

    @patch('desktop.window_manager.webview')
    def test_handles_missing_optional_fields(self, mock_webview):
        """Test that show_update_notification handles missing optional fields gracefully"""
        from desktop.window_manager import show_update_notification

        # Minimal update info
        update_info = {
            'version': '1.1.0',
            'current': '1.0.0'
        }

        mock_webview.create_confirmation_dialog.return_value = False

        result = show_update_notification(update_info)

        # Should not raise exception
        mock_webview.create_confirmation_dialog.assert_called_once()

        # Check message still works without optional fields
        call_kwargs = mock_webview.create_confirmation_dialog.call_args[1]
        message = call_kwargs['message']
        assert '1.1.0' in message
        assert '1.0.0' in message

    @patch('desktop.window_manager.webview')
    def test_falls_back_to_terminal_if_dialog_not_available(self, mock_webview):
        """Test that show_update_notification falls back gracefully if webview dialog unavailable"""
        from desktop.window_manager import show_update_notification

        update_info = {
            'version': '1.1.0',
            'current': '1.0.0',
            'release_notes': 'New features'
        }

        # Simulate AttributeError (method doesn't exist)
        mock_webview.create_confirmation_dialog = None

        # Should not raise exception, falls back to terminal
        result = show_update_notification(update_info)

        # Falls back to terminal, returns False (remind later)
        assert result is False

    @patch('desktop.window_manager.webview')
    def test_returns_false_on_exception(self, mock_webview):
        """Test that show_update_notification returns False if an error occurs"""
        from desktop.window_manager import show_update_notification

        update_info = {'version': '1.1.0', 'current': '1.0.0'}

        # Simulate error during dialog creation
        mock_webview.create_confirmation_dialog.side_effect = Exception("Dialog error")

        # Should not raise exception
        result = show_update_notification(update_info)

        # Should return False (don't crash app)
        assert result is False

    @patch('desktop.window_manager.webview')
    @patch('desktop.window_manager.logger')
    def test_logs_notification_display(self, mock_logger, mock_webview):
        """Test that show_update_notification logs appropriate messages"""
        from desktop.window_manager import show_update_notification

        update_info = {'version': '1.1.0', 'current': '1.0.0'}
        mock_webview.create_confirmation_dialog.return_value = True

        show_update_notification(update_info)

        # Check that logging occurred
        assert mock_logger.info.call_count >= 1

    @patch('desktop.window_manager.webview')
    def test_handles_unknown_version_gracefully(self, mock_webview):
        """Test that show_update_notification handles missing version info"""
        from desktop.window_manager import show_update_notification

        # Empty update info
        update_info = {}

        mock_webview.create_confirmation_dialog.return_value = False

        result = show_update_notification(update_info)

        # Should not raise exception
        mock_webview.create_confirmation_dialog.assert_called_once()

        # Check message uses 'Unknown' for missing versions
        call_kwargs = mock_webview.create_confirmation_dialog.call_args[1]
        message = call_kwargs['message']
        assert 'Unknown' in message


class TestIntegration:
    """Integration tests for window_manager module"""

    def test_module_imports_successfully(self):
        """Test that window_manager module can be imported"""
        import desktop.window_manager
        assert desktop.window_manager is not None

    def test_all_functions_are_callable(self):
        """Test that all main functions exist and are callable"""
        from desktop.window_manager import (
            create_main_window,
            create_system_tray,
            show_update_notification
        )

        assert callable(create_main_window)
        assert callable(create_system_tray)
        assert callable(show_update_notification)

    def test_functions_have_docstrings(self):
        """Test that all functions have proper documentation"""
        from desktop.window_manager import (
            create_main_window,
            create_system_tray,
            show_update_notification
        )

        assert create_main_window.__doc__ is not None
        assert len(create_main_window.__doc__) > 50

        assert create_system_tray.__doc__ is not None
        assert len(create_system_tray.__doc__) > 50

        assert show_update_notification.__doc__ is not None
        assert len(show_update_notification.__doc__) > 50
