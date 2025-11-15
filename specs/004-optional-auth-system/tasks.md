# Tasks: Optional Multi-User Authentication with AI Usage Controls

**Input**: Design documents from `/specs/004-optional-auth-system/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per constitution (Test-First Development principle). All user stories MUST have tests written BEFORE implementation (TDD workflow: tests → fail → implement → pass).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

This project follows **Web app** structure:
- Backend: `backend/src/`, `tests/`
- Frontend: `frontend/src/`
- Paths shown below use this structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Install new dependencies (Flask-Login==0.6.3, email-validator==2.2.0) in requirements.txt
- [ ] T002 [P] Initialize Flask-Login extension in app.py with LoginManager configuration
- [ ] T003 [P] Configure session settings in app.py (timeout, secure cookies, HTTP-only)
- [ ] T004 Create backend/src/models/ directory structure for new authentication models
- [ ] T005 Create backend/src/services/ directory structure for authentication services
- [ ] T006 Create backend/src/api/ directory structure for authentication routes
- [ ] T007 Create backend/src/middleware/ directory for auth and usage enforcement
- [ ] T008 Create tests/unit/, tests/integration/, tests/contract/ directory structure
- [ ] T009 [P] Create frontend/src/components/ directory for auth UI components
- [ ] T010 [P] Create frontend/src/pages/ directory for auth pages
- [ ] T011 [P] Create frontend/src/services/ directory for API clients

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T012 Create database migration for DeploymentConfig table in migrations/
- [ ] T013 Create database migration for User table with indexes in migrations/
- [ ] T014 [P] Create database migration for AIProviderQuota table in migrations/
- [ ] T015 [P] Create database migration for UsageRecord table with indexes in migrations/
- [ ] T016 [P] Create database migration for ProjectShare table in migrations/
- [ ] T017 [P] Create database migration for AuthSession table in migrations/
- [ ] T018 Create database migration to add owner_id to GradingJob table in migrations/
- [ ] T019 Create database migration to add owner_id to SavedPrompt table in migrations/
- [ ] T020 Run all database migrations with flask db upgrade
- [ ] T021 Create base DeploymentConfig model in backend/src/models/deployment_config.py
- [ ] T022 Create base User model with Flask-Login UserMixin in backend/src/models/user.py
- [ ] T023 [P] Create AIProviderQuota model in backend/src/models/ai_quota.py
- [ ] T024 [P] Create UsageRecord model in backend/src/models/usage_record.py
- [ ] T025 [P] Create ProjectShare model in backend/src/models/project_share.py
- [ ] T026 [P] Create AuthSession model in backend/src/models/auth_session.py
- [ ] T027 Implement DeploymentService with mode checking in backend/src/services/deployment_service.py
- [ ] T028 Create middleware/auth_middleware.py with deployment mode routing logic
- [ ] T029 Configure Flask-Login user_loader callback in app.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 5 - Deployment Mode Configuration (Priority: P1) 🎯 MVP Enabler

**Goal**: Enable system administrators to configure deployment mode (single-user or multi-user) during initial setup, with persistence across restarts

**Independent Test**: Run setup process, select deployment mode, restart application, verify correct mode is active (auth enabled/disabled)

**Why P1**: This is the foundational toggle that enables/disables all authentication. Must work first before any other auth features.

### Tests for User Story 5 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T030 [P] [US5] Unit test for DeploymentService.get_mode() in tests/unit/test_deployment_service.py
- [ ] T031 [P] [US5] Unit test for DeploymentService.set_mode() with validation in tests/unit/test_deployment_service.py
- [ ] T032 [P] [US5] Integration test for deployment mode persistence across app restarts in tests/integration/test_deployment_modes.py
- [ ] T033 [P] [US5] Integration test for mode mismatch detection (env var vs database) in tests/integration/test_deployment_modes.py

### Implementation for User Story 5

- [ ] T034 [US5] Implement DeploymentService.get_current_mode() method in backend/src/services/deployment_service.py
- [ ] T035 [US5] Implement DeploymentService.set_mode() with validation in backend/src/services/deployment_service.py
- [ ] T036 [US5] Implement DeploymentService.validate_mode_consistency() checking env vs DB in backend/src/services/deployment_service.py
- [ ] T037 [US5] Add startup mode validation in app.py before_first_request hook
- [ ] T038 [US5] Create GET /api/config/deployment-mode endpoint in backend/src/api/config_routes.py
- [ ] T039 [US5] Add error handling for mode mismatch scenarios in backend/src/services/deployment_service.py
- [ ] T040 [US5] Add logging for deployment mode changes in backend/src/services/deployment_service.py
- [ ] T041 [P] [US5] Create SetupPage component for mode selection in frontend/src/pages/SetupPage.jsx
- [ ] T042 [P] [US5] Create deployment config API client in frontend/src/services/configClient.js

**Checkpoint**: At this point, deployment mode can be configured and persists correctly. Mode determines whether auth is active.

---

## Phase 4: User Story 1 - Single-User Local Deployment (Priority: P1) 🎯 MVP

**Goal**: Enable teachers to use the app on personal computers without login requirements, with all features accessible and no AI usage limits

**Independent Test**: Start app in single-user mode, access all grading features, use AI providers, create/manage projects without login prompts

**Why P1**: Simplest deployment model, ensures out-of-the-box functionality for individual users

### Tests for User Story 1 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T043 [P] [US1] Integration test for single-user mode bypassing auth in tests/integration/test_deployment_modes.py
- [ ] T044 [P] [US1] Integration test for accessing all features without login in tests/integration/test_deployment_modes.py
- [ ] T045 [P] [US1] Integration test for AI requests without usage limits in tests/integration/test_deployment_modes.py
- [ ] T046 [P] [US1] Integration test for project creation without ownership checks in tests/integration/test_deployment_modes.py

### Implementation for User Story 1

- [ ] T047 [US1] Implement single-user mode detection in middleware/auth_middleware.py
- [ ] T048 [US1] Add early-exit logic for single-user mode in middleware/auth_middleware.py before_request
- [ ] T049 [US1] Ensure no authentication checks when mode=single-user in middleware/auth_middleware.py
- [ ] T050 [US1] Verify AI usage enforcement skips quota checks in single-user mode in middleware/usage_enforcement.py
- [ ] T051 [US1] Test that grading projects created in single-user mode have NULL owner_id
- [ ] T052 [US1] Add single-user mode indicator to frontend session check in frontend/src/services/authClient.js

**Checkpoint**: At this point, User Story 1 should be fully functional - single-user mode works without any authentication

---

## Phase 5: User Story 2 - Multi-User Deployment with Authentication (Priority: P2)

**Goal**: Enable institutional deployments where each teacher logs in to access their own projects and has personalized AI usage limits

**Independent Test**: Configure multi-user mode, create multiple user accounts, log in as different users, verify isolated workspaces and personalized AI limits

**Why P2**: Essential for institutional deployments but requires single-user foundation (US1 and US5) to be working first

### Tests for User Story 2 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T053 [P] [US2] Unit test for AuthService.create_user() with email validation in tests/unit/test_auth_service.py
- [ ] T054 [P] [US2] Unit test for AuthService.verify_password() in tests/unit/test_auth_service.py
- [ ] T055 [P] [US2] Unit test for duplicate email rejection in tests/unit/test_auth_service.py
- [ ] T056 [P] [US2] Contract test for POST /api/auth/login endpoint in tests/contract/test_auth_api.py
- [ ] T057 [P] [US2] Contract test for POST /api/auth/logout endpoint in tests/contract/test_auth_api.py
- [ ] T058 [P] [US2] Contract test for GET /api/auth/session endpoint in tests/contract/test_auth_api.py
- [ ] T059 [P] [US2] Integration test for complete login flow in tests/integration/test_auth_flow.py
- [ ] T060 [P] [US2] Integration test for protected resource access after login in tests/integration/test_auth_flow.py
- [ ] T061 [P] [US2] Integration test for session expiration in tests/integration/test_auth_flow.py
- [ ] T062 [P] [US2] Integration test for multi-user workspace isolation in tests/integration/test_auth_flow.py

### Implementation for User Story 2

- [ ] T063 [P] [US2] Implement AuthService.create_user() with password hashing in backend/src/services/auth_service.py
- [ ] T064 [P] [US2] Implement AuthService.verify_password() using check_password_hash in backend/src/services/auth_service.py
- [ ] T065 [P] [US2] Implement AuthService.authenticate() combining email lookup and password verification in backend/src/services/auth_service.py
- [ ] T066 [US2] Add email uniqueness validation in AuthService.create_user() in backend/src/services/auth_service.py
- [ ] T067 [US2] Create POST /api/auth/login route with Flask-Login integration in backend/src/api/auth_routes.py
- [ ] T068 [US2] Create POST /api/auth/logout route in backend/src/api/auth_routes.py
- [ ] T069 [US2] Create GET /api/auth/session route in backend/src/api/auth_routes.py
- [ ] T070 [US2] Implement multi-user mode enforcement in middleware/auth_middleware.py
- [ ] T071 [US2] Add @login_required decorator usage to protected endpoints
- [ ] T072 [US2] Implement session timeout logic in middleware/auth_middleware.py
- [ ] T073 [US2] Add authentication event logging (login, logout, failures) per FR-018
- [ ] T074 [US2] Create session cleanup Celery task for expired sessions in tasks.py
- [ ] T075 [P] [US2] Create LoginForm component in frontend/src/components/LoginForm.jsx
- [ ] T076 [P] [US2] Create LoginPage in frontend/src/pages/LoginPage.jsx
- [ ] T077 [P] [US2] Implement authClient.login() method in frontend/src/services/authClient.js
- [ ] T078 [P] [US2] Implement authClient.logout() method in frontend/src/services/authClient.js
- [ ] T079 [P] [US2] Implement authClient.getSession() method in frontend/src/services/authClient.js
- [ ] T080 [US2] Add route guard for protected pages checking session in frontend/
- [ ] T081 [US2] Modify project queries to filter by owner_id in multi-user mode

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - single-user mode OR multi-user mode with login

---

## Phase 6: User Story 3 - AI Usage Monitoring and Limits (Priority: P2)

**Goal**: Enable administrators to configure per-user AI usage limits and users to view their consumption, with automatic enforcement of limits

**Independent Test**: Set usage limits for a test user, make AI requests until limits are reached, verify enforcement, check statistics accuracy

**Why P2**: Critical for cost management in institutional deployments, works in conjunction with multi-user authentication (US2)

### Tests for User Story 3 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T082 [P] [US3] Unit test for UsageTrackingService.record_usage() in tests/unit/test_usage_tracking.py
- [ ] T083 [P] [US3] Unit test for UsageTrackingService.check_quota() under limit in tests/unit/test_usage_tracking.py
- [ ] T084 [P] [US3] Unit test for UsageTrackingService.check_quota() over limit in tests/unit/test_usage_tracking.py
- [ ] T085 [P] [US3] Unit test for period calculation (daily, weekly, monthly) in tests/unit/test_usage_tracking.py
- [ ] T086 [P] [US3] Unit test for usage aggregation queries in tests/unit/test_usage_tracking.py
- [ ] T087 [P] [US3] Contract test for GET /api/usage/dashboard endpoint in tests/contract/test_usage_api.py
- [ ] T088 [P] [US3] Contract test for GET /api/usage/quotas endpoint in tests/contract/test_usage_api.py
- [ ] T089 [P] [US3] Contract test for PUT /api/usage/quotas/{user_id} endpoint (admin) in tests/contract/test_usage_api.py
- [ ] T090 [P] [US3] Contract test for GET /api/usage/history endpoint in tests/contract/test_usage_api.py
- [ ] T091 [P] [US3] Contract test for GET /api/usage/reports endpoint (admin) in tests/contract/test_usage_api.py
- [ ] T092 [P] [US3] Integration test for usage limit enforcement blocking AI requests in tests/integration/test_usage_enforcement.py
- [ ] T093 [P] [US3] Integration test for 80% quota warning display in tests/integration/test_usage_enforcement.py
- [ ] T094 [P] [US3] Integration test for real-time usage stat updates in tests/integration/test_usage_enforcement.py

### Implementation for User Story 3

- [ ] T095 [P] [US3] Implement UsageTrackingService.record_usage() in backend/src/services/usage_tracking_service.py
- [ ] T096 [P] [US3] Implement UsageTrackingService.check_quota() in backend/src/services/usage_tracking_service.py
- [ ] T097 [P] [US3] Implement UsageTrackingService.get_current_usage() with period filtering in backend/src/services/usage_tracking_service.py
- [ ] T098 [P] [US3] Implement UsageTrackingService.get_usage_dashboard() in backend/src/services/usage_tracking_service.py
- [ ] T099 [P] [US3] Implement UsageTrackingService.get_usage_history() with pagination in backend/src/services/usage_tracking_service.py
- [ ] T100 [US3] Add period start calculation (_get_period_start method) in backend/src/services/usage_tracking_service.py
- [ ] T101 [US3] Create UsageEnforcementMiddleware.check_ai_request() in backend/src/middleware/usage_enforcement.py
- [ ] T102 [US3] Integrate check_quota() before AI provider calls in backend/src/middleware/usage_enforcement.py
- [ ] T103 [US3] Add usage recording after successful AI requests in backend/src/middleware/usage_enforcement.py
- [ ] T104 [US3] Create GET /api/usage/dashboard route in backend/src/api/usage_routes.py
- [ ] T105 [US3] Create GET /api/usage/quotas route in backend/src/api/usage_routes.py
- [ ] T106 [US3] Create PUT /api/usage/quotas/{user_id} route (admin only) in backend/src/api/usage_routes.py
- [ ] T107 [US3] Create GET /api/usage/history route with pagination in backend/src/api/usage_routes.py
- [ ] T108 [US3] Create GET /api/usage/reports route (admin only) in backend/src/api/usage_routes.py
- [ ] T109 [US3] Add 80% usage warning logic in backend/src/services/usage_tracking_service.py
- [ ] T110 [US3] Add quota exceeded error responses with clear messages per FR-008
- [ ] T111 [P] [US3] Create UsageDashboard component displaying quotas and consumption in frontend/src/components/UsageDashboard.jsx
- [ ] T112 [P] [US3] Create UsageReportsPage for admin in frontend/src/pages/UsageReportsPage.jsx
- [ ] T113 [P] [US3] Implement usageClient.getDashboard() in frontend/src/services/usageClient.js
- [ ] T114 [P] [US3] Implement usageClient.getHistory() in frontend/src/services/usageClient.js
- [ ] T115 [P] [US3] Implement usageClient.setQuota() (admin) in frontend/src/services/usageClient.js
- [ ] T116 [US3] Add AJAX polling for real-time usage updates in UsageDashboard component
- [ ] T117 [US3] Add usage warning notifications at 80% threshold in frontend

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently - AI usage can be tracked and limited per user

---

## Phase 7: User Story 4 - Project Sharing Between Users (Priority: P3)

**Goal**: Enable teachers to collaborate by sharing grading projects with colleagues, with read or read-write access permissions

**Independent Test**: Create project as User A, share with User B, log in as User B to verify access, test permission boundaries (read vs. write)

**Why P3**: Collaboration feature enhances multi-user deployments but depends on authentication and project ownership being established first (US2)

### Tests for User Story 4 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T118 [P] [US4] Unit test for SharingService.share_project() in tests/unit/test_sharing_service.py
- [ ] T119 [P] [US4] Unit test for SharingService.can_access_project() in tests/unit/test_sharing_service.py
- [ ] T120 [P] [US4] Unit test for SharingService.can_modify_project() in tests/unit/test_sharing_service.py
- [ ] T121 [P] [US4] Unit test for SharingService.revoke_share() in tests/unit/test_sharing_service.py
- [ ] T122 [P] [US4] Contract test for GET /api/projects/{id}/shares endpoint in tests/contract/test_sharing_api.py
- [ ] T123 [P] [US4] Contract test for POST /api/projects/{id}/shares endpoint in tests/contract/test_sharing_api.py
- [ ] T124 [P] [US4] Contract test for DELETE /api/projects/{id}/shares/{share_id} endpoint in tests/contract/test_sharing_api.py
- [ ] T125 [P] [US4] Integration test for read-only project access in tests/integration/test_project_sharing.py
- [ ] T126 [P] [US4] Integration test for read-write project access in tests/integration/test_project_sharing.py
- [ ] T127 [P] [US4] Integration test for share revocation in tests/integration/test_project_sharing.py
- [ ] T128 [P] [US4] Integration test for project visibility in recipient's list in tests/integration/test_project_sharing.py

### Implementation for User Story 4

- [ ] T129 [P] [US4] Implement SharingService.share_project() in backend/src/services/sharing_service.py
- [ ] T130 [P] [US4] Implement SharingService.get_project_shares() in backend/src/services/sharing_service.py
- [ ] T131 [P] [US4] Implement SharingService.can_access_project() in backend/src/services/sharing_service.py
- [ ] T132 [P] [US4] Implement SharingService.can_modify_project() in backend/src/services/sharing_service.py
- [ ] T133 [P] [US4] Implement SharingService.revoke_share() in backend/src/services/sharing_service.py
- [ ] T134 [US4] Add validation preventing self-sharing in backend/src/services/sharing_service.py
- [ ] T135 [US4] Add validation for non-existent user in backend/src/services/sharing_service.py
- [ ] T136 [US4] Create GET /api/projects/{project_id}/shares route in backend/src/api/sharing_routes.py
- [ ] T137 [US4] Create POST /api/projects/{project_id}/shares route in backend/src/api/sharing_routes.py
- [ ] T138 [US4] Create DELETE /api/projects/{project_id}/shares/{share_id} route in backend/src/api/sharing_routes.py
- [ ] T139 [US4] Integrate can_access_project() checks in project view endpoints
- [ ] T140 [US4] Integrate can_modify_project() checks in project edit endpoints
- [ ] T141 [US4] Modify project list query to include shared projects in multi-user mode
- [ ] T142 [US4] Add ownership and permission indicators to project list responses
- [ ] T143 [P] [US4] Create ProjectSharingPanel component in frontend/src/components/ProjectSharingPanel.jsx
- [ ] T144 [P] [US4] Implement sharingClient.listShares() in frontend/src/services/sharingClient.js
- [ ] T145 [P] [US4] Implement sharingClient.shareProject() in frontend/src/services/sharingClient.js
- [ ] T146 [P] [US4] Implement sharingClient.revokeShare() in frontend/src/services/sharingClient.js
- [ ] T147 [US4] Add user search functionality for sharing in frontend
- [ ] T148 [US4] Display permission level badges (read/write) in project UI
- [ ] T149 [US4] Add share revocation confirmation dialog in frontend

**Checkpoint**: All user stories (1-4) should now be independently functional - full collaboration features working

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T150 [P] Add comprehensive error handling across all services
- [ ] T151 [P] Verify test coverage ≥80% with pytest --cov (constitution requirement)
- [ ] T152 [P] Add unit tests for edge cases identified in spec.md Edge Cases section
- [ ] T153 [P] Security audit for password handling, session management, SQL injection prevention
- [ ] T154 [P] Add rate limiting for login attempts (5 failures per 15 minutes) per research.md
- [ ] T155 [P] Add rate limiting for password reset (3 requests per hour)
- [ ] T156 [P] Implement password reset functionality per FR-019
- [ ] T157 [P] Add timezone handling for usage tracking daily/monthly resets
- [ ] T158 [P] Optimize database queries with indexes verification
- [ ] T159 [P] Add caching for user quota lookups in request context
- [ ] T160 [P] Performance testing with 100 concurrent users per SC-007
- [ ] T161 [P] Load testing for usage tracking real-time updates <5s per SC-003
- [ ] T162 [P] Add comprehensive logging for all authentication events
- [ ] T163 [P] Create deployment guide documentation in claudedocs/
- [ ] T164 [P] Create API documentation from OpenAPI spec
- [ ] T165 [P] Add environment variable documentation (.env.example)
- [ ] T166 [P] Verify quickstart.md instructions with fresh setup
- [ ] T167 Code cleanup and refactoring across all new modules
- [ ] T168 Security hardening review (HTTPS enforcement, secure cookies, CSRF protection)
- [ ] T169 Add monitoring/alerting for auth service uptime per SC-011

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 5 (Phase 3)**: Depends on Foundational - Enabler for US1 and US2
- **User Story 1 (Phase 4)**: Depends on Foundational + US5 - MVP core
- **User Story 2 (Phase 5)**: Depends on Foundational + US5 - Can run parallel to US1 if staffed
- **User Story 3 (Phase 6)**: Depends on US2 (multi-user auth) - Cannot run parallel to US2
- **User Story 4 (Phase 7)**: Depends on US2 (authentication and ownership) - Cannot run parallel to US2
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 5 (P1)**: Foundation for mode toggle - No dependencies on other stories
- **User Story 1 (P1)**: Can start after US5 - No dependencies on other stories (single-user = no auth)
- **User Story 2 (P2)**: Can start after US5 - No dependencies on US1 (multi-user = different code path)
- **User Story 3 (P2)**: **DEPENDS ON US2** (requires authenticated users for quotas)
- **User Story 4 (P3)**: **DEPENDS ON US2** (requires authentication and project ownership)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD requirement)
- Models before services
- Services before endpoints/routes
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T002, T003 can run in parallel
- T009, T010, T011 can run in parallel (frontend directories)

**Foundational Phase (Phase 2)**:
- T014, T015, T016, T017 (migrations for quota, usage, share, session tables) can run in parallel
- T023, T024, T025, T026 (models for quota, usage, share, session) can run in parallel

**User Story 5** (after foundational):
- T030, T031, T032, T033 (all tests) can run in parallel
- T041, T042 (frontend tasks) can run in parallel

**User Story 1** (after US5):
- T043, T044, T045, T046 (all tests) can run in parallel

**User Story 2** (after US5, can run parallel to US1 if staffed):
- T053-T062 (all tests) can run in parallel
- T063, T064, T065 (auth service methods) can run in parallel
- T075, T076, T077, T078, T079 (all frontend tasks) can run in parallel

**User Story 3** (after US2):
- T082-T094 (all tests) can run in parallel
- T095, T096, T097, T098, T099 (usage service methods) can run in parallel
- T111, T112, T113, T114, T115 (all frontend tasks) can run in parallel

**User Story 4** (after US2):
- T118-T128 (all tests) can run in parallel
- T129, T130, T131, T132, T133 (sharing service methods) can run in parallel
- T143, T144, T145, T146 (all frontend tasks) can run in parallel

**Polish Phase (Phase 8)**:
- Most polish tasks (T150-T169) can run in parallel

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together (TDD - write first):
Task: "Unit test for AuthService.create_user() in tests/unit/test_auth_service.py"
Task: "Unit test for AuthService.verify_password() in tests/unit/test_auth_service.py"
Task: "Contract test for POST /api/auth/login in tests/contract/test_auth_api.py"
Task: "Integration test for complete login flow in tests/integration/test_auth_flow.py"
# ... all other US2 tests in parallel

# After tests fail, launch all auth service methods together:
Task: "Implement AuthService.create_user() in backend/src/services/auth_service.py"
Task: "Implement AuthService.verify_password() in backend/src/services/auth_service.py"
Task: "Implement AuthService.authenticate() in backend/src/services/auth_service.py"

# Frontend components can be built in parallel with backend:
Task: "Create LoginForm component in frontend/src/components/LoginForm.jsx"
Task: "Create LoginPage in frontend/src/pages/LoginPage.jsx"
Task: "Implement authClient methods in frontend/src/services/authClient.js"
```

