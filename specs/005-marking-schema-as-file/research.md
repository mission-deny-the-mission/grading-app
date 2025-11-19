# Phase 0: Research & Findings

**Feature**: 005-marking-schema-as-file | **Date**: 2025-11-17
**Objective**: Resolve unknowns, evaluate technologies, document best practices

## Summary

No NEEDS CLARIFICATION markers were present in spec or technical context. Research focused on validating technical approach choices and documenting best practices for key integration points:
1. JSON schema design for marking schemes (serialization format)
2. Document parsing strategy (PDF/DOCX extraction)
3. LLM integration pattern for document analysis
4. Permission model for sharing (based on Flask-SQLAlchemy)
5. Celery async task configuration for document processing

All decisions align with existing project architecture and constitution principles.

---

## Decision 1: JSON Schema for Marking Scheme Export/Import

**Decision**: Use JSON as standard export format with consistent schema validation

**Rationale**:
- Already in requirements (FR-001, FR-002)
- Project uses JSON extensively (Flask APIs return JSON)
- Existing Python ecosystem: json module built-in, json-schema library for validation
- Human-readable format enables manual editing/inspection
- Web version naturally returns/accepts JSON from Flask routes
- Integrates seamlessly with existing Flask blueprints

**Alternatives Considered**:
1. **CSV**: Rejected - insufficient structure for hierarchical criteria/descriptors; difficult to preserve weightings and point values
2. **YAML**: Rejected - less standard in Python web context, parser complexity, schema validation less established
3. **XML**: Rejected - verbose, unnecessary complexity for this domain

**Implementation Details**:
- Schema: Top-level object with `version`, `metadata`, `criteria` array, `settings`
- Validation: Use jsonschema library to validate imports against published schema
- Backward compatibility: Schema versioning approach for future expansions

---

## Decision 2: Document Parsing Strategy

**Decision**: Use existing libraries for format extraction (PyPDF2, python-docx, Pillow), delegate interpretation to LLM

**Rationale**:
- Requirements (FR-004, FR-010): Support PDF, DOCX, images
- PyPDF2 and python-docx already in requirements.txt
- Pillow already present (for image grading)
- LLM-based interpretation (FR-005) is more reliable than regex/heuristics for rubric parsing
- Separates document extraction (technical) from rubric interpretation (semantic)
- Existing LLM infrastructure from 002-api-provider-security handles provider agnosticity

**Alternatives Considered**:
1. **Rule-based parsing**: Rejected - rubric structures too varied, heuristic-based approach would achieve 60-70% accuracy, LLM achieves 85%+ (SC-002)
2. **OCR for all formats**: Rejected - unnecessary for DOCX (native extraction), slower than native parsers
3. **Third-party API (e.g., AWS Textract)**: Rejected - creates external dependency, LLM analysis required anyway

**Implementation Details**:
- Document extraction logic:
  - PDF: PyPDF2.PdfReader → extract text from all pages
  - DOCX: python-docx → extract paragraphs, tables
  - Images: Pillow identify + OCR (could use existing image grading OCR infrastructure from 001-ocr-image-grading)
- Combined extracted text/structure passed to LLM (async)
- LLM prompt: "Parse this rubric document and extract marking criteria, performance levels, and descriptions"

---

## Decision 3: LLM Integration Pattern for Document Analysis

**Decision**: Implement as Celery async task using existing provider abstraction from 002-api-provider-security

**Rationale**:
- Constitution requirement (Async-First Job Processing): document processing cannot be synchronous in request handler
- Document processing may take 10-30 seconds (SC-004: <30s for <10MB)
- Existing LLMProvider abstraction pattern already supports Claude, OpenAI, Google
- Avoids tight coupling to specific AI provider
- Celery infrastructure already exists in project (visible in requirements.txt, tasks.py)

**Alternatives Considered**:
1. **Synchronous HTTP call in request handler**: Rejected - violates constitution, poor UX (request timeout risk)
2. **Direct provider SDK calls**: Rejected - violates "AI Provider Agnostic" principle, creates maintenance burden
3. **Background job queue (non-Celery)**: Rejected - project already standardized on Celery

**Implementation Details**:
- New Celery task: `analyze_document_for_marking_scheme(file_path, document_type)`
- Task calls existing LLMProvider abstraction with domain-specific prompt
- Result stored in DocumentConversionResult model (temporary, referenced from UI polling)
- UI polls with exponential backoff until conversion complete or error returned
- Prompt template engineered to extract: criteria names, descriptor levels, descriptions, point values

---

## Decision 4: Sharing Permission Model

**Decision**: Role-based permission system with three levels: View-Only, Editable, Copy. Implement via SharePermission enum, SchemeShare join table.

**Rationale**:
- Requirements (FR-012, FR-013, FR-014): Support individual users, groups, configurable permissions
- Role-based access (View-Only, Editable, Copy) matches educator mental model
- Join table pattern standard in Flask-SQLAlchemy for many-to-many relationships
- Enum prevents invalid permission values
- Copy permission for recipients needing independent version (safer than editing shared version)
- Matches familiar patterns from Google Docs (view/edit), GitHub (read/write/admin)

