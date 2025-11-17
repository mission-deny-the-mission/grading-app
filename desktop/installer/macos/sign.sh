#!/bin/bash
# macOS Code Signing Script
# Signs application bundles with Developer ID certificate
# Usage: ./sign.sh /path/to/YourApp.app [identity]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Output functions
info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] <app_bundle_path>

Signs a macOS application bundle with Developer ID certificate.

Arguments:
  app_bundle_path       Path to .app bundle to sign (required)

Options:
  -i, --identity NAME   Signing identity (Developer ID Application: Name)
                        If not provided, will auto-detect first Developer ID cert
  -e, --entitlements    Path to entitlements.plist file
  -t, --timestamp URL   Timestamp server URL (default: Apple's)
  -d, --deep            Use deep signing (signs all nested code)
  -f, --force           Force re-signing even if already signed
  -v, --verbose         Verbose output
  -h, --help            Show this help message

Examples:
  $0 dist/GradingApp.app
  $0 -i "Developer ID Application: John Doe (ABC123XYZ)" dist/GradingApp.app
  $0 --entitlements entitlements.plist dist/GradingApp.app
  $0 --deep --force dist/GradingApp.app

EOF
}

# Default values
APP_PATH=""
IDENTITY=""
ENTITLEMENTS=""
TIMESTAMP_URL="http://timestamp.apple.com/ts01"
DEEP_SIGN=false
FORCE_SIGN=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--identity)
            IDENTITY="$2"
            shift 2
            ;;
        -e|--entitlements)
            ENTITLEMENTS="$2"
            shift 2
            ;;
        -t|--timestamp)
            TIMESTAMP_URL="$2"
            shift 2
            ;;
        -d|--deep)
            DEEP_SIGN=true
            shift
            ;;
        -f|--force)
            FORCE_SIGN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [[ -z "$APP_PATH" ]]; then
                APP_PATH="$1"
            else
                error "Multiple app paths provided"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate app path
if [[ -z "$APP_PATH" ]]; then
    error "App bundle path is required"
    usage
    exit 1
fi

# Header
echo ""
echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   macOS Code Signing Script${NC}"
echo -e "${CYAN}=====================================${NC}"
echo ""

# Check if app exists
if [[ ! -d "$APP_PATH" ]]; then
    error "App bundle not found: $APP_PATH"
    exit 1
fi

if [[ ! "$APP_PATH" =~ \.app$ ]]; then
    warning "Path does not end with .app, is this correct?"
fi

success "Found app bundle: $APP_PATH"

# Auto-detect identity if not provided
if [[ -z "$IDENTITY" ]]; then
    info "Auto-detecting Developer ID certificate..."

    # Get first Developer ID Application certificate
    IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -n 1 | sed -n 's/.*"\(.*\)"/\1/p')

    if [[ -z "$IDENTITY" ]]; then
        error "No Developer ID Application certificate found"
        echo ""
        info "Available code signing identities:"
        security find-identity -v -p codesigning
        echo ""
        error "Please install a Developer ID Application certificate"
        error "See SIGNING_SETUP.md for instructions"
        exit 1
    fi

    success "Found identity: $IDENTITY"
else
    info "Using provided identity: $IDENTITY"

    # Verify identity exists
    if ! security find-identity -v -p codesigning | grep -q "$IDENTITY"; then
        error "Identity not found: $IDENTITY"
        echo ""
        info "Available identities:"
        security find-identity -v -p codesigning
        exit 1
    fi
fi

# Check for entitlements file
if [[ -n "$ENTITLEMENTS" ]]; then
    if [[ ! -f "$ENTITLEMENTS" ]]; then
        error "Entitlements file not found: $ENTITLEMENTS"
        exit 1
    fi
    info "Using entitlements: $ENTITLEMENTS"
fi

# Build codesign arguments
SIGN_ARGS=()

if $FORCE_SIGN; then
    SIGN_ARGS+=("--force")
fi

if $DEEP_SIGN; then
    SIGN_ARGS+=("--deep")
fi

if $VERBOSE; then
    SIGN_ARGS+=("--verbose")
fi

# Always use hardened runtime (required for notarization)
SIGN_ARGS+=("--options" "runtime")

# Add timestamp
SIGN_ARGS+=("--timestamp=$TIMESTAMP_URL")

# Add entitlements if provided
if [[ -n "$ENTITLEMENTS" ]]; then
    SIGN_ARGS+=("--entitlements" "$ENTITLEMENTS")
fi

# Add identity
SIGN_ARGS+=("--sign" "$IDENTITY")

