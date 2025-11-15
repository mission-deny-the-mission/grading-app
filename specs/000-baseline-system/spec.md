# Feature Specification: Baseline System Documentation

**Feature Branch**: `001-baseline-system`
**Created**: 2025-11-14
**Status**: Baseline Documentation
**Input**: Document existing grading application system

## User Scenarios & Testing *(mandatory)*

This specification documents the **existing capabilities** of the Document Grading Web App, an AI-powered grading system that processes student submissions using multiple AI providers.

### User Story 1 - Single Document Grading (Priority: P1)

Educators submit individual documents for AI-powered grading with customizable prompts and marking criteria.

**Why this priority**: Core MVP functionality - enables basic document grading workflow.

**Independent Test**: User can upload a single DOCX/PDF/TXT file, configure grading parameters, and receive AI-generated feedback without errors.

**Acceptance Scenarios**:

1. **Given** an educator has a student document, **When** they upload the file and configure the grading prompt, **Then** the system queues the grading job and processes it asynchronously
2. **Given** a grading job is processing, **When** the AI provider returns feedback, **Then** the system stores the grade and displays it to the educator
3. **Given** a grading job fails, **When** the educator retries the job, **Then** the system re-processes the submission with retry tracking

---

### User Story 2 - Bulk Document Processing (Priority: P1)

Educators upload multiple documents simultaneously and process them as a batch with consistent grading criteria.

**Why this priority**: Essential for classroom workflows - educators grade 20-100 submissions per assignment.

**Independent Test**: User can upload CSV with multiple document paths, configure batch settings, and monitor progress as submissions process in parallel.

**Acceptance Scenarios**:

1. **Given** an educator has multiple student submissions, **When** they upload a CSV file with document paths, **Then** the system creates a batch job with all submissions
2. **Given** a batch is processing, **When** the educator views the batch page, **Then** they see real-time progress updates (completed/failed/total counts)
3. **Given** some submissions fail in a batch, **When** the educator retries failed submissions, **Then** only failed submissions are reprocessed

---

### User Story 3 - Multi-Provider AI Integration (Priority: P1)

System supports multiple AI providers (OpenRouter, Claude, LM Studio, Ollama, Gemini, OpenAI, Chutes, Z.AI, NanoGPT) with provider-agnostic abstraction.

**Why this priority**: Core architecture principle - prevents vendor lock-in and enables flexibility.

**Independent Test**: User can select any configured AI provider, grade a document, and receive consistent response format regardless of provider.

**Acceptance Scenarios**:

1. **Given** an educator configures OpenRouter API key, **When** they create a grading job with OpenRouter, **Then** the system successfully grades documents using OpenRouter models
2. **Given** an educator switches from Claude to LM Studio, **When** they process the same document, **Then** the grading completes without code changes
3. **Given** a provider API fails, **When** the system attempts grading, **Then** clear error messages indicate the specific provider issue

---

### User Story 4 - Marking Scheme Management (Priority: P2)

Educators upload rubric files (DOCX/PDF/TXT) that guide AI grading with consistent criteria across submissions.

**Why this priority**: Improves grading consistency - ensures all submissions evaluated against same standards.

**Independent Test**: User can upload a marking scheme file, attach it to a job, and verify the rubric content is included in the AI prompt.

**Acceptance Scenarios**:

1. **Given** an educator has a grading rubric, **When** they upload the marking scheme file, **Then** the system extracts text content and stores it for reuse
2. **Given** a marking scheme exists, **When** the educator creates a grading job, **Then** they can select the scheme from saved options
3. **Given** a job uses a marking scheme, **When** the AI grades documents, **Then** the rubric content is included in the grading prompt

---

### User Story 5 - Template and Configuration Reuse (Priority: P2)

Educators save prompts, marking schemes, and batch/job configurations for repeated use across assignments.

**Why this priority**: Reduces configuration overhead - educators reuse settings for recurring assignment types.

**Independent Test**: User can save a grading prompt, load it in a new job, and verify the prompt text is pre-populated.

**Acceptance Scenarios**:

1. **Given** an educator creates a custom grading prompt, **When** they save it as a template, **Then** the prompt appears in saved configurations with usage tracking
2. **Given** saved configurations exist, **When** the educator creates a new job, **Then** they can load saved prompts and marking schemes
3. **Given** an educator uses a saved configuration, **When** the job completes, **Then** the system increments the template's usage count

---

### User Story 6 - Multi-Model Comparison (Priority: P3)

Educators compare grading output from multiple AI models simultaneously to evaluate consistency and quality.

**Why this priority**: Advanced feature - helps educators assess AI grading reliability before trusting results.

**Independent Test**: User can enable multi-model comparison, specify 3 models, and view side-by-side grading results for the same document.

**Acceptance Scenarios**:

1. **Given** an educator enables multi-model comparison, **When** they select 3 models (GPT-4, Claude, Gemini), **Then** each model grades the document independently
2. **Given** multi-model grading completes, **When** the educator views results, **Then** grades from all models appear side-by-side with model metadata
3. **Given** one model fails in comparison mode, **When** others succeed, **Then** the system displays successful grades and logs the failure

