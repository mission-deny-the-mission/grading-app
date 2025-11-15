# Quickstart: Structured Grading Scheme Development

**Feature**: 003-structured-grading-scheme
**Audience**: Developers implementing this feature
**Prerequisites**: Python 3.13.7, Flask development environment set up

## Development Workflow

### 1. Environment Setup

```bash
# Ensure you're on the feature branch
git checkout 003-structured-grading-scheme

# Install dependencies (if not already installed)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify database connection
# Development: SQLite (grading_app.db)
# Production: PostgreSQL (DATABASE_URL env var)
```

### 2. Test-Driven Development Workflow

**CRITICAL**: Follow TDD strictly per constitution (Principle II)

```bash
# Step 1: Write tests first (RED)
# Create test file: tests/unit/test_scheme_models.py
# Write failing test for GradingScheme model

# Step 2: Run tests (should FAIL)
pytest tests/unit/test_scheme_models.py -v

# Step 3: Implement minimal code (GREEN)
# Add GradingScheme model to models.py

# Step 4: Run tests again (should PASS)
pytest tests/unit/test_scheme_models.py -v

# Step 5: Refactor while keeping tests passing
# Improve code quality, add documentation

# Step 6: Repeat for next feature
```

### 3. Database Migration Workflow

```bash
# Create migration after adding/modifying models
flask db migrate -m "Add GradingScheme, SchemeQuestion, SchemeCriterion models"

# Review generated migration in migrations/versions/
# Verify both upgrade() and downgrade() functions

# Apply migration
flask db upgrade

# Test rollback
flask db downgrade

# Re-apply if rollback successful
flask db upgrade
```

### 4. Running Tests

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/

# Run with coverage report
pytest --cov=. --cov-report=html
# View: htmlcov/index.html

# Run specific test file
pytest tests/unit/test_scheme_models.py -v

# Run specific test function
pytest tests/unit/test_scheme_models.py::test_scheme_creation -v

# Run tests matching pattern
pytest -k "scheme" -v
```

### 5. Code Quality Checks

```bash
# Run linting (must pass before commit)
./run_linting.sh

# Or manually:
flake8 models.py routes/schemes.py utils/
black --check models.py routes/schemes.py utils/
isort --check models.py routes/schemes.py utils/

