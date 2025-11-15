# Phase 8: Frontend UI Implementation Plan

**Status**: STARTING
**Date**: 2025-11-15
**Estimated Duration**: 25-30 hours
**Framework**: Flask + Bootstrap 5.3.0 + JavaScript (ES6+)

---

## Overview

Phase 8 builds the user-facing frontend for the structured grading scheme system. Users will manage schemes, apply them to submissions, input grades, and view statistics.

### Key Deliverables

1. **Scheme Management Dashboard** - List, create, edit, delete, clone schemes
2. **Scheme Builder Form** - Dynamic form to create/edit schemes with questions and criteria
3. **Grading Interface** - Apply schemes to submissions and enter grades per criterion
4. **Statistics Display** - Show usage statistics and per-criterion analysis
5. **Workflow Integration** - Connect with existing job creation workflow

---

## Phase 8.1: Scheme Management Dashboard

**Purpose**: Users can discover, manage, and organize grading schemes

### Routes to Implement
- `GET /schemes` - List all schemes with pagination, search, filters
- `GET /schemes/<id>` - View scheme details
- `GET /schemes/create` - Show create scheme form
- `GET /schemes/<id>/edit` - Show edit scheme form
- `POST /schemes/<id>/delete` - Delete scheme (soft delete via API)
- `GET /schemes/<id>/clone` - Clone scheme form
- `POST /schemes/<id>/clone` - Execute clone

### Templates to Create
- `templates/schemes/index.html` - List view with search, pagination
- `templates/schemes/detail.html` - View scheme with questions/criteria
- `templates/schemes/form.html` - Create/edit form
- `templates/schemes/modal_confirm.html` - Confirmation dialogs

### Features
- Pagination with 20 schemes per page
- Search by name (case-insensitive)
- Sort by created date, name, total points
- Quick actions: view, edit, clone, delete
- Display: name, description, # questions, # criteria, total points

---

## Phase 8.2: Scheme Builder Form

**Purpose**: Dynamic, user-friendly form to create/edit grading schemes

### Key Features
- Add/remove questions dynamically
- Add/remove criteria per question
- Real-time point total calculation
- Drag-and-drop reordering (optional enhancement)
- Input validation with immediate feedback
- Save as draft / publish

### JavaScript Components
- `static/js/scheme-builder.js` - Dynamic form management
- `static/js/validation.js` - Real-time validation
- `static/js/calculations.js` - Point total calculations

### Templates
- `templates/schemes/builder.html` - Main builder page with dynamic form

### Form Structure
```
Scheme Details
  - Name (required)
  - Description (optional)
  - Category (optional)

Questions (repeatable)
  - Title (required)
  - Description (optional)
  - Display Order (auto)

  Criteria (per question, repeatable)
    - Name (required)
    - Description (optional)
    - Max Points (required, > 0)
    - Display Order (auto)

Display: Total Points per Question, Total Points for Scheme
```

---

## Phase 8.3: Grading Interface

**Purpose**: Instructors apply schemes to submissions and enter grades

### Routes to Implement
- `GET /submissions/<id>/grade` - Show grading form for submission
- `GET /submissions/<id>/grade?scheme_id=<id>` - Pre-select scheme
- `POST /submissions/<id>/grade` - Save grades

### Templates
- `templates/grading/grade_submission.html` - Grading form

### Features
- Load scheme dynamically
- Display student info, submission details
- Input form per criterion with:
  - Points earned (0 to max_points)
  - Feedback text field
- Live score calculation
- Save draft / Mark complete
- View/edit grades if already graded

### JavaScript
- `static/js/grading.js` - Grading interface logic
- Real-time score calculations
- Form validation before submit

---

## Phase 8.4: Statistics and Export

**Purpose**: Display usage statistics and provide export functionality

### Routes to Implement
- `GET /schemes/<id>/stats` - Statistics page
- `GET /schemes/<id>/export` - Export options modal
- `POST /schemes/<id>/export` - Generate export file

### Templates
- `templates/schemes/statistics.html` - Statistics dashboard
- `templates/schemes/export_modal.html` - Export options

### Features
- Show total submissions graded with scheme
- Per-question average scores
- Per-criterion average scores
- Class statistics (min, max, avg)
- Export formats: CSV, JSON
- Download generated files

---

## Phase 8.5: Workflow Integration

