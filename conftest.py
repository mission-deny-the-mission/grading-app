"""
Root conftest.py for pytest configuration.

Ensures desktop/ and tests/desktop/ are available in the Python path.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add desktop module to Python path
desktop_path = project_root / "desktop"
if desktop_path.exists():
    sys.path.insert(0, str(desktop_path))

# Add tests/desktop to Python path
tests_desktop_path = project_root / "tests" / "desktop"
if tests_desktop_path.exists():
    sys.path.insert(0, str(tests_desktop_path))
