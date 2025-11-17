# Implementation Plan: Complete Optional Auth System (004)

**Current Status**: 50% complete, 45/45 tests passing  
**Target**: Full feature completion with frontend integration  
**Estimated Timeline**: 8-12 hours

---

## Phase 1: Database Setup & Migrations (HIGH PRIORITY)
**Effort**: 2-3 hours | **Blockers**: None | **Dependency**: None  
**Status**: ⏳ Pending

### Tasks

#### 1.1 Initialize Flask-Migrate
```bash
cd /home/harry/grading-app-auth
source venv_test/bin/activate
export TESTING=True
flask db init
```
**Outcome**: Creates `migrations/` directory with version control for database schema

#### 1.2 Create Migrations for Auth Models
```bash
flask db migrate -m "Add authentication models (users, sessions, quotas, usage, sharing)"
```
**What happens**:
- Auto-detects new models: User, DeploymentConfig, AIProviderQuota, UsageRecord, ProjectShare, AuthSession
- Generates migration files in `migrations/versions/`
- Detects changes to existing models (GradingJob owner_id, SavedPrompt owner_id)

**Checklist**:
- [ ] Verify migration file created in `migrations/versions/`
- [ ] Review migration file for correctness
- [ ] Check for foreign key relationships properly defined
- [ ] Verify indexes are created

#### 1.3 Apply Migrations to Database
```bash
flask db upgrade
```
**Outcome**: Database schema created with all auth tables

**Verification**:
```bash
sqlite3 grading_app.db ".tables"
# Should show: users, auth_sessions, ai_provider_quotas, usage_records, project_shares, deployment_config
```

#### 1.4 Test Database Integration
Create file: `tests/integration/test_database.py`
```python
def test_database_tables_created(app):
    """Verify all auth tables exist in database."""
    with app.app_context():
        from models import db
        # Check all tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        assert 'users' in tables
        assert 'auth_sessions' in tables
        assert 'ai_provider_quotas' in tables
        assert 'usage_records' in tables
        assert 'project_shares' in tables
        assert 'deployment_config' in tables
```

**Run test**:
```bash
pytest tests/integration/test_database.py -v
```

---

## Phase 2: Complete Test Coverage (HIGH PRIORITY)
**Effort**: 4-5 hours | **Blockers**: Database migrations | **Dependency**: Phase 1

### 2.1 Usage Tracking Tests
**File**: `tests/unit/test_usage_tracking.py`  
**Tests needed**: 13 tests (from tasks.md T082-T094)

```python
# Test structure
class TestUsageTrackingService:
    - test_record_usage_success()
    - test_record_usage_multiple_providers()
    - test_check_quota_under_limit()
    - test_check_quota_over_limit()
    - test_check_quota_at_limit()
    - test_get_current_usage()
    - test_period_calculation_daily()
    - test_period_calculation_monthly()
    - test_usage_aggregation()
    - test_80_percent_warning()
    - test_quota_exceeded_message()
```

**Run**:
```bash
pytest tests/unit/test_usage_tracking.py -v
```

### 2.2 Sharing Service Tests
**File**: `tests/unit/test_sharing_service.py`  
**Tests needed**: 4 tests (from tasks.md T118-T121)

```python
class TestSharingService:
    - test_share_project_read_only()
    - test_share_project_read_write()
    - test_can_access_project_owner()
    - test_can_access_project_shared()
    - test_can_modify_project_write_permission()
    - test_can_modify_project_read_only()
    - test_revoke_share()
    - test_prevent_self_sharing()
```

**Run**:
```bash
pytest tests/unit/test_sharing_service.py -v
```

### 2.3 Auth Flow Integration Tests
**File**: `tests/integration/test_auth_flow.py`  
**Tests needed**: 10 tests (from tasks.md T059-T062)

```python
class TestAuthFlow:
    - test_login_flow_success()
    - test_login_invalid_credentials()
    - test_logout_clears_session()
    - test_protected_resource_requires_login()
    - test_session_expiration()
    - test_session_activity_extends_timeout()
    - test_multi_user_workspace_isolation()
    - test_concurrent_logins()
```

**Run**:
```bash
pytest tests/integration/test_auth_flow.py -v
```

### 2.4 Usage Enforcement Integration Tests
**File**: `tests/integration/test_usage_enforcement.py`  
**Tests needed**: 3 tests (from tasks.md T092-T094)

```python
class TestUsageEnforcement:
    - test_usage_limit_blocks_requests()
    - test_80_percent_warning_displayed()
    - test_real_time_usage_updates()
```

### 2.5 Project Sharing Integration Tests
**File**: `tests/integration/test_project_sharing.py`  
**Tests needed**: 4 tests (from tasks.md T125-T128)

