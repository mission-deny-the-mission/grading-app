# scheme_id Integration Documentation Index

## Overview
This directory contains comprehensive documentation for integrating `scheme_id` (GradingScheme) into the job creation workflow of the grading application.

---

## Documentation Files

### 1. **CODEBASE_MAP.md** (378 lines)
**Purpose**: Complete structural analysis of existing codebase

**Contents**:
- Full database model hierarchy and relationships
- Description of all route files and their functions
- Current job creation workflow (4-step process)
- Where scheme_id needs to be added (6 integration points)
- Template files overview
- Key parameters flow through the system
- Files to modify summary table
- Database query examples

**Who Should Read**:
- Anyone new to the codebase
- Architects planning the integration
- People designing the data flow

**Key Sections**:
- Database Models & Relationships (model hierarchy diagram)
- Routes Structure (detailed breakdown of all 8 route files)
- Current Job Creation Flow (step-by-step diagram)
- Where scheme_id Should Be Added (6 specific integration points)

---

### 2. **SCHEME_INTEGRATION_GUIDE.md** (384 lines)
**Purpose**: Step-by-step guide for implementing the integration

**Contents**:
- Quick summary of what's done and what's missing
- File-by-file integration checklist with specific line numbers
- Code patterns and examples
- JavaScript functions to add
- Data inheritance patterns
- Query parameter handling
- Testing considerations
- Migration and backward compatibility notes
- UI/UX workflows after integration
- API endpoints summary
- Priority-ordered files summary

**Who Should Read**:
- Developers implementing the integration
- QA testing the implementation
- Anyone needing to understand the complete integration scope

**Key Sections**:
- File-by-File Integration Checklist (8 sections covering each file)
- Data Inheritance Pattern (batch → job → submission flow)
- Testing Considerations (unit and integration tests)
- UI/UX Workflows (3 different workflow scenarios)

---

### 3. **INTEGRATION_REFERENCE.md** (436 lines)
**Purpose**: Copy-paste code snippets for rapid implementation

**Contents**:
- Ready-to-use code changes for each file
- Exact line numbers and locations
- Complete code blocks with context
- HTML template snippets with Bootstrap styling
- JavaScript functions with error handling
- Import statement updates
- Testing commands with curl examples

**Who Should Read**:
- Developers actively coding the integration
- Anyone copy-pasting code snippets
- References during code review

**Key Sections**:
- Database Model Changes (with exact imports and relationships)
- Route Changes (complete code blocks for batches.py, upload.py, grading_ui.py)
- Template Changes (HTML snippets for bulk_upload.html, job_detail.html, batch_detail.html)
- Summary of Changes (quick reference table)
- Testing Commands (curl commands for verification)

---

## Quick Start Guide

### For Implementing the Integration:

1. **Understand the Current System** → Read: CODEBASE_MAP.md
   - Focus on: "Database Models & Relationships" and "Current Job Creation Flow"

2. **Learn What Needs to Change** → Read: SCHEME_INTEGRATION_GUIDE.md
   - Focus on: "File-by-File Integration Checklist" sections

3. **Implement the Code** → Use: INTEGRATION_REFERENCE.md
   - Use as copy-paste reference for each file

4. **Test the Implementation** → Reference: SCHEME_INTEGRATION_GUIDE.md
   - Section: "Testing Considerations"
   - Use: INTEGRATION_REFERENCE.md, Section: "Testing Commands"

---

## Integration Summary

### Files to Modify

| File | Type | Changes Required | Lines to Modify |
|------|------|------------------|-----------------|
| models.py | Model | Add scheme_id columns and relationships | ~2 locations |
| routes/batches.py | Route | Accept scheme_id in 2 functions | 2 constructors |
| routes/upload.py | Route | Accept scheme_id in 1 function | 1 location |
| routes/grading_ui.py | Route | Add fallback to job.scheme_id | 1 function |
| templates/bulk_upload.html | Template | Add scheme dropdown | After line 95 |
| templates/job_detail.html | Template | Add scheme card + JS function | After line 80 + script |
| templates/batch_detail.html | Template | Add scheme card | After overview |

**Total**: 7 files, ~12 code changes, 100% backward compatible

### Key Concepts

**scheme_id**: Foreign key linking Job/Batch to a GradingScheme
- Optional (nullable)
- Can be inherited from batch to job to submission
- Used to create GradedSubmission records for structured grading

**Data Flow**:
```
Job/Batch with scheme_id
    ↓
Submissions inherit scheme_id from job
    ↓
GradedSubmission created with scheme_id
    ↓
CriterionEvaluation records created for each criterion
```

---

## Route Changes Overview

### Modified Routes

1. **POST /create_batch**
   - Now accepts: `scheme_id` (optional)
   - Creates: JobBatch with scheme_id

2. **POST /create_job**
   - Now accepts: `scheme_id` (optional)
   - Creates: GradingJob with scheme_id

3. **POST /upload_bulk**
   - Now accepts: `scheme_id` in form data
   - Creates: GradingJob with scheme_id (if job_id not provided)

4. **GET /submissions/<id>/grade**
   - Now accepts: `scheme_id` query param (optional)
   - Falls back: To job.scheme_id if not provided

