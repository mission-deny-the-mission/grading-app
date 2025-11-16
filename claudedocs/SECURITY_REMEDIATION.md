# Security Remediation Plan
## Optional Multi-User Authentication System

**Plan Date**: 2025-11-15
**Target Completion**: Before Production Deployment
**Priority**: CRITICAL

---

## Implementation Roadmap

### Phase 1: CRITICAL (Block Production) - 2-3 Days

These vulnerabilities **MUST** be fixed before any production deployment.

#### 1.1 CSRF Protection Implementation

**Severity**: CRITICAL
**Estimated Time**: 4 hours

**Implementation**:

```bash
# Step 1: Install Flask-WTF
echo "Flask-WTF==1.2.1" >> requirements.txt
pip install Flask-WTF==1.2.1
```

```python
# Step 2: app.py - Initialize CSRF protection
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# Configure CSRF
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Or set expiration (3600 for 1 hour)
app.config['WTF_CSRF_SSL_STRICT'] = True  # Require HTTPS in production
app.config['WTF_CSRF_ENABLED'] = True

# For API endpoints using JSON, implement double-submit cookie pattern
@app.after_request
def set_csrf_cookie(response):
    """Set CSRF token in cookie for frontend to read."""
    if request.endpoint and 'api.' in request.endpoint:
        token = csrf.generate_csrf()
        response.set_cookie(
            'csrf_token',
            token,
            secure=True,
            httponly=False,  # Frontend needs to read this
            samesite='Strict'
        )
    return response
```

```python
# Step 3: Frontend - Include CSRF token in requests
// JavaScript example
fetch('/api/admin/users', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrf_token')  // Read from cookie
    },
    body: JSON.stringify(data)
});

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}
```

**Testing**:
```python
# tests/test_csrf.py
def test_csrf_protection(client):
    # Attempt POST without CSRF token
    response = client.post('/api/admin/users', json={
        'email': 'test@example.com',
        'password': 'Test1234!'
    })
    assert response.status_code == 400  # CSRF validation failed

    # With CSRF token
    response = client.get('/api/auth/session')  # Get token
    csrf_token = response.cookies.get('csrf_token')

    response = client.post('/api/admin/users',
        json={'email': 'test@example.com', 'password': 'Test1234!'},
        headers={'X-CSRFToken': csrf_token}
    )
    assert response.status_code == 201
```

---

#### 1.2 Rate Limiting Implementation

**Severity**: CRITICAL
**Estimated Time**: 3 hours

**Implementation**:

```bash
# Step 1: Install dependencies
echo "Flask-Limiter==3.5.0" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt  # Already in requirements
pip install Flask-Limiter==3.5.0
```

```python
# Step 2: app.py - Initialize rate limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379"),
    strategy="fixed-window"  # Or "moving-window" for more accuracy
)

# Export for use in blueprints
app.limiter = limiter
```

```python
# Step 3: routes/auth_routes.py - Apply rate limits
from app import limiter  # Import from app

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")  # 5 login attempts per minute
@limiter.limit("20 per hour")   # 20 login attempts per hour
def login():
    ...

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("3 per hour")  # 3 registrations per hour
def register():
    ...

@auth_bp.route("/password-reset", methods=["POST"])
@limiter.limit("3 per hour")  # 3 reset requests per hour
def request_password_reset():
    ...
```

```python
# Step 4: Custom error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later.",
        "retry_after": e.description
    }), 429
```

**Configuration**:
```bash
# .env
REDIS_URL=redis://localhost:6379
```

**Testing**:
```python
# tests/test_rate_limiting.py
def test_login_rate_limit(client):
    # Attempt 6 logins in quick succession
    for i in range(6):
        response = client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': f'wrong{i}'
        })

        if i < 5:
            assert response.status_code in [400, 401]
        else:
            assert response.status_code == 429  # Rate limited
```

---

#### 1.3 Account Lockout Implementation

**Severity**: CRITICAL
**Estimated Time**: 4 hours

**Implementation**:

```python
# Step 1: models.py - Add failed login tracking
class User(db.Model):
    # ... existing fields ...
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_failed_login = db.Column(db.DateTime, nullable=True)

    def is_locked(self):
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def increment_failed_login(self, lockout_threshold=5, lockout_duration_minutes=30):
        """Increment failed login counter and lock account if threshold exceeded."""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.now(timezone.utc)

        if self.failed_login_attempts >= lockout_threshold:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_duration_minutes)
            logger.warning(f"Account locked due to {self.failed_login_attempts} failed attempts: {self.email}")

        db.session.commit()

    def reset_failed_login(self):
        """Reset failed login counter on successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_failed_login = None
        db.session.commit()
```

