# Implementation Plan: OCR and Image Content Evaluation for Grading

**Branch**: `001-ocr-image-grading` | **Date**: 2025-11-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ocr-image-grading/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable automated text extraction and quality assessment of student image submissions (screenshots, diagrams) through OCR and Vision Language Model integration. The system will asynchronously process uploaded images to extract text content, assess image quality, and enable content-based validation against marking criteria. This supports graders in efficiently evaluating screenshot submissions while maintaining the existing async-first architecture and multi-provider AI abstraction layer.

## Technical Context

**Language/Version**: Python 3.13.7
**Primary Dependencies**: Flask 2.3.3, Flask-SQLAlchemy 3.0.5, Celery 5.3.4, Redis 5.0.1, **NEEDS CLARIFICATION** (OCR library choice: Tesseract/Google Vision/AWS Textract/DeepSeek OCR), **NEEDS CLARIFICATION** (Image processing: Pillow/OpenCV), **NEEDS CLARIFICATION** (VLM integration approach)
**Storage**: PostgreSQL (production) / SQLite (development), File storage for uploaded images, **NEEDS CLARIFICATION** (Image file storage strategy: local filesystem vs S3/object storage)
**Testing**: pytest with existing test harness (tests/conftest.py)
**Target Platform**: Linux server (Docker containerized, systemd services)
**Project Type**: Single web application (Flask backend with templates, no separate frontend)
**Performance Goals**: 95% of images processed within 30 seconds (per SC-003), <5 second access to extracted text (per SC-001), Support 100 concurrent image processing requests (per SC-007)
**Constraints**: OCR processing must be async (Celery tasks), Image files up to 50MB (per FR-017), 90%+ OCR confidence for clear images (per SC-002)
**Scale/Scope**: Multi-student submissions with 10+ images per assignment, Batch processing capability, Image quality assessment for all submissions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Quality Over Speed**:
- [x] Feature prioritizes accuracy and reliability over rapid delivery (SC-002: 90%+ OCR confidence requirement, quality assessment flags poor submissions)
- [x] Robust validation and error handling planned for all critical paths (FR-006: graceful failure handling, FR-013: processing state indicators, edge cases documented)

**Test-First Development (NON-NEGOTIABLE)**:
- [x] TDD workflow planned: tests → fail → implement → pass
- [x] Test coverage target ≥80% for new features (matching existing test-heavy codebase)
- [x] Unit, integration, and contract tests identified:
  - Unit: OCR text extraction, image quality assessment algorithms, confidence scoring
  - Integration: Celery task processing, database persistence, file storage/retrieval
  - Contract: OCR service API integration, VLM provider abstraction

**AI Provider Agnostic**:
- [x] No tight coupling to specific AI provider implementation (OCR abstraction layer planned, following existing utils/llm_providers.py pattern)
- [x] Common abstraction layer used for AI interactions (Will extend existing provider abstraction to support OCR/VLM services)

**Async-First Job Processing**:
- [x] All grading operations execute through Celery task queues (FR-005: async image processing, follows existing tasks.py pattern)
- [x] No synchronous grading in request handlers (Image processing triggered via Celery, results polled/retrieved asynchronously)

**Data Integrity & Audit Trail**:
- [x] Complete audit trails planned (Image submission metadata, OCR processing timestamps, confidence scores, quality metrics, retry attempts per FR-006)
- [x] All state transitions logged for reproducibility (Processing states: queued → processing → completed/failed, matching existing GradingJob pattern)

**Security Requirements**:
- [x] File upload validation planned (FR-001: image format validation PNG/JPG/JPEG/GIF/BMP/WebP, FR-017: 50MB size limit, content validation)
- [x] API keys stored in environment variables only (OCR service API keys in .env, following existing pattern)
- [x] Parameterized database queries (Using Flask-SQLAlchemy ORM, existing pattern)

