"""
Tests for desktop/crash_reporter.py - crash reporting functionality.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestObfuscateSensitiveData:
    """Test the obfuscate_sensitive_data function."""

    def test_obfuscates_api_keys(self):
        """Test that API keys are redacted."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        text = "Error with key sk-1234567890abcdefghij1234567890abcdefghij"
        result = obfuscate_sensitive_data(text)
        assert "sk-" not in result or "****REDACTED****" in result

    def test_obfuscates_anthropic_keys(self):
        """Test that Anthropic API keys are redacted."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        text = "Error with key sk-ant-1234567890abcdefghij1234567890abcdefghij"
        result = obfuscate_sensitive_data(text)
        assert "sk-ant-" not in result or "****REDACTED****" in result

    def test_obfuscates_openrouter_keys(self):
        """Test that OpenRouter API keys are redacted."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        text = "Error with key sk-or-1234567890abcdefghij1234567890abcdefghij"
        result = obfuscate_sensitive_data(text)
        assert "sk-or-" not in result or "****REDACTED****" in result

    def test_obfuscates_windows_user_paths(self):
        """Test that Windows user paths are obfuscated."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        text = "File at C:\\Users\\johndoe\\Documents\\file.py"
        result = obfuscate_sensitive_data(text)
        assert "johndoe" not in result

    def test_obfuscates_linux_user_paths(self):
        """Test that Linux user paths are obfuscated."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        text = "File at /home/johndoe/projects/file.txt"
        result = obfuscate_sensitive_data(text)
        assert "johndoe" not in result

    def test_obfuscates_macos_user_paths(self):
        """Test that macOS user paths are obfuscated."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        text = "File at /Users/johndoe/Desktop/script.py"
        result = obfuscate_sensitive_data(text)
        assert "johndoe" not in result

    def test_obfuscates_home_directory(self):
        """Test that home directory is replaced."""
        from desktop.crash_reporter import obfuscate_sensitive_data

        home = str(Path.home())
        text = f"Config at {home}/config.json"
        result = obfuscate_sensitive_data(text)
        assert home not in result
        assert "<HOME>" in result


class TestSaveCrashLog:
    """Test the save_crash_log function."""

    def test_saves_crash_log(self):
        """Test that crash log is saved successfully."""
        from desktop.crash_reporter import save_crash_log

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("desktop.crash_reporter.get_crash_logs_dir") as mock_dir:
                mock_dir.return_value = Path(tmpdir)

                try:
                    raise ValueError("Test error")
                except ValueError:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    result = save_crash_log(exc_type, exc_value, exc_traceback, "1.0.0")

                assert result is not None
                assert result.exists()
                content = result.read_text()
                assert "GRADING APP CRASH REPORT" in content
                assert "ValueError" in content
                assert "Test error" in content

    def test_handles_save_failure(self):
        """Test that save failure returns None."""
        from desktop.crash_reporter import save_crash_log

        with patch("desktop.crash_reporter.get_crash_logs_dir") as mock_dir:
            mock_dir.side_effect = PermissionError("Cannot create directory")

            try:
                raise ValueError("Test error")
            except ValueError:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                result = save_crash_log(exc_type, exc_value, exc_traceback, "1.0.0")

            assert result is None


class TestPromptUserForReport:
    """Test the prompt_user_for_report function."""

    def test_returns_false_for_non_tty(self):
        """Test that non-TTY environments return False."""
        from desktop.crash_reporter import prompt_user_for_report

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            result = prompt_user_for_report(Path("/tmp/crash.log"))
            assert result is False

    def test_handles_yes_response(self):
        """Test that 'yes' response returns True."""
        from desktop.crash_reporter import prompt_user_for_report

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("builtins.input", return_value="y"):
                result = prompt_user_for_report(Path("/tmp/crash.log"))
                assert result is True

    def test_handles_no_response(self):
        """Test that 'no' response returns False."""
        from desktop.crash_reporter import prompt_user_for_report

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("builtins.input", return_value="n"):
                result = prompt_user_for_report(Path("/tmp/crash.log"))
                assert result is False

    def test_handles_keyboard_interrupt(self):
        """Test that KeyboardInterrupt returns False."""
        from desktop.crash_reporter import prompt_user_for_report

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("builtins.input", side_effect=KeyboardInterrupt()):
                result = prompt_user_for_report(Path("/tmp/crash.log"))
                assert result is False

    def test_handles_eof_error(self):
        """Test that EOFError returns False."""
        from desktop.crash_reporter import prompt_user_for_report

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("builtins.input", side_effect=EOFError()):
                result = prompt_user_for_report(Path("/tmp/crash.log"))
                assert result is False


class TestOpenCrashLog:
    """Test the open_crash_log function."""

    def test_opens_on_windows(self):
        """Test opening crash log on Windows."""
        from desktop.crash_reporter import open_crash_log

        with patch("sys.platform", "win32"):
            with patch("subprocess.run") as mock_run:
                open_crash_log(Path("/tmp/crash.log"))
                mock_run.assert_called_once()
                assert "notepad" in mock_run.call_args[0][0]

    def test_opens_on_macos(self):
        """Test opening crash log on macOS."""
        from desktop.crash_reporter import open_crash_log

        with patch("sys.platform", "darwin"):
            with patch("subprocess.run") as mock_run:
                open_crash_log(Path("/tmp/crash.log"))
                mock_run.assert_called_once()
                assert "open" in mock_run.call_args[0][0]

    def test_opens_on_linux(self):
        """Test opening crash log on Linux."""
        from desktop.crash_reporter import open_crash_log

        with patch("sys.platform", "linux"):
            with patch("subprocess.run") as mock_run:
                open_crash_log(Path("/tmp/crash.log"))
                mock_run.assert_called_once()
                assert "xdg-open" in mock_run.call_args[0][0]

    def test_handles_subprocess_error(self):
        """Test handling subprocess errors."""
        from desktop.crash_reporter import open_crash_log

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")
            # Should not raise
            open_crash_log(Path("/tmp/crash.log"))


class TestGlobalExceptionHandler:
    """Test the global_exception_handler function."""

    def test_ignores_keyboard_interrupt(self):
        """Test that KeyboardInterrupt is passed to default handler."""
        from desktop.crash_reporter import global_exception_handler

        with patch("sys.__excepthook__") as mock_hook:
            global_exception_handler(KeyboardInterrupt, KeyboardInterrupt(), None)
            mock_hook.assert_called_once()

    def test_saves_crash_log_on_exception(self):
        """Test that crash log is saved on exception."""
        from desktop.crash_reporter import global_exception_handler

        with patch("desktop.crash_reporter.save_crash_log") as mock_save:
            mock_save.return_value = None
            with patch("sys.__excepthook__"):
                try:
                    raise ValueError("Test error")
                except ValueError:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    global_exception_handler(exc_type, exc_value, exc_traceback)

                mock_save.assert_called_once()

    def test_prompts_user_when_crash_file_saved(self):
        """Test that user is prompted when crash file is saved."""
        from desktop.crash_reporter import global_exception_handler

        with patch("desktop.crash_reporter.save_crash_log") as mock_save:
            mock_save.return_value = Path("/tmp/crash.log")
            with patch("desktop.crash_reporter.prompt_user_for_report") as mock_prompt:
                mock_prompt.return_value = False
                with patch("sys.__excepthook__"):
                    try:
                        raise ValueError("Test error")
                    except ValueError:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        global_exception_handler(exc_type, exc_value, exc_traceback)

                    mock_prompt.assert_called_once()

    def test_opens_crash_log_when_user_agrees(self):
        """Test that crash log is opened when user agrees."""
        from desktop.crash_reporter import global_exception_handler

        with patch("desktop.crash_reporter.save_crash_log") as mock_save:
            mock_save.return_value = Path("/tmp/crash.log")
            with patch("desktop.crash_reporter.prompt_user_for_report") as mock_prompt:
                mock_prompt.return_value = True
                with patch("desktop.crash_reporter.open_crash_log") as mock_open:
                    with patch("sys.__excepthook__"):
                        try:
                            raise ValueError("Test error")
                        except ValueError:
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            global_exception_handler(exc_type, exc_value, exc_traceback)

                        mock_open.assert_called_once()


class TestSetupCrashHandler:
    """Test the setup_crash_handler function."""

    def test_installs_exception_handler(self):
        """Test that exception handler is installed."""
        from desktop.crash_reporter import setup_crash_handler, global_exception_handler

        original_hook = sys.excepthook
        try:
            setup_crash_handler()
            assert sys.excepthook == global_exception_handler
        finally:
            sys.excepthook = original_hook


class TestCleanupOldCrashLogs:
    """Test the cleanup_old_crash_logs function."""

    def test_deletes_old_logs(self):
        """Test that old crash logs are deleted."""
        from desktop.crash_reporter import cleanup_old_crash_logs
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("desktop.crash_reporter.get_crash_logs_dir") as mock_dir:
                mock_dir.return_value = Path(tmpdir)

                # Create an old crash log
                old_log = Path(tmpdir) / "crash_20200101_120000.log"
                old_log.write_text("Old crash")
                # Set modification time to 60 days ago
                old_time = time.time() - (60 * 24 * 60 * 60)
                import os
                os.utime(old_log, (old_time, old_time))

                # Create a recent crash log
                new_log = Path(tmpdir) / "crash_recent.log"
                new_log.write_text("Recent crash")

                deleted = cleanup_old_crash_logs(days=30)

                assert deleted == 1
                assert not old_log.exists()
                assert new_log.exists()

    def test_handles_cleanup_failure(self):
        """Test that cleanup failure returns 0."""
        from desktop.crash_reporter import cleanup_old_crash_logs

        with patch("desktop.crash_reporter.get_crash_logs_dir") as mock_dir:
            mock_dir.side_effect = PermissionError("Cannot access directory")
            result = cleanup_old_crash_logs()
            assert result == 0

    def test_returns_zero_when_no_old_logs(self):
        """Test that 0 is returned when no old logs exist."""
        from desktop.crash_reporter import cleanup_old_crash_logs

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("desktop.crash_reporter.get_crash_logs_dir") as mock_dir:
                mock_dir.return_value = Path(tmpdir)

                # Create only recent logs
                new_log = Path(tmpdir) / "crash_recent.log"
                new_log.write_text("Recent crash")

                deleted = cleanup_old_crash_logs(days=30)
                assert deleted == 0


class TestGetCrashLogsDir:
    """Test the get_crash_logs_dir function."""

    def test_creates_crash_dir(self):
        """Test that crash directory is created."""
        from desktop.crash_reporter import get_crash_logs_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("desktop.app_wrapper.get_user_data_dir") as mock_dir:
                mock_dir.return_value = Path(tmpdir)
                result = get_crash_logs_dir()
                assert result.exists()
                assert result.name == "crashes"