```python
# Step 2: services/auth_service.py - Implement lockout checks
@staticmethod
def authenticate(email, password):
    """Authenticate user with account lockout protection."""
    email = AuthService.validate_email(email)
    user = User.query.filter_by(email=email).first()

    # Check account lockout BEFORE password verification
    if user and user.is_locked():
        logger.warning(f"Login attempt for locked account: {email}")
        # Return generic error (don't reveal account is locked)
        return None

    if not user or not user.is_active:
        logger.warning(f"Authentication failed for {email}: user not found or inactive")
        return None

    # Verify password
    if not AuthService.verify_password(password, user.password_hash):
        user.increment_failed_login()  # Track failed attempt
        logger.warning(f"Authentication failed for {email}: invalid password (attempt {user.failed_login_attempts})")
        return None

    # Successful login - reset counter
    user.reset_failed_login()
    logger.info(f"User authenticated: {email}")
    return user
```

```python
# Step 3: routes/admin_routes.py - Add unlock endpoint
@admin_bp.route("/users/<user_id>/unlock", methods=["POST"])
@login_required
def unlock_user_account(user_id):
    """Unlock a locked user account (admin only)."""
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        user = AuthService.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        user.reset_failed_login()
        logger.info(f"Admin unlocked account: {user.email}")

        return jsonify({
            "success": True,
            "message": f"Account {user.email} unlocked",
            "user": user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error unlocking account: {e}")
        return jsonify({"success": False, "message": "Failed to unlock account"}), 500
```

**Migration**:
```bash
# Generate migration
flask db migrate -m "Add account lockout fields"
flask db upgrade
```

**Testing**:
```python
# tests/test_account_lockout.py
def test_account_lockout(client, test_user):
    # Attempt 5 failed logins
    for i in range(5):
        response = client.post('/api/auth/login', json={
            'email': test_user.email,
            'password': 'WrongPassword123!'
        })
        assert response.status_code == 401

    # 6th attempt should be blocked
    response = client.post('/api/auth/login', json={
        'email': test_user.email,
        'password': test_user_password  # Correct password
    })
    assert response.status_code == 401  # Still locked

    # Verify account is locked
    user = User.query.filter_by(email=test_user.email).first()
    assert user.is_locked() == True
```

---

#### 1.4 Security Headers Implementation

**Severity**: CRITICAL
**Estimated Time**: 2 hours

**Implementation**:

```python
# middleware/security_headers.py
def init_security_headers(app):
    """Initialize security headers middleware."""

    @app.after_request
    def set_security_headers(response):
        """Set comprehensive security headers."""

        # Content Security Policy (CSP)
        # Adjust based on your frontend requirements
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Adjust as needed
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Strict Transport Security (HSTS)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME-sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection (legacy, but still useful)
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), payment=()'
        )

        return response

    return app
```

```python
# app.py - Enable security headers
from middleware.security_headers import init_security_headers

# After auth middleware
init_security_headers(app)
```

**Testing**:
```python
# tests/test_security_headers.py
def test_security_headers(client):
    response = client.get('/api/auth/session')

    # Verify all security headers present
    assert 'Content-Security-Policy' in response.headers
    assert 'X-Frame-Options' in response.headers
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert 'X-Content-Type-Options' in response.headers
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert 'Referrer-Policy' in response.headers
```

---

#### 1.5 Project Ownership Verification

**Severity**: CRITICAL
**Estimated Time**: 4 hours

**Implementation**:

```python
# Step 1: models.py - Add ownership field to GradingJob
class GradingJob(db.Model):
    # ... existing fields ...
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    # Relationship
    owner = db.relationship("User", foreign_keys=[owner_id], backref="owned_jobs")
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_jobs")
```

```python
# Step 2: Migration
# migrations/versions/xxx_add_job_ownership.py
def upgrade():
    with op.batch_alter_table('grading_jobs') as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('created_by', sa.String(36), nullable=True))
        batch_op.create_foreign_key('fk_job_owner', 'users', ['owner_id'], ['id'])
        batch_op.create_foreign_key('fk_job_creator', 'users', ['created_by'], ['id'])

    # Backfill existing jobs (assign to first admin or leave null)
    # op.execute("UPDATE grading_jobs SET owner_id = (SELECT id FROM users WHERE is_admin=true LIMIT 1)")
```

