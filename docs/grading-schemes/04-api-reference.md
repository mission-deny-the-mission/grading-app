# Grading Schemes API Reference

Complete API documentation for the structured grading scheme system.

## Base URL

All API endpoints are prefixed with `/api`

## Authentication

Currently, the API does not require authentication. Future versions will support:
- Session-based authentication
- API key authentication
- JWT tokens

## Response Format

All responses are JSON with consistent structure:

**Success Response**:
```json
{
  "id": "123",
  "name": "Essay Rubric",
  // ... resource data
}
```

**Error Response**:
```json
{
  "error": "Descriptive error message",
  "status": 400
}
```

## Scheme Management Endpoints

### Create Scheme

Create a new grading scheme with questions and criteria.

**Endpoint**: `POST /api/schemes`

**Request Body**:
```json
{
  "name": "Essay Rubric Fall 2025",
  "description": "Rubric for argumentative essays",
  "category": "Essays",
  "questions": [
    {
      "title": "Introduction",
      "description": "Opening section evaluation",
      "display_order": 1,
      "criteria": [
        {
          "name": "Thesis Statement",
          "description": "Clear, arguable claim",
          "max_points": 10,
          "display_order": 1
        },
        {
          "name": "Hook",
          "description": "Engaging opening",
          "max_points": 10,
          "display_order": 2
        }
      ]
    }
  ]
}
```

**Response**: `201 Created`
```json
{
  "id": "abc123",
  "name": "Essay Rubric Fall 2025",
  "description": "Rubric for argumentative essays",
  "category": "Essays",
  "total_possible_points": 20,
  "version_number": 1,
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T10:00:00Z",
  "questions": [/* full question objects */]
}
```

**Validation**:
- `name` (required): Must be unique, non-empty
- `questions` (required): At least one question
- `criteria` (required per question): At least one criterion per question
- `max_points` (required): Must be > 0, supports decimals

**Errors**:
- `400`: Validation error (missing fields, invalid data)
- `409`: Scheme name already exists

---

### List Schemes

Retrieve all grading schemes with pagination.

**Endpoint**: `GET /api/schemes`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 50 | Results per page (max: 100) |
| `search` | string | - | Filter by name (case-insensitive) |
| `include_deleted` | boolean | false | Include soft-deleted schemes |

**Example Request**:
```
GET /api/schemes?page=1&limit=20&search=essay
```

**Response**: `200 OK`
```json
{
  "schemes": [
    {
      "id": "abc123",
      "name": "Essay Rubric Fall 2025",
      "description": "Rubric for argumentative essays",
      "category": "Essays",
      "total_possible_points": 100,
      "version_number": 1,
      "created_at": "2025-11-15T10:00:00Z",
      "questions_count": 4,
      "criteria_count": 12
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  }
}
```

**Note**: Questions and criteria are NOT included in list view for performance. Use GET /api/schemes/{id} for full details.

---

### Get Scheme Details

Retrieve a single scheme with all questions and criteria.

**Endpoint**: `GET /api/schemes/{scheme_id}`

**Response**: `200 OK`
```json
{
  "id": "abc123",
  "name": "Essay Rubric Fall 2025",
  "description": "Rubric for argumentative essays",
  "category": "Essays",
  "total_possible_points": 100,
  "version_number": 1,
  "is_deleted": false,
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T10:00:00Z",
  "questions": [
    {
      "id": "q1",
      "scheme_id": "abc123",
      "title": "Introduction",
      "description": "Opening section",
      "display_order": 1,
      "total_possible_points": 20,
      "criteria": [
        {
          "id": "c1",
          "question_id": "q1",
          "name": "Thesis Statement",
          "description": "Clear, arguable claim",
          "max_points": 10,
          "display_order": 1
        },
        {
          "id": "c2",
          "question_id": "q1",
          "name": "Hook",
          "description": "Engaging opening",
          "max_points": 10,
          "display_order": 2
        }
      ]
    }
  ]
}
```

**Errors**:
- `404`: Scheme not found

---

### Update Scheme

Update scheme metadata (name, description). Questions/criteria are managed separately.

**Endpoint**: `PUT /api/schemes/{scheme_id}`

