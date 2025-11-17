#!/bin/bash
# Create macOS DMG installer for Grading App
#
# This script creates a DMG (disk image) installer for macOS distribution.
# The DMG includes the application bundle and a symbolic link to /Applications
# for easy drag-and-drop installation.
#
# Prerequisites:
#   - PyInstaller build completed (dist/GradingApp.app must exist)
#   - create-dmg tool installed: npm install -g create-dmg
#     OR: brew install create-dmg
#
# Usage:
#   bash desktop/installer/macos/create-dmg.sh
#
# Output:
#   desktop/installer/macos/GradingApp-1.0.0.dmg

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
OUTPUT_DIR="$SCRIPT_DIR"

# Application info
APP_NAME="GradingApp"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"

# Extract version from Info.plist (if available) or use default
if [ -f "$APP_BUNDLE/Contents/Info.plist" ]; then
    VERSION=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || echo "1.0.0")
else
    echo "Warning: Info.plist not found, using default version 1.0.0"
    VERSION="1.0.0"
fi

DMG_NAME="GradingApp-$VERSION.dmg"
DMG_PATH="$OUTPUT_DIR/$DMG_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "Grading App - macOS DMG Creator"
echo "======================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check if PyInstaller build exists
if [ ! -d "$APP_BUNDLE" ]; then
    echo -e "${RED}Error: Application bundle not found at $APP_BUNDLE${NC}"
    echo ""
    echo "Please build the application first:"
    echo "  cd $PROJECT_ROOT"
    echo "  pyinstaller grading-app.spec"
    echo ""
    echo "Note: Ensure BUNDLE is uncommented in grading-app.spec to create .app bundle"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found application bundle: $APP_BUNDLE"

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo -e "${RED}Error: create-dmg not found${NC}"
    echo ""
    echo "Please install create-dmg:"
    echo "  npm install -g create-dmg"
    echo "  OR"
    echo "  brew install create-dmg"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} Found create-dmg tool"

# Check if background image exists (optional)
BACKGROUND_IMAGE=""
if [ -f "$SCRIPT_DIR/background.png" ]; then
    BACKGROUND_IMAGE="$SCRIPT_DIR/background.png"
    echo -e "${GREEN}✓${NC} Found custom background image"
else
    echo -e "${YELLOW}ℹ${NC} No custom background image (background.png not found)"
fi

# Check if icon exists (optional)
VOLUME_ICON=""
if [ -f "$SCRIPT_DIR/volume-icon.icns" ]; then
    VOLUME_ICON="$SCRIPT_DIR/volume-icon.icns"
    echo -e "${GREEN}✓${NC} Found custom volume icon"
else
    echo -e "${YELLOW}ℹ${NC} No custom volume icon (volume-icon.icns not found)"
fi

echo ""
echo "Building DMG..."
echo "  Application: $APP_NAME"
echo "  Version: $VERSION"
echo "  Output: $DMG_PATH"
echo ""

# Remove old DMG if it exists
if [ -f "$DMG_PATH" ]; then
    echo "Removing old DMG..."
    rm "$DMG_PATH"
fi

# Build create-dmg command
CMD=(
    create-dmg
    --volname "Grading App"
    --window-pos 200 120
    --window-size 600 400
    --icon-size 100
    --icon "$APP_NAME.app" 150 190
    --hide-extension "$APP_NAME.app"
    --app-drop-link 450 190
)

# Add background image if available
if [ -n "$BACKGROUND_IMAGE" ]; then
    CMD+=(--background "$BACKGROUND_IMAGE")
fi

# Add volume icon if available
if [ -n "$VOLUME_ICON" ]; then
    CMD+=(--icon-volume "$VOLUME_ICON")
fi

# Add output path and source
CMD+=("$DMG_PATH" "$APP_BUNDLE")

# Execute create-dmg
echo "Running: ${CMD[@]}"
echo ""

if "${CMD[@]}"; then
    echo ""
    echo -e "${GREEN}✓${NC} DMG created successfully!"
    echo ""
    echo "Output: $DMG_PATH"
    echo "Size: $(du -h "$DMG_PATH" | cut -f1)"
    echo ""
    echo "Next steps:"
    echo "  1. Test the DMG by mounting it and installing the app"
    echo "  2. (Optional) Code sign the DMG for distribution"
    echo "  3. (Optional) Notarize the DMG with Apple"
    echo ""
    echo "For code signing and notarization, see:"
    echo "  desktop/installer/macos/README.md"
    echo ""
else
    echo -e "${RED}✗${NC} DMG creation failed"
    exit 1
fi

# Verify DMG is mountable
echo "Verifying DMG integrity..."
if hdiutil verify "$DMG_PATH" &> /dev/null; then
    echo -e "${GREEN}✓${NC} DMG integrity verified"
else
    echo -e "${YELLOW}⚠${NC} DMG verification failed (may still be usable)"
fi

echo ""
echo "Done!"
