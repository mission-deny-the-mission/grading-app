# Tasks: Marking Schemes as Files

**Feature**: 005-marking-schema-as-file | **Branch**: `005-marking-schema-as-file`
**Total Tasks**: 52 | **Phases**: 7 | **Estimated Duration**: 4-5 weeks
**Test Approach**: Test-Driven Development (TDD) - tests written before implementation

---

## Executive Summary

This feature enables educators to save, load, share, and convert marking schemes. Implementation follows 6 user stories in priority order:

| US | Story | Priority | Dependencies | Tests Required |
|----|-------|----------|--------------|-----------------|
| US1 | Export Marking Schemes | P1 | None | Round-trip tests |
| US2 | Import Marking Schemes | P1 | US1 | Validation tests |
| US3 | Document Upload & Convert | P2 | US1 | LLM integration tests |
| US4 | Reuse Schemes | P2 | US1 + US2 | Assignment linking tests |
| US5 | Share with Users (Web) | P2 | US1 + Models | Permission enforcement tests |
| US6 | Share with Groups (Web) | P3 | US5 + Groups exist | Group membership tests |

**MVP Scope** (Weeks 1-2): US1 + US2 (core file operations)
**Extended Scope** (Weeks 3-5): US3, US4, US5, US6 (advanced features)

---

## Implementation Strategy

1. **Phase 1: Setup** - Project initialization and test infrastructure
2. **Phase 2: Foundational** - Shared components (JSON schema, migrations, models)
3. **Phase 3: US1** - Export marking schemes (core serialization)
4. **Phase 4: US2** - Import marking schemes (deserialization + validation)
5. **Phase 5: US3** - Document upload and conversion (async LLM processing)
6. **Phase 6: US4** - Reuse schemes (schema cloning across assignments)
7. **Phase 7: US5+US6** - Sharing (web-version collaboration)

**Parallel Execution**: Tasks marked [P] can run in parallel with independent tasks in the same phase.

---

# Phase 1: Setup & Infrastructure

## Phase Goal
Initialize project structure, testing framework, and supporting infrastructure for all user stories.

### Setup Tasks

- [ ] T001 Create feature branch and verify initial state from 005-marking-schema-as-file
- [ ] T002 Review and document existing MarkingScheme, SchemeCriterion models in models.py
- [ ] T003 Verify pytest configuration and test runner (run_tests.py, conftest.py)
- [ ] T004 Create tests/ directory structure: unit/, integration/, contract/ subdirectories
- [ ] T005 [P] Create services/ directory for new services (scheme_serializer, document_parser, permission_checker)
- [ ] T006 [P] Create routes/ directory for new blueprints if not existing (scheme_export, scheme_document, scheme_sharing)
- [ ] T007 [P] Create fixtures/ directory for test data (sample rubrics, JSON schemas, mock documents)
- [ ] T008 Create migrations/ directory structure for database schema changes
- [ ] T009 Document existing database schema (MarkingScheme, SchemeCriterion) - examine models.py carefully
- [ ] T010 [P] Add dependencies to requirements.txt if needed (verify: jsonschema, PyPDF2, python-docx, Pillow already present)

---

# Phase 2: Foundational (Blocking for All User Stories)

## Phase Goal
Implement shared infrastructure: JSON schema, database models, and validation framework.

### Foundational Tasks

- [ ] T011 [P] Define JSON schema for MarkingScheme export format in specs/005-marking-schema-as-file/json-schema.json
- [ ] T012 [P] Create test fixture: sample_schemes.py with 3-5 test marking schemes (varying complexity)
- [ ] T013 [P] Create test fixture: sample_documents.py with mock PDF/DOCX/image files for conversion testing
- [ ] T014 Create migration: add_owner_id_to_marking_scheme.py (owner_id FK, created_at, updated_at, is_shared columns)
- [ ] T015 [P] Create migration: create_scheme_share_table.py (SchemeShare: scheme_id, user_id/group_id, permission, audit fields)
- [ ] T016 [P] Create migration: create_document_upload_log_table.py (DocumentUploadLog: file metadata, LLM provider tracking, status)
- [ ] T017 [P] Create migration: create_document_conversion_result_table.py (DocumentConversionResult: extracted scheme, uncertainty flags)
- [ ] T018 Extend models.py: Add MarkingScheme.owner_id, created_at, updated_at, is_shared attributes
- [ ] T019 [P] Add MarkingScheme relationships: one-to-many with SchemeShare
- [ ] T020 Create models.py: New SchemeShare class (scheme_id FK, user_id/group_id FK, permission enum, timestamps)
- [ ] T021 [P] Create models.py: New DocumentUploadLog class (upload metadata, LLM tracking, status)
- [ ] T022 [P] Create models.py: New DocumentConversionResult class (extracted scheme JSON, uncertainty flags, status)
- [ ] T023 Create models.py: Add SharePermission enum (VIEW_ONLY, EDITABLE, COPY)
- [ ] T024 Run migrations: Execute all migration files in order against test database
- [ ] T025 [P] Create services/schema_validator.py: validate_scheme_json() function with schema checking
- [ ] T026 [P] Create services/error_messages.py: Standardized error messages for import validation failures (FR-009)
- [ ] T027 Write integration test: test_database_migrations.py - verify migration reversibility and data integrity

