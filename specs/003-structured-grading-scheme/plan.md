# Implementation Plan: Structured Grading Scheme with Multi-Point Evaluation

**Branch**: `003-structured-grading-scheme` | **Date**: 2025-11-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-structured-grading-scheme/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature adds support for creating reusable grading schemes with hierarchical structure (scheme → questions/categories → criteria) where each criterion has specific point allocations. Instructors can apply these schemes to grade student submissions, assigning points and feedback per criterion, with automatic calculation of totals. Results can be exported in structured formats (CSV, JSON) preserving the hierarchy and including complete metadata for integration with learning management systems.

## Technical Context

**Language/Version**: Python 3.13.7
**Primary Dependencies**: Flask 2.3.3, Flask-SQLAlchemy 3.0.5, Celery 5.3.4, Redis 5.0.1
**Storage**: PostgreSQL (production), SQLite (development) via Flask-SQLAlchemy ORM
**Testing**: pytest with Flask test client, coverage target ≥80%
**Target Platform**: Linux server (Flask web application)
**Project Type**: Single project (Flask backend with templates)
**Performance Goals**:
- Create/modify schemes with 50+ criteria in <3 seconds
- Export 100+ students × 50+ criteria in <30 seconds
- Grade 20+ criteria with feedback in <10 minutes (user workflow time)
**Constraints**:
- Must integrate with existing Submission/GradingJob models
- Point calculations accurate to 2 decimal places
- Export files maintain 100% data fidelity
**Scale/Scope**:
- Support schemes with 50+ questions/categories
- Handle 1000+ students per export
- Maintain version history for scheme modifications

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Quality Over Speed**:
- [x] Feature prioritizes accuracy and reliability over rapid delivery - Point calculations use Decimal type for precision, validation prevents data inconsistencies
- [x] Robust validation and error handling planned for all critical paths - Scheme validation, point range checks, export error handling

**Test-First Development (NON-NEGOTIABLE)**:
- [x] TDD workflow planned: tests → fail → implement → pass - Will write tests for models, services, routes before implementation
- [x] Test coverage target ≥80% for new features - Target 85% for grading scheme components
- [x] Unit, integration, and contract tests identified - Unit (models, calculations), Integration (API routes, database), Contract (export format validation)

**AI Provider Agnostic**:
- [x] No tight coupling to specific AI provider implementation - This feature is data management only, no AI provider interaction
- [x] Common abstraction layer used for AI interactions - N/A for this feature

**Async-First Job Processing**:
- [x] All grading operations execute through Celery task queues - Manual grading is synchronous user interaction; bulk exports will use Celery if >100 students
- [x] No synchronous grading in request handlers - Individual grading is user-driven form submission; validation and calculation are fast (<100ms)

**Data Integrity & Audit Trail**:
- [x] Complete audit trails planned (submissions, criteria, models, timestamps, retries) - All entities have created_at/updated_at, scheme versioning tracks modifications
- [x] All state transitions logged for reproducibility - Grading scheme versions capture state at time of submission grading

**Security Requirements**:
- [x] File upload validation planned (type, size, content) - N/A for this feature (no file uploads in grading schemes)
- [x] API keys stored in environment variables only - N/A for this feature
- [x] Parameterized database queries (no string concatenation) - Using SQLAlchemy ORM for all database access

**Database Consistency**:
- [x] Migration scripts planned for all schema changes - Flask-Migrate for all new tables and relationships
- [x] Reversible migrations for rollback capability - All migrations will have downgrade() functions

## Project Structure

### Documentation (this feature)

