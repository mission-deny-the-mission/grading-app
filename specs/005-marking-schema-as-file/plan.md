# Implementation Plan: Marking Schemes as Files

**Branch**: `005-marking-schema-as-file` | **Date**: 2025-11-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-marking-schema-as-file/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable educators to save, load, and share marking schemes as JSON files. Core features include export/import functionality for all versions, document-based rubric conversion using LLM analysis, and web-version collaboration features (sharing with users and groups via configurable permissions). Technical approach: extend existing MarkingScheme/SchemeCriterion models with file serialization, implement document parser using existing LLM integration, add sharing/permission system for web platform using Flask-SQLAlchemy, and follow test-driven development with async document processing via Celery.

## Technical Context

**Language/Version**: Python 3.13.7 (per CLAUDE.md requirements)
**Primary Dependencies**: Flask 2.3.3, Flask-SQLAlchemy 3.0.5, Celery (async document processing), existing LLM provider abstraction (from 002-api-provider-security), PyPDF2 3.0.1, python-docx 0.8.11, Pillow (image handling)
**Storage**: SQLite for desktop version, database (PostgreSQL for production) for web version, local filesystem for exported JSON files
**Testing**: pytest (unit, integration, contract tests), minimum 80% coverage per constitution
**Target Platform**: Web (Flask) and desktop (via PyWebView), single-user desktop and multi-user web
**Project Type**: Web application with single-file modules at repo root (app.py, models.py, routes/, tasks.py)
**Performance Goals**: Document uploads <10MB processed within 30 seconds (SC-004), shared schemes visible within 5 seconds (SC-007), 95% valid import success rate (SC-005)
**Constraints**: File upload validation required, secure permission enforcement, audit trail for data integrity (per constitution), parameterized database queries
**Scale/Scope**: Extends existing MarkingScheme model (~20 new routes/endpoints for export/import/sharing), adds document processing pipeline, ~5-7 new database tables (SchemeShare, SharePermission, possibly DocumentUpload tracking)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Quality Over Speed**:
- [x] Feature prioritizes accuracy and reliability over rapid delivery
  - File format validation prevents corrupted imports
  - LLM conversion review workflow ensures quality before acceptance
  - Error messages guide users to correct problems
- [x] Robust validation and error handling planned for all critical paths
  - Import validation (FR-003): check file structure, required fields
  - Document processing: flag uncertain conversions (FR-011)
  - Permission enforcement: prevent unauthorized modifications (FR-019)

**Test-First Development (NON-NEGOTIABLE)**:
- [x] TDD workflow planned: tests → fail → implement → pass
  - All file operations: import/export round-trip tests
  - Document conversion: accuracy validation against known rubrics
  - Permission enforcement: verify view-only, editable, copy behaviors
  - Sharing state transitions: grant, revoke, auto-add to groups
- [x] Test coverage target ≥80% for new features
  - Unit tests: serialization, validation, permission checks
  - Integration tests: full import/export flow, multi-user sharing
  - Contract tests: LLM provider integration
- [x] Unit, integration, and contract tests identified

**AI Provider Agnostic**:
- [x] No tight coupling to specific AI provider implementation
  - Uses existing abstraction from 002-api-provider-security
  - Document analysis calls same LLM interface as grading
- [x] Common abstraction layer used for AI interactions

**Async-First Job Processing**:
- [x] All document processing executes through Celery task queues (FR-004, FR-005)
  - Document upload → LLM analysis → result presentation (async job)
  - No synchronous document parsing in request handlers
- [x] No synchronous grading in request handlers

**Data Integrity & Audit Trail**:
- [x] Complete audit trails planned (per FR-020 for shared schemes)
  - Track who shared with whom, when, with what permissions
  - Log permission changes (grant, revoke)
  - Record document conversion attempts (success/failure/uncertain)
  - Maintain original uploaded document for audit
- [x] All state transitions logged for reproducibility

**Security Requirements**:
- [x] File upload validation planned (type, size, content)
  - Document format validation: PDF, DOCX, PNG, JPG only (FR-010)
  - File size limit: 50MB max (assumption)
  - Content type verification (magic bytes for images)
- [x] API keys stored in environment variables only (existing from 002)
- [x] Parameterized database queries (no string concatenation)
  - New sharing queries use SQLAlchemy ORM

**Database Consistency**:
- [x] Migration scripts planned for all schema changes
  - New tables: SchemeShare, SharePermission enums, possibly DocumentUploadLog
  - New fields on MarkingScheme: owner_id for web version
- [x] Reversible migrations for rollback capability

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
# Monolithic Flask app (existing structure)
app.py                      # Main Flask app (add sharing blueprint)
models.py                   # Extend MarkingScheme, add SchemeShare, SharePermission
routes/
├── scheme_export.py        # POST/GET export, import endpoints
├── scheme_document.py      # Document upload, conversion endpoints
└── scheme_sharing.py       # Share, revoke, list shared schemes (web only)
tasks.py                    # Add Celery task for async document processing
services/
├── scheme_serializer.py    # JSON serialization/deserialization
├── document_parser.py      # Document → JSON via LLM
└── permission_checker.py   # Enforce share permissions

tests/
├── unit/
│   ├── test_scheme_serializer.py
│   ├── test_document_parser.py
│   └── test_permission_checker.py
├── integration/
│   ├── test_export_import_flow.py
│   ├── test_document_upload_flow.py
│   └── test_sharing_flow.py
└── contract/
    └── test_llm_provider_integration.py

migrations/
├── versions/
│   └── [new migration: add_scheme_share_table.py]
```

**Structure Decision**: Monolithic Flask app following existing patterns. New functionality in routes/ and services/, new models in models.py, async jobs in tasks.py. Existing approach (single-file modules at repo root) maximizes code reuse and consistency.

## Complexity Tracking

> **No constitution violations identified. All checks passed.**

No complexity tracking needed - all constitutional requirements met:
- Quality validation built into workflows (review before acceptance)
- TDD identified for all component tests
- Async processing mandatory for document analysis
- Existing LLM abstraction reused (no provider lock-in)
- Audit trails logged per FR-020
- Security validations comprehensive
