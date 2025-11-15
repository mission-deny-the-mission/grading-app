# Data Model: OCR and Image Content Evaluation

**Date**: 2025-11-14
**Branch**: `001-ocr-image-grading`

## Overview

This document defines the database schema and entity relationships for image submission processing, OCR text extraction, image quality assessment, and automated content validation. The design extends the existing data model (GradingJob, Submission, MarkingScheme) to support image-specific functionality.

---

## Entity Relationship Diagram

```
GradingJob (existing)
    |
    ├── Submission (existing)
    |       |
    |       └── ImageSubmission (NEW)
    |               ├── ExtractedContent (NEW)
    |               ├── ImageQualityMetrics (NEW)
    |               └── ImageValidationResult (NEW)
    |
    └── MarkingScheme (existing)
            └── ImageValidationCriteria (NEW)
```

---

## 1. ImageSubmission

**Purpose**: Extends submission tracking for image files (screenshots, diagrams) submitted by students.

### Schema

```sql
CREATE TABLE image_submissions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Relationship to existing submission
    submission_id VARCHAR(36) NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,

    -- File storage (UUID-based two-level hashing)
    storage_path VARCHAR(500) NOT NULL,  -- e.g., "/uploads/F3/B1/uuid.png"
    file_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    -- File metadata
    original_filename VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,  -- image/png, image/jpeg, etc.
    file_extension VARCHAR(10) NOT NULL,  -- png, jpg, jpeg, gif, webp, bmp

    -- Image properties
    width_pixels INTEGER,
    height_pixels INTEGER,
    aspect_ratio DECIMAL(5,2),  -- width/height
    file_hash VARCHAR(64),  -- SHA-256 hash for duplicate detection

    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'uploaded',
    -- Status values: uploaded, queued, processing, completed, failed
    ocr_started_at TIMESTAMP,
    ocr_completed_at TIMESTAMP,
    error_message TEXT,

    -- Validation status
    passes_quality_check BOOLEAN,
    requires_manual_review BOOLEAN DEFAULT FALSE,

    -- Indexes
    INDEX idx_submission_id (submission_id),
    INDEX idx_processing_status (processing_status),
    INDEX idx_file_uuid (file_uuid),
    INDEX idx_created_at (created_at)
);
```

