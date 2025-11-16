# Code Signing and Notarization Guide

## Overview

This guide provides a comprehensive overview of code signing for the Grading App desktop application across Windows and macOS platforms. Code signing prevents security warnings and builds user trust when distributing desktop applications.

## Table of Contents

1. [Why Code Signing Matters](#why-code-signing-matters)
2. [Platform Requirements](#platform-requirements)
3. [Quick Start](#quick-start)
4. [Platform-Specific Guides](#platform-specific-guides)
5. [Verification](#verification)
6. [CI/CD Integration](#cicd-integration)
7. [Cost Summary](#cost-summary)
8. [Troubleshooting](#troubleshooting)

## Why Code Signing Matters

### Without Code Signing

**Windows**:
- SmartScreen shows "Windows protected your PC" warning
- Users must click "More info" → "Run anyway"
- Severely impacts user trust and adoption
- May be flagged by antivirus software

**macOS**:
- Gatekeeper shows "cannot be opened because developer cannot be verified"
- Users must right-click → Open to bypass
- On 10.15+ (Catalina), some apps are completely blocked
- Confusing and reduces trust

### With Code Signing

**Windows**:
- Professional appearance
- Builds SmartScreen reputation over time
- EV certificates provide immediate trust
- Required for Windows Store

**macOS**:
- Seamless installation experience
- Required for macOS 10.15+ (Catalina and later)
- Proves application hasn't been tampered with
- No Gatekeeper warnings

## Platform Requirements

### Windows

**Certificate Required**: EV (Extended Validation) Code Signing Certificate

**Key Requirements**:
- Cost: $300-500 per year
- Hardware token (USB) required for EV
- Validation: 2-7 business days
- Immediate SmartScreen reputation

**Recommended Providers**:
- DigiCert (~$474/year)
- Sectigo (~$315/year)
- GlobalSign (~$399/year)
- SSL.com (~$299/year)

**See**: [windows/SIGNING_SETUP.md](windows/SIGNING_SETUP.md)

### macOS

**Certificate Required**: Developer ID Application Certificate

**Key Requirements**:
- Apple Developer Program: $99 per year
- Two-factor authentication required
- Validation: 24-48 hours (individual), 1-2 weeks (organization)
- Notarization required for macOS 10.15+

**Process**:
1. Enroll in Apple Developer Program
2. Create Developer ID Application certificate
3. Sign application with Hardened Runtime
4. Submit to Apple for notarization (malware scan)
5. Staple notarization ticket to app
6. Distribute

**See**: [macos/SIGNING_SETUP.md](macos/SIGNING_SETUP.md)

### Linux

**No Code Signing Required**: Linux users expect to verify downloads via checksums or GPG signatures. AppImage and DEB packages don't require platform-level code signing.

**Optional**: GPG signature for repository distribution (for advanced users).

## Quick Start

### Windows Quick Start

1. **Acquire Certificate** (one-time setup):
   ```
   - Choose provider (Sectigo, DigiCert, etc.)
   - Complete validation (2-7 days)
   - Receive hardware token
   - Install certificate
   ```
   See: [windows/SIGNING_SETUP.md](windows/SIGNING_SETUP.md)

2. **Sign Executable**:
   ```powershell
   # Auto-detect certificate and sign
   .\desktop\installer\windows\sign.ps1 -ExePath "dist\GradingApp.exe"

   # Specify certificate explicitly
   .\desktop\installer\windows\sign.ps1 -ExePath "dist\GradingApp.exe" -Thumbprint "ABC123..."
   ```

3. **Verify Signature**:
   ```powershell
   signtool verify /pa dist\GradingApp.exe
   Get-AuthenticodeSignature dist\GradingApp.exe
   ```
   See: [windows/VERIFICATION.md](windows/VERIFICATION.md)

### macOS Quick Start

1. **Enroll in Apple Developer Program** (one-time setup):
   ```
   - Go to https://developer.apple.com/programs/
   - Pay $99/year
   - Wait for approval (24-48 hours)
   - Create Developer ID Application certificate
   ```
   See: [macos/SIGNING_SETUP.md](macos/SIGNING_SETUP.md)

2. **Create App-Specific Password** (one-time setup):
   ```bash
   # Go to https://appleid.apple.com/
   # Generate app-specific password
   # Store in keychain
   xcrun notarytool store-credentials "grading-app" \
     --apple-id "your-email@example.com" \
     --team-id "ABC123XYZ" \
     --password "xxxx-xxxx-xxxx-xxxx"
   ```

3. **Sign Application**:
   ```bash
   # Auto-detect certificate and sign
   ./desktop/installer/macos/sign.sh dist/GradingApp.app

   # Specify identity explicitly
   ./desktop/installer/macos/sign.sh \
     --identity "Developer ID Application: Your Name (ABC123XYZ)" \
     dist/GradingApp.app
   ```

4. **Create DMG** (optional but recommended):
   ```bash
   hdiutil create -srcfolder dist/GradingApp.app -format UDZO \
     -volname "Grading App" dist/GradingApp.dmg
   ```

5. **Notarize**:
   ```bash
   # Submit for notarization and staple
   ./desktop/installer/macos/notarize.sh \
     --keychain "grading-app" \
     --staple \
     dist/GradingApp.dmg
   ```

6. **Verify**:
   ```bash
   codesign --verify --deep --strict dist/GradingApp.app
   spctl --assess --verbose=4 dist/GradingApp.dmg
   xcrun stapler validate dist/GradingApp.dmg
   ```
   See: [macos/VERIFICATION.md](macos/VERIFICATION.md)

## Platform-Specific Guides

### Windows

| Document | Description |
|----------|-------------|
| [windows/SIGNING_SETUP.md](windows/SIGNING_SETUP.md) | Complete guide to acquiring and installing Windows code signing certificates |
| [windows/sign.ps1](windows/sign.ps1) | PowerShell script for signing Windows executables |
| [windows/VERIFICATION.md](windows/VERIFICATION.md) | Guide to verifying signatures and testing SmartScreen |

**Key Features**:
- Auto-detection of installed certificates
- Support for hardware tokens and .pfx files
- Secure timestamp server integration
- Comprehensive error handling and logging
- SmartScreen reputation guidance

### macOS

| Document | Description |
|----------|-------------|
| [macos/SIGNING_SETUP.md](macos/SIGNING_SETUP.md) | Complete guide to Apple Developer Program enrollment and certificate setup |
| [macos/sign.sh](macos/sign.sh) | Bash script for signing macOS applications with Hardened Runtime |
| [macos/notarize.sh](macos/notarize.sh) | Bash script for submitting to Apple's notarization service |
| [macos/VERIFICATION.md](macos/VERIFICATION.md) | Guide to verifying signatures, notarization, and Gatekeeper testing |

**Key Features**:
- Automatic signing of nested frameworks and libraries
- Hardened Runtime enforcement (required for notarization)
- Secure timestamp integration
- Notarization submission with wait support
- Automatic ticket stapling
- Comprehensive Gatekeeper testing

## Verification

### Pre-Distribution Checklist

Before releasing a signed build, verify:

**Windows**:
- [ ] Signature verified: `signtool verify /pa`
- [ ] Certificate details correct
- [ ] Timestamp present
- [ ] Tested on clean Windows VM
- [ ] SmartScreen behavior documented (EV vs. Standard cert)
- [ ] No red warnings on test machine

**macOS**:
- [ ] Code signature verified: `codesign --verify --deep --strict`
- [ ] Hardened Runtime enabled
- [ ] Timestamp present
- [ ] Gatekeeper accepts: `spctl --assess`
- [ ] Notarization successful
- [ ] Ticket stapled: `xcrun stapler validate`
- [ ] Tested on clean macOS 10.15+ VM
- [ ] No Gatekeeper warnings

**See Platform-Specific Verification Guides**:
- [windows/VERIFICATION.md](windows/VERIFICATION.md)
- [macos/VERIFICATION.md](macos/VERIFICATION.md)

## CI/CD Integration

### Overview

Automating code signing in CI/CD pipelines requires careful security consideration. Here are recommended approaches for each platform.

### GitHub Actions - Windows

**Recommended Approach**: Use cloud signing service (SSL.com eSigner) or self-hosted runner with hardware token.

#### Option 1: Cloud Signing (Easiest)

```yaml
name: Build and Sign Windows

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v3

      - name: Build Application
        run: |
          # Your build commands here
          pyinstaller grading-app.spec

      - name: Sign with SSL.com eSigner
        env:
          ESIGNER_USERNAME: ${{ secrets.ESIGNER_USERNAME }}
          ESIGNER_PASSWORD: ${{ secrets.ESIGNER_PASSWORD }}
          ESIGNER_TOTP_SECRET: ${{ secrets.ESIGNER_TOTP_SECRET }}
        run: |
          # Install SSL.com eSigner
          # Sign executable via cloud
          # See SSL.com documentation

      - name: Verify Signature
        run: |
          signtool verify /pa dist/GradingApp.exe
```

#### Option 2: Self-Hosted Runner (Most Secure)

```yaml
name: Build and Sign Windows

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: self-hosted  # Windows machine with hardware token

    steps:
      - uses: actions/checkout@v3

      - name: Build Application
        run: pyinstaller grading-app.spec

      - name: Sign Executable
        run: |
          .\desktop\installer\windows\sign.ps1 -ExePath "dist\GradingApp.exe"

      - name: Verify Signature
        run: |
          signtool verify /pa dist\GradingApp.exe
```

**Security Notes**:
- Hardware token remains on self-hosted runner
- No credentials stored in GitHub
- Most secure option for EV certificates

#### Option 3: Software Certificate (Not Recommended for EV)

```yaml
name: Build and Sign Windows

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v3

      - name: Build Application
        run: pyinstaller grading-app.spec

      - name: Import Certificate
        env:
          CERTIFICATE_BASE64: ${{ secrets.CERTIFICATE_BASE64 }}
          CERTIFICATE_PASSWORD: ${{ secrets.CERTIFICATE_PASSWORD }}
        run: |
          # Decode certificate from base64
          $cert = [System.Convert]::FromBase64String($env:CERTIFICATE_BASE64)
          [IO.File]::WriteAllBytes("cert.pfx", $cert)

          # Import to temporary store
          certutil -importpfx cert.pfx $env:CERTIFICATE_PASSWORD

      - name: Sign Executable
        env:
          CERTIFICATE_PASSWORD: ${{ secrets.CERTIFICATE_PASSWORD }}
        run: |
          .\desktop\installer\windows\sign.ps1 `
            -ExePath "dist\GradingApp.exe" `
            -CertPath "cert.pfx" `
            -Password $env:CERTIFICATE_PASSWORD

      - name: Cleanup
        if: always()
        run: Remove-Item cert.pfx -ErrorAction SilentlyContinue
```

**Security Notes**:
- Store .pfx as base64-encoded secret
- Only works with software certificates (not EV hardware tokens)
- Less secure than hardware token or cloud signing

### GitHub Actions - macOS

**Recommended Approach**: Import certificate in CI or use self-hosted runner.

#### Option 1: Import Certificate in CI

```yaml
name: Build and Sign macOS

on:
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: macos-latest

    steps:
      - uses: actions/checkout@v3

      - name: Import Certificate
        env:
          CERTIFICATE_BASE64: ${{ secrets.MACOS_CERTIFICATE_BASE64 }}
          CERTIFICATE_PASSWORD: ${{ secrets.MACOS_CERTIFICATE_PASSWORD }}
          KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}
        run: |
          # Create temporary keychain
          security create-keychain -p "$KEYCHAIN_PASSWORD" build.keychain
          security default-keychain -s build.keychain
          security unlock-keychain -p "$KEYCHAIN_PASSWORD" build.keychain

          # Import certificate
          echo "$CERTIFICATE_BASE64" | base64 --decode > certificate.p12
          security import certificate.p12 \
            -k build.keychain \
            -P "$CERTIFICATE_PASSWORD" \
            -T /usr/bin/codesign

          security set-key-partition-list -S apple-tool:,apple:,codesign: \
            -s -k "$KEYCHAIN_PASSWORD" build.keychain

          # Cleanup
          rm certificate.p12

      - name: Build Application
        run: |
          # Your build commands here
          pyinstaller grading-app.spec

      - name: Sign Application
        run: |
          ./desktop/installer/macos/sign.sh dist/GradingApp.app

      - name: Create DMG
        run: |
          hdiutil create -srcfolder dist/GradingApp.app -format UDZO \
            -volname "Grading App" dist/GradingApp.dmg

      - name: Notarize
        env:
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          APPLE_APP_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}
        run: |
          # Store credentials temporarily
          xcrun notarytool store-credentials "temp-profile" \
            --apple-id "$APPLE_ID" \
            --team-id "$APPLE_TEAM_ID" \
            --password "$APPLE_APP_PASSWORD"

          # Notarize
          ./desktop/installer/macos/notarize.sh \
            --keychain "temp-profile" \
            --staple \
            dist/GradingApp.dmg

      - name: Verify
        run: |
          codesign --verify --deep --strict dist/GradingApp.app
          xcrun stapler validate dist/GradingApp.dmg
          spctl --assess --verbose=4 dist/GradingApp.dmg

      - name: Cleanup Keychain
        if: always()
        run: |
          security delete-keychain build.keychain || true
```

**Security Notes**:
- Export Developer ID cert as .p12 with password
- Store as base64-encoded GitHub secret
- Temporary keychain created for each build
- Cleaned up after build

#### Option 2: Self-Hosted Runner (Simpler)

```yaml
name: Build and Sign macOS

on:
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: self-hosted  # macOS machine with certificate installed

    steps:
      - uses: actions/checkout@v3

      - name: Build Application
        run: pyinstaller grading-app.spec

      - name: Sign Application
        run: ./desktop/installer/macos/sign.sh dist/GradingApp.app

      - name: Create DMG
        run: |
          hdiutil create -srcfolder dist/GradingApp.app -format UDZO \
            -volname "Grading App" dist/GradingApp.dmg

      - name: Notarize
        run: |
          ./desktop/installer/macos/notarize.sh \
            --keychain "grading-app" \
            --staple \
            dist/GradingApp.dmg

      - name: Verify
        run: |
          codesign --verify --deep --strict dist/GradingApp.app
          xcrun stapler validate dist/GradingApp.dmg
```

**Security Notes**:
- Certificate and keychain profile pre-configured on runner
- No secrets needed in GitHub
- Simpler workflow

### GitLab CI, Jenkins, Other CI Systems

Similar approaches apply:

**Windows**:
- Cloud signing: SSL.com eSigner with API credentials
- Self-hosted runner: Hardware token on dedicated build machine
- Software cert: Import .pfx from CI secrets (less secure)

**macOS**:
- Self-hosted runner: Certificate pre-installed (recommended)
- Cloud runner: Import .p12 from secrets, create temp keychain

### Security Best Practices for CI/CD

1. **Never commit certificates** to source control
2. **Use encrypted secrets** for credentials
3. **Prefer hardware tokens** on self-hosted runners
4. **Clean up credentials** after build
5. **Limit CI access** to essential personnel
6. **Rotate secrets** periodically
7. **Audit signing operations** (log all signatures)
8. **Use temporary keychains** for macOS CI
9. **Verify signatures** in CI pipeline
10. **Test downloads** from distribution channel

## Cost Summary

### One-Time Setup Costs

| Platform | Item | Cost |
|----------|------|------|
| Windows | EV Code Signing Certificate (Year 1) | $300-500 |
| Windows | Hardware Token | Included |
| macOS | Apple Developer Program (Year 1) | $99 |
| **Total** | **First Year** | **~$400-600** |

### Annual Recurring Costs

| Platform | Item | Cost/Year |
|----------|------|-----------|
| Windows | EV Certificate Renewal | $300-500 |
| macOS | Apple Developer Program Renewal | $99 |
| **Total** | **Annual** | **~$400-600/year** |

### Multi-Year Projection

| Year | Windows | macOS | Total |
|------|---------|-------|-------|
| 1 | $300-500 | $99 | $400-600 |
| 2 | $300-500 | $99 | $400-600 |
| 3 | $300-500 | $99 | $400-600 |
| **3-Year Total** | **$900-1500** | **$297** | **$1200-1800** |

**Notes**:
- Some providers offer multi-year discounts (10-20% off)
- Apple Developer Program auto-renews annually
- No per-app or per-signature fees
- Linux requires no code signing costs

### Optional: Cloud Signing Services

If using cloud signing instead of hardware tokens:

- **SSL.com eSigner**: ~$20-50/month (~$240-600/year)
- Eliminates hardware token requirement
- Easier CI/CD integration
- More expensive long-term

## Troubleshooting

### Windows Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| "SignTool not found" | Install Windows SDK | [windows/SIGNING_SETUP.md](windows/SIGNING_SETUP.md#troubleshooting) |
| "Certificate not found" | Verify certificate installed in certmgr | [windows/VERIFICATION.md](windows/VERIFICATION.md#troubleshooting) |
| "No timestamp" | Re-sign with `-t` parameter | [windows/sign.ps1](windows/sign.ps1) |
| SmartScreen warnings | Expected for new apps; build reputation | [windows/VERIFICATION.md](windows/VERIFICATION.md#smartscreen-testing) |

### macOS Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| "No identity found" | Install Developer ID certificate | [macos/SIGNING_SETUP.md](macos/SIGNING_SETUP.md#certificate-creation) |
| "Hardened Runtime not enabled" | Re-sign with `--options runtime` | [macos/sign.sh](macos/sign.sh) |
| Notarization fails | Check notarization log for details | [macos/notarize.sh](macos/notarize.sh) |
| "Could not staple" | Ensure notarization completed successfully | [macos/VERIFICATION.md](macos/VERIFICATION.md#troubleshooting) |
| Gatekeeper blocks app | Verify notarization and stapling | [macos/VERIFICATION.md](macos/VERIFICATION.md#gatekeeper-testing) |

**See Platform-Specific Troubleshooting**:
- [windows/SIGNING_SETUP.md](windows/SIGNING_SETUP.md#troubleshooting)
- [windows/VERIFICATION.md](windows/VERIFICATION.md#troubleshooting-common-issues)
- [macos/SIGNING_SETUP.md](macos/SIGNING_SETUP.md#common-issues-and-troubleshooting)
- [macos/VERIFICATION.md](macos/VERIFICATION.md#troubleshooting-common-issues)

## Next Steps

### Immediate Actions

1. **Windows**:
   - [ ] Choose certificate provider (Sectigo, DigiCert, SSL.com)
   - [ ] Gather required documents for validation
   - [ ] Purchase EV Code Signing Certificate
   - [ ] Install certificate when received
   - [ ] Test signing script with test executable

2. **macOS**:
   - [ ] Enroll in Apple Developer Program
   - [ ] Wait for approval (24-48 hours)
   - [ ] Create Developer ID Application certificate
   - [ ] Create app-specific password for notarization
   - [ ] Store credentials in keychain profile
   - [ ] Test signing and notarization with test app

### Before First Release

1. **Sign all platform builds**:
   - Windows: `.\desktop\installer\windows\sign.ps1 -ExePath "dist\GradingApp.exe"`
   - macOS: `./desktop/installer/macos/sign.sh dist/GradingApp.app`

2. **Verify all signatures**:
   - Windows: `signtool verify /pa dist\GradingApp.exe`
   - macOS: `codesign --verify --deep --strict dist/GradingApp.app`

3. **Notarize macOS builds**:
   - `./desktop/installer/macos/notarize.sh --keychain "grading-app" --staple dist/GradingApp.dmg`

4. **Test on clean VMs**:
   - Windows 10/11: Test SmartScreen behavior
   - macOS 10.15+: Test Gatekeeper behavior

5. **Document expected behavior**:
   - Record SmartScreen warnings (if any)
   - Document user installation instructions
   - Create troubleshooting guide for users

### Certificate Renewal

Set calendar reminders:

**Windows**:
- 45 days before expiry: Order renewal
- 30 days before expiry: Follow up with CA
- 15 days before expiry: Install new certificate
- After renewal: Test signing with new certificate

**macOS**:
- 45 days before expiry: Renew Apple Developer Program
- Check certificate expiry: Usually 5 years, less urgent

## Support and Resources

### Official Documentation

- **Windows**: https://docs.microsoft.com/windows/win32/seccrypto/cryptography-tools
- **macOS**: https://developer.apple.com/support/code-signing/
- **Notarization**: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution

### Certificate Authorities

- **DigiCert**: https://www.digicert.com/support/
- **Sectigo**: https://support.sectigo.com/
- **GlobalSign**: https://support.globalsign.com/
- **SSL.com**: https://www.ssl.com/how-to/

### Community Support

- **Stack Overflow**: Tag with [code-signing], [windows], [macos]
- **Apple Developer Forums**: https://developer.apple.com/forums/
- **Microsoft Q&A**: https://docs.microsoft.com/answers/

### Professional Services

For complex setups or troubleshooting:
- Consider hiring consultant for initial setup
- Most CAs offer paid support incidents
- Apple Developer Technical Support (2 free incidents/year)

---

**Note**: Code signing requirements and processes may change over time. Always refer to official documentation from certificate authorities and platform vendors for the latest information.

**Last Updated**: 2025-01-16