# Auto-format code
black models.py routes/schemes.py utils/
isort models.py routes/schemes.py utils/
```

## Implementation Order

Follow this sequence to maintain TDD and minimize integration issues:

### Phase 1: Models (P1 - Foundation)

1. **GradingScheme Model**
   - [ ] Write: `tests/unit/test_scheme_models.py::test_grading_scheme_creation`
   - [ ] Implement: `models.py::GradingScheme` class
   - [ ] Write: `tests/unit/test_scheme_models.py::test_scheme_to_dict`
   - [ ] Implement: `GradingScheme.to_dict()` method

2. **SchemeQuestion Model**
   - [ ] Write: `tests/unit/test_scheme_models.py::test_scheme_question_creation`
   - [ ] Implement: `models.py::SchemeQuestion` class
   - [ ] Write: `tests/unit/test_scheme_models.py::test_question_ordering`
   - [ ] Implement: display_order unique constraint

3. **SchemeCriterion Model**
   - [ ] Write: `tests/unit/test_scheme_models.py::test_scheme_criterion_creation`
   - [ ] Implement: `models.py::SchemeCriterion` class
   - [ ] Write: `tests/unit/test_scheme_models.py::test_criterion_point_validation`
   - [ ] Implement: max_points constraints (CHECK)

4. **Point Calculation Logic**
   - [ ] Write: `tests/unit/test_scheme_calculator.py::test_calculate_scheme_total`
   - [ ] Implement: `utils/scheme_calculator.py::calculate_scheme_total()`
   - [ ] Write: `tests/unit/test_scheme_calculator.py::test_calculate_question_total`
   - [ ] Implement: `utils/scheme_calculator.py::calculate_question_total()`

5. **Validation Utilities**
   - [ ] Write: `tests/unit/test_scheme_validator.py::test_validate_point_range`
   - [ ] Implement: `utils/scheme_validator.py::validate_point_range()`
   - [ ] Write: `tests/unit/test_scheme_validator.py::test_validate_hierarchy`
   - [ ] Implement: `utils/scheme_validator.py::validate_hierarchy()`

### Phase 2: Routes (P2 - CRUD Operations)

6. **Scheme CRUD Routes**
   - [ ] Write: `tests/integration/test_scheme_routes.py::test_create_scheme`
   - [ ] Implement: `routes/schemes.py::create_scheme()` endpoint
   - [ ] Write: `tests/integration/test_scheme_routes.py::test_get_scheme`
   - [ ] Implement: `routes/schemes.py::get_scheme()` endpoint
   - [ ] Write: `tests/integration/test_scheme_routes.py::test_list_schemes`
   - [ ] Implement: `routes/schemes.py::list_schemes()` endpoint
   - [ ] Write: `tests/integration/test_scheme_routes.py::test_update_scheme`
   - [ ] Implement: `routes/schemes.py::update_scheme()` endpoint (version increment)
   - [ ] Write: `tests/integration/test_scheme_routes.py::test_delete_scheme`
   - [ ] Implement: `routes/schemes.py::delete_scheme()` endpoint (soft delete)

### Phase 3: Grading (P3 - Apply Schemes)

7. **GradedSubmission & CriterionEvaluation Models**
   - [ ] Write: `tests/unit/test_scheme_models.py::test_graded_submission_creation`
   - [ ] Implement: `models.py::GradedSubmission` class
   - [ ] Write: `tests/unit/test_scheme_models.py::test_criterion_evaluation_creation`
   - [ ] Implement: `models.py::CriterionEvaluation` class

8. **Grading Routes**
   - [ ] Write: `tests/integration/test_grading_routes.py::test_create_submission`
   - [ ] Implement: `routes/grading.py::create_submission()` endpoint
   - [ ] Write: `tests/integration/test_grading_routes.py::test_create_evaluation`
   - [ ] Implement: `routes/grading.py::create_evaluation()` endpoint
   - [ ] Write: `tests/integration/test_grading_routes.py::test_update_evaluation`
   - [ ] Implement: `routes/grading.py::update_evaluation()` endpoint
   - [ ] Write: `tests/integration/test_grading_routes.py::test_complete_submission`
   - [ ] Implement: `routes/grading.py::complete_submission()` endpoint

9. **Optimistic Locking**
   - [ ] Write: `tests/integration/test_grading_routes.py::test_concurrent_evaluation_conflict`
   - [ ] Implement: evaluation_version check in update routes (409 Conflict)

### Phase 4: Export (P4 - Structured Output)

10. **Export Formatters**
    - [ ] Write: `tests/unit/test_export_formatters.py::test_format_csv`
    - [ ] Implement: `utils/export_formatters.py::format_csv()`
    - [ ] Write: `tests/unit/test_export_formatters.py::test_format_json`
    - [ ] Implement: `utils/export_formatters.py::format_json()`

11. **Export Routes**
    - [ ] Write: `tests/integration/test_export_routes.py::test_export_csv`
    - [ ] Implement: `routes/export.py::export_csv()` endpoint
    - [ ] Write: `tests/integration/test_export_routes.py::test_export_json`
    - [ ] Implement: `routes/export.py::export_json()` endpoint

12. **Contract Tests**
    - [ ] Write: `tests/contract/test_csv_export_contract.py::test_csv_column_headers`
    - [ ] Verify: CSV columns match specification
    - [ ] Write: `tests/contract/test_json_export_contract.py::test_json_schema`
    - [ ] Verify: JSON structure matches schema

### Phase 5: UI Templates (P5 - User Interface)

13. **Scheme Management Templates**
    - [ ] Create: `templates/schemes/list.html` (scheme listing)
    - [ ] Create: `templates/schemes/create.html` (create/edit scheme form)
    - [ ] Create: `templates/schemes/view.html` (view scheme details)

14. **Grading Templates**
    - [ ] Create: `templates/schemes/grade.html` (apply scheme to submission)
    - [ ] Add JavaScript for dynamic criterion evaluation form

## Testing Strategy

### Unit Tests

**Location**: `tests/unit/`

**What to test**:
- Model creation and validation
- Point calculation functions
- Validation utilities
- Export formatting functions

**Example**:
```python
# tests/unit/test_scheme_models.py
def test_grading_scheme_creation(app):
    """Test GradingScheme model creation with valid data."""
    with app.app_context():
        scheme = GradingScheme(
            name="Test Scheme",
            description="Test Description",
            category="essay"
        )
        db.session.add(scheme)
        db.session.commit()

        assert scheme.id is not None
        assert scheme.name == "Test Scheme"
        assert scheme.version_number == 1
        assert scheme.total_possible_points == 0  # No criteria yet
```

### Integration Tests

**Location**: `tests/integration/`

**What to test**:
- API endpoint responses
- Database persistence
- Route → Model → Database flow
- Error handling (400, 404, 409)

**Example**:
```python
# tests/integration/test_scheme_routes.py
def test_create_scheme(client):
    """Test POST /api/schemes creates scheme with questions."""
    data = {
        "name": "Essay Rubric",
        "category": "essay",
        "questions": [
            {
                "title": "Introduction",
                "criteria": [
                    {"name": "Thesis Clarity", "max_points": 10},
                    {"name": "Hook Quality", "max_points": 5}
                ]
            }
        ]
    }

    response = client.post('/api/schemes', json=data)

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['name'] == "Essay Rubric"
    assert json_data['total_possible_points'] == 15
    assert json_data['total_questions'] == 1
