"""
Pytest configuration for desktop tests.

This conftest sets up necessary mocks for desktop-specific dependencies
(webview, keyring, apscheduler) before any desktop modules are imported.
"""

import sys
from unittest.mock import MagicMock

# Mock webview, keyring, and apscheduler before any imports
# These mocks must be set up before any desktop modules are imported
sys.modules['webview'] = MagicMock()
sys.modules['keyring'] = MagicMock()
sys.modules['keyrings'] = MagicMock()
sys.modules['keyrings.cryptfile'] = MagicMock()
sys.modules['keyrings.cryptfile.cryptfile'] = MagicMock()
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()
