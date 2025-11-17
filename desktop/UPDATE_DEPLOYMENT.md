# Update Deployment Guide

This document describes how to set up and deploy automatic updates for the Grading App desktop application using GitHub Releases.

## Overview

The desktop application uses the `tufup` library (The Update Framework) for secure, automatic updates. Updates are hosted on GitHub Releases and include cryptographic signature verification.

## Update Architecture

### Components

1. **DesktopUpdater** (`desktop/updater.py`): Core update logic
2. **Settings** (`desktop/settings.py`): Update configuration storage
3. **Update Check** (`desktop/main.py`): Background update checking
4. **Update Notification** (`desktop/window_manager.py`): User notification UI

### Update Flow

```
1. App startup → Check settings for auto_check
2. Background thread → Check for updates (if enabled)
3. Cache check → Skip if checked within 24 hours
4. TUF client → Fetch metadata from GitHub Releases
5. Version compare → Compare current vs. latest
6. Notification → Show update dialog (if available)
7. User choice → "Update Now" or "Remind Me Later"
8. Download → Download update with progress tracking
9. Backup → Create backup of database and settings
10. Apply → Restart application with new version
```

## GitHub Releases Setup

### Repository Structure

Your GitHub repository should have releases in this format:

```
https://github.com/user/grading-app/releases/tag/1.1.0
```

### Release Assets

Each release should include:

1. **Executables** (platform-specific):
   - `GradingApp-1.1.0-windows.exe`
   - `GradingApp-1.1.0-macos.dmg`
   - `GradingApp-1.1.0-linux.AppImage`

2. **Metadata** (optional):
   - `update_metadata.json` - Contains version info, release notes, checksums

3. **TUF Metadata** (for tufup):
   - `targets.json` - TUF target metadata
   - `snapshot.json` - TUF snapshot metadata
   - `timestamp.json` - TUF timestamp metadata

### Example Release

```bash
# Tag and create release
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0

# Upload assets via GitHub CLI or web interface
gh release create v1.1.0 \
  --title "Version 1.1.0" \
  --notes "Bug fixes and improvements" \
  GradingApp-1.1.0-windows.exe \
  GradingApp-1.1.0-macos.dmg \
  GradingApp-1.1.0-linux.AppImage
```

## Update Metadata Format

Create `update_metadata.json` for each release:

```json
{
  "version": "1.1.0",
  "release_date": "2025-11-16T12:00:00Z",
  "release_notes": "## What's New\n\n- Feature A\n- Bug fix B",
  "file_urls": {
    "windows": "https://github.com/user/grading-app/releases/download/v1.1.0/GradingApp-1.1.0-windows.exe",
    "macos": "https://github.com/user/grading-app/releases/download/v1.1.0/GradingApp-1.1.0-macos.dmg",
    "linux": "https://github.com/user/grading-app/releases/download/v1.1.0/GradingApp-1.1.0-linux.AppImage"
  },
  "checksums": {
    "windows": {"sha256": "abc123..."},
    "macos": {"sha256": "def456..."},
    "linux": {"sha256": "789abc..."}
  },
  "minimum_version": "1.0.0",
  "critical": false
}
```

## Configuration

### Settings (User-Configurable)

Located in `%APPDATA%/GradingApp/settings.json` (Windows) or equivalent on other platforms:

```json
{
  "updates": {
    "auto_check": true,
    "check_frequency": "startup",
    "auto_download": false,
    "last_check": "2025-11-16T10:30:00Z",
    "deferred_version": null
  }
}
```

**Options:**
- `auto_check`: Enable/disable automatic update checks (default: true)
- `check_frequency`: When to check - "startup", "daily", "weekly", "never" (default: "startup")
- `auto_download`: Automatically download updates without asking (default: false)
- `last_check`: Timestamp of last update check (automatically updated)
- `deferred_version`: Version user chose to defer (null if none)

### Application Configuration

In `desktop/main.py`:

```python
__version__ = "1.0.0"  # Current app version (semver format)
```

Update this version number when building new releases.

## Update Caching

The updater implements caching to avoid excessive network requests:

- **Cache Duration**: 24 hours
- **Cache Key**: Last check timestamp in settings
- **Behavior**: Skip update check if checked within last 24 hours

This is implemented in `check_for_updates_async()` in `desktop/main.py`:

