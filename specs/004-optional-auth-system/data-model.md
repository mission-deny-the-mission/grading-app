# Data Model: Optional Multi-User Authentication with AI Usage Controls

**Feature**: 004-optional-auth-system
**Date**: 2025-11-15
**Status**: Design Complete

## Overview

This document defines the database schema for optional multi-user authentication with AI usage tracking and project sharing. All models use Flask-SQLAlchemy ORM and follow existing project patterns.

## Entity Relationship Diagram

```
┌─────────────────────┐
│  DeploymentConfig   │ (Singleton)
├─────────────────────┤
│ id (PK)             │
│ mode                │───── single-user | multi-user
│ configured_at       │
└─────────────────────┘

┌─────────────────────┐
│       User          │
├─────────────────────┤
│ id (PK)             │
│ email (unique)      │
│ password_hash       │
│ created_at          │
│ is_admin            │
└──────┬──────────────┘
       │
       │ 1:N
       │
┌──────▼──────────────┐       ┌─────────────────────┐
│  AIProviderQuota    │       │    UsageRecord      │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │       │ id (PK)             │
│ user_id (FK)        │       │ user_id (FK)        │───────┐
│ provider            │◄──────│ provider            │       │
│ limit_type          │   1:N │ tokens_consumed     │       │
│ limit_value         │       │ timestamp           │       │
│ reset_period        │       │ project_id (FK)     │       │
└─────────────────────┘       │ operation_type      │       │
                              └─────────────────────┘       │
                                                             │
┌─────────────────────┐       ┌─────────────────────┐       │
│   AuthSession       │       │   ProjectShare      │       │
├─────────────────────┤       ├─────────────────────┤       │
│ id (PK)             │       │ id (PK)             │       │
│ session_id (unique) │       │ project_id (FK)     │───────┤
│ user_id (FK)        │───┐   │ user_id (FK)        │───────┘
│ created_at          │   │   │ permission_level    │
│ expires_at          │   │   │ granted_at          │
│ ip_address          │   │   └─────────────────────┘
│ user_agent          │   │
└─────────────────────┘   │
                          │
                          └── Links to existing GradingJob, SavedPrompt via project_id
```

## Table Definitions

### 1. DeploymentConfig (Singleton)

**Purpose**: Stores system-wide deployment mode configuration

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PK, UUID | Singleton record ID (always "singleton") |
| mode | String(20) | NOT NULL | Deployment mode: "single-user" or "multi-user" |
| configured_at | DateTime | NOT NULL | Initial configuration timestamp |
| updated_at | DateTime | NOT NULL | Last mode change timestamp |

**Validation Rules**:
- Mode must be enum: `single-user` | `multi-user`
- Only one record allowed (enforced by ID="singleton")
- Mode changes require migration script validation

**State Transitions**:
```
[Initial Setup]
     ↓
single-user ←→ multi-user
     ↑              ↓
     └──[Migration]─┘
```

**Example**:
```python
{
    "id": "singleton",
    "mode": "multi-user",
    "configured_at": "2025-11-15T10:00:00Z",
    "updated_at": "2025-11-15T10:00:00Z"
}
```

---

### 2. User

**Purpose**: Represents individual users in multi-user mode

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PK, UUID | Unique user identifier |
| email | String(255) | UNIQUE, NOT NULL | User email (login identifier) |
| password_hash | String(255) | NOT NULL | PBKDF2-SHA256 hashed password |
| display_name | String(100) | NULL | Optional display name |
| created_at | DateTime | NOT NULL | Account creation timestamp |
| is_admin | Boolean | DEFAULT FALSE | Administrator privileges flag |
| is_active | Boolean | DEFAULT TRUE | Account active status |

**Indexes**:
- `UNIQUE INDEX idx_user_email ON users(email)`
- `INDEX idx_user_active ON users(is_active)`

**Validation Rules**:
- Email must be valid format (validated via email-validator)
- Password must be ≥8 characters (enforced at application layer)
- Password hashed using `werkzeug.security.generate_password_hash`
- Email case-insensitive (normalized to lowercase on save)

