# Structured Grading Scheme - Complete Implementation Plan

**Status**: Missing 70% of functionality
**Created**: 2025-11-15
**Priority**: HIGH - Core feature incomplete

---

## Executive Summary

The structured grading scheme feature has solid backend models but is **missing critical APIs and all frontend UI**. This plan provides a complete roadmap to deliver a working end-to-end feature.

### Current State
- ✅ **Backend Models**: 95% complete (GradingScheme, SchemeQuestion, SchemeCriterion)
- ✅ **Utilities**: 100% complete (calculators, validators)
- ✅ **Grading APIs**: 100% complete (submission evaluation endpoints)
- ❌ **Scheme Management APIs**: 0% complete (`routes/schemes.py` is empty!)
- ❌ **Frontend UI**: 0% complete (no scheme builder, no grading interface)

### Completion Estimate
- **Total Effort**: ~40-50 hours
- **Timeline**: 5-7 days (with focused development)
- **Risk**: Low (models already solid, well-tested)

---

## Phase 1: Backend Scheme Management APIs (12-15 hours)

**Goal**: Implement all CRUD endpoints for schemes, questions, and criteria

### 1.1 Core Scheme Endpoints (4 hours)
**File**: `routes/schemes.py`

#### Tasks:
- [ ] `POST /api/schemes` - Create new grading scheme
  - Accept: `name`, `description`, `total_points`
  - Validate: unique name, positive total_points
  - Return: created scheme with ID

- [ ] `GET /api/schemes` - List all schemes
  - Support: pagination, filtering (by name, active status)
  - Include: question/criteria counts, usage statistics
  - Return: array of schemes with metadata

- [ ] `GET /api/schemes/<id>` - Get scheme details
  - Include: full hierarchy (questions + criteria)
  - Calculate: actual vs expected totals
  - Return: complete scheme object

- [ ] `PUT /api/schemes/<id>` - Update scheme
  - Allow: name, description updates
  - Validate: no orphaned submissions
  - Create: new version if in use

- [ ] `DELETE /api/schemes/<id>` - Soft delete scheme
  - Check: no active submissions
  - Set: `is_deleted = True`
  - Return: 204 No Content

**Validation Rules**:
```python
- Name: 1-200 chars, unique among active schemes
- Description: optional, max 1000 chars
- Total points: must equal sum of question points
```

**Error Codes**:
```
400: Validation error (invalid points, duplicate name)
404: Scheme not found
409: Scheme in use (cannot delete/modify)
422: Point totals don't match
```

---

### 1.2 Question Management Endpoints (4 hours)
**File**: `routes/schemes.py`

#### Tasks:
- [ ] `POST /api/schemes/<scheme_id>/questions` - Add question to scheme
  - Accept: `question_text`, `max_points`, `display_order`
  - Validate: points don't exceed scheme total
  - Auto-calculate: display_order if not provided
  - Return: created question

- [ ] `GET /api/schemes/<scheme_id>/questions` - List all questions
  - Order by: `display_order` ASC
  - Include: criteria count per question
  - Return: array of questions

- [ ] `PUT /api/schemes/questions/<question_id>` - Update question
  - Allow: text, points, order changes
  - Validate: new points >= sum of criteria points
  - Recalculate: scheme totals
  - Return: updated question

- [ ] `DELETE /api/schemes/questions/<question_id>` - Delete question
  - Check: no criteria have evaluations
  - Cascade: delete all criteria
  - Reorder: remaining questions
  - Return: 204 No Content

- [ ] `POST /api/schemes/questions/reorder` - Reorder questions
  - Accept: array of `{question_id, display_order}`
  - Validate: all IDs belong to same scheme
  - Update: all display_order values
  - Return: updated question list

**Validation Rules**:
```python
- Question text: 1-500 chars
- Max points: 0-10000, must be positive
- Display order: auto-increment or explicit (1, 2, 3...)
- Sum of question points must equal scheme total_points
```

---

### 1.3 Criteria Management Endpoints (4 hours)
**File**: `routes/schemes.py`

