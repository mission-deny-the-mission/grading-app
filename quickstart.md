# Grading App - Quick Start Guide

Welcome to the Grading App! This guide will help you get started quickly.

## Table of Contents

1. [Installation](#installation)
2. [First Launch](#first-launch)
3. [Setting Up API Keys](#setting-up-api-keys)
4. [Creating a Marking Scheme](#creating-a-marking-scheme)
5. [Uploading Submissions](#uploading-submissions)
6. [Grading Submissions](#grading-submissions)
7. [Exporting Results](#exporting-results)
8. [Backing Up Your Data](#backing-up-your-data)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Windows

1. Download `GradingApp-Setup.exe` from [releases](https://github.com/user/grading-app/releases)
2. Double-click the installer
3. Follow the installation wizard
4. Launch from Start Menu: "Grading App"

### macOS

1. Download `GradingApp.dmg` from [releases](https://github.com/user/grading-app/releases)
2. Open the DMG file
3. Drag "Grading App" to Applications folder
4. Launch from Applications (may need to right-click > Open the first time)

### Linux

**AppImage** (recommended):
```bash
chmod +x GradingApp.AppImage
./GradingApp.AppImage
```

**Debian/Ubuntu (DEB package)**:
```bash
sudo dpkg -i GradingApp.deb
sudo apt-get install -f  # Install dependencies
grading-app  # Or launch from application menu
```

---

## First Launch

When you first launch the app:

1. **Wait for initialization** (5-10 seconds)
   - Database is created automatically
   - Settings are initialized
   - Application window opens

2. **Welcome screen appears**
   - Shows application version
   - Main dashboard with navigation

3. **No configuration required** - you're ready to go!

---

## Setting Up API Keys

To use AI-powered grading, you'll need API keys from AI providers.

### Step 1: Navigate to Settings

- Click the gear icon or navigate to Settings
- Or go directly to: `Desktop Settings` in the menu

### Step 2: Choose Your AI Provider

Supported providers:
- **OpenRouter** (recommended - access to multiple models)
- **Claude** (Anthropic's Claude API)
- **OpenAI** (GPT models)
- **Gemini** (Google's Gemini)
- **LM Studio** (local models, no API key needed)

### Step 3: Enter API Key

1. Locate your provider section
2. Enter your API key
3. Click "Save"
4. Key is encrypted and stored securely in your OS keyring

**Where to get API keys**:
- OpenRouter: https://openrouter.ai/
- Claude: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/
- Gemini: https://ai.google.dev/

**Note**: Keys are stored securely and never leave your computer.

---

## Creating a Marking Scheme

Marking schemes are reusable rubrics for grading.

### Step 1: Navigate to Schemes

- Click "Marking Schemes" in the navigation menu
- Or go to: `/schemes`

### Step 2: Create New Scheme

1. Click "Create New Scheme"
2. Enter scheme details:
   - **Name**: e.g., "Essay Grading Rubric"
   - **Description**: Brief description of what this grades
   - **Total Points**: Total points possible (e.g., 100)

### Step 3: Add Questions

1. Click "Add Question"
2. Enter question details:
   - **Text**: e.g., "Does the essay have a clear thesis?"
   - **Points**: Points for this question (e.g., 10)

### Step 4: Add Criteria (Optional)

For detailed rubrics, add criteria to questions:
1. Click "Add Criterion" under a question
2. Enter:
   - **Description**: What you're looking for
   - **Points**: Points for this criterion

### Step 5: Save Scheme

Click "Save Scheme" - it's now ready to use!

---

## Uploading Submissions

### Step 1: Create or Select a Batch

- Navigate to "Batches"
- Click "Create New Batch" or select existing batch
- Enter batch details (name, date, etc.)

### Step 2: Upload Files

1. Click "Upload Submissions"
2. Select files (PDF, DOCX, images supported)
3. Files upload automatically
4. Verify files appear in the list

**Supported formats**:
- PDF (.pdf)
- Word (.docx)
- Images (.jpg, .png)
- Text (.txt)

**Maximum file size**: 100MB per file

---

## Grading Submissions

### Manual Grading

1. Navigate to your batch
2. Click on a submission
3. Apply marking scheme
4. Enter grades for each question/criterion
5. Add comments (optional)
6. Save

### AI-Powered Grading

1. Ensure API key is configured (see [Setting Up API Keys](#setting-up-api-keys))
2. Navigate to submission
3. Apply marking scheme
4. Click "Grade with AI"
5. Select your AI provider and model
6. Click "Start Grading"
7. Wait for results (30-60 seconds typically)
8. Review and adjust grades if needed
9. Save

**Note**: AI grading requires an internet connection and API credits.

---

## Exporting Results

### Export Individual Results

1. Navigate to submission
2. Click "Export"
3. Choose format:
   - PDF (formatted report)
   - CSV (spreadsheet)
   - JSON (raw data)

### Export Batch Results

1. Navigate to batch
2. Click "Export Batch"
3. Choose format
4. All submissions exported in one file

### Export All Data

1. Navigate to Settings
2. Scroll to "Data Export"
3. Click "Export All Data"
4. ZIP file created with:
   - Full database backup
   - All uploaded files
   - Metadata

**Export location**: Downloads folder or user-selected location

---

## Backing Up Your Data

### Automatic Backups

Automatic backups are enabled by default:
- **Frequency**: Daily at 2:00 AM
- **Location**: `~/.../ GradingApp/backups/`
- **Retention**: Last 7 backups kept

### Manual Backup

1. Navigate to Settings
2. Click "Data Export/Backup"
3. Click "Create Backup Now"
4. Backup saved to backups directory

### Restoring from Backup

1. Navigate to Settings
2. Click "Import Data"
3. Select backup ZIP file
4. Click "Import"
5. Application restarts with restored data

**Important**: Keep backups in a safe location!

---

## Troubleshooting

### Application Won't Start

**Windows**: "Windows protected your PC"
- Click "More info" → "Run anyway"

**macOS**: "App can't be opened"
- Right-click app → "Open" → "Open" again
- Or: System Preferences → Security & Privacy → "Open Anyway"

**Linux**: Permission denied
- Make AppImage executable: `chmod +x GradingApp.AppImage`
- Install FUSE: `sudo apt-get install fuse libfuse2`

### Grading Fails

- Verify API key is configured correctly
- Check internet connection
- Ensure you have API credits remaining
- Check logs: Settings → "View Logs"

### Data Not Saving

- Check disk space
- Verify user data directory is writable
- Check logs for errors
- Try restarting the application

### Performance Issues

If the app is slow:
- Check RAM usage (should be <1GB)
- Close other applications
- Restart the application
- Check for updates

### Where Are My Files?

**Windows**: `%APPDATA%\GradingApp\`
**macOS**: `~/Library/Application Support/GradingApp/`
**Linux**: `~/.local/share/GradingApp/`

Contains:
- `grading.db` - Database
- `uploads/` - Uploaded files
- `backups/` - Backup files
- `logs/` - Log files
- `settings.json` - Settings

### View Logs

1. Navigate to Settings
2. Click "View Logs"
3. Opens logs directory
4. Check:
   - `app.log` - General application logs
   - `errors.log` - Error messages
   - `flask.log` - Web server logs

Or use keyboard shortcut: **Ctrl+L** (Windows/Linux) or **Cmd+L** (macOS)

### Getting Help

- **Documentation**: See README.md and desktop/README.md
- **Issues**: Report bugs on GitHub Issues
- **Logs**: Include logs when reporting issues (Settings → View Logs)

---

## Tips and Best Practices

1. **Regular Backups**: Export data regularly, especially before updates
2. **Organize Batches**: Use clear, descriptive names for batches
3. **Reuse Schemes**: Create reusable marking schemes for common tasks
4. **Review AI Grades**: Always review AI-generated grades before finalizing
5. **Keep Updated**: Check for updates periodically (Settings)

---

## Common Tasks

### Change AI Provider
Settings → Update API key → Save

### Delete Old Submissions
Batches → Select batch → Delete

### Clear Cache
Settings → Clear cache (if available)

### Update Application
Settings → Check for Updates → Install

---

## Keyboard Shortcuts

- **Ctrl/Cmd + L**: Open logs directory
- **Ctrl/Cmd + ,**: Open settings (if available)
- **Ctrl/Cmd + Q**: Quit application

---

## Next Steps

Now that you're set up:

1. Create your first marking scheme
2. Upload a test submission
3. Try AI grading with a small test case
4. Export results to verify everything works
5. Start grading your actual submissions!

For more detailed documentation, see:
- [README.md](README.md) - Full documentation
- [desktop/README.md](desktop/README.md) - Desktop app architecture
- [TESTING.md](.github/TESTING.md) - Testing guide

---

**Version**: 1.0.0
**Last Updated**: 2025-11-16
