# Desktop Application - Quick Start Guide

**Feature**: 004-desktop-app
**Branch**: `004-desktop-app`
**Date**: 2025-11-16
**Audience**: Developers implementing this feature

## Prerequisites

Before starting implementation, ensure you have:

- ✅ Completed research phase (read `research.md`)
- ✅ Reviewed data model (`data-model.md`)
- ✅ Reviewed contracts (`contracts/`)
- ✅ Reviewed constitution check in `plan.md` (2 warnings acknowledged)
- ✅ Python 3.13.7 development environment
- ✅ Access to Windows, macOS, and Linux for testing (or VMs)

---

## Technology Stack Summary

From research decisions:

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Desktop Framework | PyInstaller + PyWebView | Minimal migration, proven |
| Async Tasks | ThreadPoolExecutor + custom queue | Zero dependencies, simple |
| Credential Storage | keyring + keyrings.cryptfile | Native OS integration |
| Auto-Update | tufup + GitHub Releases | Security-focused, cross-platform |
| System Tray | pystray | Lightweight, active |
| Periodic Tasks | APScheduler | Celery Beat replacement |
| Database | SQLite | Single-user desktop |

---

## Implementation Phases

### Phase 0: Foundation (Weeks 1-2)

**Goal**: Basic desktop wrapper that launches existing Flask app in a window

**Tasks**:
1. Install dependencies:
   ```bash
   pip install pywebview>=4.0.0 pyinstaller>=5.13.0
   ```

2. Create `desktop/main.py`:
   ```python
   import webview
   import threading
   from app import app  # Existing Flask app

   def start_flask():
       app.run(host='127.0.0.1', port=5050, debug=False)

   if __name__ == '__main__':
       flask_thread = threading.Thread(target=start_flask, daemon=True)
       flask_thread.start()
       webview.create_window('Grading App', 'http://127.0.0.1:5050')
       webview.start()
   ```

3. Test manually:
   ```bash
   python desktop/main.py
   ```
   - Application window should open
   - Flask app should load
   - All existing features should work

4. Configure PyInstaller (`grading-app.spec`):
   ```python
   hiddenimports = [
       'sqlalchemy.sql.default_comparator',
       'sqlalchemy.dialects.sqlite',
       'flask_sqlalchemy',
       'flask_migrate',
   ]

   a = Analysis(
       ['desktop/main.py'],
       datas=[('templates', 'templates'), ('static', 'static')],
       hiddenimports=hiddenimports,
   )

   pyz = PYZ(a.pure, a.zipped_data)

   exe = EXE(
       pyz,
       a.scripts,
       [],
       exclude_binaries=True,
       name='GradingApp',
       console=False,  # No console window
   )

   coll = COLLECT(
       exe,
       a.binaries,
       a.zipfiles,
       a.datas,
       name='GradingApp',
   )
   ```

5. Build and test executable:
   ```bash
   pyinstaller grading-app.spec
   ./dist/GradingApp/GradingApp  # Linux/macOS
   .\dist\GradingApp\GradingApp.exe  # Windows
   ```

**Success Criteria**:
- ✅ Application launches in under 10 seconds
- ✅ Existing grading features work
- ✅ Installer size under 150MB (check `du -sh dist/GradingApp`)
- ✅ Memory usage under 500MB idle (check with `htop` or Task Manager)

**Expected Issues**:
- SQLAlchemy import errors → Add hidden imports
- Missing templates/static → Fix `datas` in spec file
- Slow startup → Acceptable for now, optimize in Phase 3

---

### Phase 1: Core Desktop Features (Weeks 3-4)

**Goal**: Replace Celery with ThreadPoolExecutor, add OS credential storage, system tray

#### Task 1.1: Thread-Based Task Queue

1. Create `desktop/task_queue.py` (see `contracts/python-interfaces.md` for full spec):
   ```python
   import concurrent.futures
   from threading import Lock
   import time
   import logging

   logger = logging.getLogger(__name__)

   class DesktopTaskQueue:
       def __init__(self, max_workers=4):
           self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
           # ... (see research.md for full implementation)

   task_queue = DesktopTaskQueue(max_workers=4)
   ```

2. Add APScheduler for periodic tasks:
   ```bash
   pip install apscheduler>=3.10.0
   ```

3. Create `desktop/scheduler.py`:
   ```python
   from apscheduler.schedulers.background import BackgroundScheduler
   from tasks import cleanup_old_files, cleanup_completed_batches

   scheduler = BackgroundScheduler()
   scheduler.add_job(cleanup_old_files, 'interval', hours=24)
   scheduler.add_job(cleanup_completed_batches, 'interval', hours=6)
   scheduler.start()
   ```

4. Migrate Celery tasks (see `research.md` section 2 for details):
   - Remove `@celery_app.task` decorators
   - Replace `.delay()` calls with `task_queue.submit()`
   - Test all grading workflows

**Tests**:
```bash
pytest tests/test_desktop/test_task_queue.py -v
```

---

#### Task 1.2: OS Credential Storage

