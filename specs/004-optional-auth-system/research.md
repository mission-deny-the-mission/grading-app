# Research: Optional Multi-User Authentication with AI Usage Controls

**Feature**: 004-optional-auth-system
**Date**: 2025-11-15
**Status**: Research Complete

## Overview

This document captures technical decisions made during the research phase for implementing optional authentication with AI usage controls and project sharing capabilities.

## Technical Decisions

### 1. Authentication Library

**Decision**: Flask-Login with session-based authentication

**Rationale**:
- **Flask-Login chosen over alternatives**:
  - Already Flask-native, minimal dependencies
  - Session-based auth simpler for web app (no token management complexity)
  - Well-documented, battle-tested library (10+ years, 17k+ stars)
  - Supports "remember me" functionality out of the box
  - Easy integration with existing Flask-SQLAlchemy models

- **Why not authlib**: Overkill for requirements; primarily OAuth/OIDC focused (we need simple username/password)
- **Why not custom JWT**: Unnecessary complexity; session-based auth is simpler for server-rendered templates + API hybrid

**Alternatives Considered**:
1. **Authlib**: More powerful but complex; best for OAuth/OIDC federation (not required)
2. **Custom JWT**: Would require token refresh logic, storage, revocation - adds significant complexity
3. **Flask-Security-Too**: Heavy-weight with many features we don't need (2FA, email confirmation beyond requirements)

**Implementation Approach**:
- Use Flask-Login's `LoginManager` for session handling
- Store sessions in secure HTTP-only cookies
- Implement `UserMixin` on User model for Flask-Login integration
- Use `@login_required` decorator for protected routes
- Session timeout configurable via `PERMANENT_SESSION_LIFETIME`

### 2. Database Solution

**Decision**: Existing SQLite/PostgreSQL setup with Flask-SQLAlchemy

**Rationale**:
- **Current setup** (from codebase analysis):
  - Flask-SQLAlchemy already configured (`models.py:line 4-7`)
  - SQLite for development (`app.py:line 23-26`)
  - PostgreSQL for production (via DATABASE_URL env var)
  - Flask-Migrate already installed for migrations (`requirements.txt:line 11`)

- **No changes needed**: Existing ORM setup supports all authentication requirements
- **Migration path**: Flask-Migrate handles schema evolution for new tables

**Database Schema Strategy**:
- Add 6 new tables: `users`, `deployment_config`, `ai_provider_quotas`, `usage_records`, `project_shares`, `auth_sessions`
- Foreign keys to existing `saved_prompts`, `grading_jobs` tables for project ownership
- Indexes on: `users.email`, `usage_records.user_id+provider+timestamp`, `project_shares.project_id`

**Alternatives Considered**:
1. **NoSQL (MongoDB/Redis)**: Unnecessary; relational data model fits requirements perfectly
2. **Separate auth database**: Overcomplication; single database simpler for small-medium scale

### 3. Frontend Framework

**Decision**: Server-rendered Flask templates (Jinja2) with progressive enhancement via vanilla JavaScript

**Rationale**:
- **Current architecture** (from codebase analysis):
  - Project uses Flask templates (`templates/*.html` exist)
  - Server-rendered HTML with Jinja2 templating
  - Minimal JavaScript for interactivity (existing pattern)
  - No package.json or frontend build system detected

- **Consistency with existing codebase**: Maintain current architecture rather than introducing React/Vue mid-project
- **Simplicity**: No build pipeline, transpilation, or state management complexity
- **Progressive enhancement**: Add JS for AJAX usage dashboard updates, real-time limit warnings

**Why not SPA framework**:
- **React/Vue**: Would require entire frontend rewrite; overkill for auth UI
- **Build complexity**: webpack/vite adds deployment complexity
- **Scope creep**: Feature spec doesn't require rich interactivity beyond basic forms/dashboards

**Implementation Approach**:
- Login form: Traditional POST with server-side validation
- Usage dashboard: Server-rendered with AJAX polling for real-time updates (vanilla fetch API)
- Project sharing: Server-rendered modal with JS form submission
- Error handling: Flash messages (existing pattern in Flask)

