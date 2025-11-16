# System Tray Integration

This document describes the system tray integration for the Grading App desktop application, implemented as part of Phase 7.

## Overview

The system tray provides quick access to common application functions without requiring the main window to be visible. This is especially useful for:

- Starting the app in the background (minimized to tray)
- Quickly showing/hiding the main window
- Accessing settings and data management
- Checking for updates
- Gracefully quitting the application

## Architecture

### Components

1. **Icon Resources** (`desktop/resources/`)
   - `icon.png` - Main application icon (64x64, color)
   - `icon_gray.png` - Inactive state icon (64x64, grayscale)
   - `icon_active.png` - Active state icon (64x64, highlighted)

2. **System Tray Module** (`desktop/window_manager.py`)
   - `create_system_tray()` - Creates and configures the system tray icon

3. **Main Application** (`desktop/main.py`)
   - Integrates system tray with window lifecycle
   - Manages tray startup/shutdown
   - Handles start minimized behavior

4. **Settings** (`desktop/settings.py`)
   - `ui.start_minimized` - Start app with window hidden
   - `ui.show_in_system_tray` - Enable/disable system tray

### Technology Stack

- **pystray** (≥0.19.0) - Cross-platform system tray library
- **PIL/Pillow** - Icon image handling
- **PyWebView** - Window show/hide functionality

## Features

### Menu Structure

The system tray menu provides the following options:

```
├─ Show Window / Hide Window (toggle, default action)
├─ ────────────────────────────── (separator)
├─ Settings
├─ Data Management
├─ Check for Updates
├─ ────────────────────────────── (separator)
├─ Help ▸
│  ├─ About
│  └─ View Logs
├─ ────────────────────────────── (separator)
└─ Quit
```

### Menu Actions

1. **Show Window / Hide Window**
   - **Action**: Toggle main window visibility
   - **Default**: Activated on left-click (platform-dependent)
   - **Behavior**:
     - Shows window if hidden
     - Hides window if visible
     - Text changes dynamically based on state

2. **Settings**
   - **Action**: Opens settings page in the application
   - **URL**: `/desktop/settings`
   - **Behavior**: Ensures window is visible before navigating

3. **Data Management**
   - **Action**: Opens data export/backup page
   - **URL**: `/desktop/data`
   - **Behavior**: Ensures window is visible before navigating

4. **Check for Updates**
   - **Action**: Manually trigger update check
   - **Behavior**:
     - Runs update check in background
     - Shows notification if update available
     - Logs "No updates available" if current

5. **Help > About**
   - **Action**: Shows version and app information
   - **Behavior**: Logs app version (can be extended with dialog)

6. **Help > View Logs**
   - **Action**: Opens logs directory in file manager
   - **Platform-specific**:
     - Windows: Uses `explorer`
     - macOS: Uses `open`
     - Linux: Uses `xdg-open`

7. **Quit**
   - **Action**: Gracefully exits the application
   - **Behavior**:
     - Stops system tray
     - Shuts down task queue
     - Stops scheduler
     - Exits with code 0

## Platform-Specific Behavior

### Windows
- **Icon Location**: System tray (bottom-right, usually near clock)
- **Menu Trigger**: Right-click shows context menu
- **Default Action**: Left-click toggles window visibility
- **Minimize Behavior**: Window can minimize to tray

### macOS
- **Icon Location**: Menu bar (top-right, near clock)
- **Menu Trigger**: Click icon shows dropdown menu
- **Appearance**: Uses native macOS styling
- **Note**: Icon rendering may differ from Windows/Linux

### Linux
- **Icon Location**: System tray or notification area
- **Compatibility**: Works with GNOME, KDE, XFCE
- **Menu Trigger**: Right-click shows context menu
- **Fallback**: If tray unavailable, app continues without tray

## Configuration

### Settings File

Settings are stored in `<user_data_dir>/settings.json`:

```json
{
  "ui": {
    "start_minimized": false,
    "show_in_system_tray": true,
    "theme": "system",
    "window_geometry": {
      "width": 1280,
      "height": 800,
      "x": 100,
      "y": 100,
      "maximized": false
    }
  }
}
```

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ui.start_minimized` | boolean | `false` | Start app with window hidden (only tray visible) |
| `ui.show_in_system_tray` | boolean | `true` | Enable system tray icon |

### Programmatic Access

```python
from desktop.settings import Settings
from pathlib import Path

settings = Settings(Path("settings.json"))
settings.load()

# Get settings
start_minimized = settings.get('ui.start_minimized', False)
show_tray = settings.get('ui.show_in_system_tray', True)

# Set settings
settings.set('ui.start_minimized', True)
settings.save()
```

## Usage

### Basic Usage

The system tray is automatically created when the application starts (if enabled in settings):

```python
from desktop.main import main
import sys

if __name__ == '__main__':
    sys.exit(main())
```

### Manual Control

For advanced use cases, you can manually control the system tray:

```python
import webview
import threading
from desktop.window_manager import create_system_tray

# Create window
window = webview.create_window('App', 'http://localhost:5050')

# Define quit callback
def on_quit():
    print("Quitting...")
    import sys
    sys.exit(0)

# Create system tray
tray_icon = create_system_tray(
    window=window,
    on_quit=on_quit,
    settings_url="http://localhost:5050/desktop/settings",
    data_url="http://localhost:5050/desktop/data",
    start_hidden=False
)

# Start tray in background thread
if tray_icon:
    tray_thread = threading.Thread(
        target=tray_icon.run,
        daemon=True
    )
    tray_thread.start()

# Start webview
webview.start()
```

### Start Minimized

To start the app minimized to tray:

1. **Via Settings File**:
   ```json
   {
     "ui": {
       "start_minimized": true
     }
   }
   ```

2. **Via Code**:
   ```python
   settings.set('ui.start_minimized', True)
   settings.save()
   ```

3. **Via Command Line** (future):
   ```bash
   ./GradingApp --minimized
   ```

## Implementation Details

### Window Visibility Tracking

The system tray maintains window visibility state:

```python
window_visible = not start_hidden  # Initial state

def on_toggle_window(icon_obj, item):
    """Toggle window visibility."""
    if window_visible:
        on_hide_window(icon_obj, item)
    else:
        on_show_window(icon_obj, item)
```

### Dynamic Menu Text

The toggle menu item text changes based on state:

```python
def get_toggle_text(item):
    """Dynamic text for toggle menu item."""
    return "Hide Window" if window_visible else "Show Window"

pystray.MenuItem(
    get_toggle_text,
    on_toggle_window,
    default=True
)
```

### Icon Loading

Icons are loaded with fallback to default:

```python
icon_path = Path(__file__).parent / 'resources' / 'icon.png'

if icon_path.exists():
    icon_image = Image.open(icon_path)
else:
    # Create default icon
    icon_image = Image.new('RGB', (64, 64), color='white')
```

### Thread Safety

The system tray runs in a background daemon thread:

```python
tray_thread = threading.Thread(
    target=tray_icon.run,
    daemon=True,  # Auto-exits when main thread exits
    name="SystemTrayThread"
)
tray_thread.start()
```

### Graceful Shutdown

The tray is stopped during shutdown:

```python
def shutdown_gracefully(tray_icon=None):
    if tray_icon:
        logger.info("Stopping system tray icon...")
        tray_icon.stop()
        logger.info("System tray stopped")
    # ... rest of shutdown
```

## Testing

### Unit Tests

Tests are located in `tests/desktop/test_window_manager.py`:

```python
class TestCreateSystemTray:
    """Tests for create_system_tray()"""

    def test_creates_tray_with_menu_items(self):
        """Test that create_system_tray creates tray with correct menu items"""
        # Tests menu structure

    def test_loads_icon_from_resources_if_exists(self):
        """Test that create_system_tray loads icon from resources if file exists"""
        # Tests icon loading

    def test_creates_default_icon_if_file_not_found(self):
        """Test that create_system_tray creates default icon if file doesn't exist"""
        # Tests fallback behavior
