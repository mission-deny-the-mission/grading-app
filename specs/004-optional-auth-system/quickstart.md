# Quick Start Guide: Optional Multi-User Authentication

**Feature**: 004-optional-auth-system
**Date**: 2025-11-15
**Target Audience**: Developers implementing this feature

## Overview

This guide provides a step-by-step walkthrough for implementing optional multi-user authentication with AI usage controls and project sharing. Follow the TDD workflow: write tests first, then implement to make them pass.

## Prerequisites

- Existing grading-app codebase
- Python 3.13.7 environment
- Flask-SQLAlchemy configured
- Familiarity with Flask blueprints and Flask-Login

## Installation

### 1. Install Dependencies

Add to `requirements.txt`:
```txt
Flask-Login==0.6.3
email-validator==2.2.0
```

Install:
```bash
pip install Flask-Login==0.6.3 email-validator==2.2.0
```

### 2. Run Database Migrations

```bash
# Create migration scripts
flask db migrate -m "Add authentication tables"

# Review generated migration (check auto-detected changes)
cat migrations/versions/[latest]_add_authentication_tables.py

# Apply migrations
flask db upgrade
```

## Implementation Phases

### Phase 1: Core Authentication (P1 - Critical)

**Goal**: Basic single-user and multi-user deployment modes with login/logout

#### Step 1.1: Write Tests First

Create `tests/unit/test_auth_service.py`:
```python
import pytest
from werkzeug.security.generate_password_hash
from services.auth_service import AuthService
from models import User

def test_create_user():
    """Test user creation with password hashing"""
    auth = AuthService()
    user = auth.create_user(
        email="test@example.com",
        password="SecurePass123"
    )
    assert user.email == "test@example.com"
    assert user.password_hash != "SecurePass123"  # Should be hashed
    assert len(user.password_hash) > 50  # PBKDF2 hash is long

def test_verify_password():
    """Test password verification"""
    auth = AuthService()
    user = auth.create_user("test@example.com", "SecurePass123")

    assert auth.verify_password(user, "SecurePass123") is True
    assert auth.verify_password(user, "WrongPass") is False

def test_duplicate_email():
    """Test email uniqueness constraint"""
    auth = AuthService()
    auth.create_user("test@example.com", "pass123")

    with pytest.raises(ValueError, match="Email already exists"):
        auth.create_user("test@example.com", "pass456")
```

**Run tests (they will fail)**:
```bash
python -m pytest tests/unit/test_auth_service.py -v
```

#### Step 1.2: Implement to Pass Tests

Create `backend/src/services/auth_service.py`:
```python
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from email_validator import validate_email, EmailNotValidError

class AuthService:
    def create_user(self, email, password, display_name=None, is_admin=False):
        """Create new user with hashed password"""
        # Validate email
        try:
            validated = validate_email(email)
            email = validated.email.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")

        # Check for existing user
        existing = User.query.filter_by(email=email).first()
        if existing:
            raise ValueError("Email already exists")

        # Hash password
        password_hash = generate_password_hash(password)

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            is_admin=is_admin
        )
        db.session.add(user)
        db.session.commit()
        return user

    def verify_password(self, user, password):
        """Verify password against hash"""
        return check_password_hash(user.password_hash, password)
```

**Run tests again (should pass)**:
```bash
python -m pytest tests/unit/test_auth_service.py -v
```

#### Step 1.3: Integration Tests

Create `tests/integration/test_auth_flow.py`:
```python
def test_login_flow(client):
    """Test complete login flow"""
    # Setup: Create test user
    auth = AuthService()
    auth.create_user("test@example.com", "TestPass123")

    # Login
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'TestPass123'
    })
    assert response.status_code == 200
    assert 'user' in response.json

    # Access protected resource
    response = client.get('/api/usage/dashboard')
    assert response.status_code == 200  # Authenticated

    # Logout
    response = client.post('/api/auth/logout')
    assert response.status_code == 200

    # Access protected resource again (should fail)
    response = client.get('/api/usage/dashboard')
    assert response.status_code == 401  # Unauthorized
```

#### Step 1.4: Implement Routes

Create `backend/src/api/auth_routes.py`:
```python
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService
from models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
auth_service = AuthService()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not auth_service.verify_password(user, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    login_user(user, remember=data.get('remember_me', False))
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})
```

