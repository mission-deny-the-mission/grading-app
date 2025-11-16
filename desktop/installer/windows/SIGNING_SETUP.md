# Windows Code Signing Setup Guide

## Overview

Code signing for Windows executables prevents security warnings (SmartScreen) when users download and run your application. Windows requires an **EV (Extended Validation) Code Signing Certificate** for optimal security and to build reputation with Microsoft SmartScreen.

## Why Code Signing is Important

Without code signing:
- Windows Defender SmartScreen shows "Windows protected your PC" warnings
- Users must click "More info" → "Run anyway" to install
- Severely impacts user trust and adoption
- Some antivirus software may flag unsigned executables

With code signing:
- Professional appearance and increased trust
- Builds SmartScreen reputation over time
- Required for Windows Store distribution
- Prevents tampering detection

## Certificate Requirements

### EV Code Signing Certificate

**Recommended Option**: EV (Extended Validation) Certificate
- **Cost**: $300-500 per year (varies by provider)
- **Validation**: Extensive company verification (2-7 days)
- **Storage**: Hardware token (USB) required by most CAs
- **Benefits**:
  - Immediate SmartScreen reputation
  - Higher trust level
  - Required for kernel-mode drivers
  - No SmartScreen warnings even for new applications

**Standard Code Signing** (Not Recommended):
- **Cost**: $75-200 per year
- **Validation**: Basic company/individual verification
- **Storage**: Software (.pfx file)
- **Limitations**:
  - Must build SmartScreen reputation over time
  - May show warnings for new applications
  - Requires many downloads before reputation is established

### Why EV is Preferred

Microsoft SmartScreen treats EV certificates differently:
- Immediate reputation inheritance from the certificate
- No warnings for users (assuming cert is trusted)
- Better for new applications without download history
- More professional and trustworthy

## Certificate Providers

### Recommended Providers

1. **DigiCert** (Most Popular)
   - **URL**: https://www.digicert.com/signing/code-signing-certificates
   - **EV Cost**: ~$474/year
   - **Pros**: Excellent reputation, good support, fast validation
   - **Cons**: More expensive
   - **Token**: Included with EV cert

2. **Sectigo (formerly Comodo)**
   - **URL**: https://www.sectigo.com/ssl-certificates-tls/code-signing
   - **EV Cost**: ~$315/year
   - **Pros**: Lower cost, good reputation
   - **Cons**: Validation can be slower
   - **Token**: Included with EV cert

3. **GlobalSign**
   - **URL**: https://www.globalsign.com/en/code-signing-certificate
   - **EV Cost**: ~$399/year
   - **Pros**: Global presence, good support
   - **Cons**: Mid-range pricing
   - **Token**: Included with EV cert

4. **SSL.com**
   - **URL**: https://www.ssl.com/code-signing/
   - **EV Cost**: ~$299/year
   - **Pros**: Most affordable EV option
   - **Cons**: Less well-known, newer to market
   - **Token**: eSigner cloud signing available (no hardware token)

### Comparison Matrix

| Provider    | EV Price/Year | Validation Time | Token Type        | Support Quality |
|-------------|---------------|-----------------|-------------------|-----------------|
| DigiCert    | $474          | 2-5 days        | USB SafeNet       | Excellent       |
| Sectigo     | $315          | 3-7 days        | USB YubiKey       | Good            |
| GlobalSign  | $399          | 2-5 days        | USB SafeNet       | Excellent       |
| SSL.com     | $299          | 3-7 days        | Cloud/USB Option  | Good            |

## Acquisition Process

### Step 1: Choose a Provider

Select a provider based on budget and requirements. For most users, **Sectigo** or **SSL.com** offer the best value.

### Step 2: Prepare Required Documents

You'll need to provide:

**For Companies**:
- Legal business name (must match registration)
- Physical address (PO Box not allowed)
- Phone number (must be published/verifiable)
- Business registration documents (Articles of Incorporation, etc.)
- Tax ID or DUNS number
- Authorized signer information

