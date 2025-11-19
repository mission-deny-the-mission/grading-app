# scheme_id Integration Guide

## Quick Summary

The grading app needs to integrate **GradingScheme** into the job creation workflow. Currently:
- ✓ GradingScheme CRUD exists (routes/schemes.py)
- ✓ GradedSubmission API exists (routes/grading.py)
- ✓ Scheme-based grading UI exists (templates/grading/grade_submission.html)
- ❌ Jobs and Batches don't link to schemes yet
- ❌ Bulk upload doesn't accept scheme_id
- ❌ Job/batch detail views don't show scheme info

---

## File-by-File Integration Checklist

### 1. Database Models (models.py)

**GradingJob** (line 165-372)
- Add: `scheme_id` column (FK to GradingScheme, nullable)
- Update: `to_dict()` method to include scheme_id and scheme info

**JobBatch** (line 705-1127)
- Add: `scheme_id` column (FK to GradingScheme, nullable)
- Update: `to_dict()` method to include scheme_id and scheme info
- Update: `create_job_with_batch_settings()` to pass scheme_id to created jobs

---

### 2. Route: Batch Creation (routes/batches.py:100-168)

**Function**: `create_batch()`
- Add to request validation: Accept `scheme_id` from JSON
- When creating JobBatch, set: `scheme_id=data.get("scheme_id")`
- Return: Include scheme_id in response

**Code Pattern**:
```python
batch = JobBatch(
    batch_name=data["batch_name"],
    # ... existing fields ...
    scheme_id=data.get("scheme_id"),  # NEW
)
```

---

### 3. Route: Job Creation (routes/batches.py:171-243)

**Function**: `create_job()`
- Add to request validation: Accept `scheme_id` from JSON
- When creating GradingJob, set: `scheme_id=data.get("scheme_id")`
- Return: Include scheme_id in response

**Code Pattern**:
```python
job = GradingJob(
    job_name=data["job_name"],
    # ... existing fields ...
    scheme_id=data.get("scheme_id"),  # NEW
)
```

---

### 4. Route: Bulk Upload (routes/upload.py:433-519)

**Function**: `upload_bulk()`
- When creating a new GradingJob (if job_id not provided), add:
  ```python
  scheme_id=request.form.get("scheme_id"),  # NEW
  ```

**Code Location**: Line 448-459 (GradingJob creation)
```python
job = GradingJob(
    job_name=request.form.get("job_name", "Bulk Upload Job"),
    # ... existing fields ...
    scheme_id=request.form.get("scheme_id"),  # NEW
)
```

---

### 5. Template: Bulk Upload Form (templates/bulk_upload.html)

**Action**: Add scheme selection dropdown
- Add after "Job Template" selection section
- Show available schemes from context
- Make optional (allow null scheme_id)

**Location**: After line 95 (template info section)
**Code to Add**:
```html
<!-- Grading Scheme Selection -->
<div class="mb-3">
    <label class="form-label fw-bold">
        <i class="fas fa-check-square me-2"></i>Grading Scheme (Optional)
    </label>
    <select class="form-select" id="schemeSelect" name="scheme_id">
        <option value="">No scheme - LLM-based grading only</option>
        {% for scheme in grading_schemes %}
        <option value="{{ scheme.id }}">
            {{ scheme.name }} ({{ scheme.total_questions }} questions, {{ scheme.total_possible_points }} pts)
        </option>
        {% endfor %}
    </select>
    <div class="form-text">
        Select a grading scheme to apply structured evaluation to submissions
    </div>
</div>
```

**Backend Update**: In routes/main.py or templates.py, load schemes in context:
```python
@some_route_bp.route("/bulk_upload")
def bulk_upload():
    grading_schemes = GradingScheme.query.filter_by(is_deleted=False).order_by(GradingScheme.name).all()
    return render_template("bulk_upload.html", grading_schemes=grading_schemes)
```

---

### 6. Template: Job Detail (templates/job_detail.html)

**Action**: Display scheme information if job has scheme_id
- After "Job Overview" section (around line 80)
- Show scheme name, questions, criteria, max points
- Add button: "Apply Scheme to Submissions"

**Code to Add**:
```html
{% if job.scheme_id %}
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">
            <i class="fas fa-check-square me-2"></i>Grading Scheme
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-8">
                <div class="mb-3">
                    <strong>Scheme Name:</strong> {{ job.scheme.name }}
                </div>
                {% if job.scheme.description %}
                <div class="mb-3">
                    <strong>Description:</strong> {{ job.scheme.description }}
                </div>
                {% endif %}
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <strong>Questions:</strong> {{ job.scheme.total_questions }}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <strong>Criteria:</strong> {{ job.scheme.total_criteria }}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <strong>Max Points:</strong> {{ job.scheme.total_possible_points }}
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <a href="/schemes/{{ job.scheme.id }}" class="btn btn-sm btn-outline-primary w-100 mb-2">
                    <i class="fas fa-eye me-1"></i>View Scheme
                </a>
                <button class="btn btn-sm btn-outline-success w-100" onclick="applySchemeToSubmissions('{{ job.id }}', '{{ job.scheme.id }}')">
                    <i class="fas fa-check me-1"></i>Apply to Submissions
                </button>
            </div>
        </div>
    </div>
</div>
{% endif %}
```

**Update Submissions Table** (around line 120):
- Add column: "Grading Status" 
- Show if submission has corresponding GradedSubmission record
- Add link to grade submission

---

### 7. Template: Batch Detail (templates/batch_detail.html)

