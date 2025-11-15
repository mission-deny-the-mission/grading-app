# Error Response Standard

## Overview

All API endpoints should use the standardized error response format defined in `utils/response_utils.py`.

## Standard Format

### Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // ... response data ...
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    // ... additional context ...
  }
}
```

## Usage Examples

### Using Response Utilities

```python
from utils.response_utils import (
    success_response,
    error_response,
    unauthorized_response,
    forbidden_response,
    not_found_response,
    validation_error_response
)

# Success responses
@app.route("/api/users", methods=["POST"])
def create_user():
    user = create_user_logic()
    return success_response(
        data={"user": user.to_dict()},
        message="User created successfully",
        status_code=201
    )

# Error responses
@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return not_found_response("User not found", resource_type="user")
    return success_response(data={"user": user.to_dict()})

# Validation errors
@app.route("/api/users", methods=["POST"])
def create_user():
    errors = validate_user_data(request.json)
    if errors:
        return validation_error_response(errors)
    # ... create user ...

# Authorization errors
@app.route("/admin/users", methods=["GET"])
def admin_users():
    if not current_user.is_admin:
        return forbidden_response("Admin access required")
    # ... return users ...
```

## HTTP Status Codes

### Success (2xx)
- **200 OK**: Successful GET, PUT, PATCH, DELETE
- **201 Created**: Successful POST creating a resource
- **204 No Content**: Successful DELETE with no response body

### Client Errors (4xx)
- **400 Bad Request**: Invalid request data or validation error
- **401 Unauthorized**: Authentication required or failed
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource already exists or state conflict
- **429 Too Many Requests**: Rate limit exceeded

### Server Errors (5xx)
- **500 Internal Server Error**: Unexpected server error
- **503 Service Unavailable**: Temporary service unavailability

## Error Codes

### Authentication & Authorization
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Access denied
- `INVALID_CREDENTIALS`: Login failed
- `ACCOUNT_LOCKED`: Account temporarily locked
- `TOKEN_EXPIRED`: Session or reset token expired

### Validation
- `VALIDATION_ERROR`: Input validation failed
- `INVALID_EMAIL`: Email format invalid
- `WEAK_PASSWORD`: Password doesn't meet requirements
- `MISSING_FIELD`: Required field not provided

### Resource Management
- `NOT_FOUND`: Resource not found
- `USER_NOT_FOUND`: Specific user not found
- `PROJECT_NOT_FOUND`: Specific project not found
- `CONFLICT`: Resource already exists
- `QUOTA_EXCEEDED`: Usage limit exceeded

### Server Errors
- `INTERNAL_ERROR`: Unexpected server error
- `DATABASE_ERROR`: Database operation failed
- `EXTERNAL_API_ERROR`: External service failed

## Migration Guide

### Old Format
```python
# Before
return jsonify({"error": "User not found"}), 404
return jsonify({"success": False, "message": "Invalid data"}), 400
return jsonify({"error": str(e)}), 500
```

### New Format
```python
# After
from utils.response_utils import not_found_response, validation_error_response, server_error_response

return not_found_response("User not found", resource_type="user")
return validation_error_response({"email": "Invalid format"})
return server_error_response("Operation failed")
```

## Testing

```python
def test_user_not_found(client):
    response = client.get('/api/users/invalid-id')
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert data['error'] == "User not found"
    assert data['code'] == "USER_NOT_FOUND"

def test_validation_error(client):
    response = client.post('/api/users', json={"email": "invalid"})
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert data['code'] == "VALIDATION_ERROR"
    assert 'validation_errors' in data['details']
```

## Best Practices

1. **Consistent Format**: Always use response_utils functions
2. **Meaningful Messages**: Provide clear, actionable error messages
3. **Error Codes**: Use standard error codes for client handling
4. **Details**: Include additional context when helpful
5. **Security**: Don't expose sensitive information in errors
6. **Logging**: Log errors server-side before returning to client

## Current Status

**Note**: As of Phase 11, standardized response utilities have been created in `utils/response_utils.py`. Routes are currently using mixed formats. Future refactoring should migrate all routes to use the standardized format.

### Routes to Migrate
- `routes/sharing_routes.py`
- `routes/usage_routes.py`
- `routes/config_routes.py`
- `routes/api.py`
- `routes/batches.py`
- `routes/templates.py`

Migration is optional for current deployment but recommended for consistency.
