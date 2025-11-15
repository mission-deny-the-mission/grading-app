# Tasks: API Provider Configuration Security & UX Improvements

**Input**: Design documents from `/specs/002-api-provider-security/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are MANDATORY per constitution (Test-First Development principle). All user stories MUST have tests written BEFORE implementation (TDD workflow: tests → fail → implement → pass).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Project uses **single structure**: Files at repository root
- **Models**: `models.py`
- **Routes**: `routes/main.py`, `routes/api.py`
- **Utils**: `utils/llm_providers.py`, `utils/encryption.py`
- **Templates**: `templates/config.html`
- **Static**: `static/js/config.js`
- **Tests**: `tests/test_*.py`
- **Migrations**: `migrations/encrypt_api_keys.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and environment configuration

- [x] T001 Add cryptography>=41.0.0 to requirements.txt for Fernet encryption
- [x] T002 [P] Add Flask-Migrate>=4.0.0 to requirements.txt for database migrations
- [ ] T003 [P] Install new dependencies with pip install -r requirements.txt
- [ ] T004 Generate encryption key and document in .env.example with python -c "from cryptography.fernet import Fernet; print(f'DB_ENCRYPTION_KEY={Fernet.generate_key().decode()}')"
- [ ] T005 Add DB_ENCRYPTION_KEY to .env file (do not commit to git)
- [ ] T006 [P] Initialize Flask-Migrate in app.py with migrate = Migrate(app, db)

**Checkpoint**: Dependencies installed, encryption key generated, environment configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create utils/encryption.py with get_encryption_key(), encrypt_value(), decrypt_value() functions
- [x] T008 [P] Add API_KEY_PATTERNS dictionary to utils/llm_providers.py with regex patterns for all 10 providers
- [x] T009 [P] Add validate_api_key_format(provider, key) function to utils/llm_providers.py
- [x] T010 [P] Create LLMProviderError exception class in utils/llm_providers.py with ERROR_TYPES enum and to_dict() method
- [x] T011 [P] Add test_connection() method to LLMProvider base class in utils/llm_providers.py

**Checkpoint**: Foundation ready - encryption utilities, validation patterns, error handling, and testing infrastructure complete. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Secure API Key Storage (Priority: P1) 🎯 MVP

**Goal**: Encrypt all API keys at rest in the database so that database compromise does not expose keys

**Independent Test**: Save an API key through the configuration interface, directly inspect the database to verify the key is encrypted (not plaintext), and then load the configuration to verify the key is correctly decrypted and functional.

### Tests for User Story 1 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T012 [P] [US1] Unit test for encrypt_value() and decrypt_value() in tests/test_encryption.py
- [ ] T013 [P] [US1] Unit test for Config model encryption properties in tests/test_models.py (test round-trip encryption)
- [ ] T014 [P] [US1] Integration test for /save_config endpoint with encryption in tests/test_config_routes.py
- [ ] T015 [P] [US1] Integration test for /load_config endpoint with decryption in tests/test_config_routes.py
- [ ] T016 [P] [US1] Test for safe failure when DB_ENCRYPTION_KEY is missing in tests/test_encryption.py

### Implementation for User Story 1

- [ ] T017 [US1] Modify Config model in models.py to add private encrypted fields (_openrouter_api_key, _claude_api_key, etc.) with VARCHAR(500)
- [ ] T018 [US1] Add @property getters for all API key fields in models.py using decrypt_value()
- [ ] T019 [US1] Add @property setters for all API key fields in models.py using encrypt_value()
- [ ] T020 [US1] Update routes/main.py save_config() to use new Config model properties (encryption automatic via setters)
- [ ] T021 [US1] Update routes/main.py load_config() to use new Config model properties (decryption automatic via getters)
- [ ] T022 [US1] Create migrations/encrypt_api_keys.py migration script to encrypt existing plaintext keys
- [ ] T023 [US1] Test migration script on development database and verify keys encrypted correctly
- [ ] T024 [US1] Add error handling for missing DB_ENCRYPTION_KEY in app.py startup (fail-safe)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. All API keys are encrypted at rest. Database inspection shows encrypted ciphertext, not plaintext.

