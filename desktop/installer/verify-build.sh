#!/bin/bash
# Verify PyInstaller Build for Grading App
#
# This script verifies that the PyInstaller build is complete and ready for installer creation.
# It checks for the existence of required files and directories.
#
# Usage:
#   bash desktop/installer/verify-build.sh
#
# Exit codes:
#   0: Build verified successfully
#   1: Build verification failed

set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect platform
case "$(uname -s)" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows";;
    *)          PLATFORM="unknown";;
esac

# Expected paths
DIST_DIR="$PROJECT_ROOT/dist"
SPEC_FILE="$PROJECT_ROOT/grading-app.spec"

# Platform-specific executable names
if [ "$PLATFORM" = "windows" ]; then
    BUILD_DIR="$DIST_DIR/GradingApp"
    EXECUTABLE="$BUILD_DIR/GradingApp.exe"
elif [ "$PLATFORM" = "macos" ]; then
    # macOS can have either .app bundle or directory build
    BUILD_DIR_APP="$DIST_DIR/GradingApp.app"
    BUILD_DIR="$DIST_DIR/GradingApp"
    EXECUTABLE_APP="$BUILD_DIR_APP/Contents/MacOS/GradingApp"
    EXECUTABLE="$BUILD_DIR/GradingApp"
else
    # Linux
    BUILD_DIR="$DIST_DIR/GradingApp"
    EXECUTABLE="$BUILD_DIR/GradingApp"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verification result
VERIFICATION_PASSED=true

echo "=========================================="
echo "PyInstaller Build Verification"
echo "=========================================="
echo ""
echo "Platform: $PLATFORM"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Check if spec file exists
echo "Checking for spec file..."
if [ -f "$SPEC_FILE" ]; then
    echo -e "${GREEN}✓${NC} Found: $SPEC_FILE"
else
    echo -e "${RED}✗${NC} Missing: $SPEC_FILE"
    VERIFICATION_PASSED=false
fi
echo ""

# Check if dist directory exists
echo "Checking for dist directory..."
if [ -d "$DIST_DIR" ]; then
    echo -e "${GREEN}✓${NC} Found: $DIST_DIR"
else
    echo -e "${RED}✗${NC} Missing: $DIST_DIR"
    VERIFICATION_PASSED=false
fi
echo ""

# Check for build output
echo "Checking for PyInstaller build output..."
BUILD_FOUND=false

if [ "$PLATFORM" = "macos" ]; then
    # macOS: Check for both .app bundle and directory
    if [ -d "$BUILD_DIR_APP" ] && [ -f "$EXECUTABLE_APP" ]; then
        echo -e "${GREEN}✓${NC} Found macOS .app bundle: $BUILD_DIR_APP"
        echo -e "${GREEN}✓${NC} Found executable: $EXECUTABLE_APP"
        BUILD_FOUND=true
    elif [ -d "$BUILD_DIR" ] && [ -f "$EXECUTABLE" ]; then
        echo -e "${GREEN}✓${NC} Found build directory: $BUILD_DIR"
        echo -e "${GREEN}✓${NC} Found executable: $EXECUTABLE"
        BUILD_FOUND=true
        echo -e "${YELLOW}ℹ${NC} Note: For macOS DMG, uncomment BUNDLE section in grading-app.spec"
    else
        echo -e "${RED}✗${NC} Build not found"
        echo "Expected either:"
        echo "  - $BUILD_DIR_APP (with $EXECUTABLE_APP)"
        echo "  - $BUILD_DIR (with $EXECUTABLE)"
        BUILD_FOUND=false
    fi
else
    # Windows/Linux: Check for directory build
    if [ -d "$BUILD_DIR" ]; then
        echo -e "${GREEN}✓${NC} Found build directory: $BUILD_DIR"

        if [ -f "$EXECUTABLE" ]; then
            echo -e "${GREEN}✓${NC} Found executable: $EXECUTABLE"
            BUILD_FOUND=true
        else
            echo -e "${RED}✗${NC} Missing executable: $EXECUTABLE"
            BUILD_FOUND=false
        fi
    else
        echo -e "${RED}✗${NC} Missing build directory: $BUILD_DIR"
        BUILD_FOUND=false
    fi