### 4. Password Hashing

**Decision**: Werkzeug's `generate_password_hash` / `check_password_hash` (PBKDF2-SHA256)

**Rationale**:
- **Already available**: Werkzeug is Flask's core dependency (`requirements.txt:line 6`)
- **Secure by default**: PBKDF2-SHA256 with 600,000 iterations (OWASP recommended)
- **Zero new dependencies**: No need for bcrypt/argon2 packages
- **Constitution compliance**: Industry-standard password hashing (Security Requirements)

**Alternatives Considered**:
1. **bcrypt**: More CPU-intensive, requires C compilation (deployment complexity)
2. **argon2**: Winner of Password Hashing Competition, but adds dependency
3. **passlib**: Additional abstraction layer, unnecessary for single algorithm

### 5. Session Storage

**Decision**: Flask's default secure cookie sessions with server-side session data

**Rationale**:
- **Secure cookies**: HTTP-only, secure flag for HTTPS, signed with SECRET_KEY
- **Scalability**: For 10-1000 users, cookie sessions sufficient
- **No external service**: Redis/Memcached not required for this scale
- **Existing secret key**: `app.secret_key` already configured (`app.py:line 18`)

**Scaling consideration**: If concurrent users >1000, migrate to Flask-Session with Redis backend (future optimization)

### 6. AI Usage Tracking Implementation

**Decision**: Database-backed usage records with in-memory caching for rate limiting

**Rationale**:
- **Persistent audit trail**: `usage_records` table satisfies audit requirements (Constitution V)
- **Real-time enforcement**: Query current period usage before AI provider calls
- **Flexible metrics**: Support tokens, requests, or provider-specific units
- **Cache optimization**: Cache user quota/usage in request context to avoid repeated queries

**Query optimization**:
```sql
-- Fast lookup with compound index
SELECT SUM(tokens_consumed)
FROM usage_records
WHERE user_id = ? AND provider = ? AND timestamp >= ?
```

**Alternatives Considered**:
1. **Redis counters**: Faster but loses audit trail detail, harder to debug
2. **Celery task for async tracking**: Over-engineered; synchronous tracking acceptable (<50ms overhead)

### 7. Deployment Mode Configuration

**Decision**: Environment variable + database flag with migration validator

**Rationale**:
- **Two-layer approach**:
  - `DEPLOYMENT_MODE` env var (single-user/multi-user) - startup configuration
  - `deployment_config` table - persistent mode tracking with migration timestamps
- **Safety**: Startup validator checks env var matches database mode; errors if mismatch
- **Migration path**: Upgrade script handles single→multi mode data attribution

**Configuration validation**:
```python
# On app startup
db_mode = DeploymentConfig.get_current_mode()
env_mode = os.getenv('DEPLOYMENT_MODE', 'single-user')
if db_mode != env_mode:
    raise ConfigError(f"Mode mismatch: DB={db_mode}, ENV={env_mode}")
```

### 8. Middleware Architecture

**Decision**: Two-middleware chain: AuthMiddleware → UsageEnforcementMiddleware

**Rationale**:
- **Separation of concerns**:
  - `AuthMiddleware`: Session validation, user loading, deployment mode routing
  - `UsageEnforcementMiddleware`: AI quota checks, usage recording, limit enforcement
- **Conditional execution**: Auth middleware checks deployment mode, skips auth in single-user
- **Performance**: Early exit if deployment mode = single-user (zero auth overhead)

**Middleware order**:
```python
@app.before_request
def check_auth():  # AuthMiddleware
    if deployment_mode == 'single-user':
        return  # Skip auth entirely
    # Validate session, load user

@app.before_request
def enforce_usage_limits():  # UsageEnforcementMiddleware
    if is_ai_request() and user.has_exceeded_limit(provider):
        abort(429, "Usage limit exceeded")
```

## Best Practices

### Security Best Practices