**For Individuals**:
- Government-issued photo ID (passport, driver's license)
- Proof of address (utility bill, bank statement)
- Phone number verification

**Important**: The name on the certificate MUST match your legal business/individual name exactly.

### Step 3: Purchase Certificate

1. Go to provider's website
2. Select "EV Code Signing Certificate"
3. Choose validity period (1-3 years typically)
4. Complete purchase (credit card, wire transfer, etc.)

### Step 4: Complete Validation

The Certificate Authority (CA) will:
1. Verify your business/identity (phone call, document review)
2. Check business registration with government databases
3. Verify phone number and address
4. Conduct additional checks for EV validation

**Timeline**: 2-7 business days typically

### Step 5: Receive Hardware Token

For EV certificates:
1. CA ships USB hardware token (SafeNet, YubiKey, etc.)
2. Receive certificate installation instructions
3. Install certificate onto token (usually pre-installed)

**Important**: Keep the token secure! It's required for all signing operations.

## Certificate Installation

### Hardware Token Installation (EV)

1. **Insert USB Token**: Plug in the hardware token
2. **Install Driver**: Download and install the token driver from CA
   - SafeNet: https://support.sectigo.com/Com_KnowledgeDetailPage?Id=kA01N000000bvCJ
   - YubiKey: https://www.yubico.com/products/services-software/download/smart-card-drivers-tools/
3. **Verify Installation**: Open Windows Certificate Manager
   ```powershell
   certmgr.msc
   ```
4. **Check Token**: Look under Personal → Certificates
   - Should see certificate with your name
   - Should show "YubiKey" or "SafeNet" as provider

### Software Certificate Installation (Standard)

If using a .pfx file (standard cert):
1. **Download .pfx**: From CA's website
2. **Import Certificate**:
   ```powershell
   # Double-click .pfx file, or use:
   certutil -importpfx "path\to\certificate.pfx"
   ```
3. **Enter Password**: Provided by CA
4. **Choose Store**: "Personal" store
5. **Mark as Exportable**: Only if you need to transfer

**Security Note**: Store .pfx files securely. Anyone with the file and password can sign as you.

## Key Storage Recommendations

### Hardware Token (EV) - Recommended

**Pros**:
- Private key never leaves the token
- Tamper-resistant
- Required for EV certificates
- Meets highest security standards

**Cons**:
- Physical device can be lost/damaged
- Requires USB port
- May need driver installation

**Best Practices**:
- Keep token in secure location when not in use
- Have backup token (some CAs offer this)
- Document token PIN/password securely
- Consider safe deposit box for backup

### Software Storage (.pfx)

**Pros**:
- Easy to backup
- Can be used on multiple machines
- No special hardware required

**Cons**:
- Less secure than hardware
- Can be stolen if system is compromised
- Not allowed for EV certificates
- Must be password-protected

**Best Practices**:
- Use strong password (20+ characters)
- Store in encrypted volume
- Limit access permissions
- Never commit to source control
- Use environment variables for automation

### Cloud Signing Services

Some providers (SSL.com) offer cloud-based signing:

**Pros**:
- No hardware token needed
- Can sign from CI/CD
- Automatic backups
- Multi-user access control

**Cons**:
- Monthly/usage fees
- Requires internet connection
- Less control over private key
- May have latency issues

## Cost Summary

### One-Time Costs
- EV Certificate (1 year): $300-500
- Hardware Token: Included with EV
- Token Driver: Free
- Total: $300-500

### Annual Renewal Costs
- Certificate Renewal: $300-500/year
- New Token (if lost): $50-100
- Total: ~$300-500/year

### Multi-Year Options
Many providers offer discounts for multi-year purchases:
- 1 year: $475 (example)
- 2 years: $850 ($425/year, 10% savings)
- 3 years: $1,140 ($380/year, 20% savings)

## Signing Process Overview

Once you have the certificate installed:

1. **Locate Certificate**: Find certificate thumbprint or subject name
2. **Run Signing Script**: Use `sign.ps1` (see script documentation)
3. **Add Timestamp**: Critical for validity beyond cert expiration
4. **Verify Signature**: Confirm signature is valid
5. **Test SmartScreen**: Download and run to verify no warnings

See `sign.ps1` for detailed signing implementation.

## Timestamp Servers

Always use a timestamp server when signing. This allows signed binaries to remain valid even after the certificate expires.

**Recommended Timestamp Servers**:
- DigiCert: http://timestamp.digicert.com
- Sectigo: http://timestamp.sectigo.com
- GlobalSign: http://timestamp.globalsign.com

**Why Timestamp Matters**:
- Without timestamp: Signature invalid after cert expires
- With timestamp: Signature valid indefinitely (if timestamped before expiry)
- Proves "this was signed when the cert was valid"

## Certificate Management

### Renewal Process

Certificates must be renewed before expiration:
1. **45 days before expiry**: CA sends renewal notice
2. **Order Renewal**: Same provider, simplified validation
3. **Re-validation**: May require updated documents
4. **Install New Cert**: Replace old certificate
5. **Update Scripts**: Use new certificate thumbprint

### Multiple Certificates

If you have multiple products or organizations:
- One EV cert per legal entity
- Can sign multiple applications with same cert
- Certificate shows on application properties
- Consider separate certs for different products (branding)

### Revocation

If certificate is compromised:
1. **Contact CA Immediately**: Request revocation
2. **Stop Using Certificate**: Remove from all systems
3. **Issue New Certificate**: CA will issue replacement
4. **Re-sign Applications**: Sign all releases with new cert

**Important**: Revoked certificates will cause installation failures. Re-sign all distributed software ASAP.

## Troubleshooting

### "SignTool not found"

**Solution**: Install Windows SDK
```powershell
# Download from:
# https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

# Or install via Visual Studio Installer:
# Individual Components → Windows SDK
```

### "Certificate not found"

**Solution**: Verify certificate installation
```powershell
# List all certificates
certmgr.msc

# Or via PowerShell:
Get-ChildItem -Path Cert:\CurrentUser\My
Get-ChildItem -Path Cert:\LocalMachine\My
```

### "Private key not found"

**Solution**: Ensure hardware token is connected, or .pfx imported correctly
```powershell
# For hardware token:
# 1. Insert token
# 2. Install driver
# 3. Verify in Device Manager

# For .pfx:
certutil -importpfx "certificate.pfx"
```

### "Timestamp server unavailable"

**Solution**: Use alternative timestamp server
```powershell
# Try different servers in order:
# 1. http://timestamp.digicert.com
# 2. http://timestamp.sectigo.com
# 3. http://timestamp.globalsign.com
```

### SmartScreen Still Showing Warnings

**Solution**: Build reputation over time
- EV certificates have faster reputation building
- Requires many users downloading the application
- Can take weeks to months for new applications
- No way to "pay" for instant reputation

## Security Best Practices

1. **Protect Private Key**: Never share certificate or token
2. **Use Strong Passwords**: For .pfx files and token PINs
3. **Limit Access**: Only authorized personnel should sign
4. **Audit Signing**: Log all signing operations
5. **Secure Storage**: Lock up hardware tokens when not in use
6. **Monitor Usage**: Watch for unauthorized signing
7. **Rotate Certificates**: Renew before expiration
8. **Test Signatures**: Verify every signed build
9. **Backup Everything**: Especially hardware tokens
10. **Document Process**: Maintain signing procedures

## CI/CD Integration

For automated signing in GitHub Actions or other CI/CD:

### Option 1: Cloud Signing (Recommended for CI/CD)
- Use SSL.com eSigner or similar cloud signing service
- Store credentials in CI/CD secrets
- No hardware token needed in CI environment

### Option 2: Software Certificate
- Store .pfx in CI/CD secrets (encrypted)
- Use password from environment variable
- More risk than hardware token

### Option 3: Self-Hosted Runner
- Use hardware token on self-hosted runner
- Most secure for EV certificates
- Requires dedicated build machine

See `CI_CD_INTEGRATION.md` for detailed workflow examples.

## Next Steps

1. **Choose Provider**: Select based on budget and needs
2. **Gather Documents**: Prepare business/identity verification
3. **Purchase Certificate**: Complete order with CA
4. **Complete Validation**: Respond to CA verification requests
5. **Receive Token**: Wait for hardware token delivery
6. **Install Certificate**: Set up token and drivers
7. **Test Signing**: Use `sign.ps1` to sign test executable
8. **Verify**: Check signature with `signtool verify`
9. **Document**: Record certificate details and thumbprint
10. **Set Reminders**: Calendar renewal 45 days before expiry

## Resources

- **Microsoft Code Signing**: https://docs.microsoft.com/windows/win32/seccrypto/cryptography-tools
- **SignTool Documentation**: https://docs.microsoft.com/windows/win32/seccrypto/signtool
- **SmartScreen Info**: https://docs.microsoft.com/windows/security/threat-protection/windows-defender-smartscreen/
- **Certificate Comparison**: https://codesigningstore.com/code-signing-comparison

## Support

If you encounter issues:
1. **CA Support**: Contact your certificate provider
2. **Microsoft Docs**: Review SignTool documentation
3. **Community Forums**: StackOverflow, Windows Dev Center
4. **Professional Help**: Consider hiring a consultant for initial setup

---

**Note**: This guide is informational only. Actual certificate acquisition and costs may vary by provider and region. Always verify current pricing and requirements with the Certificate Authority directly.
