#!/usr/bin/env bash
# Test script for desktop app
# This verifies that all required dependencies are available

echo "Testing desktop app dependencies..."
echo ""

# Test Python imports
echo "1. Testing Python imports..."
python -c "
import sys
missing = []

try:
    import keyring
    print('  ✓ keyring')
except ImportError:
    print('  ✗ keyring')
    missing.append('keyring')

try:
    import apscheduler
    print('  ✓ apscheduler')
except ImportError:
    print('  ✗ apscheduler')
    missing.append('apscheduler')

try:
    import pystray
    print('  ✓ pystray')
except ImportError:
    print('  ✗ pystray')
    missing.append('pystray')

try:
    import webview
    print('  ✓ pywebview')
except ImportError:
    print('  ✗ pywebview')
    missing.append('pywebview')

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk, WebKit2
    print('  ✓ GTK3 + WebKit2')
except (ImportError, ValueError) as e:
    print(f'  ✗ GTK3/WebKit2: {e}')
    missing.append('gtk3/webkit2')

if missing:
    print('')
    print('ERROR: Missing dependencies:', ', '.join(missing))
    print('')
    print('To fix:')
    print('  1. Exit your current shell')
    print('  2. Run: nix-shell')
    print('  3. Try again')
    sys.exit(1)
else:
    print('')
    print('✓ All dependencies available!')
    print('')
    print('You can now run:')
    print('  python desktop/main.py')
" || exit 1

echo ""
echo "2. Testing desktop app initialization..."
timeout 5 python desktop/main.py 2>&1 | head -30 &
PID=$!

sleep 3
kill $PID 2>/dev/null

echo ""
echo "✓ Desktop app initialization test complete!"
echo ""
echo "To run the full desktop app:"
echo "  python desktop/main.py"
