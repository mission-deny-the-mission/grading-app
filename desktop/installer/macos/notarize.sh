#!/bin/bash
# macOS Notarization Script
# Submits signed app/DMG to Apple for notarization
# Usage: ./notarize.sh /path/to/signed.dmg

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
Usage: $0 [OPTIONS] <file_path>

Submits a signed .app or .dmg to Apple for notarization.

Arguments:
  file_path             Path to signed .app or .dmg file (required)

Options:
  -a, --apple-id EMAIL  Apple ID email for notarization
  -t, --team-id ID      Team ID (10-character, e.g., ABC123XYZ)
  -p, --password PASS   App-specific password
  -k, --keychain NAME   Keychain profile name (recommended over --password)
  -w, --wait            Wait for notarization to complete (default: true)
  -s, --staple          Automatically staple after successful notarization
  -v, --verbose         Verbose output
  -h, --help            Show this help message

Keychain Profile (Recommended):
  Instead of providing credentials each time, create a keychain profile:

    xcrun notarytool store-credentials "grading-app" \\
      --apple-id "your-email@example.com" \\
      --team-id "ABC123XYZ" \\
      --password "xxxx-xxxx-xxxx-xxxx"

  Then use: $0 --keychain "grading-app" file.dmg

Examples:
  # Using keychain profile (recommended)
  $0 --keychain "grading-app" --staple dist/GradingApp.dmg

  # Using credentials directly
  $0 -a "dev@example.com" -t "ABC123XYZ" -p "xxxx-xxxx-xxxx-xxxx" dist/GradingApp.dmg

  # Just submit without waiting
  $0 --keychain "grading-app" --no-wait dist/GradingApp.dmg

EOF
}

# Default values
FILE_PATH=""
APPLE_ID=""
TEAM_ID=""
PASSWORD=""
KEYCHAIN_PROFILE=""
WAIT_FOR_COMPLETION=true
AUTO_STAPLE=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--apple-id)
            APPLE_ID="$2"
            shift 2
            ;;
        -t|--team-id)
            TEAM_ID="$2"
            shift 2
            ;;
        -p|--password)
            PASSWORD="$2"
            shift 2
            ;;
        -k|--keychain)
            KEYCHAIN_PROFILE="$2"
            shift 2
            ;;
        -w|--wait)
            WAIT_FOR_COMPLETION=true
            shift
            ;;
        --no-wait)
            WAIT_FOR_COMPLETION=false
            shift
            ;;
        -s|--staple)
            AUTO_STAPLE=true
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
            if [[ -z "$FILE_PATH" ]]; then
                FILE_PATH="$1"
            else
                error "Multiple file paths provided"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate file path
if [[ -z "$FILE_PATH" ]]; then
    error "File path is required"
    usage
    exit 1
fi

# Header
echo ""
echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}   macOS Notarization Script${NC}"
echo -e "${CYAN}=====================================${NC}"
echo ""

# Check if file exists
if [[ ! -e "$FILE_PATH" ]]; then
    error "File not found: $FILE_PATH"
    exit 1
fi

success "Found file: $FILE_PATH"

# Get file type
FILE_TYPE=""
if [[ "$FILE_PATH" =~ \.dmg$ ]]; then
    FILE_TYPE="DMG"
    info "File type: DMG (disk image)"
elif [[ "$FILE_PATH" =~ \.app$ ]] || [[ "$FILE_PATH" =~ \.app/$ ]]; then
    FILE_TYPE="APP"
    info "File type: APP (application bundle)"
elif [[ "$FILE_PATH" =~ \.pkg$ ]]; then
    FILE_TYPE="PKG"
    info "File type: PKG (installer package)"
else
    warning "Unknown file type, will try to notarize anyway"
    FILE_TYPE="UNKNOWN"
fi

# Verify file is signed
info "Verifying code signature..."

if [[ "$FILE_TYPE" == "DMG" ]]; then
    # For DMG, we can't directly verify, skip this check
    info "DMG signature check skipped (will be verified by Apple)"
