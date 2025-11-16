# macOS Code Signing and Notarization Setup Guide

## Overview

macOS code signing and notarization are required to distribute applications outside the Mac App Store without triggering Gatekeeper warnings. Starting with macOS 10.15 Catalina, all software must be notarized by Apple to run without user intervention.

## Why Code Signing and Notarization are Important

Without code signing and notarization:
- Gatekeeper shows "cannot be opened because the developer cannot be verified"
- Users must right-click → Open to bypass (confusing and reduces trust)
- Some versions of macOS block execution entirely
- Cannot distribute via standard download

With code signing and notarization:
- Professional appearance and user trust
- Seamless installation experience
- Required for macOS 10.15+ (Catalina and later)
- Proves application hasn't been tampered with
- Required for Mac App Store distribution

## Requirements Overview

### Apple Developer Program Membership

**Required**: Apple Developer Program
- **Cost**: $99 USD per year
- **Enrollment**: https://developer.apple.com/programs/
- **Account Types**:
  - Individual: Personal apps, your name appears
  - Organization: Company apps, company name appears
  - Enterprise: Internal distribution only (not for public apps)

### Certificates Needed

You'll need TWO certificates:

1. **Developer ID Application Certificate**
   - Signs application bundles (.app)
   - Signs frameworks and libraries
   - Required for distribution outside Mac App Store

2. **Developer ID Installer Certificate** (Optional)
   - Signs .pkg installer packages
   - Only needed if distributing via .pkg (not needed for .dmg or .app)
   - We primarily use .dmg, so this is optional

### macOS Version Requirements

- **For Signing**: macOS 10.12+ (any recent macOS)
- **For Notarization**: macOS 10.13.6+ with Xcode 10+ or Command Line Tools
- **Target Compatibility**: Signed apps work on macOS 10.9+
- **Notarization Requirement**: macOS 10.15+ Catalina requires notarization

## Apple Developer Program Enrollment

### Step 1: Create Apple ID

If you don't have an Apple ID:
1. Go to https://appleid.apple.com/
2. Create an account
3. Verify email address
4. Enable two-factor authentication (required)

### Step 2: Enroll in Developer Program

1. Go to https://developer.apple.com/programs/enroll/
2. Click "Start Your Enrollment"
3. Sign in with Apple ID
4. Choose account type:
   - **Individual**: Your personal name, faster approval
   - **Organization**: Company name, requires D-U-N-S number

### Step 3: Pay Enrollment Fee

- **Cost**: $99 USD per year
- **Payment**: Credit card, debit card, or Apple Pay
- **Auto-renewal**: Yes (can be disabled)
- **Renewal Date**: One year from enrollment

### Step 4: Verification Process

**For Individual Accounts**:
- Approval usually within 24-48 hours
- May require ID verification
- No additional documents needed

**For Organization Accounts**:
- Requires D-U-N-S number (free from Dun & Bradstreet)
- Legal entity verification (1-2 weeks)
- May require business documents
- Contact verification via phone

### Step 5: Access Developer Portal

Once approved:
1. Go to https://developer.apple.com/account/
2. Sign in with Apple ID
3. Accept agreements
4. Access to certificates, profiles, and tools

## Certificate Creation

### Prerequisites

1. **Xcode or Command Line Tools** installed:
   ```bash
   # Check if installed
   xcode-select -p

   # If not installed:
   xcode-select --install
   ```

2. **Access to Keychain Access app** (built into macOS)

### Generate Developer ID Application Certificate

#### Method 1: Via Xcode (Recommended)

1. **Open Xcode**
2. **Go to Settings**: Xcode → Settings (or Preferences)
3. **Accounts Tab**: Click "Accounts"
4. **Add Apple ID**:
   - Click "+" button
   - Sign in with your Apple Developer account
5. **Manage Certificates**:
   - Select your account
   - Click "Manage Certificates..."
   - Click "+" button
   - Choose "Developer ID Application"
6. **Certificate Created**:
   - Certificate automatically created and installed
   - Appears in Keychain Access

#### Method 2: Via Developer Portal (Manual)

1. **Go to**: https://developer.apple.com/account/resources/certificates/list
2. **Create Certificate**:
   - Click "+" button
   - Select "Developer ID Application"
   - Click "Continue"
3. **Create Certificate Request**:
   - Open "Keychain Access" on your Mac
   - Keychain Access → Certificate Assistant → Request a Certificate from a Certificate Authority
   - Enter your email (Apple ID email)
   - Select "Saved to disk"
   - Click "Continue"
   - Save as "CertificateSigningRequest.certSigningRequest"
4. **Upload Request**:
   - Back in Developer Portal
   - Upload .certSigningRequest file
   - Click "Continue"
5. **Download Certificate**:
   - Download the .cer file
   - Double-click to install in Keychain

### Generate Developer ID Installer Certificate (Optional)

Only needed if you plan to distribute .pkg installers:

1. **Go to**: https://developer.apple.com/account/resources/certificates/list
2. **Create Certificate**:
   - Click "+" button
   - Select "Developer ID Installer"
   - Follow same process as Application certificate