```

### Running Tests

```bash
# Run all window manager tests
pytest tests/desktop/test_window_manager.py -v

# Run only system tray tests
pytest tests/desktop/test_window_manager.py::TestCreateSystemTray -v

# Run with coverage
pytest tests/desktop/test_window_manager.py --cov=desktop.window_manager
```

### Manual Testing

1. **Start Normal**:
   ```bash
   python desktop/main.py
   ```
   - Verify tray icon appears
   - Verify window is visible
   - Test all menu items

2. **Start Minimized**:
   ```bash
   # Edit settings.json first
   python desktop/main.py
   ```
   - Verify tray icon appears
   - Verify window is hidden
   - Click "Show Window" to reveal

3. **Disable Tray**:
   ```bash
   # Set show_in_system_tray: false
   python desktop/main.py
   ```
   - Verify no tray icon
   - App should work normally

## Troubleshooting

### Tray Icon Not Appearing

**Possible Causes**:
1. `pystray` not installed
2. System tray disabled in settings
3. Platform doesn't support system tray

**Solutions**:
```bash
# Install pystray
pip install pystray>=0.19.0

# Check settings
cat ~/.local/share/GradingApp/settings.json | grep show_in_system_tray

# Enable in settings
python -c "from desktop.settings import Settings; from pathlib import Path; s = Settings(Path.home() / '.local/share/GradingApp/settings.json'); s.load(); s.set('ui.show_in_system_tray', True); s.save()"
```

### Icon Not Loading

**Symptoms**: Default white icon instead of app icon

**Cause**: Icon files missing from `desktop/resources/`

**Solution**:
```bash
# Create icons
python desktop/resources/create_icons.py

# Verify icons exist
ls -lh desktop/resources/*.png
```

### Menu Items Not Working

**Symptoms**: Clicking menu items does nothing

**Debugging**:
```bash
# Check logs
tail -f ~/.local/share/GradingApp/logs/app.log

# Look for errors like:
# "Failed to open settings: ..."
# "Update check failed: ..."
```

### Window Not Showing After Click

**Cause**: PyWebView window show/hide not working

**Solution**:
- Ensure PyWebView is installed: `pip install pywebview>=4.0.0`
- Try clicking "Show Window" multiple times
- Check if window is hidden behind other windows

## Future Enhancements

### Planned Features

1. **Notification Support**
   - Show notifications on update available
   - Show notifications on backup completion
   - Use system notification API

2. **Custom Icons**
   - Professional icon design
   - Platform-specific icons
   - High-DPI support

3. **Advanced Menu**
   - Quick grading mode
   - Recent assignments
   - Keyboard shortcuts

4. **Tray Settings**
   - Configure menu items
   - Custom actions
   - Hotkey support

### Implementation Ideas

```python
# Notification example (future)
from desktop.window_manager import show_notification

show_notification(
    title="Backup Complete",
    message="Your data has been backed up successfully.",
    icon="success"
)

# Custom menu items (future)
from desktop.window_manager import add_tray_menu_item

add_tray_menu_item(
    "Quick Grade",
    callback=lambda: open_quick_grade(),
    position=2  # After toggle
)
```

## References

- [pystray Documentation](https://pystray.readthedocs.io/)
- [PyWebView Documentation](https://pywebview.flowrl.com/)
- [System Tray Best Practices](https://docs.microsoft.com/en-us/windows/apps/design/shell/tiles-and-notifications/)

## Change Log

### Version 1.0.0 (Phase 7)

- ✅ Created icon resources (icon.png, icon_gray.png, icon_active.png)
- ✅ Implemented `create_system_tray()` with full menu structure
- ✅ Integrated system tray with `desktop/main.py`
- ✅ Added `start_minimized` and `show_in_system_tray` settings
- ✅ Platform-specific support (Windows, macOS, Linux)
- ✅ Comprehensive unit tests
- ✅ Graceful shutdown handling
- ✅ Documentation

## License

This implementation is part of the Grading App desktop application.
