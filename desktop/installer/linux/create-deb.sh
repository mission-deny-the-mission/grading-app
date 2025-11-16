#!/bin/bash
# Create Debian (.deb) package for Grading App
#
# This script creates a .deb package for Debian-based distributions (Ubuntu, Debian, Mint, etc.)
# The package can be installed with: sudo dpkg -i grading-app_1.0.0_amd64.deb
#
# Prerequisites:
#   - PyInstaller build completed (dist/GradingApp directory must exist)
#   - fpm installed: gem install fpm
#     OR: sudo apt-get install ruby ruby-dev build-essential && gem install fpm
#
# Usage:
#   bash desktop/installer/linux/create-deb.sh
#
# Output:
#   desktop/installer/linux/grading-app_1.0.0_amd64.deb

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist/GradingApp"
OUTPUT_DIR="$SCRIPT_DIR"

# Package info
PACKAGE_NAME="grading-app"
VERSION="${DEB_VERSION:-1.0.0}"
ARCH="amd64"
MAINTAINER="Grading App Team <support@gradingapp.com>"
DESCRIPTION="Desktop application for grading assignments"
URL="https://github.com/yourusername/grading-app"
LICENSE="MIT"

# Installation paths
INSTALL_DIR="/opt/grading-app"
BIN_LINK="/usr/bin/grading-app"
DESKTOP_FILE="/usr/share/applications/grading-app.desktop"
ICON_DIR="/usr/share/icons/hicolor/256x256/apps"

# Output file
DEB_NAME="${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
DEB_PATH="$OUTPUT_DIR/$DEB_NAME"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================"
echo "Grading App - Debian Package Creator"
echo "======================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check if PyInstaller build exists
if [ ! -d "$DIST_DIR" ]; then
    echo -e "${RED}Error: PyInstaller build not found at $DIST_DIR${NC}"
    echo ""
    echo "Please build the application first:"
    echo "  cd $PROJECT_ROOT"
    echo "  pyinstaller grading-app.spec"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found PyInstaller build: $DIST_DIR"

# Check if fpm is installed
if ! command -v fpm &> /dev/null; then
    echo -e "${RED}Error: fpm not found${NC}"
    echo ""
    echo "Please install fpm:"
    echo "  sudo apt-get install ruby ruby-dev build-essential"
    echo "  sudo gem install fpm"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} Found fpm: $(fpm --version | head -n1)"

echo ""
echo "Building Debian package..."
echo "  Package: $PACKAGE_NAME"
echo "  Version: $VERSION"
echo "  Architecture: $ARCH"
echo "  Output: $DEB_PATH"
echo ""

# Create staging directory
STAGING_DIR="$OUTPUT_DIR/deb-staging"
if [ -d "$STAGING_DIR" ]; then
    echo "Removing old staging directory..."
    rm -rf "$STAGING_DIR"
fi

mkdir -p "$STAGING_DIR$INSTALL_DIR"
mkdir -p "$STAGING_DIR/usr/bin"
mkdir -p "$STAGING_DIR/usr/share/applications"
mkdir -p "$STAGING_DIR$ICON_DIR"

