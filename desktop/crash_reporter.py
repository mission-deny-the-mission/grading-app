"""
Crash reporter for desktop application.

This module provides opt-in crash reporting functionality:
- Global exception handler
- Crash log storage in user data directory
- Optional user-initiated reporting to GitHub
- Data obfuscation for privacy

Usage:
    from desktop.crash_reporter import setup_crash_handler

    setup_crash_handler()  # Install global exception handler
"""

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
import platform
import json

logger = logging.getLogger(__name__)


def get_crash_logs_dir() -> Path:
    """
    Get the directory for storing crash logs.

    Returns:
        Path to crash logs directory (creates if doesn't exist)
    """
    from desktop.app_wrapper import get_user_data_dir

    crash_dir = get_user_data_dir() / "crashes"
    crash_dir.mkdir(parents=True, exist_ok=True)
    return crash_dir


def obfuscate_sensitive_data(text: str) -> str:
    """
    Obfuscate potentially sensitive data in crash logs.

    This function removes:
    - Full file paths (keeps only filenames)
    - API keys (replaces with ****REDACTED****)
    - Usernames in paths

    Args:
        text: Raw crash log text

    Returns:
        Sanitized text with sensitive data removed
    """
    import re

    # Replace full paths with just filenames
    # Match common path patterns: /path/to/file.py or C:\path\to\file.py
    text = re.sub(r'[A-Za-z]?:?[/\\](?:[\w\-\.]+[/\\])+[\w\-\.]+\.py', '<redacted_path>', text)

    # Replace API keys (sk-..., sk-ant-..., etc.)
    text = re.sub(r'sk-[a-zA-Z0-9\-]{20,}', '****REDACTED****', text)
    text = re.sub(r'sk-ant-[a-zA-Z0-9\-]{20,}', '****REDACTED****', text)
    text = re.sub(r'sk-or-[a-zA-Z0-9\-]{20,}', '****REDACTED****', text)

    # Replace home directory paths
    home = str(Path.home())
    text = text.replace(home, '<HOME>')

    # Replace username patterns (common in Windows paths)
    text = re.sub(r'C:\\Users\\[^\\]+\\', 'C:\\Users\\<USER>\\', text)
    text = re.sub(r'/home/[^/]+/', '/home/<USER>/', text)
    text = re.sub(r'/Users/[^/]+/', '/Users/<USER>/', text)

    return text


def save_crash_log(
    exc_type: type,
    exc_value: BaseException,
    exc_traceback: traceback,
    app_version: str = "unknown"
) -> Optional[Path]:
    """
    Save crash information to local log file.

    Args:
        exc_type: Exception type
        exc_value: Exception instance
        exc_traceback: Exception traceback
        app_version: Application version string

    Returns:
        Path to saved crash log file, or None if save failed
    """
    try:
        crash_dir = get_crash_logs_dir()

        # Generate timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = crash_dir / f"crash_{timestamp}.log"

        # Collect system information
        system_info = {
            "timestamp": datetime.now().isoformat(),
            "app_version": app_version,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        }

        # Format exception
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)

        # Obfuscate sensitive data
        tb_text_safe = obfuscate_sensitive_data(tb_text)

        # Write crash log
        with open(crash_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("GRADING APP CRASH REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write("System Information:\n")
            f.write("-" * 40 + "\n")
            for key, value in system_info.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")

            f.write("Exception:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{exc_type.__name__}: {exc_value}\n\n")

            f.write("Traceback (sanitized):\n")
            f.write("-" * 40 + "\n")
            f.write(tb_text_safe)
            f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("Note: Paths and sensitive data have been redacted for privacy.\n")
            f.write("=" * 80 + "\n")

        logger.info(f"Crash log saved to: {crash_file}")
        return crash_file

    except Exception as e:
        logger.error(f"Failed to save crash log: {e}")
        return None


def prompt_user_for_report(crash_file: Path) -> bool:
    """
    Prompt user if they want to report the crash.

    This is a text-based prompt for now. In a GUI app, this would
    show a dialog box.

    Args:
        crash_file: Path to crash log file

    Returns:
        True if user wants to report, False otherwise
    """
    print("\n" + "=" * 80)
    print("CRASH DETECTED")
    print("=" * 80)
    print("\nThe application has encountered an unexpected error and needs to close.")
    print(f"\nA crash log has been saved to:\n{crash_file}")
    print("\nYou can help improve the application by reporting this crash.")
    print("The crash log contains system information but personal data has been")
    print("redacted for your privacy.")
    print("\nTo report this crash:")
    print("1. Go to: https://github.com/user/grading-app/issues")
    print("2. Create a new issue with the crash log contents")
    print("3. Describe what you were doing when the crash occurred")
    print("\n" + "=" * 80)

    # For automated/headless operation, don't prompt
    if not sys.stdin.isatty():
        return False

    try:
        response = input("\nWould you like to open the crash log now? (y/n): ").strip().lower()
        return response in ['y', 'yes']
    except (EOFError, KeyboardInterrupt):
        return False


def open_crash_log(crash_file: Path) -> None:
    """
    Open crash log file in default text editor.

    Args:
        crash_file: Path to crash log file
    """
    import subprocess
    import sys

    try:
        if sys.platform == 'win32':
            # Windows: Use notepad
            subprocess.run(['notepad', str(crash_file)])
        elif sys.platform == 'darwin':
            # macOS: Use open
            subprocess.run(['open', '-t', str(crash_file)])
        else:
            # Linux: Try xdg-open
            subprocess.run(['xdg-open', str(crash_file)])
    except Exception as e:
        logger.error(f"Failed to open crash log: {e}")
        print(f"Could not open crash log automatically. Please open: {crash_file}")


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for uncaught exceptions.

    This function:
    1. Logs the exception
    2. Saves crash log to disk
    3. Optionally prompts user to report (opt-in)

    Args:
        exc_type: Exception type
        exc_value: Exception instance
        exc_traceback: Exception traceback
    """
    # Ignore KeyboardInterrupt (Ctrl+C)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the exception
    logger.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

    # Try to get app version
    app_version = "unknown"
    try:
        from desktop import __version__
        app_version = __version__
    except ImportError:
        pass

    # Save crash log
    crash_file = save_crash_log(exc_type, exc_value, exc_traceback, app_version)

    # Prompt user (opt-in reporting)
    if crash_file:
        should_open = prompt_user_for_report(crash_file)
        if should_open:
            open_crash_log(crash_file)

    # Call default handler to still exit
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_crash_handler() -> None:
    """
    Install global exception handler for crash reporting.

    This should be called early in application startup, before
    any other code that might raise exceptions.

    Example:
        >>> from desktop.crash_reporter import setup_crash_handler
        >>> setup_crash_handler()
        >>> # Rest of application code...
    """
    sys.excepthook = global_exception_handler
    logger.info("Crash handler installed")


def cleanup_old_crash_logs(days: int = 30) -> int:
    """
    Delete crash logs older than specified number of days.

    Args:
        days: Number of days to keep crash logs (default: 30)

    Returns:
        Number of crash logs deleted
    """
    try:
        crash_dir = get_crash_logs_dir()
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        deleted_count = 0
        for crash_file in crash_dir.glob("crash_*.log"):
            if crash_file.stat().st_mtime < cutoff_time:
                crash_file.unlink()
                deleted_count += 1
                logger.debug(f"Deleted old crash log: {crash_file}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old crash log(s)")

        return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup old crash logs: {e}")
        return 0
