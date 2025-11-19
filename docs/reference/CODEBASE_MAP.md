# Grading App - Job Creation & Submission Workflow Analysis

## Overview
The grading application has a hierarchical workflow: **Job Batch** → **Grading Job** → **Submission** → **GradedSubmission** (with Grading Scheme)

The system has two separate submission models:
- **Submission**: For LLM-based grading (uploaded documents)
- **GradedSubmission**: For structured grading using GradingScheme (with criteria evaluation)

---

## Database Models & Relationships

### Model Hierarchy

```
JobBatch
├── saved_prompt_id (SavedPrompt)
├── saved_marking_scheme_id (SavedMarkingScheme)
└── jobs: [GradingJob]

GradingJob
├── marking_scheme_id (MarkingScheme - for LLM grading)
├── saved_prompt_id (SavedPrompt)
├── saved_marking_scheme_id (SavedMarkingScheme)
├── batch_id (JobBatch)
└── submissions: [Submission]

Submission (LLM-based grading)
├── job_id (GradingJob)
├── extracted_text
├── grade (legacy field)
└── grade_results: [GradeResult]

GradingScheme (Structured grading)
├── questions: [SchemeQuestion]
│   └── criteria: [SchemeCriterion]
└── graded_submissions: [GradedSubmission]

GradedSubmission (Structured evaluation)
├── scheme_id (GradingScheme)
├── scheme_version
├── student_id, student_name
├── total_points_earned, total_points_possible
└── evaluations: [CriterionEvaluation]

CriterionEvaluation
├── submission_id (GradedSubmission)
├── criterion_id (SchemeCriterion)
├── points_awarded
└── feedback
```

### Key Models with scheme_id

**GradingScheme** (models.py:1471-1539)
- Primary model for structured grading
- Fields: name, description, category, total_possible_points, total_questions, total_criteria
- Relationships: questions, graded_submissions
- Index on: name, category, id+version_number

**GradedSubmission** (models.py:1656-1741)
- Records actual grades using a scheme
- Fields: scheme_id (FK), scheme_version, student_id, student_name, is_complete, total_points_earned, total_points_possible, percentage_score
- Relationships: evaluations (CriterionEvaluation)
- Index on: scheme_id+scheme_version, student_id, graded_at, is_complete

---

## Routes Structure

### Route Files & Blueprints

#### 1. **routes/batches.py** (Job & Batch Management)
- **GET /batches** - View all batches with filtering
- **GET /batches/<batch_id>** - View batch detail
- **POST /create_batch** - Create new batch
- **POST /create_job** - Create new grading job
  - Parameters: job_name, provider, prompt, model, temperature, max_tokens
  - Currently accepts: marking_scheme_id (MarkingScheme - old model), saved_prompt_id, saved_marking_scheme_id, batch_id
  - **MISSING: scheme_id for GradingScheme integration**

#### 2. **routes/upload.py** (File Upload & Processing)
- **POST /upload** - Single file upload with grading
- **POST /upload_marking_scheme** - Upload marking scheme file
- **POST /upload_bulk** - Bulk file upload and create submissions
  - Creates GradingJob if not provided
  - Creates Submission records for each file
  - Calls process_job.delay(job.id) to start processing

#### 3. **routes/grading.py** (API for GradedSubmission - Scheme-based)
- **POST /api/grading/submissions** - Create graded submission
  - Parameters: scheme_id, student_id, student_name (optional), submission_reference (optional), graded_by
  - Creates GradedSubmission tied to GradingScheme
- **GET /api/grading/submissions/<submission_id>** - Get graded submission
- **PATCH /api/grading/submissions/<submission_id>** - Update submission status
- **POST /api/grading/submissions/<submission_id>/evaluations** - Add criterion evaluation
  - Parameters: criterion_id, points_awarded, feedback
- **PATCH /api/grading/submissions/<submission_id>/evaluations/<eval_id>** - Update evaluation

#### 4. **routes/grading_ui.py** (UI for Grading Interface)
- **GET /submissions/<submission_id>/grade** - Display grading form
  - Query params: scheme_id (required)
  - Renders: grading/grade_submission.html
  - Loads Submission (LLM-based) with Scheme

#### 5. **routes/schemes.py** (Scheme CRUD)
- **POST /api/schemes** - Create grading scheme
- **GET /api/schemes** - List schemes (paginated, filtered)
- **GET /api/schemes/<scheme_id>** - Get scheme detail
- **PUT /api/schemes/<scheme_id>** - Update scheme
- **DELETE /api/schemes/<scheme_id>** - Soft-delete scheme
- **POST /api/schemes/<scheme_id>/clone** - Clone scheme

