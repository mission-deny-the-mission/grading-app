# Desktop Application Contracts

**Feature**: 004-desktop-app
**Date**: 2025-11-16

## Overview

This directory contains contract specifications for the desktop application feature. Unlike traditional web API features, the desktop application primarily **wraps existing Flask routes** rather than introducing new HTTP endpoints.

The contracts defined here focus on:
1. **Python Module Interfaces**: Internal APIs between desktop components
2. **External Service Contracts**: OS credential managers, update servers
3. **File Format Contracts**: Settings files, backup bundles, update manifests

---

## Contract Categories

### 1. Python Module Interfaces

Desktop-specific Python modules with defined interfaces:
- `desktop/credentials.py` - Credential storage operations
- `desktop/task_queue.py` - Async task processing
- `desktop/updater.py` - Auto-update mechanism
- `desktop/app_wrapper.py` - Flask lifecycle management
- `desktop/window_manager.py` - UI and system tray

See: [`python-interfaces.md`](python-interfaces.md)

### 2. OS Service Contracts

Integration with operating system services:
- Windows Credential Manager API
- macOS Keychain Services
- Linux Secret Service (D-Bus)
- System tray notifications

See: [`os-services.md`](os-services.md)

### 3. File Format Contracts

Structured file formats for data exchange:
- `settings.json` - Application configuration
- `update_manifest.json` - Version metadata
- `backup_metadata.json` - Backup bundle format

See: [`file-formats.md`](file-formats.md)

### 4. Update Server Contract

HTTP API for checking and downloading updates:
- GitHub Releases API
- TUF metadata endpoints
- Update package hosting

See: [`update-server.md`](update-server.md)

---

## Reused Web App Contracts

The desktop application **reuses all existing Flask routes** from the web app without modification:

### Existing HTTP Endpoints (Unchanged)

From `routes/upload.py`:
- `POST /upload` - Upload submissions
- `POST /upload/batch` - Batch upload
- `GET /status/<job_id>` - Check job status

From `routes/api.py`:
- `GET /api/jobs` - List jobs
- `GET /api/schemes` - List grading schemes
- `POST /api/export` - Export results

From `routes/grading_schemes.py`:
- `GET /schemes` - View schemes
- `POST /schemes/create` - Create scheme
- `POST /schemes/<id>/edit` - Edit scheme

**No changes required** - Desktop app embeds Flask server and uses existing routes.

---

## Testing Approach

### Contract Testing Strategy

**Python Module Interfaces**:
- Unit tests verify function signatures match documentation
- Mock external dependencies (keyring, tufup, etc.)
- Test error handling for all failure modes

**OS Service Contracts**:
- Platform-specific integration tests (skip if platform unavailable)
- Test fallback behavior when OS services unavailable
- Verify encryption and access controls

**File Format Contracts**:
- JSON schema validation tests
- Roundtrip serialization tests (write → read → verify)
- Test backward compatibility with older format versions

**Update Server Contract**:
- Mock HTTP server for testing update workflows
- Test signature verification (valid/invalid signatures)
- Test network error handling (timeout, 404, 500, etc.)

---

## Versioning

### Contract Version Policy

**Python Interfaces**: Follow SemVer
- **Breaking change**: Function signature change, removed function
- **Minor change**: New optional parameter, new function
- **Patch**: Documentation clarification, no code change

**File Formats**: Explicit version field in JSON
- `settings.json` has `version: "1.0.0"`
- App must handle older versions gracefully (migration)
- App may reject future versions (forward compatibility not guaranteed)

**OS Services**: Determined by OS version
- Windows 10+ (Credential Manager API unchanged)
- macOS 11+ (Keychain Services API unchanged)
- Linux: D-Bus Secret Service spec v0.2 (stable since 2009)

**Update Server**: GitHub Releases API
- v3 REST API (stable, widely used)
- TUF spec version 1.0 (used by tufup library)

---

## Backward Compatibility

### Upgrade Paths

**Settings File**:
- v1.0 → v1.1: Add new fields with defaults
- v1.1 → v2.0: Migrate renamed fields
- Unknown version: Reject with error message

**Update Manifest**:
- Forward compatible (app ignores unknown fields)
- `minimum_version` field prevents too-old clients from attempting incompatible updates

**Backup Bundle**:
- Include `backup_version` in metadata
- Import validates schema version before proceeding
- Database migrations handle schema changes transparently

---

## Security Considerations

### Contract-Level Security

**Credential Storage Contract**:
- MUST use OS-native encryption
- MUST NOT log API key values
- MUST validate key format before storage

**Update Server Contract**:
- MUST verify TUF signatures
- MUST use HTTPS only (no HTTP fallback)
- MUST validate checksums before applying updates

**File Format Contract**:
- MUST exclude secrets from backup bundles
- MUST validate JSON against schema (prevent injection)
- MUST use atomic writes (prevent corruption on crash)

---

## Dependencies

### External Libraries Providing Contracts

| Library | Version | Contract | Purpose |
|---------|---------|----------|---------|
| `keyring` | ≥25.6.0 | Python API | OS credential storage |
| `keyrings.cryptfile` | ≥1.3.9 | Python API | Encrypted file fallback |
| `tufup` | ≥0.5.0 | Python API, TUF spec | Auto-update framework |
| `pywebview` | ≥4.0.0 | Python API | Webview window |
| `pystray` | ≥0.19.0 | Python API | System tray |
| `APScheduler` | ≥3.10.0 | Python API | Periodic tasks |

### OS-Level Dependencies

| Platform | Service | API Version | Required |
|----------|---------|-------------|----------|
| Windows | Credential Manager | Windows 10+ | Yes (native) |
| macOS | Keychain Services | macOS 11+ | Yes (native) |
| Linux | D-Bus Secret Service | v0.2+ | Yes (via gnome-keyring/kwalletd) |

---

## Change Log

### 2025-11-16 - Initial Contract Definitions

- Defined Python module interfaces for desktop components
- Documented OS service integration contracts
- Specified file format contracts for settings and backups
- Defined update server contract using GitHub Releases + TUF

---

**Document Status**: ✅ **Complete**
**Next Steps**: Review individual contract specifications in this directory
