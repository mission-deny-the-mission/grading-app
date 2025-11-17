# macOS Installer

This directory contains scripts and resources for creating a macOS DMG installer for Grading App.

## Prerequisites

1. **PyInstaller with BUNDLE configuration**
   - Uncomment the BUNDLE section in `grading-app.spec`
   - Build: `pyinstaller grading-app.spec`
   - Verify: `dist/GradingApp.app` exists

2. **create-dmg tool**
   ```bash
   # Using npm (recommended)
   npm install -g create-dmg

   # OR using Homebrew
   brew install create-dmg
   ```

3. **macOS 10.14 or later** (for building)

## Building the DMG

### Quick Start

```bash
# From project root
bash desktop/installer/macos/create-dmg.sh
```

Output: `desktop/installer/macos/GradingApp-1.0.0.dmg`

### Detailed Steps

1. **Build the application bundle**
   ```bash
   cd /path/to/grading-app
   pyinstaller grading-app.spec
   ```

2. **Verify bundle exists**
   ```bash
   ls -la dist/GradingApp.app
   ```

3. **Run DMG creation script**
   ```bash
   bash desktop/installer/macos/create-dmg.sh
   ```

4. **Test the DMG**
   ```bash
   # Mount the DMG
   open desktop/installer/macos/GradingApp-1.0.0.dmg

   # Drag app to Applications folder
   # Launch from Applications
   ```

## DMG Features

### Layout

- **Application Icon**: Left side (drag from here)
- **Applications Shortcut**: Right side (drag to here)
- **Background Image**: Optional custom background (see Customization)
- **Volume Icon**: Optional custom icon (see Customization)
- **Window Size**: 600x400 pixels
- **Icon Size**: 100x100 pixels

### User Experience

1. User downloads DMG file
2. User opens DMG (auto-mounts)
3. Finder window shows:
   - Grading App icon
   - Applications folder shortcut
   - Background with drag instructions
4. User drags app to Applications folder
5. User can launch from Applications or Spotlight

## Info.plist Configuration

The `Info.plist` file configures the application bundle metadata.

### Integration with PyInstaller

To use the Info.plist with PyInstaller, update `grading-app.spec`:

```python
# Add to grading-app.spec
app = BUNDLE(
    exe,
    name='GradingApp.app',
    info_plist='desktop/installer/macos/Info.plist',  # Add this
    icon='desktop/installer/macos/icon.icns',         # Optional
    bundle_identifier='com.gradingapp.desktop'
)
```

### Key Settings

- **Bundle Identifier**: `com.gradingapp.desktop`
- **Display Name**: Grading App
- **Minimum macOS**: 10.14 (Mojave)
- **Category**: Education
- **High Resolution**: Enabled (Retina support)
- **Dark Mode**: Supported

### Updating Version

Version is automatically read from the bundle's Info.plist:

```xml
<key>CFBundleShortVersionString</key>
<string>1.0.0</string>
```

Update this when releasing new versions.

## Customization

### Background Image

Create a custom background image for the DMG:

1. Create `background.png` (1200x800px recommended)
2. Save to: `desktop/installer/macos/background.png`
3. Include installation instructions in the image
4. Script will automatically use it if present

Example content:
- Arrow pointing from app icon to Applications folder
- Text: "Drag to install"
- Branding/logo

### Volume Icon

Create a custom icon for the mounted DMG volume:

1. Create `volume-icon.icns` (512x512px icon)
2. Save to: `desktop/installer/macos/volume-icon.icns`
3. Script will automatically use it if present

Create .icns from PNG:
```bash
# Using iconutil (macOS built-in)
mkdir icon.iconset
sips -z 512 512 your-icon.png --out icon.iconset/icon_512x512.png
iconutil -c icns icon.iconset
mv icon.icns volume-icon.icns
```

### Application Icon

Create the main application icon:

1. Create `icon.icns` (512x512px icon)
2. Save to: `desktop/installer/macos/icon.icns`
3. Reference in `grading-app.spec`:
   ```python
   icon='desktop/installer/macos/icon.icns'
   ```

## Code Signing (Recommended for Distribution)

Unsigned apps will show "unidentified developer" warnings. To avoid this, sign your app with an Apple Developer certificate.

### Prerequisites

1. **Apple Developer Program** ($99/year)
   - Sign up at: https://developer.apple.com/programs/

2. **Developer ID Certificate**
   - Log in to Apple Developer portal
   - Certificates → Create → Developer ID Application
   - Download and install in Keychain

3. **Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```

### Signing Process

#### Sign the Application

```bash
# List available certificates
security find-identity -p basic -v

# Sign the app bundle
codesign --deep --force \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  dist/GradingApp.app

# Verify signature
codesign --verify --verbose dist/GradingApp.app
spctl --assess --verbose dist/GradingApp.app
```

#### Sign the DMG

```bash
# After creating DMG
codesign --sign "Developer ID Application: Your Name (TEAM_ID)" \
  desktop/installer/macos/GradingApp-1.0.0.dmg

