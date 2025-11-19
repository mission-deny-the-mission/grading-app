# Phase 1: Data Model Design

**Feature**: 005-marking-schema-as-file | **Date**: 2025-11-17
**Objective**: Define database schema, entities, relationships, and validation rules

---

## Existing Entities (Extended)

### MarkingScheme (Extended)

Existing entity from feature 003-structured-grading-scheme. Extensions for save/load/sharing:

```sql
ALTER TABLE marking_scheme ADD COLUMN (
  owner_id UUID FOREIGN KEY REFERENCES user(id),  -- For web version sharing
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  is_shared BOOLEAN DEFAULT false,
  description TEXT  -- Optional long description
);
```

**Attributes**:
- `id` (UUID, PK): Unique identifier
- `owner_id` (UUID FK, nullable): User who created/owns the scheme. Null for backward compat with existing schemes
- `name` (String, NOT NULL): Scheme name (e.g., "Essay Grading Rubric")
- `description` (Text): Long description of scheme purpose/usage
- `created_at` (DateTime): When scheme created
- `updated_at` (DateTime): When last modified
- `is_shared` (Boolean): True if shared with any users/groups
- Existing: criteria (relationship), weightings, etc.

**Relationships**:
- ↔ SchemeCriterion (1:many) - existing
- ↔ SchemeShare (1:many) - new, sharing relationships
- ← User (many:1) - owner of scheme

**Validation Rules**:
- name: required, 1-200 characters, unique per owner
- owner_id: optional (nullable for backward compat)
- description: optional, max 5000 characters

**Key Operations**:
- Export: Serialize to JSON with version + metadata
- Import: Deserialize from JSON, validate schema, create new instance
- Share: Create SchemeShare relationships

---

## New Entities

### SchemeShare

Represents a sharing relationship between a marking scheme and a user or group with specific permissions.

```sql
CREATE TABLE scheme_share (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id UUID NOT NULL FOREIGN KEY REFERENCES marking_scheme(id) ON DELETE CASCADE,
  user_id UUID FOREIGN KEY REFERENCES user(id) ON DELETE CASCADE,
  group_id UUID FOREIGN KEY REFERENCES user_group(id) ON DELETE CASCADE,
  permission VARCHAR(20) NOT NULL CHECK (permission IN ('VIEW_ONLY', 'EDITABLE', 'COPY')),
  shared_by_id UUID NOT NULL FOREIGN KEY REFERENCES user(id),  -- Who granted access
  shared_at TIMESTAMP NOT NULL DEFAULT now(),
  revoked_at TIMESTAMP,
  revoked_by_id UUID FOREIGN KEY REFERENCES user(id),
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  UNIQUE (scheme_id, user_id, group_id),  -- Ensure no duplicate shares (one of user_id or group_id must be non-NULL)
  CHECK ((user_id IS NOT NULL AND group_id IS NULL) OR (user_id IS NULL AND group_id IS NOT NULL))
);

CREATE INDEX idx_scheme_share_scheme ON scheme_share(scheme_id);
CREATE INDEX idx_scheme_share_user ON scheme_share(user_id);
CREATE INDEX idx_scheme_share_group ON scheme_share(group_id);
CREATE INDEX idx_scheme_share_revoked ON scheme_share(revoked_at);
```

**Attributes**:
- `id` (UUID, PK): Unique share relationship ID
- `scheme_id` (UUID FK, NOT NULL): Marking scheme being shared
- `user_id` (UUID FK, nullable): Individual user recipient
- `group_id` (UUID FK, nullable): Group recipient
- `permission` (Enum, NOT NULL): SharePermission enum value
- `shared_by_id` (UUID FK, NOT NULL): User who granted access (audit trail)
- `shared_at` (DateTime): When access granted
- `revoked_at` (DateTime, nullable): When access revoked (soft delete)
- `revoked_by_id` (UUID FK, nullable): User who revoked access

**Constraints**:
- Must have either user_id OR group_id (XOR), never both
- scheme_id + user_id must be unique (no duplicate user shares)
- scheme_id + group_id must be unique (no duplicate group shares)
- Cascade delete with marking_scheme (revoke shares when scheme deleted)

**Relationships**:
- ← MarkingScheme (many:1)
- ← User (many:1 via user_id) - recipient
- ← User (many:1 via shared_by_id) - who shared
- ← User (many:1 via revoked_by_id) - who revoked
- ← UserGroup (many:1) - recipient group

**Validation Rules**:
- permission: must be valid SharePermission enum
- Must have exactly one of user_id or group_id set
- shared_by_id must be valid user
- revoked_by_id: optional, but if set, revoked_at must be set

**Key Operations**:
- Grant access: Insert with shared_by_id (current user)
- Revoke access: Update revoked_at and revoked_by_id
- List accessible schemes for user: Query WHERE (user_id = ? OR group_id IN user_groups) AND revoked_at IS NULL
- Check permission: Query, verify permission level

---

### SharePermission (Enum)

Enumeration of permission levels for shared schemes.

