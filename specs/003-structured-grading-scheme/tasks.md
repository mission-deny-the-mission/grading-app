# Tasks: Structured Grading Scheme with Multi-Point Evaluation

**Input**: Design documents from `/specs/003-structured-grading-scheme/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per constitution (Test-First Development principle). All user stories MUST have tests written BEFORE implementation (TDD workflow: tests → fail → implement → pass).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: Root level (Flask application structure)
- Paths: `models.py`, `routes/`, `utils/`, `templates/`, `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Verify current branch is 003-structured-grading-scheme
- [ ] T002 [P] Create routes/schemes.py blueprint file (empty placeholder)
- [ ] T003 [P] Create routes/grading.py blueprint file (empty placeholder)
- [ ] T004 [P] Create routes/export.py blueprint file (empty placeholder)
- [ ] T005 [P] Create utils/scheme_calculator.py file (empty placeholder)
- [ ] T006 [P] Create utils/scheme_validator.py file (empty placeholder)
- [ ] T007 [P] Create utils/export_formatters.py file (empty placeholder)
- [ ] T008 [P] Create templates/schemes/ directory structure
- [ ] T009 [P] Create tests/unit/ subdirectories if not exist
- [ ] T010 [P] Create tests/integration/ subdirectories if not exist
- [ ] T011 [P] Create tests/contract/ directory if not exist

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T012 Create database migration: Create grading_schemes table with all fields and indexes
- [ ] T013 Create database migration: Create scheme_questions table with constraints
- [ ] T014 Create database migration: Create scheme_criteria table with constraints
- [ ] T015 Create database migration: Create graded_submissions table with indexes
- [ ] T016 Create database migration: Create criterion_evaluations table with unique constraint
- [ ] T017 [P] Implement calculate_scheme_total() in utils/scheme_calculator.py with Decimal precision
- [ ] T018 [P] Implement calculate_question_total() in utils/scheme_calculator.py with Decimal precision
- [ ] T019 [P] Implement validate_point_range() in utils/scheme_validator.py (0 to max_points check)
- [ ] T020 [P] Implement validate_hierarchy() in utils/scheme_validator.py (referential integrity)
- [ ] T021 Run database migrations: flask db upgrade
- [ ] T022 Verify migrations reversible: flask db downgrade and re-upgrade

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create Multi-Point Grading Scheme (Priority: P1) 🎯 MVP

**Goal**: Enable instructors to create reusable grading schemes with hierarchical structure (scheme → questions → criteria) with point allocations

**Independent Test**: Create a grading scheme with 5 questions where each question has 3 criteria, verify the scheme is saved with all hierarchical relationships intact, and total points calculate correctly

### Tests for User Story 1 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T023 [P] [US1] Write test_grading_scheme_creation in tests/unit/test_scheme_models.py (verify model creation, default values)
- [ ] T024 [P] [US1] Write test_scheme_to_dict in tests/unit/test_scheme_models.py (verify serialization)
- [ ] T025 [P] [US1] Write test_scheme_question_creation in tests/unit/test_scheme_models.py (verify question model, relationships)
- [ ] T026 [P] [US1] Write test_question_ordering in tests/unit/test_scheme_models.py (verify display_order unique constraint)
- [ ] T027 [P] [US1] Write test_scheme_criterion_creation in tests/unit/test_scheme_models.py (verify criterion model)
- [ ] T028 [P] [US1] Write test_criterion_point_validation in tests/unit/test_scheme_models.py (verify max_points constraints)
- [ ] T029 [P] [US1] Write test_calculate_scheme_total in tests/unit/test_scheme_calculator.py (verify point totals with Decimal precision)
- [ ] T030 [P] [US1] Write test_calculate_question_total in tests/unit/test_scheme_calculator.py (verify question totals)
- [ ] T031 [P] [US1] Write test_validate_point_range in tests/unit/test_scheme_validator.py (verify validation logic)
- [ ] T032 [P] [US1] Write test_create_scheme in tests/integration/test_scheme_routes.py (POST /api/schemes endpoint)
- [ ] T033 [P] [US1] Write test_get_scheme in tests/integration/test_scheme_routes.py (GET /api/schemes/{id} endpoint)
- [ ] T034 [P] [US1] Write test_list_schemes in tests/integration/test_scheme_routes.py (GET /api/schemes endpoint)
- [ ] T035 [P] [US1] Write test_update_scheme in tests/integration/test_scheme_routes.py (PUT /api/schemes/{id} with version increment)
- [ ] T036 [P] [US1] Write test_delete_scheme in tests/integration/test_scheme_routes.py (DELETE /api/schemes/{id} soft delete)
- [ ] T037 [P] [US1] Run all US1 tests and verify they FAIL (pytest tests/ -k "US1 or scheme" --tb=short)