```python
class TestProjectSharing:
    - test_read_only_access()
    - test_read_write_access()
    - test_share_revocation()
    - test_shared_project_in_list()
```

### 2.6 API Contract Tests
**File**: `tests/contract/test_auth_api.py`, `test_usage_api.py`, `test_sharing_api.py`  
**Tests needed**: 15 tests validating request/response formats

```python
# Example structure
class TestAuthAPI:
    - test_login_endpoint_format()
    - test_logout_endpoint_format()
    - test_session_endpoint_format()

class TestUsageAPI:
    - test_dashboard_endpoint_format()
    - test_quotas_endpoint_format()
    - test_history_endpoint_format()

class TestSharingAPI:
    - test_shares_endpoint_format()
    - test_share_endpoint_format()
```

**Target**: 80%+ test coverage for auth-related code

---

## Phase 3: Frontend Implementation (MEDIUM PRIORITY)
**Effort**: 3-4 hours | **Blockers**: None | **Dependency**: Phases 1-2 (useful but not blocking)

### 3.1 Authentication UI Components
**Directory**: `frontend/src/components/` (create if not exists)

#### 3.1.1 LoginForm Component
**File**: `frontend/src/components/LoginForm.jsx`
```jsx
// Structure:
export function LoginForm({ onSuccess }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    // Call authClient.login()
    // On success: onSuccess callback
  }

  return (
    <form onSubmit={handleSubmit}>
      <input type="email" value={email} onChange={...} />
      <input type="password" value={password} onChange={...} />
      <button type="submit">Login</button>
      {error && <div className="error">{error}</div>}
    </form>
  )
}
```

#### 3.1.2 UsageDashboard Component
**File**: `frontend/src/components/UsageDashboard.jsx`
```jsx
export function UsageDashboard() {
  const [quotas, setQuotas] = useState([])
  const [usage, setUsage] = useState({})
  
  // Fetch dashboard data from API
  // Display usage bars, percentages, warnings
  // Poll for real-time updates (5-10 second intervals)
}
```

#### 3.1.3 ProjectSharingPanel Component
**File**: `frontend/src/components/ProjectSharingPanel.jsx`
```jsx
export function ProjectSharingPanel({ projectId }) {
  const [shares, setShares] = useState([])
  const [showShareForm, setShowShareForm] = useState(false)
  
  // List current shares
  // Add new shares (email + permission)
  // Revoke shares
}
```

### 3.2 Authentication Pages
**Directory**: `frontend/src/pages/` (create if not exists)

#### 3.2.1 LoginPage
**File**: `frontend/src/pages/LoginPage.jsx`
```jsx
export default function LoginPage() {
  const navigate = useNavigate()
  
  return (
    <div className="login-container">
      <h1>Login</h1>
      <LoginForm onSuccess={() => navigate('/dashboard')} />
    </div>
  )
}
```

#### 3.2.2 SetupPage (Deployment Mode Configuration)
**File**: `frontend/src/pages/SetupPage.jsx`
```jsx
export default function SetupPage() {
  const [mode, setMode] = useState('single-user')
  
  // Radio buttons for single-user vs multi-user
  // Submit to /api/config/deployment-mode
  // Show confirmation
}
```

#### 3.2.3 UsageReportsPage
**File**: `frontend/src/pages/UsageReportsPage.jsx`
```jsx
export default function UsageReportsPage() {
  // Admin-only page showing usage reports
  // Graphs, user stats, top consumers
}
```

### 3.3 API Client Services
**Directory**: `frontend/src/services/` (create if not exists)

#### 3.3.1 authClient.js
```javascript
export const authClient = {
  login: (email, password) => POST('/api/auth/login', { email, password }),
  logout: () => POST('/api/auth/logout'),
  getSession: () => GET('/api/auth/session'),
  isAuthenticated: async () => {
    try {
      await getSession()
      return true
    } catch {
      return false
    }
  }
}
```

#### 3.3.2 configClient.js
```javascript
export const configClient = {
  getDeploymentMode: () => GET('/api/config/deployment-mode'),
  setDeploymentMode: (mode) => POST('/api/config/deployment-mode', { mode }),
  getHealth: () => GET('/api/config/health')
}
```

#### 3.3.3 usageClient.js
```javascript
export const usageClient = {
  getDashboard: () => GET('/api/usage/dashboard'),
  getQuotas: () => GET('/api/usage/quotas'),
  setQuota: (userId, quota) => PUT(`/api/usage/quotas/${userId}`, quota),
  getHistory: (page = 1) => GET(`/api/usage/history?page=${page}`),
  getReports: () => GET('/api/usage/reports')
}
```

