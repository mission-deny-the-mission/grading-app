#!/bin/bash
# Build All Installers for Grading App
#
# This script orchestrates the creation of installers for all supported platforms:
#   - Windows: Inno Setup installer (.exe)
#   - macOS: DMG disk image (.dmg)
#   - Linux: AppImage (.AppImage) and DEB package (.deb)
#
# Platform-specific builds:
#   - Windows installer requires Windows + Inno Setup (run manually on Windows)
#   - macOS DMG requires macOS (run manually on macOS)
#   - Linux installers can be built on Linux
#
# Usage:
#   bash desktop/installer/build-all.sh [platform]
#
# Arguments:
#   platform (optional): windows|macos|linux|all (default: current platform)
#
# Examples:
#   bash desktop/installer/build-all.sh           # Build for current platform
#   bash desktop/installer/build-all.sh linux     # Build Linux installers only
#   bash desktop/installer/build-all.sh all       # Attempt all platforms (will fail on unsupported)

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect current platform
detect_platform() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        CYGWIN*|MINGW*|MSYS*) echo "windows";;
        *)          echo "unknown";;
    esac
}

CURRENT_PLATFORM=$(detect_platform)
TARGET_PLATFORM="${1:-$CURRENT_PLATFORM}"

echo "=========================================="
echo "Grading App - Installer Build Script"
echo "=========================================="
echo ""
echo "Current Platform: $CURRENT_PLATFORM"
echo "Target Platform: $TARGET_PLATFORM"
echo ""

# Step 1: Verify PyInstaller build
verify_build() {
    echo -e "${BLUE}[1/3] Verifying PyInstaller build...${NC}"

    if bash "$SCRIPT_DIR/verify-build.sh"; then
        echo -e "${GREEN}✓${NC} PyInstaller build verified"
        echo ""
        return 0
    else
        echo -e "${RED}✗${NC} PyInstaller build verification failed"
        echo ""
        echo "Please build the application first:"
        echo "  cd $PROJECT_ROOT"
        echo "  pyinstaller grading-app.spec"
        echo ""
        return 1
    fi
}

# Step 2: Build Windows installer
build_windows() {
    echo -e "${BLUE}[2/3] Building Windows installer...${NC}"

    if [ "$CURRENT_PLATFORM" != "windows" ]; then
        echo -e "${YELLOW}⚠${NC} Skipping Windows installer (must be built on Windows)"
        echo ""
        echo "To build on Windows:"
        echo "  1. Install Inno Setup: https://jrsoftware.org/isinfo.php"
        echo "  2. Run: iscc desktop\\installer\\windows\\installer.iss"
        echo ""
        return 0
    fi

    # Check if Inno Setup is installed
    if ! command -v iscc &> /dev/null; then
        echo -e "${RED}✗${NC} Inno Setup Compiler (iscc) not found"
        echo ""
        echo "Please install Inno Setup:"
        echo "  Download from: https://jrsoftware.org/isinfo.php"
        echo "  Add to PATH or use full path: C:\\Program Files (x86)\\Inno Setup 6\\iscc.exe"
        echo ""
        return 1
    fi

    # Build installer
    echo "Running Inno Setup Compiler..."
    iscc "$SCRIPT_DIR/windows/installer.iss"

    echo -e "${GREEN}✓${NC} Windows installer created"
    echo ""
    return 0
}

# Step 3: Build macOS DMG
build_macos() {
    echo -e "${BLUE}[2/3] Building macOS DMG...${NC}"

    if [ "$CURRENT_PLATFORM" != "macos" ]; then
        echo -e "${YELLOW}⚠${NC} Skipping macOS DMG (must be built on macOS)"
        echo ""
        echo "To build on macOS:"
        echo "  1. Install create-dmg: npm install -g create-dmg"
        echo "  2. Run: bash desktop/installer/macos/create-dmg.sh"
        echo ""
        return 0
    fi

    # Run macOS DMG script
    bash "$SCRIPT_DIR/macos/create-dmg.sh"

    echo -e "${GREEN}✓${NC} macOS DMG created"
    echo ""
    return 0
}

