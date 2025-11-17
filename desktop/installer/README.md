# Grading App Installers

This directory contains scripts and configurations for creating installers for Windows, macOS, and Linux.

## Quick Start

### Prerequisites

1. **PyInstaller build completed**
   ```bash
   cd /path/to/grading-app
   pyinstaller grading-app.spec
   ```

2. **Platform-specific tools** (see platform sections below)

### Verify Build

Before creating installers, verify that the PyInstaller build is complete:

```bash
bash desktop/installer/verify-build.sh
```

### Build Installers

Build installers for the current platform:

```bash
bash desktop/installer/build-all.sh
```

Or build for a specific platform:

```bash
bash desktop/installer/build-all.sh windows  # Windows installer
bash desktop/installer/build-all.sh macos    # macOS DMG
bash desktop/installer/build-all.sh linux    # Linux AppImage and DEB
```

## Platform-Specific Instructions

### Windows

**Prerequisites:**
- Windows 10 or later
- Inno Setup 6.0 or later

**Build:**
```powershell
# Install Inno Setup from: https://jrsoftware.org/isinfo.php
iscc desktop\installer\windows\installer.iss
```

**Output:**
- `desktop/installer/windows/Output/GradingApp-Setup.exe`

**Documentation:**
- See `desktop/installer/windows/README.md` for detailed instructions

**Features:**
- Installs to `C:\Program Files\GradingApp`
- User data preserved in `%APPDATA%\GradingApp`
- Start Menu and Desktop shortcuts
- Registry entries for uninstall
- Uninstaller preserves user data

### macOS

**Prerequisites:**
- macOS 10.14 or later
- create-dmg tool: `npm install -g create-dmg`
- PyInstaller BUNDLE build (uncomment BUNDLE in grading-app.spec)

**Build:**
```bash
bash desktop/installer/macos/create-dmg.sh
```

**Output:**
- `desktop/installer/macos/GradingApp-1.0.0.dmg`

**Documentation:**
- See `desktop/installer/macos/README.md` for detailed instructions
- Includes code signing and notarization steps

**Features:**
- Drag-to-install DMG interface
- Application bundle: `GradingApp.app`
- User data preserved in `~/Library/Application Support/GradingApp`
- Retina display support
- Dark mode support

### Linux

Two installer formats are provided:

#### AppImage (Recommended)

**Prerequisites:**
- Linux (any distribution)
- FUSE2: `sudo apt-get install fuse libfuse2`

**Build:**
```bash
bash desktop/installer/linux/create-appimage.sh
```

**Output:**
- `desktop/installer/linux/GradingApp-1.0.0-x86_64.AppImage`

**Features:**
- Portable, no installation required
- Works on most Linux distributions
- Single file distribution
- User data in `~/.local/share/GradingApp`

#### DEB Package

**Prerequisites:**
- Debian-based distribution (Ubuntu, Debian, Mint, etc.)
- fpm: `sudo gem install fpm`

**Build:**
```bash
bash desktop/installer/linux/create-deb.sh
```

**Output:**
- `desktop/installer/linux/grading-app_1.0.0_amd64.deb`

**Features:**
- System-wide installation to `/opt/grading-app`
- Binary symlink in `/usr/bin/grading-app`
- Desktop menu integration
- User data in `~/.local/share/GradingApp`
- Preserved on uninstall

**Documentation:**
- See `desktop/installer/linux/README.md` for detailed instructions
- Includes RPM, Flatpak, and Snap packaging options

## Directory Structure

```
desktop/installer/
├── README.md                          # This file
├── verify-build.sh                    # Build verification script
├── build-all.sh                       # Orchestration script for all platforms
│
├── windows/                           # Windows installer
│   ├── README.md                      # Windows-specific documentation
│   ├── installer.iss                  # Inno Setup script
│   └── Output/                        # Generated installer (created on build)
│       └── GradingApp-Setup.exe
│
├── macos/                             # macOS installer
│   ├── README.md                      # macOS-specific documentation
│   ├── create-dmg.sh                  # DMG creation script
│   ├── Info.plist                     # App bundle configuration
│   ├── background.png                 # Optional: DMG background image
│   ├── volume-icon.icns               # Optional: DMG volume icon
│   ├── icon.icns                      # Optional: Application icon
│   └── GradingApp-1.0.0.dmg          # Generated DMG (created on build)
│
└── linux/                             # Linux installers
    ├── README.md                      # Linux-specific documentation
    ├── create-appimage.sh             # AppImage creation script
    ├── create-deb.sh                  # DEB package creation script
    ├── icon.png                       # Optional: Application icon (256x256)
    ├── GradingApp-1.0.0-x86_64.AppImage  # Generated AppImage
    ├── grading-app_1.0.0_amd64.deb       # Generated DEB package
    └── linuxdeploy-*.AppImage         # Downloaded by script
    └── appimagetool-*.AppImage        # Downloaded by script
```

## Version Management

The version number is defined in `desktop/__init__.py`:

```python
__version__ = "1.0.0"
```

