"""
Pytest configuration for desktop tests.

This conftest sets up necessary mocks for desktop-specific dependencies
(webview, keyring, apscheduler) before any desktop modules are imported.
"""

import sys
from unittest.mock import MagicMock
import pytest


def pytest_configure(config):
    """Configure pytest before test collection for desktop tests.
    
    Ensures sys.path is set before any desktop test modules are imported
    across all pytest-xdist workers.
    """
    sys.path.insert(0, '/workspace')


# Mark all desktop tests to run serially to avoid worker isolation issues
def pytest_collection_modifyitems(config, items):
    """Add serial execution marker to all desktop tests."""
    for item in items:
        if "desktop" in str(item.fspath):
            item.add_marker(pytest.mark.xdist_group("desktop_serial"))


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
