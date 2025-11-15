# Implementation Plan: Optional Multi-User Authentication with AI Usage Controls

**Branch**: `004-optional-auth-system` | **Date**: 2025-11-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-optional-auth-system/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements a flexible authentication system supporting two deployment modes: single-user (no authentication) and multi-user (with authentication, AI usage limits, and project sharing). The system enables individual teachers to use the app locally without login requirements, while educational institutions can deploy a multi-tenant version with per-user AI cost controls and collaborative features.

## Technical Context

**Language/Version**: Python 3.13.7 (existing project)
**Primary Dependencies**: NEEDS CLARIFICATION (auth library: flask-login vs authlib vs custom JWT)
**Storage**: NEEDS CLARIFICATION (existing database solution - SQLite/PostgreSQL per constitution)
**Testing**: pytest (existing project standard)
**Target Platform**: Web application (backend + frontend)
**Project Type**: Web (backend API + frontend UI)
**Performance Goals**: 100 concurrent users without degradation, <1s auth response time
**Constraints**: <5s AI usage stat updates, zero unauthorized access, 99.9% auth uptime
**Scale/Scope**: Multi-user institutional deployments (10-1000 users), per-user AI tracking

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Quality Over Speed**:
- [x] Feature prioritizes accuracy and reliability over rapid delivery
- [x] Robust validation and error handling planned for all critical paths
  - *Justification*: Authentication failure handling, session validation, usage limit enforcement, and access control all require comprehensive error handling

**Test-First Development (NON-NEGOTIABLE)**:
- [x] TDD workflow planned: tests → fail → implement → pass
- [x] Test coverage target ≥80% for new features
- [x] Unit, integration, and contract tests identified
  - *Test plan*: Unit tests for auth logic, integration tests for deployment modes, contract tests for usage tracking

**AI Provider Agnostic**:
- [x] No tight coupling to specific AI provider implementation
- [x] Common abstraction layer used for AI interactions
  - *Compliance*: Feature tracks usage per provider through existing abstraction layer, doesn't create new provider-specific code

**Async-First Job Processing**:
- [x] All grading operations execute through Celery task queues
- [x] No synchronous grading in request handlers
  - *Compliance*: This feature doesn't add grading operations, only auth/usage tracking which are request-level concerns

**Data Integrity & Audit Trail**:
- [x] Complete audit trails planned (submissions, criteria, models, timestamps, retries)
- [x] All state transitions logged for reproducibility
  - *Implementation*: Login/logout events logged (FR-018), usage records timestamped (FR-007), sharing changes audited

**Security Requirements**:
- [x] File upload validation planned (type, size, content)
  - *N/A for this feature*: No file uploads in auth system
- [x] API keys stored in environment variables only
  - *Compliance*: No new API keys introduced (uses existing AI provider keys)
- [x] Parameterized database queries (no string concatenation)
  - *Implementation*: All user/session/quota queries will use ORM or parameterized queries

**Database Consistency**:
- [x] Migration scripts planned for all schema changes
- [x] Reversible migrations for rollback capability
  - *Implementation*: Migrations for User, DeploymentConfig, AIProviderQuota, UsageRecord, ProjectShare, AuthSession tables

## Project Structure

### Documentation (this feature)

```text
specs/004-optional-auth-system/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure (backend + frontend)
backend/
├── src/
│   ├── models/
│   │   ├── user.py                    # User entity
│   │   ├── deployment_config.py       # Deployment mode configuration
│   │   ├── ai_quota.py                # AI provider quota
│   │   ├── usage_record.py            # Usage tracking
│   │   ├── project_share.py           # Project sharing permissions
│   │   └── auth_session.py            # Authentication sessions
│   ├── services/
│   │   ├── auth_service.py            # Authentication logic
│   │   ├── deployment_service.py      # Deployment mode management
│   │   ├── usage_tracking_service.py  # AI usage tracking
│   │   └── sharing_service.py         # Project sharing logic
│   ├── api/
│   │   ├── auth_routes.py             # Login/logout/register endpoints
│   │   ├── usage_routes.py            # Usage dashboard/reports endpoints
│   │   └── sharing_routes.py          # Project sharing endpoints
│   └── middleware/
│       ├── auth_middleware.py         # Authentication enforcement
│       └── usage_enforcement.py       # Usage limit enforcement
└── tests/
    ├── unit/
    │   ├── test_auth_service.py
    │   ├── test_deployment_service.py
    │   ├── test_usage_tracking.py
    │   └── test_sharing_service.py
    ├── integration/
    │   ├── test_auth_flow.py
    │   ├── test_deployment_modes.py
    │   ├── test_usage_enforcement.py
    │   └── test_project_sharing.py
    └── contract/
        ├── test_auth_api.py
        ├── test_usage_api.py
        └── test_sharing_api.py

frontend/
├── src/
│   ├── components/
│   │   ├── LoginForm.jsx              # Login UI component
│   │   ├── UsageDashboard.jsx         # AI usage display
│   │   └── ProjectSharingPanel.jsx    # Sharing UI
│   ├── pages/
│   │   ├── LoginPage.jsx              # Login page
│   │   ├── SetupPage.jsx              # Deployment mode setup
│   │   └── UsageReportsPage.jsx       # Admin usage reports
│   └── services/
│       ├── authClient.js              # Auth API client
│       ├── usageClient.js             # Usage API client
│       └── sharingClient.js           # Sharing API client
└── tests/
    └── e2e/
        ├── login.spec.js
        ├── deployment_setup.spec.js
        └── usage_tracking.spec.js
```

**Structure Decision**: Web application with backend (Python) and frontend (JavaScript/React - NEEDS CLARIFICATION on framework choice). Backend follows existing project structure with models, services, and API routes. Frontend follows component-based architecture with pages and API clients.

## Complexity Tracking

No constitution violations requiring justification.
