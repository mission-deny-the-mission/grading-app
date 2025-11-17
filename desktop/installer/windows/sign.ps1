# Windows Code Signing Script
# Signs executables and installers with code signing certificate
# Usage: .\sign.ps1 -ExePath "path\to\executable.exe" [-CertPath "cert.pfx"] [-Password "pass"]

param(
    [Parameter(Mandatory=$true, HelpMessage="Path to the executable or installer to sign")]
    [ValidateNotNullOrEmpty()]
    [string]$ExePath,

    [Parameter(Mandatory=$false, HelpMessage="Path to .pfx certificate file (not needed for hardware token)")]
    [string]$CertPath = "",

    [Parameter(Mandatory=$false, HelpMessage="Password for .pfx certificate")]
    [string]$Password = "",

    [Parameter(Mandatory=$false, HelpMessage="Certificate thumbprint (alternative to .pfx)")]
    [string]$Thumbprint = "",

    [Parameter(Mandatory=$false, HelpMessage="Timestamp server URL")]
    [string]$TimestampUrl = "http://timestamp.digicert.com",

    [Parameter(Mandatory=$false, HelpMessage="Description to embed in signature")]
    [string]$Description = "Grading App",

    [Parameter(Mandatory=$false, HelpMessage="URL to embed in signature")]
    [string]$DescriptionUrl = "https://github.com/yourusername/grading-app",

    [Parameter(Mandatory=$false, HelpMessage="Path to signtool.exe (auto-detected if not provided)")]
    [string]$SignToolPath = ""
)

# Color output functions
function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Find signtool.exe
function Find-SignTool {
    Write-Info "Searching for signtool.exe..."

    # Common installation paths
    $searchPaths = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x86\signtool.exe",
        "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\8.1\bin\x64\signtool.exe",
        "${env:ProgramFiles(x86)}\Windows Kits\8.1\bin\x86\signtool.exe",
        "${env:ProgramFiles(x86)}\Microsoft SDKs\Windows\*\bin\signtool.exe"
    )

    foreach ($pattern in $searchPaths) {
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            Write-Success "Found signtool.exe at: $($found.FullName)"
            return $found.FullName
        }
    }

    Write-Error-Custom "signtool.exe not found!"
    Write-Error-Custom "Please install Windows SDK: https://developer.microsoft.com/windows/downloads/windows-sdk/"
    return $null
}

# Validate executable exists
function Test-ExecutablePath {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Error-Custom "Executable not found: $Path"
        return $false
    }

    Write-Success "Executable found: $Path"
    return $true
}

# Find certificate by thumbprint
function Get-CertificateByThumbprint {
    param([string]$Thumbprint)

    Write-Info "Searching for certificate with thumbprint: $Thumbprint"

    # Search in CurrentUser store
    $cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $Thumbprint }
    if ($cert) {
        Write-Success "Certificate found in CurrentUser\My store"
        return $cert
    }

    # Search in LocalMachine store
    $cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object { $_.Thumbprint -eq $Thumbprint }
    if ($cert) {
        Write-Success "Certificate found in LocalMachine\My store"
        return $cert
    }

    Write-Error-Custom "Certificate not found with thumbprint: $Thumbprint"
    return $null
}

# List available code signing certificates
function Show-AvailableCertificates {
    Write-Info "Available code signing certificates:"

    $certs = @()
    $certs += Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue
    $certs += Get-ChildItem -Path Cert:\LocalMachine\My -CodeSigningCert -ErrorAction SilentlyContinue

    if ($certs.Count -eq 0) {
        Write-Warning-Custom "No code signing certificates found in certificate stores"
        return
    }

    foreach ($cert in $certs) {
        Write-Host "  Subject: $($cert.Subject)" -ForegroundColor White
        Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
        Write-Host "  Valid: $($cert.NotBefore) to $($cert.NotAfter)" -ForegroundColor Gray
        Write-Host ""
    }
}

# Sign using .pfx file
function Sign-WithPfx {
    param(
        [string]$SignTool,
        [string]$ExePath,
        [string]$PfxPath,
        [string]$PfxPassword,
        [string]$Timestamp,
        [string]$Desc,
        [string]$Url
    )

    Write-Info "Signing with .pfx certificate: $PfxPath"

    # Build signtool arguments
    $args = @(
        "sign",
        "/f", $PfxPath,
        "/p", $PfxPassword,
        "/t", $Timestamp,
        "/d", $Desc,
        "/du", $Url,
        "/v",
        $ExePath
    )

    # Execute signtool
    $process = Start-Process -FilePath $SignTool -ArgumentList $args -NoNewWindow -Wait -PassThru
    return $process.ExitCode
}

