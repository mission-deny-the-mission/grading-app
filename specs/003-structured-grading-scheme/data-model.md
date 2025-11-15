# Data Model: Structured Grading Scheme

**Feature**: 003-structured-grading-scheme
**Date**: 2025-11-15
**Phase**: Phase 1 - Design

## Entity Relationship Diagram

```
GradingScheme (1) ──< (M) SchemeQuestion (1) ──< (M) SchemeCriterion
     |                                                      |
     |                                                      |
     └──< (M) GradedSubmission (1) ──< (M) CriterionEvaluation ──┘
```

## Entities

### 1. GradingScheme

**Purpose**: Reusable template defining how papers/assignments should be evaluated

**Fields**:
```python
id: String(36) [PK] - UUID
created_at: DateTime - UTC timestamp of creation
updated_at: DateTime - UTC timestamp of last modification
version_number: Integer - Auto-incremented on each modification (starts at 1)
is_deleted: Boolean - Soft delete flag (default False)

# Metadata
name: String(255) [NOT NULL, INDEXED] - Descriptive name (e.g., "Essay Rubric Fall 2024")
description: Text [NULLABLE] - Detailed description of grading scheme purpose
category: String(100) [NULLABLE] - Classification (e.g., "essay", "lab_report", "exam")

# Calculated fields (denormalized for performance)
total_possible_points: Numeric(10, 2) [NOT NULL] - Sum of all criteria max_points
total_questions: Integer [NOT NULL] - Count of active questions in scheme
total_criteria: Integer [NOT NULL] - Count of all criteria across all questions

# Metadata
created_by: String(255) [NULLABLE] - Instructor/user who created scheme
last_modified_by: String(255) [NULLABLE] - User who last modified scheme
```

**Relationships**:
- `questions` → One-to-Many with SchemeQuestion (cascade delete)
- `graded_submissions` → One-to-Many with GradedSubmission (restrict delete if submissions exist)

**Validation Rules**:
- `name` must be unique per category (or globally unique)
- `total_possible_points` must equal sum of all criteria (calculated field, auto-updated)
- `total_questions` and `total_criteria` auto-calculated on save
- Cannot delete scheme if `graded_submissions` exist and `is_deleted = False` (soft delete instead)

**Indexes**:
```python
Index('idx_scheme_name', 'name')
Index('idx_scheme_category', 'category')
Index('idx_scheme_version', 'id', 'version_number')
```

---

### 2. SchemeQuestion

**Purpose**: Major section or question within a grading scheme

**Fields**:
```python
id: String(36) [PK] - UUID
scheme_id: String(36) [FK → GradingScheme.id, NOT NULL, INDEXED]
created_at: DateTime - UTC timestamp
updated_at: DateTime - UTC timestamp

# Question metadata
title: String(500) [NOT NULL] - Question text or category name
description: Text [NULLABLE] - Detailed instructions or rubric for this section
display_order: Integer [NOT NULL] - Order within scheme (1, 2, 3, ...)

# Calculated field
total_possible_points: Numeric(10, 2) [NOT NULL] - Sum of all criteria max_points for this question
```

**Relationships**:
- `scheme` → Many-to-One with GradingScheme
- `criteria` → One-to-Many with SchemeCriterion (cascade delete)

**Validation Rules**:
- `display_order` must be unique within scheme_id
- `total_possible_points` auto-calculated from sum of criteria
- `title` cannot be empty string

**Indexes**:
```python
Index('idx_question_scheme', 'scheme_id')
Index('idx_question_order', 'scheme_id', 'display_order')
```

**Constraints**:
```sql
CHECK (display_order > 0)
UNIQUE (scheme_id, display_order)
```

---

### 3. SchemeCriterion

**Purpose**: Individual evaluation point within a question (e.g., "Grammar - 5 points")

