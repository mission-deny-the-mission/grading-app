# Data Model: Desktop Application

**Feature**: 004-desktop-app
**Date**: 2025-11-16
**Source**: Derived from spec.md Key Entities section

## Overview

The desktop application feature primarily **wraps and packages** the existing web application rather than introducing new domain entities for grading. However, it does introduce desktop-specific configuration and metadata entities that are stored locally on the user's machine.

**Key Architectural Decision**: This feature reuses **all existing data models** from the web application (GradingScheme, Submission, Job, etc.) without modification. The new entities below are **desktop-specific** and stored separately from the main application database.

---

## Desktop-Specific Entities

### 1. Application Settings

**Purpose**: User-configurable preferences for the desktop application.

**Storage**: JSON file in user data directory (`~/.local/share/GradingApp/settings.json` on Linux, `%APPDATA%\GradingApp\settings.json` on Windows, `~/Library/Application Support/GradingApp/settings.json` on macOS)

**Schema**:
```json
{
  "version": "1.0.0",
  "app_version": "0.1.0",
  "last_updated": "2025-11-16T10:30:00Z",
  "ui": {
    "theme": "system",  // "light", "dark", "system"
    "start_minimized": false,
    "show_in_system_tray": true,
    "window_geometry": {
      "width": 1280,
      "height": 800,
      "x": 100,
      "y": 100,
      "maximized": false
    }
  },
  "updates": {
    "auto_check": true,
    "check_frequency": "startup",  // "startup", "daily", "weekly", "never"
    "auto_download": false,
    "last_check": "2025-11-16T08:00:00Z",
    "deferred_version": null  // Version user chose to skip
  },
  "data": {
    "database_path": "/home/user/.local/share/GradingApp/grading.db",
    "uploads_path": "/home/user/.local/share/GradingApp/uploads",
    "backups_enabled": true,
    "backup_frequency": "daily",  // "never", "daily", "weekly"
    "backup_retention_days": 30
  },
  "advanced": {
    "flask_port": null,  // null = auto-select, or specific port number
    "log_level": "INFO",  // "DEBUG", "INFO", "WARNING", "ERROR"
    "enable_telemetry": false  // Opt-in crash reporting (future)
  }
}
```

**Validation Rules**:
- `version` must be valid semver
- `app_version` must match current application version
- `theme` must be one of: `["light", "dark", "system"]`
- `check_frequency` must be one of: `["startup", "daily", "weekly", "never"]`
- `window_geometry` values must be positive integers
- `backup_retention_days` must be > 0
- `flask_port` if not null, must be 1024-65535

**Relationships**: None (standalone configuration)

**State Transitions**: Settings are read on startup, written on change or graceful shutdown

---

### 2. Update Manifest

**Purpose**: Metadata about available application versions retrieved from update server.

**Storage**: In-memory during update check, cached temporarily in `~/.local/share/GradingApp/update_cache.json`

**Schema**:
```json
{
  "version": "1.1.0",
  "release_date": "2025-11-20T00:00:00Z",
  "release_notes_url": "https://github.com/USER/REPO/releases/tag/v1.1.0",
  "release_notes_summary": "Bug fixes and performance improvements",
  "critical": false,  // If true, strongly encourage immediate update
  "downloads": {
    "windows": {
      "url": "https://github.com/USER/REPO/releases/download/v1.1.0/grading-app-windows.exe",
      "size_bytes": 125829120,
      "sha256": "abc123...",
      "signature": "tuf_signature_data"
    },
    "macos": {
      "url": "https://github.com/USER/REPO/releases/download/v1.1.0/grading-app-macos.dmg",
      "size_bytes": 130023424,
      "sha256": "def456...",
      "signature": "tuf_signature_data"
    },
    "linux": {
      "url": "https://github.com/USER/REPO/releases/download/v1.1.0/grading-app-linux.AppImage",
      "size_bytes": 127926272,
      "sha256": "ghi789...",
      "signature": "tuf_signature_data"
    }
  },
  "patches": {
    "1.0.0": {
      "windows": {
        "url": "https://github.com/USER/REPO/releases/download/v1.1.0/patch-1.0.0-to-1.1.0-windows.patch",
        "size_bytes": 15728640,
        "sha256": "patch_hash..."
      },
      "macos": { /* ... */ },
      "linux": { /* ... */ }
    }
  },
  "minimum_version": "1.0.0"  // Versions below this cannot use patch updates
}
```

**Validation Rules**:
- `version` must be valid semver and greater than current version
- `release_date` must be valid ISO 8601 timestamp
- `size_bytes` must be positive integer
- `sha256` must be 64 hex characters
- `signature` must be valid TUF signature (verified by tufup library)
- Platform-specific downloads required for at least one platform

**Relationships**:
- References `Application Settings.deferred_version` (user can defer specific version)

**State Transitions**:
1. **Fetched**: Retrieved from update server
2. **Cached**: Saved to local cache (valid for 24 hours)
3. **Downloading**: User approved, download in progress
4. **Downloaded**: Package on disk, awaiting application
5. **Applied**: Update installed, app restarted

---

### 3. Credential Storage Entries