### Unchanged Routes

- `/api/grading/submissions` - Already supports scheme_id
- `/api/schemes/*` - Already implements scheme CRUD
- `/api/export/schemes/*` - Already exports GradedSubmission by scheme_id

---

## Data Model Changes

### GradingJob
```python
# Add to models.py (after batch_id field):
scheme_id = db.Column(db.String(36), db.ForeignKey("grading_schemes.id"), nullable=True)
scheme = db.relationship("GradingScheme", backref="jobs_using_scheme")
```

### JobBatch
```python
# Add to models.py (after saved_marking_scheme_id field):
scheme_id = db.Column(db.String(36), db.ForeignKey("grading_schemes.id"), nullable=True)
scheme = db.relationship("GradingScheme", backref="batches_using_scheme")
```

Both changes are **backward compatible** - existing records will have NULL scheme_id.

---

## Testing Strategy

### Unit Tests
- Test JobBatch creation with scheme_id
- Test GradingJob creation with scheme_id  
- Test bulk upload with scheme_id
- Test scheme_id inheritance from batch to job

### Integration Tests
- Create batch with scheme → create job → upload files → verify scheme_id flows
- Create job with scheme directly → verify scheme_id preserved through submission creation

### Manual Testing
1. Create a GradingScheme via /api/schemes
2. Create a job with scheme_id
3. Upload files
4. Verify job detail shows scheme information
5. Click "Apply Scheme" button
6. Verify GradedSubmission records created
7. Grade using the scheme interface

---

## Document Cross-References

### Understanding the Flow:
1. Start with CODEBASE_MAP.md: "Database Models & Relationships"
2. Then CODEBASE_MAP.md: "Current Job Creation Flow"
3. Then SCHEME_INTEGRATION_GUIDE.md: "Data Inheritance Pattern"

### Implementing Each File:
1. Check CODEBASE_MAP.md for current code location
2. Read SCHEME_INTEGRATION_GUIDE.md for what needs to change
3. Use INTEGRATION_REFERENCE.md for exact code snippets

### Testing the Implementation:
1. Follow SCHEME_INTEGRATION_GUIDE.md: "Testing Considerations"
2. Use curl commands from INTEGRATION_REFERENCE.md: "Testing Commands"

---

## Backward Compatibility

All changes are **100% backward compatible**:

- ✓ scheme_id is optional (nullable) in all locations
- ✓ Existing jobs/batches without scheme_id continue to work
- ✓ All endpoints accept but don't require scheme_id
- ✓ Grading still works without scheme_id (LLM-only mode)
- ✓ No database migration required

---

## Architecture Decisions

### Why scheme_id at Both Job and Batch Level?
- **Flexibility**: Can set at either level, or override per-job
- **Inheritance**: Jobs inherit from batch, inherited by submissions
- **Consistency**: Supports both batch-wide and job-specific grading schemes

### Why Not Require scheme_id?
- **Backward Compatibility**: Existing LLM-only workflow continues to work
- **Optional Grading**: Users can add structured grading after LLM processing
- **Gradual Migration**: No forced changes to existing workflows

### Query Parameter Fallback
- Query param `/submissions/123/grade?scheme_id=X` takes precedence
- Falls back to `job.scheme_id` if not provided
- Allows both permanent (model) and temporary (query param) links

---

## Performance Considerations

**No Performance Impact**:
- scheme_id is a simple FK column (no joins required for basic queries)
- Lazy loading of relationships (no forced eager loading)
- Existing indexes on GradingScheme still apply
- No schema migration costs

---

## Questions & Troubleshooting

### Q: Do I need to migrate the database?
**A**: No. scheme_id is nullable, so NULL values work fine for existing records.

### Q: What if a scheme is deleted after a job references it?
**A**: The FK remains but the relationship breaks. Handle gracefully in templates with null checks.

### Q: Can I change a job's scheme_id after creation?
**A**: Yes, it's editable. Already-created GradedSubmission records reference the old scheme version.

### Q: How does this interact with LLM-based grading?
**A**: No interaction. Separate systems: LLM grades submissions, scheme evaluates the same submissions.

---

## Next Steps After Integration

1. **Immediate**: Implement changes per INTEGRATION_REFERENCE.md
2. **Testing**: Follow testing strategy above
3. **Future Enhancements**:
   - Bulk apply scheme to multiple submissions
   - Template inheritance of scheme settings
   - Grade comparison (LLM vs. scheme-based)
   - Analytics on scheme usage and grades

---

## Document Statistics

| Document | Lines | Purpose |
|----------|-------|---------|
| CODEBASE_MAP.md | 378 | Complete codebase analysis |
| SCHEME_INTEGRATION_GUIDE.md | 384 | Step-by-step implementation guide |
| INTEGRATION_REFERENCE.md | 436 | Copy-paste code snippets |
| **Total** | **1,198** | **Complete integration documentation** |

---

## Version Information

- **Grading App**: 003-structured-grading-scheme branch
- **Framework**: Flask 2.3.3
- **Database**: SQLAlchemy ORM
- **Python**: 3.13.7
- **Last Updated**: 2025-11-15

---

For questions or issues, refer to the specific document sections listed above.