```python
class SharePermission(Enum):
    VIEW_ONLY = "VIEW_ONLY"      # Can see, view, and use scheme; cannot modify
    EDITABLE = "EDITABLE"        # Can see, view, use, and modify (affects shared version)
    COPY = "COPY"                # Can see and create independent copy (non-destructive)
```

**Permission Enforcement**:
- VIEW_ONLY: Read-only access in UI; reject modifications (FR-019)
- EDITABLE: Full access including modifications to shared scheme
- COPY: Allow recipient to create independent copy; modifications don't affect original

**Checking Permission**:
```
def has_permission(user_id, scheme_id, required_permission):
  share = query_active_share(user_id, scheme_id)
  if not share: return False
  return compare_permissions(share.permission, required_permission)
```

---

### DocumentUploadLog

Audit trail for document uploads and conversions. Tracks all document processing requests.

```sql
CREATE TABLE document_upload_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL FOREIGN KEY REFERENCES user(id),
  file_name VARCHAR(500) NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  file_hash VARCHAR(64),  -- SHA256 for deduplication
  upload_at TIMESTAMP NOT NULL DEFAULT now(),

  llm_provider VARCHAR(50) NOT NULL,  -- e.g., 'openai', 'claude', 'google'
  llm_model VARCHAR(100) NOT NULL,    -- e.g., 'gpt-4', 'claude-3-sonnet'
  llm_request_tokens INTEGER,
  llm_response_tokens INTEGER,
  conversion_status VARCHAR(20) NOT NULL CHECK (conversion_status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED')),
  conversion_time_ms INTEGER,  -- Time taken for LLM analysis

  error_message TEXT,  -- If conversion_status = 'FAILED'
  extracted_scheme_preview TEXT,  -- First 1000 chars of result for audit
  uncertainty_flags TEXT,  -- JSON array of uncertain fields

  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),

  INDEX idx_user_upload (user_id, upload_at),
  INDEX idx_conversion_status (conversion_status)
);
```

**Attributes**:
- `id` (UUID, PK): Unique upload record ID
- `user_id` (UUID FK, NOT NULL): User who uploaded
- `file_name` (String, NOT NULL): Original file name (1-500 chars)
- `file_size_bytes` (Integer, NOT NULL): File size for performance tracking
- `mime_type` (String, NOT NULL): Detected MIME type
- `file_hash` (String, 64 chars): SHA256 hash for deduplication
- `upload_at` (DateTime): When uploaded
- `llm_provider` (String): Which AI provider used
- `llm_model` (String): Model version for reproducibility
- `llm_request_tokens` (Integer): Input tokens used
- `llm_response_tokens` (Integer): Output tokens used
- `conversion_status` (Enum): PENDING → PROCESSING → SUCCESS or FAILED
- `conversion_time_ms` (Integer): LLM latency for performance monitoring
- `error_message` (Text, nullable): If failed
- `extracted_scheme_preview` (Text): Snippet of result
- `uncertainty_flags` (JSON): Array of flagged conversion issues
- `created_at`, `updated_at`: Timestamps

**Relationships**:
- ← User (many:1)

**Validation Rules**:
- file_name: required, max 500 chars
- file_size_bytes: > 0, < 52428800 (50MB)
- mime_type: must match uploaded file content
- conversion_status: enum value
- conversion_time_ms: >= 0 (duration)
- llm_provider/model: must be valid configured provider

**Key Operations**:
- Log upload: Insert with PENDING status
- Update conversion: Mark as PROCESSING, then SUCCESS or FAILED
- Audit trail: Query by user_id, date range, status
- Performance analysis: Query conversion_time_ms distribution

---

### DocumentConversionResult

Transient storage for in-progress or completed document conversions. Used for UI polling and result retrieval.

```sql
CREATE TABLE document_conversion_result (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upload_log_id UUID UNIQUE NOT NULL FOREIGN KEY REFERENCES document_upload_log(id) ON DELETE CASCADE,

  status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'QUEUED', 'PROCESSING', 'SUCCESS', 'FAILED')),

  -- Raw LLM response (JSON)
  llm_response TEXT,

  -- Extracted marking scheme (JSON - draft MarkingScheme object)
  extracted_scheme JSON,

  -- Uncertainty markers from conversion
  uncertainty_flags JSON,  -- Array of {"field": "...", "confidence": 0.7, "reason": "..."}

  -- Error information
  error_code VARCHAR(50),
  error_message TEXT,

  -- Timestamps
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  completed_at TIMESTAMP,

  INDEX idx_status (status),
  INDEX idx_completed (completed_at)
);
```

**Attributes**:
- `id` (UUID, PK): Unique result ID
- `upload_log_id` (UUID FK, UNIQUE): Links to the upload event
- `status` (Enum): PENDING → QUEUED → PROCESSING → SUCCESS or FAILED
- `llm_response` (Text/JSON): Raw response from LLM API
- `extracted_scheme` (JSON): Parsed MarkingScheme structure (null until SUCCESS)
- `uncertainty_flags` (JSON): Array of confidence ratings per field
- `error_code` (String): Error classification (timeout, parsing_error, invalid_format, etc.)
- `error_message` (Text): Human-readable error
- `created_at`, `updated_at`, `completed_at`: Timestamps