---

## Phase 4: User Story 2 - API Key Validation (Priority: P1)

**Goal**: Provide immediate feedback when administrators enter incorrectly formatted API keys to prevent configuration errors

**Independent Test**: Enter various API keys (valid format, invalid format, empty) for different providers and verify that format validation occurs immediately with clear error messages before any API calls are made. Test "Test Key" button makes actual API calls and returns latency on success or specific error types on failure.

### Tests for User Story 2 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T025 [P] [US2] Unit tests for validate_api_key_format() in tests/test_validation.py (all providers, valid/invalid keys)
- [ ] T026 [P] [US2] Contract test for POST /test_api_key endpoint in tests/test_config_routes.py (verify contract spec)
- [ ] T027 [P] [US2] Integration test for client-side validation in tests/test_config_routes.py (simulate form validation)
- [ ] T028 [P] [US2] Integration test for server-side validation in tests/test_config_routes.py (verify save_config rejects invalid keys)
- [ ] T029 [P] [US2] Integration test for test_connection() method in tests/test_llm_providers.py (mock API calls)

### Implementation for User Story 2

- [ ] T030 [P] [US2] Update routes/main.py save_config() to validate API key formats before saving and return validation errors
- [ ] T031 [P] [US2] Create POST /test_api_key endpoint in routes/main.py that calls test_connection() and returns result
- [ ] T032 [P] [US2] Create static/js/config.js with client-side validation using JavaScript regex patterns matching API_KEY_PATTERNS
- [ ] ] T033 [P] [US2] Add validateKeyFormat(provider, key) function to static/js/config.js
- [ ] T034 [US2] Add testApiKey(provider, key) function to static/js/config.js that calls /test_api_key endpoint
- [ ] T035 [US2] Update templates/config.html to include static/js/config.js script
- [ ] T036 [US2] Add client-side validation event handlers to all API key input fields in templates/config.html
- [ ] T037 [US2] Add "Test Key" button onclick handlers in templates/config.html that call testApiKey()
- [ ] T038 [US2] Add success/error message display areas in templates/config.html for validation and test feedback

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. API keys are encrypted AND validated before storage. "Test Key" buttons make actual API calls and show latency or error types.

---

## Phase 5: User Story 3 - Provider Type Clarity (Priority: P2)

**Goal**: Visually distinguish cloud providers from local providers to reduce confusion during configuration

**Independent Test**: Open the configuration page and visually verify that cloud providers (OpenRouter, Claude, etc.) are clearly marked as "Cloud API" with pricing indicators, and local providers (LM Studio, Ollama) are marked as "Local Only" with appropriate styling.

### Tests for User Story 3 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T039 [P] [US3] Integration test for config page HTML contains cloud provider badges in tests/test_config_routes.py
- [ ] T040 [P] [US3] Integration test for config page HTML contains local provider badges in tests/test_config_routes.py
- [ ] T041 [P] [US3] Integration test for Z.AI explanation panel in tests/test_config_routes.py

### Implementation for User Story 3

- [ ] T042 [P] [US3] Add CSS classes for provider badges in templates/config.html (provider-section, cloud, local)
- [ ] T043 [P] [US3] Add "Cloud API" badge HTML to OpenRouter section in templates/config.html
- [ ] T044 [P] [US3] Add "Cloud API" badge HTML to Claude section in templates/config.html
- [ ] T045 [P] [US3] Add "Cloud API" badge HTML to Gemini section in templates/config.html
- [ ] T046 [P] [US3] Add "Cloud API" badge HTML to OpenAI section in templates/config.html
- [ ] T047 [P] [US3] Add "Cloud API" badge HTML to NanoGPT section in templates/config.html
- [ ] T048 [P] [US3] Add "Cloud API" badge HTML to Chutes section in templates/config.html
- [ ] T049 [P] [US3] Add "Cloud API" badge HTML to Z.AI sections in templates/config.html
- [ ] T050 [P] [US3] Add "Local Only" badge HTML to LM Studio section in templates/config.html
- [ ] T051 [P] [US3] Add "Local Only" badge HTML to Ollama section in templates/config.html
- [ ] T052 [US3] Add Z.AI pricing plan explanation panel HTML in templates/config.html with comparison of Normal API vs Coding Plan
- [ ] T053 [US3] Add pricing model indicators (pay-per-use, subscription) to cloud provider badges in templates/config.html

