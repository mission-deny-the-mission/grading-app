## Testing

Run tests from the project root using the virtual environment.

### Quick commands

```bash
./venv/bin/python -m pytest
```

Run specific modules or increase verbosity:

```bash
./venv/bin/python -m pytest tests/test_models.py -v
./venv/bin/python -m pytest -k "create and not slow"
```

### Coverage

Coverage may be enabled by default via configuration. To avoid generating HTML coverage locally, run:

```bash
./venv/bin/python -m pytest --no-cov
```

### Structure

```
tests/
  conftest.py      # fixtures
  test_models.py   # models/db
  test_routes.py   # Flask routes/API
  test_tasks.py    # Celery tasks/providers
  test_utils.py    # helpers and extraction
```

### CI

The suite is designed for CI. Typical steps:

```bash
pip install -r requirements-dev.txt
./venv/bin/python -m pytest
```