**Purpose**: Securely store AI provider API keys using OS-native credential managers.

**Storage**:
- **Windows**: Windows Credential Locker (encrypted with DPAPI)
- **macOS**: macOS Keychain (encrypted with Keychain encryption)
- **Linux**: Secret Service API / GNOME Keyring / KWallet (encrypted)
- **Fallback**: `keyrings.cryptfile` (Argon2id + AES-GCM encrypted file)

**Schema** (Logical representation, actual storage handled by `keyring` library):
```python
{
  "service": "grading-app",
  "username": "openrouter_api_key",  # One entry per provider
  "password": "sk-or-v1-..."  # The actual API key (encrypted at rest)
}
```

**Supported Credential Keys**:
- `openrouter_api_key`
- `claude_api_key`
- `openai_api_key`
- `gemini_api_key`
- `nanogpt_api_key`
- `chutes_api_key`
- `zai_api_key`

**Validation Rules**:
- API keys must match provider-specific format (reuses existing validation from 002-api-provider-security)
- Empty string is valid (represents "not configured")

**Relationships**: None (accessed via `keyring` library API)

**State Transitions**:
1. **Not Set**: No credential stored
2. **Set**: Credential stored in OS credential manager
3. **Deleted**: Credential removed from OS credential manager

---

### 4. Data Backup Bundle

**Purpose**: Portable file format for exporting/importing user data between installations.

**Storage**: User-chosen location (e.g., Downloads folder, external drive)

**Format**: ZIP archive containing SQLite database + uploads directory

**Structure**:
```
grading-app-backup-20251116-103000.zip
├── metadata.json
├── grading.db (SQLite database file)
└── uploads/ (directory containing all uploaded submission files)
    ├── <submission_id_1>/
    │   └── document.pdf
    ├── <submission_id_2>/
    │   └── essay.docx
    └── ...
```

**metadata.json Schema**:
```json
{
  "backup_version": "1.0",
  "created_at": "2025-11-16T10:30:00Z",
  "app_version": "0.1.0",
  "platform": "linux",
  "hostname": "user-laptop",
  "database_schema_version": "003",  // Flask-Migrate revision
  "includes": {
    "database": true,
    "uploads": true,
    "settings": false,  // Settings excluded by default for security
    "credentials": false  // API keys NEVER included for security
  },
  "statistics": {
    "num_schemes": 5,
    "num_submissions": 127,
    "num_jobs": 127,
    "database_size_bytes": 5242880,
    "uploads_size_bytes": 104857600,
    "total_size_bytes": 110100480
  }
}
```

**Validation Rules** (on import):
- `backup_version` must be supported by current app version
- `database_schema_version` must be compatible (may trigger migrations)
- ZIP integrity checked (no corruption)
- File sizes must match metadata statistics (±1% tolerance)
- Database must be valid SQLite format

**Relationships**:
- Contains complete copy of main application database
- Contains all files referenced in `Submission.file_path`

**State Transitions**:
1. **Created**: User initiated export, ZIP file generated
2. **Transferred**: Copied to another machine (out of scope)
3. **Imported**: User initiated import, data restored to new installation

---

## Reused Existing Entities

The following entities from the existing web application are **reused without modification**:

### From Existing Web App (models.py)

1. **GradingScheme** - Reusable rubrics with hierarchical questions and criteria (003-structured-grading-scheme)
2. **Question** - Major sections within a grading scheme
3. **Criterion** - Individual evaluation points within questions
4. **Submission** - Student work to be evaluated
5. **Job** - Grading task execution records
6. **JobBatch** - Groups of related grading jobs
7. **Configuration** - System-wide settings (API providers, etc.)

**Storage**: SQLite database in user data directory (replaces PostgreSQL from web app)
- **Path**: `~/.local/share/GradingApp/grading.db` (Linux)
- **Path**: `%APPDATA%\GradingApp\grading.db` (Windows)
- **Path**: `~/Library/Application Support/GradingApp/grading.db` (macOS)

**Schema**: Identical to existing web app - no changes required

**Migrations**: Reuses existing Flask-Migrate migration scripts, auto-applied on startup

---

## Data Storage Architecture

### File System Layout

```
User Data Directory (platform-specific)
├── grading.db                  # SQLite database (existing models)
├── settings.json               # Application settings (new)
├── update_cache.json           # Cached update manifest (new)
├── logs/
│   ├── app.log
│   ├── flask.log
│   └── updates.log
├── uploads/                    # Submission files (existing)
│   ├── <submission_id_1>/
│   └── <submission_id_2>/
└── backups/                    # Automatic backups (new)
    ├── 20251116_100000/
    │   ├── grading.db
    │   └── settings.json
    └── 20251115_100000/
        ├── grading.db
        └── settings.json

OS Credential Manager
└── Service: "grading-app"
    ├── openrouter_api_key → (encrypted by OS)
    ├── claude_api_key → (encrypted by OS)
    └── ... (other providers)
```

### Database Connection Configuration

**Web App (existing)**:
```python
# PostgreSQL or SQLite based on DATABASE_URL environment variable
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
```