1. Install dependencies:
   ```bash
   pip install keyring>=25.6.0 keyrings.cryptfile>=1.3.9
   ```

2. Create `desktop/credentials.py` (see `contracts/python-interfaces.md`):
   ```python
   import keyring
   from keyrings.cryptfile.cryptfile import CryptFileKeyring
   import logging

   logger = logging.getLogger(__name__)

   SERVICE_NAME = "grading-app"
   PROVIDERS = ["openrouter_api_key", "claude_api_key", ...]

   def initialize_keyring():
       # ... (see contracts doc)

   def set_api_key(provider_key: str, api_key: str) -> bool:
       # ... (see contracts doc)

   # ... other functions
   ```

3. Integrate with Flask app (`desktop/app_wrapper.py`):
   ```python
   import os
   from desktop.credentials import initialize_keyring, get_api_key, PROVIDERS

   def configure_app_for_desktop(app):
       initialize_keyring()

       # Load API keys from OS credential manager
       for provider in PROVIDERS:
           api_key = get_api_key(provider)
           if api_key:
               os.environ[provider.upper()] = api_key

       # Configure SQLite database
       user_data_dir = get_user_data_dir()
       app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{user_data_dir}/grading.db'

       return app
   ```

**Tests**:
```bash
pytest tests/test_desktop/test_credentials.py -v
pytest tests/test_desktop/test_app_wrapper.py -v
```

---

#### Task 1.3: System Tray Integration

1. Install pystray:
   ```bash
   pip install pystray>=0.19.0
   ```

2. Create `desktop/window_manager.py`:
   ```python
   import pystray
   from PIL import Image

   def create_system_tray(on_show, on_hide, on_quit):
       icon = pystray.Icon(
           "Grading App",
           Image.open("desktop/resources/icon.png"),
           menu=pystray.Menu(
               pystray.MenuItem("Show", on_show),
               pystray.MenuItem("Hide", on_hide),
               pystray.MenuItem("Quit", on_quit)
           )
       )
       icon.run()
   ```

3. Update `desktop/main.py` to use system tray

**Tests**:
- Manual testing (system tray not easily unit-testable)
- Verify on Windows, macOS, Linux

---

### Phase 2: Auto-Update & UX (Weeks 5-6)

#### Task 2.1: Auto-Update Mechanism

1. Install tufup:
   ```bash
   pip install tufup>=0.5.0
   ```

2. Create `desktop/updater.py` (see `contracts/python-interfaces.md`):
   ```python
   import tufup.client
   from pathlib import Path

   class DesktopUpdater:
       def __init__(self, app_name, current_version, update_url):
           # ... (see contracts doc)

       def check_for_updates(self) -> dict:
           # ... (see contracts doc)

       def download_update(self, progress_callback=None) -> bool:
           # ... (see contracts doc)

       def apply_update(self) -> None:
           # ... (see contracts doc - DOES NOT RETURN)
   ```

3. Integrate with main app:
   ```python
   # Check for updates on startup (background thread)
   updater = DesktopUpdater("grading-app", "0.1.0", "https://github.com/USER/REPO/releases")

   def check_updates():
       update_info = updater.check_for_updates()
       if update_info.get('available'):
           show_update_notification(update_info)

   threading.Thread(target=check_updates, daemon=True).start()
   ```

**Tests**:
```bash
pytest tests/test_desktop/test_updater.py -v
```

---

#### Task 2.2: Settings & Data Management

1. Create `desktop/settings.py`:
   - Load/save settings.json
   - Apply settings on startup
   - Validate schema

2. Create `desktop/data_export.py`:
   - Export data to ZIP bundle
   - Import data from ZIP bundle
   - Validate backup integrity

**Tests**:
```bash
pytest tests/test_desktop/test_settings.py -v
pytest tests/test_desktop/test_data_export.py -v
```

---

### Phase 3: Polish & Distribution (Week 7)

#### Task 3.1: Code Signing

**Windows**:
1. Obtain EV Code Signing Certificate (~$300-500/year)
2. Sign executable:
   ```bash
   signtool.exe sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist/GradingApp/GradingApp.exe
   ```

**macOS**:
1. Enroll in Apple Developer Program ($99/year)
2. Sign and notarize:
   ```bash
   codesign --deep --force --sign "Developer ID Application: ..." GradingApp.app
   xcrun notarytool submit GradingApp.zip --apple-id ... --password ...
   xcrun stapler staple GradingApp.app
   ```

**Linux**:
- Optional GPG signature for AppImage

---

#### Task 3.2: Installer Creation

**Windows**: Use Inno Setup or NSIS to create installer
**macOS**: Create DMG with `create-dmg` tool
**Linux**: Package as AppImage or create DEB/RPM

---

#### Task 3.3: Optimization

- Reduce installer size (exclude unnecessary dependencies)
- Optimize startup time (lazy import heavy modules)
- Test on minimal hardware (4GB RAM, slow HDD)

---

## Development Workflow

### 1. Development Mode

Run desktop app directly without packaging:
```bash
python desktop/main.py
```