**Request Body**:
```json
{
  "name": "Essay Rubric Spring 2026",
  "description": "Updated description"
}
```

**Response**: `200 OK`
```json
{
  "id": "abc123",
  "name": "Essay Rubric Spring 2026",
  "description": "Updated description",
  "version_number": 2,  // Auto-incremented
  "updated_at": "2025-11-15T11:00:00Z"
}
```

**Validation**:
- `name` (optional): Must be unique if provided
- Cannot modify: `total_possible_points`, `questions`, `created_at`

**Errors**:
- `400`: Validation error
- `404`: Scheme not found
- `409`: Name conflict

---

### Delete Scheme

Soft delete a scheme (sets `is_deleted=true`).

**Endpoint**: `DELETE /api/schemes/{scheme_id}`

**Response**: `200 OK`
```json
{
  "message": "Scheme deleted successfully",
  "scheme_id": "abc123"
}
```

**Behavior**:
- Soft delete: Scheme marked as deleted but data preserved
- Existing graded submissions unaffected
- Scheme hidden from default list views
- Can be restored manually via database

**Errors**:
- `404`: Scheme not found
- `400`: Already deleted

---

### Clone Scheme

Create a copy of an existing scheme.

**Endpoint**: `POST /api/schemes/{scheme_id}/clone`

**Request Body**:
```json
{
  "name": "Essay Rubric - Section 2",
  "description": "Modified for Section 2"
}
```

**Response**: `201 Created`
```json
{
  "id": "xyz789",  // New scheme ID
  "name": "Essay Rubric - Section 2",
  "description": "Modified for Section 2",
  "total_possible_points": 100,  // Copied from original
  "version_number": 1,
  "questions": [/* cloned questions with new IDs */]
}
```

**Behavior**:
- Deep copy: Questions and criteria are duplicated
- New IDs: All entities get new unique IDs
- Same structure: Point values and ordering preserved
- Independent: Changes to clone don't affect original

**Errors**:
- `404`: Source scheme not found
- `400`: Validation error (name required)
- `409`: Name conflict

---

### Validate Scheme

Check scheme integrity and data consistency.

**Endpoint**: `POST /api/schemes/{scheme_id}/validate`

