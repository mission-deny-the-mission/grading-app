# macOS Code Signing and Notarization Verification Guide

## Overview

This guide covers how to verify code signatures and notarization on macOS applications, ensuring they pass Gatekeeper checks and provide a smooth installation experience.

## Verification Steps

### 1. Verify Code Signature

Before notarizing or distributing, verify the application is properly signed.

#### Basic Signature Verification

```bash
# Verify signature exists and is valid
codesign --verify --deep --strict --verbose=2 YourApp.app

# Expected output:
# YourApp.app: valid on disk
# YourApp.app: satisfies its Designated Requirement
```

**What to check**:
- "valid on disk" message appears
- No error messages
- No warnings about modified files

#### Display Signature Information

```bash
# Show detailed signature information
codesign -dvv YourApp.app

# Key information to verify:
# - Authority: Developer ID Application: Your Name (TEAM_ID)
# - Timestamp: Should show a valid timestamp
# - Runtime Version: Should be present (hardened runtime)
# - Identifier: Should match your bundle identifier
```

**Expected output**:
```
Executable=/path/to/YourApp.app/Contents/MacOS/YourApp
Identifier=com.yourcompany.gradingapp
Format=app bundle with Mach-O universal (x86_64 arm64)
CodeDirectory v=20500 size=1234 flags=0x10000(runtime) hashes=50+5 location=embedded
Hash type=sha256 size=32
...
Authority=Developer ID Application: Your Name (ABC123XYZ)
Authority=Developer ID Certification Authority
Authority=Apple Root CA
Timestamp=Jan 15, 2025 at 10:30:00 AM
Info.plist entries=25
TeamIdentifier=ABC123XYZ
Runtime Version=10.14.0
...
Sealed Resources version=2 rules=13 files=42
```

#### Check for Hardened Runtime

Critical for notarization:

```bash
# Check if hardened runtime is enabled
codesign -dvv YourApp.app 2>&1 | grep -i runtime

# Should show:
# flags=0x10000(runtime)
# Runtime Version=10.14.0
```

**If missing**: Re-sign with `--options runtime` flag.

#### Verify All Nested Code

Ensure all frameworks, libraries, and executables are signed:

```bash
# Verify all nested code recursively
codesign --verify --deep --strict YourApp.app

# Check specific components
codesign --verify --verbose=4 YourApp.app/Contents/Frameworks/SomeFramework.framework
codesign --verify --verbose=4 YourApp.app/Contents/MacOS/helper-binary
```

**What to check**:
- No "not signed" errors
- All frameworks are signed
- All dylibs are signed
- Helper apps are signed

### 2. Verify Timestamp

Timestamps allow signatures to remain valid after certificate expiration.

```bash
# Check for secure timestamp
codesign -dvv YourApp.app 2>&1 | grep Timestamp

# Expected:
# Timestamp=Jan 15, 2025 at 10:30:00 AM
```

**If "Timestamp=none"**:
- Re-sign with `--timestamp` option
- Use Apple's timestamp server (default)
- Without timestamp, signature expires with certificate

### 3. Verify Entitlements

If you used entitlements, verify they're correctly applied:

```bash
# Display entitlements
codesign -d --entitlements - YourApp.app

# Or save to file for inspection
codesign -d --entitlements entitlements.xml YourApp.app
cat entitlements.xml
```

**Common entitlements** for desktop apps:
- `com.apple.security.cs.allow-unsigned-executable-memory`: JIT compilation
- `com.apple.security.cs.allow-dyld-environment-variables`: Dynamic loading
- `com.apple.security.cs.disable-library-validation`: External plugins

### 4. Check Certificate Chain

Verify the certificate chain is complete and trusted:

```bash
# View certificate chain
codesign -dvv YourApp.app 2>&1 | grep Authority

# Expected chain:
# Authority=Developer ID Application: Your Name (TEAM_ID)
# Authority=Developer ID Certification Authority
# Authority=Apple Root CA
```

**Valid chain requirements**:
- Three authorities (your cert, intermediate CA, root CA)
- All certificates trusted
- No expired certificates in chain