**Desktop App (new)**:
```python
# Always SQLite in user data directory
import sys
from pathlib import Path

def get_user_data_dir():
    if sys.platform == 'win32':
        base = Path(os.getenv('APPDATA'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux
        base = Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'GradingApp'

USER_DATA_DIR = get_user_data_dir()
SQLALCHEMY_DATABASE_URI = f'sqlite:///{USER_DATA_DIR}/grading.db'
```

---

## Data Migration Patterns

### From Web App to Desktop

**Not Applicable**: Desktop app and web app are different deployment modes of the same codebase. Users either:
1. Use web app (PostgreSQL + Redis)
2. Use desktop app (SQLite + Threading)

No migration between them is planned for initial release.

**Future Consideration**: Export from web app → Import to desktop app using Data Backup Bundle format.

### Desktop App Updates (Version N → N+1)

**Database Migrations**: Flask-Migrate handles schema updates automatically
- Run migrations on first startup after update
- Backup created before migrations apply
- Rollback to backup if migration fails

**Settings Migration**: Settings file includes `version` field
- App detects old version, applies transformations
- Example: v1.0 → v1.1 adds new `telemetry` field with default `false`

**Credential Migration**: No migration needed (OS credential manager handles persistence across updates)

---

## Data Integrity Constraints

### Application Settings
- **Atomicity**: Settings written atomically (write to temp file, rename on success)
- **Validation**: JSON schema validation before write
- **Backup**: Previous settings.json backed up as settings.json.bak

### Update Manifest
- **Signature Verification**: TUF signatures verified before trusting manifest
- **HTTPS Only**: Manifests retrieved over HTTPS
- **Checksum Validation**: Downloaded packages verified against SHA256 before application

### Credential Storage
- **Encryption at Rest**: OS-native encryption (DPAPI, Keychain, Secret Service)
- **Access Control**: Only current user can access
- **No Plaintext**: Keys never written to disk in plaintext (except in OS credential manager's encrypted storage)

### Data Backup Bundle
- **Integrity**: ZIP CRC32 checksums verify no corruption
- **Metadata Validation**: Statistics checked against actual contents
- **Schema Compatibility**: Database schema version checked before import

---

## Performance Considerations

### SQLite Optimization (Single-User Desktop)

**Configuration**:
```python
# app_wrapper.py
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
    cursor.execute("PRAGMA foreign_keys=ON")  # Enforce FK constraints
    cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
    cursor.close()
```

**Expected Performance**:
- Database startup: <100ms
- Query response: <50ms for typical grading queries
- Large imports (10,000 submissions): ~30-60 seconds

**Scalability Limits**:
- Tested up to 10,000 submissions (spec requirement: SC-004)
- SQLite performs well for single-user workloads
- For larger datasets (>100k submissions), recommend web app with PostgreSQL

---

## Data Security

### Threat Model

**In Scope**:
- ✅ Protect API keys from filesystem access by other users
- ✅ Prevent accidental exposure via backups/exports
- ✅ Verify update integrity (prevent malicious updates)

**Out of Scope** (acknowledged limitations):
- ❌ Protection against malware with admin/root privileges
- ❌ Protection against forensic disk analysis
- ❌ Encrypted database at rest (SQLite not encrypted by default)

### Mitigations

| Threat | Mitigation |
|--------|------------|
| API key theft via filesystem | OS credential manager with OS-level access controls |
| Malicious updates | TUF signatures + HTTPS + checksum verification |
| Database tampering | File permissions (user-only read/write) |
| Backup includes secrets | API keys excluded from backup bundles |
| Accidental commits to git | .gitignore includes user data directory |

---

## Testing Strategy

### Unit Tests
- Settings JSON serialization/deserialization
- Settings validation logic
- Update manifest parsing and validation
- Backup bundle creation and extraction
- Credential storage CRUD operations (mocked keyring)

### Integration Tests
- SQLite database creation in user data directory
- Settings persistence across app restarts
- Update check → download → apply workflow
- Backup export → import roundtrip (data fidelity)
- Credential storage → retrieval → Flask env var loading

### Platform-Specific Tests
- User data directory creation on Windows/macOS/Linux
- OS credential manager integration (WinVault, Keychain, SecretService)
- Permissions on created files (verify user-only access)

---

## Open Questions

1. **Database Encryption**: Should we offer optional database encryption at rest (e.g., SQLCipher)?
   - **Pro**: Enhanced security for sensitive grading data
   - **Con**: Adds dependency, performance overhead, user password management

2. **Settings Sync**: Should settings sync across multiple installations (e.g., via cloud config file)?
   - **Pro**: Consistent experience on multiple machines
   - **Con**: Requires cloud integration, privacy concerns

3. **Backup Automation**: Should backups run automatically or only on user request?
   - **Current**: Automatic daily backups (configurable)
   - **Question**: Is daily frequency appropriate, or should it be event-based (e.g., after importing submissions)?

4. **Credential Export**: Should Data Backup Bundle optionally include encrypted API keys?
   - **Pro**: Complete portability between machines
   - **Con**: Security risk if backup file compromised, complex key encryption

---

**Document Status**: ✅ **Complete**
**Next Step**: Generate API contracts in `contracts/` directory
