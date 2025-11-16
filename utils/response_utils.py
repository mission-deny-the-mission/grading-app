"""
Response Utility Functions

Standardized response formats for consistent API behavior.
"""

from flask import jsonify


def success_response(data=None, message=None, status_code=200):
    """
    Create a standardized success response.

    Args:
        data: Optional data payload
        message: Optional success message
        status_code: HTTP status code (default: 200)

    Returns:
        tuple: (flask.Response, int)

    Example:
        return success_response({"user": user_dict}, "User created", 201)
        # Returns: ({"success": True, "message": "User created", "data": {"user": ...}}, 201)
    """
    response = {"success": True}

    if message:
        response["message"] = message

    if data is not None:
        response["data"] = data

    return jsonify(response), status_code


def error_response(message, status_code=400, error_code=None, details=None):
    """
    Create a standardized error response.

    Args:
        message: Error message for the user
        status_code: HTTP status code (default: 400)
        error_code: Optional application-specific error code
        details: Optional additional error details

    Returns:
        tuple: (flask.Response, int)

    Example:
        return error_response("User not found", 404, "USER_NOT_FOUND")
        # Returns: ({"success": False, "error": "User not found", "code": "USER_NOT_FOUND"}, 404)
    """
    response = {
        "success": False,
        "error": message
    }

    if error_code:
        response["code"] = error_code

    if details:
        response["details"] = details

    return jsonify(response), status_code


def validation_error_response(errors, message="Validation failed"):
    """
    Create a standardized validation error response.

    Args:
        errors: dict or list of validation errors
        message: Optional error message

    Returns:
        tuple: (flask.Response, int)

    Example:
        return validation_error_response({"email": "Invalid format", "password": "Too short"})
        # Returns: ({"success": False, "error": "Validation failed", "validation_errors": {...}}, 400)
    """
    return error_response(
        message=message,
        status_code=400,
        error_code="VALIDATION_ERROR",
        details={"validation_errors": errors}
    )


# Common HTTP error responses
def unauthorized_response(message="Authentication required"):
    """Return 401 Unauthorized response."""
    return error_response(message, 401, "UNAUTHORIZED")


def forbidden_response(message="Access denied"):
    """Return 403 Forbidden response."""
    return error_response(message, 403, "FORBIDDEN")


def not_found_response(message="Resource not found", resource_type=None):
    """Return 404 Not Found response."""
    code = f"{resource_type.upper()}_NOT_FOUND" if resource_type else "NOT_FOUND"
    return error_response(message, 404, code)


def conflict_response(message="Resource already exists"):
    """Return 409 Conflict response."""
    return error_response(message, 409, "CONFLICT")


def server_error_response(message="Internal server error"):
    """Return 500 Internal Server Error response."""
    return error_response(message, 500, "INTERNAL_ERROR")
