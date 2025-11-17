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
        """
        # TODO: Implement error formatting (T026)
        pass

    @staticmethod
    def format_multiple_errors(errors: List[Dict[str, Any]]) -> str:
        """
        Format multiple validation errors for user display.

        Args:
            errors: List of error objects with {code, details}

        Returns:
            str: Formatted multi-line error message
        """
        # TODO: Implement multi-error formatting (T026)
        pass

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
        # TODO: Implement suggestion generation (T026)
        pass

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
        # TODO: Implement field error formatting (T026)
        pass