**Benefits**:
- Fast iteration
- Easy debugging
- No build step

**Limitations**:
- Doesn't test packaging issues
- May behave differently than packaged app

---

### 2. Build and Test Cycle

Package application for testing:
```bash
pyinstaller grading-app.spec
./dist/GradingApp/GradingApp
```

**When to use**:
- Before committing changes
- Testing platform-specific behavior
- Validating installer size/performance

---

### 3. Cross-Platform Testing

**Recommended Approach**:
1. Develop on primary platform (Linux/macOS/Windows)
2. Test on real hardware for each platform (not VMs when possible)
3. Use GitHub Actions for automated builds

**GitHub Actions Workflow** (`.github/workflows/build.yml`):
```yaml
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
    # ... similar steps

  build-linux:
    runs-on: ubuntu-latest
    # ... similar steps
```

---

## Testing Strategy

### Unit Tests

Focus on desktop-specific modules:

```bash
# Run all desktop tests
pytest tests/test_desktop/ -v

# Test specific modules
pytest tests/test_desktop/test_credentials.py -v
pytest tests/test_desktop/test_task_queue.py -v
pytest tests/test_desktop/test_updater.py -v
```

**Coverage Target**: ≥80% for new desktop modules

---

### Integration Tests

Test full desktop app workflows:

```bash
# Test app startup
pytest tests/test_desktop/integration/test_startup.py -v

# Test credential loading
pytest tests/test_desktop/integration/test_credential_loading.py -v

# Test task processing
pytest tests/test_desktop/integration/test_task_processing.py -v
```

---

### Manual Testing Checklist

Before each release:

- [ ] Install from installer (not dev mode)
- [ ] First-run experience (no existing data)
- [ ] Configure AI providers
- [ ] Upload submissions
- [ ] Run grading jobs
- [ ] Export data
- [ ] Restart application (verify settings persist)
- [ ] Import data on fresh install
- [ ] Check for updates
- [ ] System tray functions (show/hide/quit)

Test on each platform (Windows, macOS, Linux):
- [ ] All manual tests pass
- [ ] No console errors
- [ ] Performance meets targets (startup <10s, RAM <500MB idle)

---

## Common Issues & Solutions

### Issue: PyInstaller missing imports

**Symptoms**: Application crashes with `ModuleNotFoundError`

**Solution**: Add to `hiddenimports` in grading-app.spec:
```python
hiddenimports = [
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'flask_sqlalchemy',
    'flask_migrate',
    # Add any missing modules here
]
```

---

### Issue: Templates not found

**Symptoms**: Flask returns "Template not found" errors

**Solution**: Ensure templates/static in `datas`:
```python
datas=[('templates', 'templates'), ('static', 'static')],
```

---

### Issue: Port already in use

**Symptoms**: Flask fails to start with "Address already in use"

**Solution**: Auto-select available port:
```python
import socket

def get_free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]

port = get_free_port()
app.run(port=port)
```

---

### Issue: Keyring not available (Linux headless)

**Symptoms**: `RuntimeError: No keyring backend available`

**Solution**: Install D-Bus and GNOME Keyring:
```bash
sudo apt-get install gnome-keyring dbus-x11
```

Or use fallback:
```python
from keyrings.cryptfile.cryptfile import CryptFileKeyring
keyring.set_keyring(CryptFileKeyring())
```

---

### Issue: Slow startup time

**Symptoms**: Application takes >10 seconds to start

**Solutions**:
1. Lazy import heavy modules (defer until needed)
2. Use PyInstaller --onedir (faster startup than --onefile)
3. Consider Nuitka instead of PyInstaller (faster startup, see research.md)

---

### Issue: Large installer size

**Symptoms**: Installer exceeds 150MB

**Solutions**:
1. Exclude unnecessary dependencies:
   ```python
   excludes=['matplotlib', 'pandas', 'numpy']  # If not used
   ```
2. Use UPX compression:
   ```bash
   pyinstaller --upx-dir=/path/to/upx grading-app.spec
   ```
3. Switch to Nuitka (20-30% smaller, see research.md)

---

## Resources

### Documentation
- PyInstaller: https://pyinstaller.org/
- PyWebView: https://pywebview.flowrl.com/
- keyring library: https://keyring.readthedocs.io/
- tufup: https://github.com/dennisvang/tufup
- pystray: https://pystray.readthedocs.io/
- APScheduler: https://apscheduler.readthedocs.io/

### Related Specs
- `spec.md` - Feature requirements
- `research.md` - Technology decisions
- `data-model.md` - Data structures
- `contracts/` - API specifications

### Project Files
- `plan.md` - Implementation plan
- `tasks.md` - Task breakdown (created by `/speckit.tasks`)

---

## Next Steps

After completing implementation:

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Create GitHub Issues from tasks (`/speckit.taskstoissues`)
3. Begin implementation following task dependencies
4. Update `CLAUDE.md` with new technologies used

---

**Document Status**: ✅ **Complete**
**Last Updated**: 2025-11-16
**Ready for**: Implementation (`/speckit.tasks`)