#### Tasks:
- [ ] `POST /api/schemes/questions/<question_id>/criteria` - Add criterion
  - Accept: `criterion_name`, `description`, `max_points`, `display_order`
  - Validate: points don't exceed question max
  - Auto-calculate: display_order
  - Return: created criterion

- [ ] `GET /api/schemes/questions/<question_id>/criteria` - List criteria
  - Order by: `display_order` ASC
  - Include: average score across submissions (if any)
  - Return: array of criteria

- [ ] `PUT /api/schemes/criteria/<criterion_id>` - Update criterion
  - Allow: name, description, points, order changes
  - Validate: points >= highest awarded value
  - Recalculate: question/scheme totals
  - Return: updated criterion

- [ ] `DELETE /api/schemes/criteria/<criterion_id>` - Delete criterion
  - Check: no evaluations exist
  - Reorder: remaining criteria
  - Return: 204 No Content

- [ ] `POST /api/schemes/criteria/reorder` - Reorder criteria
  - Accept: array of `{criterion_id, display_order}`
  - Validate: all IDs belong to same question
  - Update: display_order values
  - Return: updated criteria list

**Validation Rules**:
```python
- Criterion name: 1-200 chars
- Description: optional, max 1000 chars
- Max points: 0-10000, positive
- Sum of criteria points must equal question max_points
```

---

### 1.4 Scheme Utilities (2-3 hours)

#### Tasks:
- [ ] `POST /api/schemes/<id>/clone` - Clone existing scheme
  - Copy: scheme + all questions + criteria
  - Increment: name with " (Copy)" suffix
  - Reset: usage statistics
  - Return: new scheme ID

- [ ] `GET /api/schemes/<id>/statistics` - Get usage statistics
  - Calculate: # submissions graded
  - Calculate: average score, min/max
  - Calculate: per-question averages
  - Calculate: per-criterion averages
  - Return: comprehensive stats object

- [ ] `POST /api/schemes/<id>/validate` - Validate scheme integrity
  - Check: all point totals match
  - Check: no orphaned criteria
  - Check: display_order is sequential
  - Return: validation report with warnings/errors

- [ ] `GET /api/schemes/<id>/export` - Export scheme as JSON
  - Include: full hierarchy
  - Format: portable JSON structure
  - Use case: backup, sharing, migration
  - Return: JSON file download

**Response Examples**:
```json
// Clone response
{
  "id": 42,
  "name": "Midterm Rubric (Copy)",
  "cloned_from": 23,
  "created_at": "2025-11-15T10:30:00Z"
}

// Statistics response
{
  "scheme_id": 23,
  "total_submissions": 87,
  "average_score": 78.5,
  "average_percentage": 78.5,
  "min_score": 45.0,
  "max_score": 98.0,
  "questions": [
    {
      "question_id": 1,
      "question_text": "Problem Solving",
      "average_score": 18.3,
      "max_points": 25
    }
  ],
  "criteria": [
    {
      "criterion_id": 1,
      "criterion_name": "Correctness",
      "average_score": 8.7,
      "max_points": 10
    }
  ]
}
```

---

## Phase 2: Frontend Scheme Builder UI (15-18 hours)

**Goal**: Create intuitive UI for creating and managing grading schemes

### 2.1 Scheme Management Dashboard (4 hours)
**File**: `templates/schemes/index.html` (new)

#### Features:
- [ ] **List View**
  - Display all schemes in table/card layout
  - Show: name, total_points, # questions, # submissions graded
  - Sort: by name, created date, usage count
  - Filter: active vs deleted, by name search

- [ ] **Action Buttons**
  - Create New Scheme (opens builder)
  - Edit Scheme (opens builder in edit mode)
  - Clone Scheme (duplicates with new name)
  - Delete Scheme (with confirmation modal)
  - View Statistics (opens analytics modal)

- [ ] **Quick Stats**
  - Total schemes count
  - Most used scheme
  - Recent activity timeline