### Implementation for User Story 1

- [ ] T038 [P] [US1] Implement GradingScheme model in models.py (all fields, relationships, indexes per data-model.md)
- [ ] T039 [P] [US1] Implement SchemeQuestion model in models.py (with unique display_order constraint)
- [ ] T040 [P] [US1] Implement SchemeCriterion model in models.py (with CHECK constraints on max_points)
- [ ] T041 [US1] Add to_dict() method to GradingScheme model (serialize to JSON)
- [ ] T042 [US1] Add to_dict() method to SchemeQuestion model (include criteria)
- [ ] T043 [US1] Add to_dict() method to SchemeCriterion model
- [ ] T044 [US1] Implement auto-calculation listeners for GradingScheme.total_possible_points (SQLAlchemy event listeners)
- [ ] T045 [US1] Implement auto-calculation listeners for SchemeQuestion.total_possible_points
- [ ] T046 [US1] Create schemes blueprint in routes/schemes.py with Flask-SQLAlchemy integration
- [ ] T047 [US1] Implement POST /api/schemes endpoint in routes/schemes.py (create scheme with nested questions/criteria)
- [ ] T048 [US1] Implement GET /api/schemes/{id} endpoint with eager loading (joinedload questions.criteria)
- [ ] T049 [US1] Implement GET /api/schemes endpoint with pagination and category filtering
- [ ] T050 [US1] Implement PUT /api/schemes/{id} endpoint with version_number increment logic
- [ ] T051 [US1] Implement DELETE /api/schemes/{id} endpoint (soft delete: set is_deleted=True)
- [ ] T052 [US1] Implement POST /api/schemes/{id}/questions endpoint (add question to existing scheme)
- [ ] T053 [US1] Implement POST /api/questions/{id}/criteria endpoint (add criterion to question)
- [ ] T054 [US1] Add validation to all scheme routes (use utils/scheme_validator.py)
- [ ] T055 [US1] Add error handling to schemes routes (400 Bad Request, 404 Not Found, 409 Conflict)
- [ ] T056 [US1] Register schemes blueprint in app.py
- [ ] T057 [US1] Create templates/schemes/list.html (list all schemes with pagination)
- [ ] T058 [US1] Create templates/schemes/create.html (form for creating/editing schemes with dynamic question/criteria fields)
- [ ] T059 [US1] Create templates/schemes/view.html (display scheme with all questions and criteria)
- [ ] T060 [US1] Add JavaScript for dynamic form fields in create.html (add/remove questions and criteria)
- [ ] T061 [US1] Run all US1 tests and verify they PASS (pytest tests/ -k "US1 or scheme" -v)
- [ ] T062 [US1] Manual test: Create scheme via UI with 5 questions × 3 criteria, verify display and totals

**Checkpoint**: At this point, User Story 1 should be fully functional - instructors can create, view, edit, and delete grading schemes

---

## Phase 4: User Story 2 - Apply Grading Scheme to Student Submissions (Priority: P2)

**Goal**: Enable instructors to apply grading schemes to student submissions, assign points and feedback per criterion, with auto-calculation of totals

**Independent Test**: Apply an existing grading scheme to a student submission, assign points and feedback to each criterion, save partially, complete grading, verify all totals calculate correctly and data persists