# Sign using certificate from store (thumbprint)
function Sign-WithThumbprint {
    param(
        [string]$SignTool,
        [string]$ExePath,
        [string]$Thumbprint,
        [string]$Timestamp,
        [string]$Desc,
        [string]$Url
    )

    Write-Info "Signing with certificate thumbprint: $Thumbprint"

    # Build signtool arguments
    $args = @(
        "sign",
        "/sha1", $Thumbprint,
        "/t", $Timestamp,
        "/d", $Desc,
        "/du", $Url,
        "/v",
        $ExePath
    )

    # Execute signtool
    $process = Start-Process -FilePath $SignTool -ArgumentList $args -NoNewWindow -Wait -PassThru
    return $process.ExitCode
}

# Sign using best available certificate (auto-detect)
function Sign-Auto {
    param(
        [string]$SignTool,
        [string]$ExePath,
        [string]$Timestamp,
        [string]$Desc,
        [string]$Url
    )

    Write-Info "Auto-detecting code signing certificate..."

    # Try to find a code signing certificate
    $cert = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $cert) {
        $cert = Get-ChildItem -Path Cert:\LocalMachine\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object -First 1
    }

    if (-not $cert) {
        Write-Error-Custom "No code signing certificate found in certificate stores"
        Show-AvailableCertificates
        return 1
    }

    Write-Success "Found certificate: $($cert.Subject)"
    Write-Info "Thumbprint: $($cert.Thumbprint)"

    # Sign using thumbprint
    return Sign-WithThumbprint -SignTool $SignTool -ExePath $ExePath -Thumbprint $cert.Thumbprint -Timestamp $Timestamp -Desc $Desc -Url $Url
}

# Verify signature
function Verify-Signature {
    param(
        [string]$SignTool,
        [string]$ExePath
    )

    Write-Info "Verifying signature..."

    $args = @(
        "verify",
        "/pa",
        "/v",
        $ExePath
    )

    $process = Start-Process -FilePath $SignTool -ArgumentList $args -NoNewWindow -Wait -PassThru
    return $process.ExitCode
}

# Main execution
function Main {
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host "   Windows Code Signing Script" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""

    # Find signtool.exe
    if ($SignToolPath -eq "") {
        $SignToolPath = Find-SignTool
        if (-not $SignToolPath) {
            exit 1
        }
    } else {
        if (-not (Test-Path $SignToolPath)) {
            Write-Error-Custom "SignTool not found at: $SignToolPath"
            exit 1
        }
        Write-Success "Using signtool.exe at: $SignToolPath"
    }

    # Validate executable path
    if (-not (Test-ExecutablePath -Path $ExePath)) {
        exit 1
    }

    # Determine signing method
    $exitCode = 0

    if ($CertPath -ne "") {
        # Sign with .pfx file
        if (-not (Test-Path $CertPath)) {
            Write-Error-Custom "Certificate file not found: $CertPath"
            exit 1
        }

        if ($Password -eq "") {
            Write-Warning-Custom "No password provided for .pfx file"
            $securePassword = Read-Host "Enter certificate password" -AsSecureString
            $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
        }

        $exitCode = Sign-WithPfx -SignTool $SignToolPath -ExePath $ExePath -PfxPath $CertPath -PfxPassword $Password -Timestamp $TimestampUrl -Desc $Description -Url $DescriptionUrl

    } elseif ($Thumbprint -ne "") {
        # Sign with thumbprint
        $cert = Get-CertificateByThumbprint -Thumbprint $Thumbprint
        if (-not $cert) {
            Show-AvailableCertificates
            exit 1
        }

        $exitCode = Sign-WithThumbprint -SignTool $SignToolPath -ExePath $ExePath -Thumbprint $Thumbprint -Timestamp $TimestampUrl -Desc $Description -Url $DescriptionUrl

    } else {
        # Auto-detect certificate
        $exitCode = Sign-Auto -SignTool $SignToolPath -ExePath $ExePath -Timestamp $TimestampUrl -Desc $Description -Url $DescriptionUrl
    }

    Write-Host ""

    if ($exitCode -eq 0) {
        Write-Success "Signing completed successfully!"
    } else {
        Write-Error-Custom "Signing failed with exit code: $exitCode"
        exit $exitCode
    }

    # Verify signature
    Write-Host ""
    $verifyCode = Verify-Signature -SignTool $SignToolPath -ExePath $ExePath

    Write-Host ""

    if ($verifyCode -eq 0) {
        Write-Success "Signature verification successful!"
        Write-Host ""
        Write-Host "=====================================" -ForegroundColor Green
        Write-Host "   Code Signing Complete!" -ForegroundColor Green
        Write-Host "=====================================" -ForegroundColor Green
        exit 0
    } else {
        Write-Error-Custom "Signature verification failed with exit code: $verifyCode"
        exit $verifyCode
    }
}

# Run main function
Main