**Action**: Similar to job_detail.html - display scheme info
- Show batch's scheme if present
- Add button to apply scheme

---

### 8. Route: Submission Grading UI (routes/grading_ui.py:14-46)

**Function**: `grade_submission()`
- Add fallback: If scheme_id not in query params, try to get from job
  ```python
  scheme_id = request.args.get("scheme_id")
  if not scheme_id and submission.job and submission.job.scheme_id:
      scheme_id = submission.job.scheme_id
  ```

---

## JavaScript Functions to Add

Add to templates (e.g., in job_detail.html script section):

```javascript
function applySchemeToSubmissions(jobId, schemeId) {
    // Fetch all submissions for the job
    fetch(`/api/jobs/${jobId}/submissions`)
        .then(r => r.json())
        .then(data => {
            // For each submission, create a GradedSubmission
            const submissions = data.submissions || [];
            Promise.all(submissions.map(sub =>
                fetch(`/api/grading/submissions`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        scheme_id: schemeId,
                        student_id: sub.original_filename,  // Use filename as student ID
                        submission_reference: sub.id,
                        graded_by: 'system'  // or get from user context
                    })
                })
            )).then(() => {
                alert(`Applied scheme to ${submissions.length} submissions`);
                location.reload();
            });
        });
}
```

---

## Data Inheritance Pattern

When scheme_id is set at different levels:

```
Batch Level: batch.scheme_id
    └─> Inherited by each job created in batch
        └─> Inherited by each submission created in job
            └─> Used to create GradedSubmission records

Job Level: job.scheme_id
    └─> Inherited by each submission created in job
        └─> Used to create GradedSubmission records
```

In `JobBatch.create_job_with_batch_settings()`:
```python
job_data = {
    # ... existing fields ...
    "scheme_id": kwargs.get("scheme_id") or self.scheme_id,
}
```

---

## Query Parameter vs. Model Linking

### Current Behavior (Works)
```
GET /submissions/123/grade?scheme_id=abc
```
- scheme_id passed as query parameter
- Temporary link for grading UI

### Enhanced Behavior (After Integration)
```
GET /submissions/123/grade?scheme_id=abc  (still works as override)
```
- Falls back to job.scheme_id if query param not provided
- Permanent link stored in job/batch

---

## Testing Considerations

### Unit Tests to Update
- Test JobBatch creation with scheme_id
- Test GradingJob creation with scheme_id
- Test bulk upload with scheme_id
- Test inheritance from batch to job to submission

### Integration Tests
- Create batch with scheme → create job → upload files → verify scheme_id flows through
- Create job with scheme directly → upload files → verify scheme_id preserved

---

## Migration Considerations

**No database migration needed** - scheme_id is optional/nullable

**Backward Compatibility**:
- Existing jobs/batches without scheme_id continue to work
- scheme_id parameter is optional in all endpoints
- Grading still works without scheme_id (LLM-only mode)

---

## UI/UX Workflow After Integration

### Workflow 1: Batch → Job → Upload → Grade with Scheme
1. Create Batch with scheme_id
2. Create Job in batch (inherits scheme_id)
3. Upload files
4. View job detail → Click "Apply Scheme to Submissions"
5. Creates GradedSubmission records for each submission
6. Click submission → Grade using scheme

### Workflow 2: Direct Job with Scheme
1. Create Job with scheme_id
2. Upload files
3. Job detail shows scheme
4. Click "Apply Scheme"
5. Creates GradedSubmission records
6. Grade using scheme

### Workflow 3: Legacy LLM-Only (No Scheme)
1. Create Job/Batch without scheme_id
2. Upload files
3. LLM processes submissions
4. (Optionally) Apply scheme retroactively to add structured grading

---

## API Endpoints Summary

### Existing Endpoints (No Changes)
- `POST /api/grading/submissions` - Create graded submission (needs scheme_id)
- `GET /api/schemes` - List all schemes
- `GET /api/schemes/<scheme_id>` - Get scheme details

### Modified Endpoints
- `POST /create_batch` - Now accepts scheme_id
- `POST /create_job` - Now accepts scheme_id
- `POST /upload_bulk` - Now accepts scheme_id in form

### New Query Param Behavior
- `GET /submissions/<id>/grade?scheme_id=abc` - Fallback to job.scheme_id if not provided

---

## Files Summary

| File | Type | Changes | Priority |
|------|------|---------|----------|
| models.py | Model | Add scheme_id columns, update methods | HIGH |
| routes/batches.py | Route | Accept scheme_id in create_batch, create_job | HIGH |
| routes/upload.py | Route | Accept scheme_id in upload_bulk | HIGH |
| routes/grading_ui.py | Route | Fallback to job.scheme_id | MEDIUM |
| templates/bulk_upload.html | Template | Add scheme dropdown | HIGH |
| templates/job_detail.html | Template | Show scheme info, add apply button | HIGH |
| templates/batch_detail.html | Template | Show scheme info | MEDIUM |
| templates/grading/grade_submission.html | Template | Already works, may enhance | LOW |

---

## Dependency Graph

```
models.py (GradingJob.scheme_id)
    ↓
routes/batches.py (create_job accepts scheme_id)
    ↓
templates/bulk_upload.html (dropdown) + routes/upload.py (form data)
    ↓
templates/job_detail.html (display + apply button)
    ↓
routes/grading_ui.py (fallback to job.scheme_id)
    ↓
routes/grading.py (create GradedSubmission with scheme_id)
```