```text
specs/003-structured-grading-scheme/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (decisions on versioning, export formats, precision)
├── data-model.md        # Phase 1 output (GradingScheme, SchemeQuestion, SchemeCriterion entities)
├── quickstart.md        # Phase 1 output (developer guide for grading scheme implementation)
├── contracts/           # Phase 1 output (API contracts for CRUD + export endpoints)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Single project structure (Flask application)
models.py                      # Add: GradingScheme, SchemeQuestion, SchemeCriterion, GradedSubmission, CriterionEvaluation
├── (existing: SavedPrompt, SavedMarkingScheme, GradingJob, Submission, JobBatch)

routes/
├── schemes.py                 # NEW: CRUD operations for grading schemes
├── grading.py                 # NEW: Apply schemes to submissions, save evaluations
├── export.py                  # NEW: Export grading results (CSV, JSON)
└── (existing: main.py, upload.py, api.py, batches.py, templates.py)

utils/
├── scheme_calculator.py       # NEW: Point calculation utilities (totals, aggregations)
├── scheme_validator.py        # NEW: Validation logic (point ranges, hierarchy integrity)
├── export_formatters.py       # NEW: CSV and JSON export formatting
└── (existing: extraction utilities, OCR handlers)

templates/
├── schemes/
│   ├── list.html             # NEW: List all grading schemes
│   ├── create.html           # NEW: Create/edit grading scheme
│   ├── view.html             # NEW: View scheme details
│   └── grade.html            # NEW: Apply scheme to submission
└── (existing: upload forms, job status, batch management)

tests/
├── unit/
│   ├── test_scheme_models.py        # NEW: GradingScheme, SchemeQuestion, SchemeCriterion tests
│   ├── test_scheme_calculator.py    # NEW: Point calculation tests (totals, precision)
│   ├── test_scheme_validator.py     # NEW: Validation logic tests
│   └── test_export_formatters.py    # NEW: CSV/JSON export formatting tests
├── integration/
│   ├── test_scheme_routes.py        # NEW: CRUD API integration tests
│   ├── test_grading_routes.py       # NEW: Apply scheme, save evaluations integration tests
│   └── test_export_routes.py        # NEW: Export endpoint integration tests
└── contract/
    ├── test_csv_export_contract.py  # NEW: CSV format validation (column headers, data types)
    └── test_json_export_contract.py # NEW: JSON schema validation (hierarchy preservation)
```

**Structure Decision**: Single project structure following existing Flask application pattern. New models extend existing models.py, routes follow blueprint pattern in routes/, utilities in utils/, templates in templates/schemes/. This maintains consistency with existing codebase (001-ocr-image-grading feature) and leverages established patterns (Flask-SQLAlchemy, Celery integration, blueprint routing).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations requiring justification.

**Note on Async-First**: Manual grading workflow is inherently synchronous (instructor fills form, submits evaluation). Individual operations (save evaluation, calculate points) complete in <100ms. Bulk exports for >100 students will use Celery background tasks to prevent request timeouts, following async-first principle where operation duration warrants it.

---

## Current Implementation Status

**Last Updated**: 2025-11-15
**Overall Completion**: 30%

### Completed Components ✅

**Phase 1: Setup** (100% Complete)
- ✅ All directory structures created
- ✅ Blueprint files initialized

**Phase 2: Foundational** (100% Complete)
- ✅ Database migrations complete (GradingScheme, SchemeQuestion, SchemeCriterion, GradedSubmission, CriterionEvaluation)
- ✅ Point calculation utilities implemented (utils/scheme_calculator.py)
- ✅ Validation utilities implemented (utils/scheme_validator.py)
- ✅ All migrations tested and reversible

**Phase 3: User Story 1** (30% Complete)
- ✅ All backend models implemented and tested
- ✅ Model serialization (to_dict methods) complete
- ❌ **CRITICAL GAP**: routes/schemes.py is EMPTY (only blueprint definition, no endpoints)
- ❌ No frontend templates exist (templates/schemes/ directory missing)
- **Actual Status**: Models work, but unusable without APIs and UI

