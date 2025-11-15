# Research: Structured Grading Scheme with Multi-Point Evaluation

**Feature**: 003-structured-grading-scheme
**Date**: 2025-11-15
**Phase**: Phase 0 - Research & Technical Decisions

## Research Areas

### 1. Scheme Versioning Strategy

**Decision**: Immutable scheme versions with snapshot-on-use pattern

**Rationale**:
- When a grading scheme is applied to submissions, capture a snapshot of the scheme structure at that moment
- If instructor modifies the scheme later, existing graded submissions remain associated with their original version
- This prevents retroactive changes from invalidating historical grading data
- Similar to SavedMarkingScheme pattern already in codebase

**Implementation Approach**:
- Store `version_number` (integer, auto-incrementing) on GradingScheme
- When scheme is modified, increment version_number
- GradedSubmission references specific scheme_id + version_number
- Optionally maintain scheme_snapshot JSON field for complete historical record

**Alternatives Considered**:
- **Full audit table**: Create separate GradingSchemeVersion table for each version
  - Rejected: Adds schema complexity, most schemes won't have many versions
- **No versioning**: Allow scheme modifications to affect all submissions
  - Rejected: Violates data integrity principle, historical grades lose context
- **Copy-on-write**: Deep copy entire scheme structure for each submission
  - Rejected: Storage inefficient for 1000+ students, version_number + snapshot JSON is sufficient

---

### 2. Point Calculation Precision

**Decision**: Use Python Decimal type for all point calculations, store as DECIMAL(10, 2) in database

**Rationale**:
- Floating-point arithmetic can introduce rounding errors (e.g., 0.1 + 0.2 ≠ 0.3)
- Grading requires exact precision to 2 decimal places (FR-011, SC-006)
- Financial-grade accuracy needed for fairness and auditability
- Python's `decimal.Decimal` provides arbitrary precision decimal arithmetic

**Implementation Approach**:
- Database columns: `db.Column(db.Numeric(10, 2))` for all point fields
- Python: Use `from decimal import Decimal` for all calculations
- Validation: Round user input to 2 decimal places on entry
- Display: Format as `{:.2f}` for consistency

**Alternatives Considered**:
- **Float with rounding**: Use float, round at display time
  - Rejected: Accumulation errors in multi-level totals, fails SC-006 accuracy requirement
- **Integer cents**: Store points as integers (multiply by 100)
  - Rejected: Less intuitive for developers, conversion overhead, Decimal is standard for this use case
- **String storage**: Store as VARCHAR and parse
  - Rejected: Loses database type safety, can't use SUM() aggregations

---

### 3. Export Format Specifications

**Decision**: Implement both flat CSV (denormalized) and hierarchical JSON formats

**CSV Format** (Flat, denormalized for spreadsheet compatibility):
```csv
Student ID,Student Name,Scheme Name,Scheme Version,Question/Category,Criterion Name,Points Earned,Max Points,Feedback,Graded By,Graded At
12345,John Doe,Essay Rubric,1,Question 1,Argument Clarity,8.5,10,"Good thesis",instructor@email.com,2025-11-15T10:30:00Z
12345,John Doe,Essay Rubric,1,Question 1,Evidence Quality,7.0,10,"Needs more sources",instructor@email.com,2025-11-15T10:30:00Z
```

**JSON Format** (Hierarchical, preserves structure):
```json
{
  "export_metadata": {
    "generated_at": "2025-11-15T12:00:00Z",
    "scheme_name": "Essay Rubric",
    "scheme_version": 1,
    "total_students": 100
  },
  "submissions": [
    {
      "student_id": "12345",
      "student_name": "John Doe",
      "graded_by": "instructor@email.com",
      "graded_at": "2025-11-15T10:30:00Z",
      "total_points_earned": 75.5,
      "total_points_possible": 100,
      "questions": [
        {
          "title": "Question 1",
          "points_earned": 15.5,
          "points_possible": 20,
          "criteria": [
            {
              "name": "Argument Clarity",
              "points_earned": 8.5,
              "max_points": 10,
              "feedback": "Good thesis"
            }
          ]
        }
      ]
    }
  ]
}
```

**Rationale**:
- CSV: Optimized for import into Excel/Google Sheets, LMS bulk upload, statistical analysis tools
- JSON: Preserves hierarchy, better for programmatic access, API integration, detailed analysis
- Both formats meet FR-009, FR-010, FR-015 (metadata inclusion)

**Alternatives Considered**:
- **XML**: More verbose, less popular than JSON for modern integrations
- **Parquet**: Efficient but requires specialized tools, overkill for this use case
- **Nested CSV**: Multiple CSV files (one per level) - complex for users to manage

---

### 4. Concurrent Grading Handling

**Decision**: Optimistic locking with last-write-wins, warn on version conflict

**Rationale**:
- Edge case identified: Two instructors grading same submission simultaneously (spec edge cases)
- Most common scenario: Single instructor per submission
- Optimistic locking minimizes database locks, better performance
- For rare conflicts, show warning and allow instructor to review/reconcile

**Implementation Approach**:
- Add `evaluation_version` column to GradedSubmission (integer, auto-increment on update)
- When saving evaluation:
  1. Check if `evaluation_version` matches expected version from form
  2. If mismatch, return 409 Conflict with current state
  3. Allow instructor to choose: overwrite, merge, or review differences
- For concurrent scheme usage (not modification): No conflict, both use same version

**Alternatives Considered**:
- **Pessimistic locking**: Lock submission row during grading
  - Rejected: Long-lived locks (10+ minutes) harm concurrent access, instructor may leave page open
- **No conflict detection**: Always overwrite
  - Rejected: Data loss risk if two instructors collaborate on same submission