### Verify Certificate Installation

```bash
# List all Developer ID certificates
security find-identity -v -p codesigning

# You should see output like:
# 1) ABC123... "Developer ID Application: Your Name (TEAM_ID)"
# 2) DEF456... "Developer ID Installer: Your Name (TEAM_ID)"
```

## Certificate Management

### Certificate Storage

Certificates are stored in macOS Keychain:
- **Location**: Keychain Access → My Certificates
- **Export**: Right-click → Export (creates .p12 file)
- **Import**: Double-click .p12 file

### Certificate Validity

- **Duration**: Typically 5 years
- **Renewal**: Create new certificate before expiry
- **Revocation**: Can be revoked via Developer Portal
- **Multiple Machines**: Export .p12 and import on other Macs

### Certificate Backup

**Important**: Backup your certificates!

```bash
# Export certificate (requires password)
security export -k login.keychain -t identities -f pkcs12 \
  -o developer_id_backup.p12

# Import on another Mac
security import developer_id_backup.p12 -k login.keychain
```

**Best Practices**:
- Export to encrypted external drive
- Store password in secure location (password manager)
- Test restore process annually
- Keep backup separate from Mac

### Team ID

Your Team ID is a 10-character identifier:
- **Find it**: https://developer.apple.com/account/ (Membership section)
- **Format**: ABC123XYZ (example)
- **Usage**: Required for some signing operations
- **Unique**: One per Apple Developer account

## App-Specific Password for Notarization

Notarization requires an app-specific password (not your Apple ID password):

### Create App-Specific Password

1. **Go to**: https://appleid.apple.com/
2. **Sign in**: Use your Apple ID
3. **Security Section**: Find "App-Specific Passwords"
4. **Generate Password**:
   - Click "Generate Password..."
   - Label: "notarization" or "grading-app-notarization"
   - Copy the generated password (format: xxxx-xxxx-xxxx-xxxx)