```python
# Step 3: services/authorization_service.py (NEW)
"""Authorization service for project access control."""

import logging
from flask_login import current_user

from models import GradingJob, ProjectShare, User
from services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Service for authorization and access control."""

    @staticmethod
    def can_access_project(user_id, project_id):
        """Check if user can access a project (read or write)."""
        # Single-user mode: everyone can access everything
        if DeploymentService.is_single_user_mode():
            return True

        project = GradingJob.query.get(project_id)
        if not project:
            return False

        # Owner always has access
        if project.owner_id == user_id or project.created_by == user_id:
            return True

        # Check for shared access
        share = ProjectShare.query.filter_by(project_id=project_id, user_id=user_id).first()
        return share is not None

    @staticmethod
    def can_modify_project(user_id, project_id):
        """Check if user can modify a project (write access)."""
        # Single-user mode: everyone can modify everything
        if DeploymentService.is_single_user_mode():
            return True

        project = GradingJob.query.get(project_id)
        if not project:
            return False

        # Owner can always modify
        if project.owner_id == user_id or project.created_by == user_id:
            return True

        # Check for write permission
        share = ProjectShare.query.filter_by(project_id=project_id, user_id=user_id).first()
        return share is not None and share.permission_level == "write"

    @staticmethod
    def require_project_access(project_id):
        """Decorator helper to require project access."""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401

        if not AuthorizationService.can_access_project(current_user.id, project_id):
            return {"error": "Unauthorized"}, 403

        return None

    @staticmethod
    def require_project_write(project_id):
        """Decorator helper to require project write access."""
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}, 401

        if not AuthorizationService.can_modify_project(current_user.id, project_id):
            return {"error": "Unauthorized"}, 403

        return None
```

```python
# Step 4: routes/sharing_routes.py - Add ownership checks
from services.authorization_service import AuthorizationService

@sharing_bp.route("/<project_id>/shares", methods=["POST"])
@login_required
def share_project(project_id):
    """Share a project with another user."""
    # CRITICAL: Verify ownership before allowing share
    auth_check = AuthorizationService.require_project_write(project_id)
    if auth_check:
        return jsonify(auth_check[0]), auth_check[1]

    # Verify project exists
    from models import GradingJob
    project = GradingJob.query.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Now safe to share
    data = request.get_json() or {}
    recipient_id = data.get("user_id")
    permission_level = data.get("permission_level", "read")

    try:
        share = SharingService.share_project(project_id, current_user.id, recipient_id, permission_level)
        return jsonify({
            "success": True,
            "message": f"Project shared with {recipient_id}",
            "share": share.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
```

**Testing**:
```python
# tests/test_project_authorization.py
def test_unauthorized_project_access(client, test_user, other_user):
    # Create project as test_user
    login_as(client, test_user)
    project = create_project(client)

    # Try to access as other_user
    login_as(client, other_user)
    response = client.get(f'/api/jobs/{project.id}')
    assert response.status_code == 403

def test_unauthorized_project_share(client, test_user, other_user):
    # Create project as test_user
    login_as(client, test_user)
    project = create_project(client)

    # Try to share as other_user (not owner)
    login_as(client, other_user)
    response = client.post(f'/api/projects/{project.id}/shares', json={
        'user_id': other_user.id,
        'permission_level': 'write'
    })
    assert response.status_code == 403
```

---

#### 1.6 Production-Ready Password Reset

**Severity**: CRITICAL
**Estimated Time**: 3 hours

**Implementation**:

```python
# Step 1: models.py - Add PasswordResetToken model
class PasswordResetToken(db.Model):
    """Password reset token storage (database-backed)."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45))  # Track request origin

    # Relationship
    user = db.relationship("User", backref="reset_tokens")

    def is_valid(self):
        """Check if token is still valid."""
        if self.used_at is not None:
            return False  # Already used
        if datetime.now(timezone.utc) > self.expires_at:
            return False  # Expired
        return True

    def mark_used(self):
        """Mark token as used."""
        self.used_at = datetime.now(timezone.utc)
        db.session.commit()
```

