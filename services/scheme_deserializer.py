"""
Marking Scheme Deserialization Service

Handles conversion of JSON to MarkingScheme objects for import.
Implements deserialization for User Story 2 (Import Marking Schemes).
"""

import json
from typing import Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import os

try:
    import jsonschema
except ImportError:
    jsonschema = None


class MarkingSchemeDecoder:
    """Deserializes JSON to MarkingScheme objects."""

    def __init__(self):
        """Initialize deserializer with JSON schema."""
        self.schema = self._load_schema()
        self.validation_errors = []

    def _load_schema(self) -> Dict[str, Any]:
        """
        Load JSON schema for validation.

        Returns:
            dict: JSON schema or empty dict if not found
        """
        try:
            # Try to load from specs directory
            schema_path = Path(__file__).parent.parent / 'specs' / '005-marking-schema-as-file' / 'json-schema.json'
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass

        # Return a minimal schema if file not found
        return {}

    def deserialize(self, json_string: str):
        """
        Deserialize JSON string to dictionary representation of MarkingScheme.

        Args:
            json_string: JSON string containing scheme data

        Returns:
            dict: Scheme data dictionary ready for database insertion

        Raises:
            ValueError: If JSON is invalid or doesn't match schema
        """
        # Parse JSON string
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

        # Validate against schema
        errors = self.collect_validation_errors(data)
        if errors:
            error_msg = self.format_validation_errors(errors)
            raise ValueError(f"Schema validation failed: {error_msg}")

        # Convert to standard format
        return self.from_dict(data)

    def from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create MarkingScheme dictionary from validated data.

        Args:
            data: Dictionary with scheme structure from JSON

        Returns:
            dict: Normalized scheme data

        Raises:
            ValueError: If data is invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Scheme data must be a dictionary")

        # Extract metadata
        metadata = data.get('metadata', {})
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be an object")

        scheme_name = metadata.get('name')
        if not scheme_name:
            raise ValueError("Scheme name is required")

        # Extract and validate criteria
        criteria_list = data.get('criteria', [])
        if not isinstance(criteria_list, list):
            raise ValueError("Criteria must be an array")

        if not criteria_list:
            raise ValueError("At least one criterion is required")

        criteria = self.decode_criteria(criteria_list)

        # Return normalized scheme data
        return {
            'name': scheme_name,
            'description': metadata.get('description'),
            'criteria': criteria,
            'version': data.get('version', '1.0.0'),
            'metadata': metadata
        }

    def decode_criteria(self, criteria_list: list) -> list:
        """
        Decode criteria from JSON format.

        Args:
            criteria_list: List of criterion dictionaries

        Returns:
            list: List of normalized criterion dictionaries
        """
        decoded = []

        for i, criterion in enumerate(criteria_list):
            if not isinstance(criterion, dict):
                raise ValueError(f"Criterion at index {i} must be an object")

            # Required fields
            criterion_id = criterion.get('id')
            name = criterion.get('name')

            if not name:
                raise ValueError(f"Criterion at index {i} is missing required field: name")

            criterion_dict = {
                'id': criterion_id,
                'name': name,
            }

            # Optional fields
            if 'description' in criterion:
                criterion_dict['description'] = criterion['description']

            if 'weight' in criterion:
                criterion_dict['weight'] = float(criterion['weight'])

            if 'point_value' in criterion:
                criterion_dict['point_value'] = float(criterion['point_value'])

            # Decode descriptors
            descriptors = criterion.get('descriptors', [])
            if not isinstance(descriptors, list):
                raise ValueError(f"Descriptors for criterion '{name}' must be an array")

            if not descriptors:
                raise ValueError(f"Criterion '{name}' must have at least one descriptor")

            criterion_dict['descriptors'] = self.decode_descriptors(descriptors)

            decoded.append(criterion_dict)

        return decoded

    def decode_descriptors(self, descriptors_list: list) -> list:
        """
        Decode performance descriptors from JSON format.

        Args:
            descriptors_list: List of descriptor dictionaries

        Returns:
            list: List of normalized descriptor dictionaries
        """
        decoded = []

        valid_levels = ['excellent', 'good', 'satisfactory', 'poor', 'fail']

        for i, descriptor in enumerate(descriptors_list):
            if not isinstance(descriptor, dict):
                raise ValueError(f"Descriptor at index {i} must be an object")

            # Validate level
            level = descriptor.get('level')
            if not level:
                raise ValueError(f"Descriptor at index {i} is missing required field: level")

            if level.lower() not in valid_levels:
                raise ValueError(
                    f"Descriptor at index {i} has invalid level '{level}'. "
                    f"Must be one of: {', '.join(valid_levels)}"
                )
            
            # Normalize level
            level = level.lower()

            # Validate description
            desc = descriptor.get('description')
            if not desc:
                raise ValueError(f"Descriptor at index {i} is missing required field: description")

            descriptor_dict = {
                'level': level,
                'description': desc,
            }

            # Optional points field
            if 'points' in descriptor:
                descriptor_dict['points'] = float(descriptor['points'])

            decoded.append(descriptor_dict)

        return decoded

    def validate_scheme_json(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Validate JSON against JSON schema.

        Args:
            data: Dictionary to validate

        Returns:
            (is_valid, errors): Boolean validity and list of error details
        """
        if not self.schema or not jsonschema:
            # If schema not loaded or jsonschema not available, do basic validation
            return self._basic_validation(data)

        errors = []
        try:
            jsonschema.validate(instance=data, schema=self.schema)
        except jsonschema.ValidationError as e:
            errors.append({
                'field': e.json_path or 'root',
                'error_type': e.validator,
                'message': e.message,
            })
        except jsonschema.SchemaError as e:
            errors.append({
                'field': 'schema',
                'error_type': 'schema_error',
                'message': str(e),
            })

        return len(errors) == 0, errors

    def _basic_validation(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Perform basic structural validation when schema is not available.

        Args:
            data: Dictionary to validate

        Returns:
            (is_valid, errors): Validation result
        """
        errors = []

        if not isinstance(data, dict):
            errors.append({
                'field': 'root',
                'message': 'Data must be an object'
            })
            return False, errors

        # Check required top-level fields
        if 'version' not in data:
            errors.append({'field': 'version', 'message': 'Required field missing'})
        if 'metadata' not in data:
            errors.append({'field': 'metadata', 'message': 'Required field missing'})
        if 'criteria' not in data:
            errors.append({'field': 'criteria', 'message': 'Required field missing'})

        # Check metadata
        if 'metadata' in data:
            metadata = data['metadata']
            if not isinstance(metadata, dict):
                errors.append({'field': 'metadata', 'message': 'Metadata must be an object'})
            elif 'name' not in metadata:
                errors.append({'field': 'metadata.name', 'message': 'Scheme name is required'})

        # Check criteria
        if 'criteria' in data:
            criteria = data['criteria']
            if not isinstance(criteria, list):
                errors.append({'field': 'criteria', 'message': 'Criteria must be an array'})
            elif len(criteria) == 0:
                errors.append({'field': 'criteria', 'message': 'At least one criterion is required'})

        return len(errors) == 0, errors

    def collect_validation_errors(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect ALL validation errors (don't fail on first error).

        Returns list of errors with field path, error type, and suggestions.

        Args:
            json_data: Data to validate

        Returns:
            list: Detailed error objects
        """
        errors = []

        # Validate JSON structure
        is_valid, schema_errors = self.validate_scheme_json(json_data)
        if not is_valid:
            errors.extend(schema_errors)

        # Additional detailed validation
        if isinstance(json_data, dict):
            # Validate metadata
            metadata = json_data.get('metadata', {})
            if isinstance(metadata, dict):
                if not metadata.get('name'):
                    errors.append({
                        'field': 'metadata.name',
                        'error_type': 'required',
                        'suggestion': 'Scheme name is required'
                    })

            # Validate criteria
            criteria = json_data.get('criteria', [])
            if isinstance(criteria, list):
                for i, criterion in enumerate(criteria):
                    if isinstance(criterion, dict):
                        # Check required fields
                        if not criterion.get('name'):
                            errors.append({
                                'field': f'criteria[{i}].name',
                                'error_type': 'required',
                                'suggestion': 'Criterion name is required'
                            })

                        # Validate descriptors
                        descriptors = criterion.get('descriptors', [])
                        if not isinstance(descriptors, list):
                            errors.append({
                                'field': f'criteria[{i}].descriptors',
                                'error_type': 'type',
                                'expected': 'array',
                                'actual': type(descriptors).__name__,
                                'suggestion': 'Descriptors must be an array'
                            })
                        elif not descriptors:
                            errors.append({
                                'field': f'criteria[{i}].descriptors',
                                'error_type': 'min_items',
                                'suggestion': 'At least one descriptor is required'
                            })
                        else:
                            # Validate each descriptor
                            for j, desc in enumerate(descriptors):
                                if isinstance(desc, dict):
                                    if not desc.get('level'):
                                        errors.append({
                                            'field': f'criteria[{i}].descriptors[{j}].level',
                                            'error_type': 'required',
                                            'suggestion': 'Performance level is required'
                                        })
                                    elif desc['level'] not in ['excellent', 'good', 'satisfactory', 'poor', 'fail']:
                                        errors.append({
                                            'field': f'criteria[{i}].descriptors[{j}].level',
                                            'error_type': 'enum',
                                            'expected': 'excellent, good, satisfactory, poor, fail',
                                            'actual': desc['level'],
                                            'suggestion': f"Level must be one of: excellent, good, satisfactory, poor, fail"
                                        })

                                    if not desc.get('description'):
                                        errors.append({
                                            'field': f'criteria[{i}].descriptors[{j}].description',
                                            'error_type': 'required',
                                            'suggestion': 'Descriptor description is required'
                                        })

        return errors

    def format_validation_errors(self, errors: List[Dict[str, Any]]) -> str:
        """
        Format validation errors for user display.

        Args:
            errors: List of error dictionaries

        Returns:
            str: Human-readable error message
        """
        if not errors:
            return "No errors found"

        lines = ["Validation errors found:"]

        for error in errors:
            field = error.get('field', 'unknown')
            error_type = error.get('error_type', 'validation')
            message = error.get('message') or error.get('suggestion', 'Unknown error')

            lines.append(f"  - {field}: {message}")

            # Add suggestions if available
            if 'suggestion' in error:
                lines.append(f"    Suggestion: {error['suggestion']}")

        return '\n'.join(lines)
