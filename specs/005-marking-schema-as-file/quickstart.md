# Phase 1: Quickstart Implementation Guide

**Feature**: 005-marking-schema-as-file | **Date**: 2025-11-17
**Objective**: Provide clear entry point and first implementation steps

---

## Overview

This feature extends the grading application to support:
1. **File-based persistence**: Export/import marking schemes as JSON
2. **Document conversion**: Upload PDF/DOCX/image rubrics → convert to marking schemes via LLM
3. **Collaboration** (web only): Share schemes with users/groups, configurable permissions

All components follow test-driven development, async-first for document processing, and maintain complete audit trails per constitution.

---

## Component Breakdown

### 1. Core: Marking Scheme Serialization (Phase 1a)
**Priority**: P1 - Foundational
**Effort**: Small (2-3 days)
**Dependencies**: None

**What**: JSON schema and serialization/deserialization logic

**Deliverables**:
- `services/scheme_serializer.py`:
  - `MarkingSchemeEncoder`: Serialize MarkingScheme → JSON
  - `MarkingSchemeDecoder`: JSON → MarkingScheme
  - `validate_scheme_json()`: Schema validation
  - JSON schema definition (in docstring or separate file)
- `tests/unit/test_scheme_serializer.py`: Round-trip tests, edge cases
- `routes/scheme_export.py` stub: GET/POST endpoints (basic implementation)

**Test Requirements** (TDD):
- Round-trip: export → import → verify identical
- Validation: reject invalid JSON (missing fields, type errors)
- Edge cases: empty criteria, null values, special characters

**Success Criteria**:
- All existing schemes can export without errors (SC-001 partial)
- Imported schemes restore all data (SC-001 partial)
- 95% of valid JSON imports succeed (SC-005 partial)

---

### 2. File I/O: Import/Export Routes (Phase 1b)
**Priority**: P1 - Foundational
**Effort**: Small (1-2 days)
**Dependencies**: Core serialization (1a)

**What**: Flask routes and file handling for export/import

**Deliverables**:
- `routes/scheme_export.py`:
  - `POST /schemes/{id}/export` → serialization + file storage
  - `GET /schemes/{id}/download` → file download
  - `POST /schemes/import` → file upload + deserialization
  - Error handling with clear messages (FR-009)
- File storage logic (filesystem or database column per deployment)
- Tests: upload/download round-trip, error cases, large files

**Test Requirements**:
- File upload validation (format, size)
- Successful export/download cycle
- Import error messages (FR-009: "Missing required field 'criteria'")
- Permission check: user can only export own schemes

**Success Criteria**:
- Users can complete export/import cycle (SC-001)
- 95% valid import success (SC-005)
- Clear error messages for invalid files (FR-009)

---

### 3. Document Processing Pipeline (Phase 2a)
**Priority**: P2 - Async foundation
**Effort**: Medium (4-5 days)
**Dependencies**: Core serialization (1a), LLM integration (existing 002)

**What**: Async Celery task for document → JSON conversion

**Deliverables**:
- `services/document_parser.py`:
  - `extract_document_text()`: PDF/DOCX/image text extraction
  - `call_llm_for_rubric_analysis()`: Call LLM provider abstraction with domain prompt
  - `parse_llm_response()`: Extract MarkingScheme from LLM output
- `tasks.py` addition:
  - `process_document_rubric`: Celery task (async)
  - Task monitoring, retry logic (exponential backoff)
- Models: DocumentUploadLog, DocumentConversionResult (via migration)
- `routes/scheme_document.py`:
  - `POST /schemes/{id}/documents/upload` → queue task, return conversion_id (202)
  - `GET /schemes/{id}/documents/{conversion_id}/status` → poll status
  - `GET /schemes/{id}/documents/{conversion_id}/result` → get result (after completion)
- Tests: mock LLM, verify extraction, accuracy on sample rubrics