# Copy application files
echo "Copying application files..."
cp -r "$DIST_DIR"/* "$STAGING_DIR$INSTALL_DIR/"

# Create wrapper script
cat > "$STAGING_DIR/usr/bin/grading-app" << 'EOF'
#!/bin/bash
# Wrapper script for Grading App
# This script sets up the environment and launches the application

# Application directory
APP_DIR="/opt/grading-app"

# Set up environment
export LD_LIBRARY_PATH="$APP_DIR:$LD_LIBRARY_PATH"

# Launch the application
exec "$APP_DIR/GradingApp" "$@"
EOF

chmod +x "$STAGING_DIR/usr/bin/grading-app"

# Create .desktop file
cat > "$STAGING_DIR/usr/share/applications/grading-app.desktop" << EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Grading App
GenericName=Grading Application
Comment=$DESCRIPTION
Exec=/usr/bin/grading-app
Icon=grading-app
Terminal=false
Categories=Education;Office;
Keywords=grading;education;assignments;
StartupNotify=true
EOF

# Copy icon (if available)
if [ -f "$SCRIPT_DIR/icon.png" ]; then
    cp "$SCRIPT_DIR/icon.png" "$STAGING_DIR$ICON_DIR/grading-app.png"
    echo -e "${GREEN}✓${NC} Copied icon"
else
    echo -e "${YELLOW}ℹ${NC} No icon.png found, creating placeholder"
    touch "$STAGING_DIR$ICON_DIR/grading-app.png"
fi

# Create post-install script
cat > "$STAGING_DIR/postinst" << 'EOF'
#!/bin/bash
# Post-installation script

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database -q /usr/share/applications || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

# Create user data directory template (optional)
# User data will be created at runtime in ~/.local/share/GradingApp

echo ""
echo "Grading App has been installed successfully!"
echo ""
echo "To launch:"
echo "  - From terminal: grading-app"
echo "  - From applications menu: Search for 'Grading App'"
echo ""
echo "User data will be stored in: ~/.local/share/GradingApp"
echo ""

exit 0
EOF

chmod +x "$STAGING_DIR/postinst"

# Create pre-remove script
cat > "$STAGING_DIR/prerm" << 'EOF'
#!/bin/bash
# Pre-removal script

# Nothing special to do before removal
# User data in ~/.local/share/GradingApp will be preserved

exit 0
EOF

chmod +x "$STAGING_DIR/prerm"

# Create post-remove script
cat > "$STAGING_DIR/postrm" << 'EOF'
#!/bin/bash
# Post-removal script

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database -q /usr/share/applications || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

echo ""
echo "Grading App has been removed."
echo ""
echo "Your user data has been preserved at: ~/.local/share/GradingApp"
echo "Delete this directory manually if you want to remove all data."
echo ""

exit 0
EOF

chmod +x "$STAGING_DIR/postrm"

# Remove old package if it exists
if [ -f "$DEB_PATH" ]; then
    echo "Removing old package..."
    rm "$DEB_PATH"
fi

# Build package with fpm
echo "Building package with fpm..."

fpm \
    --input-type dir \
    --output-type deb \
    --name "$PACKAGE_NAME" \
    --version "$VERSION" \
    --architecture "$ARCH" \
    --maintainer "$MAINTAINER" \
    --description "$DESCRIPTION" \
    --url "$URL" \
    --license "$LICENSE" \
    --category "Education" \
    --depends "libc6 >= 2.27" \
    --depends "libglib2.0-0" \
    --depends "libgtk-3-0" \
    --depends "libwebkit2gtk-4.0-37" \
    --after-install "$STAGING_DIR/postinst" \
    --before-remove "$STAGING_DIR/prerm" \
    --after-remove "$STAGING_DIR/postrm" \
    --deb-priority "optional" \
    --deb-compression "xz" \
    --package "$DEB_PATH" \
    --chdir "$STAGING_DIR" \
    opt usr

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓${NC} Debian package created successfully!"
    echo ""
    echo "Output: $DEB_PATH"
    echo "Size: $(du -h "$DEB_PATH" | cut -f1)"
    echo ""
    echo "To install:"
    echo "  sudo dpkg -i $DEB_PATH"
    echo "  sudo apt-get install -f  # If there are dependency issues"
    echo ""
    echo "To uninstall:"
    echo "  sudo apt-get remove $PACKAGE_NAME"
    echo ""
    echo "Next steps:"
    echo "  1. Test installation on target systems"
    echo "  2. Upload to PPA or package repository"
    echo "  3. See desktop/installer/linux/README.md for details"
    echo ""
else
    echo -e "${RED}✗${NC} Package creation failed"
    exit 1
fi

# Clean up staging directory
echo "Cleaning up staging directory..."
rm -rf "$STAGING_DIR"

echo ""
echo "Done!"
