# Implementation Plan: API Provider Configuration Security & UX Improvements

**Branch**: `002-api-provider-security` | **Date**: 2025-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-api-provider-security/spec.md`

## Summary

Enhance API provider configuration with encryption at rest, comprehensive validation, improved UX, and accessibility compliance. Addresses critical security vulnerability (plaintext API keys in database) while improving administrator experience through better error messages, visual provider type distinction, bulk configuration management, and screen reader support.

**Primary Requirement**: Encrypt all API keys stored in database using Fernet symmetric encryption, add format validation with actual API testing, improve configuration UI with visual badges and import/export capabilities, and ensure WCAG 2.1 Level AA accessibility compliance.

**Technical Approach**:
1. Add `cryptography` library for Fernet encryption
2. Modify Config model with property-based encryption/decryption
3. Implement one-time migration script for existing keys
4. Add client/server validation with provider-specific regex patterns
5. Enhance LLMProvider base class with `test_connection()` method
6. Standardize error handling with custom exception classes
7. Update config.html with badges, ARIA labels, and import/export UI
8. Add JavaScript for client-side validation and bulk operations

## Technical Context

**Language/Version**: Python 3.13.7 (recommend constraint: `>=3.9,<4.0` in setup.py)
**Primary Dependencies**:
- Flask 2.3.3 (web framework)
- Flask-SQLAlchemy 3.0.5 (ORM)
- Celery 5.3.4 + Redis 5.0.1 (async tasks)
- cryptography >=41.0.0 (**NEW** - for Fernet encryption)
- Flask-Migrate >=4.0.0 (**NEW** - for database migrations)

**Storage**: SQLite (development), PostgreSQL (production via psycopg2-binary 2.9.10)
**Testing**: pytest 7.4.4 + pytest-cov 4.1.0 + pytest-flask 1.3.0
**Target Platform**: Linux server (web application)
**Project Type**: Web (Flask backend + Jinja2 templates + Bootstrap frontend)

**Performance Goals**:
- Encryption/decryption overhead <1ms per operation
- Config page load <500ms
- Import/export operations <2 minutes for full configuration

**Constraints**:
- Zero downtime migration (encrypt keys while system running)
- Backward compatibility with environment variable fallback
- No breaking changes to existing provider integrations

**Scale/Scope**:
- 10 AI providers (OpenRouter, Claude, Gemini, OpenAI, NanoGPT, Chutes, Z.AI x2, LM Studio, Ollama)
- Single-user configuration (no multi-tenancy)
- ~1,000 configuration operations per month (estimate)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Quality Over Speed**:
- [x] Feature prioritizes security (encryption) and reliability over rapid delivery
- [x] Robust validation planned: format validation + actual API testing
- [x] Migration script with rollback capability and comprehensive error handling

**Test-First Development (NON-NEGOTIABLE)**:
- [x] TDD workflow planned: tests → fail → implement → pass
- [x] Test coverage target ≥80% for new encryption, validation, and UI features
- [x] Unit tests (encryption, validation), integration tests (config endpoints), E2E tests (accessibility)

**AI Provider Agnostic**:
- [x] No tight coupling to specific provider - changes affect Config model universally
- [x] Common abstraction layer (LLMProvider base class) used for validation and testing
- [x] Error standardization works across all providers

**Async-First Job Processing**:
- [x] Not applicable - configuration changes are synchronous admin operations
- [x] No impact on existing Celery task queue for grading operations

**Data Integrity & Audit Trail**:
- [x] Migration script preserves all existing API keys (lossless encryption)
- [x] Audit trail: export includes timestamp and version metadata
- [x] Error logging planned for encryption failures and validation errors

**Security Requirements**:
- [x] Not applicable - no file uploads in this feature
- [x] API keys encrypted at rest AND stored in environment variables (double protection)
- [x] All database queries use SQLAlchemy ORM (parameterized by default)
- [x] **ADDITIONAL**: Encryption key stored separately in environment variable

**Database Consistency**:
- [x] Migration script planned for encrypting existing plaintext keys
- [x] Adding Flask-Migrate for reversible migrations
- [x] Dry-run validation before production migration

**RESULT**: ✅ **CONSTITUTION CHECK PASSED** - All requirements met, no violations to justify

## Project Structure

### Documentation (this feature)

```text
specs/002-api-provider-security/
├── spec.md              # Feature specification (/speckit.specify output)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Technical decisions and alternatives
├── data-model.md        # Database schema changes
├── quickstart.md        # Developer setup guide
├── contracts/           # API contract specifications
│   ├── test-api-key.yml
│   ├── export-config.yml
│   └── import-config.yml
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # NOT YET CREATED - run /speckit.tasks next
```

### Source Code (repository root)

```text
/home/harry/grading-app-main/
├── app.py                      # Flask application (no changes)
├── models.py                   # MODIFY: Add encryption to Config model
├── routes/
│   ├── main.py                 # MODIFY: Update config endpoints
│   ├── api.py                  # No changes
│   ├── batches.py              # No changes
│   ├── templates.py            # No changes
│   └── upload.py               # No changes
├── utils/
│   ├── llm_providers.py       # MODIFY: Add LLMProviderError, test_connection()
│   ├── encryption.py          # NEW: Encryption utilities and key management
│   ├── file_utils.py          # No changes
│   └── text_extraction.py     # No changes
├── templates/
│   ├── config.html            # MODIFY: Add badges, ARIA labels, import/export UI
│   └── [other templates]      # No changes
├── static/
│   └── js/
│       └── config.js          # NEW: Import/export JavaScript functionality
├── migrations/
│   └── encrypt_api_keys.py    # NEW: One-time migration script
├── tests/
│   ├── test_encryption.py     # NEW: Encryption unit tests
│   ├── test_validation.py     # NEW: API key validation unit tests
│   ├── test_config_routes.py  # MODIFY: Add import/export endpoint tests
│   ├── test_models.py         # MODIFY: Add Config encryption tests
│   ├── test_accessibility.py  # NEW: WCAG compliance tests
│   └── [existing tests]       # No changes
└── requirements.txt            # MODIFY: Add cryptography, Flask-Migrate
```

**Structure Decision**: Single project structure (Flask web application). All changes are backend (models, routes, utils) and frontend (templates, static JS). No new services or separate projects needed. Testing follows existing pytest structure with unit, integration, and new accessibility test categories.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - Constitution Check passed without exceptions. Feature aligns with all core principles:
- Security-first approach (encryption as P1 priority)
- Test-driven development workflow
- Provider-agnostic design
- Data integrity maintained through lossless migration
- Database consistency via migration scripts

No complexity justification required.