---

# Phase 3: User Story 1 - Export Marking Schemes (P1)

**Story Goal**: Enable educators to export marking schemes as JSON files for portability and backup.

**Independent Test Criteria**:
- Existing scheme can be exported to JSON without errors
- Exported JSON structure matches JSON schema
- JSON is human-readable and properly formatted
- Multiple exports have unique file names

**Acceptance Criteria** (from spec):
1. Completed scheme → JSON file (FR-001, FR-008)
2. Human-readable, consistent formatting (FR-001)
3. Unique identification by date/version (naming) (FR-001)

---

## Phase 3 Tasks

### Tests (TDD - Write First)

- [ ] T028 [P] [US1] Write unit test: tests/unit/test_scheme_serializer.py - test serialize_marking_scheme() basic functionality
- [ ] T029 [P] [US1] Write unit test: tests/unit/test_scheme_serializer.py - test serialization of criteria with all fields
- [ ] T030 [P] [US1] Write unit test: tests/unit/test_scheme_serializer.py - test JSON output validates against schema
- [ ] T031 [P] [US1] Write unit test: tests/unit/test_scheme_serializer.py - test handling of null/empty criteria
- [ ] T032 [P] [US1] Write integration test: tests/integration/test_export_import_flow.py - test POST /schemes/{id}/export returns 200 with file_url
- [ ] T033 [P] [US1] Write integration test: tests/integration/test_export_import_flow.py - test exported file can be read and parsed as JSON
- [ ] T034 [P] [US1] Write integration test: tests/integration/test_export_import_flow.py - test user can only export own schemes (permission check)
- [ ] T035 [US1] Write integration test: tests/integration/test_export_import_flow.py - test export with custom file name parameter

### Implementation

- [ ] T036 [P] [US1] Create services/scheme_serializer.py: Implement MarkingSchemeEncoder class - serialize MarkingScheme → JSON
  - Methods: serialize(), to_dict(), encode_criteria(), encode_descriptors()
  - Include metadata: name, description, export_date, version
  - Handle all fields per JSON schema definition
- [ ] T037 [US1] Create services/scheme_serializer.py: Implement json_default() helper for custom JSON encoding
- [ ] T038 [P] [US1] Create routes/scheme_export.py: Implement POST /schemes/{id}/export endpoint
  - Route: POST /schemes/{id}/export
  - Verify user authorization (owner check)
  - Call serializer to convert scheme to JSON
  - Generate file name (scheme_name_YYYY-MM-DD.json)
  - Store file (filesystem for now, database column for web version)
  - Return response with file_url, file_name, export_date
  - Handle errors: scheme not found (404), unauthorized (403), serialization failure (500)
- [ ] T039 [P] [US1] Create routes/scheme_export.py: Implement GET /schemes/{id}/download endpoint
  - Route: GET /schemes/{id}/download
  - Retrieve previously exported JSON file
  - Return with appropriate Content-Disposition header (attachment)
  - Handle errors: file not found (404), access denied (403)
- [ ] T040 [US1] Add routes/scheme_export.py blueprint registration to app.py
- [ ] T041 [P] [US1] Create tests/unit/test_scheme_serializer.py: Run all unit tests and verify 100% pass
- [ ] T042 [P] [US1] Create tests/integration/test_export_import_flow.py: Run all integration tests and verify functionality

---

# Phase 4: User Story 2 - Import Marking Schemes (P1)

**Story Goal**: Enable educators to load marking schemes from JSON files, supporting reuse across assignments.

**Independent Test Criteria**:
- Valid JSON file can be imported without errors
- Imported scheme data matches original (round-trip)
- Invalid files show clear error messages
- Import failures don't corrupt database

**Acceptance Criteria** (from spec):
1. Import JSON → restore scheme (FR-002)
2. Imported data matches original (FR-008)
3. Clear error messages for validation failures (FR-009)

---

## Phase 4 Tasks

### Tests (TDD - Write First)

