# Implementation Plan: Desktop Application

**Branch**: `004-desktop-app` | **Date**: 2025-11-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-desktop-app/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a native desktop application for Windows, macOS, and Linux that bundles the existing Flask-based grading web app with an embedded runtime and provides easy installation, offline functionality, secure credential storage, automatic updates, and cross-platform data portability. The application must start within 10 seconds, run entirely offline except for AI API calls, and support seamless data export/import between installations.

## Technical Context

**Language/Version**: Python 3.13.7 (existing web app), NEEDS CLARIFICATION (desktop framework choice - Electron alternatives, PyInstaller, Tauri, etc.)
**Primary Dependencies**: Flask 2.3.3, Flask-SQLAlchemy 3.0.5, existing web app dependencies, NEEDS CLARIFICATION (desktop packaging toolchain)
**Storage**: SQLite (replacing PostgreSQL/Redis for single-user desktop), local filesystem for uploads and backups
**Testing**: pytest (existing), NEEDS CLARIFICATION (desktop integration testing framework, installer testing)
**Target Platform**: Windows 10+, macOS 11+, Ubuntu 20.04+ (cross-platform desktop)
**Project Type**: Desktop application wrapping existing web application
**Performance Goals**: <10s startup time, <500MB RAM idle, <1GB RAM active grading, <150MB installer size
**Constraints**: Offline-first (except AI API calls and updates), single-user deployment, bundled dependencies (no manual installation)
**Scale/Scope**: Single-user desktop application, existing grading features, 4 new user stories (P1-P4), ~10,000 submission database support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Quality Over Speed**:
- [x] Feature prioritizes accuracy and reliability over rapid delivery
- [x] Robust validation and error handling planned for all critical paths
  - Installer validation, update integrity checks, data export/import validation

**Test-First Development (NON-NEGOTIABLE)**:
- [x] TDD workflow planned: tests → fail → implement → pass
- [x] Test coverage target ≥80% for new features
- [x] Unit, integration, and contract tests identified
  - Unit: Desktop wrapper logic, update mechanisms, data portability
  - Integration: Full app startup, installer workflows, update processes
  - Contract: Existing web app compatibility, OS credential storage APIs

**AI Provider Agnostic**:
- [x] No tight coupling to specific AI provider implementation
- [x] Common abstraction layer used for AI interactions
  - Reuses existing web app's provider abstraction layer

**Async-First Job Processing**:
- [⚠️] All grading operations execute through Celery task queues
- [⚠️] No synchronous grading in request handlers
  - **NEEDS CLARIFICATION**: Desktop app is single-user, may replace Celery/Redis with threading/async for simplicity
  - Existing web app grading logic remains async (reused as-is)

**Data Integrity & Audit Trail**:
- [x] Complete audit trails planned (submissions, criteria, models, timestamps, retries)
- [x] All state transitions logged for reproducibility
  - Reuses existing web app's audit trail mechanisms
  - Adds desktop-specific logs: app version, update history, export/import events

**Security Requirements**:
- [x] File upload validation planned (type, size, content)
  - Reuses existing web app validation
- [⚠️] API keys stored in environment variables only
  - **MODIFIED FOR DESKTOP**: Keys stored in OS-native credential manager (Keychain/Credential Manager/Secret Service)
  - Environment variables not suitable for desktop GUI apps
- [x] Parameterized database queries (no string concatenation)
  - Reuses existing SQLAlchemy ORM

**Database Consistency**:
- [x] Migration scripts planned for all schema changes
- [x] Reversible migrations for rollback capability
  - Reuses existing Flask-Migrate infrastructure
  - Desktop app runs migrations automatically on startup

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Existing web application (reused as-is)
app.py                    # Flask application entry point
models.py                 # SQLAlchemy models (existing)
tasks.py                  # Celery tasks (existing, may be adapted)
routes/                   # Flask routes (existing)
utils/                    # Utilities including LLM providers (existing)
templates/                # Jinja templates (existing)
static/                   # CSS/JS assets (existing)

# New desktop application components
desktop/
├── main.py              # Desktop app entry point
├── app_wrapper.py       # Flask server lifecycle management
├── window_manager.py    # Native window/tray management
├── updater.py           # Auto-update mechanism
├── credentials.py       # OS credential storage integration
├── data_export.py       # Export/import functionality
├── installer/           # Platform-specific installer configs
│   ├── windows/         # NSIS/Inno Setup/WiX configs
│   ├── macos/           # DMG/pkg builder configs
│   └── linux/           # AppImage/DEB/RPM specs
└── resources/           # Icons, splash screens, assets

# Desktop-specific tests
tests/
├── unit/                # Existing unit tests
├── integration/         # Existing integration tests
├── contract/            # Existing contract tests
└── desktop/             # New desktop-specific tests
    ├── test_wrapper.py
    ├── test_updater.py
    ├── test_credentials.py
    ├── test_export.py
    └── test_installer.py

# Build artifacts (gitignored)
dist/                    # Compiled installers
build/                   # Build intermediates
```

**Structure Decision**: Hybrid approach - reuse existing Flask web application code entirely, add new `desktop/` module for desktop-specific functionality (packaging, updates, credentials, data portability). This minimizes duplication and maintains single source of truth for grading logic.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| API keys in OS credential manager (not env vars) | Desktop GUI apps don't have persistent environment variables like servers do. Users need seamless experience without editing config files. | Environment variables require technical knowledge and manual editing. OS credential managers provide secure, encrypted storage with zero user configuration. |
| Replace Celery/Redis with threading (pending research) | Desktop is single-user, bundling Redis adds 50MB+ to installer and complexity. Python threading/asyncio can handle async grading without external dependencies. | Celery requires Redis broker which is overkill for single-user desktop. Simpler async approaches reduce installer size and eliminate network dependencies. |