### Phase 2: AI Usage Tracking (P2 - High Priority)

#### Step 2.1: Write Usage Tracking Tests

Create `tests/unit/test_usage_tracking.py`:
```python
def test_record_usage():
    """Test usage recording"""
    tracker = UsageTrackingService()
    user = create_test_user()

    record = tracker.record_usage(
        user_id=user.id,
        provider='openrouter',
        tokens_consumed=1500,
        operation_type='grading'
    )

    assert record.user_id == user.id
    assert record.tokens_consumed == 1500

def test_check_quota_under_limit():
    """Test quota check when under limit"""
    tracker = UsageTrackingService()
    user = create_test_user()

    # Set quota: 10000 tokens/month
    set_user_quota(user.id, 'openrouter', 10000, 'monthly')

    # Use 5000 tokens
    tracker.record_usage(user.id, 'openrouter', 5000, 'grading')

    # Check if can use 3000 more (should pass)
    can_use = tracker.check_quota(user.id, 'openrouter', 3000)
    assert can_use is True

def test_check_quota_over_limit():
    """Test quota enforcement when over limit"""
    tracker = UsageTrackingService()
    user = create_test_user()

    # Set quota: 10000 tokens/month
    set_user_quota(user.id, 'openrouter', 10000, 'monthly')

    # Use 9500 tokens
    tracker.record_usage(user.id, 'openrouter', 9500, 'grading')

    # Check if can use 1000 more (should fail)
    can_use = tracker.check_quota(user.id, 'openrouter', 1000)
    assert can_use is False
```

#### Step 2.2: Implement Usage Tracking Service

Create `backend/src/services/usage_tracking_service.py`:
```python
from datetime import datetime, timedelta, timezone
from models import db, UsageRecord, AIProviderQuota
from sqlalchemy import func

class UsageTrackingService:
    def record_usage(self, user_id, provider, tokens_consumed, operation_type, project_id=None, model_name=None):
        """Record AI usage"""
        record = UsageRecord(
            user_id=user_id,
            provider=provider,
            tokens_consumed=tokens_consumed,
            timestamp=datetime.now(timezone.utc),
            project_id=project_id,
            operation_type=operation_type,
            model_name=model_name
        )
        db.session.add(record)
        db.session.commit()
        return record

    def check_quota(self, user_id, provider, estimated_tokens):
        """Check if user can consume estimated tokens"""
        quota = AIProviderQuota.query.filter_by(
            user_id=user_id,
            provider=provider
        ).first()

        if not quota:
            return True  # No quota set = unlimited

        if quota.limit_value == -1:
            return True  # Unlimited quota

        # Calculate current usage for period
        period_start = self._get_period_start(quota.reset_period)
        current_usage = db.session.query(
            func.sum(UsageRecord.tokens_consumed)
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.provider == provider,
            UsageRecord.timestamp >= period_start
        ).scalar() or 0

        # Check if adding estimated tokens would exceed limit
        return (current_usage + estimated_tokens) <= quota.limit_value

    def _get_period_start(self, reset_period):
        """Calculate period start datetime"""
        now = datetime.now(timezone.utc)
        if reset_period == 'daily':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif reset_period == 'weekly':
            return now - timedelta(days=now.weekday())
        elif reset_period == 'monthly':
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # unlimited
            return datetime.min.replace(tzinfo=timezone.utc)
```

### Phase 3: Project Sharing (P3 - Medium Priority)

#### Step 3.1: Write Sharing Tests

Create `tests/integration/test_project_sharing.py`:
```python
def test_share_project_read_access():
    """Test sharing project with read access"""
    # Create owner and recipient users
    owner = create_test_user('owner@example.com')
    recipient = create_test_user('recipient@example.com')

    # Create project as owner
    project = create_test_project(owner_id=owner.id)

    # Share with recipient (read access)
    sharing = SharingService()
    share = sharing.share_project(
        project_id=project.id,
        user_email=recipient.email,
        permission_level='read',
        granted_by=owner.id
    )

    # Recipient can view project
    assert sharing.can_access_project(recipient.id, project.id) is True

    # Recipient cannot modify project
    assert sharing.can_modify_project(recipient.id, project.id) is False
```