### 5. Test Gatekeeper

Simulate what users will experience:

```bash
# Check if Gatekeeper will allow the app
spctl --assess --verbose=4 --type execute YourApp.app

# Expected for signed app:
# YourApp.app: accepted
# source=Developer ID

# Expected for notarized app:
# YourApp.app: accepted
# source=Notarized Developer ID
# origin=Developer ID Application: Your Name (TEAM_ID)
```

**Status meanings**:
- `accepted` + `source=Notarized Developer ID`: Perfect (signed + notarized)
- `accepted` + `source=Developer ID`: Good (signed, may need notarization for 10.15+)
- `rejected`: Problem with signature or not signed

### 6. Verify Notarization Status

After notarizing, verify the notarization ticket is attached:

#### Check Notarization Online

```bash
# Check if Apple has a notarization record (requires internet)
xcrun stapler validate YourApp.app

# Expected:
# Processing: YourApp.app
# The validate action worked!
```

#### Check Stapled Ticket

```bash
# Verify ticket is stapled to app
stapler validate -v YourApp.app

# Or check for ticket manually
xattr -l YourApp.app | grep com.apple.quarantine
```

**If not stapled**:
```bash
# Staple the ticket (after successful notarization)
xcrun stapler staple YourApp.app

# Verify again
xcrun stapler validate YourApp.app
```

### 7. Test Download Experience

Best way to verify real user experience:

#### Option 1: Test with Quarantine Attribute

```bash
# Simulate download by adding quarantine attribute
xattr -w com.apple.quarantine "0001;$(date +%s);Safari;12345678-1234-1234-1234-123456789012" YourApp.app

# Try to open
open YourApp.app

# Expected: Should open without warnings (if notarized)
# If not notarized: Gatekeeper warning will appear

# Remove quarantine after test
xattr -d com.apple.quarantine YourApp.app
```

#### Option 2: Test with Clean macOS VM

1. **Set up clean macOS VM**:
   - macOS 10.15+ (Catalina or later)
   - Fresh install, all updates applied
   - Gatekeeper enabled (default)

2. **Transfer app**:
   - Upload to temporary web server
   - Download via Safari in VM
   - Or transfer via AirDrop

3. **Open app**:
   - Double-click to open
   - Observe any warnings or dialogs

4. **Expected behavior**:
   - **Notarized**: Opens immediately, no warnings
   - **Signed only**: May show Gatekeeper warning on 10.15+
   - **Not signed**: Blocked by Gatekeeper

## Notarization Verification

### Check Submission Status

After submitting for notarization:

```bash
# List recent submissions
xcrun notarytool history --keychain-profile "grading-app"

# Get specific submission info
xcrun notarytool info <submission-id> --keychain-profile "grading-app"

# Expected status:
# status: Accepted
```

### Get Notarization Log

If notarization fails, get detailed log:

```bash
# Fetch log for failed submission
xcrun notarytool log <submission-id> --keychain-profile "grading-app"

# Or save to file
xcrun notarytool log <submission-id> --keychain-profile "grading-app" > notarization-log.json
cat notarization-log.json | python3 -m json.tool
```

**Common issues in log**:
- Missing hardened runtime
- Unsigned frameworks or dylibs
- Invalid entitlements
- Code signature issues

### Verify Notarization Ticket

After stapling:

```bash
# Verify ticket is present and valid
xcrun stapler validate -v YourApp.app

# Check ticket metadata
xcrun stapler info YourApp.app
```

## DMG Verification

If distributing via DMG:

### Verify DMG Signature

```bash
# Check if DMG is signed
codesign --verify --deep --strict --verbose=2 GradingApp.dmg

# Display DMG signature info
codesign -dvv GradingApp.dmg
```

### Verify DMG Notarization

```bash
# Check notarization status
xcrun stapler validate GradingApp.dmg

# Test with Gatekeeper
spctl --assess --verbose=4 --type install GradingApp.dmg
```

### Test DMG Mount and Install

