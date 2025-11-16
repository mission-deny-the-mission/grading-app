# Tasks: Desktop Application

**Input**: Design documents from `/specs/004-desktop-app/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per constitution (Test-First Development principle). All user stories MUST have tests written BEFORE implementation (TDD workflow: tests → fail → implement → pass).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Desktop app components in `desktop/` directory
- Reuses existing Flask app in root (app.py, routes/, models.py, tasks.py)
- Tests in `tests/desktop/` for new desktop features
- Build artifacts in `dist/` and `build/` (gitignored)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and desktop module structure

- [ ] T001 Create desktop/ directory structure: main.py, app_wrapper.py, window_manager.py, task_queue.py, credentials.py, updater.py, data_export.py, settings.py
- [ ] T002 [P] Create desktop/installer/ subdirectories: windows/, macos/, linux/
- [ ] T003 [P] Create desktop/resources/ directory for icons and assets
- [ ] T004 [P] Create tests/desktop/ structure: test_wrapper.py, test_task_queue.py, test_credentials.py, test_updater.py, test_export.py, test_settings.py
- [ ] T005 Install PyInstaller>=5.13.0, pywebview>=4.0.0, keyring>=25.6.0, keyrings.cryptfile>=1.3.9, pystray>=0.19.0, apscheduler>=3.10.0, tufup>=0.5.0
- [ ] T006 [P] Create grading-app.spec PyInstaller configuration file with hiddenimports for SQLAlchemy
- [ ] T007 [P] Add desktop/ and tests/desktop/ to Python path configuration
- [ ] T008 [P] Create .gitignore entries for dist/, build/, *.spec build artifacts

**Checkpoint**: Desktop module structure ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core desktop infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Implement get_user_data_dir() in desktop/app_wrapper.py for platform-specific data paths (Windows: %APPDATA%/GradingApp, macOS: ~/Library/Application Support/GradingApp, Linux: ~/.local/share/GradingApp)
- [ ] T010 [P] Implement DesktopTaskQueue class in desktop/task_queue.py with ThreadPoolExecutor, submit(), get_status(), shutdown(), retry logic with exponential backoff
- [ ] T011 [P] Implement initialize_keyring(), set_api_key(), get_api_key(), delete_api_key() in desktop/credentials.py using keyring library
- [ ] T012 Create global task_queue instance in desktop/task_queue.py
- [ ] T013 Implement configure_app_for_desktop() in desktop/app_wrapper.py: initialize keyring, load API keys to env vars, configure SQLite database path, create user data directories
- [ ] T014 [P] Implement SQLite pragma configuration in desktop/app_wrapper.py (WAL mode, foreign keys, cache size)
- [ ] T015 [P] Create Settings class in desktop/settings.py for loading/saving settings.json (schema from data-model.md)
- [ ] T016 Implement get_free_port() helper in desktop/app_wrapper.py to auto-select available Flask port

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Install and Launch Desktop Application (Priority: P1) 🎯 MVP

**Goal**: Users can download, install, and launch the desktop app with existing grading features working offline

**Independent Test**: Download installer, run installation, launch app, verify grading interface loads and core features (schemes, submissions) are accessible without configuration

### Tests for User Story 1 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T017 [P] [US1] Unit test for desktop/main.py startup sequence in tests/desktop/test_main.py
- [ ] T018 [P] [US1] Unit test for get_user_data_dir() in tests/desktop/test_app_wrapper.py (verify correct paths for each platform)
- [ ] T019 [P] [US1] Unit test for configure_app_for_desktop() in tests/desktop/test_app_wrapper.py
- [ ] T020 [P] [US1] Integration test for Flask server startup in desktop window in tests/desktop/integration/test_startup.py
- [ ] T021 [P] [US1] Integration test for offline functionality (no internet) in tests/desktop/integration/test_offline.py

### Implementation for User Story 1

- [ ] T022 [P] [US1] Implement desktop/main.py: start_flask() function to launch Flask server in background thread
- [ ] T023 [P] [US1] Implement create_main_window() in desktop/window_manager.py using PyWebView to display Flask URL
- [ ] T024 [US1] Integrate start_flask() and create_main_window() in desktop/main.py __main__ block
- [ ] T025 [US1] Configure grading-app.spec to include templates/, static/, and uploads/ directories in datas
- [ ] T026 [US1] Add SQLAlchemy hidden imports to grading-app.spec: sqlalchemy.sql.default_comparator, sqlalchemy.dialects.sqlite, flask_sqlalchemy, flask_migrate
- [ ] T027 [US1] Test PyInstaller build: pyinstaller grading-app.spec and verify executable runs
- [ ] T028 [US1] Verify startup time <10s and memory usage <500MB idle
- [ ] T029 [US1] Test existing grading features work in desktop app (upload submission, view schemes)
- [ ] T030 [P] [US1] Create loading screen component for desktop/main.py to display during Flask startup
- [ ] T031 [US1] Add graceful shutdown handling in desktop/main.py (cleanup task queue, close Flask server)

**Checkpoint**: At this point, User Story 1 should be fully functional - users can install and use the desktop app with all existing grading features

---

## Phase 4: User Story 2 - Configure AI Providers from Desktop Interface (Priority: P2)

**Goal**: Users can configure AI provider API keys in settings with OS-native secure storage

**Independent Test**: Open settings, enter API keys, save, restart app, verify keys persist and are used for grading

### Tests for User Story 2 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T032 [P] [US2] Unit test for set_api_key(), get_api_key(), delete_api_key() in tests/desktop/test_credentials.py
- [ ] T033 [P] [US2] Unit test for initialize_keyring() with fallback to keyrings.cryptfile in tests/desktop/test_credentials.py
- [ ] T034 [P] [US2] Unit test for Settings class load/save in tests/desktop/test_settings.py
- [ ] T035 [P] [US2] Integration test for credential persistence across app restarts in tests/desktop/integration/test_credential_persistence.py
- [ ] T036 [P] [US2] Integration test for API key loading into Flask environment in tests/desktop/integration/test_credential_loading.py

### Implementation for User Story 2

- [ ] T037 [P] [US2] Create Flask route for desktop settings page in routes/desktop_settings.py: show_settings()
- [ ] T038 [P] [US2] Create Flask route for updating API keys in routes/desktop_settings.py: update_api_keys()
- [ ] T039 [P] [US2] Create Flask route for deleting API keys in routes/desktop_settings.py: delete_api_key_route()
- [ ] T040 [US2] Create desktop settings template in templates/desktop_settings.html with forms for AI provider configuration
- [ ] T041 [US2] Implement API key masking in show_settings() (display only last 4 characters)
- [ ] T042 [US2] Add link to desktop settings in main navigation menu
- [ ] T043 [US2] Test credential storage with each OS backend (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- [ ] T044 [P] [US2] Implement detect_keyring_backend() in desktop/credentials.py to identify native vs fallback storage
- [ ] T045 [US2] Add first-run dialog to show credential storage backend information
- [ ] T046 [P] [US2] Test keyrings.cryptfile fallback on systems without OS credential manager

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - users can install app and configure AI providers

---

## Phase 5: User Story 3 - Automatic Updates and Version Management (Priority: P3)

**Goal**: Users receive update notifications and can install updates with one click without data loss

**Independent Test**: Release new version, launch old version, verify update notification appears, install update, verify data preserved

### Tests for User Story 3 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T047 [P] [US3] Unit test for DesktopUpdater.check_for_updates() in tests/desktop/test_updater.py
- [ ] T048 [P] [US3] Unit test for DesktopUpdater.download_update() in tests/desktop/test_updater.py
- [ ] T049 [P] [US3] Unit test for backup_before_update() in tests/desktop/test_updater.py
- [ ] T050 [P] [US3] Integration test for full update workflow (check → download → apply) in tests/desktop/integration/test_update_workflow.py
- [ ] T051 [P] [US3] Integration test for update with data preservation in tests/desktop/integration/test_update_data_preservation.py

### Implementation for User Story 3

- [ ] T052 [P] [US3] Implement DesktopUpdater class __init__() in desktop/updater.py with tufup.client.Client initialization
- [ ] T053 [P] [US3] Implement DesktopUpdater.check_for_updates() in desktop/updater.py returning update availability dict
- [ ] T054 [P] [US3] Implement DesktopUpdater.download_update() in desktop/updater.py with progress callback
- [ ] T055 [P] [US3] Implement DesktopUpdater.apply_update() in desktop/updater.py with backup and restart logic
- [ ] T056 [US3] Implement backup_before_update() in desktop/updater.py to copy database and settings
- [ ] T057 [US3] Integrate update check on app startup in desktop/main.py (background thread)
- [ ] T058 [US3] Create show_update_notification() in desktop/window_manager.py with "Update Now" / "Remind Me Later" buttons
- [ ] T059 [US3] Implement update download progress dialog in desktop/window_manager.py
- [ ] T060 [US3] Add update settings to Settings class in desktop/settings.py (auto_check, check_frequency, deferred_version)
- [ ] T061 [US3] Test update caching (24-hour cache for update manifest)
- [ ] T062 [P] [US3] Create update metadata.json format per data-model.md
- [ ] T063 [US3] Set up GitHub Releases structure for hosting updates (or alternative hosting)

**Checkpoint**: All core user stories (1-3) should now be independently functional - install, configure, auto-update

---

## Phase 6: User Story 4 - Cross-Platform Data Portability (Priority: P4)

**Goal**: Users can export grading data to portable file and import on another machine

**Independent Test**: Create data, export to file, install on different machine, import, verify all data restored exactly

### Tests for User Story 4 (MANDATORY - Constitution Requirement) ⚠️

> **CONSTITUTION REQUIREMENT**: Write these tests FIRST, ensure they FAIL, THEN implement (TDD cycle: Red → Green → Refactor)

- [ ] T064 [P] [US4] Unit test for export_data() in tests/desktop/test_export.py
- [ ] T065 [P] [US4] Unit test for import_data() in tests/desktop/test_export.py
- [ ] T066 [P] [US4] Unit test for validate_backup_bundle() in tests/desktop/test_export.py
- [ ] T067 [P] [US4] Integration test for export → import roundtrip with 100% data fidelity in tests/desktop/integration/test_data_portability.py
- [ ] T068 [P] [US4] Integration test for automatic backup creation in tests/desktop/integration/test_automatic_backup.py

### Implementation for User Story 4

- [ ] T069 [P] [US4] Implement export_data() in desktop/data_export.py to create ZIP bundle (database + uploads + metadata.json)
- [ ] T070 [P] [US4] Implement create_backup_metadata() in desktop/data_export.py per data-model.md schema
- [ ] T071 [P] [US4] Implement import_data() in desktop/data_export.py to extract and restore ZIP bundle
- [ ] T072 [P] [US4] Implement validate_backup_bundle() in desktop/data_export.py (check integrity, schema version, file sizes)
- [ ] T073 [US4] Create Flask route for data export in routes/desktop_data.py: export_all_data()
- [ ] T074 [US4] Create Flask route for data import in routes/desktop_data.py: import_all_data()
- [ ] T075 [US4] Add "Export All Data" and "Import Data" menu items to desktop/window_manager.py system tray menu
- [ ] T076 [US4] Implement automatic backup scheduler in desktop/app_wrapper.py using APScheduler
- [ ] T077 [US4] Add backup settings to Settings class (backups_enabled, backup_frequency, backup_retention_days)
- [ ] T078 [US4] Implement backup retention cleanup (delete backups older than retention period)
- [ ] T079 [P] [US4] Test export with large database (10,000 submissions)
- [ ] T080 [P] [US4] Test import conflict handling (existing data with same names)

**Checkpoint**: All user stories (1-4) should now be complete and independently functional

---

## Phase 7: System Tray Integration (Cross-Cutting)

**Purpose**: Add system tray for show/hide/quit functionality across all user stories

- [ ] T081 [P] Create icon resources for system tray in desktop/resources/ (PNG format, multiple sizes)
- [ ] T082 [P] Implement create_system_tray() in desktop/window_manager.py using pystray library
- [ ] T083 Integrate system tray with desktop/main.py: show/hide window, check for updates, settings, quit
- [ ] T084 [P] Test system tray on Windows (system tray area)
- [ ] T085 [P] Test system tray on macOS (menu bar)
- [ ] T086 [P] Test system tray on Linux (GNOME, KDE, system tray support)
- [ ] T087 Add "Start Minimized" option to settings

---

## Phase 8: Periodic Task Migration (Cross-Cutting)

**Purpose**: Replace Celery Beat with APScheduler for periodic tasks

- [ ] T088 Create desktop/scheduler.py with APScheduler BackgroundScheduler
- [ ] T089 [P] Migrate cleanup_old_files task from tasks.py to desktop/scheduler.py (24-hour interval)
- [ ] T090 [P] Migrate cleanup_completed_batches task from tasks.py to desktop/scheduler.py (6-hour interval)
- [ ] T091 Start scheduler in desktop/main.py on app startup
- [ ] T092 Stop scheduler gracefully in desktop/main.py shutdown handler
- [ ] T093 [P] Test periodic task execution (mock time advancement)

---

## Phase 9: Celery to ThreadPoolExecutor Migration (Cross-Cutting)

**Purpose**: Replace Celery task queue with ThreadPoolExecutor for single-user desktop

- [ ] T094 Remove @celery_app.task decorators from all task functions in tasks.py
- [ ] T095 Update process_job() in tasks.py to use task_queue.submit() instead of .delay()
- [ ] T096 [P] Update retry_submission_task() in tasks.py to use task_queue.submit()
- [ ] T097 [P] Update process_batch() in tasks.py to use task_queue.submit() with countdown parameter
- [ ] T098 [P] Update process_image_ocr() in tasks.py to use task_queue.submit()
- [ ] T099 [P] Update assess_image_quality() in tasks.py to use task_queue.submit()
- [ ] T100 Update all route handlers in routes/ to use task_queue.submit() instead of .delay() (~23 call sites)
- [ ] T101 Test task chaining: process_image_ocr → assess_image_quality
- [ ] T102 Test delayed task execution (countdown parameter)
- [ ] T103 [P] Test retry logic with exponential backoff
- [ ] T104 Remove Celery and Redis dependencies from requirements.txt
- [ ] T105 Update app.py to not initialize Celery/Redis for desktop deployment

---

## Phase 10: Installer Creation (Cross-Cutting)

**Purpose**: Create native installers for each platform

### Windows Installer

- [ ] T106 [P] Create Inno Setup script in desktop/installer/windows/installer.iss
- [ ] T107 [P] Configure application metadata (name, version, publisher) in installer.iss
- [ ] T108 [P] Add uninstaller cleanup in installer.iss (preserve user data)
- [ ] T109 [P] Test Windows installer on Windows 10 and Windows 11

### macOS Installer

- [ ] T110 [P] Create DMG creation script in desktop/installer/macos/create-dmg.sh
- [ ] T111 [P] Configure macOS app bundle structure (Info.plist, icon, resources)
- [ ] T112 [P] Test macOS installer on macOS 11, 12, 13

### Linux Installer

- [ ] T113 [P] Create AppImage build script in desktop/installer/linux/create-appimage.sh
- [ ] T114 [P] Create DEB package script in desktop/installer/linux/create-deb.sh
- [ ] T115 [P] Test Linux installers on Ubuntu 20.04, 22.04, Fedora

---

## Phase 11: Code Signing (Cross-Cutting)

**Purpose**: Sign executables to avoid security warnings

- [ ] T116 Obtain EV Code Signing Certificate for Windows (~$300-500/year)
- [ ] T117 [P] Sign Windows executable with signtool.exe in desktop/installer/windows/sign.sh
- [ ] T118 Enroll in Apple Developer Program for macOS ($99/year)
- [ ] T119 [P] Sign macOS app bundle with codesign in desktop/installer/macos/sign.sh
- [ ] T120 [P] Notarize macOS app with xcrun notarytool in desktop/installer/macos/notarize.sh
- [ ] T121 [P] Staple notarization ticket with xcrun stapler in desktop/installer/macos/notarize.sh
- [ ] T122 [P] Test signed Windows installer (verify no SmartScreen warnings)
- [ ] T123 [P] Test signed macOS app (verify no Gatekeeper blocks)

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T124 [P] Add application version display in desktop UI (from __version__ in desktop/main.py)
- [ ] T125 [P] Implement crash reporting (optional, opt-in) in desktop/main.py
- [ ] T126 [P] Create application logs in user data directory (app.log, flask.log, updates.log)
- [ ] T127 [P] Add "View Logs" menu item to desktop/window_manager.py system tray
- [ ] T128 Optimize PyInstaller bundle size (exclude unnecessary dependencies, use UPX compression if <150MB target missed)
- [ ] T129 [P] Test startup performance on slow hardware (HDD, 4GB RAM)
- [ ] T130 [P] Test application with 10,000 submissions database (verify SC-004: <15s startup)
- [ ] T131 [P] Verify test coverage ≥80% for desktop modules (constitution requirement): pytest --cov=desktop --cov-report=html
- [ ] T132 [P] Update README.md with desktop installation instructions
- [ ] T133 [P] Create desktop/README.md documenting desktop module architecture
- [ ] T134 [P] Update CLAUDE.md with desktop technology stack (already done by update-agent-context.sh)
- [ ] T135 [P] Security audit: verify API keys never logged, credentials encrypted at rest
- [ ] T136 Create GitHub Actions workflow for automated builds (.github/workflows/build-desktop.yml)
- [ ] T137 [P] Test installer download and installation on fresh OS installs (Windows, macOS, Linux)
- [ ] T138 Run full manual test checklist from quickstart.md on each platform

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1) - MVP: Install and Launch ← **START HERE**
  - User Story 2 (P2): Configure AI Providers (can start after Foundational, integrates with US1)
  - User Story 3 (P3): Auto-Update (can start after Foundational, integrates with US1)
  - User Story 4 (P4): Data Portability (can start after Foundational, integrates with US1)
- **Cross-Cutting (Phases 7-12)**: Depend on desired user stories being complete
  - System Tray: After US1 (basic), enhances all stories
  - Periodic Tasks: After US1 (needed for cleanup)
  - Celery Migration: After US1 (core grading works)
  - Installers: After US1-US4 complete
  - Code Signing: After installers ready
  - Polish: After all features complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 settings but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Integrates with US1 for updates but independently testable
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Integrates with US1 for data but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD cycle)
- Models/infrastructure before services
- Services before UI/routes
- Core implementation before integration
- Story complete and tested before moving to next priority

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T002 (installer directories), T003 (resources), T004 (test structure), T006 (spec file), T007 (path config), T008 (gitignore) can all run in parallel

**Within Foundational (Phase 2)**:
- T010 (task queue), T011 (credentials), T014 (SQLite config), T015 (settings), T016 (port helper) can run in parallel after T009 (user data dir)

**Within User Stories**:
- All tests for a story can run in parallel (marked [P])
- Independent models/services within a story can run in parallel (marked [P])

**User Stories in Parallel** (if team capacity):
- After Foundational completes, US1, US2, US3, US4 can be worked on by different team members
- Recommended: Complete US1 (MVP) first, then parallelize US2-US4

**Cross-Cutting in Parallel**:
- Windows/macOS/Linux installer tasks can run in parallel (different platforms)
- Code signing tasks can run in parallel (different platforms)
- Polish tasks marked [P] can run in parallel

---

## Implementation Strategy

### Minimum Viable Product (MVP)

**Scope**: User Story 1 only
- Phases 1, 2, 3 (Setup + Foundational + US1)
- Results in working desktop app with existing grading features
- ~31 tasks (T001-T031)
- **Timeline**: 2 weeks

**Deliverable**: Installable desktop application that launches existing grading features

### Incremental Delivery

**After MVP, add in priority order**:

1. **US2 (Configure AI Providers)**: Phase 4
   - Adds secure credential storage
   - +15 tasks (T032-T046)
   - **Timeline**: +1 week

2. **US3 (Auto-Update)**: Phase 5
   - Adds update notifications and one-click updates
   - +17 tasks (T047-T063)
   - **Timeline**: +1.5 weeks

3. **US4 (Data Portability)**: Phase 6
   - Adds export/import and automatic backups
   - +16 tasks (T064-T080)
   - **Timeline**: +1 week

4. **Cross-Cutting Features**: Phases 7-12
   - System tray, periodic tasks, Celery migration, installers, signing, polish
   - +58 tasks (T081-T138)
   - **Timeline**: +2.5 weeks

**Total Timeline**: ~8 weeks for full feature (matches quickstart.md 7-week estimate + buffer)

### Recommended Approach

1. **Week 1-2**: Complete MVP (US1) - Phase 1, 2, 3
2. **Week 3**: Add US2 (Configure AI Providers) - Phase 4
3. **Week 4-5**: Add US3 (Auto-Update) - Phase 5
4. **Week 6**: Add US4 (Data Portability) - Phase 6
5. **Week 7-8**: Cross-Cutting Features and Polish - Phases 7-12

**Decision Point**: After MVP, evaluate whether US2-US4 are needed for initial release or can be deferred

---

## Task Summary

**Total Tasks**: 138 tasks

**By Phase**:
- Phase 1 (Setup): 8 tasks
- Phase 2 (Foundational): 8 tasks
- Phase 3 (US1 - Install/Launch): 15 tasks
- Phase 4 (US2 - Configure AI): 15 tasks
- Phase 5 (US3 - Auto-Update): 17 tasks
- Phase 6 (US4 - Data Portability): 16 tasks
- Phase 7 (System Tray): 7 tasks
- Phase 8 (Periodic Tasks): 6 tasks
- Phase 9 (Celery Migration): 12 tasks
- Phase 10 (Installers): 10 tasks
- Phase 11 (Code Signing): 8 tasks
- Phase 12 (Polish): 16 tasks

**Parallelizable Tasks**: 89 tasks marked [P] (64% can run in parallel when dependencies met)

**Independent Test Criteria** (per user story):
- **US1**: Download installer → Install → Launch → Verify grading interface loads
- **US2**: Open settings → Enter API keys → Save → Restart → Verify keys persist
- **US3**: Launch old version → Receive update notification → Install → Verify data preserved
- **US4**: Create data → Export → Install on new machine → Import → Verify 100% fidelity

**Suggested MVP Scope**: Phase 1-3 (US1 only) = 31 tasks = 2 weeks = Working desktop app

---

**Format Validation**: ✅ All 138 tasks follow checklist format with ID, [P] marker (where applicable), [Story] label (for user story phases), and file paths in descriptions