**UI Components**:
```html
<div class="scheme-card">
  <h3>Midterm Rubric</h3>
  <div class="stats">
    <span>50 points</span>
    <span>5 questions</span>
    <span>87 submissions</span>
  </div>
  <div class="actions">
    <button class="btn-edit">Edit</button>
    <button class="btn-clone">Clone</button>
    <button class="btn-delete">Delete</button>
  </div>
</div>
```

**API Integration**:
- Load: `GET /api/schemes`
- Delete: `DELETE /api/schemes/<id>`
- Clone: `POST /api/schemes/<id>/clone`

---

### 2.2 Scheme Builder Form (6-8 hours)
**File**: `templates/schemes/builder.html` (new)

#### Features:
- [ ] **Basic Info Section**
  - Input: Scheme Name (required)
  - Textarea: Description (optional)
  - Input: Total Points (required, validated)
  - Auto-calculate: total from questions
  - Warning: if totals don't match

- [ ] **Question Management**
  - Add Question button
  - Question list (sortable with drag-and-drop)
  - Each question row shows:
    - Question text (editable inline)
    - Max points (editable, validated)
    - Criteria count
    - Expand/collapse to show criteria
    - Delete button (with confirmation)

- [ ] **Criteria Management** (nested under questions)
  - Add Criterion button per question
  - Criteria list (sortable)
  - Each criterion row shows:
    - Criterion name (editable)
    - Description (editable)
    - Max points (editable, validated)
    - Delete button

- [ ] **Validation & Save**
  - Real-time validation:
    - Scheme total = sum of question points
    - Question total = sum of criteria points
  - Visual indicators: ✓ valid, ⚠ warning, ✗ error
  - Save button (disabled until valid)
  - Cancel button (with unsaved changes warning)

**UI Structure**:
```html
<form id="scheme-builder">
  <!-- Basic Info -->
  <section class="basic-info">
    <input name="scheme_name" placeholder="e.g., Midterm Rubric" required>
    <textarea name="description"></textarea>
    <input name="total_points" type="number" readonly>
    <span class="calculated">(Calculated from questions)</span>
  </section>

  <!-- Questions -->
  <section class="questions">
    <button type="button" id="add-question">+ Add Question</button>
    <div class="question-list" data-sortable>
      <!-- Dynamic question items -->
      <div class="question-item" data-question-id="temp-1">
        <input name="question_text" placeholder="Question 1">
        <input name="max_points" type="number" min="0">
        <button class="toggle-criteria">Show Criteria (0)</button>
        <button class="delete-question">Delete</button>

        <!-- Nested Criteria -->
        <div class="criteria-list" style="display:none">
          <button type="button" class="add-criterion">+ Add Criterion</button>
          <div class="criterion-item">
            <input name="criterion_name" placeholder="Criterion name">
            <input name="criterion_description" placeholder="Description">
            <input name="max_points" type="number" min="0">
            <button class="delete-criterion">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Actions -->
  <div class="form-actions">
    <button type="submit" class="btn-primary" disabled>Save Scheme</button>
    <button type="button" class="btn-secondary">Cancel</button>
  </div>
</form>
```

**JavaScript Logic** (`static/js/scheme-builder.js`):
- [ ] Dynamic add/remove questions and criteria
- [ ] Real-time point calculation and validation
- [ ] Drag-and-drop reordering (using SortableJS or similar)
- [ ] Form serialization to JSON
- [ ] AJAX submission to API
- [ ] Unsaved changes detection

**API Integration**:
- Create: `POST /api/schemes` + `POST /api/schemes/<id>/questions` + `POST /api/schemes/questions/<id>/criteria`
- Load (edit mode): `GET /api/schemes/<id>`
- Update: `PUT /api/schemes/<id>`, `PUT /api/schemes/questions/<id>`, `PUT /api/schemes/criteria/<id>`

---

### 2.3 Inline Validation & UX Polish (3-4 hours)

#### Features:
- [ ] **Point Validation**
  - Show running totals at each level
  - Highlight mismatches in red
  - Show "✓ Valid" when correct

- [ ] **Auto-save Draft** (optional)
  - Save to localStorage every 30 seconds
  - Restore on page reload
  - Clear on successful save