#### 6. **routes/schemes_ui.py** (UI for Scheme Management)
- **GET /schemes** - List schemes UI
- **GET /schemes/<scheme_id>** - Scheme detail page
- **GET /schemes/<scheme_id>/builder** - Scheme builder form
- **GET /schemes/statistics** - Scheme usage statistics

#### 7. **routes/export.py** (Data Export)
- **GET /api/export/schemes/<scheme_id>** - Export graded submissions for scheme
  - Parameters: format (csv/json), include_incomplete, start_date, end_date
  - Exports GradedSubmission records with evaluations

#### 8. **routes/api.py** (Extended API)
- Large file with many batch/job/template endpoints
- Manages SavedPrompt, SavedMarkingScheme, JobTemplate, BatchTemplate operations

---

## Current Job Creation Flow

### Step 1: Create Batch (Optional)
```
POST /create_batch
├── Input: batch_name, description, provider, prompt, model, priority, tags, template_id, saved_prompt_id, saved_marking_scheme_id
├── Creates: JobBatch record
└── DB: JobBatch table
```

### Step 2: Create Job
```
POST /create_job (routes/batches.py:171-243)
├── Input: job_name, description, provider, prompt, model, priority, temperature, max_tokens
├── Optional: marking_scheme_id, saved_prompt_id, saved_marking_scheme_id, batch_id
├── Creates: GradingJob record
├── Associates with: Batch (if batch_id provided)
├── Associates with: SavedPrompt and SavedMarkingScheme (increments usage)
└── DB: GradingJob table
```

### Step 3: Upload Files & Create Submissions
```
POST /upload_bulk (routes/upload.py:433-519)
├── Input: files[], job_id or job_name, job_template_id
├── Creates: GradingJob (if job_id not provided)
├── For each file:
│   ├── Creates: Submission record with job_id
│   └── DB: Submission table
├── Updates: job.total_submissions
└── Queues: process_job.delay(job.id) via Celery
```

### Step 4: Process Job (Background Task)
```
tasks.process_job (process_job.delay)
├── Reads: Submission records for job
├── For each submission:
│   ├── Extracts: Text from file
│   ├── Grades: Using LLM with prompt
│   ├── Creates: GradeResult record
│   └── Updates: Submission.status → "completed"
└── Updates: Job progress
```

---

## Where scheme_id Should Be Added

### Integration Points Needed

#### 1. **Job Creation (routes/batches.py:171-243)**
**Current Issue**: No scheme_id parameter accepted in /create_job
**Action**: Add optional scheme_id parameter
```python
# Should accept:
{
    "scheme_id": "uuid",  # NEW - Link job to grading scheme
    ...existing fields...
}
```

#### 2. **Batch Creation (routes/batches.py:100-168)**
**Current Issue**: Batch accepts saved_marking_scheme_id but not GradingScheme.scheme_id
**Action**: Add optional scheme_id parameter
```python
# Should accept:
{
    "scheme_id": "uuid",  # NEW - Link batch to grading scheme
    ...existing fields...
}
```

#### 3. **Bulk Upload (routes/upload.py:433-519)**
**Current Issue**: Job created in bulk upload doesn't accept scheme_id
**Action**: Add scheme_id to job creation form data
```python
# When creating GradingJob in upload_bulk:
job = GradingJob(
    scheme_id=request.form.get("scheme_id"),  # NEW
    ...existing fields...
)
```

#### 4. **Submission Detail View (grading_ui.py)**
**Current Issue**: Grade submission UI should show scheme link and evaluation form
**Action**: Load GradingScheme and display evaluation interface
- Query: GradingScheme.query.get(scheme_id)
- Render: Scheme details (questions, criteria, max points)
- Form: CriterionEvaluation inputs

#### 5. **Job Detail View (job_detail.html)**
**Current Issue**: Job detail doesn't show associated scheme
**Action**: Display scheme link if job.scheme_id exists
- Show: Scheme name, criteria count, max points
- Link: To grading interface for applying scheme

#### 6. **Batch Detail View (batch_detail.html)**
**Current Issue**: Batch detail doesn't show associated scheme
**Action**: Display scheme information if batch.scheme_id exists

---

## Template Files for Integration