### Tests for User Story 2 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [X] T063 [P] [US2] Write test_graded_submission_creation in tests/unit/test_scheme_models.py (verify GradedSubmission model)
- [X] T064 [P] [US2] Write test_criterion_evaluation_creation in tests/unit/test_scheme_models.py (verify CriterionEvaluation model)
- [X] T065 [P] [US2] Write test_submission_completion in tests/unit/test_scheme_models.py (verify is_complete triggers graded_at)
- [X] T066 [P] [US2] Write test_evaluation_points_range in tests/unit/test_scheme_models.py (verify points_awarded constraints)
- [X] T067 [P] [US2] Write test_percentage_calculation in tests/unit/test_scheme_calculator.py (verify percentage_score accuracy)
- [X] T068 [P] [US2] Write test_create_submission in tests/integration/test_grading_routes.py (POST /api/grading/submissions)
- [X] T069 [P] [US2] Write test_create_evaluation in tests/integration/test_grading_routes.py (POST /api/grading/evaluations)
- [X] T070 [P] [US2] Write test_update_evaluation in tests/integration/test_grading_routes.py (PUT /api/grading/evaluations/{id})
- [X] T071 [P] [US2] Write test_complete_submission in tests/integration/test_grading_routes.py (PATCH /api/grading/submissions/{id})
- [X] T072 [P] [US2] Write test_partial_grading in tests/integration/test_grading_routes.py (save incomplete, resume later)
- [X] T073 [P] [US2] Write test_concurrent_evaluation_conflict in tests/integration/test_grading_routes.py (optimistic locking 409)
- [X] T074 [P] [US2] Run all US2 tests and verify they FAIL (pytest tests/ -k "US2 or grading" --tb=short)

### Implementation for User Story 2

- [X] T075 [P] [US2] Implement GradedSubmission model in models.py (all fields, scheme version snapshot, optimistic locking)
- [X] T076 [P] [US2] Implement CriterionEvaluation model in models.py (points, feedback, denormalized names for export)
- [X] T077 [US2] Add to_dict() method to GradedSubmission model (include evaluations)
- [X] T078 [US2] Add to_dict() method to CriterionEvaluation model
- [X] T079 [US2] Implement auto-calculation listener for GradedSubmission.total_points_earned
- [X] T080 [US2] Implement percentage_score calculation when is_complete=True
- [X] T081 [US2] Implement calculate_submission_total() in utils/scheme_calculator.py
- [X] T082 [US2] Implement calculate_percentage_score() in utils/scheme_calculator.py with Decimal precision
- [X] T083 [US2] Create grading blueprint in routes/grading.py
- [X] T084 [US2] Implement POST /api/grading/submissions endpoint (create new graded submission)
- [X] T085 [US2] Implement GET /api/grading/submissions/{id} endpoint with eager loaded evaluations
- [X] T086 [US2] Implement PATCH /api/grading/submissions/{id} endpoint (mark complete/reopen)
- [X] T087 [US2] Implement POST /api/grading/evaluations endpoint (create/update criterion evaluation)
- [X] T088 [US2] Implement PUT /api/grading/evaluations/{id} endpoint (update points/feedback)
- [X] T089 [US2] Add optimistic locking check in update routes (evaluation_version validation, return 409 on conflict)
- [X] T090 [US2] Add validation to grading routes (points within 0 to max_points)
- [X] T091 [US2] Add error handling to grading routes (400, 404, 409 responses)
- [X] T092 [US2] Register grading blueprint in app.py
- [X] T093 [US2] Create templates/schemes/grade.html (grading form with all criteria from scheme)
- [X] T094 [US2] Add JavaScript for grading form (point validation, feedback text, save progress, submit complete)
- [X] T095 [US2] Add route to render grade.html with submission context
- [X] T096 [US2] Run all US2 tests and verify they PASS (pytest tests/ -k "US2 or grading" -v)
- [X] T097 [US2] Manual test: Grade submission with 20+ criteria, save partial, resume, complete, verify totals

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - schemes can be created and applied to grade submissions

---

## Phase 5: User Story 3 - Export Grades and Feedback in Structured Formats (Priority: P3)

**Goal**: Enable export of grading results in CSV and JSON formats for record-keeping, analysis, and LMS integration

**Independent Test**: Grade several submissions using a scheme, export to CSV and JSON, verify exported data contains all grades, feedback, metadata, and hierarchical structure is preserved

### Tests for User Story 3 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T098 [P] [US3] Write test_format_csv in tests/unit/test_export_formatters.py (verify CSV row generation)
- [ ] T099 [P] [US3] Write test_format_json in tests/unit/test_export_formatters.py (verify JSON hierarchy preservation)
- [ ] T100 [P] [US3] Write test_export_csv in tests/integration/test_export_routes.py (GET /api/export/schemes/{id}?format=csv)
- [ ] T101 [P] [US3] Write test_export_json in tests/integration/test_export_routes.py (GET /api/export/schemes/{id}?format=json)
- [ ] T102 [P] [US3] Write test_export_with_filters in tests/integration/test_export_routes.py (date range, completion filters)
- [ ] T103 [P] [US3] Write test_csv_column_headers in tests/contract/test_csv_export_contract.py (verify column order matches spec)
- [ ] T104 [P] [US3] Write test_json_schema in tests/contract/test_json_export_contract.py (verify JSON structure per spec)
- [ ] T105 [P] [US3] Run all US3 tests and verify they FAIL (pytest tests/ -k "US3 or export" --tb=short)