---

### User Story 7 - Result Export and Progress Tracking (Priority: P2)

Educators export grading results to CSV and monitor real-time progress for long-running batch jobs.

**Why this priority**: Integration with existing workflows - educators need results in spreadsheet format for gradebooks.

**Independent Test**: User can export a completed batch to CSV and verify all submission grades are included with metadata.

**Acceptance Scenarios**:

1. **Given** a batch job completes, **When** the educator clicks export, **Then** the system generates a CSV with all submission grades and metadata
2. **Given** a batch is processing, **When** the educator refreshes the page, **Then** progress percentages update in real-time
3. **Given** the educator closes the browser during processing, **When** they return later, **Then** progress persists and jobs continue processing

---

### Edge Cases

- **Large files**: What happens when a document exceeds the 100MB limit?
  - System rejects upload with clear error message before processing begins
- **Provider API failures**: How does the system handle transient network errors vs authentication failures?
  - Network errors trigger automatic retries with exponential backoff; auth failures fail immediately with actionable error messages
- **Concurrent job processing**: How does the system prevent API rate limit violations across simultaneous batches?
  - Semaphore-based concurrency limits per provider (configurable via environment variables)
- **Database connection loss**: What happens if the database disconnects during job processing?
  - Celery tasks use Flask app context with connection pooling; failed tasks requeue for retry
- **Text extraction failures**: How does the system handle corrupted or password-protected PDFs?
  - Extraction errors mark submission as failed with specific error message; educator can fix and retry
- **Model parameter conflicts**: What happens when temperature/max_tokens exceed provider limits?
  - System uses provider-specific validation and falls back to provider defaults if invalid

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support document uploads in DOCX, PDF, and TXT formats with content extraction
- **FR-002**: System MUST process grading jobs asynchronously using Celery task queues to prevent request timeouts
- **FR-003**: System MUST support 9 AI providers (OpenRouter, Claude, LM Studio, Ollama, Gemini, OpenAI, Chutes, Z.AI, NanoGPT) with provider-agnostic abstraction
- **FR-004**: System MUST maintain complete audit trails for submissions (status, timestamps, retry count, error messages)
- **FR-005**: System MUST allow retry of failed submissions with configurable retry limits (default: 3 attempts)
- **FR-006**: System MUST support bulk uploads via CSV with batch progress tracking (total/completed/failed counts)
- **FR-007**: System MUST enable multi-model comparison grading (parallel execution of same document across multiple models)
- **FR-008**: System MUST extract and store marking scheme content from uploaded rubric files
- **FR-009**: System MUST persist saved prompts, marking schemes, and templates with usage tracking
- **FR-010**: System MUST export batch results to CSV format with submission metadata
- **FR-011**: System MUST enforce API rate limiting per provider using semaphore-based concurrency controls
- **FR-012**: System MUST validate file uploads (type, size) before processing
- **FR-013**: System MUST store API keys in environment variables and database config (never in code)
- **FR-014**: System MUST support configurable model parameters (temperature, max_tokens) per job
- **FR-015**: System MUST calculate and display job/batch progress percentages in real-time

### Key Entities

- **GradingJob**: Represents a grading task with configuration (provider, model, prompt, temperature, max_tokens), status tracking, and submission relationships
- **Submission**: Individual document to be graded with file metadata, processing status, extracted text, grade results, and retry tracking
- **JobBatch**: Collection of grading jobs processed together with batch-level progress tracking, deadlines, and shared configuration
- **GradeResult**: Individual grading output from a specific AI model/provider, supporting multi-model comparison
- **MarkingScheme**: Uploaded rubric file with extracted content used to guide AI grading
- **SavedPrompt**: Reusable grading prompt template with usage tracking and categorization
- **SavedMarkingScheme**: Reusable marking scheme with file metadata and usage tracking
- **BatchTemplate**: Reusable batch configuration with default settings and processing rules
- **JobTemplate**: Reusable job configuration with provider, model, and parameter defaults
- **Config**: Application-wide settings including API keys, default models per provider, and system preferences

### Data Relationships

- **One-to-Many**: GradingJob → Submission (one job contains multiple documents)
- **One-to-Many**: JobBatch → GradingJob (one batch contains multiple jobs)
- **One-to-Many**: Submission → GradeResult (one submission can have results from multiple models)
- **Many-to-One**: GradingJob → MarkingScheme (many jobs can use the same rubric)
- **Many-to-One**: GradingJob → SavedPrompt (many jobs can use the same saved prompt)
- **Many-to-One**: GradingJob → SavedMarkingScheme (many jobs can reference the same saved scheme)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System processes single document submissions from upload to graded result within 2 minutes (assuming AI provider response time <60s)
- **SC-002**: System handles batch uploads of 50+ documents without UI freezing or request timeouts
- **SC-003**: Failed submissions can be retried without reprocessing successful submissions in the same job
- **SC-004**: Educators can switch between any configured AI provider without system code changes
- **SC-005**: System maintains 100% audit trail completeness (all status transitions, timestamps, and errors logged)
- **SC-006**: Batch progress updates display accurate completion percentages within 5 seconds of submission status changes
- **SC-007**: Multi-model comparison completes all configured model gradings or clearly indicates which models failed
- **SC-008**: CSV exports include all submission data (filename, grade, status, provider, model, timestamps) without data loss
- **SC-009**: System enforces provider-specific rate limits without exceeding API quotas during concurrent batch processing
- **SC-010**: Marking scheme content extraction succeeds for 95%+ of valid DOCX/PDF/TXT rubric files