fi

if [ "$BUILD_FOUND" = false ]; then
    VERIFICATION_PASSED=false
fi
echo ""

# Check for critical bundled files/directories
if [ "$BUILD_FOUND" = true ]; then
    echo "Checking for bundled resources..."

    # Determine the actual build directory to check
    if [ "$PLATFORM" = "macos" ] && [ -d "$BUILD_DIR_APP" ]; then
        CHECK_DIR="$BUILD_DIR_APP/Contents/MacOS"
    else
        CHECK_DIR="$BUILD_DIR"
    fi

    # Check for templates directory
    if [ -d "$CHECK_DIR/templates" ] || [ -d "$CHECK_DIR/_internal/templates" ]; then
        echo -e "${GREEN}✓${NC} Found templates directory"
    else
        echo -e "${YELLOW}⚠${NC} Templates directory not found (may cause issues)"
        echo "  Expected: $CHECK_DIR/templates or $CHECK_DIR/_internal/templates"
    fi

    # Check for static directory
    if [ -d "$CHECK_DIR/static" ] || [ -d "$CHECK_DIR/_internal/static" ]; then
        echo -e "${GREEN}✓${NC} Found static directory"
    else
        echo -e "${YELLOW}⚠${NC} Static directory not found (may cause issues)"
        echo "  Expected: $CHECK_DIR/static or $CHECK_DIR/_internal/static"
    fi

    echo ""
fi

# Check build size
if [ "$BUILD_FOUND" = true ]; then
    echo "Checking build size..."

    if [ "$PLATFORM" = "macos" ] && [ -d "$BUILD_DIR_APP" ]; then
        SIZE=$(du -sh "$BUILD_DIR_APP" 2>/dev/null | cut -f1)
        SIZE_MB=$(du -sm "$BUILD_DIR_APP" 2>/dev/null | cut -f1)
        echo "Build size: $SIZE ($SIZE_MB MB)"
    else
        SIZE=$(du -sh "$BUILD_DIR" 2>/dev/null | cut -f1)
        SIZE_MB=$(du -sm "$BUILD_DIR" 2>/dev/null | cut -f1)
        echo "Build size: $SIZE ($SIZE_MB MB)"
    fi

    # Check against target size
    TARGET_SIZE_MB=150
    if [ "$SIZE_MB" -gt "$TARGET_SIZE_MB" ]; then
        echo -e "${YELLOW}⚠${NC} Bundle size exceeds target ($TARGET_SIZE_MB MB)"
        echo "  Consider running: bash desktop/installer/analyze-bundle.sh"
    else
        echo -e "${GREEN}✓${NC} Bundle size is within target ($TARGET_SIZE_MB MB)"
    fi

    echo ""
fi

# Final result
echo "=========================================="
if [ "$VERIFICATION_PASSED" = true ]; then
    echo -e "${GREEN}✓ Verification PASSED${NC}"
    echo ""
    echo "PyInstaller build is ready for installer creation."
    echo ""
    echo "Next steps:"
    echo "  - Run platform-specific installer script:"

    case "$PLATFORM" in
        windows)
            echo "    iscc desktop\\installer\\windows\\installer.iss"
            ;;
        macos)
            echo "    bash desktop/installer/macos/create-dmg.sh"
            ;;
        linux)
            echo "    bash desktop/installer/linux/create-appimage.sh"
            echo "    bash desktop/installer/linux/create-deb.sh"
            ;;
    esac

    echo ""
    echo "  - Or build all installers for current platform:"
    echo "    bash desktop/installer/build-all.sh"
    echo ""

    exit 0
else
    echo -e "${RED}✗ Verification FAILED${NC}"
    echo ""
    echo "PyInstaller build is incomplete or missing."
    echo ""
    echo "To build the application:"
    echo "  cd $PROJECT_ROOT"
    echo "  pyinstaller grading-app.spec"
    echo ""
    echo "Troubleshooting:"
    echo "  - Ensure PyInstaller is installed: pip install pyinstaller"
    echo "  - Check for errors in the build output"
    echo "  - Verify grading-app.spec is correctly configured"
    echo "  - See desktop/README.md for more information"
    echo ""

    exit 1
fi
