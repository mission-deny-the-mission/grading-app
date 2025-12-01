# Task Completion Checklist

## Before Committing Code

### 1. Run Tests
```bash
# Run full test suite
pytest tests/

# Or run specific tests related to your changes
pytest tests/test_<relevant_module>.py -v
```

### 2. Run Linting
```bash
# Check for linting issues
ruff check .

# Fix auto-fixable issues
ruff check . --fix
```

### 3. Format Code
```bash
# Format with black
black .

# Sort imports
isort .
```

### 4. Database Migrations
If you modified models:
```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

### 5. Manual Testing
- Test the feature in the browser at http://localhost:5001
- Test API endpoints with curl or Postman
- For desktop changes, run `python run_desktop_dev.py`

## Code Review Considerations

### Security
- [ ] API keys are encrypted, never logged in plaintext
- [ ] User input is validated and sanitized
- [ ] No SQL injection vulnerabilities
- [ ] CSRF protection on forms
- [ ] Proper authentication/authorization checks

### Quality
- [ ] Code follows existing patterns and conventions
- [ ] No unused imports or dead code
- [ ] Error handling is appropriate
- [ ] Logging is informative but not excessive

### Testing
- [ ] New features have test coverage
- [ ] Existing tests still pass
- [ ] Edge cases are handled

## Post-Deployment

### Monitor
- Check application logs for errors
- Verify database migrations applied correctly
- Test critical user flows

### Rollback Plan
- Keep database backup before migrations
- Document how to revert changes if needed