**Checkpoint**: All user stories 1, 2, and 3 should now be independently functional. Configuration page clearly shows provider types with visual badges.

---

## Phase 6: User Story 4 - Bulk Configuration Management (Priority: P2)

**Goal**: Enable administrators to export and import configuration settings to quickly replicate across environments

**Independent Test**: Configure multiple API keys, export the configuration to a JSON file, clear all configuration, import the JSON file, and verify all settings are restored correctly.

### Tests for User Story 4 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T054 [P] [US4] Contract test for GET /export_config endpoint in tests/test_config_routes.py (verify JSON structure)
- [ ] T055 [P] [US4] Contract test for POST /import_config endpoint in tests/test_config_routes.py (verify validation)
- [ ] T056 [P] [US4] Integration test for export functionality in tests/test_config_routes.py (verify all fields exported)
- [ ] T057 [P] [US4] Integration test for import functionality in tests/test_config_routes.py (verify form populated)
- [ ] T058 [P] [US4] Integration test for import validation errors in tests/test_config_routes.py (invalid JSON, version mismatch)

### Implementation for User Story 4

- [ ] T059 [P] [US4] Create GET /export_config endpoint in routes/main.py that returns JSON with all config fields
- [ ] T060 [P] [US4] Add export metadata (version, exported_at, warning) to export response in routes/main.py
- [ ] T061 [P] [US4] Create POST /import_config endpoint in routes/main.py that validates and applies JSON configuration
- [ ] T062 [US4] Add version validation (must be "1.0") to import_config in routes/main.py
- [ ] T063 [US4] Add API key format validation during import in routes/main.py using validate_api_key_format()
- [ ] T064 [US4] Add URL format validation during import in routes/main.py
- [ ] T065 [P] [US4] Add exportConfig() JavaScript function to static/js/config.js that calls fetch /export_config and downloads JSON
- [ ] T066 [P] [US4] Add importConfig(file) JavaScript function to static/js/config.js that reads file and POSTs to /import_config
- [ ] T067 [US4] Add security warning alert to exportConfig() in static/js/config.js
- [ ] T068 [US4] Add "Export Configuration" button to templates/config.html with onclick="exportConfig()"
- [ ] T069 [US4] Add "Import Configuration" file input and button to templates/config.html with onchange="importConfig(this.files[0])"
- [ ] T070 [US4] Add success/error message handling for import/export in static/js/config.js

**Checkpoint**: All user stories 1, 2, 3, and 4 should now be independently functional. Administrators can export/import full configuration as JSON files.

---

## Phase 7: User Story 5 - Standardized Error Handling (Priority: P3)

**Goal**: Provide consistent and actionable error messages across all providers for efficient troubleshooting

**Independent Test**: Trigger various error conditions (authentication failure, rate limit, timeout, network error) across different providers and verify that error messages follow a consistent format with error type, message, and suggested remediation.

### Tests for User Story 5 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T071 [P] [US5] Unit test for LLMProviderError.to_dict() in tests/test_llm_providers.py (verify all error types)
- [ ] T072 [P] [US5] Unit test for LLMProviderError._get_remediation() in tests/test_llm_providers.py (verify remediation text)
- [ ] T073 [P] [US5] Integration test for OpenRouterLLMProvider error handling in tests/test_llm_providers.py (mock auth failure)
- [ ] T074 [P] [US5] Integration test for ClaudeLLMProvider error handling in tests/test_llm_providers.py (mock rate limit)
- [ ] T075 [P] [US5] Integration test for consistent error format across providers in tests/test_llm_providers.py

