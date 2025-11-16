# Windows Code Signing Verification Guide

## Overview

This guide covers how to verify code signatures on Windows executables and installers, ensuring they are properly signed before distribution and testing for SmartScreen warnings.

## Verification Steps

### 1. Verify Signature Locally

Before distributing your signed executable, verify the signature is valid and properly configured.

#### Using SignTool (Recommended)

```powershell
# Basic verification
signtool verify /pa GradingApp.exe

# Verbose verification with details
signtool verify /pa /v GradingApp.exe

# Expected output:
# Successfully verified: GradingApp.exe
# Number of files successfully Verified: 1
```

**What to check**:
- "Successfully verified" message appears
- No errors or warnings
- Certificate chain is valid
- Timestamp is present

#### Using PowerShell

```powershell
# Get signature information
Get-AuthenticodeSignature -FilePath "GradingApp.exe" | Format-List

# Check status
$sig = Get-AuthenticodeSignature -FilePath "GradingApp.exe"
if ($sig.Status -eq "Valid") {
    Write-Host "Signature is valid" -ForegroundColor Green
} else {
    Write-Host "Signature is NOT valid: $($sig.StatusMessage)" -ForegroundColor Red
}
```

**Expected output**:
```
SignerCertificate : [Subject]
                      CN=Your Name, O=Your Organization, ...
                    [Issuer]
                      CN=DigiCert SHA2 Assured ID Code Signing CA, ...
                    [Serial Number]
                      ABC123...
TimeStamperCertificate : [Subject]
                           CN=DigiCert Timestamp 2021, ...
Status                 : Valid
StatusMessage          : Signature verified.
```

#### Using Windows Explorer

1. **Right-click executable** → Properties
2. **Digital Signatures tab**: Should show your signature
3. **Select signature** → Details
4. **Verify**:
   - Signer: Your name/organization
   - Timestamp: Present and valid
   - Status: "This digital signature is OK"

### 2. Check Certificate Details

Verify the certificate used for signing is correct:

```powershell
# View certificate details
signtool verify /pa /v GradingApp.exe | Select-String "Issuing|Expires"

# Or using PowerShell
$sig = Get-AuthenticodeSignature -FilePath "GradingApp.exe"
$sig.SignerCertificate | Format-List Subject, Issuer, NotBefore, NotAfter, Thumbprint
```

**What to verify**:
- Subject: Your name/organization
- Issuer: Your Certificate Authority (DigiCert, Sectigo, etc.)
- NotBefore/NotAfter: Certificate is currently valid
- Thumbprint: Matches your certificate

### 3. Verify Timestamp

Critical: Timestamp allows signature to remain valid after certificate expires.

```powershell
# Check for timestamp
$sig = Get-AuthenticodeSignature -FilePath "GradingApp.exe"
if ($sig.TimeStamperCertificate) {
    Write-Host "Timestamp present: $($sig.TimeStamperCertificate.Subject)" -ForegroundColor Green
} else {
    Write-Host "WARNING: No timestamp found!" -ForegroundColor Red
}
```

**Expected**: Timestamp certificate should be present from a trusted timestamp authority (DigiCert, Sectigo, etc.)

**If missing**: Re-sign with `-t` or `-tr` parameter to add timestamp.

### 4. Verify Certificate Chain

Ensure the entire certificate chain is trusted:

```powershell
# Verify certificate chain
signtool verify /pa /all /v GradingApp.exe

# Check specific chain element
$sig = Get-AuthenticodeSignature -FilePath "GradingApp.exe"
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
$chain.Build($sig.SignerCertificate)

foreach ($element in $chain.ChainElements) {
    Write-Host "Chain: $($element.Certificate.Subject)"
}
```

**Expected chain** (example for DigiCert EV):
1. Your Certificate (CN=Your Name)
2. DigiCert SHA2 Assured ID Code Signing CA
3. DigiCert Assured ID Root CA

### 5. Check Signature Properties

Verify signature algorithm and hash:

```powershell
# View detailed signature info
certutil -verify GradingApp.exe

# Or using signtool
signtool verify /pa /v /debug GradingApp.exe 2>&1 | Select-String "Algorithm|Hash"
```

**Expected**:
- Signature algorithm: SHA256 or SHA384 (not SHA1)
- Hash algorithm: SHA256 or higher
- Digest algorithm: SHA256 or higher

**Note**: SHA1 is deprecated and should not be used.

## SmartScreen Testing

Windows SmartScreen is Microsoft's reputation-based security feature. Testing helps ensure users won't see warnings.

### Pre-Distribution SmartScreen Check

