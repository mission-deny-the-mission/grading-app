# 🚀 Desktop App Quick Start Guide

## Running the App RIGHT NOW

The easiest way to run the desktop app immediately:

```bash
python run_desktop_dev.py
```

**What you'll see:**
```
======================================================================
DESKTOP APP - DEVELOPMENT MODE WITH MOCKS
======================================================================

Starting Grading App Desktop Application
Flask server starting on 127.0.0.1:XXXXX
Flask URL: http://127.0.0.1:XXXXX
```

**How to use it:**
1. Look for the line showing: `Flask URL: http://127.0.0.1:XXXXX`
2. Open that URL in your web browser
3. The app will work just like the web version!
4. Press `Ctrl+C` to stop

## What's Working

✅ **Flask server** - Full web interface
✅ **SQLite database** - Local database (grading_app_dev.db)
✅ **Task queue** - Async job processing (ThreadPoolExecutor)
✅ **Scheduler** - Periodic cleanup tasks
✅ **Settings** - Configuration management
✅ **Data export/import** - Backup and restore
✅ **All grading features** - Upload, grade, view results

⚠️ **What's Mocked** (won't work fully in dev mode):
- Desktop window (PyWebView) - use browser instead
- API key storage - keys won't persist between runs
- System tray - not available in dev mode
- Auto-updates - not available in dev mode

## New Features in Desktop Mode

### 1. Settings Page
Visit: `http://localhost:XXXXX/desktop/settings`

Configure:
- AI provider API keys (OpenRouter, Claude, OpenAI, Gemini, etc.)
- Auto-update preferences
- Backup settings

### 2. Data Management
Visit: `http://localhost:XXXXX/desktop/data`

Features:
- Export all data (schemes, submissions, jobs) to ZIP file
- Import data from backup
- View database statistics

### 3. Automatic Backups

Backups are created automatically (configurable):
- **Frequency**: Daily (default), Weekly, or Never
- **Location**: `~/.local/share/GradingApp/backups/` (Linux)
- **Retention**: 30 days (default)
- **Format**: ZIP file with database + uploads

## File Locations

### Development Mode
- Database: `grading_app_dev.db` (in current directory)
- Uploads: `uploads/` (in current directory)

### Production Desktop Mode
- **Linux**: `~/.local/share/GradingApp/`
- **macOS**: `~/Library/Application Support/GradingApp/`
- **Windows**: `%APPDATA%\\GradingApp\\`

## Next Steps

### To Get Full Desktop Experience

**For Nix users** (recommended):

1. Exit and reload your Nix shell to get the new dependencies:
```bash
exit  # Exit current shell
nix-shell  # Re-enter with updated dependencies
```

2. Then run the desktop app:
```bash
python desktop/main.py
```

**For pip users**:

Install the missing dependencies:

```bash
pip install pywebview>=4.0.0 pystray>=0.19.0 apscheduler>=3.10.0 tufup>=0.5.0
```

Then run:
```bash
python desktop/main.py
```

This will open an actual desktop window instead of requiring a browser.

**Note**: PyWebView requires GTK3 on Linux. If you get errors, install:
```bash
# On Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0

# On Fedora
sudo dnf install python3-gobject gtk3 webkit2gtk3
```

### To Build an Executable

```bash
# Install PyInstaller
pip install PyInstaller>=5.13.0

# Build the executable
pyinstaller grading-app.spec

# Run it
./dist/GradingApp/GradingApp  # Linux/macOS
```

## Testing

Run the test suite:

```bash
# All desktop tests
pytest tests/desktop/ -v

# Just unit tests (fast)
pytest tests/desktop/test_*.py -v

# Integration tests
pytest tests/desktop/integration/ -v
```

## Troubleshooting

### App won't start
- Make sure you're in the grading-app directory
- Check that DATABASE_URL is set to SQLite (the runner does this)
- Try: `rm grading_app_dev.db` to reset the database

### Can't access the URL
- Make sure you use the exact URL from the logs
- The port changes each time (finds an available port automatically)
- Try `localhost` instead of `127.0.0.1` if one doesn't work

### Database errors
- Delete the dev database: `rm grading_app_dev.db`
- Run migrations: `flask db upgrade`

## More Information

- **Full Instructions**: See `RUNNING_DESKTOP.md`
- **Architecture**: See `desktop/README.md`
- **Feature Specs**: See `specs/004-desktop-app/`