## Technical Context *(for reference, not requirements)*

This section documents the existing implementation for architecture understanding:

### Technology Stack

- **Backend**: Python 3.10+, Flask web framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Task Queue**: Celery with Redis broker
- **ORM**: SQLAlchemy with session management
- **File Processing**: python-docx, PyPDF2, BeautifulSoup4 for text extraction
- **AI Providers**: OpenRouter, Anthropic, OpenAI, Google Gemini, LM Studio, Ollama, Chutes, Z.AI, NanoGPT

### Project Structure

```
grading-app/
├── app.py                    # Flask application entry point
├── models.py                 # SQLAlchemy database models
├── tasks.py                  # Celery background tasks
├── routes/                   # Flask blueprints
│   ├── main.py              # Index, config, jobs pages
│   ├── upload.py            # Single/bulk upload handlers
│   ├── api.py               # REST API endpoints
│   ├── batches.py           # Batch management
│   └── templates.py         # Template CRUD operations
├── utils/                    # Utility modules
│   ├── llm_providers.py     # AI provider abstraction layer
│   ├── text_extraction.py   # Document text extraction
│   └── file_utils.py        # File operations
├── templates/                # Jinja2 HTML templates
├── tests/                    # pytest test suite
└── docs/                     # User documentation
```

### Database Schema

- **Tables**: 11 entities (GradingJob, Submission, JobBatch, GradeResult, MarkingScheme, SavedPrompt, SavedMarkingScheme, BatchTemplate, JobTemplate, Config)
- **Migration Strategy**: SQLAlchemy migrations (version-controlled, reversible)
- **Connection Pooling**: Production PostgreSQL uses connection pooling
- **Session Management**: Flask-SQLAlchemy with expire_on_commit=False to prevent DetachedInstanceError

### Async Processing

- **Queue**: Celery with Redis broker (production) or memory (development)
- **Workers**: Configurable worker count for parallel processing
- **Concurrency**: Provider-specific semaphore limits (default: 4 for proprietary, unlimited for local)
- **Retry Logic**: Exponential backoff for network errors, max 3 retries per submission

### AI Provider Integration

- **Abstraction**: Common `grade_document()` interface across all providers
- **Response Format**: Standardized `{success, grade, model, provider, usage, error}` structure
- **Error Handling**: Provider-specific error classification (auth, network, API, rate limit)
- **Rate Limiting**: Environment-configurable concurrency per provider

### Current Capabilities

- **File Formats**: DOCX (python-docx), PDF (PyPDF2), TXT (direct read)
- **Max File Size**: 100MB (configurable via Flask MAX_CONTENT_LENGTH)
- **Concurrent Jobs**: ThreadPoolExecutor for parallel submission processing within jobs
- **Progress Tracking**: Database-backed progress calculation with real-time UI updates
- **Export Formats**: CSV with comprehensive submission metadata

## Assumptions

- Educators have basic technical literacy to configure API keys via web UI
- AI provider APIs are accessible (no corporate firewall blocking)
- Redis is available for production deployments (required for Celery)
- Uploaded documents are in supported formats (DOCX/PDF/TXT) and not corrupted
- Marking scheme files contain extractable text (not scanned images without OCR)
- Educators understand AI grading limitations and review results before finalizing grades
- System administrators manage database backups and migrations
- Environment variables (.env file) are configured before first run

## Dependencies

- **External Services**: AI provider APIs (OpenRouter, Claude, OpenAI, Gemini, Chutes, Z.AI, NanoGPT)
- **Local Services**: LM Studio (http://localhost:1234), Ollama (http://localhost:11434) for local AI
- **Infrastructure**: Redis server for Celery task queue
- **Python Packages**: See requirements.txt (Flask, SQLAlchemy, Celery, python-docx, PyPDF2, openai, anthropic, google-generativeai, beautifulsoup4)

## Out of Scope (Baseline Documentation)

This baseline specification documents **existing capabilities only**. The following are not currently implemented:

- User authentication and role-based access control
- Real-time collaborative grading
- Advanced analytics and reporting dashboards
- Integration with Learning Management Systems (LMS)
- Automated plagiarism detection
- Custom AI model fine-tuning
- Mobile application interface
- WebSocket-based live progress updates
- Advanced retry strategies beyond simple count limits
- Cost tracking and budget management per provider
