# Desktop Application Architecture

This document describes the architecture, design decisions, and development workflow for the Grading App desktop application.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Module Descriptions](#module-descriptions)
- [Development Guide](#development-guide)
- [Building](#building)
- [Testing](#testing)
- [Distribution](#distribution)

---

## Overview

The Grading App desktop application is a standalone, single-user version of the web application, packaged using PyInstaller. It provides:

- **Zero-configuration startup**: No server setup required
- **Offline capability**: Works without internet (except for AI grading)
- **Secure credential storage**: API keys stored in OS keyring
- **Automatic updates**: Built-in update checker and installer
- **Data portability**: Export/import capabilities for backups
- **Cross-platform**: Windows, macOS, and Linux support

### Key Design Decisions

1. **SQLite instead of PostgreSQL/Redis**: Single-user desktop apps don't need multi-user database systems
2. **Thread-based task queue**: Replaces Celery for background tasks (no Redis dependency)
3. **OS keyring integration**: More secure than storing keys in local files
4. **PyWebView for GUI**: Embeds Flask app in native window without browser chrome
5. **PyInstaller packaging**: Bundles Python interpreter and dependencies into single executable

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Application                       │
├─────────────────────────────────────────────────────────────┤
│  desktop/main.py (Entry Point)                              │
│    │                                                          │
│    ├──> Flask App (app.py)                                  │
│    │      └──> Routes, Templates, Models                    │
│    │                                                          │
│    ├──> PyWebView Window (window_manager.py)               │
│    │      └──> Native OS window displaying Flask UI         │
│    │                                                          │
│    ├──> Background Services                                 │
│    │      ├──> Task Queue (task_queue.py)                   │
│    │      ├──> Scheduler (scheduler.py)                     │
│    │      └──> Updater (updater.py)                        │
│    │                                                          │
│    ├──> Data Layer                                          │
│    │      ├──> SQLite Database (app_wrapper.py)            │
│    │      ├──> OS Keyring (credentials.py)                 │
│    │      └──> Settings File (settings.py)                 │
│    │                                                          │
│    └──> Utilities                                           │
│           ├──> Data Export/Import (data_export.py)         │
│           ├──> Crash Reporter (crash_reporter.py)          │
│           └──> Logging (main.py)                           │
└─────────────────────────────────────────────────────────────┘
```

### Application Startup Sequence

1. **Crash Handler Setup** (`crash_reporter.py`)
   - Install global exception handler for crash reporting

2. **Logging Configuration** (`main.py:setup_logging()`)
   - Create rotating log files in user data directory
   - Configure console and file handlers

3. **Database Configuration** (`app_wrapper.py`)
   - Set DATABASE_URL to SQLite path in user data directory
   - Import Flask app (triggers database initialization)

4. **Desktop Configuration** (`app_wrapper.py:configure_app_for_desktop()`)
   - Initialize OS keyring for credentials
   - Load API keys from keyring to environment
   - Configure directories (database, uploads, backups)
   - Set up SQLite performance pragmas

5. **Database Initialization** (`models.py`)
   - Create all tables if they don't exist

6. **Settings Initialization** (`settings.py`)
   - Load or create default settings file

7. **Scheduler Start** (`scheduler.py`)
   - Start background task scheduler
   - Schedule automatic backups

8. **Update Check** (`updater.py`, background thread)
   - Check for application updates (if enabled)

9. **Flask Server Start** (background thread)
   - Start Flask on localhost with random free port

10. **PyWebView Window** (`window_manager.py`)
    - Create native OS window
    - Load Flask URL
    - Start event loop (blocks until window closed)

11. **Graceful Shutdown** (`main.py:shutdown_gracefully()`)
    - Shutdown task queue (wait for running tasks)
    - Stop scheduler
    - Exit application

---

## Directory Structure

```
desktop/
├── __init__.py           # Package initialization, version info
├── main.py               # Application entry point
├── app_wrapper.py        # Flask configuration for desktop
├── window_manager.py     # PyWebView window creation
├── task_queue.py         # Thread-based background tasks
├── scheduler.py          # Periodic task scheduling
├── credentials.py        # OS keyring integration
├── settings.py           # User preferences/settings
├── updater.py            # Automatic update system
├── data_export.py        # Data backup/restore
├── crash_reporter.py     # Crash logging and reporting
├── loading.py            # Startup loading screen
│
├── installer/            # Installer scripts
│   ├── build-all.sh      # Build all platform installers
│   ├── verify-build.sh   # Verify PyInstaller output
│   ├── analyze-bundle.sh # Bundle size analysis
│   ├── windows/          # Windows installer (Inno Setup)
│   ├── macos/            # macOS DMG creation
│   └── linux/            # Linux AppImage/DEB
│
├── resources/            # Application resources
│   └── icon.png          # Application icon
│
├── performance_test.py   # Performance testing script
└── large_db_test.py      # Large database stress test
```

---

## Module Descriptions

### Core Modules

#### `main.py`
**Application Entry Point**

- Orchestrates startup sequence
- Configures logging with rotating file handlers
- Starts Flask server in background thread
- Creates PyWebView window
- Handles graceful shutdown

Key functions:
- `setup_logging()`: Configure application logging
- `start_flask()`: Run Flask server (background thread)
- `create_main_window()`: Create PyWebView window
- `shutdown_gracefully()`: Clean shutdown of all services
- `main()`: Entry point

#### `app_wrapper.py`
**Flask Desktop Configuration**

- Configures Flask app for desktop deployment
- Manages SQLite database path and pragmas
- Initializes OS keyring for credentials
- Sets up directory structure

Key functions:
- `get_user_data_dir()`: Platform-specific user data directory
- `get_free_port()`: Find available port for Flask
- `configure_app_for_desktop()`: Main configuration function
- `set_sqlite_pragmas()`: Optimize SQLite performance

#### `window_manager.py`
**PyWebView Integration**

- Creates native OS window for Flask UI
- Manages system tray icon (optional)
- Displays update notifications

Key functions:
- `create_main_window()`: Create PyWebView window
- `create_system_tray()`: System tray icon with menu
- `show_update_notification()`: Update notification dialog

### Background Services

#### `task_queue.py`
**Thread-Based Task Queue**

Replacement for Celery in desktop mode. Provides:
- Background task execution using threading
- Task priority management
- Graceful shutdown with timeout
- Error handling and retry logic

Key classes:
- `DesktopTaskQueue`: Main queue implementation
- Methods: `submit()`, `submit_batch()`, `shutdown()`

#### `scheduler.py`
**Periodic Task Scheduler**

Uses APScheduler for recurring tasks:
- Automatic database backups
- Log file rotation
- Update checks (if enabled)

Key functions:
- `start()`: Initialize and start scheduler
- `stop()`: Shutdown scheduler
- `schedule_automatic_backup()`: Configure backup schedule

### Data Management

#### `credentials.py`
**Secure Credential Storage**

Integrates with OS keyring for API key storage:
- **Windows**: Windows Credential Manager
- **macOS**: Keychain
- **Linux**: Secret Service API (gnome-keyring, KWallet)
- **Fallback**: Encrypted file storage

Key functions:
- `initialize_keyring()`: Set up keyring backend
- `get_api_key()`: Retrieve API key
- `set_api_key()`: Store API key
- `delete_api_key()`: Remove API key
- `detect_keyring_backend()`: Detect active keyring

#### `settings.py`
**User Settings Management**

JSON-based settings file with validation:
- Application preferences
- Update settings
- Backup configuration
- Window geometry

Key class:
- `Settings`: Settings manager with get/set/save/validate

#### `data_export.py`
**Data Backup and Restore**

Export/import functionality for user data:
- Database export to ZIP with JSON metadata
- Automatic backup creation
- Backup retention management
- Import validation

Key class:
- `DataExporter`: Export/import manager

### Utilities

#### `updater.py`
**Automatic Update System**

Uses TUFUP (The Update Framework for PyInstaller) for secure updates:
- Check for updates from GitHub releases
- Download and verify updates
- Install updates with rollback capability
- Pre-update data backup

Key class:
- `DesktopUpdater`: Update manager

#### `crash_reporter.py`
**Crash Reporting**

Opt-in crash reporting system:
- Global exception handler
- Crash log generation
- Data obfuscation for privacy
- User prompt for reporting

Key functions:
- `setup_crash_handler()`: Install exception handler
- `save_crash_log()`: Save crash to disk
- `obfuscate_sensitive_data()`: Remove sensitive info

---

## Development Guide

### Prerequisites

```bash
# Install development dependencies
pip install -r requirements.txt

# Install desktop-specific dependencies
pip install pyinstaller>=5.13.0
pip install pywebview>=4.0.0
pip install keyring>=24.0.0
pip install apscheduler>=3.10.0
pip install tufup>=0.5.0

# Optional: For testing
pip install pytest-cov
pip install psutil  # For memory usage testing
```

### Running in Development

```bash
# Run desktop app directly
python desktop/main.py

# Run with debug logging
LOGLEVEL=DEBUG python desktop/main.py
```

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Document all public functions/classes
- Maximum line length: 100 characters

### Adding a New Desktop Feature

1. **Create module in `desktop/`**
   ```python
   # desktop/my_feature.py
   """
   Brief description of what this module does.
   """
   import logging

   logger = logging.getLogger(__name__)

   def my_function():
       """Docstring explaining function."""
       pass
   ```

2. **Integrate with main.py**
   ```python
   from desktop.my_feature import my_function

   # Call during startup or as needed
   my_function()
   ```

3. **Add tests**
   ```python
   # tests/desktop/test_my_feature.py
   import pytest
   from desktop.my_feature import my_function

   def test_my_function():
       result = my_function()
       assert result == expected
   ```

4. **Update documentation**
   - Add to this README if significant
   - Update docstrings

---

## Building

### Build Process

```bash
# Clean previous builds
rm -rf build/ dist/

# Build with PyInstaller
pyinstaller grading-app.spec

# Verify build
bash desktop/installer/verify-build.sh

# Analyze bundle size (optional)
bash desktop/installer/analyze-bundle.sh
```

### Build Output

- **Directory**: `dist/GradingApp/`
- **Executable**: `dist/GradingApp/GradingApp` (or `.exe` on Windows)
- **Size**: ~100-150MB (includes Python, Flask, dependencies)
- **Startup Time**: <10 seconds (target)

### Platform-Specific Builds

#### Windows
```bash
pyinstaller grading-app.spec
bash desktop/installer/build-all.sh windows
# Output: dist/installers/GradingApp-Setup.exe
```

#### macOS
```bash
pyinstaller grading-app.spec
bash desktop/installer/build-all.sh macos
# Output: dist/installers/GradingApp.dmg
```

#### Linux
```bash
pyinstaller grading-app.spec
bash desktop/installer/build-all.sh linux
# Output: dist/installers/GradingApp.AppImage
#         dist/installers/GradingApp.deb
```

---

## Testing

### Unit Tests

```bash
# Run all desktop tests
pytest tests/desktop/

# Run with coverage
pytest --cov=desktop --cov-report=html tests/desktop/

# View coverage report
open htmlcov/index.html
```

### Integration Tests

```bash
# Test full startup sequence
pytest tests/desktop/integration/test_startup.py

# Test offline functionality
pytest tests/desktop/integration/test_offline.py

# Test update workflow
pytest tests/desktop/integration/test_update_workflow.py
```

### Performance Tests

```bash
# Test startup performance
python desktop/performance_test.py

# Test with large database
python desktop/large_db_test.py
```

### Manual Testing Checklist

- [ ] First launch (database creation)
- [ ] Settings persistence
- [ ] API key storage/retrieval
- [ ] Create marking scheme
- [ ] Upload submission
- [ ] Grade submission
- [ ] Export data
- [ ] Import data
- [ ] Check for updates
- [ ] View logs
- [ ] Application shutdown

---

## Distribution

### Release Process

1. **Update version** in `desktop/__init__.py`:
   ```python
   __version__ = "1.1.0"
   ```

2. **Build for all platforms**:
   ```bash
   bash desktop/installer/build-all.sh
   ```

3. **Test installers** on target platforms

4. **Create GitHub release**:
   - Tag: `v1.1.0`
   - Upload installers from `dist/installers/`
   - Add release notes

5. **Update repository** is automatically checked by updater

### Installer Formats

- **Windows**: Inno Setup (`.exe`)
  - Creates Start Menu shortcut
  - Adds to Programs & Features
  - Optional desktop shortcut

- **macOS**: DMG disk image
  - Drag-to-Applications installation
  - Code signing (optional, requires Apple Developer account)

- **Linux**:
  - AppImage (universal, no installation)
  - DEB package (Debian/Ubuntu)

### Update Distribution

Updates are distributed via GitHub Releases. The updater:
1. Checks GitHub releases for newer versions
2. Downloads and verifies update
3. Creates backup of user data
4. Installs update
5. Restarts application

---

## Performance Targets

From SC-004 requirements:

- **Startup Time**: <10 seconds
- **Idle RAM**: <500MB
- **Active RAM**: <1GB
- **Bundle Size**: <150MB (target)

### Optimization Strategies

1. **Lazy imports**: Import heavy modules only when needed
2. **UPX compression**: Compress executable (enabled in spec file)
3. **Exclude unused modules**: See `grading-app.spec` excludes list
4. **SQLite pragmas**: Performance optimizations for database
5. **Rotating logs**: Prevent log files from growing too large

---

## Troubleshooting

### Common Issues

**Import errors when running desktop/main.py**
- Ensure you're running from repository root
- Check sys.path includes parent directory

**PyWebView window doesn't appear**
- Check if pywebview is installed
- Verify OS supports PyWebView (may need additional packages on Linux)

**Keyring errors on Linux**
- Install gnome-keyring or kwallet
- Or use encrypted file fallback (automatic)

**Build fails with PyInstaller**
- Clean build/dist directories
- Check hidden imports in spec file
- Verify all dependencies installed

**Application crashes on startup**
- Check logs in user data directory
- Run with DEBUG logging: `LOGLEVEL=DEBUG python desktop/main.py`
- Check crash logs in user data directory

---

## Contributing

### Development Workflow

1. Create feature branch
2. Make changes
3. Add tests
4. Run test suite
5. Update documentation
6. Submit pull request

### Testing Requirements

- All new code must have tests
- Maintain >80% coverage for desktop modules
- Integration tests for user-facing features

---

## Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyWebView Documentation](https://pywebview.flowrl.com/)
- [Keyring Documentation](https://keyring.readthedocs.io/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [TUFUP Documentation](https://pypi.org/project/tufup/)

---

## License

MIT License - See LICENSE file for details