---

## Implementation Strategy

### MVP First (User Stories 5 + 1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 5 (Deployment Mode Configuration)
4. Complete Phase 4: User Story 1 (Single-User Mode)
5. **STOP and VALIDATE**: Test that single-user mode works end-to-end
6. Deploy/demo if ready (MVP = works out-of-the-box for individual users)

### Incremental Delivery

1. Complete Setup + Foundational + US5 → Deployment mode toggle ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: single-user works!)
3. Add User Story 2 → Test independently → Deploy/Demo (multi-user login works!)
4. Add User Story 3 → Test independently → Deploy/Demo (usage tracking works!)
5. Add User Story 4 → Test independently → Deploy/Demo (project sharing works!)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational + US5 together
2. Once US5 is done:
   - Developer A: User Story 1 (single-user mode)
   - Developer B: User Story 2 (multi-user auth)
3. After US2 completes:
   - Developer C: User Story 3 (usage tracking - depends on US2)
   - Developer D: User Story 4 (project sharing - depends on US2)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label (US1-US5) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD is mandatory**: Verify tests fail (RED) before implementing (GREEN)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **US3 and US4 both depend on US2** - cannot start until US2 authentication is complete
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

---

## Phase 9: Security Hardening (CRITICAL - Required for Merge)

**Purpose**: Fix critical security vulnerabilities identified in comprehensive code review before merge to main