# Function to sign a single file
sign_file() {
    local file="$1"
    local description="$2"

    if $VERBOSE; then
        info "Signing: $description"
    fi

    if codesign "${SIGN_ARGS[@]}" "$file" 2>&1; then
        if $VERBOSE; then
            success "Signed: $description"
        fi
        return 0
    else
        error "Failed to sign: $description"
        return 1
    fi
}

# Sign nested frameworks and libraries first
info "Scanning for nested frameworks and libraries..."

# Find all dylibs and frameworks
DYLIBS=($(find "$APP_PATH/Contents" -name "*.dylib" 2>/dev/null || true))
FRAMEWORKS=($(find "$APP_PATH/Contents/Frameworks" -name "*.framework" 2>/dev/null || true))

# Sign dylibs
if [[ ${#DYLIBS[@]} -gt 0 ]]; then
    info "Found ${#DYLIBS[@]} dynamic libraries to sign"
    for dylib in "${DYLIBS[@]}"; do
        sign_file "$dylib" "$(basename "$dylib")"
    done
    success "Signed all dynamic libraries"
fi

# Sign frameworks
if [[ ${#FRAMEWORKS[@]} -gt 0 ]]; then
    info "Found ${#FRAMEWORKS[@]} frameworks to sign"
    for framework in "${FRAMEWORKS[@]}"; do
        sign_file "$framework" "$(basename "$framework")"
    done
    success "Signed all frameworks"
fi

# Find and sign executables in Contents/MacOS
info "Signing executables in Contents/MacOS..."

if [[ -d "$APP_PATH/Contents/MacOS" ]]; then
    while IFS= read -r -d '' executable; do
        # Skip if not executable
        if [[ ! -x "$executable" ]]; then
            continue
        fi

        sign_file "$executable" "$(basename "$executable")"
    done < <(find "$APP_PATH/Contents/MacOS" -type f -perm +111 -print0)
fi

# Sign Python.framework if present (PyInstaller/py2app)
if [[ -d "$APP_PATH/Contents/Frameworks/Python.framework" ]]; then
    info "Found Python.framework, signing..."
    sign_file "$APP_PATH/Contents/Frameworks/Python.framework" "Python.framework"
fi

# Sign helper apps and plugins
if [[ -d "$APP_PATH/Contents/Helpers" ]]; then
    info "Signing helper applications..."
    while IFS= read -r -d '' helper; do
        sign_file "$helper" "$(basename "$helper")"
    done < <(find "$APP_PATH/Contents/Helpers" -name "*.app" -print0)
fi

# Sign the main app bundle last
info "Signing main app bundle..."

if $DEEP_SIGN; then
    # Deep signing - signs everything recursively
    info "Using deep signing (this may take longer)..."
    if codesign --deep --force --options runtime --timestamp="$TIMESTAMP_URL" \
        ${ENTITLEMENTS:+--entitlements "$ENTITLEMENTS"} \
        --sign "$IDENTITY" \
        ${VERBOSE:+--verbose} \
        "$APP_PATH"; then
        success "Deep signing completed"
    else
        error "Deep signing failed"
        exit 1
    fi
else
    # Sign just the app bundle
    if codesign --force --options runtime --timestamp="$TIMESTAMP_URL" \
        ${ENTITLEMENTS:+--entitlements "$ENTITLEMENTS"} \
        --sign "$IDENTITY" \
        ${VERBOSE:+--verbose} \
        "$APP_PATH"; then
        success "App bundle signing completed"
    else
        error "App bundle signing failed"
        exit 1
    fi
fi

# Verify signature
echo ""
info "Verifying signature..."

if codesign --verify --deep --strict --verbose=2 "$APP_PATH" 2>&1; then
    success "Signature verification passed!"
else
    error "Signature verification failed!"
    exit 1
fi

# Display signature information
echo ""
info "Signature information:"
codesign -dvv "$APP_PATH" 2>&1 | grep -E "(Authority|Identifier|Format|Timestamp|Runtime)"

# Check if hardened runtime is enabled
if codesign -dvv "$APP_PATH" 2>&1 | grep -q "flags=0x10000(runtime)"; then
    success "Hardened Runtime is enabled (required for notarization)"
else
    warning "Hardened Runtime may not be enabled"
fi

# Check for secure timestamp
if codesign -dvv "$APP_PATH" 2>&1 | grep -q "Timestamp="; then
    success "Secure timestamp is present"
else
    warning "No timestamp found (signature will expire with certificate)"
fi

# Final success message
echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   Code Signing Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

info "Next steps:"
echo "  1. Test the signed app: open '$APP_PATH'"
echo "  2. Create DMG: hdiutil create -srcfolder '$APP_PATH' output.dmg"
echo "  3. Notarize: ./notarize.sh output.dmg"
echo "  4. Staple ticket: xcrun stapler staple output.dmg"
echo ""

exit 0
