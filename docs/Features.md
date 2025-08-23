## Features Overview

- Multi-format uploads: DOCX, PDF, TXT
- Multiple providers: OpenRouter, Claude API, LM Studio (local)
- Marking schemes: Upload a rubric to guide grading
- Saved configurations: Reuse prompts and marking schemes
- Multi-model comparison: Compare feedback from multiple models
- Background processing with Celery; progress tracking and exports

### Marking Schemes

- Upload rubric files (DOCX/PDF/TXT) and attach to jobs
- Content is extracted and included in prompts for consistent grading

### Saved Configurations

- Save prompts and marking schemes for reuse
- Load saved items from the bulk upload and job creation flows

### Multi-Model Comparison

- Enable comparison to grade with multiple models simultaneously
- Results appear side-by-side in job details and submission views

### Configurable Parameters

- Control temperature and maximum output tokens per job
- Defaults are applied if omitted; values can be tuned per workload

### Error Handling

- Clear, actionable errors for missing keys, auth failures, timeouts
- Provider-specific handling for OpenRouter, Claude, and LM Studio