**Alternatives Considered**:
1. **Fine-grained ACL (CRUD per component)**: Rejected - over-engineered, educators think in simple roles
2. **Shared vs. Owned (binary)**: Rejected - doesn't support view-only use case
3. **String-based permissions ("view", "edit")**: Rejected - enum type-safety better for constants

**Implementation Details**:
- SharePermission enum: `VIEW_ONLY`, `EDITABLE`, `COPY`
- SchemeShare model: scheme_id, user_id OR group_id, permission, shared_at, revoked_at
- Query pattern: WHERE scheme_id = ? AND (user_id = ? OR group_id IN (SELECT id FROM user_groups WHERE user_id = ?))
- Enforce in permission_checker service: check SchemeShare before allowing modifications (FR-019)

---

## Decision 5: Celery Configuration for Document Processing

**Decision**: Use existing Celery infrastructure with dedicated queue for document processing

**Rationale**:
- Celery already present in project (requirements.txt, tasks.py, likely workers running)
- Provides reliable task persistence, retry logic, failure tracking
- Enables parallel processing of multiple document conversions
- Constitution requirement: async-first, all external API calls have retry logic with exponential backoff

**Alternatives Considered**:
1. **Direct threading**: Rejected - not persistent across restarts, poor failure recovery
2. **Message queue (RabbitMQ separate)**: Rejected - Celery already chosen for project

**Implementation Details**:
- Queue name: `document_processing` (separate from default grading queue)
- Task name: `tasks.process_document_rubric`
- Task parameters: document_id, file_path, file_type
- Return: DocumentConversionResult or exception with retry
- Retry logic: exponential backoff (3 max retries), only for transient failures (API timeout, not parsing errors)
- Result stored with: conversion_status (pending/success/failed), llm_response, uncertainty_flags, created_at

---

## Decision 6: Database Models - New Tables & Relationships

**Decision**: Extend MarkingScheme with owner_id, add SchemeShare, DocumentUploadLog, optionally DocumentConversionResult

**Rationale**:
- MarkingScheme owner_id: enables sharing and audit trail (which user created/owns)
- SchemeShare: encapsulates permission grants to users/groups, tracks revocation
- DocumentUploadLog: audit trail per FR-020 (who uploaded, when, file name, LLM provider/model used)
- DocumentConversionResult: transient storage for in-progress/completed conversions (web UI polling)

**Implementation**:
- MarkingScheme.owner_id: ForeignKey(User.id), nullable for backward compat with existing schemes
- SchemeShare:
  - scheme_id (FK)
  - user_id or group_id (ForeignKey, one is NULL)
  - permission (Enum)
  - shared_at, shared_by_id, revoked_at
- DocumentUploadLog:
  - document_id, user_id, file_name, file_size, mime_type, upload_at
  - llm_provider, llm_model, llm_status
  - error_message (if failed)
- DocumentConversionResult:
  - document_id (FK)
  - status (pending/processing/success/failed)
  - llm_response_raw
  - extracted_scheme (JSON - draft MarkingScheme)
  - uncertainty_flags (list of flagged items needing review)
  - created_at, completed_at

---

## Decision 7: File Storage for Exported Schemes

**Decision**: Store exported JSON files on local filesystem for desktop, in database/object store for web

**Rationale**:
- Desktop version (feature 004): uses local filesystem naturally
- Web version: database stores JSON as text field, or object store (S3/GCS) if storage concerns arise
- Simple approach: store scheme as JSON string in MarkingScheme.exported_json after export
- Users can download via Flask endpoint returning JSON with Content-Disposition: attachment

**Implementation**:
- Route: POST /schemes/{id}/export → generates JSON, stores on filesystem/DB, returns download link
- Route: GET /schemes/{id}/download → returns JSON file with appropriate headers
- For import: File upload endpoint accepts .json, validates schema, creates new MarkingScheme
- Optional: implement S3 storage for large deployments later

---

## Summary Table

| Decision | Choice | Key Technology | Dependencies |
|----------|--------|-----------------|---------------|
| Export/Import Format | JSON with schema validation | jsonschema library | None (built-in) |
| Document Extraction | PyPDF2, python-docx, Pillow (already in project) | Multi-format extractor | Existing libs |
| LLM Analysis | Async Celery task + existing LLMProvider abstraction | Celery, existing provider code | 002-api-provider-security |
| Permissions | Role-based (View/Edit/Copy) with SchemeShare table | SQLAlchemy ORM | Flask-SQLAlchemy |
| Document Processing Queue | Dedicated Celery queue with retry logic | Celery configuration | Existing infrastructure |
| Database Extensions | owner_id on MarkingScheme, new SchemeShare table, DocumentUploadLog | SQLAlchemy migrations | Flask-Migrate |
| File Storage | Filesystem (desktop) or DB field (web) | Native file I/O or PostgreSQL | Existing patterns |

All decisions align with:
- ✅ Constitution principles (TDD, async-first, AI provider agnostic, audit trails)
- ✅ Existing project architecture (Flask monolith, SQLAlchemy models, Celery)
- ✅ Technology choices already in requirements.txt
- ✅ Feature specifications and requirements