### Implementation for User Story 5

- [ ] T076 [P] [US5] Update OpenRouterLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T077 [P] [US5] Update ClaudeLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T078 [P] [US5] Update GeminiLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T079 [P] [US5] Update OpenAILLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T080 [P] [US5] Update NanoGPTLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T081 [P] [US5] Update ChutesLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T082 [P] [US5] Update ZAILLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T083 [P] [US5] Update ZAICodingPlanProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T084 [P] [US5] Update LMStudioLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T085 [P] [US5] Update OllamaLLMProvider.grade_document() in utils/llm_providers.py to raise LLMProviderError with proper error types
- [ ] T086 [US5] Update POST /test_api_key endpoint in routes/main.py to catch LLMProviderError and return to_dict()
- [ ] T087 [US5] Update testApiKey() in static/js/config.js to display error_type and remediation in error messages

**Checkpoint**: All user stories 1-5 should now be independently functional. All providers return consistent error formats with specific error types and actionable remediation suggestions.

---

## Phase 8: User Story 6 - Accessibility Compliance (Priority: P3)

**Goal**: Ensure configuration page meets WCAG 2.1 Level AA standards for screen reader and keyboard-only users

**Independent Test**: Navigate the configuration page using only keyboard and screen reader software, verifying that all interactive elements can be accessed, understood, and operated without a mouse.

### Tests for User Story 6 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T088 [P] [US6] Accessibility test for password toggle buttons ARIA labels in tests/test_accessibility.py using pytest-axe
- [ ] T089 [P] [US6] Accessibility test for status indicators screen reader text in tests/test_accessibility.py
- [ ] T090 [P] [US6] Accessibility test for form validation error announcements in tests/test_accessibility.py
- [ ] T091 [P] [US6] Accessibility test for keyboard navigation tab order in tests/test_accessibility.py
- [ ] T092 [P] [US6] Manual accessibility test checklist in specs/002-api-provider-security/checklists/accessibility.md

### Implementation for User Story 6

- [ ] T093 [P] [US6] Add aria-label="Toggle [provider] API key visibility" to all password toggle buttons in templates/config.html
- [ ] T094 [P] [US6] Add aria-pressed="false" to all password toggle buttons in templates/config.html
- [ ] T095 [US6] Update togglePassword() in templates/config.html to update aria-pressed attribute on toggle
- [ ] T096 [P] [US6] Add role="status" and aria-label to all provider status indicators in templates/config.html
- [ ] T097 [P] [US6] Add visually-hidden status text spans for all provider status indicators in templates/config.html
- [ ] T098 [US6] Update status indicator JavaScript to update screen reader text on status change in templates/config.html
- [ ] T099 [P] [US6] Add aria-invalid="true" to form fields with validation errors in static/js/config.js
- [ ] T100 [P] [US6] Add aria-describedby linking errors to fields in static/js/config.js
- [ ] T101 [US6] Add role="alert" to validation error messages in static/js/config.js for screen reader announcements
- [ ] T102 [US6] Verify logical tab order (top to bottom, left to right) for all form fields in templates/config.html
- [ ] T103 [US6] Add visible focus indicators to all interactive elements with CSS in templates/config.html

**Checkpoint**: All user stories 1-6 should now be independently functional and fully accessible. Configuration page meets WCAG 2.1 Level AA compliance.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories and production readiness