**Important**: SmartScreen warnings depend on:
1. Certificate type (EV vs. Standard)
2. Application reputation (download count)
3. Certificate reputation
4. Publisher reputation

#### Test 1: Local Machine Test

1. **Copy signed executable** to Downloads folder
2. **Run from Downloads**: Double-click to execute
3. **Observe behavior**:
   - No warning: Excellent (EV cert or established reputation)
   - Blue SmartScreen warning: Expected for new apps with standard cert
   - Red warning: Problem with signature or certificate

#### Test 2: Fresh Windows VM Test

Best way to simulate real user experience:

1. **Set up clean Windows VM**:
   - Windows 10 or 11 (latest version)
   - Fresh install, no updates disabled
   - SmartScreen enabled (default)

2. **Download executable**:
   - Upload to temporary web server
   - Download via web browser in VM
   - Or transfer via network share

3. **Run executable**:
   - Double-click to run
   - Note any warnings or messages

4. **Check expected behavior**:
   - **EV Certificate**: Should run without warnings (if cert is trusted)
   - **Standard Certificate**: May show SmartScreen warning initially
   - **No Certificate**: Will definitely show warnings

### SmartScreen Warning Types

#### No Warning (Ideal)

- Application runs immediately
- No SmartScreen popup
- Indicates: EV certificate or strong reputation

#### Blue SmartScreen Warning

```
Windows protected your PC
Windows Defender SmartScreen prevented an unrecognized app from starting.
Running this app might put your PC at risk.

App: GradingApp.exe
Publisher: Your Name (or "Unknown publisher" if cert issue)

[More info]
```

**If "More info" shows "Run anyway"**:
- Normal for new apps with standard certificates
- Reputation will build over time with downloads
- EV certificates skip this phase

**If no "Run anyway" option**:
- Serious issue with signature or certificate
- Check certificate is valid and trusted
- Verify certificate chain

#### Red Warning (Problem)

```
This app has been blocked for your protection
Contact your system administrator for more info.
```

**Causes**:
- Invalid or revoked certificate
- Known malware signature
- Corporate policy blocking
- Missing or corrupted signature

**Fix**:
- Verify signature is valid
- Check certificate hasn't been revoked
- Re-sign if necessary

### Understanding SmartScreen Reputation

**How reputation builds**:
1. User downloads: Each download counts toward reputation
2. Time: Older files have more reputation
3. Publisher: Reputation tied to certificate
4. No malware reports: Clean scanning history

**EV Certificate Advantage**:
- Immediate reputation from certificate
- No "unknown publisher" warnings
- Faster user adoption

**Standard Certificate**:
- Must build reputation over time
- Requires significant downloads (100s-1000s)
- May take weeks to months
- No way to "pay" for instant reputation

**Important**: You cannot pay Microsoft to bypass SmartScreen warnings (except via EV certificate). Reputation must be earned.

## Verification Checklist

Before distributing your signed executable, verify all of the following:

### Pre-Distribution Checklist

- [ ] Signature verified with `signtool verify /pa`
- [ ] Certificate details are correct (your name/organization)
- [ ] Certificate is currently valid (not expired)
- [ ] Certificate chain is complete and trusted
- [ ] Timestamp is present (check `TimeStamperCertificate`)
- [ ] Signature algorithm is SHA256 or higher (not SHA1)
- [ ] Properties → Digital Signatures tab shows valid signature
- [ ] Tested on clean Windows VM
- [ ] Documented expected SmartScreen behavior (EV vs. Standard)
- [ ] No red SmartScreen warnings on test machine
- [ ] Installer/executable runs successfully after signature verification

### Post-Distribution Monitoring

- [ ] Monitor user reports of SmartScreen warnings
- [ ] Track download count for reputation building
- [ ] Watch for certificate expiry (set reminders 45 days before)
- [ ] Verify signature periodically (monthly)
- [ ] Check for certificate revocation notices
- [ ] Update signature if certificate is renewed

## Troubleshooting Common Issues

### Issue: "SignTool Error: No signature found."

**Cause**: File is not signed or signature was removed.

**Solution**:
```powershell
# Re-sign the file
.\sign.ps1 -ExePath "GradingApp.exe"
```

### Issue: "SignTool Error: Trust verification failed"

**Cause**: Certificate is not trusted or chain is broken.

**Solution**:
1. Check certificate is installed: `certmgr.msc`
2. Verify certificate chain is complete
3. Ensure root CA is trusted
4. Re-sign with correct certificate

### Issue: "The digital signature is invalid"

**Cause**: File was modified after signing, or signature is corrupted.