## Development Workflow

### 1. TDD Cycle for Each Component

```bash
# 1. Write test
vim tests/unit/test_component.py

# 2. Run test (should fail - RED)
python -m pytest tests/unit/test_component.py -v

# 3. Implement minimum code to pass
vim backend/src/services/component.py

# 4. Run test (should pass - GREEN)
python -m pytest tests/unit/test_component.py -v

# 5. Refactor while keeping tests green
# Run tests after each refactor
```

### 2. Integration Testing

```bash
# Run all tests for the feature
python -m pytest tests/unit/ tests/integration/ -v --cov=backend/src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 3. Manual Testing Checklist

**Single-User Mode**:
- [ ] Start app without `DEPLOYMENT_MODE` env var
- [ ] Access `/` without login prompt
- [ ] Create grading project successfully
- [ ] Make AI requests without limits

**Multi-User Mode**:
- [ ] Set `DEPLOYMENT_MODE=multi-user`
- [ ] Access `/` → redirected to `/login`
- [ ] Create user via admin panel
- [ ] Login with credentials
- [ ] Create grading project → project owned by user
- [ ] Access usage dashboard → see quotas

**Usage Enforcement**:
- [ ] Set user quota to 100 tokens
- [ ] Make AI requests consuming 50 tokens → success
- [ ] Make AI request consuming 60 tokens → blocked (quota exceeded)
- [ ] View usage dashboard → shows 50/100 used

**Project Sharing**:
- [ ] Login as User A
- [ ] Create project
- [ ] Share with User B (read access)
- [ ] Login as User B
- [ ] See shared project in list
- [ ] View project → success
- [ ] Try to edit project → error (read-only)

## Common Issues & Solutions

### Issue: Migration Fails with "table already exists"

**Solution**: Check if running migrations on existing database
```bash
# Reset migrations (development only!)
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration with auth tables"
flask db upgrade
```

### Issue: Login fails with "User not found"

**Solution**: Check deployment mode configuration
```python
# In Python shell
from models import DeploymentConfig
config = DeploymentConfig.query.first()
print(config.mode)  # Should be 'multi-user'
```

### Issue: Tests fail with "DetachedInstanceError"

**Solution**: Add `expire_on_commit=False` to session options (already in models.py)
```python
db = SQLAlchemy(session_options={"expire_on_commit": False})
```

## Next Steps

After completing implementation:

1. **Run full test suite**: `python -m pytest tests/ -v --cov=backend/src`
2. **Check coverage**: Ensure ≥80% for new code
3. **Manual testing**: Follow checklist above
4. **Code review**: Submit PR with test results
5. **Documentation**: Update main README with deployment modes

## Reference Implementation

See existing patterns in codebase:
- **Models**: `models.py` (SavedPrompt, GradingJob examples)
- **Services**: `utils/llm_providers.py` (service layer pattern)
- **Routes**: `routes/api.py` (blueprint registration)
- **Tests**: `tests/test_models.py` (model testing patterns)

## Performance Optimization

### Database Query Optimization

```python
# Bad: N+1 query
users = User.query.all()
for user in users:
    quotas = user.ai_quotas  # Lazy load

# Good: Eager loading
from sqlalchemy.orm import joinedload
users = User.query.options(joinedload(User.ai_quotas)).all()
```

### Caching Usage Calculations

```python
# Cache quota check result in request context
from flask import g

def get_user_quota_cached(user_id, provider):
    cache_key = f"quota_{user_id}_{provider}"
    if not hasattr(g, cache_key):
        quota = calculate_quota(user_id, provider)
        setattr(g, cache_key, quota)
    return getattr(g, cache_key)
```

## Deployment Checklist

Before deploying to production:

- [ ] All migrations tested on staging database
- [ ] Rollback migrations tested
- [ ] Environment variables documented
- [ ] Session secret key configured (production-strength)
- [ ] HTTPS enforced (secure cookies)
- [ ] Database backup verified
- [ ] Monitoring configured (Sentry/logging)
- [ ] Load testing completed (100 concurrent users)

---

**Questions?** Refer to:
- [Data Model](./data-model.md) - Entity definitions
- [API Contract](./contracts/openapi.yaml) - Endpoint specifications
- [Research](./research.md) - Technical decisions and rationale