```python
last_check = settings.get('updates.last_check')
if last_check:
    last_check_dt = datetime.fromisoformat(last_check)
    if datetime.utcnow() - last_check_dt < timedelta(hours=24):
        logger.debug("Update check skipped - checked less than 24 hours ago")
        return
```

## Building and Releasing Updates

### 1. Update Version Number

```python
# desktop/main.py
__version__ = "1.1.0"  # Update this
```

### 2. Build Application

```bash
# Using PyInstaller
pyinstaller grading-app.spec

# Output: dist/GradingApp/GradingApp
```

### 3. Package for Platforms

**Windows:**
```bash
# Create installer with NSIS or Inno Setup
# Output: GradingApp-1.1.0-windows.exe
```

**macOS:**
```bash
# Create DMG
# Output: GradingApp-1.1.0-macos.dmg
```

**Linux:**
```bash
# Create AppImage
# Output: GradingApp-1.1.0-linux.AppImage
```

### 4. Generate Checksums

```bash
# SHA256 checksums for verification
sha256sum GradingApp-1.1.0-windows.exe > checksums.txt
sha256sum GradingApp-1.1.0-macos.dmg >> checksums.txt
sha256sum GradingApp-1.1.0-linux.AppImage >> checksums.txt
```

### 5. Create GitHub Release

```bash
# Using GitHub CLI
gh release create v1.1.0 \
  --title "Version 1.1.0" \
  --notes-file RELEASE_NOTES.md \
  GradingApp-1.1.0-windows.exe \
  GradingApp-1.1.0-macos.dmg \
  GradingApp-1.1.0-linux.AppImage \
  update_metadata.json
```

### 6. Generate TUF Metadata (Optional)

If using tufup for enhanced security:

```bash
# Initialize TUF repository (first time only)
tufup init --repo-dir ./tuf-repo

# Add new version
tufup targets add \
  --repo-dir ./tuf-repo \
  --version 1.1.0 \
  GradingApp-1.1.0-windows.exe \
  GradingApp-1.1.0-macos.dmg \
  GradingApp-1.1.0-linux.AppImage

# Upload TUF metadata to GitHub Release
```

## Testing Updates

### Manual Testing

1. **Build old version** (e.g., 1.0.0)
2. **Run application** - Should show current version
3. **Create new release** (e.g., 1.1.0) on GitHub
4. **Restart application** - Should detect update
5. **Verify notification** appears
6. **Download and apply** update
7. **Verify new version** is running

### Automated Testing

Run the integration tests:

```bash
# Test updater unit tests
pytest tests/desktop/test_updater.py -v

# Test update workflow integration
pytest tests/desktop/integration/test_update_workflow.py -v
```

## Security Considerations

1. **TUF Signatures**: Use tufup for cryptographic signature verification
2. **HTTPS Only**: All update URLs must use HTTPS
3. **Checksum Verification**: Verify SHA256 checksums after download
4. **Backup Before Update**: Always create backup before applying updates
5. **Rollback Support**: Keep backups to enable rollback if update fails

## Troubleshooting

### Update Check Fails

- **Network Error**: Check internet connectivity
- **Invalid URL**: Verify `update_url` in DesktopUpdater initialization
- **Rate Limiting**: GitHub API rate limits may apply

### Download Fails

- **Disk Space**: Ensure sufficient disk space for download
- **Permissions**: Check write permissions to temp directory
- **Firewall**: Verify firewall allows HTTPS connections

### Backup Fails

- **Disk Space**: Ensure space for backup in user data directory
- **Permissions**: Check write permissions to backup directory

### Update Not Detected

- **Cache**: Wait 24 hours or clear `last_check` in settings
- **Version Format**: Ensure versions follow semver (e.g., "1.0.0")
- **Auto-Check Disabled**: Verify `auto_check: true` in settings

## Future Enhancements

1. **Delta Updates**: Download only changed files (bandwidth optimization)
2. **Background Downloads**: Download updates silently in background
3. **Staged Rollouts**: Deploy to percentage of users first
4. **Auto-Retry**: Retry failed downloads automatically
5. **Update Channels**: Support beta/stable channels

## References

- [TUF (The Update Framework)](https://theupdateframework.io/)
- [tufup Library](https://github.com/dennisvang/tufup)
- [GitHub Releases API](https://docs.github.com/en/rest/releases)
- [Semantic Versioning](https://semver.org/)