1. **Password Requirements**:
   - Minimum 8 characters (configurable)
   - NIST SP 800-63B recommendations: no composition rules (flexibility)
   - Check against common password lists (future enhancement)

2. **Session Security**:
   - HTTP-only cookies (XSS protection)
   - Secure flag in production (HTTPS only)
   - SameSite=Lax (CSRF protection)
   - Configurable timeout (default: 30 minutes idle, 8 hours absolute)

3. **Rate Limiting**:
   - Login attempts: 5 failures per email per 15 minutes
   - Password reset: 3 requests per email per hour
   - Usage tracking: Prevent timing attacks with constant-time queries

### Testing Strategy

1. **Unit Tests**:
   - Service layer: Auth logic, usage calculations, sharing permissions
   - Model layer: Validation rules, state transitions
   - Isolation: Mock database, AI providers

2. **Integration Tests**:
   - Full auth flow: Register → Login → Protected resource → Logout
   - Deployment modes: Verify single-user bypasses auth, multi-user enforces
   - Usage enforcement: Create user → Set limit → Exceed limit → Block request
   - Project sharing: Share → Access → Permission enforcement

3. **Contract Tests**:
   - API endpoints return expected schemas
   - Error responses include proper status codes
   - Backward compatibility with existing endpoints

### Migration Strategy

**Phase 1: Schema deployment**
```bash
# Create tables without enforcement
flask db migrate -m "Add authentication tables"
flask db upgrade
```

**Phase 2: Feature flag rollout**
```python
# Enable auth with feature flag
if os.getenv('AUTH_ENABLED', 'false') == 'true':
    @app.before_request
    def check_auth(): ...
```

**Phase 3: Full deployment**
- Remove feature flag
- Enable auth by default for multi-user mode
- Document single-user → multi-user migration process

## Performance Considerations

### Database Query Optimization

1. **Indexes required**:
   - `users(email)` - Unique index for login lookups
   - `usage_records(user_id, provider, timestamp)` - Compound index for usage queries
   - `project_shares(project_id, user_id)` - Compound index for access checks
   - `auth_sessions(session_id)` - Primary key for session lookups

2. **N+1 query prevention**:
   - Use `joinedload` for user → quotas relationship
   - Eager load project_shares when fetching project lists
   - Cache deployment mode configuration in app context

### Scaling Limits

**Current design supports**:
- 1,000 concurrent users (cookie sessions)
- 10,000 usage records per user (with quarterly archiving)
- 100 projects per user
- 50 collaborators per project

**Scaling triggers**:
- >1,000 concurrent users: Migrate to Redis sessions
- >100k usage records: Implement time-series database (InfluxDB/TimescaleDB)
- >10k total users: Add read replicas, connection pooling

## Dependencies Added

```txt
Flask-Login==0.6.3        # Session-based authentication
email-validator==2.2.0     # Email validation for user accounts
```

**Total new dependencies**: 2 (minimal addition)

## Open Questions Resolved

1. **Q: Support OAuth (Google/Microsoft)?**
   - A: Not in scope; focus on username/password. OAuth can be added later via authlib if needed.

2. **Q: CAPTCHA for registration/login?**
   - A: Not in initial scope; add if abuse detected in production.

3. **Q: Email verification for registration?**
   - A: Admin creates users initially (institutional deployment); self-registration not required in v1.

4. **Q: Multi-factor authentication (MFA)?**
   - A: Not required by spec; can add as optional feature in v2.

5. **Q: API tokens for programmatic access?**
   - A: Not required; all access via web UI. Can add if API clients emerge.

## References

- Flask-Login documentation: https://flask-login.readthedocs.io/
- OWASP Password Storage Cheat Sheet: https://cheatsheetsheetshet.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- NIST SP 800-63B Digital Identity Guidelines: https://pages.nist.gov/800-63-3/sp800-63b.html
- Flask-SQLAlchemy documentation: https://flask-sqlalchemy.palletsprojects.com/
- Werkzeug security utilities: https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security