- [ ] **Keyboard Shortcuts**
  - Ctrl+S: Save
  - Ctrl+Q: Add question
  - Ctrl+C: Add criterion (when question focused)
  - Tab/Shift+Tab: Navigate between fields

- [ ] **Accessibility**
  - ARIA labels on all inputs
  - Keyboard-only navigation support
  - Screen reader announcements for dynamic changes

- [ ] **Error Handling**
  - Show API errors in-page (not alerts)
  - Field-level validation messages
  - Network error recovery (retry button)

**CSS Styling**:
```css
.point-mismatch {
  border: 2px solid #e74c3c;
  background: #ffe5e5;
}

.point-valid {
  border: 2px solid #27ae60;
}

.validation-message {
  color: #e74c3c;
  font-size: 0.9em;
  margin-top: 4px;
}

.question-item {
  border-left: 4px solid #3498db;
  padding: 15px;
  margin: 10px 0;
  background: #f9f9f9;
}

.criterion-item {
  border-left: 2px solid #95a5a6;
  padding: 10px;
  margin: 8px 0 8px 20px;
  background: white;
}
```

---

### 2.4 Statistics & Analytics Modal (2-3 hours)
**File**: `templates/schemes/statistics.html` (modal component)

#### Features:
- [ ] **Overview Stats**
  - Total submissions graded
  - Average score & percentage
  - Min/Max scores
  - Standard deviation

- [ ] **Per-Question Breakdown**
  - Table showing each question
  - Average score vs max points
  - Visual bar chart

- [ ] **Per-Criterion Breakdown**
  - Most/least successful criteria
  - Average points awarded
  - Recommendations (e.g., "Students struggle with X")

- [ ] **Export Options**
  - Download as CSV
  - Download full data as JSON
  - Print-friendly view

**API Integration**:
- Load: `GET /api/schemes/<id>/statistics`
- Export: `GET /api/export/schemes/<id>?format=csv`

---

## Phase 3: Frontend Grading Interface (10-12 hours)

**Goal**: Enable teachers to grade submissions using the structured scheme

### 3.1 Submission Grading Page (6-8 hours)
**File**: `templates/grading/grade_submission.html` (new)

#### Features:
- [ ] **Header Section**
  - Student name/ID
  - Submission date
  - Scheme name
  - Current total score (live updates)
  - Progress indicator (X of Y criteria graded)

- [ ] **Dynamic Grading Form**
  - Generated from scheme structure
  - Grouped by question
  - Each criterion shows:
    - Name and description
    - Max points allowed
    - Points input (0 to max)
    - Feedback textarea
    - Visual indicator (points awarded / max)

- [ ] **Score Summary**
  - Per-question totals
  - Overall total
  - Percentage score
  - Color-coded grade (A/B/C/D/F)

- [ ] **Actions**
  - Save Draft (incomplete grading)
  - Mark Complete (finalizes grade)
  - Previous/Next Submission
  - Return to Submission List

**UI Structure**:
```html
<div class="grading-interface">
  <!-- Header -->
  <header class="submission-header">
    <h2>Grading: John Doe (#12345)</h2>
    <div class="current-score">
      <span class="score">45.5</span> / <span class="max">50</span> points
      <span class="percentage">(91%)</span>
    </div>
  </header>

  <!-- Grading Form -->
  <form id="grading-form">
    <!-- Question 1 -->
    <section class="question-section">
      <h3>Question 1: Problem Solving (25 points)</h3>
      <div class="question-total">
        Awarded: <span class="awarded-total">18.5</span> / 25
      </div>

      <!-- Criterion 1 -->
      <div class="criterion-grading">
        <label>
          <strong>Correctness</strong> (10 points)
          <p class="criterion-desc">Solution is logically correct</p>
        </label>
        <div class="points-input">
          <input
            type="number"
            name="criterion_1_points"
            min="0"
            max="10"
            step="0.5"
            data-criterion-id="1"
            required>
          <span class="max-points">/ 10</span>
        </div>
        <textarea
          name="criterion_1_feedback"
          placeholder="Feedback (optional)"
          rows="2"></textarea>
        <div class="visual-score">
          <div class="score-bar" style="width: 85%"></div>
        </div>
      </div>

      <!-- Criterion 2 -->
      <div class="criterion-grading">
        <!-- Similar structure -->
      </div>
    </section>

    <!-- Question 2 -->
    <section class="question-section">
      <!-- Similar structure -->
    </section>

    <!-- Actions -->
    <div class="grading-actions">
      <button type="button" class="btn-draft">Save Draft</button>
      <button type="submit" class="btn-complete">Mark Complete</button>
      <a href="/submissions" class="btn-cancel">Cancel</a>
    </div>
  </form>
</div>
```