```python
# Step 2: services/auth_service.py - Replace in-memory storage
import hashlib

@staticmethod
def generate_password_reset_token(email, ip_address=None):
    """Generate database-backed password reset token."""
    email = AuthService.validate_email(email)
    user = User.query.filter_by(email=email).first()

    if not user:
        # For security, don't reveal whether email exists
        logger.warning(f"Password reset requested for non-existent email: {email}")
        # Still return success (timing-safe)
        time.sleep(random.uniform(0.1, 0.3))  # Random delay
        raise ValueError("If this email exists, a reset link has been sent")

    # Generate secure token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Invalidate old tokens for this user
    PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update({"used_at": datetime.now(timezone.utc)})

    # Create new token
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ip_address=ip_address
    )
    db.session.add(reset_token)
    db.session.commit()

    logger.info(f"Password reset token generated for {email}")

    return {
        "token": token,  # Return plaintext token (send via email in production)
        "expires_at": reset_token.expires_at.isoformat(),
        "user_id": user.id
    }

@staticmethod
def validate_reset_token(token):
    """Validate password reset token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    reset_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()

    if not reset_token:
        raise ValueError("Invalid reset token")

    if not reset_token.is_valid():
        raise ValueError("Reset token has expired or been used")

    return {
        "valid": True,
        "user_id": reset_token.user_id,
        "email": reset_token.user.email
    }

@staticmethod
def reset_password_with_token(token, new_password):
    """Reset password using validated token."""
    # Validate token
    token_data = AuthService.validate_reset_token(token)
    user_id = token_data["user_id"]

    # Validate password
    AuthService.validate_password(new_password)

    # Update password
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")

    user.password_hash = generate_password_hash(new_password)

    # Mark token as used
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    reset_token.mark_used()

    # Reset failed login attempts
    user.reset_failed_login()

    db.session.commit()

    logger.info(f"Password reset successful for user {user.email}")
    return user
```

```python
# Step 3: routes/auth_routes.py - Remove token from response
@auth_bp.route("/password-reset", methods=["POST"])
def request_password_reset():
    """Request password reset token."""
    data = request.get_json() or {}
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    try:
        result = AuthService.generate_password_reset_token(email, ip_address=request.remote_addr)

        # TODO: Send email with token (production)
        # send_password_reset_email(email, result["token"])

        # PRODUCTION: Do NOT return token in response
        return jsonify({
            "success": True,
            "message": "If this email exists, a reset link has been sent"
            # "token": result["token"]  # REMOVE THIS IN PRODUCTION
        }), 200

    except ValueError as e:
        # Return success even if email doesn't exist (security best practice)
        return jsonify({
            "success": True,
            "message": "If this email exists, a reset link has been sent"
        }), 200
```

**Migration**:
```bash
flask db migrate -m "Add password reset token table"
flask db upgrade
```

---

#### 1.7 Remove Debug Code

**Severity**: HIGH
**Estimated Time**: 30 minutes

**Implementation**:

```python
# routes/auth_routes.py:161-163 - REMOVE or IMPLEMENT
# Current code:
# if not current_user.is_authenticated or not current_user.is_admin:
#     return jsonify({"success": False, "message": "Admin only"}), 403

# OPTION 1: Implement admin-only registration
@auth_bp.route("/register", methods=["POST"])
@login_required  # Require authentication
def register():
    # Check admin privilege
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin only"}), 403

    # ... rest of registration logic

# OPTION 2: Allow open registration (less secure)
# Remove the admin check entirely

# DECISION: Implement OPTION 1 (admin-only) for security
```

---

#### 1.8 SECRET_KEY Validation

**Severity**: CRITICAL
**Estimated Time**: 1 hour

**Implementation**:

```python
# app.py - Validate SECRET_KEY on startup
import sys

# Load environment
load_dotenv()

# CRITICAL: Validate SECRET_KEY
secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

# Production check
if not app.debug and secret_key == "your-secret-key-here":
    print("CRITICAL ERROR: SECRET_KEY not configured!", file=sys.stderr)
    print("Set SECRET_KEY environment variable before running in production", file=sys.stderr)
    sys.exit(1)

# Additional validation
if len(secret_key) < 32:
    print("WARNING: SECRET_KEY should be at least 32 characters", file=sys.stderr)
    if not app.debug:
        sys.exit(1)

app.secret_key = secret_key
```

```bash
# .env.example (CREATE THIS FILE)
# Flask Configuration
SECRET_KEY=generate-a-secure-random-string-at-least-32-characters-long
DATABASE_URL=postgresql://user:password@localhost:5432/grading_app
REDIS_URL=redis://localhost:6379

# Deployment Mode
DEPLOYMENT_MODE=single-user

# API Keys (optional)
OPENROUTER_API_KEY=
CLAUDE_API_KEY=
GEMINI_API_KEY=

# Session Configuration
SESSION_TIMEOUT=1800
PERMANENT_SESSION_LIFETIME=1800

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://localhost:6379
```