**Purpose**: Connect grading schemes with existing job creation workflow

### Integration Points

1. **Job Creation Form** (`templates/jobs.html` or job creation template)
   - Add dropdown to select grading scheme
   - Optional field (can use existing marking scheme or new scheme)

2. **Submission List** (`templates/image_submissions.html` or similar)
   - Show grading status per submission
   - Quick link to grade submission if scheme selected

3. **Job Details** (`templates/job_detail.html`)
   - Show selected grading scheme
   - Link to grading interface
   - Link to statistics

### Routes
- Modify existing job creation route to accept `scheme_id` parameter
- Modify submission routes to provide scheme context

---

## File Structure

```
templates/
├── schemes/
│   ├── index.html           # List schemes
│   ├── detail.html          # View scheme details
│   ├── form.html            # Create/edit form
│   ├── builder.html         # Dynamic builder
│   ├── statistics.html      # View statistics
│   ├── export_modal.html    # Export options
│   └── modal_confirm.html   # Confirmation dialogs
├── grading/
│   └── grade_submission.html # Grading form
└── (existing templates remain unchanged)

static/
├── js/
│   ├── scheme-builder.js    # Dynamic form management
│   ├── scheme-validator.js  # Form validation
│   ├── scheme-calculations.js # Point calculations
│   ├── grading.js           # Grading interface
│   └── export.js            # Export functionality
└── css/
    └── schemes.css          # Scheme-specific styles (if needed)

routes/
├── schemes_ui.py            # NEW: UI routes for viewing/creating schemes
└── (existing routes remain unchanged)
```

---

## Implementation Order

1. Create basic routes (Flask view functions)
2. Create base templates with navigation
3. Implement dashboard list view
4. Implement scheme detail view
5. Implement scheme builder form
6. Implement grading interface
7. Implement statistics
8. Integrate with existing workflows
9. Test and polish

---

## Technical Decisions

### Framework & Libraries
- **Template Engine**: Jinja2 (Flask default)
- **Styling**: Bootstrap 5.3.0 (existing)
- **Icons**: Font Awesome 6.0.0 (existing)
- **Form Handling**: JavaScript for dynamic forms, Flask for processing
- **AJAX**: Fetch API for async operations

### API Integration
- Frontend templates call backend `/api/schemes/*` endpoints
- All data manipulation through established API
- No direct database access from templates

### Validation
- Client-side (JavaScript) for immediate feedback
- Server-side (Flask/API) for data integrity
- Display errors in user-friendly toast notifications

### State Management
- Session for user preferences (items per page, sort order)
- Local storage for form drafts (optional enhancement)
- Database as source of truth

---

## Success Criteria

- [ ] All 5 phase sections fully implemented
- [ ] All UI components tested in browser
- [ ] Works with all major browsers (Chrome, Firefox, Safari, Edge)
- [ ] Responsive on mobile (Bootstrap grid)
- [ ] 90%+ test coverage for JavaScript components
- [ ] 100% of API endpoints have corresponding UI
- [ ] No console errors or warnings
- [ ] Load times < 2 seconds per page
- [ ] Accessibility: Level AA WCAG compliance

---

## Testing Strategy

### Manual Testing
- Create/edit/delete schemes via UI
- Apply scheme to submission
- Grade submission with multiple criteria
- View statistics
- Export data

### Automated Testing
- Playwright E2E tests for user workflows
- JavaScript unit tests for calculations/validation
- Flask route tests for view functions

---

## Estimated Effort

| Component | Hours | Notes |
|-----------|-------|-------|
| 8.1 Dashboard | 4-5 | List, detail, modals |
| 8.2 Builder | 10-12 | Dynamic form, validation |
| 8.3 Grading | 8-10 | Form, calculations, save |
| 8.4 Statistics | 2-3 | Charts, export |
| 8.5 Integration | 2-3 | Job/submission linking |
| Testing/Polish | 2-3 | Bug fixes, optimization |
| **Total** | **28-36** | ~4-5 days development |

---

## Notes

- This plan assumes all backend APIs are functional (verified in Phase 7 with 42/42 passing tests)
- Frontend will use existing design system (Bootstrap 5 gradient theme)
- No changes to existing templates/routes unless explicitly needed
- New routes in `routes/schemes_ui.py` will be separate from API routes
- All CSS kept minimal to leverage Bootstrap (no large CSS files)
