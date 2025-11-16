#!/bin/bash
# Create Linux AppImage for Grading App
#
# This script creates an AppImage (portable Linux application) for distribution.
# AppImages are self-contained and can run on most Linux distributions without installation.
#
# Prerequisites:
#   - PyInstaller build completed (dist/GradingApp directory must exist)
#   - linuxdeploy and appimagetool downloaded (script will download if missing)
#   - FUSE2 installed: sudo apt-get install fuse libfuse2
#
# Usage:
#   bash desktop/installer/linux/create-appimage.sh
#
# Output:
#   desktop/installer/linux/GradingApp-1.0.0-x86_64.AppImage

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist/GradingApp"
OUTPUT_DIR="$SCRIPT_DIR"

# Application info
APP_NAME="GradingApp"
VERSION="${APPIMAGE_VERSION:-1.0.0}"  # Can be overridden via env var

# AppImage build directory
APPDIR="$OUTPUT_DIR/AppDir"

# Tools
LINUXDEPLOY="$OUTPUT_DIR/linuxdeploy-x86_64.AppImage"
APPIMAGETOOL="$OUTPUT_DIR/appimagetool-x86_64.AppImage"

# Output file
APPIMAGE_NAME="GradingApp-$VERSION-x86_64.AppImage"
APPIMAGE_PATH="$OUTPUT_DIR/$APPIMAGE_NAME"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================"
echo "Grading App - Linux AppImage Creator"
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

# Check for FUSE2
if ! command -v fusermount &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} FUSE not found - AppImage may not run"
    echo "Install with: sudo apt-get install fuse libfuse2"
fi

# Download linuxdeploy if missing
if [ ! -f "$LINUXDEPLOY" ]; then
    echo "Downloading linuxdeploy..."
    wget -q --show-progress \
        "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage" \
        -O "$LINUXDEPLOY"
    chmod +x "$LINUXDEPLOY"
    echo -e "${GREEN}✓${NC} Downloaded linuxdeploy"
else
    echo -e "${GREEN}✓${NC} Found linuxdeploy"
fi

# Download appimagetool if missing
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    wget -q --show-progress \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
        -O "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
    echo -e "${GREEN}✓${NC} Downloaded appimagetool"
else
    echo -e "${GREEN}✓${NC} Found appimagetool"
fi

echo ""
echo "Building AppImage..."
echo "  Application: $APP_NAME"
echo "  Version: $VERSION"
echo "  Output: $APPIMAGE_PATH"
echo ""

# Clean old build
if [ -d "$APPDIR" ]; then
    echo "Removing old AppDir..."
    rm -rf "$APPDIR"
fi

if [ -f "$APPIMAGE_PATH" ]; then
    echo "Removing old AppImage..."
    rm "$APPIMAGE_PATH"
fi

# Create AppDir structure
echo "Creating AppDir structure..."
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/metainfo"

# Copy application files
echo "Copying application files..."
cp -r "$DIST_DIR"/* "$APPDIR/usr/bin/"

# Create wrapper script to set up environment
cat > "$APPDIR/usr/bin/grading-app-wrapper.sh" << 'EOF'
#!/bin/bash
# AppImage wrapper script for Grading App
# Sets up environment and launches the application

# Get the directory where this script is located (inside AppImage)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up Python path
export PYTHONHOME="$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR"

# Set LD_LIBRARY_PATH to find bundled libraries
export LD_LIBRARY_PATH="$SCRIPT_DIR:$LD_LIBRARY_PATH"

# Launch the application
exec "$SCRIPT_DIR/GradingApp" "$@"
EOF

chmod +x "$APPDIR/usr/bin/grading-app-wrapper.sh"

# Create .desktop file
cat > "$APPDIR/usr/share/applications/grading-app.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Grading App
GenericName=Grading Application
Comment=Desktop application for grading assignments
Exec=grading-app-wrapper.sh
Icon=grading-app
Terminal=false
Categories=Education;Office;
Keywords=grading;education;assignments;
StartupNotify=true
EOF

# Create icon (placeholder - use a real icon in production)
# If you have an icon, copy it here:
if [ -f "$SCRIPT_DIR/icon.png" ]; then
    cp "$SCRIPT_DIR/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/grading-app.png"
else
    # Create a simple placeholder icon
    echo -e "${YELLOW}ℹ${NC} No icon.png found, creating placeholder"
    # This would require imagemagick: convert -size 256x256 xc:blue "$APPDIR/usr/share/icons/hicolor/256x256/apps/grading-app.png"
    # For now, just create an empty file
    touch "$APPDIR/usr/share/icons/hicolor/256x256/apps/grading-app.png"
fi

# Create AppStream metadata
cat > "$APPDIR/usr/share/metainfo/grading-app.appdata.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.gradingapp.desktop</id>
  <metadata_license>MIT</metadata_license>
  <project_license>MIT</project_license>
  <name>Grading App</name>
  <summary>Desktop application for grading assignments</summary>
  <description>
    <p>
      Grading App is a desktop application for educators to efficiently grade
      assignments using AI-powered OCR and automated grading features.
    </p>
  </description>
  <launchable type="desktop-id">grading-app.desktop</launchable>
  <url type="homepage">https://github.com/yourusername/grading-app</url>
  <url type="bugtracker">https://github.com/yourusername/grading-app/issues</url>
  <developer_name>Grading App Team</developer_name>
  <releases>
    <release version="$VERSION" date="$(date +%Y-%m-%d)"/>
  </releases>
  <content_rating type="oars-1.1"/>
</component>
EOF

# Create AppRun (entry point for AppImage)
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
# AppRun entry point for Grading App AppImage

# Get the AppImage directory
APPDIR="$(dirname "$(readlink -f "${0}")")"

# Set up environment
export PATH="${APPDIR}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${APPDIR}/usr/lib:${LD_LIBRARY_PATH}"

# Launch wrapper script
exec "${APPDIR}/usr/bin/grading-app-wrapper.sh" "$@"
EOF

chmod +x "$APPDIR/AppRun"

# Create symlinks for linuxdeploy
ln -sf "usr/share/applications/grading-app.desktop" "$APPDIR/grading-app.desktop"
ln -sf "usr/share/icons/hicolor/256x256/apps/grading-app.png" "$APPDIR/grading-app.png"

echo "AppDir structure created successfully"
echo ""

# Build AppImage using appimagetool
echo "Building AppImage with appimagetool..."

# Set environment for appimagetool
export ARCH=x86_64
export VERSION="$VERSION"

# Run appimagetool
if "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_PATH"; then
    echo ""
    echo -e "${GREEN}✓${NC} AppImage created successfully!"
    echo ""
    echo "Output: $APPIMAGE_PATH"
    echo "Size: $(du -h "$APPIMAGE_PATH" | cut -f1)"
    echo ""

    # Make executable
    chmod +x "$APPIMAGE_PATH"

    echo "Next steps:"
    echo "  1. Test the AppImage:"
    echo "     $APPIMAGE_PATH"
    echo "  2. Distribute to users (single file, no installation needed)"
    echo "  3. (Optional) Create .zsync file for delta updates"
    echo ""
    echo "For distribution, see:"
    echo "  desktop/installer/linux/README.md"
    echo ""
else
    echo -e "${RED}✗${NC} AppImage creation failed"
    exit 1
fi

# Clean up AppDir
echo "Cleaning up build directory..."
rm -rf "$APPDIR"

echo ""
echo "Done!"