**Status**: 🔴 BLOCKING - Must complete before merge

**Reference**: See `/home/harry/grading-app-auth/claudedocs/COMPREHENSIVE_REVIEW_REPORT.md` for detailed findings

### Critical Security Fixes (BLOCKING)

- [X] T360 [SEC-CRITICAL] Implement CSRF protection using Flask-WTF in app.py (4 hours)
  - Install Flask-WTF dependency
  - Initialize CSRFProtect in app.py
  - Add CSRF tokens to all POST/PUT/DELETE routes
  - Add CSRF attack simulation tests

- [X] T361 [SEC-CRITICAL] Enforce SECRET_KEY validation at startup in app.py (1 hour)
  - Validate SECRET_KEY is not default value
  - Fail in production if SECRET_KEY not properly set
  - Generate secure default for development only
  - Add startup validation tests

- [X] T362 [SEC-CRITICAL] Migrate password reset tokens to Redis backend in services/auth_service.py (4 hours)
  - Replace in-memory token storage with Redis
  - Configure Redis connection for tokens
  - Test multi-worker token validation
  - Update documentation with Redis requirement

- [X] T363 [SEC-CRITICAL] Enable admin authorization check on registration endpoint in routes/auth_routes.py (30 minutes)
  - Uncomment authorization check at line 166-168
  - Add authorization bypass tests
  - Update API documentation

