# Code Integration Reference

Quick copy-paste code snippets for implementing scheme_id integration.

---

## 1. Database Model Changes

### Add to models.py - GradingJob class (after batch_id field, line ~209)

```python
# Grading scheme reference
scheme_id = db.Column(db.String(36), db.ForeignKey("grading_schemes.id"), nullable=True)

# Relationship to GradingScheme
scheme = db.relationship("GradingScheme", backref="jobs_using_scheme", lazy=True)
```

### Update models.py - GradingJob.to_dict() method (add to return dict)

```python
"scheme_id": self.scheme_id,
```

### Add to models.py - JobBatch class (after saved_marking_scheme_id field, line ~761)

```python
# Grading scheme reference
scheme_id = db.Column(db.String(36), db.ForeignKey("grading_schemes.id"), nullable=True)

# Relationship to GradingScheme
scheme = db.relationship("GradingScheme", backref="batches_using_scheme", lazy=True)
```

### Update models.py - JobBatch.to_dict() method (add to return dict)

```python
"scheme_id": self.scheme_id,
```

### Update models.py - JobBatch.create_job_with_batch_settings() method

In the job_data dict (around line 1027), change:
```python
# Before:
"saved_marking_scheme_id": kwargs.get("saved_marking_scheme_id") or self.saved_marking_scheme_id,

# After:
"saved_marking_scheme_id": kwargs.get("saved_marking_scheme_id") or self.saved_marking_scheme_id,
"scheme_id": kwargs.get("scheme_id") or self.scheme_id,  # NEW
```

---

## 2. Route Changes - routes/batches.py

### Update create_batch() function (line 100)

In the JobBatch() constructor, add:
```python
scheme_id=data.get("scheme_id"),
```

Full context:
```python
batch = JobBatch(
    batch_name=data["batch_name"],
    description=data.get("description", ""),
    provider=data.get("provider"),
    prompt=data.get("prompt"),
    model=data.get("model"),
    models_to_compare=data.get("models_to_compare"),
    temperature=data.get("temperature", 0.3),
    max_tokens=data.get("max_tokens", 2000),
    priority=data.get("priority", 5),
    tags=data.get("tags", []),
    batch_settings=data.get("batch_settings", {}),
    auto_assign_jobs=data.get("auto_assign_jobs", False),
    deadline=(datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None),
    template_id=data.get("template_id"),
    saved_prompt_id=data.get("saved_prompt_id"),
    saved_marking_scheme_id=data.get("saved_marking_scheme_id"),
    scheme_id=data.get("scheme_id"),  # NEW LINE
    created_by=data.get("created_by", "anonymous"),
)
```

### Update create_job() function (line 171)

In the GradingJob() constructor, add:
```python
scheme_id=data.get("scheme_id"),
```

Full context:
```python
job = GradingJob(
    job_name=data["job_name"],
    description=data.get("description", ""),
    provider=data["provider"],
    prompt=data["prompt"],
    model=data.get("model"),
    models_to_compare=data.get("models_to_compare"),
    priority=data.get("priority", 5),
    temperature=data.get("temperature", 0.3),
    max_tokens=data.get("max_tokens", 2000),
    marking_scheme_id=data.get("marking_scheme_id"),
    scheme_id=data.get("scheme_id"),  # NEW LINE
    saved_prompt_id=data.get("saved_prompt_id"),
    saved_marking_scheme_id=data.get("saved_marking_scheme_id"),
    batch_id=data.get("batch_id"),
)
```

---

## 3. Route Changes - routes/upload.py

### Update upload_bulk() function (line 448)

Around line 448 where GradingJob is created if job_id not provided:
```python
job = GradingJob(
    job_name=request.form.get("job_name", "Bulk Upload Job"),
    description=request.form.get("description", ""),
    provider=request.form.get("provider", "openrouter"),
    prompt=request.form.get(
        "prompt",
        session.get("default_prompt", "Please grade these documents."),
    ),
    model=request.form.get("customModel") or None,
    temperature=float(request.form.get("temperature", "0.3")),
    max_tokens=int(request.form.get("max_tokens", "2000")),
    scheme_id=request.form.get("scheme_id"),  # NEW LINE
)
```

### Add to upload_bulk() - pass schemes to template

First, add import at top of file:
```python
from models import GradingJob, MarkingScheme, Submission, GradingScheme, db  # Add GradingScheme
```

Then add before upload_bulk function return (or in a GET handler):
```python
grading_schemes = GradingScheme.query.filter_by(is_deleted=False).order_by(GradingScheme.name).all()
return render_template("bulk_upload.html", grading_schemes=[s.to_dict() for s in grading_schemes])
```

---

## 4. Route Changes - routes/grading_ui.py

### Update grade_submission() function (line 14)

Replace the entire function with:
```python
@grading_ui_bp.route("/<submission_id>/grade", methods=["GET"])
def grade_submission(submission_id):
    """
    Display grading form for a submission.

    Query Parameters:
    - scheme_id: Scheme to use for grading (optional, falls back to job.scheme_id)
    """
    try:
        scheme_id = request.args.get("scheme_id")

        # Validate submission exists
        submission = Submission.query.filter_by(id=submission_id).first()
        if not submission:
            flash("Submission not found", "danger")
            return redirect(request.referrer or "/")

        # If scheme_id not provided, try to get from job
        if not scheme_id and submission.job and submission.job.scheme_id:
            scheme_id = submission.job.scheme_id

        # Validate scheme if provided
        if scheme_id:
            scheme = GradingScheme.query.filter_by(id=scheme_id, is_deleted=False).first()
            if not scheme:
                flash("Grading scheme not found", "danger")
                return redirect(request.referrer or "/")

        return render_template(
            "grading/grade_submission.html",
            submission=submission,
            scheme_id=scheme_id,
        )

    except Exception as e:
        flash(f"Error loading grading form: {str(e)}", "danger")
        return redirect(request.referrer or "/")
```