Update this file when releasing new versions. The installer scripts will automatically use this version.

## Customization

### Application Icons

Place platform-specific icons in the installer directories:

- **Windows**: Embedded in executable (configure in `grading-app.spec`)
- **macOS**: `desktop/installer/macos/icon.icns` (512x512 ICNS format)
- **Linux**: `desktop/installer/linux/icon.png` (256x256 PNG format)

### DMG Background (macOS)

Create a custom background for the macOS DMG installer:

1. Create `desktop/installer/macos/background.png` (1200x800px)
2. Include installation instructions in the image
3. Script will automatically use it if present

### Package Metadata

Update metadata in the installer scripts:

- **Windows**: Edit defines in `installer.iss`
- **macOS**: Edit variables in `create-dmg.sh`
- **Linux**: Edit variables in `create-appimage.sh` and `create-deb.sh`

## Code Signing

For production distribution, code signing is highly recommended:

### Windows

Requires EV Code Signing Certificate ($300-500/year):

```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /fd SHA256 dist\GradingApp\GradingApp.exe
iscc installer.iss
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /fd SHA256 Output\GradingApp-Setup.exe
```

### macOS

Requires Apple Developer Program ($99/year):

```bash
# Sign app
codesign --deep --force --sign "Developer ID Application: Your Name" dist/GradingApp.app

# Notarize
xcrun notarytool submit GradingApp.zip --apple-id you@example.com --password app-specific-password --wait
xcrun stapler staple dist/GradingApp.app

# Create and sign DMG
bash desktop/installer/macos/create-dmg.sh
codesign --sign "Developer ID Application: Your Name" desktop/installer/macos/GradingApp-1.0.0.dmg
```

### Linux

Code signing is less critical for Linux, but can be done:

- GPG sign DEB packages: `dpkg-sig --sign builder grading-app_1.0.0_amd64.deb`
- AppImage doesn't have standard signing mechanism

## Testing

### Test Checklist

For each platform:

1. **Build Verification**:
   - [ ] Installer builds without errors
   - [ ] Installer size is reasonable (<200MB)
   - [ ] Version number is correct

2. **Installation**:
   - [ ] Installer runs without errors
   - [ ] Application installs to correct location
   - [ ] Shortcuts/menu entries created
   - [ ] No security warnings (if code signed)

3. **Functionality**:
   - [ ] Application launches successfully
   - [ ] Database is created
   - [ ] Can upload files
   - [ ] API keys can be stored
   - [ ] Settings are saved
   - [ ] Backups work

4. **Uninstallation**:
   - [ ] Uninstaller runs successfully
   - [ ] Application files removed
   - [ ] User data preserved
   - [ ] Shortcuts/menu entries removed

### Test Platforms

Recommended test matrix:

- **Windows**: Windows 10, Windows 11
- **macOS**: macOS 11 (Big Sur), macOS 12 (Monterey), macOS 13 (Ventura)
- **Linux**: Ubuntu 20.04, Ubuntu 22.04, Debian 11, Fedora 39

## Distribution

### GitHub Releases

1. Create a new release on GitHub
2. Upload installers as release assets:
   - `GradingApp-Setup.exe` (Windows)
   - `GradingApp-1.0.0.dmg` (macOS)
   - `GradingApp-1.0.0-x86_64.AppImage` (Linux)
   - `grading-app_1.0.0_amd64.deb` (Linux)
3. Write release notes
4. Publish release

### Platform-Specific Stores

- **Windows**: Microsoft Store (requires UWP conversion)
- **macOS**: Mac App Store (requires sandbox compatibility)
- **Linux**: Snap Store, Flathub, AppImageHub

See platform-specific README files for submission instructions.

## Continuous Integration

To automate installer creation with GitHub Actions, see:
- `desktop/README.md` - GitHub Actions workflow example
- Each platform README for CI-specific considerations

## Troubleshooting

### Common Issues

**"PyInstaller build not found"**
- Run `pyinstaller grading-app.spec` first
- Check `dist/GradingApp/` exists

**"Permission denied" on scripts**
- Make scripts executable: `chmod +x desktop/installer/**/*.sh`

**"Tool not found" errors**
- Install platform-specific prerequisites (see platform sections above)

**Large installer size (>200MB)**
- Optimize `grading-app.spec` to exclude unnecessary packages
- Enable UPX compression (already enabled)

**Security warnings on unsigned installers**
- Code sign installers for production distribution
- See Code Signing section above

### Getting Help

For detailed troubleshooting:
- Windows: `desktop/installer/windows/README.md`
- macOS: `desktop/installer/macos/README.md`
- Linux: `desktop/installer/linux/README.md`
- General: `desktop/README.md`

## References

- PyInstaller: https://pyinstaller.org/
- Inno Setup: https://jrsoftware.org/isinfo.php
- create-dmg: https://github.com/sindresorhus/create-dmg
- AppImage: https://appimage.org/
- fpm: https://fpm.readthedocs.io/

## License

Same as main Grading App project.
