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
- Spec-Driven Development: `SPEC_DRIVEN_DEVELOPMENT.md`

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
├── uploads/
├── .specify/                      # Spec-Driven Development setup
├── specify_cli.py                 # Spec Kit CLI tool
└── SPEC_DRIVEN_DEVELOPMENT.md     # SDD usage guide
```

## Spec-Driven Development 🚀

This project uses a simplified version of **GitHub Spec Kit** for structured development. The Spec-Driven Development methodology helps create better features through:

- **Structured specifications** with clear requirements
- **Technical planning** before implementation  
- **Task breakdown** with dependencies
- **Consistent processes** for all development

### Quick Start
```bash
python specify_cli.py check      # Verify setup
python specify_cli.py status     # View current status
```

Then use these AI agent slash commands:
- `/constitution` - View project principles
- `/specify` - Define feature requirements  
- `/plan` - Create technical implementation
- `/tasks` - Generate actionable tasks
- `/implement` - Execute development

See `SPEC_DRIVEN_DEVELOPMENT.md` for complete guide.

## License

MIT