**Fields**:
```python
id: String(36) [PK] - UUID
question_id: String(36) [FK → SchemeQuestion.id, NOT NULL, INDEXED]
created_at: DateTime - UTC timestamp
updated_at: DateTime - UTC timestamp

# Criterion metadata
name: String(255) [NOT NULL] - Short criterion name (e.g., "Argument Clarity")
description: Text [NULLABLE] - Detailed grading guidance for this criterion
max_points: Numeric(10, 2) [NOT NULL] - Maximum points for this criterion
display_order: Integer [NOT NULL] - Order within question (1, 2, 3, ...)
```

**Relationships**:
- `question` → Many-to-One with SchemeQuestion
- `evaluations` → One-to-Many with CriterionEvaluation (restrict delete if evaluations exist)

**Validation Rules**:
- `max_points` must be > 0 and <= 1000 (reasonable upper bound)
- `display_order` must be unique within question_id
- `name` cannot be empty string
- Precision: 2 decimal places (enforced by Numeric(10, 2))

**Indexes**:
```python
Index('idx_criterion_question', 'question_id')
Index('idx_criterion_order', 'question_id', 'display_order')
```

**Constraints**:
```sql
CHECK (max_points > 0 AND max_points <= 1000)
CHECK (display_order > 0)
UNIQUE (question_id, display_order)
```

---

### 4. GradedSubmission

**Purpose**: Represents a student's work that has been evaluated using a grading scheme

**Fields**:
```python
id: String(36) [PK] - UUID
scheme_id: String(36) [FK → GradingScheme.id, NOT NULL, INDEXED]
scheme_version: Integer [NOT NULL] - Snapshot of scheme version at time of grading
created_at: DateTime - UTC timestamp when grading started
updated_at: DateTime - UTC timestamp of last evaluation update

# Submission metadata
student_id: String(255) [NOT NULL, INDEXED] - Student identifier
student_name: String(255) [NULLABLE] - Student name for export convenience
submission_reference: String(255) [NULLABLE] - Link to actual submission (file ID, assignment ID, etc.)

# Grading metadata
graded_by: String(255) [NOT NULL] - Instructor/grader identifier
graded_at: DateTime [NULLABLE, INDEXED] - Timestamp when marked complete
is_complete: Boolean [NOT NULL, DEFAULT False] - Whether grading is finished
evaluation_version: Integer [NOT NULL, DEFAULT 1] - Optimistic locking for concurrent edits

# Calculated totals (denormalized for performance)
total_points_earned: Numeric(10, 2) [NOT NULL, DEFAULT 0] - Sum of all criterion evaluations
total_points_possible: Numeric(10, 2) [NOT NULL] - Total from scheme at time of grading
percentage_score: Numeric(5, 2) [NULLABLE] - (points_earned / points_possible) * 100

# Scheme snapshot (for historical integrity)
scheme_snapshot: JSON [NULLABLE] - Complete scheme structure at time of grading (optional)
```

**Relationships**:
- `scheme` → Many-to-One with GradingScheme
- `evaluations` → One-to-Many with CriterionEvaluation (cascade delete)

**Validation Rules**:
- `scheme_version` must match a valid version of scheme_id
- `total_points_earned` must be >= 0 and <= total_points_possible
- `percentage_score` auto-calculated when is_complete = True
- `graded_at` must be set when is_complete = True

**Indexes**:
```python
Index('idx_submission_scheme', 'scheme_id', 'scheme_version')
Index('idx_submission_student', 'student_id')
Index('idx_submission_graded_at', 'graded_at')
Index('idx_submission_complete', 'is_complete')
```

**Constraints**:
```sql
CHECK (total_points_earned >= 0)
CHECK (total_points_earned <= total_points_possible)
CHECK (percentage_score >= 0 AND percentage_score <= 100)
CHECK (is_complete = False OR graded_at IS NOT NULL)
```

---

### 5. CriterionEvaluation

**Purpose**: Actual grade and feedback for one criterion on one submission

