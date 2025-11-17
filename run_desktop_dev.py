#!/usr/bin/env python3
"""
Development runner for desktop app that mocks missing dependencies.
This allows testing the desktop app without installing PyWebView, pystray, etc.
"""

import sys
from unittest.mock import MagicMock

# Mock dependencies that may not be installed
print("Setting up mocks for development mode...")

# Mock keyring with proper return values
mock_keyring = MagicMock()
mock_keyring.get_password = MagicMock(return_value="")  # Return empty string for API keys
mock_keyring.set_password = MagicMock(return_value=None)
mock_keyring.delete_password = MagicMock(return_value=None)
mock_keyring.get_keyring = MagicMock(return_value=MagicMock(__class__=MagicMock(__name__="MockKeyring")))

sys.modules['keyring'] = mock_keyring
sys.modules['keyrings'] = MagicMock()
sys.modules['keyrings.cryptfile'] = MagicMock()
sys.modules['keyrings.cryptfile.cryptfile'] = MagicMock()

# Mock PyWebView
mock_webview = MagicMock()
sys.modules['webview'] = mock_webview

# Mock pystray
sys.modules['pystray'] = MagicMock()

# Mock apscheduler
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()

# Mock tufup
sys.modules['tufup'] = MagicMock()
sys.modules['tufup.client'] = MagicMock()

print("✓ Mocks configured")

# Set environment variable for SQLite database (development mode)
import os
os.environ['DATABASE_URL'] = 'sqlite:///grading_app_dev.db'

print()
print("=" * 70)
print("DESKTOP APP - DEVELOPMENT MODE WITH MOCKS")
print("=" * 70)
print()
print("Note: PyWebView is mocked, so no window will appear.")
print("The Flask server will still start and you can access it via browser.")
print("Database: SQLite (grading_app_dev.db)")
print()
print("Press Ctrl+C to stop the server")
print("=" * 70)
print()

# Now import and run the desktop app
if __name__ == '__main__':
    import desktop.main
    desktop.main.main()