5. **Save Password**: Store securely (you can't view it again)

### Store Password in Keychain (Recommended)

```bash
# Store in keychain for automatic use
xcrun notarytool store-credentials "grading-app-notarization" \
  --apple-id "your-email@example.com" \
  --team-id "ABC123XYZ" \
  --password "xxxx-xxxx-xxxx-xxxx"

# This creates a keychain profile you can reference later
```

## Hardened Runtime

Starting with macOS 10.14 Mojave, apps must enable "Hardened Runtime":

### What is Hardened Runtime?

- Security feature that protects against code injection
- Required for notarization
- Restricts certain operations unless entitled

### Enable Hardened Runtime

When signing, add `--options runtime`:

```bash
codesign --force --options runtime \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  YourApp.app
```

### Entitlements

Some apps need specific entitlements (exceptions to Hardened Runtime):

**Common Entitlements**:
- `com.apple.security.cs.allow-unsigned-executable-memory`: For JIT compilation
- `com.apple.security.cs.allow-dyld-environment-variables`: For dynamic loading
- `com.apple.security.cs.disable-library-validation`: For loading external libraries

**Create entitlements.plist** (if needed):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
</dict>
</plist>
```

**Sign with entitlements**:
```bash
codesign --force --options runtime \
  --entitlements entitlements.plist \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  YourApp.app
```

## Notarization Process Overview

Notarization is Apple's malware scanning service:

1. **Sign Application**: Code sign with Developer ID
2. **Create Archive**: Zip or DMG the app
3. **Submit to Apple**: Upload for scanning
4. **Wait for Results**: Usually 5-30 minutes
5. **Staple Ticket**: Attach notarization ticket to app
6. **Distribute**: App now passes Gatekeeper

### Notarization Requirements

- macOS 10.9+ SDK (target)
- Hardened Runtime enabled
- Developer ID certificate (not Mac App Store cert)
- All binaries signed with secure timestamp
- No issues detected by Apple's automated scan

## Cost Summary

### Initial Setup Costs
- Apple Developer Program: $99/year
- macOS machine: Required (existing Mac)
- Xcode/Command Line Tools: Free
- Total: $99 first year

### Ongoing Costs
- Apple Developer Program renewal: $99/year
- No per-app or per-notarization fees
- Unlimited signing and notarization
- Total: $99/year

### Multi-Year Planning
- Year 1: $99 (enrollment)
- Year 2: $99 (renewal)
- Year 3: $99 (renewal)
- Average: $99/year indefinitely

## Signing Process Overview

Once certificates are installed:

1. **Sign All Binaries**: Sign frameworks, dylibs, executables
2. **Sign App Bundle**: Sign .app with Developer ID
3. **Create DMG**: Package app in distributable format
4. **Sign DMG**: Sign the .dmg file
5. **Notarize**: Submit to Apple for scanning
6. **Staple**: Attach notarization ticket
7. **Distribute**: Upload to website or distribute

See `sign.sh` and `notarize.sh` for detailed implementation.

## Common Issues and Troubleshooting

### "No identity found" when signing

**Cause**: Certificate not installed or not visible to codesign

**Solution**:
```bash
# List available identities
security find-identity -v -p codesigning

# If empty, certificate not installed
# Re-download from Developer Portal or import .p12 backup
```

### "The application is not signed at all"

**Cause**: Signing failed or was incomplete

**Solution**:
```bash
# Verify signature
codesign --verify --deep --strict --verbose=2 YourApp.app

# Re-sign if needed
codesign --force --deep --sign "Developer ID Application: Your Name" YourApp.app
```

### "Hardened Runtime not enabled"

**Cause**: Forgot `--options runtime` when signing

**Solution**:
```bash
# Re-sign with Hardened Runtime
codesign --force --options runtime \
  --sign "Developer ID Application: Your Name" \
  YourApp.app
```

### Notarization fails with "Invalid"

**Cause**: Various issues (check Apple's email for details)

**Common Solutions**:
- Ensure Hardened Runtime enabled
- Sign all binaries (frameworks, dylibs)
- Use secure timestamp: `--timestamp`
- Check for forbidden APIs or frameworks

### "Error: Unable to find notarization record"

**Cause**: Submission didn't complete or wrong request ID

**Solution**:
```bash
# Check recent submissions
xcrun notarytool history --keychain-profile "grading-app-notarization"

# Get specific submission info
xcrun notarytool info <submission-id> --keychain-profile "grading-app-notarization"
```

### Stapling fails

**Cause**: Notarization not complete or .dmg format issue

**Solution**:
```bash
# Verify notarization completed first
xcrun notarytool info <submission-id> --keychain-profile "grading-app-notarization"

# Ensure DMG format is correct (UDIF)
hdiutil convert input.dmg -format UDZO -o output.dmg

# Try stapling again
xcrun stapler staple output.dmg
```

## Security Best Practices

1. **Protect Certificates**: Never share or commit to source control
2. **Enable 2FA**: Required for Apple Developer account
3. **Backup Certificates**: Export .p12 to secure location
4. **Rotate Certificates**: Renew before expiry (5 years)
5. **Limit Access**: Only trusted team members can sign
6. **Audit Releases**: Verify every signed build
7. **Monitor Account**: Check Developer Portal regularly
8. **Secure App Password**: Store in password manager
9. **Use Keychain Profiles**: Avoid hardcoding credentials
10. **Test Before Release**: Verify on fresh macOS install

## Automation and CI/CD

### Local Machine Signing

Recommended for initial setup:
- Keep certificates on development Mac
- Use keychain profiles for notarization
- Run signing scripts manually or via build script

### CI/CD Signing (GitHub Actions, etc.)

More complex, requires secure credential storage:

**Option 1: Import Certificates in CI**
- Store .p12 as encrypted secret
- Import to keychain in CI runner
- Sign and notarize in pipeline
- Clean up keychain after

**Option 2: Self-Hosted Runner**
- Mac mini or macOS VM as runner
- Certificates installed locally
- More secure than cloud runners
- Recommended for production

**Option 3: Separate Signing Machine**
- Build in CI, transfer to Mac for signing
- Sign on dedicated Mac
- Upload signed build back to CI
- Most secure, but complex

See main CODE_SIGNING_GUIDE.md for CI/CD examples.

## Alternative: Mac App Store Distribution

If you're considering Mac App Store:

**Pros**:
- No notarization needed (different process)
- Apple handles distribution
- Automatic updates via App Store
- More user trust

**Cons**:
- Apple takes 30% commission (15% for small business)
- Strict review process
- Sandboxing requirements (very restrictive)
- Cannot use some APIs we need

**Recommendation**: For Grading App, direct distribution (notarization) is better due to sandboxing limitations.

## Next Steps

1. **Enroll**: Join Apple Developer Program ($99)
2. **Wait for Approval**: 24-48 hours (individual) or 1-2 weeks (organization)
3. **Install Xcode**: Or Command Line Tools
4. **Create Certificates**: Developer ID Application via Xcode
5. **Create App Password**: For notarization
6. **Store in Keychain**: Use `notarytool store-credentials`
7. **Test Signing**: Use `sign.sh` on test app
8. **Test Notarization**: Use `notarize.sh` on signed app
9. **Verify on Fresh Mac**: Download and test
10. **Document Team ID**: Save for scripts

## Resources

- **Apple Developer Portal**: https://developer.apple.com/account/
- **Code Signing Guide**: https://developer.apple.com/support/code-signing/
- **Notarization Guide**: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
- **Hardened Runtime**: https://developer.apple.com/documentation/security/hardened_runtime
- **Entitlements**: https://developer.apple.com/documentation/bundleresources/entitlements
- **Gatekeeper**: https://support.apple.com/guide/security/gatekeeper-sec5599b66df/web

## Support

If you encounter issues:
1. **Apple Developer Support**: https://developer.apple.com/support/
2. **Technical Support Incidents**: 2 included free per year with membership
3. **Developer Forums**: https://developer.apple.com/forums/
4. **Stack Overflow**: Tag with [macos], [code-signing], [notarization]
5. **Professional Services**: Consider hiring macOS consultant for initial setup

---

**Note**: This guide is current as of 2025. Apple's requirements and processes may change. Always refer to official Apple documentation for the latest information.