### Implementation for User Story 3

- [ ] T106 [P] [US3] Implement format_csv() in utils/export_formatters.py (flat denormalized rows per spec)
- [ ] T107 [P] [US3] Implement format_json() in utils/export_formatters.py (hierarchical structure with metadata)
- [ ] T108 [P] [US3] Implement calculate_aggregate_stats() in utils/scheme_calculator.py (average scores per criterion/question)
- [ ] T109 [US3] Create export blueprint in routes/export.py
- [ ] T110 [US3] Implement GET /api/export/schemes/{id} endpoint with format parameter (csv/json)
- [ ] T111 [US3] Add query filters to export endpoint (include_incomplete, start_date, end_date)
- [ ] T112 [US3] Implement CSV export response with correct Content-Type and headers
- [ ] T113 [US3] Implement JSON export response with metadata section
- [ ] T114 [US3] Add pagination support for large exports (>100 students trigger Celery async task)
- [ ] T115 [US3] Implement Celery task for async export (export_large_dataset) in tasks.py
- [ ] T116 [US3] Add export file download link generation (temporary file storage)
- [ ] T117 [US3] Add error handling to export routes (400 for invalid format, 404 for missing scheme)
- [ ] T118 [US3] Register export blueprint in app.py
- [ ] T119 [US3] Add export buttons to templates/schemes/view.html (CSV and JSON download)
- [ ] T120 [US3] Run all US3 tests and verify they PASS (pytest tests/ -k "US3 or export" -v)
- [ ] T121 [US3] Manual test: Export 100+ students with 50+ criteria, verify CSV and JSON format correctness

**Checkpoint**: All user stories should now be independently functional - complete grading scheme system with export capabilities

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T122 [P] Add comprehensive docstrings to all models in models.py
- [ ] T123 [P] Add comprehensive docstrings to all utility functions in utils/
- [ ] T124 [P] Add comprehensive docstrings to all route handlers in routes/
- [ ] T125 [P] Run flake8 linting: ./run_linting.sh and fix all issues
- [ ] T126 [P] Run black code formatter: black models.py routes/ utils/ tests/
- [ ] T127 [P] Run isort import sorter: isort models.py routes/ utils/ tests/
- [ ] T128 Verify test coverage ≥80%: pytest --cov=. --cov-report=html (constitution requirement)
- [ ] T129 [P] Add edge case tests for fractional points (2.5 out of 5.0) in tests/unit/test_scheme_calculator.py
- [ ] T130 [P] Add edge case tests for scheme modification versioning in tests/integration/test_scheme_routes.py
- [ ] T131 [P] Add edge case tests for concurrent grading scenarios in tests/integration/test_grading_routes.py
- [ ] T132 [P] Add performance test for large scheme creation (50+ criteria) in tests/integration/
- [ ] T133 [P] Add performance test for large export (1000+ students) in tests/integration/
- [ ] T134 [P] Update README.md with grading scheme feature documentation
- [ ] T135 [P] Create sample grading schemes for testing/demo purposes
- [ ] T136 Add logging for all grading operations (scheme creation, grading, export)
- [ ] T137 Add user feedback messages to templates (success/error notifications)
- [ ] T138 Security review: Verify all database queries use parameterized queries (SQLAlchemy ORM)
- [ ] T139 Security review: Verify point validation prevents negative or excessive values
- [ ] T140 Run quickstart.md validation workflow with clean database
- [ ] T141 Final integration test: Complete workflow (create scheme → grade students → export CSV/JSON)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - Can start once migrations and utilities complete
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) - Can start in parallel with US1, but US1 models help for testing
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) and US2 models (needs graded submissions to export)
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses GradingScheme from US1 but can test with fixtures
- **User Story 3 (P3)**: Requires US2 completion (needs GradedSubmission and CriterionEvaluation models)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD cycle: Red → Green → Refactor)
- Models before services/utilities
- Services/utilities before routes
- Routes before templates
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: T002-T011 can all run in parallel (different files)