```

### Contract Tests

**Location**: `tests/contract/`

**What to test**:
- Export format compliance
- CSV column headers match spec
- JSON schema validation
- API response schemas

**Example**:
```python
# tests/contract/test_csv_export_contract.py
def test_csv_column_headers(client):
    """Verify CSV export has required columns in correct order."""
    # Setup: Create scheme, submission, evaluations

    response = client.get(f'/api/export/schemes/{scheme.id}?format=csv')

    csv_content = response.data.decode('utf-8')
    reader = csv.DictReader(io.StringIO(csv_content))

    expected_headers = [
        'Student ID', 'Student Name', 'Scheme Name', 'Scheme Version',
        'Question/Category', 'Criterion Name', 'Points Earned',
        'Max Points', 'Feedback', 'Graded By', 'Graded At'
    ]

    assert list(reader.fieldnames) == expected_headers
```

## Common Pitfalls & Solutions

### 1. Decimal Precision Issues

**Problem**: Float arithmetic causes rounding errors
```python
# ❌ WRONG: Float loses precision
points = 0.1 + 0.2  # 0.30000000000000004
```

**Solution**: Use Decimal type
```python
# ✅ CORRECT: Decimal maintains precision
from decimal import Decimal
points = Decimal('0.1') + Decimal('0.2')  # Decimal('0.3')
```

### 2. N+1 Query Problem

**Problem**: Loading scheme with questions and criteria makes N+1 queries
```python
# ❌ WRONG: Causes N+1 queries
scheme = GradingScheme.query.get(id)
for question in scheme.questions:  # Query per question
    for criterion in question.criteria:  # Query per criterion
        print(criterion.name)
```

**Solution**: Use eager loading
```python
# ✅ CORRECT: 1 query with joins
scheme = GradingScheme.query.options(
    joinedload('questions').joinedload('criteria')
).get(id)
```

### 3. Forgetting to Update Calculated Fields

**Problem**: Scheme total doesn't update when criteria change
```python
# ❌ WRONG: Total not recalculated
criterion.max_points = 20
db.session.commit()
# scheme.total_possible_points still has old value
```

**Solution**: Use SQLAlchemy event listeners
```python
# ✅ CORRECT: Auto-recalculate on change
@event.listens_for(SchemeCriterion, 'after_update')
def recalculate_totals(mapper, connection, target):
    target.question.recalculate_total()
    target.question.scheme.recalculate_total()
```

### 4. Soft Delete Leaking into Queries

**Problem**: Deleted schemes appear in listings
```python
# ❌ WRONG: Shows deleted schemes
schemes = GradingScheme.query.all()
```

**Solution**: Filter by is_deleted
```python
# ✅ CORRECT: Only active schemes
schemes = GradingScheme.query.filter_by(is_deleted=False).all()

# Or use scoped query:
class GradingScheme(db.Model):
    @classmethod
    def active(cls):
        return cls.query.filter_by(is_deleted=False)
```

## Debugging Tips

### 1. Check SQL Queries

```python
# Enable SQL logging in development
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or use Flask-DebugToolbar (already in dev dependencies)
```

### 2. Inspect Database State

```bash
# SQLite (development)
sqlite3 grading_app.db
.tables
SELECT * FROM grading_schemes;

# PostgreSQL (production)
psql $DATABASE_URL
\dt
SELECT * FROM grading_schemes;
```

### 3. Test Data Fixtures

```python
# Create test data helper (tests/conftest.py)
@pytest.fixture
def sample_scheme(app):
    """Create a complete grading scheme with questions and criteria."""
    with app.app_context():
        scheme = GradingScheme(name="Test Scheme")
        db.session.add(scheme)

        q1 = SchemeQuestion(scheme=scheme, title="Q1", display_order=1)
        db.session.add(q1)

        c1 = SchemeCriterion(question=q1, name="Clarity", max_points=10, display_order=1)
        db.session.add(c1)

        db.session.commit()
        return scheme
```

## Performance Optimization

### 1. Bulk Insert for Large Schemes

```python
# For schemes with 50+ criteria
db.session.bulk_save_objects([criterion1, criterion2, ...])
db.session.commit()
```

### 2. Export Pagination for Large Datasets

```python
# For exports with 1000+ students
def export_csv(scheme_id, page=1, per_page=100):
    submissions = GradedSubmission.query\
        .filter_by(scheme_id=scheme_id)\
        .paginate(page=page, per_page=per_page)
    # Generate CSV for this page only
```

### 3. Celery for Async Exports

```python
# For exports >100 students (per constitution)
@celery.task
def export_large_dataset(scheme_id, format):
    # Generate export file
    # Store in temporary location
    # Return file URL
```

## Next Steps

After implementing this feature:

1. Run full test suite: `pytest --cov=.`
2. Verify coverage ≥80%: Check `htmlcov/index.html`
3. Run linting: `./run_linting.sh`
4. Manual testing with UI
5. Create pull request with:
   - Test results
   - Coverage report
   - Screenshots of UI (if applicable)

## Resources

- **Spec**: [spec.md](./spec.md)
- **Plan**: [plan.md](./plan.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/api-spec.yaml](./contracts/api-spec.yaml)
- **Research**: [research.md](./research.md)
- **Constitution**: [.specify/memory/constitution.md](../.specify/memory/constitution.md)
- **Existing Tests**: `tests/test_models.py` (for reference on testing patterns)