**Database Consistency**:
- [x] Migration scripts planned for all schema changes (New tables: ImageSubmission, ExtractedContent, QualityAssessment; migrations via Alembic)
- [x] Reversible migrations for rollback capability (Standard Alembic upgrade/downgrade pattern)

### Post-Design Re-Evaluation (Phase 1 Complete)

**Date**: 2025-11-14

All constitution principles remain satisfied after completing Phase 1 design (research.md, data-model.md, API contracts, quickstart.md):

✅ **Quality Over Speed**: Quality assessment algorithms defined (Laplacian variance blur detection, edge-based completeness), robust validation pipelines designed (multi-layer file validation, OCR confidence scoring)

✅ **Test-First Development**: TDD workflow documented in quickstart.md with test examples (unit, integration, contract tests), test fixtures defined, coverage targets maintained (≥80%)

✅ **AI Provider Agnostic**: OCR abstraction layer designed following existing utils/llm_providers.py pattern, VLM integration extends existing provider abstraction, supports multiple OCR providers (Azure Vision, Tesseract, Google Vision)

✅ **Async-First Job Processing**: All image processing executes through Celery tasks (process_image_ocr, assess_image_quality), no synchronous processing in request handlers, async architecture maintained

✅ **Data Integrity & Audit Trail**: Complete audit trails in database schema (processing timestamps, confidence scores, quality metrics, retry attempts), all state transitions logged (uploaded → queued → processing → completed/failed)

✅ **Security Requirements**: Multi-layer validation pipeline designed (extension, size, MIME type, PIL verification), file upload validation documented, API keys in environment variables, UUID-based file naming prevents directory traversal

✅ **Database Consistency**: 5 reversible migrations planned (ImageSubmission, ExtractedContent, ImageQualityMetrics, ImageValidationCriteria, ImageValidationResult), Alembic upgrade/downgrade pattern, referential integrity constraints defined

**Conclusion**: No constitution violations introduced during design phase. All principles satisfied. Ready to proceed to Phase 2 (tasks.md generation via /speckit.tasks command).

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
# Flask application (single project at root level)
/
├── models.py                 # SQLAlchemy models (EXTEND: ImageSubmission, ExtractedContent, QualityAssessment)
├── tasks.py                  # Celery tasks (ADD: process_image_ocr, assess_image_quality)
├── app.py                    # Flask application factory
├── routes/
│   ├── api.py               # API endpoints (ADD: image upload, OCR results retrieval)
│   ├── main.py              # UI routes (ADD: image viewer, extracted text display)
│   └── upload.py            # File upload handling (EXTEND: image validation)
├── utils/
│   ├── file_utils.py        # File operations (EXTEND: image file validation)
│   ├── llm_providers.py     # AI provider abstraction (EXTEND: OCR/VLM provider support)
│   ├── text_extraction.py   # Text extraction utilities (EXTEND: OCR integration)
│   └── image_processing.py  # NEW: Image quality assessment, OCR text extraction
├── templates/
│   └── [HTML templates]     # (EXTEND: image viewer UI, OCR results display)
└── tests/
    ├── test_models.py        # Model tests (ADD: ImageSubmission, ExtractedContent tests)
    ├── test_tasks.py         # Task tests (ADD: OCR processing task tests)
    ├── test_routes.py        # Route tests (ADD: image upload, retrieval endpoint tests)
    └── test_utils.py         # Utility tests (ADD: image processing, quality assessment tests)
```

**Structure Decision**: Extends existing Flask application structure at repository root. New functionality integrates into existing patterns:
- Models extend `models.py` (following existing GradingJob, Submission patterns)
- Celery tasks added to `tasks.py` (following existing async processing pattern)
- Routes extend `routes/` modules (API endpoints in `api.py`, UI in `main.py`)
- Utilities extend `utils/` (new `image_processing.py` for OCR/quality logic)
- Tests extend existing `tests/` structure (matching current comprehensive test coverage)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