**JavaScript Logic** (`static/js/grading.js`):
- [ ] Load scheme structure via API
- [ ] Generate form dynamically from JSON
- [ ] Real-time score calculation
- [ ] Auto-save draft every 60 seconds
- [ ] Validation: all criteria have points before complete
- [ ] AJAX submission
- [ ] Navigate to next submission on success

**API Integration**:
- Load scheme: `GET /api/schemes/<id>`
- Load submission: `GET /api/grading/submissions/<id>`
- Save draft: `POST /api/grading/evaluations` (partial)
- Complete: `POST /api/grading/evaluations` + `PATCH /api/grading/submissions/<id>`

---

### 3.2 Grading Workflow Integration (3-4 hours)

#### Tasks:
- [ ] **Update Job Details Page**
  - Add "Grade Submissions" button
  - Show scheme name (if selected)
  - Link to grading interface

- [ ] **Submission List View**
  - Add "Grading Status" column
    - Not Started
    - In Progress (draft saved)
    - Completed
  - Add "Grade" action button per submission
  - Filter by grading status

- [ ] **Bulk Grading**
  - Select multiple submissions
  - Open grading interface with next/previous navigation
  - Progress tracker (5 of 20 graded)

- [ ] **Grading History**
  - Show who graded each submission
  - Show grading date/time
  - Allow re-opening completed grades (with warning)

**Files to Modify**:
- `templates/job_details.html`: Add grading workflow links
- `templates/submissions_list.html`: Add status and actions
- `routes/submissions.py`: Add grading status endpoint

---

### 3.3 Mobile-Responsive Grading (1-2 hours)

#### Features:
- [ ] **Responsive Layout**
  - Stack criterion inputs on mobile
  - Sticky header with total score
  - Collapsible question sections
  - Touch-friendly input sizes

- [ ] **Mobile Optimizations**
  - Swipe to next/previous submission
  - Tap to expand/collapse sections
  - Large touch targets for buttons
  - Auto-hide keyboard on score input

**CSS Media Queries**:
```css
@media (max-width: 768px) {
  .criterion-grading {
    flex-direction: column;
  }

  .points-input input {
    font-size: 18px; /* Touch-friendly */
    padding: 12px;
  }

  .question-section {
    padding: 10px;
  }
}
```

---

## Phase 4: Integration, Testing & Documentation (8-10 hours)

### 4.1 End-to-End Integration (3-4 hours)

#### Tasks:
- [ ] **Wire Up Complete Flow**
  - Job Creation → Select Scheme
  - Submissions → Grade with Scheme
  - Export → Include scheme-based grades

- [ ] **Data Migration** (if needed)
  - Convert existing SavedMarkingScheme references
  - Link old jobs to new schemes
  - Preserve historical data

- [ ] **Bridge Old & New Systems**
  - Allow jobs to use either SavedMarkingScheme OR GradingScheme
  - Display appropriate UI based on scheme type
  - Deprecate old system gracefully

**Files to Modify**:
- `templates/create_job.html`: Add scheme selection dropdown
- `routes/jobs.py`: Link jobs to schemes
- `routes/export.py`: Include scheme data in exports

---

### 4.2 Testing (3-4 hours)

#### Backend Tests:
- [ ] **Scheme CRUD Tests** (`tests/integration/test_schemes_routes.py`)
  - Test all endpoints
  - Test validation errors
  - Test concurrent updates
  - Test deletion constraints