### Attributes

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | VARCHAR(36) | No | Primary key (UUID) |
| `submission_id` | VARCHAR(36) | No | Foreign key to submissions table |
| `storage_path` | VARCHAR(500) | No | File path using two-level UUID hashing |
| `file_uuid` | UUID | No | Unique identifier for file storage |
| `original_filename` | VARCHAR(255) | No | Student's original filename |
| `file_size_bytes` | INTEGER | No | File size in bytes (max 50MB per FR-017) |
| `mime_type` | VARCHAR(100) | No | Validated MIME type (image/*) |
| `file_extension` | VARCHAR(10) | No | png, jpg, jpeg, gif, webp, bmp |
| `width_pixels` | INTEGER | Yes | Image width in pixels |
| `height_pixels` | INTEGER | Yes | Image height in pixels |
| `aspect_ratio` | DECIMAL(5,2) | Yes | Width/height ratio |
| `file_hash` | VARCHAR(64) | Yes | SHA-256 hash for duplicate detection |
| `processing_status` | VARCHAR(50) | No | Current processing state |
| `ocr_started_at` | TIMESTAMP | Yes | OCR processing start time |
| `ocr_completed_at` | TIMESTAMP | Yes | OCR processing completion time |
| `error_message` | TEXT | Yes | Error details if processing failed |
| `passes_quality_check` | BOOLEAN | Yes | Result of quality assessment |
| `requires_manual_review` | BOOLEAN | No | Flag for manual grader attention |

### Processing Status Values

- `uploaded`: Image uploaded and validated, not yet queued
- `queued`: Added to Celery task queue for processing
- `processing`: OCR and quality assessment in progress
- `completed`: All processing finished successfully
- `failed`: Processing encountered unrecoverable error

### Relationships

- **Parent**: `Submission` (many-to-one) - Links to existing submission record
- **Children**:
  - `ExtractedContent` (one-to-one) - OCR results
  - `ImageQualityMetrics` (one-to-one) - Quality assessment
  - `ImageValidationResult` (one-to-many) - Validation outcomes

### Validation Rules

- `file_size_bytes` ≤ 52,428,800 (50MB per FR-017)
- `mime_type` ∈ {'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/bmp'}
- `file_extension` ∈ {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
- `storage_path` must match pattern: `/uploads/[A-F0-9]{2}/[A-F0-9]{2}/[uuid].[ext]`
- `processing_status` ∈ {'uploaded', 'queued', 'processing', 'completed', 'failed'}

---

## 2. ExtractedContent

**Purpose**: Stores OCR-extracted text and metadata from image submissions.

### Schema

```sql
CREATE TABLE extracted_content (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Relationship
    image_submission_id VARCHAR(36) NOT NULL UNIQUE REFERENCES image_submissions(id) ON DELETE CASCADE,

    -- OCR results
    extracted_text TEXT,  -- Full extracted text content
    text_length INTEGER,  -- Character count
    line_count INTEGER,  -- Number of text lines detected

    -- OCR metadata
    ocr_provider VARCHAR(50) NOT NULL,  -- azure_vision, tesseract, google_vision
    ocr_model VARCHAR(100),  -- Model version if applicable
    confidence_score DECIMAL(5,4),  -- Overall confidence (0.0000-1.0000)
    processing_time_ms INTEGER,  -- OCR processing duration in milliseconds

    -- Structured data
    text_regions JSON,
    -- Format: [{"text": "...", "confidence": 0.95, "bounding_box": [x,y,w,h]}, ...]

    -- Usage tracking
    api_cost_usd DECIMAL(10,6),  -- Cost of API call (if using cloud OCR)

    -- Indexes
    INDEX idx_image_submission_id (image_submission_id),
    INDEX idx_confidence_score (confidence_score),
    INDEX idx_ocr_provider (ocr_provider)
);
```

### Attributes

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | VARCHAR(36) | No | Primary key (UUID) |
| `image_submission_id` | VARCHAR(36) | No | Foreign key to image_submissions (unique: one-to-one) |
| `extracted_text` | TEXT | Yes | Full OCR-extracted text content |
| `text_length` | INTEGER | Yes | Character count of extracted text |
| `line_count` | INTEGER | Yes | Number of text lines detected |
| `ocr_provider` | VARCHAR(50) | No | OCR service used (azure_vision, tesseract, google_vision) |
| `ocr_model` | VARCHAR(100) | Yes | OCR model version/identifier |
| `confidence_score` | DECIMAL(5,4) | Yes | Overall confidence (0.0000-1.0000, 90%+ per SC-002) |
| `processing_time_ms` | INTEGER | Yes | OCR processing duration in milliseconds |
| `text_regions` | JSON | Yes | Structured text regions with bounding boxes |
| `api_cost_usd` | DECIMAL(10,6) | Yes | API call cost for cloud OCR services |

### Text Regions JSON Schema

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "text": {"type": "string"},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "bounding_box": {
        "type": "array",
        "items": {"type": "integer"},
        "minItems": 4,
        "maxItems": 4,
        "description": "[x, y, width, height] in pixels"
      },
      "line_number": {"type": "integer"}
    },
    "required": ["text", "confidence"]
  }
}
```

### Relationships

- **Parent**: `ImageSubmission` (one-to-one)

### Validation Rules

- `confidence_score` ∈ [0.0000, 1.0000]
- `ocr_provider` ∈ {'azure_vision', 'tesseract', 'google_vision', 'gemini_vision'}
- `processing_time_ms` < 30,000 (30-second budget per SC-003)
- `text_regions` must conform to JSON schema if present

---

## 3. ImageQualityMetrics

**Purpose**: Stores automated quality assessment results for image submissions.

### Schema

```sql
CREATE TABLE image_quality_metrics (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Relationship
    image_submission_id VARCHAR(36) NOT NULL UNIQUE REFERENCES image_submissions(id) ON DELETE CASCADE,

    -- Overall assessment
    overall_quality VARCHAR(20) NOT NULL,  -- excellent, good, poor, rejected
    passes_quality_check BOOLEAN NOT NULL DEFAULT FALSE,

    -- Blur detection (Laplacian variance)
    blur_score DECIMAL(10,2),  -- Higher = sharper
    is_blurry BOOLEAN,
    blur_threshold DECIMAL(10,2),  -- Threshold used for classification

    -- Resolution metrics
    meets_min_resolution BOOLEAN,
    min_width_required INTEGER,
    min_height_required INTEGER,

    -- Completeness assessment
    edge_density_top DECIMAL(5,2),  -- Edge density percentage in top border
    edge_density_bottom DECIMAL(5,2),
    edge_density_left DECIMAL(5,2),
    edge_density_right DECIMAL(5,2),
    avg_edge_density DECIMAL(5,2),
    max_edge_density DECIMAL(5,2),
    likely_cropped BOOLEAN,

    -- Quality issues (array of issue descriptions)
    issues JSON,
    -- Format: ["Image is blurry (score: 45.23)", "Resolution too low (800x600)"]

    -- Processing metadata
    assessment_duration_ms INTEGER,  -- Quality assessment duration

    -- Indexes
    INDEX idx_image_submission_id (image_submission_id),
    INDEX idx_overall_quality (overall_quality),
    INDEX idx_passes_quality_check (passes_quality_check)
);
```

### Attributes

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | VARCHAR(36) | No | Primary key (UUID) |
| `image_submission_id` | VARCHAR(36) | No | Foreign key to image_submissions (unique: one-to-one) |
| `overall_quality` | VARCHAR(20) | No | excellent, good, poor, rejected |
| `passes_quality_check` | BOOLEAN | No | Whether image meets minimum quality standards |
| `blur_score` | DECIMAL(10,2) | Yes | Laplacian variance (higher = sharper) |
| `is_blurry` | BOOLEAN | Yes | Whether image fails blur threshold |
| `blur_threshold` | DECIMAL(10,2) | Yes | Threshold used (default: 100.0) |
| `meets_min_resolution` | BOOLEAN | Yes | Whether image meets minimum resolution |
| `min_width_required` | INTEGER | Yes | Minimum width requirement applied |
| `min_height_required` | INTEGER | Yes | Minimum height requirement applied |
| `edge_density_*` | DECIMAL(5,2) | Yes | Edge density percentages in borders |
| `likely_cropped` | BOOLEAN | Yes | Whether image appears improperly cropped |
| `issues` | JSON | Yes | Array of quality issue descriptions |
| `assessment_duration_ms` | INTEGER | Yes | Processing time in milliseconds |

### Quality Classification

| Overall Quality | Criteria | Action |
|----------------|----------|--------|
| `excellent` | No issues, high blur score | Accept, proceed to grading |
| `good` | Minor issues, acceptable blur | Accept with note |
| `poor` | Multiple issues or low blur score | Flag for manual review |
| `rejected` | Critical issues (very blurry, too small) | Request re-submission |

### Relationships

- **Parent**: `ImageSubmission` (one-to-one)

### Validation Rules

- `overall_quality` ∈ {'excellent', 'good', 'poor', 'rejected'}
- `blur_score` ≥ 0 (typically 0-500 range)
- `blur_threshold` ≥ 0 (default: 100.0)
- `edge_density_*` ∈ [0.00, 100.00] (percentage)
- `issues` must be valid JSON array of strings

---

## 4. ImageValidationCriteria

**Purpose**: Defines expected image content patterns for automated validation (extends marking schemes).

### Schema

```sql
CREATE TABLE image_validation_criteria (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Relationship to marking scheme
    marking_scheme_id VARCHAR(36) REFERENCES saved_marking_schemes(id) ON DELETE CASCADE,

    -- Criteria metadata
    criteria_name VARCHAR(255) NOT NULL,
    criteria_description TEXT,
    criteria_type VARCHAR(50) NOT NULL,
    -- Types: text_pattern, ui_element, visual_state, layout

    -- Validation rules
    validation_rules JSON NOT NULL,
    -- Format depends on criteria_type (see schemas below)

    -- Grading impact
    points_value DECIMAL(5,2),  -- Points awarded if criteria met
    is_required BOOLEAN DEFAULT FALSE,  -- Whether failure blocks submission
    weight DECIMAL(5,4),  -- Weight in overall grade (0.0000-1.0000)

    -- VLM configuration (if using Vision Language Model)
    use_vlm BOOLEAN DEFAULT FALSE,
    vlm_provider VARCHAR(50),  -- gemini, claude, openai
    vlm_prompt TEXT,  -- Custom prompt for VLM validation

    -- Indexes
    INDEX idx_marking_scheme_id (marking_scheme_id),
    INDEX idx_criteria_type (criteria_type)
);
```

### Validation Rules JSON Schemas

**Text Pattern Criteria**:
```json
{
  "type": "text_pattern",
  "patterns": [
    {
      "pattern": "Server started on port \\d+",
      "regex": true,
      "case_sensitive": false,
      "required": true
    }
  ]
}
```

**UI Element Criteria** (VLM-based):
```json
{
  "type": "ui_element",
  "elements": [
    {
      "element_type": "button",
      "label": "Submit",
      "required": true
    },
    {
      "element_type": "input",
      "name": "username",
      "required": true
    }
  ]
}
```

**Visual State Criteria** (VLM-based):
```json
{
  "type": "visual_state",
  "states": [
    {
      "element": "submit_button",
      "expected_state": "disabled",
      "required": true
    }
  ]
}
```

**Layout Criteria** (VLM-based):
```json
{
  "type": "layout",
  "requirements": [
    {
      "description": "Form elements vertically stacked",
      "validation_prompt": "Check if form inputs are arranged vertically with consistent spacing"
    }
  ]
}
```

### Attributes

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | VARCHAR(36) | No | Primary key (UUID) |
| `marking_scheme_id` | VARCHAR(36) | Yes | Optional link to saved marking scheme |
| `criteria_name` | VARCHAR(255) | No | Human-readable criteria name |
| `criteria_description` | TEXT | Yes | Detailed explanation of criteria |
| `criteria_type` | VARCHAR(50) | No | text_pattern, ui_element, visual_state, layout |
| `validation_rules` | JSON | No | Type-specific validation configuration |
| `points_value` | DECIMAL(5,2) | Yes | Points awarded when met |
| `is_required` | BOOLEAN | No | Whether failure blocks grading |
| `weight` | DECIMAL(5,4) | Yes | Weight in overall grade (0-1) |
| `use_vlm` | BOOLEAN | No | Whether to use VLM for validation |
| `vlm_provider` | VARCHAR(50) | Yes | gemini, claude, openai |
| `vlm_prompt` | TEXT | Yes | Custom VLM validation prompt |

### Relationships

- **Parent**: `SavedMarkingScheme` (many-to-one, optional)
- **Children**: `ImageValidationResult` (one-to-many)

### Validation Rules

- `criteria_type` ∈ {'text_pattern', 'ui_element', 'visual_state', 'layout'}
- `weight` ∈ [0.0000, 1.0000] if present
- `vlm_provider` ∈ {'gemini', 'claude', 'openai'} if `use_vlm = true`
- `validation_rules` must conform to type-specific JSON schema

---

## 5. ImageValidationResult

**Purpose**: Stores outcomes of applying validation criteria to image submissions.

### Schema

```sql
CREATE TABLE image_validation_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Relationships
    image_submission_id VARCHAR(36) NOT NULL REFERENCES image_submissions(id) ON DELETE CASCADE,
    criteria_id VARCHAR(36) NOT NULL REFERENCES image_validation_criteria(id) ON DELETE CASCADE,

    -- Validation outcome
    validation_status VARCHAR(50) NOT NULL,  -- passed, failed, partial, error
    passes_criteria BOOLEAN NOT NULL,
    confidence_score DECIMAL(5,4),  -- 0.0000-1.0000

    -- Results
    detected_elements JSON,  -- Elements/patterns found
    validation_message TEXT,  -- Human-readable result description
    points_awarded DECIMAL(5,2),

    -- Processing metadata
    processing_method VARCHAR(50) NOT NULL,  -- ocr_text_match, vlm_analysis
    vlm_provider VARCHAR(50),  -- If VLM used
    vlm_model VARCHAR(100),  -- Model version
    vlm_response TEXT,  -- Full VLM analysis response
    processing_duration_ms INTEGER,
    api_cost_usd DECIMAL(10,6),

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Indexes
    INDEX idx_image_submission_id (image_submission_id),
    INDEX idx_criteria_id (criteria_id),
    INDEX idx_validation_status (validation_status),
    INDEX idx_passes_criteria (passes_criteria)
);
```

### Attributes

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | VARCHAR(36) | No | Primary key (UUID) |
| `image_submission_id` | VARCHAR(36) | No | Foreign key to image_submissions |
| `criteria_id` | VARCHAR(36) | No | Foreign key to image_validation_criteria |
| `validation_status` | VARCHAR(50) | No | passed, failed, partial, error |
| `passes_criteria` | BOOLEAN | No | Whether submission meets criteria |
| `confidence_score` | DECIMAL(5,4) | Yes | Validation confidence (0-1) |
| `detected_elements` | JSON | Yes | Elements/patterns found during validation |
| `validation_message` | TEXT | Yes | Human-readable result description |
| `points_awarded` | DECIMAL(5,2) | Yes | Points given for this criteria |
| `processing_method` | VARCHAR(50) | No | ocr_text_match, vlm_analysis |
| `vlm_provider` | VARCHAR(50) | Yes | VLM service if used |
| `vlm_model` | VARCHAR(100) | Yes | VLM model version |
| `vlm_response` | TEXT | Yes | Full VLM analysis |
| `processing_duration_ms` | INTEGER | Yes | Processing time |
| `api_cost_usd` | DECIMAL(10,6) | Yes | API cost if applicable |
| `error_message` | TEXT | Yes | Error details if validation failed |
| `retry_count` | INTEGER | No | Number of retry attempts |

### Validation Status Values

- `passed`: Criteria fully met with high confidence
- `failed`: Criteria not met
- `partial`: Some aspects met, others not (for multi-part criteria)
- `error`: Validation process encountered error

### Relationships

- **Parents**:
  - `ImageSubmission` (many-to-one)
  - `ImageValidationCriteria` (many-to-one)

### Validation Rules

- `validation_status` ∈ {'passed', 'failed', 'partial', 'error'}
- `confidence_score` ∈ [0.0000, 1.0000] if present
- `processing_method` ∈ {'ocr_text_match', 'vlm_analysis'}
- `vlm_provider` ∈ {'gemini', 'claude', 'openai'} if VLM used

---

## Database Migrations

### Migration Plan

**Migration 001: Create ImageSubmission Table**
- Add `image_submissions` table
- Add foreign key constraint to `submissions`
- Create indexes

**Migration 002: Create ExtractedContent Table**
- Add `extracted_content` table
- Add foreign key constraint to `image_submissions`
- Create indexes

**Migration 003: Create ImageQualityMetrics Table**
- Add `image_quality_metrics` table
- Add foreign key constraint to `image_submissions`
- Create indexes

**Migration 004: Create ImageValidationCriteria Table**
- Add `image_validation_criteria` table
- Add optional foreign key to `saved_marking_schemes`
- Create indexes

**Migration 005: Create ImageValidationResult Table**
- Add `image_validation_results` table
- Add foreign key constraints
- Create indexes

### Rollback Strategy

All migrations are reversible:
- Each migration includes `DROP TABLE IF EXISTS` statements
- Foreign key constraints can be safely dropped
- Indexes automatically removed with table drops

### Data Integrity Constraints

**Referential Integrity**:
- ON DELETE CASCADE for child tables (ExtractedContent, ImageQualityMetrics follow parent ImageSubmission)
- ON DELETE CASCADE for ImageValidationResult (follows parent ImageSubmission)
- Foreign key to SavedMarkingScheme is optional (nullable)

**Check Constraints**:
```sql
ALTER TABLE image_submissions
  ADD CONSTRAINT chk_file_size CHECK (file_size_bytes > 0 AND file_size_bytes <= 52428800),
  ADD CONSTRAINT chk_processing_status CHECK (processing_status IN ('uploaded', 'queued', 'processing', 'completed', 'failed'));

ALTER TABLE extracted_content
  ADD CONSTRAINT chk_confidence_score CHECK (confidence_score >= 0.0000 AND confidence_score <= 1.0000);

ALTER TABLE image_quality_metrics
  ADD CONSTRAINT chk_overall_quality CHECK (overall_quality IN ('excellent', 'good', 'poor', 'rejected'));

ALTER TABLE image_validation_results
  ADD CONSTRAINT chk_validation_status CHECK (validation_status IN ('passed', 'failed', 'partial', 'error'));
```

---

## SQLAlchemy Model Classes

### ImageSubmission Model

```python
class ImageSubmission(db.Model):
    """Model for image submissions (screenshots, diagrams)."""

    __tablename__ = "image_submissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    submission_id = db.Column(db.String(36), db.ForeignKey("submissions.id"), nullable=False)

    # File storage
    storage_path = db.Column(db.String(500), nullable=False)
    file_uuid = db.Column(db.String(36), unique=True, nullable=False)

    # File metadata
    original_filename = db.Column(db.String(255), nullable=False)
    file_size_bytes = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_extension = db.Column(db.String(10), nullable=False)

    # Image properties
    width_pixels = db.Column(db.Integer)
    height_pixels = db.Column(db.Integer)
    aspect_ratio = db.Column(db.Numeric(5, 2))
    file_hash = db.Column(db.String(64))

    # Processing status
    processing_status = db.Column(db.String(50), default="uploaded")
    ocr_started_at = db.Column(db.DateTime)
    ocr_completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

    # Validation
    passes_quality_check = db.Column(db.Boolean)
    requires_manual_review = db.Column(db.Boolean, default=False)

    # Relationships
    submission = db.relationship("Submission", backref="image_submissions", lazy=True)
    extracted_content = db.relationship(
        "ExtractedContent", backref="image_submission", uselist=False, cascade="all, delete-orphan"
    )
    quality_metrics = db.relationship(
        "ImageQualityMetrics", backref="image_submission", uselist=False, cascade="all, delete-orphan"
    )
    validation_results = db.relationship(
        "ImageValidationResult", backref="image_submission", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "storage_path": self.storage_path,
            "file_uuid": self.file_uuid,
            "original_filename": self.original_filename,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "file_extension": self.file_extension,
            "width_pixels": self.width_pixels,
            "height_pixels": self.height_pixels,
            "processing_status": self.processing_status,
            "passes_quality_check": self.passes_quality_check,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

---

## Performance Considerations

### Indexing Strategy

**Primary Indexes**:
- `image_submissions.submission_id` - Most common query pattern (get images for submission)
- `image_submissions.processing_status` - Filter by processing state
- `image_submissions.file_uuid` - Direct file lookups
- `extracted_content.confidence_score` - Filter low-quality OCR results

**Composite Indexes** (if needed at scale):
- `(submission_id, processing_status)` - Fetch pending images for specific submission
- `(processing_status, created_at)` - Queue processing with FIFO ordering

### Query Optimization

**Avoid N+1 Queries**:
```python
# Good: Eager load related data
submissions = db.session.query(ImageSubmission).options(
    joinedload(ImageSubmission.extracted_content),
    joinedload(ImageSubmission.quality_metrics)
).filter(ImageSubmission.submission_id == submission_id).all()

# Bad: N+1 queries
submissions = ImageSubmission.query.filter_by(submission_id=submission_id).all()
for s in submissions:
    content = s.extracted_content  # Separate query for each
    quality = s.quality_metrics   # Another query
```

**Pagination for Large Result Sets**:
```python
# Paginate when fetching many images
page = 1
per_page = 50
images = ImageSubmission.query.filter_by(
    processing_status='completed'
).paginate(page=page, per_page=per_page)
```

### Storage Estimates

**Per Image Submission** (average):
- `image_submissions` row: ~500 bytes
- `extracted_content` row: ~2KB (varies by text length)
- `image_quality_metrics` row: ~500 bytes
- `image_validation_results` rows: ~1KB each (3-5 criteria typical)
- **Total DB**: ~5KB per image
- **File storage**: 5-20MB per image (50MB max)

**1,000 images**:
- Database: ~5MB
- File storage: ~10GB (average 10MB/image)

---

## Summary

This data model extends the existing grading system with comprehensive image processing capabilities:

- ✅ **Integrated Design**: Builds on existing Submission/MarkingScheme patterns
- ✅ **OCR Support**: Stores extracted text with confidence scores and metadata
- ✅ **Quality Assessment**: Automated blur/resolution/completeness checks
- ✅ **Content Validation**: Flexible criteria system supporting OCR and VLM approaches
- ✅ **Audit Trail**: Complete processing history with timestamps and error tracking
- ✅ **Performance Optimized**: Indexes for common queries, file storage on filesystem
- ✅ **FERPA Compliant**: Referential integrity, cascade deletes, data retention support

**Next Steps**: Generate API contracts (Phase 1 continued)