# Step 4: Build Linux installers
build_linux() {
    echo -e "${BLUE}[2/3] Building Linux installers...${NC}"

    if [ "$CURRENT_PLATFORM" != "linux" ]; then
        echo -e "${YELLOW}⚠${NC} Skipping Linux installers (must be built on Linux)"
        echo ""
        echo "To build on Linux:"
        echo "  1. Install fpm: sudo gem install fpm"
        echo "  2. Run AppImage: bash desktop/installer/linux/create-appimage.sh"
        echo "  3. Run DEB: bash desktop/installer/linux/create-deb.sh"
        echo ""
        return 0
    fi

    # Build AppImage
    echo "Building AppImage..."
    if bash "$SCRIPT_DIR/linux/create-appimage.sh"; then
        echo -e "${GREEN}✓${NC} AppImage created"
    else
        echo -e "${RED}✗${NC} AppImage creation failed"
        return 1
    fi

    echo ""

    # Build DEB package
    echo "Building DEB package..."
    if bash "$SCRIPT_DIR/linux/create-deb.sh"; then
        echo -e "${GREEN}✓${NC} DEB package created"
    else
        echo -e "${RED}✗${NC} DEB package creation failed"
        return 1
    fi

    echo ""
    return 0
}

# Step 5: Summary
show_summary() {
    echo -e "${BLUE}[3/3] Build Summary${NC}"
    echo ""

    echo "Installers created:"
    echo ""

    # Windows
    WIN_INSTALLER="$SCRIPT_DIR/windows/Output/GradingApp-Setup.exe"
    if [ -f "$WIN_INSTALLER" ]; then
        echo -e "${GREEN}✓${NC} Windows: $WIN_INSTALLER"
        echo "   Size: $(du -h "$WIN_INSTALLER" | cut -f1)"
    else
        echo -e "${YELLOW}○${NC} Windows: Not built (requires Windows)"
    fi

    # macOS
    MACOS_DMG=$(find "$SCRIPT_DIR/macos" -name "GradingApp-*.dmg" -type f 2>/dev/null | head -n1)
    if [ -n "$MACOS_DMG" ] && [ -f "$MACOS_DMG" ]; then
        echo -e "${GREEN}✓${NC} macOS: $MACOS_DMG"
        echo "   Size: $(du -h "$MACOS_DMG" | cut -f1)"
    else
        echo -e "${YELLOW}○${NC} macOS: Not built (requires macOS)"
    fi

    # Linux AppImage
    LINUX_APPIMAGE=$(find "$SCRIPT_DIR/linux" -name "GradingApp-*-x86_64.AppImage" -type f 2>/dev/null | head -n1)
    if [ -n "$LINUX_APPIMAGE" ] && [ -f "$LINUX_APPIMAGE" ]; then
        echo -e "${GREEN}✓${NC} Linux AppImage: $LINUX_APPIMAGE"
        echo "   Size: $(du -h "$LINUX_APPIMAGE" | cut -f1)"
    else
        echo -e "${YELLOW}○${NC} Linux AppImage: Not built (requires Linux)"
    fi

    # Linux DEB
    LINUX_DEB=$(find "$SCRIPT_DIR/linux" -name "grading-app_*_amd64.deb" -type f 2>/dev/null | head -n1)
    if [ -n "$LINUX_DEB" ] && [ -f "$LINUX_DEB" ]; then
        echo -e "${GREEN}✓${NC} Linux DEB: $LINUX_DEB"
        echo "   Size: $(du -h "$LINUX_DEB" | cut -f1)"
    else
        echo -e "${YELLOW}○${NC} Linux DEB: Not built (requires Linux)"
    fi

    echo ""
    echo "Next steps:"
    echo "  1. Test installers on target platforms"
    echo "  2. (Optional) Code sign installers"
    echo "  3. Upload to distribution channels"
    echo ""
    echo "For more information, see:"
    echo "  - Windows: desktop/installer/windows/README.md"
    echo "  - macOS: desktop/installer/macos/README.md"
    echo "  - Linux: desktop/installer/linux/README.md"
    echo ""
}

# Main execution
main() {
    # Verify build exists
    if ! verify_build; then
        exit 1
    fi

    # Build for target platform(s)
    case "$TARGET_PLATFORM" in
        windows)
            build_windows
            ;;
        macos)
            build_macos
            ;;
        linux)
            build_linux
            ;;
        all)
            echo "Building for all platforms..."
            echo ""
            build_windows || true
            build_macos || true
            build_linux || true
            ;;
        *)
            echo -e "${RED}Error: Unknown platform '$TARGET_PLATFORM'${NC}"
            echo ""
            echo "Usage: $0 [platform]"
            echo "  platform: windows|macos|linux|all (default: current)"
            echo ""
            exit 1
            ;;
    esac

    # Show summary
    show_summary
}

# Run main
main