---

## 5. Template - templates/bulk_upload.html

### Add after the Job Template section (around line 95)

Find the templateInfo div and add this after it:
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
            {{ scheme.name }} 
            ({{ scheme.total_questions }} questions, {{ scheme.total_possible_points }} pts)
        </option>
        {% endfor %}
    </select>
    <div class="form-text">
        <i class="fas fa-info-circle me-1"></i>
        Select a grading scheme to apply structured evaluation to submissions
    </div>
</div>
```

---

## 6. Template - templates/job_detail.html

### Add after Job Overview card (around line 80)

Insert this new card section after the existing Job Overview card:
```html
<!-- Grading Scheme Card (if job has a scheme) -->
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
                    <strong>Scheme Name:</strong> 
                    <span class="text-primary">{{ job.scheme.name if job.scheme else 'Scheme not found' }}</span>
                </div>
                {% if job.scheme and job.scheme.description %}
                <div class="mb-3">
                    <strong>Description:</strong> {{ job.scheme.description }}
                </div>
                {% endif %}
                {% if job.scheme %}
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
                {% endif %}
            </div>
            <div class="col-md-4">
                {% if job.scheme %}
                <a href="/schemes/{{ job.scheme.id }}" class="btn btn-sm btn-outline-primary w-100 mb-2">
                    <i class="fas fa-eye me-1"></i>View Scheme
                </a>
                <button class="btn btn-sm btn-outline-success w-100" 
                        onclick="applySchemeToSubmissions('{{ job.id }}', '{{ job.scheme.id }}')">
                    <i class="fas fa-check me-1"></i>Apply to Submissions
                </button>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endif %}
```

### Add JavaScript function to job_detail.html (in <script> section at bottom)

```javascript
function applySchemeToSubmissions(jobId, schemeId) {
    if (!confirm(`Apply scheme to all submissions in this job?`)) {
        return;
    }

    // Fetch all submissions for the job
    fetch(`/api/jobs/${jobId}/submissions`)
        .then(r => r.json())
        .then(data => {
            const submissions = data.submissions || [];
            if (submissions.length === 0) {
                alert("No submissions found for this job");
                return;
            }

            // For each submission, create a GradedSubmission
            Promise.all(submissions.map(sub =>
                fetch(`/api/grading/submissions`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        scheme_id: schemeId,
                        student_id: sub.original_filename || `submission_${sub.id}`,
                        submission_reference: sub.id,
                        graded_by: 'system'  // Could be user email from session
                    })
                })
                .then(r => r.json())
                .catch(e => console.error('Failed to create graded submission:', e))
            ))
            .then(results => {
                const successful = results.filter(r => r && r.id).length;
                alert(`Applied scheme to ${successful} submissions`);
                location.reload();
            })
            .catch(e => {
                alert(`Error applying scheme: ${e.message}`);
                console.error(e);
            });
        })
        .catch(e => {
            alert(`Error fetching submissions: ${e.message}`);
            console.error(e);
        });
}
```

---

## 7. Template - templates/batch_detail.html

### Add similar scheme card (if batch has scheme_id)

Add after batch overview section:
```html
{% if batch.scheme_id %}
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">
            <i class="fas fa-check-square me-2"></i>Grading Scheme
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-8">
                <p><strong>Scheme:</strong> {{ batch.scheme.name if batch.scheme else 'Not found' }}</p>
            </div>
            <div class="col-md-4">
                {% if batch.scheme %}
                <a href="/schemes/{{ batch.scheme.id }}" class="btn btn-sm btn-outline-primary w-100">
                    <i class="fas fa-eye me-1"></i>View Scheme
                </a>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endif %}
```

---

## 8. Import Statement Update

### In routes/upload.py - Update imports (line 11)

Change:
```python
from models import GradingJob, MarkingScheme, Submission, db
```

To:
```python
from models import GradingJob, MarkingScheme, Submission, GradingScheme, db
```

---

## Summary of Changes

- **models.py**: 3 additions (2 columns, 1 relationship per model) + 2 to_dict() updates
- **routes/batches.py**: 2 additions (one per constructor)
- **routes/upload.py**: 1 addition + 1 import update
- **routes/grading_ui.py**: 1 function replacement
- **templates/bulk_upload.html**: 1 form section addition
- **templates/job_detail.html**: 1 card addition + 1 JavaScript function
- **templates/batch_detail.html**: 1 card addition

All changes are **backward compatible** - scheme_id is optional everywhere.

---

## Testing Commands

After implementation, test with:

```bash
# Create a scheme first
curl -X POST http://localhost:5000/api/schemes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Scheme",
    "questions": [{
      "title": "Q1",
      "criteria": [{"name": "Criterion 1", "max_points": 10}]
    }]
  }'

# Create job with scheme_id
curl -X POST http://localhost:5000/create_job \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Test Job",
    "provider": "openrouter",
    "prompt": "Grade this",
    "scheme_id": "SCHEME_ID_FROM_ABOVE"
  }'

# View job to verify scheme is attached
curl http://localhost:5000/api/jobs/JOB_ID_FROM_ABOVE
```

