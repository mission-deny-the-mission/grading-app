# Platform Testing Guide

This document provides instructions for testing the desktop application on fresh OS installations.

## Testing Platforms

### Windows
- **Target**: Windows 10 (version 1809+), Windows 11
- **Test on**: Fresh VM or clean machine

### macOS
- **Target**: macOS 10.14 (Mojave) or later
- **Test on**: Fresh install or VM

### Linux
- **Target**: Ubuntu 20.04+, Fedora 35+, or equivalent
- **Test on**: Fresh installation

---

## Pre-Testing Setup

### 1. Download Installers
- Windows: `GradingApp-Setup.exe`
- macOS: `GradingApp.dmg`
- Linux: `GradingApp.AppImage` or `GradingApp.deb`

### 2. Prepare Test Environment
- Fresh OS installation (VM recommended)
- No developer tools installed
- Standard user account (not admin/root)

---

## Testing Checklist

### Installation Testing

#### Windows
- [ ] Download installer
- [ ] Double-click to run
- [ ] Accept UAC prompt (if shown)
- [ ] Follow installation wizard
- [ ] Verify Start Menu shortcut created
- [ ] Verify desktop shortcut (if selected)
- [ ] Launch from Start Menu

#### macOS
- [ ] Download DMG
- [ ] Mount DMG (double-click)
- [ ] Drag app to Applications folder
- [ ] Eject DMG
- [ ] Launch from Applications
- [ ] Right-click > Open if Gatekeeper blocks
- [ ] Verify app launches without errors

#### Linux (AppImage)
- [ ] Download AppImage
- [ ] Make executable: `chmod +x GradingApp.AppImage`
- [ ] Run: `./GradingApp.AppImage`
- [ ] Verify FUSE is available (or install if needed)
- [ ] Verify app launches

#### Linux (DEB)
- [ ] Download DEB package
- [ ] Install: `sudo dpkg -i GradingApp.deb`
- [ ] Fix dependencies: `sudo apt-get install -f`
- [ ] Launch: `grading-app` or from application menu
- [ ] Verify app launches

### First Launch Testing

- [ ] Application starts within 10 seconds
- [ ] No error dialogs shown
- [ ] Database created automatically
- [ ] Settings file created with defaults
- [ ] Window displays properly (1280x800 default)
- [ ] UI is responsive
- [ ] Check About/Help for version number

### Core Functionality Testing

#### 1. Settings and Configuration
- [ ] Navigate to Settings (or /desktop/settings)
- [ ] Version number displayed correctly
- [ ] Keyring backend detected correctly
- [ ] Add OpenRouter API key
- [ ] Save successfully
- [ ] Reload page - key shows masked (****1234)
- [ ] Delete API key
- [ ] Reload - key no longer present

#### 2. Marking Scheme Creation
- [ ] Navigate to Schemes
- [ ] Create new scheme
- [ ] Add questions
- [ ] Add criteria with points
- [ ] Save scheme
- [ ] Verify scheme appears in list

#### 3. Submission Upload
- [ ] Navigate to Batches or Uploads
- [ ] Upload a test PDF/image file
- [ ] Verify file uploads successfully
- [ ] Verify file appears in list

#### 4. Grading
- [ ] Select uploaded submission
- [ ] Apply marking scheme
- [ ] Grade using AI (requires API key)
- [ ] Verify results displayed
- [ ] Verify points calculated correctly

#### 5. Data Export
- [ ] Navigate to Data Export/Settings
- [ ] Export database
- [ ] Verify ZIP file created
- [ ] Check ZIP contains database and metadata

#### 6. Data Import
- [ ] Create new backup/export
- [ ] Import previously exported data
- [ ] Verify data restored correctly

### Logging and Diagnostics

- [ ] Navigate to Settings
- [ ] Click "View Logs" button
- [ ] Verify logs directory opens
- [ ] Verify log files present:
  - app.log
  - flask.log
  - errors.log
  - updates.log (if update check ran)
- [ ] Check logs for errors

### Update Testing

- [ ] Navigate to Settings
- [ ] Enable update checking
- [ ] Trigger update check (if available)
- [ ] Verify check completes
- [ ] If update available:
  - [ ] Download update
  - [ ] Verify backup created
  - [ ] Install update
  - [ ] Verify app restarts with new version

### Performance Testing

- [ ] Measure startup time (should be <10s)
- [ ] Check RAM usage while idle (should be <500MB)
- [ ] Upload 10 files and check RAM (should be <1GB)
- [ ] Navigate between pages (should be responsive)

### Shutdown Testing

- [ ] Close application window
- [ ] Verify graceful shutdown (no errors)
- [ ] Verify no zombie processes left
- [ ] Relaunch application
- [ ] Verify data persisted correctly

---

## Uninstallation Testing

### Windows
- [ ] Open Settings > Apps
- [ ] Find "Grading App"
- [ ] Uninstall
- [ ] Verify program removed from Program Files
- [ ] Check if user data remains (should remain in %APPDATA%)

### macOS
- [ ] Drag app from Applications to Trash
- [ ] Empty Trash
- [ ] Verify app removed
- [ ] Check if user data remains (should remain in ~/Library/Application Support)

### Linux (DEB)
- [ ] Run: `sudo apt remove grading-app`
- [ ] Verify package removed
- [ ] Check if user data remains (should remain in ~/.local/share)

### Linux (AppImage)
- [ ] Delete AppImage file
- [ ] Check if user data remains

---

## Issue Reporting Template

If you encounter issues, report using this template:

```
**Platform**: Windows 10 / macOS 11 / Ubuntu 22.04
**Installer**: GradingApp-Setup.exe / GradingApp.dmg / GradingApp.AppImage
**Issue**: Brief description
**Steps to Reproduce**:
1. Step 1
2. Step 2
3. ...

**Expected Behavior**: What should happen
**Actual Behavior**: What actually happened
**Logs**: Attach relevant logs from logs directory
**Screenshots**: If applicable
```

---

## Success Criteria

For a release to be approved, all checklist items must pass on:
- At least one Windows version (10 or 11)
- At least one macOS version (10.14+)
- At least two Linux distributions (Ubuntu + Fedora/Debian)

Critical failures (app doesn't start, crashes, data loss) are release blockers.
