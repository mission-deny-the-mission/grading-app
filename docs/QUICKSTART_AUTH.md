# Quick Start: Complete the Auth Implementation

## Current Status ✅
- Environment: Set up and ready
- Tests: 45/45 passing
- Backend: Implemented
- Frontend: Not yet started
- Database: Migrations not created
- Overall: ~50% complete

---

## Quick Commands

### Activate Environment
```bash
cd /home/harry/grading-app-auth
source venv_test/bin/activate
export TESTING=True
```

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/unit/test_auth_service.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Verify Current State
```bash
# Check 45 tests passing
pytest tests/ -q
# Expected: 45 passed

# Check models load
python -c "from models import User, DeploymentConfig; print('✓ Models loaded')"

# Check services work
python -c "from services.auth_service import AuthService; print('✓ Services loaded')"
```

---

## The 5 Phases (In Order)

### Phase 1: Database Migrations (2-3 hours) 🔴 NEXT
```bash
source venv_test/bin/activate
export TESTING=True
flask db init
flask db migrate -m "Add auth models"
flask db upgrade
```
**Then**: Run `pytest tests/integration/test_database.py -v`

### Phase 2: Complete Test Coverage (4-5 hours)
Write 35+ additional tests:
- Usage tracking (13 tests)
- Sharing service (8 tests)
- Auth flow (10 tests)
- Usage enforcement (3 tests)
- Project sharing (4 tests)
- API contracts (15 tests)

**Target**: 80+ tests passing, 70%+ coverage

### Phase 3: Frontend Implementation (3-4 hours)
Create 10 components:
- LoginForm, UsageDashboard, ProjectSharingPanel (3 components)
- LoginPage, SetupPage, UsageReportsPage (3 pages)
- 4 API client services (authClient, configClient, usageClient, sharingClient)

### Phase 4: Polish & Optimization (2-3 hours)
- Error handling standardization
- Rate limiting (login attempts)
- Password reset flow
- Timezone support
- Documentation

### Phase 5: Validation (1-2 hours)
- Full test suite run
- Manual integration testing
- Final documentation
- Commit and push

---

## File Structure Reference

```
backend/
├── models.py                 ✅ Complete (6 auth models)
├── services/
│   ├── auth_service.py       ✅ Complete
│   ├── deployment_service.py ✅ Complete
│   ├── usage_tracking_service.py ✅ Complete
│   └── sharing_service.py    ✅ Complete
├── routes/
│   ├── auth_routes.py        ✅ Complete
│   ├── config_routes.py      ✅ Complete
│   ├── usage_routes.py       ✅ Complete
│   └── sharing_routes.py     ✅ Complete
└── middleware/
    └── auth_middleware.py    ✅ Complete

frontend/
├── src/
│   ├── components/           ⏳ TODO (3 components)
│   ├── pages/                ⏳ TODO (3 pages)
│   └── services/             ⏳ TODO (4 clients)

tests/
├── unit/
│   ├── test_auth_service.py        ✅ 19 tests passing
│   ├── test_deployment_service.py  ✅ 12 tests passing
│   ├── test_usage_tracking.py      ⏳ TODO (13 tests)
│   ├── test_sharing_service.py     ⏳ TODO (8 tests)
│   └── test_usage_edge_cases.py    ⏳ TODO (6 tests)
├── integration/
│   ├── test_deployment_modes.py    ✅ 14 tests passing
│   ├── test_auth_flow.py           ⏳ TODO (10 tests)
│   ├── test_usage_enforcement.py   ⏳ TODO (3 tests)
│   ├── test_project_sharing.py     ⏳ TODO (4 tests)
│   └── test_database.py            ⏳ TODO (6 tests)
└── contract/
    ├── test_auth_api.py            ⏳ TODO (5 tests)
    ├── test_usage_api.py           ⏳ TODO (5 tests)
    └── test_sharing_api.py         ⏳ TODO (5 tests)
```

---

## One-Liner Status Checks

```bash
# Check venv is active
python -c "import sys; print('✓ venv active' if 'venv_test' in sys.prefix else '✗ venv not active')"

# Check TESTING env is set
python -c "import os; print('✓ TESTING set' if os.getenv('TESTING') else '✗ TESTING not set')"

# Check all current tests pass
pytest tests/ -q

# Check database exists
test -f grading_app.db && echo "✓ DB exists" || echo "✗ DB missing"

# Check migrations directory
test -d migrations && echo "✓ Migrations init" || echo "✗ Migrations not init"
```

---

## Common Issues & Fixes

**Issue**: `ModuleNotFoundError: No module named 'flask_login'`
```bash
# Fix: Activate venv
source venv_test/bin/activate
```

**Issue**: Tests fail with email validation error
```bash
# Fix: Set TESTING env var
export TESTING=True
```

**Issue**: Database migration fails
```bash
# Fix: Initialize Flask-Migrate first
flask db init
# Then:
flask db migrate -m "message"
flask db upgrade
```

**Issue**: "Ambiguous foreign key" error
```bash
# Already fixed in models.py - should not occur
# But if it does, check ProjectShare relationships
```

---

## Progress Tracking

Use this to track completion:

```bash
# After Phase 1 complete, should see:
pytest tests/integration/test_database.py -v
# 6 tests passing (database integrity)

# After Phase 2 complete, should see:
pytest tests/ -q
# 80+ tests passing
# 70%+ coverage

# After Phase 3 complete:
# Frontend components render without errors
# All API clients functional

# After Phase 4 complete:
# All services have error handling
# Rate limiting works
# Password reset functional

# After Phase 5 complete:
pytest tests/ -q
# All tests passing (100%)
# Ready for production
```

---

## Next Action

Run this to start Phase 1:

```bash
cd /home/harry/grading-app-auth
source venv_test/bin/activate
export TESTING=True

# Initialize migrations
flask db init

# Show what was created
ls -la migrations/

# Create migration
flask db migrate -m "Add authentication models (users, sessions, quotas, usage, sharing)"

# Review migration
cat migrations/versions/*.py

# Apply migration
flask db upgrade

# Verify
sqlite3 grading_app.db ".tables"

# Test
pytest tests/integration/test_database.py -v
```

---

## Resources

- **Full Plan**: `claudedocs/IMPLEMENTATION_PLAN.md`
- **Current Status**: `claudedocs/004-auth-implementation-status.md`
- **Task List**: `specs/004-optional-auth-system/tasks.md`
- **Spec**: `specs/004-optional-auth-system/spec.md`

---

**Last Updated**: 2025-11-15  
**Status**: Ready for Phase 1