```bash
# Mount DMG
hdiutil attach GradingApp.dmg

# Verify mounted app
codesign --verify --deep /Volumes/GradingApp/GradingApp.app
spctl --assess --verbose=4 /Volumes/GradingApp/GradingApp.app

# Unmount
hdiutil detach /Volumes/GradingApp
```

## Verification Checklist

Before distributing your signed and notarized application:

### Pre-Distribution Checklist

- [ ] Code signature verified: `codesign --verify --deep --strict`
- [ ] Hardened runtime enabled: `flags=0x10000(runtime)`
- [ ] Timestamp present: Not "Timestamp=none"
- [ ] Certificate chain complete: 3 authorities shown
- [ ] Developer ID certificate used (not Mac App Store cert)
- [ ] All nested frameworks/dylibs signed
- [ ] Entitlements correct (if used)
- [ ] Gatekeeper accepts app: `spctl --assess`
- [ ] Submitted for notarization
- [ ] Notarization status: "Accepted"
- [ ] Notarization ticket stapled: `stapler validate`
- [ ] Tested on clean macOS VM (10.15+)
- [ ] App opens without Gatekeeper warnings
- [ ] DMG signed (if distributing via DMG)
- [ ] DMG notarized (if distributing via DMG)

### Post-Distribution Monitoring

- [ ] Monitor user reports of Gatekeeper issues
- [ ] Verify downloads work from distribution channel
- [ ] Test on latest macOS version periodically
- [ ] Check certificate expiry (set reminders 45 days before)
- [ ] Re-verify signature monthly
- [ ] Watch for Apple notarization policy changes
- [ ] Update signature if certificate is renewed

## Troubleshooting Common Issues

### Issue: "Code object is not signed at all"

**Cause**: Application or component is not signed.

**Solution**:
```bash
# Sign the application
./sign.sh YourApp.app

# Verify all components signed
codesign --verify --deep YourApp.app
```

### Issue: "Code signature invalid"

**Cause**: File was modified after signing, or signature is corrupted.

**Solution**:
```bash
# Check what's invalid
codesign --verify --deep --strict --verbose=4 YourApp.app

# Re-sign
./sign.sh --force YourApp.app
```

### Issue: "Hardened Runtime not enabled"

**Cause**: Signed without `--options runtime` flag.

**Solution**:
```bash
# Re-sign with hardened runtime
./sign.sh --force YourApp.app

# Verify
codesign -dvv YourApp.app 2>&1 | grep runtime
```

### Issue: Notarization fails with "Invalid"

**Cause**: Various code signing or format issues.

**Solution**:
```bash
# Get detailed error log
xcrun notarytool log <submission-id> --keychain-profile "grading-app"

# Common fixes:
# 1. Enable hardened runtime: --options runtime
# 2. Sign all nested code: sign frameworks first
# 3. Use secure timestamp: --timestamp
# 4. Fix entitlements: check entitlements.plist

# Re-sign and re-submit
./sign.sh --force YourApp.app
./notarize.sh YourApp.app
```

### Issue: "Could not staple ticket"

**Cause**: Notarization not complete, or file format issue.

**Solution**:
```bash
# Check notarization status first
xcrun notarytool info <submission-id> --keychain-profile "grading-app"

# Wait if still "In Progress"
# If "Accepted", try stapling again
xcrun stapler staple YourApp.app

# For DMG issues, recreate with correct format
hdiutil create -srcfolder YourApp.app -format UDZO output.dmg
./notarize.sh output.dmg
xcrun stapler staple output.dmg
```

### Issue: Gatekeeper blocks app: "cannot be opened"

**Cause**: Not notarized, or notarization ticket not stapled.

**Solution**:
```bash
# Check if notarized
xcrun stapler validate YourApp.app

# If not notarized, submit
./notarize.sh YourApp.app

# Staple ticket
xcrun stapler staple YourApp.app

# Test again
spctl --assess --verbose=4 YourApp.app
```

### Issue: "The identity used for signing is not valid"

**Cause**: Certificate expired, revoked, or wrong certificate type.

