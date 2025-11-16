# Desktop Application

This directory contains the desktop application wrapper for the Grading App, which packages the Flask web application into a standalone executable for Windows, macOS, and Linux.

## Architecture

The desktop application uses:
- **PyWebView**: Lightweight desktop window (uses system browser engine)
- **PyInstaller**: Python application bundler
- **Flask**: Existing web application (runs on localhost)
- **SQLite**: Local database (replacing PostgreSQL for single-user desktop)
- **ThreadPoolExecutor**: Async task processing (replacing Celery/Redis)

## Quick Start

### Prerequisites

- Python 3.13.7 or compatible version (>=3.9,<4.0)
- pip package manager
- Operating system: Windows 10+, macOS 11+, or Ubuntu 20.04+

### Installation

1. Install desktop dependencies:
```bash
pip install -r requirements.txt
```

This includes:
- `pywebview>=4.0.0` - Desktop window framework
- `pyinstaller>=5.13.0` - Application bundler
- `keyring>=25.6.0` - OS credential storage
- `keyrings.cryptfile>=1.3.9` - Encrypted file fallback for credentials
- `apscheduler>=3.10.0` - Periodic task scheduler

## Running the Application

### Development Mode

Run the application directly from source (fastest iteration):

```bash
# From project root
python desktop/main.py
```

**When to use:**
- During active development
- Testing code changes quickly
- Debugging with full stack traces

**Limitations:**
- Doesn't test packaging issues
- May behave differently than packaged app
- Requires Python environment

### Production Build

Package the application into a standalone executable:

```bash
# From project root
pyinstaller grading-app.spec

# Run the packaged application
./dist/GradingApp/GradingApp          # Linux/macOS
.\dist\GradingApp\GradingApp.exe      # Windows
```

**When to use:**
- Before committing changes to ensure packaging works
- Testing platform-specific behavior
- Validating performance metrics (startup time, memory usage, installer size)
- Preparing for distribution

**Performance Targets:**
- Startup time: <10 seconds (typically 1-3s)
- Memory usage (idle): <500MB (typically 150-300MB)
- Installer size: ~100-130MB

## Building for Distribution

### Platform-Specific Builds

PyInstaller must be run on the target platform (cross-compilation is not supported).

#### Windows

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable
pyinstaller grading-app.spec

# Output location
dist\GradingApp\GradingApp.exe
```

**Installer creation**:
```powershell
# Install Inno Setup from: https://jrsoftware.org/isinfo.php
# Then compile the installer script:
iscc desktop\installer\windows\installer.iss

# Output: desktop\installer\windows\Output\GradingApp-Setup.exe
```

For detailed instructions, see `desktop/installer/windows/README.md`

#### macOS

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable
pyinstaller grading-app.spec

# Output location
dist/GradingApp/GradingApp
```

**DMG creation**:
```bash
# Install create-dmg: npm install -g create-dmg
# Create DMG installer:
bash desktop/installer/macos/create-dmg.sh

# Output: desktop/installer/macos/GradingApp-1.0.0.dmg
```

**Note**: For DMG creation, uncomment the BUNDLE section in `grading-app.spec` to create `dist/GradingApp.app`

For detailed instructions including code signing and notarization, see `desktop/installer/macos/README.md`

#### Linux

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable
pyinstaller grading-app.spec

# Output location
dist/GradingApp/GradingApp
```

**AppImage creation** (portable, recommended):
```bash
# Create AppImage (auto-downloads tools if needed):
bash desktop/installer/linux/create-appimage.sh

# Output: desktop/installer/linux/GradingApp-1.0.0-x86_64.AppImage
```

**DEB package** (for Debian/Ubuntu):
```bash
# Install fpm: sudo gem install fpm
# Create DEB package:
bash desktop/installer/linux/create-deb.sh

# Output: desktop/installer/linux/grading-app_1.0.0_amd64.deb
```

For detailed instructions including RPM and Flatpak, see `desktop/installer/linux/README.md`

### Build All Installers

To build installers for all platforms at once (or for the current platform):

```bash
# Verify PyInstaller build is ready
bash desktop/installer/verify-build.sh

# Build installers for current platform
bash desktop/installer/build-all.sh

# Or specify a platform
bash desktop/installer/build-all.sh windows  # Windows only
bash desktop/installer/build-all.sh macos    # macOS only
bash desktop/installer/build-all.sh linux    # Linux only
bash desktop/installer/build-all.sh all      # All platforms (cross-platform not supported)
```

**Note**: Cross-compilation is not supported. Windows installers must be built on Windows, macOS on macOS, and Linux on Linux.

### Automated Builds with GitHub Actions

For continuous integration, use GitHub Actions to build for all platforms:

```yaml
# .github/workflows/build.yml
name: Build Desktop App

on: [push, pull_request]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pyinstaller grading-app.spec
      - uses: actions/upload-artifact@v3
        with:
          name: GradingApp-Windows
          path: dist/GradingApp/

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pyinstaller grading-app.spec
      - uses: actions/upload-artifact@v3
        with:
          name: GradingApp-macOS
          path: dist/GradingApp/

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pyinstaller grading-app.spec
      - uses: actions/upload-artifact@v3
        with:
          name: GradingApp-Linux
          path: dist/GradingApp/