- [ ] **Grading Flow Tests** (`tests/integration/test_grading_flow.py`)
  - Create scheme → grade submission → export
  - Test point calculations
  - Test validation rules
  - Test statistics accuracy

- [ ] **Edge Cases**
  - Scheme with 0 points
  - Empty questions/criteria
  - Very large schemes (100+ criteria)
  - Concurrent grading of same submission

#### Frontend Tests:
- [ ] **Manual Testing Checklist**
  - Create scheme with 3 questions, 2 criteria each
  - Validate point totals match
  - Grade 5 submissions
  - Export grades to CSV
  - Clone scheme
  - Delete unused scheme
  - View statistics

- [ ] **Browser Compatibility**
  - Test in Chrome, Firefox, Safari
  - Test on mobile devices
  - Test with keyboard-only navigation
  - Test with screen reader

**Test Commands**:
```bash
# Run backend tests
pytest tests/integration/test_schemes_routes.py -v
pytest tests/integration/test_grading_flow.py -v

# Run all model tests
pytest tests/unit/test_scheme_models.py -v

# Check coverage
pytest --cov=routes.schemes --cov-report=html
```

---

### 4.3 Documentation (2-3 hours)

#### User Documentation:
- [ ] **User Guide** (`docs/user-guide-grading-schemes.md`)
  - How to create a grading scheme
  - How to grade submissions
  - How to view statistics
  - Screenshots of each step

- [ ] **Video Tutorial** (optional)
  - 5-minute walkthrough
  - Create scheme → grade submission → export

- [ ] **FAQ Section**
  - Can I edit a scheme after use?
  - What happens if I delete a scheme?
  - How do I regrade a submission?

#### Developer Documentation:
- [ ] **API Documentation** (`docs/api-grading-schemes.md`)
  - All endpoints with request/response examples
  - Error codes and meanings
  - Rate limits and pagination

- [ ] **Database Schema** (`docs/schema-grading.md`)
  - ER diagram of scheme tables
  - Relationship explanations
  - Indexing strategy

- [ ] **Code Comments**
  - Docstrings for all API functions
  - Complex logic explanations
  - TODO markers for future enhancements

**Template Structure**:
```markdown
# API Endpoint: POST /api/schemes

## Description
Creates a new grading scheme.

## Request
```json
{
  "name": "Midterm Rubric",
  "description": "Grading for CS101 Midterm",
  "total_points": 50
}
```

## Response (201 Created)
```json
{
  "id": 23,
  "name": "Midterm Rubric",
  "description": "Grading for CS101 Midterm",
  "total_points": 50,
  "created_at": "2025-11-15T10:30:00Z"
}
```

## Errors
- 400: Invalid input (missing name, negative points)
- 409: Scheme name already exists
```

---

## Phase 5: Optional Enhancements (Future Work)

### 5.1 Advanced Features (Backlog)
- [ ] **Scheme Templates**
  - Pre-built templates for common use cases
  - "Essay Rubric", "Programming Assignment", "Lab Report"
  - One-click copy and customize

- [ ] **AI-Assisted Grading** (future)
  - Auto-suggest points based on submission content
  - Feedback templates
  - Consistency checks across submissions

- [ ] **Peer Review Mode**
  - Students grade each other using same scheme
  - Anonymous submissions
  - Calibration exercises

- [ ] **Rubric Alignment**
  - Map criteria to learning objectives
  - Generate standards-based reports
  - Accreditation support

### 5.2 Performance Optimizations
- [ ] **Caching**
  - Cache scheme structures (Redis)
  - Cache statistics for large jobs
  - Invalidate on scheme updates

- [ ] **Batch Operations**
  - Bulk grade multiple submissions
  - Batch export to Excel
  - Parallel grading (multiple graders)

- [ ] **Database Indexing**
  - Index `display_order` fields
  - Index `is_deleted` for faster filtering
  - Composite index on (scheme_id, display_order)

---

## Implementation Checklist