**Phase 4: User Story 2** (40% Complete)
- ✅ GradedSubmission and CriterionEvaluation models implemented
- ✅ All grading API endpoints functional (routes/grading.py)
- ✅ Point calculation and validation working
- ❌ No grading interface UI (templates/schemes/grade.html doesn't exist)
- ❌ No integration with job creation workflow
- **Actual Status**: Can save evaluations via API, but no user interface

**Phase 5: User Story 3** (50% Complete)
- ✅ Export API endpoint exists (routes/export.py)
- ❌ Export formatters incomplete
- ❌ No UI buttons to trigger export
- ❌ No statistics endpoint
- **Actual Status**: API works but inaccessible to users

**Phase 6: Polish** (100% Complete - for what exists)
- ✅ All existing code documented
- ✅ Tests passing for implemented components
- ✅ Linting and formatting complete
- **Note**: Polish was applied to completed components only

### Critical Gaps Requiring Immediate Attention ❌

**Gap 1: Scheme Management APIs (Blocks ALL Frontend Work)**

File: `routes/schemes.py` (Currently 6 lines - EMPTY)

Missing 13 essential endpoints:
```python
# Core CRUD
POST   /api/schemes              # Create scheme
GET    /api/schemes              # List all schemes
GET    /api/schemes/<id>         # Get scheme details
PUT    /api/schemes/<id>         # Update scheme
DELETE /api/schemes/<id>         # Soft delete

# Question Management
POST   /api/schemes/<id>/questions        # Add question
PUT    /api/schemes/questions/<id>        # Update question
DELETE /api/schemes/questions/<id>        # Delete question

# Criteria Management
POST   /api/schemes/questions/<id>/criteria  # Add criterion
PUT    /api/schemes/criteria/<id>            # Update criterion
DELETE /api/schemes/criteria/<id>            # Delete criterion

# Utilities
POST   /api/schemes/<id>/clone              # Clone scheme
GET    /api/schemes/<id>/statistics         # Get usage stats
```

**Impact**: Without these APIs, the frontend UI cannot function. This is the primary blocker.

**Gap 2: Frontend UI (0% Complete)**

Directory: `templates/schemes/` (MISSING)

Required components:
1. **Scheme Management Dashboard** (templates/schemes/index.html)
   - List all schemes
   - Create/Edit/Delete actions
   - Clone functionality
   - Statistics view

2. **Scheme Builder Form** (templates/schemes/builder.html)
   - Dynamic question/criterion editor
   - Real-time point validation
   - Drag-and-drop reordering
   - Save/Cancel actions

3. **Grading Interface** (templates/grading/grade_submission.html)
   - Load scheme structure dynamically
   - Input fields for each criterion
   - Feedback text areas
   - Save draft / Mark complete
   - Live score calculation

4. **Statistics Modal** (templates/schemes/statistics.html)
   - Per-question averages
   - Per-criterion analysis
   - Export options

5. **JavaScript Files** (static/js/)
   - scheme-builder.js (dynamic form management)
   - grading.js (grading interface logic)
   - validation.js (real-time point validation)

**Impact**: Users cannot interact with the system. Feature is completely unusable.

**Gap 3: Integration Points**

Missing integrations:
- Job creation form doesn't show grading scheme selection
- Submission list doesn't display grading status
- No bridge between SavedMarkingScheme (PDFs) and GradingScheme (structured data)

**Impact**: Fragmented user experience, feature feels disconnected from existing workflows.

### Recommended Implementation Path

**Phase 7: Complete Scheme Management APIs** (Priority: P0 - BLOCKING)
- Implement all 13 missing endpoints in routes/schemes.py
- Add comprehensive validation and error handling
- Write integration tests for all endpoints
- Estimated: 12-15 hours

**Phase 8: Build Frontend UI** (Priority: P1 - HIGH)
- Phase 8.1: Scheme management dashboard (4h)
- Phase 8.2: Scheme builder form (10-12h)
- Phase 8.3: Grading interface (8-10h)
- Phase 8.4: Statistics and export UI (2-3h)
- Phase 8.5: Integration with existing workflows (2h)
- Estimated: 25-30 hours

**Phase 9: End-to-End Testing and Polish** (Priority: P2 - MEDIUM)
- Browser compatibility testing
- Mobile responsiveness
- Performance testing with large datasets
- User acceptance testing
- Estimated: 4-6 hours

**Total Remaining Work**: 40-50 hours (5-7 days of focused development)

### Why Tasks Were Marked Complete Prematurely

The tasks.md file shows many tasks marked as [X] complete, but investigation reveals:

1. **T047-T053 (Scheme Routes)**: Marked complete, but routes/schemes.py is empty
2. **T057-T059 (Templates)**: Marked complete, but templates/schemes/ directory doesn't exist
3. **T093-T095 (Grading UI)**: Marked complete, but templates/grading/ has no grade.html

**Root Cause**: Tasks may have been auto-marked based on test passing, but the actual implementation files were never created or were created as placeholders only.

**Corrective Action**: Phase 7-9 tasks will be added to tasks.md with explicit verification steps to ensure real implementation, not just placeholder files.
