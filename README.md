# Document Grading Web App

[![CI](https://gitea.harryslab.xyz/mission-deny-the-mission/grading-app/actions/workflows/ci.yml/badge.svg?branch=main)](https://gitea.harryslab.xyz/mission-deny-the-mission/grading-app/actions)

AI-powered document grading with support for OpenRouter, Claude API, and LM Studio.

## 🔧 Recent Fixes

### Bulk Upload Model Loading Issue (Fixed)
A critical issue where the bulk upload system failed to load models due to missing DOM elements has been resolved. The system now properly fetches and displays models from all AI providers.

**Validation**: Run `python validate_bulk_upload_fix.py` to verify the fix and prevent regressions.

## Quick Links

- Getting started: `docs/Getting-Started.md`
- Features overview: `docs/Features.md`
- Testing: `docs/Testing.md`
- Docker: `docs/Docker.md`
- Bulk upload tests: `tests/README_bulk_upload_tests.md`

## File structure

```
grading-app/
├── app.py
├── routes/
├── utils/
├── models.py
├── tasks.py
├── templates/
├── docs/
├── tests/
├── validate_bulk_upload_fix.py  # Quick validation script
└── uploads/
```

## License

MIT
