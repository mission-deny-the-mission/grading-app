<!--
Sync Impact Report:
Version: 1.0.0 (Initial Constitution)
Ratification: 2025-11-14
Last Amendment: 2025-11-14

Modified Principles: N/A (Initial version)
Added Sections: All (Initial constitution establishment)
Removed Sections: None

Templates Requiring Updates:
✅ plan-template.md - Reviewed, compatible with constitution principles
✅ spec-template.md - Reviewed, aligned with quality requirements
✅ tasks-template.md - Reviewed, supports test-driven workflow
✅ README.md - Referenced, project context confirmed

Follow-up TODOs: None
-->

# Document Grading Web App Constitution

## Core Principles

### I. Quality Over Speed

The grading application must prioritize accuracy and reliability over rapid feature delivery. AI grading results directly impact users, requiring robust validation and error handling. All features must be thoroughly tested before deployment to ensure grading consistency and fairness.

**Rationale**: Incorrect grading results undermine trust in the system. Quality gates prevent deployment of unreliable grading logic that could harm users.

### II. Test-First Development (NON-NEGOTIABLE)

All new features and bug fixes MUST follow the Test-Driven Development cycle:
1. Write tests that capture requirements
2. Verify tests fail (red)
3. Implement minimal code to pass tests (green)
4. Refactor while keeping tests passing

**Rationale**: TDD ensures code correctness, prevents regressions, and creates living documentation of system behavior. Given the critical nature of grading accuracy, test coverage is mandatory, not optional.

### III. AI Provider Agnostic

The system MUST support multiple AI providers (OpenRouter, Claude API, LM Studio) through a common abstraction layer. No feature should be tightly coupled to a specific AI provider's implementation details.

**Rationale**: Provider lock-in creates operational risk and limits flexibility. Users should be able to switch providers based on cost, performance, or availability without system changes.

### IV. Async-First Job Processing

All document grading operations MUST execute asynchronously through Celery task queues. Synchronous grading operations in request handlers are prohibited to prevent request timeouts and enable scalability.

**Rationale**: Document grading can take seconds to minutes depending on document size and AI provider response times. Async processing ensures responsive UI and enables parallel job execution.

### V. Data Integrity & Audit Trail

All grading operations MUST maintain complete audit trails including:
- Original submission data
- Grading criteria used
- AI provider and model version
- Timestamps for all state transitions
- Retry attempts and failure reasons

**Rationale**: Grading transparency and reproducibility are essential for fairness and debugging. Complete audit trails enable issue investigation and results validation.

## System Architecture Requirements

### Database Consistency

- Database migrations MUST be version-controlled and reversible
- All schema changes require migration scripts (no manual DB modifications)
- SQLite for development, PostgreSQL for production
- Database connection pooling and retry logic required for production

### Error Handling Standards

- All external API calls (AI providers) MUST have retry logic with exponential backoff
- Failed jobs MUST be logged with full context for debugging
- User-facing errors MUST be actionable (not raw stack traces)
- System health checks MUST monitor job queue depth and processing rates

### Security Requirements

- All file uploads MUST be validated (type, size, content)
- API keys MUST be stored in environment variables, never committed to code
- User sessions MUST have configurable timeouts
- All database queries MUST use parameterized queries (no string concatenation)

## Development Workflow

### Code Review Gates

All pull requests MUST pass:
1. Automated test suite (unit, integration, contract tests)
2. Linting and formatting checks (flake8, black, isort)
3. Code review from maintainer focusing on constitution compliance
4. Manual testing verification for UI changes

### Testing Discipline

- **Unit Tests**: Test business logic in isolation (services, utilities)
- **Integration Tests**: Test component interactions (routes + database)
- **Contract Tests**: Verify AI provider integrations don't break
- Minimum 80% code coverage for new features
- All critical paths (grading, submission, export) MUST have integration tests

### Deployment Standards

- Production deployments require migration dry-run validation
- Database backups MUST be verified before schema migrations
- Rollback plan required for all deployments
- Feature flags preferred for risky changes

## Governance

### Amendment Process

Constitution changes require:
1. Proposal with rationale documenting why change is needed
2. Impact assessment on existing codebase and workflows
3. Template synchronization plan (spec, plan, tasks templates)
4. Approval from project maintainer
5. Migration period for backward-incompatible changes

### Compliance Verification

- All code reviews MUST verify constitution compliance
- Quarterly constitution review to identify outdated or unnecessary rules
- Violations require justification (documented in Complexity Tracking section of plan.md)
- Repeated violations trigger constitution amendment discussion

### Version Control

This constitution uses semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Principle removal, backward-incompatible governance changes
- **MINOR**: New principle addition, expanded requirements
- **PATCH**: Clarifications, wording improvements, non-semantic fixes

**Version**: 1.0.0 | **Ratified**: 2025-11-14 | **Last Amended**: 2025-11-14
