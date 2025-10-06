# Grading App - Spec-Driven Development Agent Guide

This document provides guidance for AI agents working with the Grading App using Spec-Driven Development methodology.

## Available Slash Commands

### `/constitution`
Create or update project governing principles and development guidelines that will guide all subsequent development.

**Usage:**
```
/constitution Create principles focused on [specific areas]
```

**Example:**
```
/constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements
```

**Result:** Updates `.specify/memory/constitution.md` with project principles

### `/specify`
Define what you want to build (requirements and user stories). Focus on the "what" and "why", not the tech stack.

**Usage:**
```
/specify [detailed description of feature requirements]
```

**Example:**
```
/specify Enhance the bulk grading system to support real-time progress tracking, allowing users to monitor batch processing status, pause/resume operations, and receive notifications when grading is complete
```

**Result:** Creates new feature specification in `.specify/specs/XXX-feature-name/spec.md`

### `/clarify`
Resolve underspecified areas through structured questioning. Must be run before `/plan` unless explicitly skipped.

**Usage:**
```
/clarify
```

**Result:** Adds clarifications section to specification with Q&A format

### `/plan`
Create technical implementation plans with your chosen tech stack and architecture choices.

**Usage:**
```
/plan [technical implementation details and architecture choices]
```

**Example:**
```
/plan Use WebSocket connections for real-time updates, Redis for status storage, and add Celery task monitoring with progress callbacks
```

**Result:** Creates implementation plan, data models, and research documents in the feature directory

### `/tasks`
Generate actionable task lists for implementation from the technical plan.

**Usage:**
```
/tasks
```

**Result:** Creates detailed task breakdown in `.specify/specs/XXX-feature-name/tasks.md`

### `/analyze`
Cross-artifact consistency & coverage analysis. Run after `/tasks`, before `/implement`.

**Usage:**
```
/analyze
```

**Result:** Validates consistency between spec, plan, and tasks; identifies gaps

### `/implement`
Execute all tasks to build the feature according to the plan.

**Usage:**
```
/implement
```

**Result:** Executes the implementation plan by running tasks in order

## Project Context

### Current System Architecture
- **Backend**: Flask with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Database**: SQLite (default) or PostgreSQL
- **AI Integration**: Multiple providers (OpenRouter, Claude API, LM Studio)
- **File Processing**: DOCX, PDF, TXT support

### Key Components
- `app.py` - Main Flask application
- `models.py` - Database models
- `tasks.py` - Celery background tasks
- `routes/` - Flask route blueprints
- `utils/` - Utility modules (LLM providers, text extraction, file handling)

### Development Guidelines
- Follow PEP 8 with Black formatting
- Use blueprint pattern for Flask routes
- Implement comprehensive tests (minimum 80% coverage)
- Handle AI provider errors gracefully
- Use async processing for long-running operations
- Maintain security and privacy standards

## Example Workflow

1. **Establish Principles:**
   ```
   /constitution Create principles focused on real-time user feedback and system reliability
   ```

2. **Define Requirements:**
   ```
   /specify Add real-time notifications to the grading dashboard so users can see progress updates as documents are being processed, including current status, completion percentage, and estimated time remaining
   ```

3. **Clarify Details:**
   ```
   /clarify
   ```

4. **Plan Implementation:**
   ```
   /plan Use WebSocket connections with Socket.IO for real-time updates, Redis pub/sub for message broadcasting, and update the Celery tasks to emit progress events
   ```

5. **Generate Tasks:**
   ```
   /tasks
   ```

6. **Analyze Coverage:**
   ```
   /analyze
   ```

7. **Execute Implementation:**
   ```
   /implement
   ```

## File Structure

```
.specify/
├── memory/
│   └── constitution.md          # Project principles
├── specs/
│   └── XXX-feature-name/
│       ├── spec.md              # Feature requirements
│       ├── plan.md              # Technical implementation plan
│       ├── tasks.md             # Task breakdown
│       └── research.md          # Technical research
├── templates/
│   ├── spec-template.md         # Specification template
│   ├── plan-template.md         # Plan template
│   └── tasks-template.md        # Tasks template
└── CLAUDE.md                    # This file
```

## Important Notes

- Always run `/clarify` before `/plan` unless you explicitly want to skip it
- Focus on "what" and "why" in `/specify`, save "how" for `/plan`
- The constitution guides all subsequent development decisions
- Use the existing codebase patterns and architecture
- Maintain backward compatibility when possible
- Test thoroughly before marking features complete