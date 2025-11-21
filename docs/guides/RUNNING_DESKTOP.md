# Running the Desktop App

This guide explains how to run the grading application in desktop mode.

## 🚀 Quick Start

### Option 1: Development Mode (With Mocks - Works Now!)

If you can't install all dependencies, use the development runner with mocks:

```bash
python run_desktop_dev.py
```

This will:
- ✅ Start the Flask server on an available port
- ✅ Mock PyWebView, pystray, keyring, etc.
- ✅ Allow you to access the app via your web browser
- ⚠️ No actual desktop window (PyWebView is mocked)
- ⚠️ API keys won't persist (keyring is mocked)

**Access the app:**
- Look for the log line showing the port: `Flask server starting on http://127.0.0.1:XXXXX`
- Open your browser to that URL

### Option 2: Full Desktop Mode (Requires Dependencies)

To run with actual desktop window and all features:

```bash
# 1. Install dependencies (if pip is available)
pip install -r requirements.txt
pip install pywebview>=4.0.0 pystray>=0.19.0 apscheduler>=3.10.0 tufup>=0.5.0

# 2. Run the desktop app
python desktop/main.py
```

This will:
- ✅ Open a native desktop window (via PyWebView)
- ✅ Store API keys securely in OS credential manager
- ✅ Create user data directory for database and uploads
- ✅ Run periodic cleanup tasks
- ✅ Support automatic backups

### Option 3: Web Mode (Original - Always Works)

Run the web version (no desktop features):

```bash
python app.py
```

Then visit: http://localhost:5000

## 📁 User Data Location

The desktop app stores data in platform-specific locations:

- **Linux**: `~/.local/share/GradingApp/`
- **macOS**: `~/Library/Application Support/GradingApp/`
- **Windows**: `%APPDATA%\GradingApp\`

Contents:
- `grading.db` - SQLite database
- `uploads/` - Uploaded submission files
- `settings.json` - Application settings
- `backups/` - Automatic backups
- `logs/` - Application logs

## 🔧 Configuration

### API Keys (Desktop Mode)

1. Run the app
2. Navigate to Settings (in the navigation menu)
3. Enter API keys for your AI providers
4. Keys are stored securely in your OS credential manager

### Automatic Backups

Configure in Settings or edit `~/.local/share/GradingApp/settings.json`:

```json
{
  "data": {
    "backups_enabled": true,
    "backup_frequency": "daily",  // "never", "daily", "weekly"
    "backup_retention_days": 30
  }
}
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest tests/test_desktop/ -v

# Specific module
pytest tests/test_desktop/test_main.py -v

# Integration tests
pytest tests/test_desktop/integration/ -v

# With coverage
pytest tests/test_desktop/ --cov=desktop --cov-report=html
```

## 🐛 Troubleshooting

### "No module named 'keyring'"

**Solution 1**: Use the mocked development runner:
```bash
python run_desktop_dev.py
```

**Solution 2**: Install keyring:
```bash
pip install keyring>=25.6.0 keyrings.cryptfile>=1.3.9
```

### "No module named 'webview'"

**Solution 1**: Use the mocked development runner:
```bash
python run_desktop_dev.py
```

**Solution 2**: Install PyWebView:
```bash
pip install pywebview>=4.0.0
```

### Port Already in Use

The app automatically finds an available port. If you see this error, check if another instance is running.

### Database Locked

Close any other connections to the database. The app uses SQLite WAL mode which helps with concurrency.

## 📦 Building the Executable (Future)

Once dependencies are installed:

```bash
# Build with PyInstaller
pyinstaller grading-app.spec

# Run the built executable
./dist/GradingApp/GradingApp          # Linux/macOS
.\dist\GradingApp\GradingApp.exe      # Windows
```

## 📚 More Information

- See `desktop/README.md` for desktop module architecture
- See `specs/004-desktop-app/` for feature specifications
- See `specs/004-desktop-app/quickstart.md` for development guide

## 🆘 Getting Help

If you encounter issues:

1. Check the logs in `~/.local/share/GradingApp/logs/`
2. Run with debug logging: Set `log_level: "DEBUG"` in settings.json
3. Check test failures: `pytest tests/test_desktop/ -v --tb=short`
4. Review the desktop app README: `desktop/README.md`
