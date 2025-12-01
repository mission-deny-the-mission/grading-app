# Code Style and Conventions

## Python Style

### General
- Follow PEP 8 style guidelines
- Use `black` for formatting
- Use `isort` for import sorting
- Use `ruff` for linting

### Naming Conventions
- **Classes**: PascalCase (e.g., `GradingJob`, `SchemeQuestion`)
- **Functions/Methods**: snake_case (e.g., `create_job`, `get_scheme_by_id`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `UPLOAD_FOLDER`, `DEFAULT_SQLITE_PATH`)
- **Variables**: snake_case (e.g., `grading_job`, `batch_template`)

### Type Hints
- Type hints are used but not consistently enforced
- Use type hints for function parameters and return values when practical

### Docstrings
- Module-level docstrings for files
- Function/method docstrings for public APIs
- Follow Google-style docstrings where used

## Flask Patterns

### Blueprints
- Routes are organized into blueprints in `routes/` directory
- Each feature area has its own route module
- Blueprints registered in `app.py`

### Request Handling
```python
@blueprint.route('/endpoint', methods=['POST'])
def endpoint():
    data = request.get_json()
    # Validation and processing
    return jsonify({'status': 'success', 'data': result})
```

### Error Handling
- Use `jsonify` for API responses
- Return appropriate HTTP status codes
- Use `response_utils.py` for consistent responses

## SQLAlchemy Patterns

### Model Definition
```python
class ModelName(db.Model):
    __tablename__ = 'table_name'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # ... other columns
    
    def to_dict(self):
        return {
            'id': self.id,
            # ... other fields
        }
```

### Relationships
- Use `db.relationship()` with `backref` or `back_populates`
- Define foreign keys explicitly

## Testing Patterns

### Test Structure
```python
class TestFeatureName:
    """Test suite for feature."""
    
    def test_specific_behavior(self, app, client):
        """Test description."""
        with app.app_context():
            # Setup
            # Action
            # Assertion
```

### Fixtures
- Use pytest fixtures for common setup
- App fixture provides Flask app context
- Client fixture provides test client

## File Organization
- One module per logical feature area
- Separate routes, services, and utilities
- Keep models in single `models.py` file