- [ ] T043 [P] [US2] Write unit test: tests/unit/test_scheme_deserializer.py - test deserialize_json_to_scheme() with valid JSON
- [ ] T044 [P] [US2] Write unit test: tests/unit/test_scheme_deserializer.py - test schema validation rejects invalid JSON (missing criteria)
- [ ] T045 [P] [US2] Write unit test: tests/unit/test_scheme_deserializer.py - test schema validation rejects malformed JSON syntax
- [ ] T046 [P] [US2] Write unit test: tests/unit/test_scheme_deserializer.py - test error messages for specific validation failures (FR-009)
- [ ] T047 [P] [US2] Write unit test: tests/unit/test_scheme_deserializer.py - test handling of optional fields (description, metadata)
- [ ] T048 [US2] Write integration test: tests/integration/test_export_import_flow.py - test round-trip: export → import → verify identical
- [ ] T049 [US2] Write integration test: tests/integration/test_export_import_flow.py - test POST /schemes/import with valid file (201)
- [ ] T050 [US2] Write integration test: tests/integration/test_export_import_flow.py - test POST /schemes/import with invalid JSON (400)
- [ ] T051 [US2] Write integration test: tests/integration/test_export_import_flow.py - test POST /schemes/import with missing fields (400 with detailed error)
- [ ] T052 [P] [US2] Write integration test: tests/integration/test_export_import_flow.py - test large scheme import (50+ criteria) completes successfully

### Implementation

- [ ] T053 [P] [US2] Create services/scheme_deserializer.py: Implement MarkingSchemeDecoder class - JSON → MarkingScheme
  - Methods: deserialize(), from_dict(), decode_criteria(), decode_descriptors()
  - Validate all fields against JSON schema
  - Create MarkingScheme database object
  - Handle version compatibility
- [ ] T054 [US2] Create services/scheme_deserializer.py: Implement validate_scheme_json() with jsonschema.validate()
  - Load JSON schema from specs/005-marking-schema-as-file/json-schema.json
  - Validate structure, field types, enum values
  - Return detailed validation errors (field, expected, actual)