**Test Requirements** (TDD):
- Successful document upload and queueing (202 response)
- Polling status (PENDING → PROCESSING → SUCCESS)
- Result extraction matches MarkingScheme schema
- Error handling: corrupted PDF, unsupported format, LLM timeout
- Uncertainty flags: ambiguous sections marked for review (FR-011)
- Accuracy: 85% on test rubrics (SC-002)

**Success Criteria**:
- Document upload queued within 2 seconds (FR-004)
- LLM processing completes within 30 seconds for <10MB (SC-004)
- Result usable without manual correction for clear rubrics (SC-003)
- Uncertain conversions flagged (FR-011)

---

### 4. Sharing System (Phase 2b - Web Only)
**Priority**: P2 - Collaboration
**Effort**: Medium (4-5 days)
**Dependencies**: Core serialization (1a), User/Group models (must exist)

**What**: Permission-based sharing for web version

**Deliverables**:
- Models extension (migration):
  - MarkingScheme: add owner_id, created_at, updated_at, is_shared
  - SchemeShare: new table (scheme_id, user_id/group_id, permission, audit fields)
  - SharePermission: enum (VIEW_ONLY, EDITABLE, COPY)
- `services/permission_checker.py`:
  - `check_scheme_permission()`: Verify user access + permission
  - `can_edit_scheme()`, `can_view_scheme()`, `can_copy_scheme()`: Helper checks
  - Handle direct owner access (always full access)
- `routes/scheme_sharing.py`:
  - `POST /schemes/{id}/share` → grant access to users/groups
  - `DELETE /schemes/{id}/share/{share_id}/revoke` → revoke access
  - `GET /schemes/{id}/shares` → list all shares (owner only)
  - `GET /schemes/shared-with-me` → list accessible schemes
  - Permission enforcement on all operations
- Middleware: Check permission before route execution
- Tests: permission enforcement, group membership, revocation

**Test Requirements** (TDD):
- Grant access: user/group can see scheme (FR-012, FR-013)
- Permission enforcement: VIEW_ONLY cannot modify (FR-019)
- Revocation: immediate access loss (SC-010)
- Group auto-add: new group member gets access (FR-013)
- Group removal: member loses access (unless individually shared)
- Notification: recipients notified on share (FR-018)

**Success Criteria**:
- Shares visible within 5 seconds (SC-007)
- Permissions enforced (up to 50 recipients per action) (SC-008, SC-009)
- Revocation takes effect immediately (SC-010)

---

### 5. Data Model Extensions (Parallel with phases)
**Priority**: P1 - All phases require this
**Effort**: Small (1 day)
**Dependencies**: None initially

**What**: Database migrations and model updates

**Deliverables**:
- Migration files (Flask-Migrate):
  - `add_owner_id_to_marking_scheme.py`
  - `create_scheme_share_table.py`
  - `create_document_upload_log_table.py`
  - `create_document_conversion_result_table.py`
- Model updates (models.py):
  - Extend MarkingScheme: owner_id FK, created_at, updated_at
  - New SchemeShare class
  - New DocumentUploadLog class
  - New DocumentConversionResult class
- All with relationships, validation, constraints

**Test Requirements**:
- Migration reversibility
- Data integrity constraints enforced
- Relationships work correctly

---

## Implementation Sequence

```
Phase 1: Core Features (Weeks 1-2)
├── 1a. Serialization (TDD: tests → code)
│   ├── tests/unit/test_scheme_serializer.py
│   └── services/scheme_serializer.py
├── 1b. Export/Import Routes (TDD)
│   ├── tests/integration/test_export_import_flow.py
│   └── routes/scheme_export.py
└── 1c. Data Model Extensions
    └── migrations/ + models.py updates

Phase 2: Advanced Features (Weeks 3-4)
├── 2a. Document Processing (TDD)
│   ├── tests/contract/test_llm_provider_integration.py
│   ├── services/document_parser.py
│   ├── routes/scheme_document.py
│   └── tasks.py addition
└── 2b. Sharing System (TDD, web version only)
    ├── tests/integration/test_sharing_flow.py
    ├── services/permission_checker.py
    └── routes/scheme_sharing.py

Phase 3: Testing & Refinement (Week 5+)
├── Accuracy testing: Document conversion on real rubrics
├── Performance testing: Large documents, concurrent conversions
├── UX testing: Error messages, workflow clarity
├── Load testing: Sharing at scale (50+ recipients)
└── Security testing: Permission enforcement, file validation
```