### Phase 1: Backend APIs ✅
- [ ] 1.1 Core Scheme Endpoints (4h)
- [ ] 1.2 Question Management (4h)
- [ ] 1.3 Criteria Management (4h)
- [ ] 1.4 Utilities (2-3h)

### Phase 2: Scheme Builder UI ✅
- [ ] 2.1 Management Dashboard (4h)
- [ ] 2.2 Builder Form (6-8h)
- [ ] 2.3 Validation & UX (3-4h)
- [ ] 2.4 Statistics Modal (2-3h)

### Phase 3: Grading Interface ✅
- [ ] 3.1 Grading Page (6-8h)
- [ ] 3.2 Workflow Integration (3-4h)
- [ ] 3.3 Mobile Responsive (1-2h)

### Phase 4: Testing & Docs ✅
- [ ] 4.1 Integration (3-4h)
- [ ] 4.2 Testing (3-4h)
- [ ] 4.3 Documentation (2-3h)

**Total Estimated Time**: 40-50 hours
**Recommended Schedule**: 5-7 days (8 hours/day)

---

## Risk Mitigation

### Technical Risks:
1. **Point Calculation Bugs**
   - Mitigation: Comprehensive unit tests, validate on every update
   - Detection: Automated totals checks in API responses

2. **Concurrent Editing**
   - Mitigation: Optimistic locking, version numbers
   - Detection: 409 Conflict errors with retry logic

3. **Performance with Large Schemes**
   - Mitigation: Pagination, lazy loading, caching
   - Detection: Load testing with 1000+ criteria

### UX Risks:
1. **Complex UI Overwhelms Users**
   - Mitigation: Progressive disclosure, good defaults, tooltips
   - Detection: User testing, feedback surveys

2. **Mobile Usability Issues**
   - Mitigation: Mobile-first design, touch targets
   - Detection: Device testing, analytics

---

## Success Metrics

### Completion Criteria:
- ✅ All API endpoints functional and tested
- ✅ Scheme builder creates valid schemes
- ✅ Grading interface calculates scores correctly
- ✅ Statistics display accurate data
- ✅ End-to-end flow works (create → grade → export)
- ✅ 90%+ test coverage on new code
- ✅ Documentation complete

### Performance Targets:
- Scheme creation: < 2 seconds
- Load grading interface: < 1 second
- Calculate statistics: < 3 seconds (for 100 submissions)
- API response time: < 200ms (p95)

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up development branch**: `feature/structured-grading-ui`
3. **Start with Phase 1.1**: Core scheme endpoints
4. **Test incrementally**: Don't wait until end
5. **Deploy to staging**: Test with real data
6. **Gather feedback**: Iterate on UX

---

## Appendix: File Structure

```
grading-app/
├── routes/
│   ├── schemes.py          # NEW: All scheme management endpoints
│   ├── grading.py          # EXISTS: Add scheme integration
│   └── export.py           # EXISTS: Add scheme data to exports
├── templates/
│   ├── schemes/
│   │   ├── index.html      # NEW: Scheme list dashboard
│   │   ├── builder.html    # NEW: Scheme creation form
│   │   └── statistics.html # NEW: Analytics modal
│   └── grading/
│       └── grade_submission.html  # NEW: Grading interface
├── static/
│   ├── js/
│   │   ├── scheme-builder.js  # NEW: Builder logic
│   │   └── grading.js         # NEW: Grading interface logic
│   └── css/
│       └── schemes.css        # NEW: Scheme-specific styles
├── tests/
│   ├── integration/
│   │   ├── test_schemes_routes.py  # NEW: API tests
│   │   └── test_grading_flow.py    # NEW: E2E tests
│   └── unit/
│       └── test_scheme_models.py   # EXISTS: Already complete
├── docs/
│   ├── user-guide-grading-schemes.md   # NEW
│   └── api-grading-schemes.md          # NEW
└── utils/
    ├── scheme_calculator.py  # EXISTS: Already complete
    └── scheme_validator.py   # EXISTS: Already complete
```

---

**Questions or concerns?** Review each phase and adjust estimates based on team capacity and priorities.