**Response**: `200 OK`
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "Question 'Conclusion' has only 1 criterion (recommended: 2+)"
  ],
  "summary": {
    "total_questions": 4,
    "total_criteria": 12,
    "total_points": 100,
    "orphaned_criteria": 0,
    "duplicate_criteria_names": 0
  }
}
```

**Validation Checks**:
- ✓ All questions have at least one criterion
- ✓ All criteria have max_points > 0
- ✓ No orphaned criteria (question_id doesn't exist)
- ✓ Total points sum correctly
- ⚠ Questions have reasonable number of criteria (2-5)
- ⚠ Point distributions are balanced

---

### Get Scheme Statistics

Retrieve usage statistics and grade analytics.

**Endpoint**: `GET /api/schemes/{scheme_id}/statistics`

**Response**: `200 OK`
```json
{
  "scheme_id": "abc123",
  "scheme_name": "Essay Rubric Fall 2025",
  "total_submissions": 25,
  "complete_submissions": 23,
  "incomplete_submissions": 2,
  "average_score": 82.3,
  "median_score": 84.0,
  "min_score": 45.5,
  "max_score": 98.0,
  "std_deviation": 12.4,
  "per_question_stats": [
    {
      "question_id": "q1",
      "question_title": "Introduction",
      "max_points": 25,
      "average_score": 21.2,
      "achievement_percentage": 84.8,
      "evaluations_count": 25
    }
  ],
  "per_criterion_stats": [
    {
      "criterion_id": "c1",
      "criterion_name": "Thesis Statement",
      "question_title": "Introduction",
      "max_points": 10,
      "average_score": 9.1,
      "achievement_percentage": 91.0,
      "evaluations_count": 25
    }
  ]
}
```

**Errors**:
- `404`: Scheme not found

---

## Question Management Endpoints

### Add Question to Scheme

Add a new question to an existing scheme.

**Endpoint**: `POST /api/schemes/{scheme_id}/questions`

**Request Body**:
```json
{
  "title": "Methodology",
  "description": "Research methods section",
  "criteria": [
    {
      "name": "Research Design",
      "description": "Appropriate methodology chosen",
      "max_points": 15
    },
    {
      "name": "Data Collection",
      "max_points": 10
    }
  ]
}
```

**Response**: `201 Created`
```json
{
  "id": "q5",
  "scheme_id": "abc123",
  "title": "Methodology",
  "description": "Research methods section",
  "display_order": 5,  // Auto-assigned
  "total_possible_points": 25,
  "criteria": [/* full criterion objects */]
}
```

**Behavior**:
- `display_order` auto-assigned (max + 1)
- Scheme's `total_possible_points` updated automatically
- Scheme's `version_number` incremented

**Errors**:
- `400`: Validation error
- `404`: Scheme not found

---

### Update Question

Update question metadata.

**Endpoint**: `PUT /api/schemes/questions/{question_id}`

**Request Body**:
```json
{
  "title": "Methodology (Updated)",
  "description": "Updated description"
}
```

**Response**: `200 OK`
```json
{
  "id": "q5",
  "title": "Methodology (Updated)",
  "description": "Updated description",
  "updated_at": "2025-11-15T11:00:00Z"
}
```

**Note**: Cannot update criteria via this endpoint. Use criterion endpoints.

---

### Delete Question

Delete a question and all its criteria.

**Endpoint**: `DELETE /api/schemes/questions/{question_id}`

**Response**: `200 OK`
```json
{
  "message": "Question deleted successfully",
  "question_id": "q5"
}
```

**Behavior**:
- Cascade delete: All criteria under this question are deleted
- Reordering: Remaining questions' `display_order` adjusted
- Points update: Scheme's `total_possible_points` recalculated
- Prevention: Cannot delete if evaluations exist

**Errors**:
- `400`: Evaluations exist for this question
- `404`: Question not found

---

### Reorder Questions

Change display order of questions.

**Endpoint**: `POST /api/schemes/questions/reorder`

**Request Body**:
```json
{
  "question_orders": [
    {"question_id": "q3", "display_order": 1},
    {"question_id": "q1", "display_order": 2},
    {"question_id": "q2", "display_order": 3}
  ]
}
```

**Response**: `200 OK`
```json
{
  "message": "Questions reordered successfully",
  "updated_count": 3
}
```

---

## Criterion Management Endpoints

### Add Criterion to Question

Add a criterion to a question.

**Endpoint**: `POST /api/schemes/questions/{question_id}/criteria`

**Request Body**:
```json
{
  "name": "Literature Review",
  "description": "Comprehensive review of relevant literature",
  "max_points": 20
}
```

**Response**: `201 Created`
```json
{
  "id": "c13",
  "question_id": "q5",
  "name": "Literature Review",
  "description": "Comprehensive review of relevant literature",
  "max_points": 20,
  "display_order": 3
}
```

**Validation**:
- `name` (required): Non-empty
- `max_points` (required): > 0, supports decimals
- `display_order`: Auto-assigned if not provided

**Errors**:
- `400`: Validation error (name empty, points ≤ 0)
- `404`: Question not found

---

### Update Criterion

Update criterion details.

**Endpoint**: `PUT /api/schemes/criteria/{criterion_id}`

**Request Body**:
```json
{
  "name": "Literature Review (Updated)",
  "description": "Updated description",
  "max_points": 25
}
```

**Response**: `200 OK`
```json
{
  "id": "c13",
  "name": "Literature Review (Updated)",
  "max_points": 25,
  "updated_at": "2025-11-15T11:00:00Z"
}
```

**Behavior**:
- Point changes trigger recalculation of question and scheme totals
- Existing evaluations unaffected (use original max_points)

---

### Delete Criterion

Delete a criterion.

**Endpoint**: `DELETE /api/schemes/criteria/{criterion_id}`

**Response**: `200 OK`
```json
{
  "message": "Criterion deleted successfully",
  "criterion_id": "c13"
}
```

**Behavior**:
- Reordering: Remaining criteria's `display_order` adjusted
- Points update: Question and scheme totals recalculated
- Prevention: Cannot delete if evaluations exist

**Errors**:
- `400`: Evaluations exist for this criterion
- `404`: Criterion not found

---

### Reorder Criteria

Change display order of criteria within a question.

**Endpoint**: `POST /api/schemes/criteria/reorder`

**Request Body**:
```json
{
  "criterion_orders": [
    {"criterion_id": "c2", "display_order": 1},
    {"criterion_id": "c1", "display_order": 2}
  ]
}
```

**Response**: `200 OK`
```json
{
  "message": "Criteria reordered successfully",
  "updated_count": 2
}
```

---

## Grading Endpoints

### Grade Submission

Apply a scheme and record grades for a submission.

**Endpoint**: `POST /api/submissions/{submission_id}/grade`

**Request Body**:
```json
{
  "scheme_id": "abc123",
  "evaluations": [
    {
      "criterion_id": "c1",
      "points_earned": 9.5,
      "feedback": "Excellent thesis statement"
    },
    {
      "criterion_id": "c2",
      "points_earned": 8.0,
      "feedback": "Good hook, could be stronger"
    }
  ],
  "is_complete": true
}
```

**Response**: `201 Created`
```json
{
  "graded_submission": {
    "id": "gs123",
    "submission_id": "sub456",
    "scheme_id": "abc123",
    "scheme_version": 1,
    "student_id": "STU001",
    "student_name": "John Doe",
    "total_points_earned": 87.5,
    "total_points_possible": 100,
    "percentage_score": 87.5,
    "is_complete": true,
    "graded_by": "prof@example.com",
    "graded_at": "2025-11-15T12:00:00Z",
    "evaluations": [/* full evaluation objects */]
  }
}
```

**Validation**:
- All criteria for the scheme must have evaluations
- `points_earned` must be ≥ 0 and ≤ `max_points`
- Decimal precision preserved

**Concurrency Control**:
- Uses optimistic locking via `evaluation_version`
- If concurrent edit detected, returns `409 Conflict`
- Client must fetch latest version and retry

**Errors**:
- `400`: Validation error (missing criteria, invalid points)
- `404`: Submission or scheme not found
- `409`: Concurrent modification conflict

---

## Export Endpoints

### Export Scheme Results

Export all grading data for a scheme.

**Endpoint**: `GET /api/export/schemes/{scheme_id}`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | json | Export format: "csv" or "json" |
| `include_incomplete` | boolean | true | Include incomplete submissions |

**Example Requests**:
```
GET /api/export/schemes/abc123?format=csv
GET /api/export/schemes/abc123?format=json&include_incomplete=false
```

**CSV Response**: `200 OK` (Content-Type: text/csv)
```csv
Student ID,Student Name,Submission ID,Question,Criterion,Points Earned,Max Points,Percentage,Feedback,Graded By,Graded At
STU001,John Doe,sub456,Introduction,Thesis Statement,9.5,10,95.0%,Excellent thesis,prof@example.com,2025-11-15 12:00:00
...
```

**JSON Response**: `200 OK` (Content-Type: application/json)
```json
{
  "metadata": {
    "scheme_id": "abc123",
    "scheme_name": "Essay Rubric Fall 2025",
    "total_submissions": 25,
    "export_date": "2025-11-15T13:00:00Z"
  },
  "submissions": [/* detailed submission data */]
}
```

**Performance**:
- Optimized for large datasets (100+ students × 50+ criteria)
- CSV generation: ~0.3 seconds for 5,000 evaluations
- JSON generation: ~0.2 seconds for 5,000 evaluations

**Errors**:
- `400`: Invalid format parameter
- `404`: Scheme not found

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Validation error |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Name conflict or concurrent modification |
| 500 | Server Error - Internal error (contact admin) |

## Rate Limiting

Currently no rate limiting. Future versions will implement:
- 100 requests per minute per IP
- 1000 requests per hour per IP
- Higher limits for authenticated users

## Versioning

API version: v1 (current)
Future versions will use URL versioning: `/api/v2/schemes`

## See Also

- [Creating Schemes](01-creating-schemes.md) - User guide for creating schemes
- [Grading Submissions](02-grading-submissions.md) - Grading workflow guide
- [Exporting Results](03-export-analysis.md) - Export and analysis guide