**Documentation**:
```markdown
# claudedocs/DEPLOYMENT_SECURITY.md (to be created in Phase 2)

## Required Environment Variables

### CRITICAL
- `SECRET_KEY`: Flask session encryption key (min 32 chars, cryptographically random)
- `DATABASE_URL`: PostgreSQL connection string

### Generate SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
```

---

### Phase 2: HIGH Priority (Launch Week) - 2-3 Days

#### 2.1 Audit Logging Implementation

**Estimated Time**: 6 hours

```python
# models.py - AuditLog model
class AuditLog(db.Model):
    """Tamper-resistant audit log for security events."""

    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # login, user_created, role_changed, etc.
    event_category = db.Column(db.String(20), nullable=False)  # authentication, authorization, data_modification
    severity = db.Column(db.String(10), nullable=False)  # info, warning, critical
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    resource_type = db.Column(db.String(50))  # user, project, share
    resource_id = db.Column(db.String(36))
    action = db.Column(db.String(50))  # create, read, update, delete
    details = db.Column(db.JSON)  # Additional context
    previous_value = db.Column(db.JSON)  # For modifications
    new_value = db.Column(db.JSON)  # For modifications

    # Tamper detection
    entry_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hash of log entry

    __table_args__ = (
        db.Index("idx_audit_user_time", "user_id", "timestamp"),
        db.Index("idx_audit_event", "event_type", "timestamp"),
    )

    def compute_hash(self):
        """Compute tamper-detection hash."""
        import hashlib
        import json

        data = f"{self.id}|{self.timestamp}|{self.user_id}|{self.event_type}|{json.dumps(self.details)}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "severity": self.severity,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details
        }
```

```python
# services/audit_service.py (NEW)
"""Audit logging service for security events."""

import logging
from flask import request
from flask_login import current_user

from models import AuditLog, db

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging."""

    @staticmethod
    def log_event(event_type, event_category, severity, resource_type=None, resource_id=None,
                  action=None, details=None, previous_value=None, new_value=None):
        """Log an audit event."""
        try:
            user_id = current_user.id if current_user.is_authenticated else None

            log_entry = AuditLog(
                user_id=user_id,
                event_type=event_type,
                event_category=event_category,
                severity=severity,
                ip_address=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent') if request else None,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                details=details or {},
                previous_value=previous_value,
                new_value=new_value
            )

            # Compute tamper-detection hash
            log_entry.entry_hash = log_entry.compute_hash()

            db.session.add(log_entry)
            db.session.commit()

            logger.info(f"Audit log: {event_type} by {user_id or 'anonymous'}")

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't fail the original operation if logging fails

    @staticmethod
    def log_authentication(event_type, email, success, details=None):
        """Log authentication events."""
        AuditService.log_event(
            event_type=event_type,
            event_category="authentication",
            severity="info" if success else "warning",
            details={
                "email": email,
                "success": success,
                **(details or {})
            }
        )

    @staticmethod
    def log_authorization_failure(resource_type, resource_id, attempted_action):
        """Log authorization failures."""
        AuditService.log_event(
            event_type="authorization_denied",
            event_category="authorization",
            severity="warning",
            resource_type=resource_type,
            resource_id=resource_id,
            action=attempted_action
        )

    @staticmethod
    def log_user_management(action, target_user_id, details=None):
        """Log user management events."""
        AuditService.log_event(
            event_type=f"user_{action}",
            event_category="user_management",
            severity="info",
            resource_type="user",
            resource_id=target_user_id,
            action=action,
            details=details
        )

    @staticmethod
    def log_role_change(user_id, previous_roles, new_roles):
        """Log role changes."""
        AuditService.log_event(
            event_type="role_changed",
            event_category="authorization",
            severity="critical",
            resource_type="user",
            resource_id=user_id,
            action="update",
            previous_value={"is_admin": previous_roles.get("is_admin")},
            new_value={"is_admin": new_roles.get("is_admin")}
        )
```