**Relationships**:
- `ai_quotas` → AIProviderQuota (1:N)
- `usage_records` → UsageRecord (1:N)
- `sessions` → AuthSession (1:N)
- `owned_projects` → GradingJob (1:N, via foreign key on GradingJob)
- `shared_projects` → ProjectShare (1:N)

**Example**:
```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "teacher@school.edu",
    "password_hash": "pbkdf2:sha256:600000$...",
    "display_name": "Jane Smith",
    "created_at": "2025-11-15T10:00:00Z",
    "is_admin": false,
    "is_active": true
}
```

---

### 3. AIProviderQuota

**Purpose**: Per-user AI usage limits for each provider

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PK, UUID | Unique quota identifier |
| user_id | String(36) | FK(User.id), NOT NULL | User this quota applies to |
| provider | String(50) | NOT NULL | Provider name (openrouter, claude, gemini, lmstudio) |
| limit_type | String(20) | NOT NULL | Limit metric: "tokens" or "requests" |
| limit_value | Integer | NOT NULL | Maximum allowed value |
| reset_period | String(20) | NOT NULL | Reset frequency: "daily", "weekly", "monthly", "unlimited" |
| created_at | DateTime | NOT NULL | Quota creation timestamp |
| updated_at | DateTime | NOT NULL | Last quota modification timestamp |

**Indexes**:
- `UNIQUE INDEX idx_quota_user_provider ON ai_provider_quotas(user_id, provider)`

**Validation Rules**:
- Provider must match existing AI provider names
- Limit type must be enum: `tokens` | `requests`
- Limit value must be > 0 or -1 (unlimited)
- Reset period must be enum: `daily` | `weekly` | `monthly` | `unlimited`
- One quota per (user, provider) pair (enforced by unique index)

**Calculated Fields** (application layer):
- `current_usage`: SUM(usage_records.tokens_consumed) for current period
- `remaining_quota`: limit_value - current_usage
- `percentage_used`: (current_usage / limit_value) * 100

**Example**:
```python
{
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "provider": "openrouter",
    "limit_type": "tokens",
    "limit_value": 1000000,
    "reset_period": "monthly",
    "created_at": "2025-11-15T10:00:00Z",
    "updated_at": "2025-11-15T10:00:00Z"
}
```

---

### 4. UsageRecord

**Purpose**: Audit trail of all AI provider usage

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PK, UUID | Unique record identifier |
| user_id | String(36) | FK(User.id), NOT NULL | User who made the request |
| provider | String(50) | NOT NULL | AI provider used |
| tokens_consumed | Integer | NOT NULL | Tokens/requests consumed |
| timestamp | DateTime | NOT NULL | Usage timestamp (UTC) |
| project_id | String(36) | FK(GradingJob.id), NULL | Associated project (if applicable) |
| operation_type | String(50) | NOT NULL | Operation: "grading", "ocr", "analysis" |
| model_name | String(100) | NULL | Specific model used (e.g., "gpt-4") |

**Indexes**:
- `INDEX idx_usage_user_provider_time ON usage_records(user_id, provider, timestamp DESC)`
- `INDEX idx_usage_project ON usage_records(project_id)`
- `INDEX idx_usage_timestamp ON usage_records(timestamp DESC)`

**Validation Rules**:
- Timestamp must be in UTC
- Tokens consumed must be ≥ 0
- Provider must match AIProviderQuota.provider values

**Retention Policy**:
- Keep all records for 90 days (auditing requirement)
- Archive records >90 days to cold storage (future enhancement)

**Aggregation Queries** (examples):
```sql
-- Current month usage for user
SELECT SUM(tokens_consumed)
FROM usage_records
WHERE user_id = ? AND provider = ? AND timestamp >= DATE_TRUNC('month', CURRENT_DATE);

-- Top users by usage
SELECT user_id, SUM(tokens_consumed) as total
FROM usage_records
WHERE timestamp >= ?
GROUP BY user_id
ORDER BY total DESC
LIMIT 10;
```