#### 3.3.4 sharingClient.js
```javascript
export const sharingClient = {
  listShares: (projectId) => GET(`/api/projects/${projectId}/shares`),
  shareProject: (projectId, data) => POST(`/api/projects/${projectId}/shares`, data),
  revokeShare: (projectId, shareId) => DELETE(`/api/projects/${projectId}/shares/${shareId}`)
}
```

### 3.4 Session Management
**File**: `frontend/src/services/sessionManager.js`

```javascript
// Session context/store for managing auth state globally
// Track: isLoggedIn, currentUser, deploymentMode
// Handle: login/logout, session expiration, mode switching
```

### 3.5 Route Protection
**File**: `frontend/src/components/ProtectedRoute.jsx`

```jsx
export function ProtectedRoute({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(null)
  
  useEffect(() => {
    authClient.getSession()
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false))
  }, [])
  
  if (isAuthenticated === null) return <Loading />
  if (!isAuthenticated) return <Navigate to="/login" />
  return children
}
```

---

## Phase 4: Polish & Optimization (MEDIUM PRIORITY)
**Effort**: 2-3 hours | **Blockers**: None | **Dependency**: Phases 1-3

### 4.1 Error Handling Standardization

**File**: `backend/src/errors.py`
```python
class AuthError(Exception):
    """Base authentication error"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code

class InvalidCredentialsError(AuthError):
    pass

class UserNotFoundError(AuthError):
    pass

class QuotaExceededError(AuthError):
    pass
```

**Apply to all services**:
- [ ] auth_service.py - Use custom errors
- [ ] deployment_service.py - Use custom errors
- [ ] usage_tracking_service.py - Use custom errors
- [ ] sharing_service.py - Use custom errors

### 4.2 Rate Limiting

**Dependencies**: `flask-limiter`
```bash
pip install flask-limiter
```

**File**: `middleware/rate_limiting.py`
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply to endpoints:
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per 15 minutes")  # 5 login attempts per 15 min
def login():
    pass
```

### 4.3 Password Reset Flow

**File**: `routes/auth_routes.py` - Add endpoints
```python
@auth_bp.route('/password-reset', methods=['POST'])
def request_password_reset():
    # 1. Validate email exists
    # 2. Generate reset token
    # 3. Send email with reset link
    # 4. Rate limit: 3 per hour

@auth_bp.route('/password-reset/<token>', methods=['POST'])
def reset_password(token):
    # 1. Validate token
    # 2. Hash new password
    # 3. Update user
```

**File**: `services/password_reset_service.py`
```python
class PasswordResetService:
    @staticmethod
    def request_reset(email):
        # Generate token, store in cache, send email
        pass
    
    @staticmethod
    def validate_token(token):
        # Check token validity and expiration
        pass
    
    @staticmethod
    def reset_password(token, new_password):
        # Validate token, update password
        pass
```

### 4.4 Usage Tracking Edge Cases

**File**: `tests/unit/test_usage_edge_cases.py`
```python
class TestUsageEdgeCases:
    - test_usage_with_timezone_boundary()
    - test_daily_reset_at_boundary()
    - test_monthly_reset_at_boundary()
    - test_concurrent_usage_recording()
    - test_deleted_user_quota()
    - test_invalid_provider_quota()
```

### 4.5 Timezone Handling

**File**: `services/timezone_service.py`
```python
class TimezoneService:
    @staticmethod
    def get_user_timezone(user):
        # Get from user profile or default to UTC
        pass
    
    @staticmethod
    def get_period_start(period_type, user):
        # daily: 00:00 user time
        # monthly: 1st of month at 00:00 user time
        pass
```

### 4.6 Documentation

**File**: `claudedocs/AUTH_API_GUIDE.md`
- API endpoint documentation
- Request/response examples
- Error codes and meanings
- Authentication flow diagrams

**File**: `claudedocs/FRONTEND_INTEGRATION.md`
- How to use auth components
- Session management examples
- Error handling patterns

**File**: `README.md` - Update with:
- Setup instructions
- Running tests
- Deployment modes
- Usage limits configuration

---

## Phase 5: Validation & Testing (HIGH PRIORITY)
**Effort**: 1-2 hours | **Blockers**: Phases 1-4 | **Dependency**: All phases

### 5.1 Full Test Suite Run
```bash
source venv_test/bin/activate
export TESTING=True

# Run all tests
pytest tests/ -v --cov=. --cov-report=html

# Expected:
# - Total tests: 80+
# - Coverage: 70%+
# - All tests passing
```

### 5.2 Integration Test
```bash
# Start app
flask run