**Integration Examples**:
```python
# routes/auth_routes.py
from services.audit_service import AuditService

@auth_bp.route("/login", methods=["POST"])
def login():
    # ... existing code ...
    if not user:
        AuditService.log_authentication("login_failed", email, False)
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    login_user(user)
    AuditService.log_authentication("login_success", email, True)
    return jsonify({"success": True}), 200

# routes/admin_routes.py
@admin_bp.route("/users", methods=["POST"])
def create_user():
    # ... existing code ...
    user = AuthService.create_user(email, password, display_name, is_admin)
    AuditService.log_user_management("created", user.id, details={"email": email, "is_admin": is_admin})
    return jsonify({"success": True, "user": user.to_dict()}), 201

@admin_bp.route("/users/<user_id>/role", methods=["PATCH"])
def update_user_role(user_id):
    # ... existing code ...
    user = AuthService.get_user_by_id(user_id)
    previous_is_admin = user.is_admin

    user = AuthService.update_user(user_id, is_admin=is_admin)
    AuditService.log_role_change(user_id, {"is_admin": previous_is_admin}, {"is_admin": is_admin})
    return jsonify({"success": True}), 200
```

---

#### 2.2 Session Fixation Prevention

**Estimated Time**: 2 hours

```python
# routes/auth_routes.py
from flask import session

@auth_bp.route("/login", methods=["POST"])
def login():
    user = AuthService.authenticate(email, password)

    if not user:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    # Clear old session data
    session.clear()

    # Login user (creates new session)
    login_user(user, remember=data.get("remember_me", False))

    # Force session ID regeneration
    session.modified = True

    logger.info(f"User logged in: {email}")
    return jsonify({"success": True, "user": user.to_dict()}), 200
```

---

#### 2.3 CORS Configuration

**Estimated Time**: 1 hour

```bash
# Install Flask-CORS
echo "Flask-CORS==4.0.0" >> requirements.txt
pip install Flask-CORS==4.0.0
```

```python
# app.py
from flask_cors import CORS

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
        "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRFToken"],
        "expose_headers": ["Content-Type", "X-CSRFToken"],
        "supports_credentials": True,
        "max_age": 3600
    }
})
```

```bash
# .env
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

#### 2.4 Dependency Vulnerability Scanning

**Estimated Time**: 2 hours setup + ongoing

```bash
# Install safety
pip install safety

# Run scan
safety check --json > security-report.json
safety check --full-report

# Add to CI/CD pipeline
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run safety check
        run: |
          pip install safety
          safety check --json
```

---

#### 2.5 Structured Logging with Rotation

**Estimated Time**: 3 hours

```python
# logging_config.py (NEW)
"""Centralized logging configuration."""

import logging
import logging.handlers
import os
from datetime import datetime


def configure_logging(app):
    """Configure structured logging with rotation."""

    # Create logs directory
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Set log level
    log_level = os.getenv("LOG_LEVEL", "INFO")
    app.logger.setLevel(getattr(logging, log_level))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)

    # Security event handler
    security_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "security.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=30  # Keep 30 days of security logs
    )
    security_handler.setLevel(logging.WARNING)

    # JSON formatter for structured logging
    json_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
    )

    console_handler.setFormatter(json_formatter)
    file_handler.setFormatter(json_formatter)
    security_handler.setFormatter(json_formatter)

    # Add handlers
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)

    # Security logger
    security_logger = logging.getLogger("security")
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)

    return app
```

```python
# app.py
from logging_config import configure_logging

configure_logging(app)
```

---

### Phase 3: MEDIUM Priority (Post-Launch) - 1-2 Weeks

#### 3.1 Constant-Time Password Comparison

**Estimated Time**: 2 hours

```python
# services/auth_service.py
import time
import random

@staticmethod
def authenticate(email, password):
    """Authenticate user with timing-attack protection."""
    email = AuthService.validate_email(email)

    # Always hash a dummy password to maintain constant time
    dummy_hash = generate_password_hash("dummy_password_for_timing_protection")

    user = User.query.filter_by(email=email).first()

    if user and user.is_active and not user.is_locked():
        password_valid = check_password_hash(user.password_hash, password)
    else:
        # Perform dummy verification to maintain constant time
        check_password_hash(dummy_hash, password)
        password_valid = False

    # Add small random delay to further obscure timing
    time.sleep(random.uniform(0.01, 0.05))

    if user and password_valid:
        user.reset_failed_login()
        logger.info(f"User authenticated: {email}")
        return user
    elif user:
        user.increment_failed_login()
        logger.warning(f"Authentication failed: {email}")

    return None