**Example**:
```python
{
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "provider": "openrouter",
    "tokens_consumed": 1523,
    "timestamp": "2025-11-15T14:30:00Z",
    "project_id": "880e8400-e29b-41d4-a716-446655440003",
    "operation_type": "grading",
    "model_name": "gpt-4-turbo"
}
```

---

### 5. ProjectShare

**Purpose**: Project sharing permissions between users

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PK, UUID | Unique share identifier |
| project_id | String(36) | FK(GradingJob.id), NOT NULL | Shared project |
| user_id | String(36) | FK(User.id), NOT NULL | User granted access |
| permission_level | String(10) | NOT NULL | Permission: "read" or "write" |
| granted_at | DateTime | NOT NULL | Share creation timestamp |
| granted_by | String(36) | FK(User.id), NOT NULL | User who granted access (owner) |

**Indexes**:
- `UNIQUE INDEX idx_share_project_user ON project_shares(project_id, user_id)`
- `INDEX idx_share_user ON project_shares(user_id)`

**Validation Rules**:
- Permission level must be enum: `read` | `write`
- Cannot share with self (user_id ≠ granted_by)
- Project owner determined by GradingJob.owner_id (added in migration)
- One share per (project, user) pair (enforced by unique index)

**Access Control Logic**:
```python
def can_access_project(user_id, project_id):
    # Owner always has access
    if GradingJob.query.get(project_id).owner_id == user_id:
        return True
    # Check shared access
    share = ProjectShare.query.filter_by(
        project_id=project_id, user_id=user_id
    ).first()
    return share is not None

def can_modify_project(user_id, project_id):
    project = GradingJob.query.get(project_id)
    if project.owner_id == user_id:
        return True
    share = ProjectShare.query.filter_by(
        project_id=project_id, user_id=user_id
    ).first()
    return share and share.permission_level == "write"
```

**Example**:
```python
{
    "id": "990e8400-e29b-41d4-a716-446655440004",
    "project_id": "880e8400-e29b-41d4-a716-446655440003",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",  # Recipient
    "permission_level": "read",
    "granted_at": "2025-11-15T15:00:00Z",
    "granted_by": "550e8400-e29b-41d4-a716-446655440000"  # Owner
}
```

---

### 6. AuthSession

**Purpose**: Active user sessions for authentication

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | String(36) | PK, UUID | Internal session identifier |
| session_id | String(255) | UNIQUE, NOT NULL | Flask session identifier |
| user_id | String(36) | FK(User.id), NOT NULL | Authenticated user |
| created_at | DateTime | NOT NULL | Session creation time |
| last_activity | DateTime | NOT NULL | Last request timestamp |
| expires_at | DateTime | NOT NULL | Session expiration time |
| ip_address | String(45) | NULL | Client IP address (IPv4/IPv6) |
| user_agent | String(255) | NULL | Client user agent string |

**Indexes**:
- `UNIQUE INDEX idx_session_id ON auth_sessions(session_id)`
- `INDEX idx_session_expires ON auth_sessions(expires_at)`
- `INDEX idx_session_user ON auth_sessions(user_id)`

**Validation Rules**:
- Session expires after 30 minutes of inactivity (configurable)
- Absolute session timeout: 8 hours (configurable)
- IP address stored for audit/security (not enforced for validation)

**Session Lifecycle**:
```
[Login] → Create session → Set expires_at
   ↓
[Request] → Update last_activity → Extend expiration
   ↓
[Timeout/Logout] → Delete session
```

**Cleanup Job**:
```sql
-- Delete expired sessions (run every 15 minutes via Celery)
DELETE FROM auth_sessions WHERE expires_at < NOW();
```

**Example**:
```python
{
    "id": "aa0e8400-e29b-41d4-a716-446655440005",
    "session_id": "flask_session_abc123def456...",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-11-15T10:00:00Z",
    "last_activity": "2025-11-15T10:25:00Z",
    "expires_at": "2025-11-15T10:30:00Z",  # 30 min from last_activity
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 ..."
}
```

