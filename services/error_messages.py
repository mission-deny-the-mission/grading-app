"""
Error Messages Service

Standardized error messages for import validation failures.
Implements FR-009 (Clear Error Messages).
"""

from typing import Dict, List, Any

class ErrorMessageFormatter:
    """Formats standardized error messages for user feedback."""

    # Error message templates
    ERRORS = {
        'INVALID_JSON': 'Invalid JSON format: {detail}',
        'MISSING_FIELD': 'Required field missing: {field}',
        'INVALID_FIELD_TYPE': 'Field {field} must be {expected_type}, got {actual_type}',
        'INVALID_ENUM': 'Field {field} must be one of {valid_values}, got {actual_value}',
        'NUMERIC_OUT_OF_RANGE': 'Field {field} must be between {min} and {max}, got {actual}',
        'STRING_TOO_LONG': 'Field {field} must be max {max_length} chars, got {actual_length}',
        'STRING_TOO_SHORT': 'Field {field} must be at least {min_length} chars',
        'EMPTY_ARRAY': 'Field {field} must have at least {min_items} items, got {actual_count}',
        'DUPLICATE_ITEM': 'Duplicate {item_type}: {item_name} at {location}',
        'MISSING_RELATIONSHIP': 'Field {field} references non-existent {referenced_type}: {ref_id}',
        'INVALID_FILE_SIZE': 'File size {actual_size} exceeds maximum {max_size}',
        'INVALID_FILE_TYPE': 'File type must be {valid_types}, got {actual_type}',
        'FILE_UPLOAD_FAILED': 'Failed to upload file: {detail}',
        'PERMISSION_DENIED': 'You do not have permission to {action}',
        'RESOURCE_NOT_FOUND': '{resource_type} not found: {resource_id}',
    }

    @staticmethod
    def format_validation_error(error_code: str, **kwargs) -> str:
        """
        Format a validation error message.

        Args:
            error_code: Error code key (from ERRORS dict)
            **kwargs: Template parameters

        Returns:
            str: Formatted error message

        Raises:
            KeyError: If error_code is not found in ERRORS
        """
        if error_code not in ErrorMessageFormatter.ERRORS:
            raise KeyError(f"Unknown error code: {error_code}")

        template = ErrorMessageFormatter.ERRORS[error_code]

        # Provide default values for missing parameters to maintain backward compatibility
        required_params = {
            'INVALID_JSON': {'detail': 'unknown error'},
            'MISSING_FIELD': {'field': 'unknown'},
            'INVALID_FIELD_TYPE': {'field': 'unknown', 'expected_type': 'valid type', 'actual_type': 'unknown'},
            'INVALID_ENUM': {'field': 'unknown', 'valid_values': 'valid options', 'actual_value': 'unknown'},
            'NUMERIC_OUT_OF_RANGE': {'field': 'unknown', 'min': '0', 'max': 'unknown', 'actual': 'unknown'},
            'STRING_TOO_LONG': {'field': 'unknown', 'max_length': 'unknown', 'actual_length': 'unknown'},
            'STRING_TOO_SHORT': {'field': 'unknown', 'min_length': 'unknown'},
            'EMPTY_ARRAY': {'field': 'unknown', 'min_items': '1', 'actual_count': '0'},
            'DUPLICATE_ITEM': {'item_type': 'item', 'item_name': 'unknown', 'location': 'unknown'},
            'MISSING_RELATIONSHIP': {'field': 'unknown', 'referenced_type': 'item', 'ref_id': 'unknown'},
            'INVALID_FILE_SIZE': {'actual_size': 'unknown', 'max_size': 'unknown'},
            'INVALID_FILE_TYPE': {'valid_types': 'valid types', 'actual_type': 'unknown'},
            'FILE_UPLOAD_FAILED': {'detail': 'unknown error'},
            'PERMISSION_DENIED': {'action': 'perform this action'},
            'RESOURCE_NOT_FOUND': {'resource_type': 'resource', 'resource_id': 'unknown'},
        }

        # Merge provided kwargs with defaults
        all_params = {**required_params.get(error_code, {}), **kwargs}

        try:
            return template.format(**all_params)
        except KeyError as e:
            # Fallback to simple error message if formatting fails
            return f"Validation error: {error_code} - {str(e)}"

    @staticmethod
    def format_multiple_errors(errors: List[Dict[str, Any]]) -> str:
        """
        Format multiple validation errors for user display.

        Args:
            errors: List of error objects with {code, details}

        Returns:
            str: Formatted multi-line error message
        """
        if not errors:
            return "No validation errors found."

        error_messages = []
        for error in errors:
            if isinstance(error, dict):
                error_code = error.get('code', 'UNKNOWN_ERROR')
                details = error.get('details', {})
                try:
                    formatted = ErrorMessageFormatter.format_validation_error(error_code, **details)
                    error_messages.append(f"• {formatted}")
                except (KeyError, ValueError) as e:
                    error_messages.append(f"• Validation error: {str(e)}")
            else:
                error_messages.append(f"• {str(error)}")

        return "Validation failed with the following errors:\n" + "\n".join(error_messages)

    @staticmethod
    def get_error_suggestion(error_code: str, **kwargs) -> str:
        """
        Get user-friendly suggestion for fixing error.

        Args:
            error_code: Error code
            **kwargs: Error context

        Returns:
            str: Suggestion text
        """
        suggestions = {
            'INVALID_JSON': "Please check the JSON syntax and ensure it's properly formatted.",
            'MISSING_FIELD': "Please add the required '{field}' field to your data.",
            'INVALID_FIELD_TYPE': "Please ensure '{field}' is of type {expected_type}.",
            'INVALID_ENUM': "Please use one of the valid values: {valid_values}.",
            'NUMERIC_OUT_OF_RANGE': "Please adjust '{field}' to be between {min} and {max}.",
            'STRING_TOO_LONG': "Please shorten '{field}' to {max_length} characters or less.",
            'STRING_TOO_SHORT': "Please extend '{field}' to at least {min_length} characters.",
            'EMPTY_ARRAY': "Please add at least {min_items} items to '{field}'.",
            'DUPLICATE_ITEM': "Please remove or rename the duplicate {item_type}.",
            'MISSING_RELATIONSHIP': "Please ensure all references in '{field}' point to existing items.",
            'INVALID_FILE_SIZE': "Please reduce the file size or increase the upload limit.",
            'INVALID_FILE_TYPE': "Please upload a file of type: {valid_types}.",
            'FILE_UPLOAD_FAILED': "Please try uploading the file again.",
            'PERMISSION_DENIED': "Please contact an administrator for access to {action}.",
            'RESOURCE_NOT_FOUND': "Please verify the {resource_type} exists and try again.",
        }

        if error_code not in suggestions:
            return "Please review the error details and correct the issue."

        try:
            return suggestions[error_code].format(**kwargs)
        except KeyError:
            return suggestions[error_code]

    @staticmethod
    def format_field_error(field_path: str, error_type: str, expected: Any, actual: Any) -> Dict[str, str]:
        """
        Format a specific field error with context.

        Args:
            field_path: JSON path to field (e.g., "criteria[0].level")
            error_type: Type of error
            expected: What was expected
            actual: What was provided

        Returns:
            dict: {field, error_message, suggestion}
        """
        error_message = f"Field '{field_path}' has {error_type}: expected {expected}, got {actual}"

        # Generate suggestion based on error type
        if error_type == "type mismatch":
            suggestion = f"Please ensure '{field_path}' is of type {expected}."
        elif error_type == "value out of range":
            suggestion = f"Please adjust '{field_path}' to be within the valid range."
        elif error_type == "missing field":
            suggestion = f"Please provide a value for '{field_path}'."
        else:
            suggestion = f"Please correct the value for '{field_path}'."

        return {
            'field': field_path,
            'error_message': error_message,
            'suggestion': suggestion
        }