**Relationships**:
- ← DocumentUploadLog (1:1 via upload_log_id)

**Validation Rules**:
- status: enum value
- extracted_scheme: valid MarkingScheme JSON when status = SUCCESS
- uncertainty_flags: array of {field, confidence, reason} objects
- error_code: required if status = FAILED

**Key Operations**:
- Create placeholder: Insert with PENDING status
- Queue job: Update to QUEUED with job_id
- Update progress: Mark as PROCESSING
- Store result: Update to SUCCESS with extracted_scheme
- Record error: Update to FAILED with error details
- Poll for result: SELECT by result_id WHERE status IN (SUCCESS, FAILED)

---

## Relationship Diagram

```
User (existing)
├─ 1──0..n──→ MarkingScheme (owner_id)
├─ 1──0..n──→ SchemeShare (shared_by_id)
├─ 1──0..n──→ SchemeShare (revoked_by_id)
├─ 1──0..n──→ DocumentUploadLog
└─ 1──0..n──→ UserGroup (via user_group_members)

MarkingScheme (existing, extended)
├─ 1──0..n──→ SchemeCriterion (existing)
├─ 1──0..n──→ SchemeShare (scheme_id)
└─ 1──←──0..1──UserGroup (via SchemeShare.group_id)

UserGroup (existing or assumed)
└─ 1──0..n──→ SchemeShare (group_id)

DocumentUploadLog
├─ ←──1──1──→ DocumentConversionResult (upload_log_id)
└─ ←──1──0..n──→ User (user_id)

SharePermission (enum - not a table)
└─ ⊆ SchemeShare.permission
```

---

## JSON Schema: MarkingScheme Export Format

Standard JSON format for export/import operations. Validated against this schema.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Marking Scheme Export",
  "type": "object",
  "required": ["version", "metadata", "criteria"],
  "properties": {
    "version": {
      "type": "string",
      "description": "Format version for backward compatibility",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "example": "1.0.0"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 200
        },
        "description": {
          "type": "string",
          "maxLength": 5000
        },
        "exported_at": {
          "type": "string",
          "format": "date-time"
        },
        "exported_by": {
          "type": "string",
          "description": "Email or user ID of exporter"
        }
      },
      "required": ["name", "exported_at"]
    },
    "criteria": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "name", "descriptors"],
        "properties": {
          "id": {
            "type": "string",
            "description": "Unique criterion ID"
          },
          "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": "Criterion name"
          },
          "description": {
            "type": "string",
            "maxLength": 2000
          },
          "weight": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Relative weight (0-1)"
          },
          "point_value": {
            "type": "number",
            "minimum": 0,
            "description": "Total points available"
          },
          "descriptors": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["level", "description"],
              "properties": {
                "level": {
                  "type": "string",
                  "enum": ["excellent", "good", "satisfactory", "poor", "fail"],
                  "description": "Performance level"
                },
                "description": {
                  "type": "string",
                  "minLength": 1,
                  "maxLength": 500
                },
                "points": {
                  "type": "number",
                  "minimum": 0,
                  "description": "Points for this level"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Export Validation** (FR-001):
- All criteria present
- All descriptors for each criterion
- Weights sum to 1.0 (or optional if equal weight)
- Point values >= 0
- No required fields missing

**Import Validation** (FR-003):
- Must match JSON schema above
- Criteria count >= 1
- Each criterion has >= 1 descriptor
- Descriptor levels valid (enum check)
- No duplicate criterion names
- All numeric values valid ranges

---

## Migration Plan

**Phase 1 (Initial deployment)**:
1. Add columns to MarkingScheme table (owner_id, created_at, updated_at, is_shared, description)
2. Create SchemeShare table with indexes
3. Create DocumentUploadLog table
4. Create DocumentConversionResult table

**Phase 2 (Data migration)**:
1. Populate owner_id: Set to current user or admin for existing schemes (requires context)
2. Set created_at/updated_at to current timestamp for existing schemes
3. Set is_shared = false for all existing schemes

**Rollback**:
- Drop new tables (SchemeShare, DocumentUploadLog, DocumentConversionResult)
- Remove new columns from MarkingScheme
- Restore previous MarkingScheme state

---

## Database Consistency Rules

Per constitution requirements:

1. **Audit Trail**: All sharing operations logged in SchemeShare (who, when, what permission)
2. **Soft Delete**: revoked_at field enables audit recovery, not hard deletes
3. **Cascading**: Deleting MarkingScheme cascades to SchemeShare (makes sense - delete scheme revokes all shares)
4. **Concurrency**: Unique constraints prevent race conditions (duplicate shares)
5. **Integrity**: Foreign keys with proper constraints, CHECK constraints on enums