```

---

#### 3.2 AI Usage Quota Enforcement

**Estimated Time**: 4 hours

```python
# services/usage_tracking_service.py - Implement quota checks
class UsageTrackingService:
    @staticmethod
    def check_quota(user_id, provider, tokens_needed):
        """Check if user has quota for operation."""
        from models import AIProviderQuota, UsageRecord
        from datetime import datetime, timedelta, timezone

        # Get quota for provider
        quota = AIProviderQuota.query.filter_by(user_id=user_id, provider=provider).first()

        if not quota:
            # No quota configured - allow unlimited
            return True

        if quota.limit_value == -1:
            # Unlimited quota
            return True

        # Calculate current period usage
        now = datetime.now(timezone.utc)

        if quota.reset_period == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif quota.reset_period == "weekly":
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif quota.reset_period == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # unlimited
            return True

        # Sum usage in current period
        current_usage = db.session.query(db.func.sum(UsageRecord.tokens_consumed)).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.provider == provider,
            UsageRecord.timestamp >= period_start
        ).scalar() or 0

        # Check if adding new usage exceeds quota
        if current_usage + tokens_needed > quota.limit_value:
            logger.warning(f"Quota exceeded for user {user_id}, provider {provider}")
            return False

        return True
```

---

#### 3.3 Two-Factor Authentication (2FA)

**Estimated Time**: 8 hours

```bash
# Install pyotp for TOTP
echo "pyotp==2.9.0" >> requirements.txt
pip install pyotp==2.9.0
```

```python
# models.py - Add 2FA fields
class User(db.Model):
    # ... existing fields ...
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)
    two_factor_backup_codes = db.Column(db.JSON, nullable=True)  # Encrypted backup codes

    def enable_2fa(self):
        """Enable 2FA and generate secret."""
        import pyotp
        self.two_factor_secret = pyotp.random_base32()
        self.two_factor_enabled = True

        # Generate backup codes
        import secrets
        self.two_factor_backup_codes = [
            secrets.token_hex(4) for _ in range(10)
        ]

        db.session.commit()
        return self.two_factor_secret

    def verify_2fa(self, token):
        """Verify TOTP token."""
        import pyotp
        if not self.two_factor_enabled:
            return True

        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 time-step variance
```

---

### Phase 4: Monitoring & Documentation (Ongoing)

#### 4.1 Security Monitoring Dashboard

**Estimated Time**: 8 hours

Create admin dashboard showing:
- Failed login attempts (last 24 hours)
- Locked accounts
- Active sessions
- Recent audit log events
- Quota usage per user
- Security alerts

#### 4.2 Documentation

**Estimated Time**: 6 hours

Create comprehensive security documentation:
- DEPLOYMENT_SECURITY.md (production deployment checklist)
- SECURITY_CHECKLIST.md (pre-production validation)
- INCIDENT_RESPONSE.md (security incident procedures)
- API_SECURITY.md (API security best practices for developers)

---

## Testing Strategy

### Security Test Suite

```python
# tests/security/test_security_suite.py
"""Comprehensive security test suite."""

import pytest


class TestAuthenticationSecurity:
    """Authentication security tests."""

    def test_rate_limiting(self, client):
        """Test login rate limiting."""
        # Attempt 6 logins
        for i in range(6):
            response = client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': f'wrong{i}'
            })
            if i < 5:
                assert response.status_code in [400, 401]
            else:
                assert response.status_code == 429

    def test_account_lockout(self, client, test_user):
        """Test account lockout after 5 failed attempts."""
        # 5 failed attempts
        for _ in range(5):
            client.post('/api/auth/login', json={
                'email': test_user.email,
                'password': 'wrong'
            })

        # 6th attempt with correct password should fail (locked)
        response = client.post('/api/auth/login', json={
            'email': test_user.email,
            'password': 'correct_password'
        })
        assert response.status_code == 401

    def test_csrf_protection(self, client):
        """Test CSRF token validation."""
        response = client.post('/api/admin/users', json={
            'email': 'test@example.com',
            'password': 'Test1234!'
        })
        assert response.status_code == 400  # CSRF validation failed

    def test_session_fixation(self, client, test_user):
        """Test session ID changes after login."""
        # Get initial session
        response = client.get('/api/auth/session')
        initial_cookie = response.headers.get('Set-Cookie')

        # Login
        client.post('/api/auth/login', json={
            'email': test_user.email,
            'password': 'password'
        })

        # Get new session
        response = client.get('/api/auth/session')
        new_cookie = response.headers.get('Set-Cookie')

        assert initial_cookie != new_cookie  # Session ID changed


