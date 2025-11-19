## Features Overview

- Multi-format uploads: DOCX, PDF, TXT
- Multiple providers: OpenRouter, Claude API, LM Studio (local), Chutes AI, Z.AI (Normal API), NanoGPT
- Grading Schemes: Upload hierarchical rubric files (questions → criteria) and attach to jobs. Schemes are versioned, cloneable, and provide structured scoring.
- Saved configurations: Reuse prompts and grading schemes
- Multi-model comparison: Compare feedback from multiple models simultaneously
- Background processing with Celery; progress tracking and exports
- Secure credential storage: API keys encrypted at rest
- Desktop Application: Standalone binaries for Windows, macOS, Linux with auto‑updates

### Grading Schemes

- Upload rubric files (DOCX/PDF/TXT) and attach to jobs
- Content is extracted and used in prompts for consistent grading
- Hierarchical structure: Scheme → Questions → Criteria, each with point values
- Versioning & cloning for easy reuse and iteration
- Usage statistics and export of detailed evaluation results

### Saved Configurations

- Save prompts and grading schemes for reuse
- Load saved items from the bulk upload and job creation flows

### Multi-Model Comparison

- Enable comparison to grade with multiple models simultaneously
- Results appear side‑by‑side in job details and submission views

### Configurable Parameters

- Control temperature and maximum output tokens per job
- Defaults are applied if omitted; values can be tuned per workload

### Error Handling

- Clear, actionable errors for missing keys, auth failures, timeouts
- Provider‑specific handling for OpenRouter, Claude, LM Studio, Chutes, Z.AI, NanoGPT