---

## Key Technical Decisions

| Component | Choice | Why |
|-----------|--------|-----|
| Export Format | JSON | Human-readable, widely supported, schema validation |
| Document Extraction | PyPDF2 + python-docx + Pillow | Already in requirements, native parsers faster than OCR |
| LLM Integration | Existing provider abstraction | Avoids lock-in, async via Celery |
| Permissions | Role-based (3 levels) | Simple mental model, covers educator workflows |
| Async Processing | Celery with dedicated queue | Already in project, enables parallel conversions |
| Storage | Filesystem (desktop), DB field (web) | Follows existing patterns, simple for initial MVP |

---

## Testing Strategy

**Unit Tests** (70% of coverage):
- Serialization round-trips
- JSON schema validation
- Permission logic
- Document extraction on mock files

**Integration Tests** (25% of coverage):
- Export → download → import flow
- Document upload → conversion → acceptance
- Sharing → permission check → access

**Contract Tests** (5% of coverage):
- LLM provider integration (mock API responses)

**Manual Tests**:
- Real document rubrics (various formats)
- Multi-user sharing scenarios
- Large documents (edge cases)

**Coverage Target**: 80% per constitution

---

## Success Metrics & Monitoring

**During Development**:
- Test coverage: Track 80%+ target
- Build success: All tests passing before merge
- Performance: Document <10MB processes in <30s (log times)

**Post-Deployment**:
- Export success rate: Track failures, error messages
- Import success rate: Monitor validation failures (SC-005: target 95%)
- Document conversion accuracy: User review feedback (SC-002: target 85%)
- Share adoption: % of schemes shared, usage rate (SC-011: target 90% within 7 days)
- Revocation latency: Audit trail entries

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM accuracy on rubrics | Test with diverse sample rubrics, set expectation at 85%, flag uncertain fields |
| Large document timeouts | 30-second processing limit, async job, clear "processing" UI feedback |
| Corrupted exports | Strict JSON schema validation, error messages guide fixing |
| Permission bypasses | Comprehensive unit + integration tests, security code review |
| Sharing confusion | Clear UI labels, permission icons, notification messages |
| Database schema conflicts | Reversible migrations, test rollback, dry-run on production-like DB |

---

## Deployment Considerations

**Prerequisites**:
- Celery workers running (required for document processing)
- LLM API provider configured (from feature 002)
- Group management system (for sharing recipients)

**Rollout Strategy**:
1. Phase 1 (export/import): Deploy to both desktop + web
2. Phase 2a (document conversion): Deploy to both with feature flag
3. Phase 2b (sharing): Deploy to web version only with feature flag

**Database Migration**:
- Run migrations in order (schema must be ready before code)
- Test rollback on staging environment
- Backup before production migration

**Monitoring**:
- Log all export/import operations (audit trail)
- Monitor document conversion queue depth and processing times
- Alert on conversion failures (LLM API issues)

---

## Next Steps

1. **Setup**: Create feature branch (already: `005-marking-schema-as-file`)
2. **Design Review**: Review this plan + data model + API contracts
3. **Start Phase 1a**: Implement serialization with TDD
4. **Iterate**: Complete each phase with full test coverage
5. **Integration**: Merge to main after all phases complete + 80% coverage

See `/speckit.tasks` for detailed task breakdown and dependency ordering.