class TestAuthorizationSecurity:
    """Authorization security tests."""

    def test_unauthorized_project_access(self, client, user1, user2):
        """Test users cannot access each other's projects."""
        # User1 creates project
        login_as(client, user1)
        project = create_project(client)

        # User2 tries to access
        login_as(client, user2)
        response = client.get(f'/api/jobs/{project.id}')
        assert response.status_code == 403

    def test_unauthorized_share(self, client, user1, user2):
        """Test users cannot share projects they don't own."""
        # User1 creates project
        login_as(client, user1)
        project = create_project(client)

        # User2 tries to share it
        login_as(client, user2)
        response = client.post(f'/api/projects/{project.id}/shares', json={
            'user_id': user2.id,
            'permission_level': 'write'
        })
        assert response.status_code == 403


class TestDataProtectionSecurity:
    """Data protection tests."""

    def test_password_hashing(self):
        """Test passwords are hashed with bcrypt."""
        from werkzeug.security import generate_password_hash, check_password_hash

        password = "Test1234!"
        hashed = generate_password_hash(password)

        assert password != hashed
        assert check_password_hash(hashed, password)
        assert not check_password_hash(hashed, "wrong")

    def test_session_cookies_secure(self, app):
        """Test session cookies have secure flags."""
        assert app.config['SESSION_COOKIE_SECURE'] == True
        assert app.config['SESSION_COOKIE_HTTPONLY'] == True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


class TestSecurityHeaders:
    """Security header tests."""

    def test_security_headers_present(self, client):
        """Test all security headers are set."""
        response = client.get('/api/auth/session')

        assert 'Content-Security-Policy' in response.headers
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
```

---

## Deployment Checklist

### Pre-Production Validation

```markdown
# SECURITY_DEPLOYMENT_CHECKLIST.md

## CRITICAL (Must be completed before production)
- [ ] CSRF protection enabled and tested
- [ ] Rate limiting configured on all auth endpoints
- [ ] Account lockout implemented (5 attempts, 30 min lockout)
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)
- [ ] Password reset moved to database storage
- [ ] Project ownership verification in all sharing routes
- [ ] SECRET_KEY validation on startup
- [ ] Debug code removed or properly gated
- [ ] HTTPS enforced in production
- [ ] Database connections using SSL/TLS

## HIGH PRIORITY (Complete during launch week)
- [ ] Audit logging implemented for sensitive operations
- [ ] Session fixation prevention
- [ ] CORS properly configured
- [ ] Dependency vulnerability scan passed
- [ ] Log rotation configured
- [ ] Security monitoring enabled

## MEDIUM PRIORITY (Complete post-launch)
- [ ] Constant-time password comparison
- [ ] Quota enforcement for AI usage
- [ ] 2FA for admin accounts
- [ ] Explicit bcrypt rounds configuration (14+)

## VERIFICATION
- [ ] All security tests passing
- [ ] Penetration testing completed
- [ ] Security review by external expert
- [ ] Incident response plan documented
```

---

## Success Metrics

### Security Posture Improvement
- **Before**: MODERATE RISK (8 Critical, 12 High, 9 Medium issues)
- **After Phase 1**: LOW RISK (0 Critical, 2-3 High, 5 Medium issues)
- **After Phase 2**: VERY LOW RISK (0 Critical, 0 High, 2-3 Medium issues)
- **After Phase 3**: PRODUCTION READY

### Compliance Achievement
- **OWASP Top 10**: Full coverage
- **GDPR**: Basic compliance (data protection, audit trail)
- **SOC 2**: Audit logging, access controls, incident response

---

## Timeline Summary

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| Phase 1 (Critical) | 2-3 days | BLOCKS PRODUCTION |
| Phase 2 (High) | 2-3 days | LAUNCH WEEK |
| Phase 3 (Medium) | 1-2 weeks | POST-LAUNCH |
| Phase 4 (Monitoring) | Ongoing | CONTINUOUS |

**Total Time to Production-Ready**: 4-6 days (Phases 1+2)

---

**Next Steps**:
1. Review and prioritize remediation items
2. Assign owners for each phase
3. Begin Phase 1 implementation
4. Schedule security review after Phase 1
5. Plan penetration testing after Phase 2

**Document Owner**: Security Engineering Team
**Review Frequency**: After each phase completion
**Reassessment**: After all Critical and High issues resolved