- [ ] T104 [P] Add encryption key generation instructions to README.md
- [ ] T105 [P] Add migration instructions to README.md for production deployment
- [ ] T106 [P] Update .env.example with DB_ENCRYPTION_KEY and comments
- [ ] T107 [P] Create deployment checklist in specs/002-api-provider-security/checklists/deployment.md
- [ ] T108 [P] Add API key sanitization to logging in utils/llm_providers.py (never log keys)
- [ ] T109 [P] Verify test coverage ≥80% with pytest --cov (constitution requirement)
- [ ] T110 [P] Run flake8 and black for code quality (constitution requirement)
- [ ] T111 [P] Security review: verify no API keys in logs, errors, or debug output
- [ ] T112 [P] Performance test: verify encryption overhead <5% of request time
- [ ] T113 Rollback procedure documentation in specs/002-api-provider-security/rollback.md
- [ ] T114 Run full quickstart.md validation from fresh clone
- [ ] T115 Production migration dry-run on copy of production database

**Checkpoint**: Feature complete, tested, documented, and ready for production deployment.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-8)**: All depend on Foundational phase completion
  - US1 (P1): Encryption - Can start after Foundational
  - US2 (P1): Validation - Can start after Foundational (works with US1 encryption)
  - US3 (P2): UI Badges - Can start after Foundational (independent of US1/US2)
  - US4 (P2): Import/Export - Can start after Foundational (works with US1 encryption)
  - US5 (P3): Error Handling - Can start after Foundational (enhances US2 validation)
  - US6 (P3): Accessibility - Can start after Foundational (enhances US3 UI)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Encryption)**: BLOCKS US4 (import/export needs encryption)
- **User Story 2 (P1 - Validation)**: Independent - can run in parallel with US1
- **User Story 3 (P2 - UI Badges)**: Independent - can run in parallel with US1/US2
- **User Story 4 (P2 - Import/Export)**: DEPENDS on US1 (needs encryption), can integrate with US2 validation
- **User Story 5 (P3 - Error Handling)**: Independent - enhances US2 but not blocking
- **User Story 6 (P3 - Accessibility)**: Independent - enhances US3 but not blocking

### Critical Path

**MVP (User Story 1 + 2)**: Setup → Foundational → US1 (Encryption) → US2 (Validation) → DONE
- This gives you secure, validated API key storage (critical security fix)

**Within Each User Story**

- Tests MUST be written and FAIL before implementation (TDD cycle)
- Unit tests before integration tests
- Models/utilities before endpoints
- Backend before frontend
- Core implementation before integration with other stories
- Story complete and tested before moving to next priority

### Parallel Opportunities

**Setup Phase**: T001, T002, T003, T004, T005, T006 can all run in parallel

**Foundational Phase**: T007, T008, T009, T010, T011 can all run in parallel

**User Story Test Tasks**: All test tasks marked [P] within a story can run in parallel

**User Story Implementation Tasks**: Tasks marked [P] can run in parallel (different files, no dependencies)

**Cross-Story Parallelization**: After Foundational phase:
- Team A: US1 (Encryption) - CRITICAL PATH
- Team B: US2 (Validation) - parallel with US1
- Team C: US3 (UI Badges) - parallel with US1/US2
- Then: US4 depends on US1, US5/US6 can run in parallel with US4

---

## Parallel Example: User Story 1 (Encryption)

```bash
# Launch all tests for User Story 1 together (TDD - write first, verify they fail):
Task T012: "Unit test for encrypt_value() and decrypt_value()"
Task T013: "Unit test for Config model encryption properties"
Task T014: "Integration test for /save_config with encryption"
Task T015: "Integration test for /load_config with decryption"
Task T016: "Test safe failure when DB_ENCRYPTION_KEY missing"

# After tests fail, launch parallel implementation tasks:
Task T017: "Modify Config model - private encrypted fields"
Task T018: "Add @property getters using decrypt_value()"
Task T019: "Add @property setters using encrypt_value()"

# Sequential tasks (depend on model changes):
Task T020: "Update save_config() route"
Task T021: "Update load_config() route"
Task T022: "Create migration script"
Task T023: "Test migration"
Task T024: "Add startup error handling"
```

---

## Parallel Example: User Story 3 (UI Badges)

