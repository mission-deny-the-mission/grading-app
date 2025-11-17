# Windows Installer

This directory contains the Inno Setup script for creating a Windows installer for Grading App.

## Prerequisites

1. **Inno Setup 6.0 or later**
   - Download from: https://jrsoftware.org/isinfo.php
   - Install with default options
   - Add to PATH (optional, for command-line builds)

2. **PyInstaller build completed**
   - Run from project root: `pyinstaller grading-app.spec`
   - Verify `dist/GradingApp/GradingApp.exe` exists

## Building the Installer

### Method 1: GUI (Inno Setup Compiler)

1. Open Inno Setup Compiler
2. Open `desktop/installer/windows/installer.iss`
3. Click **Build** > **Compile**
4. Installer will be created in: `desktop/installer/windows/Output/GradingApp-Setup.exe`

### Method 2: Command Line

```powershell
# From project root
iscc desktop\installer\windows\installer.iss
```

Output: `desktop\installer\windows\Output\GradingApp-Setup.exe`

## Installer Features

### Installation Locations

- **Program Files**: `C:\Program Files\GradingApp\`
  - Contains application executable and dependencies
  - Removed on uninstall

- **User Data**: `%APPDATA%\GradingApp\`
  - Contains database, uploads, settings, backups
  - **Preserved on uninstall/upgrade**
  - User must manually delete if they want to remove all data

### Shortcuts Created

- **Start Menu**: `Start Menu > Grading App`
- **Desktop Icon**: Optional (unchecked by default)
- **Quick Launch**: Optional (Windows 7 and earlier only)

### Registry Entries

- Uninstall information in `HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall`
- Application metadata (name, version, publisher, URL)
- All registry entries are removed on uninstall

### User Experience

1. **Welcome Screen**: Introduction to installer
2. **License Agreement**: Display LICENSE.txt
3. **Installation Directory**: Default to `C:\Program Files\GradingApp`
4. **Start Menu Folder**: Default to "Grading App"
5. **Additional Tasks**: Option to create desktop/quick launch icons
6. **Installation Progress**: Copy files, create shortcuts, write registry
7. **Finish**: Option to launch application immediately

## Customization

### Application Metadata

Edit the defines at the top of `installer.iss`:

```inno
#define MyAppName "Grading App"
#define MyAppPublisher "Your Company Name"
#define MyAppURL "https://your-website.com"
```

### App ID (Important!)

The AppId GUID uniquely identifies your application:

```inno
AppId={{A1B2C3D4-E5F6-4G7H-8I9J-0K1L2M3N4O5P}
```

**Generate a new GUID for your fork:**
- Windows: Run `New-Guid` in PowerShell
- Online: https://www.guidgenerator.com/

### License File

The installer expects a license file at:
```
desktop/installer/windows/../../../LICENSE.txt
```

If your license is elsewhere, update the path:
```inno
LicenseFile=path\to\your\LICENSE.txt
```

### Version Number

Version is automatically extracted from the built executable:
```inno
#define MyAppVersion GetVersionNumbersString("..\..\..\..\dist\GradingApp\GradingApp.exe")
```

For this to work, ensure PyInstaller builds with version info (configured in `grading-app.spec`).

## Testing

### Test Installation

1. Build installer as described above
2. Run `GradingApp-Setup.exe`
3. Follow installation wizard
4. Verify application launches
5. Verify shortcuts created
6. Check user data directory exists: `%APPDATA%\GradingApp`

### Test Uninstallation

1. Open **Settings** > **Apps** > **Installed Apps**
2. Find "Grading App" and click **Uninstall**
3. Verify program files removed: `C:\Program Files\GradingApp`
4. Verify user data preserved: `%APPDATA%\GradingApp`
5. Verify shortcuts removed from Start Menu and Desktop
6. Verify registry entries removed

### Test Upgrade

1. Install version 1.0.0
2. Create test data (add assignments, settings, etc.)
3. Build and install version 1.1.0 over existing installation
4. Verify:
   - Application upgraded to new version
   - User data preserved
   - Settings maintained
   - No data loss

## Code Signing (Recommended for Distribution)

Unsigned installers will show Windows SmartScreen warnings. To avoid this, sign your installer with a code signing certificate.

### Prerequisites

1. **EV Code Signing Certificate** ($300-500/year)
   - Recommended providers: DigiCert, Sectigo, GlobalSign
   - EV (Extended Validation) certificates provide instant SmartScreen reputation

2. **SignTool.exe** (included with Windows SDK)
   - Download: https://developer.microsoft.com/windows/downloads/windows-sdk/

### Signing Process

```powershell
# Sign the executable before building installer
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /fd SHA256 dist\GradingApp\GradingApp.exe

# Build installer
iscc installer.iss

# Sign the installer
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /fd SHA256 Output\GradingApp-Setup.exe
```

### Automated Signing

Add to `installer.iss` (requires SignTool in PATH):

```inno
[Setup]
SignTool=signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /fd SHA256 $f
```

## Troubleshooting

### Error: "Cannot find source file"

**Problem**: Inno Setup can't find the PyInstaller build output

**Solution**: Ensure you've run `pyinstaller grading-app.spec` and `dist/GradingApp/` exists

### Error: "Cannot find license file"

**Problem**: LICENSE.txt not found at expected path

**Solution**: Either create LICENSE.txt or remove the `LicenseFile` line from installer.iss

### Installer shows "Unknown Publisher"

**Problem**: Installer is not code signed

**Solution**: Sign with a code signing certificate (see Code Signing section above)

### User data not preserved after uninstall

**Problem**: User data directory being deleted

**Solution**: User data is intentionally preserved in `%APPDATA%\GradingApp`. The uninstaller shows a message explaining this. User must manually delete if desired.

### Large installer size (>200MB)

**Problem**: Installer contains unnecessary files

**Solution**:
1. Check `grading-app.spec` excludes unnecessary packages
2. Ensure UPX compression is enabled in spec file
3. Verify no duplicate dependencies bundled

## File Structure

```
desktop/installer/windows/
├── installer.iss          # Inno Setup script
├── README.md              # This file
└── Output/                # Generated installer (created on build)
    └── GradingApp-Setup.exe
```

## References

- Inno Setup Documentation: https://jrsoftware.org/ishelp/
- Inno Setup Script Examples: https://jrsoftware.org/ishelp/topic_scriptintro.htm
- Code Signing Guide: https://learn.microsoft.com/en-us/windows/win32/seccrypto/using-signtool-to-sign-a-file