**Fields**:
```python
id: String(36) [PK] - UUID
submission_id: String(36) [FK → GradedSubmission.id, NOT NULL, INDEXED]
criterion_id: String(36) [FK → SchemeCriterion.id, NOT NULL, INDEXED]
created_at: DateTime - UTC timestamp
updated_at: DateTime - UTC timestamp

# Evaluation data
points_awarded: Numeric(10, 2) [NOT NULL] - Points given for this criterion (0 to max_points)
feedback: Text [NULLABLE] - Instructor feedback for this criterion
max_points: Numeric(10, 2) [NOT NULL] - Snapshot of max_points from criterion (for historical data)

# Metadata (denormalized for export performance)
criterion_name: String(255) [NOT NULL] - Snapshot of criterion name
question_title: String(500) [NOT NULL] - Snapshot of question title
```

**Relationships**:
- `submission` → Many-to-One with GradedSubmission
- `criterion` → Many-to-One with SchemeCriterion

**Validation Rules**:
- `points_awarded` must be >= 0 and <= max_points
- One evaluation per (submission_id, criterion_id) combination (unique constraint)
- `max_points` must match criterion.max_points at time of creation (snapshot for history)

**Indexes**:
```python
Index('idx_evaluation_submission', 'submission_id')
Index('idx_evaluation_criterion', 'criterion_id')
```

**Constraints**:
```sql
CHECK (points_awarded >= 0)
CHECK (points_awarded <= max_points)
UNIQUE (submission_id, criterion_id)
```

---

## State Transitions

### GradingScheme Lifecycle
```
Created (v1) → Modified (v2) → Modified (v3) → Soft Deleted (is_deleted=True)
                                                    ↓
                                              Cannot Hard Delete (has submissions)
```

### GradedSubmission Lifecycle
```
Created (is_complete=False, graded_at=NULL)
    ↓
In Progress (evaluations added/updated, evaluation_version increments)
    ↓
Marked Complete (is_complete=True, graded_at=now, percentage_score calculated)
    ↓
[Optional] Reopened (is_complete=False, graded_at=NULL)
```

---

## Calculated Fields & Triggers

### Auto-Calculation Rules

**GradingScheme.total_possible_points**:
- Recalculate when: SchemeQuestion or SchemeCriterion added/modified/deleted
- Formula: `SUM(SchemeQuestion.total_possible_points)`

**SchemeQuestion.total_possible_points**:
- Recalculate when: SchemeCriterion added/modified/deleted for this question
- Formula: `SUM(SchemeCriterion.max_points WHERE question_id = this.id)`

**GradedSubmission.total_points_earned**:
- Recalculate when: CriterionEvaluation added/modified/deleted for this submission
- Formula: `SUM(CriterionEvaluation.points_awarded WHERE submission_id = this.id)`

**GradedSubmission.percentage_score**:
- Calculate when: `is_complete = True`
- Formula: `(total_points_earned / total_points_possible) * 100`
- Precision: 2 decimal places

**Implementation**: SQLAlchemy event listeners or database triggers (prefer Python for testing/debugging)

---

## Data Integrity Rules

1. **Referential Integrity**:
   - All foreign keys must reference existing records
   - Cascade deletes: GradingScheme → SchemeQuestion → SchemeCriterion
   - Restrict deletes: SchemeCriterion cannot be deleted if evaluations exist

2. **Versioning Integrity**:
   - GradedSubmission.scheme_version must exist in GradingScheme history
   - Scheme modifications increment version_number
   - Old versions remain accessible for historical data

3. **Point Calculation Integrity**:
   - All point totals must be >= 0
   - Earned points cannot exceed possible points at any level
   - Precision maintained at 2 decimal places throughout

4. **Audit Trail**:
   - All entities have created_at, updated_at timestamps
   - GradedSubmission tracks graded_by for accountability
   - Scheme snapshots preserve exact grading criteria used

---

## Migration Strategy