elif [[ "$FILE_TYPE" == "APP" ]]; then
    if codesign --verify --deep --strict "$FILE_PATH" 2>&1; then
        success "Code signature valid"
    else
        error "Code signature verification failed"
        error "File must be signed before notarization"
        error "Run ./sign.sh first"
        exit 1
    fi

    # Check for hardened runtime
    if codesign -dvv "$FILE_PATH" 2>&1 | grep -q "flags=0x10000(runtime)"; then
        success "Hardened Runtime enabled"
    else
        warning "Hardened Runtime may not be enabled (required for notarization)"
    fi
fi

# Prepare notarization command arguments
NOTARIZE_ARGS=()

if [[ -n "$KEYCHAIN_PROFILE" ]]; then
    info "Using keychain profile: $KEYCHAIN_PROFILE"
    NOTARIZE_ARGS+=("--keychain-profile" "$KEYCHAIN_PROFILE")
else
    # Use credentials directly
    if [[ -z "$APPLE_ID" ]] || [[ -z "$TEAM_ID" ]] || [[ -z "$PASSWORD" ]]; then
        error "Must provide either --keychain or all of --apple-id, --team-id, --password"
        echo ""
        info "Recommended: Create a keychain profile first:"
        echo "  xcrun notarytool store-credentials \"grading-app\" \\"
        echo "    --apple-id \"your-email@example.com\" \\"
        echo "    --team-id \"ABC123XYZ\" \\"
        echo "    --password \"xxxx-xxxx-xxxx-xxxx\""
        exit 1
    fi

    info "Using Apple ID: $APPLE_ID"
    info "Using Team ID: $TEAM_ID"

    NOTARIZE_ARGS+=("--apple-id" "$APPLE_ID")
    NOTARIZE_ARGS+=("--team-id" "$TEAM_ID")
    NOTARIZE_ARGS+=("--password" "$PASSWORD")
fi

# Add wait flag
if $WAIT_FOR_COMPLETION; then
    NOTARIZE_ARGS+=("--wait")
    info "Will wait for notarization to complete"
else
    info "Will submit and return immediately"
fi

# Create temporary zip if APP bundle (notarization requires zip or dmg)
TEMP_ZIP=""
SUBMIT_FILE="$FILE_PATH"

if [[ "$FILE_TYPE" == "APP" ]]; then
    info "Creating temporary zip for app bundle..."
    TEMP_ZIP="/tmp/$(basename "$FILE_PATH" .app)-notarize.zip"

    # Remove old zip if exists
    if [[ -f "$TEMP_ZIP" ]]; then
        rm "$TEMP_ZIP"
    fi

    # Create zip using ditto (preserves code signatures)
    if ditto -c -k --keepParent "$FILE_PATH" "$TEMP_ZIP"; then
        success "Created zip: $TEMP_ZIP"
        SUBMIT_FILE="$TEMP_ZIP"
    else
        error "Failed to create zip"
        exit 1
    fi
fi

# Submit for notarization
echo ""
info "Submitting to Apple for notarization..."
info "This may take 5-30 minutes depending on Apple's load"
echo ""

SUBMISSION_ID=""
NOTARIZE_OUTPUT=$(mktemp)