```

## Configuration

### PyInstaller Spec File

The `grading-app.spec` file controls the bundling process. Key sections:

**Hidden Imports** (lines 13-28):
```python
hiddenimports = [
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.postgresql',
    'flask_sqlalchemy',
    'flask_migrate',
    'celery',  # Will be removed in future phases
]
```

Add any dynamically imported modules here if you encounter `ModuleNotFoundError` at runtime.

**Data Files** (lines 34-38):
```python
datas=[
    ('templates', 'templates'),  # Flask templates
    ('static', 'static'),        # Static assets
]
```

User data (uploads, database) is stored separately and NOT bundled with the application.

**Console Mode** (line 65):
```python
console=False  # No console window (GUI mode)
```

Set to `True` for debugging to see Python error messages in a console window.

### User Data Directory

User data is stored in platform-specific locations (survives application updates):

- **Windows**: `%APPDATA%\GradingApp\`
- **macOS**: `~/Library/Application Support/GradingApp/`
- **Linux**: `~/.local/share/GradingApp/`

Contents:
- `grading.db` - SQLite database
- `uploads/` - Uploaded files
- `settings.json` - User settings
- `backups/` - Automatic backups

## Troubleshooting

### PyInstaller Missing Imports

**Symptom**: Application crashes with `ModuleNotFoundError` at runtime

**Solution**: Add missing module to `hiddenimports` in `grading-app.spec`:
```python
hiddenimports = [
    # ... existing imports ...
    'your.missing.module',
]
```

Then rebuild:
```bash
pyinstaller grading-app.spec
```

### Templates Not Found

**Symptom**: Flask returns "Template not found" errors

**Solution**: Ensure templates are included in `datas` in `grading-app.spec`:
```python
datas=[
    ('templates', 'templates'),
    ('static', 'static'),
]
```

### Port Already in Use

**Symptom**: Flask fails to start with "Address already in use"

**Solution**: The application automatically selects an available port. If this fails, check `desktop/main.py` for the `get_free_port()` function.

### Large Installer Size

**Symptom**: Distribution exceeds 150MB

**Solutions**:
1. Exclude unnecessary dependencies in `grading-app.spec`:
   ```python
   excludes=['matplotlib', 'pandas', 'numpy']  # If not used
   ```

2. Enable UPX compression (already enabled in spec file)

3. Consider Nuitka instead of PyInstaller for 20-30% size reduction:
   ```bash
   pip install nuitka
   python -m nuitka --standalone --onefile desktop/main.py
   ```

### Slow Startup Time

**Symptom**: Application takes >10 seconds to start

**Solutions**:
1. Use `--onedir` mode instead of `--onefile` (already configured)
2. Lazy import heavy modules in `desktop/main.py`
3. Profile startup with:
   ```bash
   python -X importtime desktop/main.py
   ```

### Keyring Not Available (Linux)

**Symptom**: `RuntimeError: No keyring backend available`

**Solution 1** - Install system keyring:
```bash
sudo apt-get install gnome-keyring dbus-x11
```

**Solution 2** - Fallback is automatic (keyrings.cryptfile), no action needed

## Module Reference

### `app_wrapper.py`
Configures Flask application for desktop deployment:
- Loads API keys from OS credential manager
- Configures SQLite database path
- Sets up user data directory

### `credentials.py`
Manages API key storage using OS credential manager:
- `set_api_key(provider, key)` - Store API key
- `get_api_key(provider)` - Retrieve API key
- `delete_api_key(provider)` - Delete API key

### `task_queue.py`
ThreadPoolExecutor-based task queue (replaces Celery):
- `submit(func, *args, **kwargs)` - Queue task for execution
- `get_status(task_id)` - Check task status
- Automatic retry with exponential backoff

### `settings.py`
User settings management:
- Load/save settings from user data directory
- Validate settings schema
- Apply settings on startup

### `main.py` (to be created in Phase 0)
Application entry point:
- Starts Flask server in background thread
- Creates PyWebView window
- Handles graceful shutdown

## Development Status

**Current Phase**: Phase 0 - Foundation (Week 1-2)

**Completed:**
- ✅ PyInstaller spec file created
- ✅ Desktop module structure
- ✅ Credential storage implementation
- ✅ Task queue implementation

**Next Steps:**
1. Create `desktop/main.py` (entry point)
2. Test basic packaging on primary development platform
3. Address platform-specific packaging issues
4. Validate performance metrics

For detailed implementation plan, see:
- `/specs/004-desktop-app/quickstart.md`
- `/specs/004-desktop-app/research.md`
- `/specs/004-desktop-app/plan.md`

## Contributing

When making changes to desktop packaging:

1. **Test in development mode first**:
   ```bash
   python desktop/main.py
   ```

2. **Test packaging before committing**:
   ```bash
   pyinstaller grading-app.spec
   ./dist/GradingApp/GradingApp
   ```

3. **Verify performance targets**:
   - Startup time: `time ./dist/GradingApp/GradingApp`
   - Memory usage: `htop` or Task Manager
   - Installer size: `du -sh dist/GradingApp`

4. **Update this README** if you change:
   - Build process
   - Configuration options
   - Platform-specific requirements

## License

Same as main Grading App project.
