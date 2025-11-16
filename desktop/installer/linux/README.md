# Linux Installers

This directory contains scripts for creating Linux distribution packages for Grading App.

Two installer formats are provided:
- **AppImage**: Universal, portable, no installation required
- **DEB**: Debian/Ubuntu package for system-wide installation

## AppImage (Recommended)

AppImage is a universal format that works on most Linux distributions without installation.

### Prerequisites

1. **PyInstaller build completed**
   ```bash
   cd /path/to/grading-app
   pyinstaller grading-app.spec
   ```

2. **FUSE2** (for running AppImages)
   ```bash
   sudo apt-get install fuse libfuse2
   ```

3. **Tools** (auto-downloaded by script)
   - linuxdeploy
   - appimagetool

### Building AppImage

```bash
# From project root
bash desktop/installer/linux/create-appimage.sh
```

Output: `desktop/installer/linux/GradingApp-1.0.0-x86_64.AppImage`

### Testing AppImage

```bash
# Make executable (if not already)
chmod +x desktop/installer/linux/GradingApp-1.0.0-x86_64.AppImage

# Run
./desktop/installer/linux/GradingApp-1.0.0-x86_64.AppImage
```

### Distributing AppImage

1. Upload to GitHub Releases
2. Users download and run (no installation needed)
3. Optional: Integrate with AppImageHub for discoverability

### AppImage Features

- **Portable**: Single file, no installation
- **Universal**: Works on most Linux distributions
- **Self-contained**: All dependencies bundled
- **User data**: Stored in `~/.local/share/GradingApp`

## Debian Package (.deb)

Debian packages are for system-wide installation on Debian-based distributions (Ubuntu, Mint, etc.).

### Prerequisites

1. **PyInstaller build completed**
   ```bash
   pyinstaller grading-app.spec
   ```

2. **fpm (Effing Package Management)**
   ```bash
   sudo apt-get install ruby ruby-dev build-essential
   sudo gem install fpm
   ```

### Building DEB Package

```bash
# From project root
bash desktop/installer/linux/create-deb.sh
```

Output: `desktop/installer/linux/grading-app_1.0.0_amd64.deb`

### Testing DEB Package

```bash
# Install
sudo dpkg -i desktop/installer/linux/grading-app_1.0.0_amd64.deb

# If there are dependency issues:
sudo apt-get install -f

# Run
grading-app

# Or from applications menu: Search for "Grading App"

# Uninstall
sudo apt-get remove grading-app
```

### DEB Package Features

- **System integration**: Desktop entry, menu icon
- **Binary in PATH**: Run with `grading-app` command
- **Auto-updates**: Via APT if hosted in a repository
- **Installation location**: `/opt/grading-app`
- **User data**: Stored in `~/.local/share/GradingApp` (preserved on uninstall)

## Customization

### Application Icon

Both installers look for `icon.png` in this directory:

```bash
# Create or copy icon
cp /path/to/your/icon.png desktop/installer/linux/icon.png
```

Icon should be 256x256 PNG format.

### Version Number

Set version via environment variable:

```bash
# AppImage
APPIMAGE_VERSION=1.2.0 bash desktop/installer/linux/create-appimage.sh

# DEB
DEB_VERSION=1.2.0 bash desktop/installer/linux/create-deb.sh
```

Or edit the `VERSION` variable in each script.

### Package Metadata

Edit the following in `create-deb.sh`:

```bash
PACKAGE_NAME="grading-app"
MAINTAINER="Your Name <you@example.com>"
DESCRIPTION="Your description"
URL="https://your-website.com"
```

## Distribution Strategies

### AppImage Distribution

**GitHub Releases** (Recommended):
1. Create release on GitHub
2. Upload AppImage as asset
3. Users download and run

**AppImageHub**:
1. Fork https://github.com/AppImage/appimage.github.io
2. Add your app metadata
3. Submit PR
4. Get listed on https://appimage.github.io

### DEB Distribution

**Direct Download**:
- Host .deb file on your website
- Users download and install with `sudo dpkg -i`

**Personal Package Archive (PPA)**:
1. Create Launchpad account
2. Set up PPA
3. Upload package
4. Users add PPA and install via APT:
   ```bash
   sudo add-apt-repository ppa:yourusername/grading-app
   sudo apt-get update
   sudo apt-get install grading-app
   ```

**Third-party Repositories**:
- Submit to GetDeb, RPM Fusion, etc.
- Follow their submission guidelines

## Testing

### Test Matrix

Test on multiple distributions to ensure compatibility:

**Ubuntu-based**:
- Ubuntu 20.04 LTS
- Ubuntu 22.04 LTS
- Ubuntu 24.04 LTS
- Linux Mint 21

**Debian**:
- Debian 11 (Bullseye)
- Debian 12 (Bookworm)

**Other**:
- Fedora 39+
- Arch Linux (for AppImage portability test)

### Test Checklist

For each distribution:

1. **AppImage**:
   - [ ] Download/copy AppImage
   - [ ] Make executable: `chmod +x`
   - [ ] Run: `./GradingApp-*.AppImage`
   - [ ] Verify app launches and works
   - [ ] Check user data directory created

2. **DEB Package**:
   - [ ] Install: `sudo dpkg -i grading-app_*.deb`
   - [ ] Resolve dependencies: `sudo apt-get install -f`
   - [ ] Run: `grading-app`
   - [ ] Find in applications menu
   - [ ] Verify app launches and works
   - [ ] Uninstall: `sudo apt-get remove grading-app`
   - [ ] Verify user data preserved

3. **Functionality**:
   - [ ] Database created
   - [ ] Upload files
   - [ ] API keys stored
   - [ ] Settings saved
   - [ ] Backups work

### Virtual Machine Testing

Use VirtualBox or QEMU to test on different distributions:

```bash
# Example: Create Ubuntu VM
# 1. Download Ubuntu ISO from ubuntu.com
# 2. Create VM in VirtualBox
# 3. Copy installer to VM
# 4. Test installation and functionality
```

## Troubleshooting

### AppImage Issues

#### Error: "cannot execute: required file not found"

**Problem**: FUSE not installed

**Solution**:
```bash
sudo apt-get install fuse libfuse2
```

#### Error: "AppImage won't run"

**Problem**: Not executable

**Solution**:
```bash
chmod +x GradingApp-*.AppImage
```

#### AppImage runs but app crashes

**Problem**: Missing system libraries

**Solution**: Check console output for missing libraries, install them:
```bash
ldd /path/to/AppImage --appimage-extract
# Check for "not found" libraries
```

### DEB Package Issues

#### Error: "dependency problems"

**Problem**: Missing dependencies

**Solution**:
```bash
sudo apt-get install -f
```

#### Error: "package is already installed"

**Problem**: Old version installed

**Solution**:
```bash
sudo apt-get remove grading-app
sudo dpkg -i grading-app_*.deb
```

#### Error: "permission denied" when running

**Problem**: Binary not executable

**Solution**:
```bash
chmod +x /opt/grading-app/GradingApp
# Or reinstall package
```

### General Issues

#### Large package size (>200MB)

**Problem**: Unnecessary files included

**Solution**: Optimize PyInstaller build in `grading-app.spec`:
```python
excludes=['matplotlib', 'pandas', 'numpy']  # If unused
```

#### Missing icon in menu

**Problem**: Icon not found or wrong format

**Solution**: Ensure `icon.png` exists and is 256x256 PNG

#### User data not preserved after uninstall

**Problem**: Expected behavior

**Solution**: User data is intentionally preserved in `~/.local/share/GradingApp`. Delete manually if needed.

## Advanced: RPM Package

For Red Hat-based distributions (Fedora, RHEL, CentOS):

```bash
# Install fpm
sudo dnf install ruby ruby-devel gcc make rpm-build
sudo gem install fpm

# Build RPM
fpm \
    -s dir \
    -t rpm \
    -n grading-app \
    -v 1.0.0 \
    --architecture x86_64 \
    --description "Desktop application for grading assignments" \
    --url "https://github.com/yourusername/grading-app" \
    --license MIT \
    --maintainer "Your Name <you@example.com>" \
    --depends "glibc >= 2.27" \
    --depends "gtk3" \
    --depends "webkit2gtk3" \
    --rpm-compression xz \
    --after-install postinst \
    --before-remove prerm \
    --after-remove postrm \
    dist/GradingApp/=/opt/grading-app
```

## Advanced: Flatpak

For sandboxed distribution via Flathub:

1. Create flatpak manifest: `com.gradingapp.desktop.yml`
2. Build: `flatpak-builder build com.gradingapp.desktop.yml`
3. Test: `flatpak-builder --run build com.gradingapp.desktop.yml grading-app`
4. Submit to Flathub

See: https://docs.flatpak.org/en/latest/

## Advanced: Snap

For Ubuntu Store distribution:

1. Create snapcraft.yaml
2. Build: `snapcraft`
3. Test: `snap install grading-app_*.snap --dangerous`
4. Publish: `snapcraft upload grading-app_*.snap`

See: https://snapcraft.io/docs

## File Structure

```
desktop/installer/linux/
├── create-appimage.sh         # AppImage builder
├── create-deb.sh              # DEB package builder
├── README.md                  # This file
├── icon.png                   # Optional: app icon (256x256)
├── GradingApp-1.0.0-x86_64.AppImage  # Generated (AppImage)
├── grading-app_1.0.0_amd64.deb       # Generated (DEB)
└── linuxdeploy-*.AppImage     # Downloaded by script
└── appimagetool-*.AppImage    # Downloaded by script
```

## References

- AppImage: https://appimage.org/
- AppImageKit: https://github.com/AppImage/AppImageKit
- fpm: https://fpm.readthedocs.io/
- Debian Packaging: https://www.debian.org/doc/manuals/maint-guide/
- Ubuntu PPA: https://help.launchpad.net/Packaging/PPA