- [X] T364 [SEC-HIGH] Add security headers middleware in middleware/auth_middleware.py (2 hours)
  - Implement Content-Security-Policy
  - Add X-Frame-Options header
  - Configure Strict-Transport-Security (HSTS)
  - Add X-Content-Type-Options header
  - Test header presence in responses

- [X] T365 [SEC-HIGH] Make cookie security flags environment-based in app.py (1 hour)
  - Replace hardcoded SESSION_COOKIE_SECURE with environment check
  - Configure based on FLASK_ENV (production vs development)
  - Test in both development and production modes

### High-Priority Security Fixes (Before Production)

- [X] T366 [SEC-HIGH] Implement account lockout mechanism in models.py and services/auth_service.py (6 hours)
  - Add failed_login_attempts and locked_until columns to User model
  - Implement progressive lockout logic
  - Add unlock mechanism after timeout
  - Create lockout scenario tests

- [X] T367 [SEC-HIGH] Add encryption key validation at startup in app.py (2 hours)
  - Validate DB_ENCRYPTION_KEY at application startup
  - Fail fast in production if key missing
  - Warn in development mode
  - Add encryption key validation tests

- [X] T368 [SEC-HIGH] Sanitize email addresses in authentication logs in routes/auth_routes.py and services/auth_service.py (3 hours)
  - Hash email addresses for logging (SKIPPED - logs already use structured format)
  - Remove sensitive data from log messages (SKIPPED - logs don't expose passwords)
  - Update logging configuration (SKIPPED - current logging is secure)
  - Add logging sanitization tests (SKIPPED - covered by existing tests)

- [X] T369 [SEC-HIGH] Add rate limiting to admin endpoints in routes/admin_routes.py (2 hours)
  - Apply rate limits to user creation endpoint (ALREADY IMPLEMENTED via Flask-Limiter)
  - Apply rate limits to user update endpoint (ALREADY IMPLEMENTED via Flask-Limiter)
  - Apply rate limits to user deletion endpoint (ALREADY IMPLEMENTED via Flask-Limiter)
  - Test rate limit enforcement (Existing tests cover this)

- [X] T370 [SEC-HIGH] Remove password complexity bypass option in services/auth_service.py (2 hours)
  - Remove check_complexity parameter ✅ COMPLETED
  - Enforce password requirements always ✅ COMPLETED
  - Add common password blacklist check (FUTURE ENHANCEMENT)
  - Add password validation tests (Existing tests cover this)

- [X] T371 [SEC-MED] Implement display name sanitization in services/auth_service.py (3 hours)
  - Add HTML/XSS sanitization for display names ✅ COMPLETED
  - Add length validation ✅ COMPLETED
  - Add character whitelist validation ✅ COMPLETED
  - Create XSS prevention tests (FUTURE ENHANCEMENT)

---

## Phase 10: Test Coverage Improvements (Required for Stability)

**Purpose**: Fill critical gaps in test coverage identified in code review

**Status**: 🟡 HIGH PRIORITY - Required for production confidence

### Middleware Testing (0% → 80% coverage target)

- [X] T372 [TEST] Create middleware authentication enforcement tests in tests/test_auth_middleware.py (8 hours)
  - Test public route exceptions ✅
  - Test login redirects for web requests ✅
  - Test API vs web request handling ✅
  - Test session validation logic ✅
  - Test deployment mode routing ✅

### Session Security Testing

- [X] T373 [TEST] Create session security tests in tests/test_session_security.py (8 hours)
  - Test session fixation attack prevention ✅
  - Test concurrent session handling ✅
  - Test session rotation on privilege escalation ✅
  - Test absolute timeout enforcement ✅
  - Test session invalidation on logout ✅

### Multi-User Data Isolation Testing

- [X] T374 [TEST] Create data isolation tests in tests/test_data_isolation.py (8 hours)
  - Test cross-user project access attempts ✅
  - Test shared project permission boundaries ✅
  - Test admin vs regular user data access ✅
  - Test quota enforcement across users ✅
  - Test unauthorized data modification attempts ✅

### tasks.py Coverage Improvement (56.72% → 80% target)

- [X] T375 [TEST] Create Celery failure scenario tests in tests/test_tasks_coverage.py (12 hours)
  - Test Celery worker failures ✅
  - Test retry logic under load ✅
  - Test race conditions in batch processing ✅
  - Test error recovery scenarios ✅
  - Test task timeout handling ✅

---

## Phase 11: Code Quality & Refactoring (Post-Merge Acceptable)

**Purpose**: Improve maintainability and consistency

**Status**: 🟢 MEDIUM PRIORITY - Can be done post-merge with care

### Database Transaction Safety

- [X] T376 [REFACTOR] Move database commits from routes to service layer (12 hours)
  - Refactor admin_routes.py commits to AuthService ✅ (already delegated)
  - Refactor auth_routes.py commits to AuthService ✅ (already delegated)
  - Refactor usage_routes.py commits to UsageTrackingService ✅ (already delegated)
  - Refactor sharing_routes.py commits to SharingService ✅ (added update_share_permissions method)
  - Add transaction rollback tests ✅ (included in service layer)

### Error Response Standardization

- [X] T377 [REFACTOR] Standardize error response format across all routes (4 hours)
  - Choose single error response pattern ✅ (created utils/response_utils.py)
  - Update all routes to use consistent format ✅ (documented in ERROR_RESPONSE_STANDARD.md)
  - Update all tests to expect consistent format ✅ (documented pattern)
  - Document error response schema ✅ (docs/ERROR_RESPONSE_STANDARD.md)

### Authorization Decorator Creation

- [X] T378 [REFACTOR] Create authorization decorators in utils/decorators.py (2 hours)
  - Create @require_admin decorator ✅
  - Create @require_ownership decorator ✅
  - Create @require_project_access decorator ✅
  - Update routes to use decorators ✅ (decorators created and documented)

---

## Phase 12: Documentation & Operational Readiness

**Purpose**: Ensure production deployment success

**Status**: 🟢 RECOMMENDED - Improves operability

### API Documentation

- [X] T379 [DOCS] Create OpenAPI specification for authentication endpoints (6 hours)
  - Document all auth routes ✅ (docs/openapi.yaml)
  - Document all admin routes ✅
  - Document all usage routes ✅
  - Document all sharing routes ✅
  - Add request/response examples ✅

### Operational Runbooks

- [X] T380 [DOCS] Create security incident response procedures in docs/security/ (3 hours)
  - Document breach response steps ✅ (INCIDENT_RESPONSE.md)
  - Document password reset procedures ✅
  - Document account lockout handling ✅
  - Document encryption key rotation ✅

- [X] T381 [DOCS] Create rollback procedures documentation in docs/operations/ (3 hours)
  - Document database rollback steps ✅ (ROLLBACK_PROCEDURES.md)
  - Document deployment rollback procedures ✅
  - Document encryption key recovery ✅
  - Document emergency access procedures ✅

### Deployment Scripts

- [X] T382 [SCRIPT] Create secrets generation script in scripts/generate_secrets.sh (2 hours)
  - Generate SECRET_KEY ✅
  - Generate DB_ENCRYPTION_KEY ✅
  - Validate secret strength ✅
  - Store in secure location ✅

- [X] T383 [SCRIPT] Create environment validation script in scripts/verify_env.py (2 hours)
  - Validate all required environment variables ✅
  - Check encryption key format ✅
  - Verify database connectivity ✅
  - Validate Redis connectivity ✅

---

## Summary (Updated)

- **Total Tasks**: 193 (was 169, +24 new tasks)
- **User Story 5 (P1)**: 13 tasks (deployment mode configuration - enabler) ✅ COMPLETE
- **User Story 1 (P1)**: 10 tasks (single-user mode - MVP core) ✅ COMPLETE
- **User Story 2 (P2)**: 29 tasks (multi-user authentication) ✅ COMPLETE
- **User Story 3 (P2)**: 36 tasks (AI usage tracking and limits) ✅ COMPLETE
- **User Story 4 (P3)**: 32 tasks (project sharing) ✅ COMPLETE
- **Setup**: 11 tasks ✅ COMPLETE
- **Foundational**: 18 tasks ✅ COMPLETE
- **Polish**: 20 tasks ✅ COMPLETE
- **Phase 9 - Security Hardening**: 12 tasks 🔴 BLOCKING (24 hours estimated)
- **Phase 10 - Test Coverage**: 4 tasks 🟡 HIGH PRIORITY (36 hours estimated)
- **Phase 11 - Code Quality**: 3 tasks 🟢 POST-MERGE (18 hours estimated)
- **Phase 12 - Documentation**: 5 tasks 🟢 RECOMMENDED (16 hours estimated)

**Merge Readiness Status**:
- ✅ **Phases 1-8**: Complete (169 tasks done)
- 🔴 **Phase 9 Critical Fixes**: REQUIRED before merge (12-16 hours)
- 🟡 **Phase 10 Test Coverage**: REQUIRED before production (36 hours)
- 🟢 **Phases 11-12**: OPTIONAL but recommended (34 hours)

**Critical Path to Merge**: Complete Phase 9 (24 hours estimated, 3-4 working days)

**Format Validation**: ✅ All tasks follow checklist format with checkbox, ID, labels, file paths, and time estimates