### Phase 1: Create Tables
```python
# Migration 001: Create grading_schemes table
# Migration 002: Create scheme_questions table
# Migration 003: Create scheme_criteria table
# Migration 004: Create graded_submissions table
# Migration 005: Create criterion_evaluations table
# Migration 006: Add indexes and constraints
```

### Rollback Plan
- All migrations have downgrade() functions
- Drop tables in reverse dependency order
- No data loss for existing features (new tables only)

### Data Population
- No migration of existing data (new feature)
- Test data fixtures for development/testing
- Sample schemes provided in documentation

---

## Query Performance Considerations

### Common Query Patterns

**1. Fetch complete scheme with hierarchy**:
```python
scheme = GradingScheme.query.filter_by(id=scheme_id)\
    .options(joinedload('questions').joinedload('criteria'))\
    .first()
```
- Uses eager loading to avoid N+1 queries
- Returns: 1 scheme + N questions + M criteria in 1 query

**2. Fetch graded submission with all evaluations**:
```python
submission = GradedSubmission.query.filter_by(id=submission_id)\
    .options(joinedload('evaluations'))\
    .first()
```
- Eager loads all criterion evaluations
- Returns: 1 submission + N evaluations

**3. Export query (filter + pagination)**:
```python
submissions = GradedSubmission.query\
    .filter_by(scheme_id=scheme_id, is_complete=True)\
    .filter(GradedSubmission.graded_at >= start_date)\
    .order_by(GradedSubmission.graded_at.desc())\
    .paginate(page=1, per_page=100)
```
- Uses indexes on scheme_id, is_complete, graded_at
- Pagination prevents memory issues for large exports

**4. Calculate scheme usage statistics**:
```python
stats = db.session.query(
    GradingScheme.id,
    GradingScheme.name,
    func.count(GradedSubmission.id).label('total_submissions'),
    func.avg(GradedSubmission.percentage_score).label('avg_score')
).join(GradedSubmission)\
 .filter(GradedSubmission.is_complete == True)\
 .group_by(GradingScheme.id)\
 .all()
```
- Aggregation query for analytics dashboard
- Uses indexed columns for efficient joins

### Optimization Notes
- Denormalized fields (total_points, criterion_name snapshots) trade write complexity for read performance
- Indexes on foreign keys and frequently filtered columns (graded_at, is_complete)
- JSON snapshot field trades storage for query simplicity (avoid complex historical reconstructions)

---

## Testing Strategy

### Model Tests (Unit)
- `test_scheme_creation`: Verify GradingScheme creation with default values
- `test_scheme_total_calculation`: Verify total_possible_points auto-calculation
- `test_question_ordering`: Verify display_order unique constraint
- `test_criterion_validation`: Verify max_points constraints (>0, <=1000)
- `test_evaluation_points_range`: Verify points_awarded constraints (0 to max)
- `test_submission_completion`: Verify is_complete triggers graded_at update
- `test_versioning`: Verify version_number increment on scheme modification
- `test_soft_delete`: Verify is_deleted flag prevents hard delete with submissions

### Integration Tests
- `test_create_complete_scheme`: Create scheme with 3 questions, 10 criteria
- `test_grade_submission`: Apply scheme, create evaluations, verify totals
- `test_partial_grading`: Save incomplete submission, resume later
- `test_concurrent_evaluation`: Verify optimistic locking detects conflicts
- `test_scheme_modification`: Modify scheme, verify new version, old submissions unchanged

### Contract Tests
- `test_to_dict_methods`: Verify all models serialize to JSON correctly
- `test_export_csv_format`: Verify CSV columns match specification
- `test_export_json_schema`: Verify JSON structure matches schema

---

## Next Steps (Phase 1 Continued)

- Create OpenAPI contract specifications in contracts/ directory
- Generate quickstart.md with development workflow
- Update CLAUDE.md (no new technologies, confirm existing stack)