# In another terminal, run integration tests
pytest tests/integration/ -v --tb=short
```

### 5.3 Manual Testing Checklist
- [ ] Start in single-user mode - access all features without login
- [ ] Switch to multi-user mode - login required
- [ ] Create user - validation works
- [ ] Login - session created
- [ ] Set usage limits - enforced
- [ ] Share project - works with read/write permissions
- [ ] View dashboard - usage displayed in real-time
- [ ] Logout - session cleared

---

## Execution Checklist

### Before Starting
- [ ] Activate venv: `source venv_test/bin/activate`
- [ ] Set env: `export TESTING=True`
- [ ] Verify current state: `pytest tests/ -v` (45/45 passing)

### Phase 1: Database
- [ ] `flask db init`
- [ ] `flask db migrate`
- [ ] `flask db upgrade`
- [ ] Verify tables: `sqlite3 grading_app.db ".tables"`
- [ ] Run database test: `pytest tests/integration/test_database.py -v`

### Phase 2: Tests
- [ ] Create `tests/unit/test_usage_tracking.py` (13 tests)
- [ ] Create `tests/unit/test_sharing_service.py` (8 tests)
- [ ] Create `tests/integration/test_auth_flow.py` (10 tests)
- [ ] Create `tests/integration/test_usage_enforcement.py` (3 tests)
- [ ] Create `tests/integration/test_project_sharing.py` (4 tests)
- [ ] Create `tests/contract/test_auth_api.py` (15 tests)
- [ ] Run all: `pytest tests/ -v` (target: 80+ tests passing)

### Phase 3: Frontend
- [ ] Create `frontend/src/components/LoginForm.jsx`
- [ ] Create `frontend/src/components/UsageDashboard.jsx`
- [ ] Create `frontend/src/components/ProjectSharingPanel.jsx`
- [ ] Create `frontend/src/pages/LoginPage.jsx`
- [ ] Create `frontend/src/pages/SetupPage.jsx`
- [ ] Create `frontend/src/pages/UsageReportsPage.jsx`
- [ ] Create `frontend/src/services/authClient.js`
- [ ] Create `frontend/src/services/configClient.js`
- [ ] Create `frontend/src/services/usageClient.js`
- [ ] Create `frontend/src/services/sharingClient.js`

### Phase 4: Polish
- [ ] Create `backend/src/errors.py`
- [ ] Implement rate limiting
- [ ] Implement password reset
- [ ] Test edge cases
- [ ] Add timezone support
- [ ] Write documentation

### Phase 5: Validation
- [ ] Run full test suite (target: 80+ tests, 70%+ coverage)
- [ ] Manual integration testing
- [ ] Update README.md
- [ ] Commit and push

---

## Time Estimates

| Phase | Tasks | Est. Time | Actual |
|-------|-------|-----------|--------|
| 1. Database | 4 tasks | 2-3h | |
| 2. Tests | 40+ tests | 4-5h | |
| 3. Frontend | 10 components | 3-4h | |
| 4. Polish | 6 tasks | 2-3h | |
| 5. Validation | 4 tasks | 1-2h | |
| **TOTAL** | **64 tasks** | **12-17h** | |

---

## Git Workflow

After each phase:
```bash
git add -A
git commit -m "Phase X: [description]"
git push origin 004-optional-auth-system
```

Example commits:
```
Phase 1: Initialize database migrations and apply schema
Phase 2: Implement comprehensive test coverage (80 tests)
Phase 3: Build frontend auth UI components
Phase 4: Add error handling, rate limiting, password reset
Phase 5: Validate implementation and complete documentation
```

---

## Success Criteria

✅ **Phase 1**: 
- Database tables exist and are accessible
- All relationships properly configured

✅ **Phase 2**: 
- 80+ tests written and passing
- 70%+ code coverage
- All user stories tested

✅ **Phase 3**: 
- All UI components render
- API clients work correctly
- Session management functional

✅ **Phase 4**: 
- Error handling consistent
- Rate limiting working
- Password reset flow complete

✅ **Phase 5**: 
- All tests pass (100%)
- Manual testing successful
- Documentation complete
- Ready for production

---

## Resources

- **Code**: `/home/harry/grading-app-auth/`
- **Tests**: `/home/harry/grading-app-auth/tests/`
- **Frontend**: `/home/harry/grading-app-auth/frontend/` (create if not exists)
- **Spec**: `/home/harry/grading-app-auth/specs/004-optional-auth-system/`
- **Tasks Reference**: `/home/harry/grading-app-auth/specs/004-optional-auth-system/tasks.md`

---

**Last Updated**: 2025-11-15  
**Status**: Plan ready for execution