```bash
# Launch all tests together:
Task T039: "Test cloud provider badges in HTML"
Task T040: "Test local provider badges in HTML"
Task T041: "Test Z.AI explanation panel"

# After tests fail, launch all badge additions in parallel:
Task T042: "Add CSS classes"
Task T043: "Add OpenRouter badge"
Task T044: "Add Claude badge"
Task T045: "Add Gemini badge"
Task T046: "Add OpenAI badge"
Task T047: "Add NanoGPT badge"
Task T048: "Add Chutes badge"
Task T049: "Add Z.AI badges"
Task T050: "Add LM Studio badge"
Task T051: "Add Ollama badge"
Task T052: "Add Z.AI explanation panel"
Task T053: "Add pricing indicators"

# All these tasks modify different sections of templates/config.html
# and can be completed in parallel without conflicts
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

**Recommendation**: Deliver encryption + validation first as critical security fix

1. Complete Phase 1: Setup (6 tasks, ~30 mins)
2. Complete Phase 2: Foundational (5 tasks, ~1 hour)
3. Complete Phase 3: User Story 1 - Encryption (13 tasks, ~4-6 hours)
4. Complete Phase 4: User Story 2 - Validation (14 tasks, ~4-6 hours)
5. **STOP and VALIDATE**: Test encryption + validation independently
6. Deploy to production (critical security fix live)
7. **Total MVP Time**: ~10-14 hours

### Incremental Delivery

1. **Foundation** (Setup + Foundational) → ~2 hours → Foundation ready
2. **MVP** (US1 + US2) → ~10 hours → Critical security + validation live
3. **UX Enhancement** (US3 + US4) → ~8 hours → Better usability + bulk operations
4. **Quality** (US5 + US6) → ~10 hours → Error handling + accessibility
5. **Polish** (Phase 9) → ~4 hours → Production ready
6. **Total Feature Time**: ~34 hours (complete feature)

Each increment is independently testable and deployable.

### Parallel Team Strategy

With 3 developers:

1. **Phase 1+2** (All together): ~2 hours → Foundation ready
2. **Phase 3-5** (Parallel work):
   - Developer A: US1 Encryption (4-6 hours)
   - Developer B: US2 Validation (4-6 hours)
   - Developer C: US3 UI Badges (3-4 hours)
3. **Phase 6** (After US1 complete):
   - Developer C: US4 Import/Export (4-5 hours, needs US1 encryption)
4. **Phase 7-8** (Parallel work):
   - Developer A: US5 Error Handling (4-5 hours)
   - Developer B: US6 Accessibility (4-5 hours)
5. **Phase 9** (All together): ~4 hours → Polish and deploy

**Total Parallel Time**: ~16-20 hours with 3 developers (vs 34 hours solo)

---

## Task Summary

**Total Tasks**: 115
**Test Tasks**: 31 (27% - ensures >80% coverage per constitution)
**Implementation Tasks**: 84 (73%)

**Tasks per User Story**:
- US1 (Encryption): 13 tasks (5 tests + 8 implementation)
- US2 (Validation): 14 tasks (5 tests + 9 implementation)
- US3 (UI Badges): 15 tasks (3 tests + 12 implementation)
- US4 (Import/Export): 17 tasks (5 tests + 12 implementation)
- US5 (Error Handling): 17 tasks (5 tests + 12 implementation)
- US6 (Accessibility): 15 tasks (5 tests + 10 implementation)
- Setup: 6 tasks
- Foundational: 5 tasks
- Polish: 13 tasks

**Parallel Opportunities**: 67 tasks marked [P] can run in parallel (58% of tasks)

**MVP Scope**: User Story 1 + 2 (27 tasks, ~10-14 hours)

**Format Validation**: ✅ All tasks follow checklist format with ID, [P] marker (where applicable), [Story] label (for user stories), and file paths

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD CRITICAL**: Verify tests FAIL before implementing (constitution requirement)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Run tests after each implementation task to verify it passes
- User Story 1+2 recommended as MVP (critical security fix)
- All provider implementations can be updated in parallel (US5 tasks T076-T085)
- All badge additions can be done in parallel (US3 tasks T043-T051)