if xcrun notarytool submit "$SUBMIT_FILE" "${NOTARIZE_ARGS[@]}" 2>&1 | tee "$NOTARIZE_OUTPUT"; then
    # Extract submission ID from output
    SUBMISSION_ID=$(grep -o -E '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' "$NOTARIZE_OUTPUT" | head -n 1)

    if [[ -n "$SUBMISSION_ID" ]]; then
        info "Submission ID: $SUBMISSION_ID"
    fi

    # Check if notarization succeeded
    if grep -q "status: Accepted" "$NOTARIZE_OUTPUT"; then
        echo ""
        success "Notarization completed successfully!"

        # Clean up temp files
        rm -f "$NOTARIZE_OUTPUT"
        if [[ -n "$TEMP_ZIP" ]]; then
            rm -f "$TEMP_ZIP"
        fi

        # Staple if requested
        if $AUTO_STAPLE; then
            echo ""
            info "Stapling notarization ticket..."

            if xcrun stapler staple "$FILE_PATH"; then
                success "Notarization ticket stapled successfully!"
            else
                error "Stapling failed"
                error "You can staple manually later with: xcrun stapler staple '$FILE_PATH'"
                exit 1
            fi

            # Verify stapling
            if xcrun stapler validate "$FILE_PATH" 2>&1; then
                success "Staple validation passed!"
            else
                warning "Staple validation failed"
            fi
        else
            echo ""
            info "To staple the notarization ticket, run:"
            echo "  xcrun stapler staple '$FILE_PATH'"
        fi

        echo ""
        echo -e "${GREEN}=====================================${NC}"
        echo -e "${GREEN}   Notarization Complete!${NC}"
        echo -e "${GREEN}=====================================${NC}"
        echo ""

        info "Next steps:"
        if ! $AUTO_STAPLE; then
            echo "  1. Staple ticket: xcrun stapler staple '$FILE_PATH'"
            echo "  2. Test download: Copy to another Mac and open"
            echo "  3. Distribute: Upload to your website or distribution channel"
        else
            echo "  1. Test download: Copy to another Mac and open"
            echo "  2. Distribute: Upload to your website or distribution channel"
        fi
        echo ""

        exit 0

    elif grep -q "status: Invalid" "$NOTARIZE_OUTPUT"; then
        echo ""
        error "Notarization failed: Invalid"
        error "The submission was rejected by Apple"
        echo ""

        if [[ -n "$SUBMISSION_ID" ]]; then
            info "Fetching detailed error log..."
            echo ""

            # Get detailed log
            if [[ -n "$KEYCHAIN_PROFILE" ]]; then
                xcrun notarytool log "$SUBMISSION_ID" --keychain-profile "$KEYCHAIN_PROFILE"
            else
                xcrun notarytool log "$SUBMISSION_ID" --apple-id "$APPLE_ID" --team-id "$TEAM_ID" --password "$PASSWORD"
            fi
        fi

        echo ""
        error "Common issues:"
        echo "  - Hardened Runtime not enabled (use --options runtime when signing)"
        echo "  - Not all binaries signed (sign frameworks and dylibs first)"
        echo "  - Missing secure timestamp (use --timestamp when signing)"
        echo "  - Code signature issues (verify with: codesign --verify --deep --strict)"
        echo ""

        # Clean up
        rm -f "$NOTARIZE_OUTPUT"
        if [[ -n "$TEMP_ZIP" ]]; then
            rm -f "$TEMP_ZIP"
        fi

        exit 1

    elif grep -q "status: In Progress" "$NOTARIZE_OUTPUT"; then
        echo ""
        info "Notarization is in progress"

        if [[ -n "$SUBMISSION_ID" ]]; then
            info "Check status with:"
            if [[ -n "$KEYCHAIN_PROFILE" ]]; then
                echo "  xcrun notarytool info $SUBMISSION_ID --keychain-profile '$KEYCHAIN_PROFILE'"
            else
                echo "  xcrun notarytool info $SUBMISSION_ID --apple-id '$APPLE_ID' --team-id '$TEAM_ID' --password '$PASSWORD'"
            fi
        fi

        # Clean up temp files
        rm -f "$NOTARIZE_OUTPUT"
        if [[ -n "$TEMP_ZIP" ]]; then
            rm -f "$TEMP_ZIP"
        fi

        exit 0
    fi

else
    error "Notarization submission failed"

    # Clean up
    rm -f "$NOTARIZE_OUTPUT"
    if [[ -n "$TEMP_ZIP" ]]; then
        rm -f "$TEMP_ZIP"
    fi

    exit 1
fi

# Clean up (shouldn't reach here, but just in case)
rm -f "$NOTARIZE_OUTPUT"
if [[ -n "$TEMP_ZIP" ]]; then
    rm -f "$TEMP_ZIP"
fi