### Existing Templates
- **templates/base.html** - Base layout
- **templates/jobs.html** - Job list view
- **templates/job_detail.html** - Job detail (needs scheme integration)
- **templates/bulk_upload.html** - Bulk upload form (needs scheme_id field)
- **templates/batch_detail.html** - Batch detail (needs scheme integration)
- **templates/batches.html** - Batch list
- **templates/schemes/index.html** - Scheme list
- **templates/schemes/detail.html** - Scheme detail
- **templates/schemes/builder.html** - Scheme builder
- **templates/grading/grade_submission.html** - Grading interface (uses scheme_id from query param)

### Needed Template Changes
1. **bulk_upload.html** - Add scheme_id dropdown field
2. **job_detail.html** - Add scheme display and "Apply Scheme" button
3. **batch_detail.html** - Add scheme display
4. **grading/grade_submission.html** - Add evaluation form (criteria, points, feedback)

---

## Key Parameters Through Workflow

### Parameter Flow Map

```
Batch Creation
├── batch_name ✓
├── provider ✓
├── prompt ✓
├── model ✓
├── scheme_id ❌ NEEDS ADDITION
└── saved_marking_scheme_id ✓ (Old model - SavedMarkingScheme)

Job Creation
├── job_name ✓
├── provider ✓
├── prompt ✓
├── model ✓
├── marking_scheme_id ✓ (Old model - MarkingScheme, for LLM)
├── scheme_id ❌ NEEDS ADDITION (GradingScheme)
├── saved_marking_scheme_id ✓
├── batch_id ✓
└── temperature, max_tokens ✓

Submission Creation (upload_bulk)
├── job_id ✓
├── filename ✓
├── file_type ✓
├── file_size ✓
└── (scheme_id inherited from job) ❌ NOT PASSED

Grading Interface (grade_submission GET)
├── submission_id ✓
├── scheme_id ✓ (Query param)
└── (Should load job.scheme_id as fallback if not provided)

Graded Submission Creation (API)
├── scheme_id ✓
├── student_id ✓
├── graded_by ✓
└── submission_reference (optional) ✓
```

---

## Files to Modify for scheme_id Integration

### Model Changes
- **models.py**
  - GradingJob: Add `scheme_id` column (FK to GradingScheme)
  - JobBatch: Add `scheme_id` column (FK to GradingScheme)

### Route Changes
- **routes/batches.py** (create_batch, create_job)
- **routes/upload.py** (upload_bulk)
- **routes/grading_ui.py** (grade_submission - fallback to job.scheme_id)

### Template Changes
- **templates/bulk_upload.html** - Add scheme_id field
- **templates/job_detail.html** - Show scheme, add apply scheme button
- **templates/batch_detail.html** - Show scheme
- **templates/grading/grade_submission.html** - Add evaluation form

### No Changes Needed
- **routes/grading.py** - Already supports scheme_id
- **routes/schemes.py** - Already implements scheme CRUD
- **routes/export.py** - Already exports GradedSubmission by scheme_id

---

## Database Queries for Integration

### List available schemes
```python
GradingScheme.query.filter_by(is_deleted=False).all()
```

### Get job with scheme
```python
job = GradingJob.query.get(job_id)
scheme = GradingScheme.query.get(job.scheme_id)
```

### Get submissions for job
```python
Submission.query.filter_by(job_id=job_id).all()
```

### Create graded submission
```python
submission = GradedSubmission(
    scheme_id=scheme_id,
    student_id="STU001",
    graded_by="instructor@example.com",
    total_points_possible=scheme.total_possible_points,
)
db.session.add(submission)
db.session.commit()
```

### Query graded submissions for scheme
```python
GradedSubmission.query.filter_by(scheme_id=scheme_id).all()
```

---

## Summary of Integration Points

| Component | Current State | Need scheme_id | Files |
|-----------|---------------|----------------|-------|
| JobBatch Model | Has saved_marking_scheme_id | Add scheme_id FK | models.py |
| GradingJob Model | Has marking_scheme_id (old) | Add scheme_id FK | models.py |
| Batch Creation Route | No scheme param | Add scheme_id input | routes/batches.py |
| Job Creation Route | No scheme param | Add scheme_id input | routes/batches.py |
| Bulk Upload Route | No scheme in form | Add scheme_id field | routes/upload.py, templates/bulk_upload.html |
| Submission Detail View | Not created yet | Create/enhance | routes/grading_ui.py |
| Job Detail Template | Doesn't show scheme | Add scheme display | templates/job_detail.html |
| Batch Detail Template | Doesn't show scheme | Add scheme display | templates/batch_detail.html |
| Grading Interface | Already accepts scheme_id in query param | OK | routes/grading_ui.py |
| GradedSubmission API | Already supports scheme_id | OK | routes/grading.py |