- **Merge-on-write**: Automatically merge criterion evaluations
  - Rejected: Complex logic, unclear merge semantics for feedback text

---

### 5. Database Schema Performance Optimization

**Decision**: Add database indexes on foreign keys and frequently queried fields

**Rationale**:
- Scheme lookup by name: Common operation in UI
- Export queries: Filter by scheme_id, graded_at date range
- Hierarchical queries: Join scheme → questions → criteria → evaluations

**Indexes to Create**:
```python
# GradingScheme
Index('idx_scheme_name', 'name')

# SchemeQuestion
Index('idx_question_scheme_id', 'scheme_id')
Index('idx_question_order', 'scheme_id', 'display_order')

# SchemeCriterion
Index('idx_criterion_question_id', 'question_id')

# GradedSubmission
Index('idx_submission_scheme_version', 'scheme_id', 'version_number')
Index('idx_submission_graded_at', 'graded_at')

# CriterionEvaluation
Index('idx_evaluation_submission_id', 'submission_id')
Index('idx_evaluation_criterion_id', 'criterion_id')
```

**Alternatives Considered**:
- **No indexes**: Rely on database defaults
  - Rejected: Performance degrades with 1000+ students per export (SC-003)
- **Full-text search indexes**: For feedback text search
  - Rejected: Not in requirements, can add later if needed

---

### 6. Validation Strategy

**Decision**: Multi-layer validation (client-side hints, server-side enforcement, database constraints)

**Rationale**:
- FR-012: Prevent points exceeding maximum (strict requirement)
- Data integrity: Maintain hierarchical consistency

**Validation Layers**:
1. **Client-side** (HTML5 + JavaScript): Input hints, max value validation
   - Fast feedback, prevents accidental errors
   - Not security boundary (can be bypassed)

2. **Server-side** (Flask routes + utils/scheme_validator.py): Business logic validation
   - Points within range (0 to max_points)
   - Required fields present
   - Hierarchy integrity (question belongs to scheme, criterion belongs to question)
   - Return 400 Bad Request with specific error messages

3. **Database constraints**: Final enforcement
   - CHECK constraints: `points_awarded >= 0 AND points_awarded <= max_points`
   - NOT NULL constraints on required fields
   - Foreign key constraints for referential integrity

**Test Coverage**:
- Unit tests: Validator functions with boundary cases (0, max, max+1, negative)
- Integration tests: API endpoints with invalid data (400 responses)
- Database tests: Constraint violations raise IntegrityError

**Alternatives Considered**:
- **Server-only validation**: Skip client-side
  - Rejected: Poor UX, forces round-trip for simple errors
- **Database-only validation**: Rely on constraints
  - Rejected: Generic error messages, no field-specific feedback

---

### 7. Partial Grading Support

**Decision**: Allow saving partially completed grading, mark completion status explicitly

**Rationale**:
- FR-013: Support saving partially completed grading sessions
- Instructor may grade in multiple sittings (10 min per 20 criteria = multiple sessions)

**Implementation Approach**:
- Add `is_complete` boolean flag to GradedSubmission
- Default: `is_complete = False` when first created
- Instructor explicitly marks submission as complete when finished
- Partial submissions: Allow missing criterion evaluations (nullable relationship)
- Export: Include completion status, optionally filter to complete-only

**Validation Rules**:
- Can save with any subset of criteria graded (0 to 100%)
- Can mark complete only if all required criteria have evaluations (business rule)
- Can reopen completed submission for modifications (sets is_complete=False)

**Alternatives Considered**:
- **Auto-complete**: Mark complete when all criteria have evaluations
  - Rejected: Instructor may want to review before finalizing
- **Required completion**: Force all criteria before saving
  - Rejected: Violates FR-013, poor UX for long grading sessions
- **Draft/Published states**: Separate draft and published versions
  - Rejected: Over-engineered for this use case, is_complete flag sufficient

---

## Technology Stack Summary

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Models** | Flask-SQLAlchemy ORM | Consistent with existing codebase (SavedPrompt, GradingJob patterns) |
| **Decimal Math** | Python `decimal.Decimal` | Financial-grade precision required (SC-006) |
| **Versioning** | Integer version_number + JSON snapshot | Simple, efficient, sufficient for most use cases |
| **Export** | CSV (csv module), JSON (json module) | Standard library, no additional dependencies |
| **Validation** | Custom validators + DB constraints | Multi-layer defense, clear error messages |
| **Concurrency** | Optimistic locking (version field) | Performance over pessimistic locks for rare conflicts |
| **Testing** | pytest + Flask test client | Existing test infrastructure (README_TESTING.md) |
| **Async Export** | Celery (for >100 students) | Existing Celery infrastructure (tasks.py) |

---

## Open Questions Resolved

1. **Q: Should schemes be soft-deleted or hard-deleted?**
   - **A**: Soft-delete (add `is_deleted` flag). Used schemes must remain available for historical grading data integrity.

2. **Q: How to handle scheme modification after grading?**
   - **A**: Version snapshot pattern (see decision #1). Historical data remains valid.

3. **Q: Maximum number of criteria per question?**
   - **A**: No hard limit in code. Database can handle 1000s. UI pagination if >50 criteria per question.

4. **Q: Should feedback be required or optional?**
   - **A**: Optional (nullable column). Instructor may provide points-only grading for some criteria.

5. **Q: Support for weighted criteria (e.g., 30% of total)?**
   - **A**: Not in initial version. Point allocations achieve same goal (assign 30 points out of 100 total).

---

## Next Steps (Phase 1)

- Generate data-model.md with complete entity definitions
- Create API contracts in contracts/ directory (OpenAPI spec)
- Write quickstart.md for developer onboarding
- Update CLAUDE.md with new technologies (none new, using existing stack)