**Solution**:
```bash
# Check certificate validity
security find-identity -v -p codesigning

# Look for "Developer ID Application" certificate
# Check expiration date

# If expired, renew certificate via Apple Developer Portal
# If revoked, contact Apple Developer Support
# If wrong type, get correct Developer ID certificate
```

### Issue: Gatekeeper shows "damaged" message

**Cause**: Quarantine attribute with invalid signature.

**Solution**:
```bash
# Remove quarantine
xattr -d com.apple.quarantine YourApp.app

# Verify signature
codesign --verify --deep YourApp.app

# If signature is valid, re-notarize
./notarize.sh YourApp.app
xcrun stapler staple YourApp.app
```

## Testing Tools

### Recommended Testing Tools

1. **codesign** (built into macOS)
   - Signature verification
   - Display signature information
   - Required for all testing

2. **spctl** (built into macOS)
   - Gatekeeper assessment
   - Simulates user experience
   - Tests if app will be allowed to run

3. **stapler** (built into macOS)
   - Notarization ticket management
   - Stapling and validation
   - Required for distribution

4. **notarytool** (Xcode Command Line Tools)
   - Notarization submission
   - Status checking
   - Log retrieval

5. **hdiutil** (built into macOS)
   - DMG creation and verification
   - Mounting and testing
   - Format conversion

### Automated Verification Script

Create a bash script for consistent verification:

```bash
#!/bin/bash
# verify-signature.sh

APP_PATH="$1"

if [[ -z "$APP_PATH" ]]; then
    echo "Usage: $0 <app_path>"
    exit 1
fi

echo "Verifying: $APP_PATH"
echo ""

# 1. Basic signature verification
echo "[TEST] Code signature validation..."
if codesign --verify --deep --strict "$APP_PATH" 2>&1; then
    echo "[PASS] Signature is valid"
else
    echo "[FAIL] Signature verification failed"
    exit 1
fi

# 2. Check hardened runtime
echo "[TEST] Hardened runtime..."
if codesign -dvv "$APP_PATH" 2>&1 | grep -q "flags=0x10000(runtime)"; then
    echo "[PASS] Hardened runtime enabled"
else
    echo "[FAIL] Hardened runtime not enabled"
    exit 1
fi

# 3. Check timestamp
echo "[TEST] Secure timestamp..."
if codesign -dvv "$APP_PATH" 2>&1 | grep -q "Timestamp="; then
    echo "[PASS] Timestamp present"
else
    echo "[FAIL] No timestamp found"
    exit 1
fi

# 4. Gatekeeper assessment
echo "[TEST] Gatekeeper assessment..."
if spctl --assess --verbose=4 "$APP_PATH" 2>&1 | grep -q "accepted"; then
    echo "[PASS] Gatekeeper accepts app"
else
    echo "[FAIL] Gatekeeper rejects app"
    exit 1
fi

# 5. Notarization check
echo "[TEST] Notarization status..."
if xcrun stapler validate "$APP_PATH" 2>&1 | grep -q "The validate action worked"; then
    echo "[PASS] Notarization ticket present"
else
    echo "[WARN] No notarization ticket (may not be required)"
fi

echo ""
echo "[SUCCESS] All critical checks passed!"
```

## Best Practices

1. **Always verify signatures** before distributing
2. **Test on clean macOS VM** (10.15+ Catalina or later)
3. **Test download from web** to simulate user experience
4. **Check notarization logs** if submission fails
5. **Staple tickets** immediately after notarization
6. **Keep certificates backed up** and secure
7. **Set expiry reminders** for certificate renewal (5 years)
8. **Document verification process** in release checklist
9. **Automate verification** in build pipeline
10. **Re-verify after updates** or patches

## Support and Resources

- **Code Signing Guide**: https://developer.apple.com/support/code-signing/
- **Notarization Guide**: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
- **Gatekeeper**: https://support.apple.com/guide/security/gatekeeper-sec5599b66df/web
- **codesign man page**: `man codesign`
- **spctl man page**: `man spctl`
- **Apple Developer Support**: https://developer.apple.com/support/

---

**Note**: Gatekeeper and notarization requirements may change with macOS updates. Always test on the latest macOS version before major releases.