# Verify
codesign --verify --verbose desktop/installer/macos/GradingApp-1.0.0.dmg
```

### Hardened Runtime

For macOS 10.14+, enable hardened runtime:

```bash
codesign --deep --force \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  --entitlements desktop/installer/macos/entitlements.plist \
  dist/GradingApp.app
```

Create `entitlements.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

## Notarization (Required for macOS 10.15+)

Notarization proves to Apple that your app is malware-free. Required for Catalina and later.

### Prerequisites

1. Code signed app (see above)
2. App-specific password for Apple ID
   - Generate at: https://appleid.apple.com/account/manage
   - Security → App-Specific Passwords

### Notarization Process

```bash
# 1. Create a ZIP of the app
cd dist
ditto -c -k --keepParent GradingApp.app GradingApp.zip

# 2. Submit for notarization
xcrun notarytool submit GradingApp.zip \
  --apple-id "you@example.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID" \
  --wait

# 3. Staple the notarization ticket
xcrun stapler staple GradingApp.app

# 4. Rebuild DMG with notarized app
cd ..
bash desktop/installer/macos/create-dmg.sh

# 5. Sign the DMG
codesign --sign "Developer ID Application: Your Name (TEAM_ID)" \
  desktop/installer/macos/GradingApp-1.0.0.dmg

# 6. Notarize the DMG
xcrun notarytool submit desktop/installer/macos/GradingApp-1.0.0.dmg \
  --apple-id "you@example.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID" \
  --wait

# 7. Staple the DMG
xcrun stapler staple desktop/installer/macos/GradingApp-1.0.0.dmg
```

### Verify Notarization

```bash
# Check stapling
xcrun stapler validate desktop/installer/macos/GradingApp-1.0.0.dmg

# Check Gatekeeper acceptance
spctl --assess --verbose --type install desktop/installer/macos/GradingApp-1.0.0.dmg
```

## Testing

### Test DMG Creation

1. Build and verify:
   ```bash
   bash desktop/installer/macos/create-dmg.sh
   hdiutil verify desktop/installer/macos/GradingApp-1.0.0.dmg
   ```

2. Mount and inspect:
   ```bash
   open desktop/installer/macos/GradingApp-1.0.0.dmg
   ```

3. Check layout:
   - Icons positioned correctly
   - Background visible
   - Applications shortcut works

### Test Installation

1. Drag app to Applications folder
2. Launch from Applications
3. Verify app runs correctly
4. Check user data directory: `~/Library/Application Support/GradingApp/`

### Test Uninstallation

1. Quit app if running
2. Drag app from Applications to Trash
3. Verify program removed
4. Verify user data preserved: `~/Library/Application Support/GradingApp/`

### Test Upgrade

1. Install version 1.0.0
2. Create test data
3. Install version 1.1.0 (drag to Applications, replace)
4. Verify data preserved

### Test on Clean System

1. Use a VM or test Mac
2. Download DMG
3. Open and install
4. Verify no errors or warnings (if signed and notarized)

## Troubleshooting

### Error: "Application bundle not found"

**Problem**: PyInstaller didn't create .app bundle

**Solution**: Uncomment BUNDLE section in `grading-app.spec` and rebuild:
```python
app = BUNDLE(
    exe,
    name='GradingApp.app',
    # ...
)
```

### Error: "create-dmg not found"

**Problem**: create-dmg tool not installed

**Solution**: Install with npm or Homebrew:
```bash
npm install -g create-dmg
# OR
brew install create-dmg
```

### Warning: "Unidentified Developer"

**Problem**: App is not code signed

**Solution**: Code sign with Developer ID certificate (see Code Signing section)

### Error: "App is damaged and can't be opened"

**Problem**: Gatekeeper quarantine on unsigned app

**Solution 1**: Remove quarantine attribute:
```bash
xattr -cr /Applications/GradingApp.app
```

**Solution 2**: Code sign and notarize (recommended for distribution)

### Large DMG Size (>200MB)

**Problem**: DMG contains unnecessary files

**Solution**: Optimize PyInstaller build in `grading-app.spec`:
```python
excludes=['matplotlib', 'pandas', 'numpy']  # If unused
```

### Background Image Not Showing

**Problem**: Background image not found or wrong format

**Solution**: Ensure `background.png` exists and is PNG format (1200x800px)

## File Structure

```
desktop/installer/macos/
├── create-dmg.sh          # DMG creation script
├── Info.plist             # App bundle configuration
├── README.md              # This file
├── background.png         # Optional: DMG background
├── volume-icon.icns       # Optional: DMG volume icon
├── icon.icns              # Optional: App icon
└── GradingApp-1.0.0.dmg  # Generated DMG (created on build)
```

## References

- create-dmg: https://github.com/sindresorhus/create-dmg
- Info.plist Reference: https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/
- Code Signing Guide: https://developer.apple.com/support/code-signing/
- Notarization Guide: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
- PyInstaller Bundles: https://pyinstaller.org/en/stable/spec-files.html#spec-file-options-for-a-macos-bundle