**Solution**:
```powershell
# Verify file integrity
Get-FileHash "GradingApp.exe" -Algorithm SHA256

# Re-sign if file is correct
.\sign.ps1 -ExePath "GradingApp.exe"
```

### Issue: No timestamp certificate

**Cause**: Timestamp server was unavailable during signing, or `-t` parameter was omitted.

**Solution**:
```powershell
# Re-sign with timestamp
.\sign.ps1 -ExePath "GradingApp.exe" -TimestampUrl "http://timestamp.digicert.com"
```

### Issue: SmartScreen always blocks (red warning)

**Cause**: Certificate is revoked, invalid, or application is flagged.

**Solution**:
1. Check certificate status: `certutil -verify GradingApp.exe`
2. Verify certificate not revoked: Contact CA
3. Scan for malware: `Windows Defender scan`
4. Re-sign with valid certificate
5. Contact Microsoft if issue persists

### Issue: "Windows cannot verify the digital signature"

**Cause**: Timestamp server certificate expired or was revoked.

**Solution**:
- If timestamp is old and server cert expired, this is expected
- Re-sign with current timestamp server
- Ensure timestamp server is from trusted CA

### Issue: Signature shows "Unknown publisher"

**Cause**: Certificate subject name doesn't match expected publisher.

**Solution**:
1. Verify certificate details: `Get-AuthenticodeSignature`
2. Check certificate subject matches your organization
3. Ensure correct certificate was used for signing
4. Re-sign with correct certificate if needed

## Testing Tools

### Recommended Testing Tools

1. **SignTool.exe** (included with Windows SDK)
   - Official Microsoft tool
   - Most reliable for verification
   - Use for all pre-distribution checks

2. **PowerShell Get-AuthenticodeSignature**
   - Built into Windows
   - Good for scripting and automation
   - Detailed signature information

3. **CertUtil**
   - Certificate verification
   - Chain validation
   - Built into Windows

4. **Windows Defender**
   - Scan signed executable for malware
   - Ensure clean before distribution

5. **VirusTotal**
   - Upload to https://www.virustotal.com
   - Check against 70+ antivirus engines
   - Verify no false positives

### Automated Verification Script

Create a PowerShell script for consistent verification:

```powershell
# verify-signature.ps1
param([string]$FilePath)

Write-Host "Verifying signature for: $FilePath" -ForegroundColor Cyan

# 1. Basic verification
$result = signtool verify /pa $FilePath 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[PASS] Signature is valid" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Signature verification failed" -ForegroundColor Red
    exit 1
}

# 2. Check timestamp
$sig = Get-AuthenticodeSignature -FilePath $FilePath
if ($sig.TimeStamperCertificate) {
    Write-Host "[PASS] Timestamp present" -ForegroundColor Green
} else {
    Write-Host "[FAIL] No timestamp found" -ForegroundColor Red
    exit 1
}

# 3. Check certificate validity
$cert = $sig.SignerCertificate
$now = Get-Date
if ($now -ge $cert.NotBefore -and $now -le $cert.NotAfter) {
    Write-Host "[PASS] Certificate is valid" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Certificate is expired or not yet valid" -ForegroundColor Red
    exit 1
}

# 4. Check signature algorithm
if ($sig.SignatureAlgorithm -match "sha256|sha384|sha512") {
    Write-Host "[PASS] Strong signature algorithm: $($sig.SignatureAlgorithm)" -ForegroundColor Green
} else {
    Write-Host "[WARN] Weak signature algorithm: $($sig.SignatureAlgorithm)" -ForegroundColor Yellow
}

Write-Host "`nAll checks passed!" -ForegroundColor Green
```

## Best Practices

1. **Always verify signatures** before distributing
2. **Test on clean Windows VM** to simulate user experience
3. **Monitor SmartScreen reputation** after release
4. **Keep certificates backed up** and secure
5. **Set expiry reminders** for certificate renewal
6. **Document verification process** in release checklist
7. **Automate verification** in build pipeline
8. **Test downloads** from actual distribution channel
9. **Collect user feedback** on installation experience
10. **Re-verify after updates** or patches

## Support and Resources

- **SignTool Documentation**: https://docs.microsoft.com/windows/win32/seccrypto/signtool
- **Authenticode**: https://docs.microsoft.com/windows-hardware/drivers/install/authenticode
- **SmartScreen**: https://docs.microsoft.com/windows/security/threat-protection/windows-defender-smartscreen/
- **Certificate Troubleshooting**: Contact your Certificate Authority (DigiCert, Sectigo, etc.)

---

**Note**: SmartScreen behavior may change with Windows updates. Always test on the latest Windows version before major releases.