---

## Migration Plan

### Existing Tables Modified

**GradingJob** (existing table):
- Add `owner_id` column: `String(36), FK(User.id), NULL`
- Nullable for backward compatibility (single-user mode)
- Backfill with NULL for existing records (migration script)

**SavedPrompt** (existing table):
- Add `owner_id` column: `String(36), FK(User.id), NULL`
- Same approach as GradingJob

### Migration Order

1. **Migration 001**: Create `deployment_config` table
   - Insert default record: `mode='single-user'`

2. **Migration 002**: Create `users` table with indexes

3. **Migration 003**: Create `ai_provider_quotas` table

4. **Migration 004**: Create `usage_records` table with indexes

5. **Migration 005**: Create `project_shares` table

6. **Migration 006**: Create `auth_sessions` table

7. **Migration 007**: Add `owner_id` to `grading_jobs` and `saved_prompts`
   - NOT NULL constraint added later after backfill

### Rollback Strategy

- All migrations reversible via `flask db downgrade`
- Drop tables in reverse order: 007 → 006 → 005 → 004 → 003 → 002 → 001
- Foreign key constraints prevent orphaned records

## Data Integrity Constraints

### Referential Integrity

- `AIProviderQuota.user_id` → `User.id` (CASCADE DELETE)
- `UsageRecord.user_id` → `User.id` (RESTRICT DELETE - preserve audit trail)
- `ProjectShare.user_id` → `User.id` (CASCADE DELETE)
- `ProjectShare.granted_by` → `User.id` (RESTRICT DELETE)
- `AuthSession.user_id` → `User.id` (CASCADE DELETE)

### Application-Level Constraints

1. **Single-User Mode**:
   - Users table empty
   - No auth checks performed
   - All projects owned by NULL (system)

2. **Multi-User Mode**:
   - Users table populated
   - All requests authenticated
   - Projects must have owner_id (enforced at creation)

3. **Quota Enforcement**:
   - Check before AI request: `current_usage + request_cost <= limit_value`
   - Record usage immediately after AI response
   - Transaction isolation: SELECT FOR UPDATE on quota row

## Performance Characteristics

### Expected Query Patterns

| Query | Frequency | Optimization |
|-------|-----------|--------------|
| Check user quota | Every AI request | Index on (user_id, provider) + caching |
| Record usage | After every AI request | Batch insert if possible |
| Load user session | Every HTTP request | Index on session_id + in-memory cache |
| List user projects | Page load | Index on owner_id + eager loading shares |
| Aggregate usage reports | Admin dashboard | Materialized view (future) |

### Scalability Targets

- **Users**: 1,000 concurrent, 10,000 total
- **Usage records**: 1M rows (3 months at 10k requests/day)
- **Sessions**: 1,000 concurrent (cleanup job prevents buildup)
- **Projects**: 100k total (existing scale)

### Bottleneck Mitigation

1. **Usage recording**: Consider async Celery task if >100 req/s
2. **Session lookups**: Redis caching layer if >1000 concurrent users
3. **Usage aggregations**: Pre-calculated summaries table for dashboard

## Testing Data

### Seed Data (Development)

```python
# Default admin user
admin = User(
    email="admin@localhost",
    password_hash=generate_password_hash("admin123"),
    is_admin=True
)

# Test quotas
quota = AIProviderQuota(
    user_id=admin.id,
    provider="openrouter",
    limit_type="tokens",
    limit_value=1000000,
    reset_period="monthly"
)
```

### Test Scenarios

1. **Auth Flow**: Create user → Login → Access protected route → Logout
2. **Quota Enforcement**: Set limit=100 → Consume 100 → Verify block → Verify error message
3. **Project Sharing**: User A creates project → Shares with User B (read) → User B views → User B denied edit
4. **Deployment Mode**: Start single-user → No auth required → Switch to multi-user → Auth required

---

**Status**: Ready for implementation. All entities defined with validation rules, indexes, and relationships specified.