**Phase 2 (Foundational)**:
- T012-T016 migrations can run sequentially (database dependencies)
- T017-T020 utilities can run in parallel once migrations complete

**Phase 3 (User Story 1 - Tests)**:
- T023-T036 all US1 tests can run in parallel (different test files)

**Phase 3 (User Story 1 - Models)**:
- T038-T040 models can run in parallel (different classes in models.py)
- T041-T043 to_dict() methods can run in parallel

**Phase 3 (User Story 1 - Routes)**:
- T047-T053 route endpoints can run in parallel (different functions in schemes.py)

**Phase 3 (User Story 1 - Templates)**:
- T057-T059 templates can run in parallel (different HTML files)

**Phase 4 (User Story 2 - Tests)**:
- T063-T073 all US2 tests can run in parallel

**Phase 4 (User Story 2 - Models)**:
- T075-T076 models can run in parallel

**Phase 5 (User Story 3 - Tests)**:
- T098-T104 all US3 tests can run in parallel

**Phase 5 (User Story 3 - Formatters)**:
- T106-T108 formatters and calculators can run in parallel

**Phase 6 (Polish)**:
- T122-T127 documentation and linting tasks can run in parallel
- T129-T135 additional tests can run in parallel

---

## Parallel Example: User Story 1

```bash
# Phase 3 - Write all tests for User Story 1 together (TDD: Red phase):
Task T023: "test_grading_scheme_creation in tests/unit/test_scheme_models.py"
Task T024: "test_scheme_to_dict in tests/unit/test_scheme_models.py"
Task T025: "test_scheme_question_creation in tests/unit/test_scheme_models.py"
Task T026: "test_question_ordering in tests/unit/test_scheme_models.py"
Task T027: "test_scheme_criterion_creation in tests/unit/test_scheme_models.py"
Task T028: "test_criterion_point_validation in tests/unit/test_scheme_models.py"
Task T029: "test_calculate_scheme_total in tests/unit/test_scheme_calculator.py"
Task T030: "test_calculate_question_total in tests/unit/test_scheme_calculator.py"
Task T031: "test_validate_point_range in tests/unit/test_scheme_validator.py"
Task T032-T036: "Integration tests in tests/integration/test_scheme_routes.py"

# Verify all tests FAIL: T037

# Phase 3 - Implement all models together (TDD: Green phase):
Task T038: "GradingScheme model in models.py"
Task T039: "SchemeQuestion model in models.py"
Task T040: "SchemeCriterion model in models.py"

# Phase 3 - Implement all routes together:
Task T047: "POST /api/schemes in routes/schemes.py"
Task T048: "GET /api/schemes/{id} in routes/schemes.py"
Task T049: "GET /api/schemes in routes/schemes.py"
Task T050: "PUT /api/schemes/{id} in routes/schemes.py"
Task T051: "DELETE /api/schemes/{id} in routes/schemes.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T011)
2. Complete Phase 2: Foundational (T012-T022) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T023-T062)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo MVP if ready

**MVP Deliverable**: Instructors can create, view, edit, and delete grading schemes with hierarchical questions and criteria. Point totals calculate automatically.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Core grading functionality!)
4. Add User Story 3 → Test independently → Deploy/Demo (Complete feature with exports!)
5. Polish phase → Deploy final version

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (Phase 1) together (T001-T011)
2. Team completes Foundational (Phase 2) together (T012-T022)
3. Once Foundational is done:
   - **Developer A**: User Story 1 (T023-T062) - Scheme management
   - **Developer B**: User Story 2 (T063-T097) - Grading functionality (starts after US1 models available)
   - **Developer C**: User Story 3 (T098-T121) - Export functionality (starts after US2 models available)
4. Stories integrate and test together
5. Team completes Polish phase together (T122-T141)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [US1], [US2], [US3] labels map tasks to specific user stories for traceability
- Each user story should be independently completable and testable
- TDD workflow: Write tests (T023-T037) → Verify FAIL (T037) → Implement (T038-T060) → Verify PASS (T061)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All database operations use SQLAlchemy ORM (parameterized queries by design)
- All point calculations use Python Decimal type for 2-decimal precision
- Soft deletes (is_deleted flag) prevent data loss for schemes with submissions