- [ ] T055 [P] [US2] Create services/scheme_deserializer.py: Implement detailed error collection and reporting
  - Collect ALL validation errors (don't fail on first error)
  - Format errors for user display: field path, error type, suggestion
  - Example: "criteria[0].descriptors[1].level: must be one of [excellent, good, satisfactory, poor, fail]"
- [ ] T056 [P] [US2] Create routes/scheme_export.py: Implement POST /schemes/import endpoint
  - Route: POST /schemes/import
  - Accept multipart/form-data file upload
  - Validate file type: must be JSON
  - Validate file size: < 10MB
  - Parse JSON
  - Call validator and deserializer
  - Create new MarkingScheme object in database
  - Return 201 with created scheme_id, name, criteria_count
  - Return 400 with validation errors if import fails (FR-009)
  - Handle errors: invalid file, schema mismatch, database failure
- [ ] T057 [US2] Add error handler in app.py for import-specific exceptions
- [ ] T058 [P] [US2] Create tests/unit/test_scheme_deserializer.py: Run all unit tests and verify 100% pass
- [ ] T059 [P] [US2] Create tests/integration/test_export_import_flow.py: Run all integration tests and verify round-trip works

---

# Phase 5: User Story 3 - Document Upload & Convert (P2)

**Story Goal**: Enable educators to upload document-based rubrics (PDF, DOCX, images) and automatically convert to marking schemes via LLM.

**Independent Test Criteria**:
- Document file accepted and queued (202 response)
- Conversion status polling works (returns PENDING → SUCCESS)
- Extracted scheme validates against JSON schema
- Uncertain conversions flagged for review
- LLM integration tested via mocked responses

**Acceptance Criteria** (from spec):
1. Document accepted and queued (FR-004)
2. LLM generates marking scheme (FR-005)
3. User can review and edit before acceptance (FR-006, FR-007)
4. Uncertain conversions flagged (FR-011)
5. Supports PDF, DOCX, PNG, JPG (FR-010)

---

## Phase 5 Tasks

### Tests (TDD - Write First)

- [ ] T060 [P] [US3] Write unit test: tests/unit/test_document_parser.py - test extract_text_from_pdf() with sample PDF
- [ ] T061 [P] [US3] Write unit test: tests/unit/test_document_parser.py - test extract_text_from_docx() with sample DOCX
- [ ] T062 [P] [US3] Write unit test: tests/unit/test_document_parser.py - test extract_text_from_image() with sample PNG/JPG
- [ ] T063 [P] [US3] Write unit test: tests/unit/test_document_parser.py - test parse_llm_response() extracts MarkingScheme from LLM output (mocked)
- [ ] T064 [P] [US3] Write unit test: tests/unit/test_document_parser.py - test uncertainty_flags extracted from LLM confidence values
- [ ] T065 [US3] Write contract test: tests/contract/test_llm_provider_integration.py - verify LLM provider abstraction (from 002) is called correctly
- [ ] T066 [US3] Write contract test: tests/contract/test_llm_provider_integration.py - mock LLM response and verify parsing handles various formats
- [ ] T067 [P] [US3] Write integration test: tests/integration/test_document_upload_flow.py - test POST /schemes/{id}/documents/upload returns 202 with conversion_id
- [ ] T068 [P] [US3] Write integration test: tests/integration/test_document_upload_flow.py - test GET /schemes/{id}/documents/{conversion_id}/status polls status correctly
- [ ] T069 [P] [US3] Write integration test: tests/integration/test_document_upload_flow.py - test status transitions: PENDING → PROCESSING → SUCCESS
- [ ] T070 [US3] Write integration test: tests/integration/test_document_upload_flow.py - test GET /schemes/{id}/documents/{conversion_id}/result returns extracted scheme
- [ ] T071 [US3] Write integration test: tests/integration/test_document_upload_flow.py - test invalid document format rejected (400)
- [ ] T072 [US3] Write integration test: tests/integration/test_document_upload_flow.py - test file size validation (reject >50MB)
- [ ] T073 [P] [US3] Write integration test: tests/integration/test_document_upload_flow.py - test uncertainty flags included in result
- [ ] T074 [US3] Write integration test: tests/integration/test_document_upload_flow.py - test POST /schemes/{id}/documents/{conversion_id}/accept saves scheme

### Implementation

- [ ] T075 [P] [US3] Create services/document_parser.py: Implement extract_document_text() for PDF
  - Use PyPDF2.PdfReader
  - Extract text from all pages
  - Return combined text string
  - Handle corrupted PDFs gracefully (log error, raise exception)
- [ ] T076 [P] [US3] Create services/document_parser.py: Implement extract_document_text() for DOCX
  - Use python-docx Document
  - Extract paragraphs and tables
  - Preserve structure (section headers, bullets)
  - Return formatted text string
- [ ] T077 [P] [US3] Create services/document_parser.py: Implement extract_document_text() for images
  - Use Pillow to verify image format
  - Call OCR (integrate with existing OCR from 001-ocr-image-grading if available)
  - Return extracted text
  - Log confidence/quality metrics
- [ ] T078 [P] [US3] Create services/document_parser.py: Implement detect_document_type() and route to correct extractor
  - Detect from file extension
  - Verify from magic bytes (content)
  - Return document_type and extracted text
  - Raise error for unsupported formats
- [ ] T079 [US3] Create services/document_parser.py: Implement get_llm_provider() using existing abstraction from 002-api-provider-security
  - Get provider from app config
  - Initialize with credentials from environment
  - Return provider instance
  - Handle errors: provider not configured
- [ ] T080 [P] [US3] Create services/document_parser.py: Implement call_llm_for_rubric_analysis()
  - Build prompt: "Parse this rubric document and extract marking criteria, performance levels, descriptions, and point values"
  - Include extracted text in prompt
  - Call LLM provider with error handling (retry logic, timeout)
  - Return raw LLM response string
  - Track provider and model used (for audit trail)
- [ ] T081 [P] [US3] Create services/document_parser.py: Implement parse_llm_response()
  - Parse LLM output (may be JSON, free text, or structured)
  - Extract: criteria names, levels, descriptions, point values
  - Map to MarkingScheme schema
  - Identify uncertain/ambiguous fields (low confidence)
  - Return dict with extracted_scheme and uncertainty_flags
  - Example: {"confidence": 0.7, "field": "criteria[0].point_value", "reason": "Not explicitly stated in rubric"}
- [ ] T082 [US3] Create services/document_parser.py: Implement create_marking_scheme_from_extracted()
  - Validate extracted data against JSON schema
  - Create MarkingScheme database object
  - Set default values if fields missing
  - Return new scheme or raise validation error
- [ ] T083 [P] [US3] Create tasks.py: Implement Celery task process_document_rubric()
  - Task signature: process_document_rubric(upload_id: UUID, file_path: str, document_type: str)
  - Task steps:
    1. Mark DocumentConversionResult as PROCESSING
    2. Extract text from document
    3. Call LLM for analysis
    4. Parse response
    5. Validate extracted scheme
    6. Store in DocumentConversionResult.extracted_scheme
    7. Mark as SUCCESS or FAILED
  - Implement retry logic: exponential backoff, max 3 retries (transient errors only)
  - Log all steps to DocumentUploadLog
  - Handle errors: log details, mark as FAILED with error_message
- [ ] T084 [P] [US3] Create routes/scheme_document.py: Implement POST /schemes/{id}/documents/upload endpoint
  - Route: POST /schemes/{id}/documents/upload
  - Accept multipart/form-data with document file
  - Validate file size: < 50MB
  - Validate file type: PDF, DOCX, PNG, JPG only
  - Create DocumentUploadLog record
  - Create DocumentConversionResult placeholder (PENDING)
  - Queue Celery task: process_document_rubric
  - Return 202 Accepted with conversion_id
  - Response includes: conversion_id, status, estimated_seconds
  - Handle errors: invalid format (400), file too large (413)
- [ ] T085 [P] [US3] Create routes/scheme_document.py: Implement GET /schemes/{id}/documents/{conversion_id}/status endpoint
  - Route: GET /schemes/{id}/documents/{conversion_id}/status
  - Retrieve DocumentConversionResult by conversion_id
  - Return current status (PENDING, PROCESSING, SUCCESS, FAILED)
  - Return progress percentage (estimated)
  - If SUCCESS: include extracted_scheme and uncertainty_flags
  - If FAILED: include error_code and error_message
  - Handle errors: conversion not found (404)
- [ ] T086 [US3] Create routes/scheme_document.py: Implement GET /schemes/{id}/documents/{conversion_id}/result endpoint
  - Route: GET /schemes/{id}/documents/{conversion_id}/result
  - Retrieve DocumentConversionResult after completion
  - Return: extracted_scheme, uncertainty_flags, llm_provider, conversion_time_ms
  - Return 202 if still processing
  - Return 400 if conversion failed
  - Handle errors: not found (404)
- [ ] T087 [P] [US3] Create routes/scheme_document.py: Implement POST /schemes/{id}/documents/{conversion_id}/accept endpoint
  - Route: POST /schemes/{id}/documents/{conversion_id}/accept
  - Retrieve DocumentConversionResult
  - Accept optionally modified extracted_scheme from request body
  - Validate against JSON schema
  - Create new MarkingScheme from extracted data
  - Save to database
  - Return 201 with new scheme_id
  - Handle errors: validation failure (422), not found (404)
- [ ] T088 [US3] Add routes/scheme_document.py blueprint registration to app.py
- [ ] T089 [P] [US3] Create tests/unit/test_document_parser.py: Run all unit tests and verify extraction works
- [ ] T090 [P] [US3] Create tests/contract/test_llm_provider_integration.py: Run contract tests with mocked LLM
- [ ] T091 [P] [US3] Create tests/integration/test_document_upload_flow.py: Run integration tests and verify full pipeline works

---

# Phase 6: User Story 4 - Reuse Schemes (P2)

**Story Goal**: Enable efficient reuse of saved schemes across assignments and courses.

**Independent Test Criteria**:
- Imported scheme can be loaded for new assignment without errors
- Multiple assignments can use same scheme with identical data
- Scheme data isolated per assignment (no cross-contamination)

**Acceptance Criteria** (from spec):
1. Load saved scheme for new assignment (FR-002)
2. Multiple assignments maintain identical criteria (FR-008)

---

## Phase 6 Tasks

### Tests (TDD - Write First)

- [ ] T092 [P] [US4] Write integration test: tests/integration/test_scheme_reuse.py - test import scheme and assign to assignment
- [ ] T093 [P] [US4] Write integration test: tests/integration/test_scheme_reuse.py - test load same scheme for 2 assignments
- [ ] T094 [P] [US4] Write integration test: tests/integration/test_scheme_reuse.py - test modifying scheme in one assignment doesn't affect other
- [ ] T095 [P] [US4] Write integration test: tests/integration/test_scheme_reuse.py - test 10+ assignments using same scheme

### Implementation

- [ ] T096 [US4] Extend existing assignment creation flow in app/routes/main.py or appropriate location:
  - Add option to "Use existing scheme" when creating assignment
  - Query available MarkingScheme objects
  - Allow selection of scheme to use
  - Link assignment to selected scheme
  - No schema changes needed (Assignment model already has scheme_id relationship)
  - Verify no existing tests break
- [ ] T097 [P] [US4] Create tests/integration/test_scheme_reuse.py: Run tests verifying scheme reuse works correctly
- [ ] T098 [US4] Verify existing assignment endpoints work with imported schemes (no modifications needed if relationship already exists)

---

# Phase 7: User Story 5 & 6 - Sharing (P2/P3, Web Version Only)

**Story Goal** (US5): Enable educators to share schemes with colleagues with configurable permissions.
**Story Goal** (US6): Enable educators to share schemes with groups for efficient team distribution.

**Independent Test Criteria** (US5):
- User can share scheme with another user
- View-only recipients cannot modify
- Editable recipients can modify
- Copy recipients get independent copy
- Revocation takes effect immediately

**Independent Test Criteria** (US6):
- User can share scheme with group
- All group members gain access
- New group members auto-gain access
- Removed members lose access

**Acceptance Criteria** (from spec):
- Grant/revoke access (FR-012, FR-013, FR-017)
- Enforce permissions (FR-019)
- Display shared schemes (FR-016)
- Notify recipients (FR-018)
- Track modifications (FR-020)

---

## Phase 7 Tasks

### Tests (TDD - Write First)

- [ ] T099 [P] [US5] Write unit test: tests/unit/test_permission_checker.py - test has_permission() for owner (always true)
- [ ] T100 [P] [US5] Write unit test: tests/unit/test_permission_checker.py - test has_permission() for VIEW_ONLY recipient
- [ ] T101 [P] [US5] Write unit test: tests/unit/test_permission_checker.py - test has_permission() for EDITABLE recipient
- [ ] T102 [P] [US5] Write unit test: tests/unit/test_permission_checker.py - test has_permission() for COPY recipient
- [ ] T103 [P] [US5] Write unit test: tests/unit/test_permission_checker.py - test revoked access denied (revoked_at not null)
- [ ] T104 [P] [US5] Write unit test: tests/unit/test_permission_checker.py - test group membership evaluated correctly
- [ ] T105 [P] [US5] Write integration test: tests/integration/test_sharing_flow.py - test POST /schemes/{id}/share with user grants access
- [ ] T106 [P] [US5] Write integration test: tests/integration/test_sharing_flow.py - test POST /schemes/{id}/share with group grants access to all members
- [ ] T107 [P] [US5] Write integration test: tests/integration/test_sharing_flow.py - test DELETE /schemes/{id}/share/{share_id}/revoke removes access
- [ ] T108 [P] [US5] Write integration test: tests/integration/test_sharing_flow.py - test GET /schemes/shared-with-me returns schemes shared with user
- [ ] T109 [P] [US5] Write integration test: tests/integration/test_sharing_flow.py - test permission enforcement: VIEW_ONLY cannot modify (403)
- [ ] T110 [P] [US5] Write integration test: tests/integration/test_sharing_flow.py - test permission enforcement: EDITABLE can modify
- [ ] T111 [US5] Write integration test: tests/integration/test_sharing_flow.py - test permission enforcement: COPY creates independent copy
- [ ] T112 [P] [US6] Write integration test: tests/integration/test_sharing_flow.py - test group member auto-gets access when added to group
- [ ] T113 [P] [US6] Write integration test: tests/integration/test_sharing_flow.py - test group member loses access when removed from group (unless individually shared)
- [ ] T114 [P] [US6] Write integration test: tests/integration/test_sharing_flow.py - test 50+ recipients in single share action

### Implementation

- [ ] T115 [P] [US5] Create services/permission_checker.py: Implement check_scheme_permission()
  - Parameters: user_id, scheme_id, required_permission
  - Check if user is owner (direct access)
  - Query SchemeShare for matching record (user_id OR group_id)
  - Verify revoked_at is NULL (not revoked)
  - Compare permission level (permission check)
  - Return bool (True if permitted)
  - Example: check_scheme_permission(user_id, scheme_id, "EDITABLE") → can modify if owner or EDITABLE/COPY share
- [ ] T116 [P] [US5] Create services/permission_checker.py: Implement helper functions
  - can_view_scheme(user_id, scheme_id) → checks VIEW_ONLY or higher
  - can_edit_scheme(user_id, scheme_id) → checks EDITABLE only (not COPY, not VIEW_ONLY)
  - can_copy_scheme(user_id, scheme_id) → checks COPY only
  - Each returns bool
- [ ] T117 [US5] Create services/permission_checker.py: Implement get_user_accessible_schemes()
  - Parameters: user_id
  - Query: schemes where owner_id = user_id OR user has SchemeShare with revoked_at IS NULL
  - Include group membership in query (join through user_groups)
  - Return list of (MarkingScheme, permission_level) tuples
  - Order by shared_at DESC (recently shared first)
- [ ] T118 [P] [US5] Create routes/scheme_sharing.py: Implement POST /schemes/{id}/share endpoint
  - Route: POST /schemes/{id}/share
  - Verify user is owner (403 if not)
  - Accept array of recipients: [{type: "user", user_id: "..."}, {type: "group", group_id: "..."}]
  - Accept permission: VIEW_ONLY, EDITABLE, or COPY
  - For each recipient:
    1. Create SchemeShare record
    2. Set shared_by_id = current user
    3. Set shared_at = now()
    4. Verify recipient exists (404 if not)
  - Return 200 with shares_created count
  - Emit notification events (FR-018) - placeholder for messaging system
  - Handle errors: not owner (403), recipient not found (404), invalid permission (422)
- [ ] T119 [P] [US5] Create routes/scheme_sharing.py: Implement DELETE /schemes/{id}/share/{share_id}/revoke endpoint
  - Route: DELETE /schemes/{id}/share/{share_id}/revoke
  - Verify user is owner (403 if not)
  - Retrieve SchemeShare record
  - Set revoked_at = now()
  - Set revoked_by_id = current user
  - Save to database
  - Return 204 No Content
  - Handle errors: not owner (403), share not found (404)
- [ ] T120 [P] [US5] Create routes/scheme_sharing.py: Implement GET /schemes/{id}/shares endpoint
  - Route: GET /schemes/{id}/shares
  - Verify user is owner (403 if not)
  - Query all SchemeShare records for scheme_id
  - Include all shares (both active and revoked, or filter by revoked_at)
  - Return array of: {share_id, user_id/group_id, permission, shared_at, revoked_at, shared_by}
  - Handle errors: not owner (403), scheme not found (404)
- [ ] T121 [P] [US5] Create routes/scheme_sharing.py: Implement GET /schemes/shared-with-me endpoint
  - Route: GET /schemes/shared-with-me
  - Use permission_checker.get_user_accessible_schemes()
  - Filter by current user
  - Optional query param: permission_filter (VIEW_ONLY, EDITABLE, COPY)
  - Return array of: {scheme_id, name, owner, permission, shared_at, shared_by, criteria_count}
  - Handle errors: none (user may have no schemes shared)
- [ ] T122 [P] [US5] Create middleware/permission_enforcement.py: Implement permission decorator for routes
  - @require_scheme_permission(required_permission)
  - Before route execution, check: check_scheme_permission()
  - Return 403 if permission denied
  - Allows clean route definitions
- [ ] T123 [US5] Update route handlers for existing scheme operations (GET /schemes/{id}, PUT /schemes/{id}) to enforce permissions:
  - GET /schemes/{id}: Require VIEW_ONLY or higher
  - PUT /schemes/{id}: Require EDITABLE or is_owner
  - Apply @require_scheme_permission decorator
  - Test all existing tests still pass
- [ ] T124 [P] [US5] Create routes/scheme_sharing.py: Implement notification system stub (FR-018)
  - Function: notify_scheme_shared()
  - Parameters: recipient_id, scheme_name, shared_by_email, permission
  - Create Notification record or queue email (depends on existing system)
  - Log for audit trail
  - Placeholder for actual messaging implementation
- [ ] T125 [P] [US5] Create routes/scheme_sharing.py: Implement audit logging for sharing operations
  - Log all share grants: who shared, with whom, when, permission level
  - Log all revocations: who revoked, when
  - Store in DocumentUploadLog or similar audit table
  - Queries available for compliance/audit
- [ ] T126 [US6] Extend POST /schemes/{id}/share to handle group members
  - When sharing with group: query UserGroup.members
  - For each current member, ensure access (may already exist)
  - No duplicate SchemeShare records
  - Notify all current members (FR-018)
- [ ] T127 [P] [US6] Create services/group_sync.py: Implement group membership change hooks
  - Hook on: user_added_to_group(user_id, group_id)
  - Action: Grant access to all schemes shared with that group
  - Hook on: user_removed_from_group(user_id, group_id)
  - Action: Revoke access to schemes (unless individually shared)
  - These hooks integrate with user management system
  - Placeholder if group system not yet integrated
- [ ] T128 [P] [US5] Create tests/unit/test_permission_checker.py: Run tests verifying permission checks work
- [ ] T129 [P] [US5] Create tests/integration/test_sharing_flow.py: Run tests verifying sharing workflow end-to-end
- [ ] T130 [US5] Add routes/scheme_sharing.py blueprint registration to app.py

---

# Phase 8: Testing, Documentation & Polish

## Phase Goal
Achieve 80%+ test coverage, verify all acceptance criteria met, finalize documentation.

### Testing Tasks

- [ ] T131 [P] Run full test suite: pytest tests/ -v --cov --cov-report=html
- [ ] T132 [P] Verify coverage >= 80% for: services/scheme_serializer.py, services/scheme_deserializer.py, services/permission_checker.py, services/document_parser.py
- [ ] T133 [P] Verify coverage >= 80% for: routes/scheme_export.py, routes/scheme_document.py, routes/scheme_sharing.py
- [ ] T134 [P] Fix any failing tests (debug, update mocks, or adjust implementation)
- [ ] T135 Run database migration tests: verify all migrations apply and rollback cleanly
- [ ] T136 [P] Run linting: ruff check . (per project standards)
- [ ] T137 [P] Format code: black . (per project standards)
- [ ] T138 Manual acceptance testing:
  - Test US1 (export) end-to-end in UI
  - Test US2 (import) end-to-end in UI
  - Test US3 (document upload) end-to-end in UI with real documents
  - Test US4 (scheme reuse) end-to-end
  - Test US5/US6 (sharing) end-to-end with multiple users

### Documentation Tasks

- [ ] T139 Update README.md or FEATURES.md with:
  - Feature overview (save/load/share marking schemes)
  - User guide: how to export, import, upload documents, share
  - API documentation (reference contracts/openapi.yaml)
  - Configuration: LLM provider setup, file storage options
- [ ] T140 Add code comments/docstrings to all new functions (explain intent, parameters, return values)
- [ ] T141 Create MIGRATION_GUIDE.md documenting:
  - Database schema changes
  - How to apply migrations
  - How to rollback if needed
  - Any data migration steps

### Integration Tasks

- [ ] T142 Update app.py: Register all new blueprints (scheme_export, scheme_document, scheme_sharing)
- [ ] T143 [P] Update app.py: Add permission decorator to existing scheme routes (enforce sharing permissions)
- [ ] T144 Update conftest.py: Add fixtures for sharing tests (users, groups, shared schemes)
- [ ] T145 Update models.py: Run final verification that all relationships work (test via pytest)
- [ ] T146 Verify Celery worker configuration: Document how to run workers for document processing
- [ ] T147 Create/update deployment documentation for:
  - Environment variables needed (LLM provider config)
  - Database migrations on deployment
  - Celery worker startup
  - Storage configuration

### Final Tasks

- [ ] T148 Create RELEASE_NOTES.md documenting:
  - New features (US1-US6)
  - Breaking changes (none expected)
  - Known limitations (e.g., document accuracy)
  - Performance characteristics
- [ ] T149 Commit all code to feature branch: git add -A && git commit -m "Feature 005: Marking schemes as files"
- [ ] T150 Create pull request from 005-marking-schema-as-file → main
- [ ] T151 Code review: Verify constitutional compliance (TDD, async-first, security, audit trails)
- [ ] T152 Merge to main after review approval

---

## Execution Strategy & Parallel Opportunities

### Phase Execution Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
Phase 3 (US1)      Phase 4 (US2)
    ↓  (depends)      ↓ (depends on US1)
    └─────────────────┘
           ↓
Phase 5 (US3)      Phase 6 (US4)
    ↓ (depends)      ↓ (depends on US1+US2)
    └──────────────┬──┘
                   ↓
Phase 7 (US5+US6)
    ↓
Phase 8 (Testing & Polish)
```

### Parallelization Within Phases

**Phase 2** (Foundational):
- T011, T012, T013: JSON schema + fixtures (parallel)
- T014, T015, T016, T017: Migrations (parallel creation, sequential execution)
- T018-T023: Models (can be implemented in parallel, test together)
- T025, T026: Services (parallel)

**Phase 3** (US1):
- T028-T035: Tests (all can be written in parallel)
- T036-T042: Implementation (can be parallelized in multiple developers: T036 vs. T038-T040)

**Phase 4** (US2):
- T043-T052: Tests (parallel)
- T053-T059: Implementation (T053 can be parallel with T056)

**Phase 5** (US3):
- T060-T074: Tests (parallel)
- T075-T091: Implementation (document extraction: T075, T076, T077 parallel; LLM integration: T079-T082; routes: T084-T087; can run multiple in parallel)

**Phase 6** (US4):
- T092-T095: Tests (parallel)
- T096-T098: Implementation (small scope, sequential)

**Phase 7** (US5+US6):
- T099-T114: Tests (parallel)
- T115-T130: Implementation (permission checker: T115-T117; sharing routes: T118-T125; group sync: T126-T127)

**Phase 8**:
- T131-T138: Testing (mostly parallel)
- T139-T147: Documentation (parallel)

### Recommended Team Distribution

**Single Developer**:
- Implement phases sequentially (1→2→3→4→5→6→7→8)
- Estimated: 4-5 weeks

**Two Developers**:
- Dev 1: Phases 1-4 (setup, foundational, US1, US2) = 2 weeks
- Dev 2: Phase 2 (foundational) in parallel with Dev 1
- Then Dev 1+2: Phase 5 (US3) together = 1 week
- Then Dev 1: Phase 6 (US4) = 3-4 days
- Then Dev 1+2: Phase 7 (US5+US6) = 1 week
- Then Dev 1+2: Phase 8 (testing) = 3-4 days

**Three Developers**:
- Dev 1: Setup + US1/US2 serialization
- Dev 2: US3 document processing + tests
- Dev 3: US5/US6 sharing system + tests
- Converge for Phase 8

---

## Success Criteria Summary

✅ All 6 user stories implemented with independent test criteria
✅ 80%+ code coverage with unit, integration, and contract tests
✅ JSON export/import round-trip verified (SC-001)
✅ Document conversion accuracy 85%+ (SC-002)
✅ Import success rate 95%+ (SC-005)
✅ Document processing <30 seconds (SC-004)
✅ Sharing visible within 5 seconds (SC-007)
✅ Permission enforcement verified (SC-009)
✅ Revocation takes effect immediately (SC-010)
✅ All constitutional requirements met (TDD, async, security, audit trails)
✅ Comprehensive documentation and migration guide

---

## Notes

- **Constitutional Compliance**: All tasks follow TDD (tests before implementation), async-first (Celery for document processing), and audit trails (DocumentUploadLog, SchemeShare tracking)
- **Dependency Resolution**: Tasks organized to ensure blocking dependencies complete first (US1→US2→US3+US4→US5+US6)
- **Test Coverage**: Every feature has unit, integration, and where applicable contract tests
- **Estimated Effort**: 52 tasks across 8 phases, ~4-5 weeks for single developer
- **MVP Scope**: US1+US2 (5-7 days) provides complete export/import for all versions
- **Extended Scope**: US3-US6 (additional 2-3 weeks) adds advanced document conversion and web-version sharing
