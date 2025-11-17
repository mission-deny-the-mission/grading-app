"""
Unit tests for MarkingSchemeDecoder class.

Tests the deserialization of marking schemes from JSON format for import functionality.
These tests follow TDD principles - they are written before the implementation.
"""

import json
import pytest
from datetime import datetime
from decimal import Decimal
from copy import deepcopy

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from services.scheme_deserializer import MarkingSchemeDecoder
from tests.unit.fixtures.sample_schemes import (
    get_simple_scheme,
    get_medium_scheme,
    get_complex_scheme,
)


@pytest.fixture
def deserializer():
    """Create a MarkingSchemeDecoder instance for testing."""
    return MarkingSchemeDecoder()


@pytest.fixture
def json_schema():
    """Load the JSON schema for validation."""
    import os
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "../../specs/005-marking-schema-as-file/json-schema.json",
    )
    with open(schema_path, "r") as f:
        return json.load(f)


class TestDeserialization:
    """Test basic deserialization functionality."""

    def test_deserialize_valid_json_returns_dict(self, deserializer):
        """
        Test that deserialize() converts JSON string to dict with proper structure.

        Verifies that the deserializer can convert a JSON string representing
        a marking scheme into a dictionary structure that can be used to
        create ORM objects.
        """
        # Arrange
        simple_scheme = get_simple_scheme()
        json_string = json.dumps(simple_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert isinstance(result, dict)
        assert "version" in result
        assert "metadata" in result
        assert "criteria" in result
        assert result["version"] == "1.0.0"

    def test_deserialize_simple_scheme(self, deserializer):
        """
        Test deserialization of a simple scheme fixture.

        Verifies that a simple marking scheme with 2 criteria can be
        deserialized correctly with all fields preserved.
        """
        # Arrange
        simple_scheme = get_simple_scheme()
        json_string = json.dumps(simple_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert result["metadata"]["name"] == "Simple Essay Rubric"
        assert len(result["criteria"]) == 2
        assert result["criteria"][0]["name"] == "Organization"
        assert result["criteria"][1]["name"] == "Grammar and Mechanics"

    def test_deserialize_preserves_all_fields(self, deserializer):
        """
        Test that all metadata and criteria fields are preserved during deserialization.

        Verifies that no data is lost during the deserialization process,
        including optional fields and nested structures.
        """
        # Arrange
        medium_scheme = get_medium_scheme()
        json_string = json.dumps(medium_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        # Check metadata fields
        assert result["metadata"]["name"] == medium_scheme["metadata"]["name"]
        assert result["metadata"]["description"] == medium_scheme["metadata"]["description"]
        assert "exported_at" in result["metadata"]
        assert "exported_by" in result["metadata"]

        # Check criteria preservation
        assert len(result["criteria"]) == len(medium_scheme["criteria"])
        for i, criterion in enumerate(result["criteria"]):
            original = medium_scheme["criteria"][i]
            assert criterion["id"] == original["id"]
            assert criterion["name"] == original["name"]
            assert criterion["description"] == original["description"]
            assert criterion["weight"] == original["weight"]
            assert criterion["point_value"] == original["point_value"]
            assert len(criterion["descriptors"]) == len(original["descriptors"])

    def test_deserialize_handles_optional_fields(self, deserializer):
        """
        Test that deserialization handles optional fields correctly.

        Some fields like description and exported_by are optional per the schema.
        The deserializer should handle both their presence and absence gracefully.
        """
        # Arrange - create minimal scheme without optional fields
        minimal_scheme = {
            "version": "1.0.0",
            "metadata": {
                "name": "Minimal Scheme",
                "exported_at": datetime.now().isoformat(),
            },
            "criteria": [
                {
                    "id": "c1",
                    "name": "Single Criterion",
                    "descriptors": [
                        {
                            "level": "excellent",
                            "description": "Excellent work",
                            "points": 10
                        }
                    ]
                }
            ]
        }
        json_string = json.dumps(minimal_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert "name" in result["metadata"]
        assert "exported_at" in result["metadata"]
        # Optional fields should either be absent or None
        assert result["metadata"].get("description") is None or "description" not in result["metadata"]
        assert result["metadata"].get("exported_by") is None or "exported_by" not in result["metadata"]


class TestSchemaValidation:
    """Test JSON schema validation during deserialization."""

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_valid_scheme_passes_validation(self, deserializer, json_schema):
        """
        Test that a valid scheme passes jsonschema validation.

        The deserializer should validate incoming JSON against the schema
        and accept valid schemes without errors.
        """
        # Arrange
        simple_scheme = get_simple_scheme()
        json_string = json.dumps(simple_scheme)

        # Act - should not raise
        result = deserializer.deserialize(json_string)

        # Assert - manually validate result against schema
        jsonschema.validate(instance=result, schema=json_schema)

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_invalid_schema_fails_validation(self, deserializer):
        """
        Test that schemes missing required fields are rejected.

        The deserializer should raise an appropriate exception when
        required fields are missing from the input JSON.
        """
        # Arrange - scheme missing required 'version' field
        invalid_scheme = {
            "metadata": {
                "name": "Invalid Scheme",
                "exported_at": datetime.now().isoformat(),
            },
            "criteria": []
        }
        json_string = json.dumps(invalid_scheme)

        # Act & Assert
        with pytest.raises((ValueError, jsonschema.ValidationError)) as exc_info:
            deserializer.deserialize(json_string)

        # Should mention the missing field or validation error
        assert "version" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    def test_malformed_json_fails_validation(self, deserializer):
        """
        Test that invalid JSON syntax is detected and rejected.

        The deserializer should raise a clear error when the input
        string is not valid JSON.
        """
        # Arrange - malformed JSON
        malformed_json = '{"version": "1.0.0", "metadata": {invalid json here}'

        # Act & Assert
        with pytest.raises((ValueError, json.JSONDecodeError)) as exc_info:
            deserializer.deserialize(malformed_json)

        # Should indicate JSON parsing failure
        assert "json" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_invalid_enum_values_rejected(self, deserializer):
        """
        Test that descriptor levels must be in the allowed enum.

        Valid levels are: excellent, good, satisfactory, poor, fail.
        Any other value should be rejected.
        """
        # Arrange - scheme with invalid descriptor level
        invalid_scheme = get_simple_scheme()
        invalid_scheme["criteria"][0]["descriptors"][0]["level"] = "super_amazing"  # Invalid level
        json_string = json.dumps(invalid_scheme)

        # Act & Assert
        with pytest.raises((ValueError, jsonschema.ValidationError)) as exc_info:
            deserializer.deserialize(json_string)

        # Should mention enum or level validation
        error_msg = str(exc_info.value).lower()
        assert "level" in error_msg or "enum" in error_msg or "super_amazing" in error_msg


class TestErrorCollection:
    """Test error collection and reporting functionality."""

    def test_collect_all_validation_errors(self, deserializer):
        """
        Test that multiple validation errors are collected instead of failing on first error.

        When multiple issues exist, the deserializer should collect all errors
        and report them together, helping users fix all issues at once.
        """
        # Arrange - scheme with multiple issues
        invalid_scheme = {
            "version": "invalid.version.format",  # Invalid version format
            "metadata": {
                "name": "",  # Empty name (invalid per minLength: 1)
                "exported_at": "not-a-datetime",  # Invalid datetime format
            },
            "criteria": []  # Empty criteria array (invalid per minItems: 1)
        }
        json_string = json.dumps(invalid_scheme)

        # Act
        try:
            deserializer.deserialize(json_string)
            # If no exception raised, check if errors are returned in result
            pytest.fail("Expected validation error but none was raised")
        except (ValueError, Exception) as e:
            # Assert - error message should mention multiple issues
            error_msg = str(e).lower()
            # Should collect multiple errors (at least criteria and possibly others)
            assert "criteria" in error_msg or "multiple" in error_msg or len(str(e)) > 50

    def test_error_includes_field_path(self, deserializer):
        """
        Test that error messages include the field path where validation failed.

        Error messages should clearly indicate which field failed validation,
        e.g., "criteria[0].level" or "metadata.name".
        """
        # Arrange - scheme with specific field error
        invalid_scheme = get_simple_scheme()
        invalid_scheme["criteria"][0]["descriptors"][0]["level"] = "invalid_level"
        json_string = json.dumps(invalid_scheme)

        # Act & Assert
        try:
            deserializer.deserialize(json_string)
            pytest.fail("Expected validation error but none was raised")
        except (ValueError, Exception) as e:
            error_msg = str(e)
            # Should include path-like information
            assert "level" in error_msg or "descriptor" in error_msg or "criteria" in error_msg

    def test_error_includes_suggestions(self, deserializer):
        """
        Test that error messages include helpful suggestions for fixing errors.

        When validation fails, the deserializer should provide actionable
        suggestions to help users correct the issue.
        """
        # Arrange - scheme with invalid enum value
        invalid_scheme = get_simple_scheme()
        invalid_scheme["criteria"][0]["descriptors"][0]["level"] = "outstanding"
        json_string = json.dumps(invalid_scheme)

        # Act & Assert
        try:
            deserializer.deserialize(json_string)
            pytest.fail("Expected validation error but none was raised")
        except (ValueError, Exception) as e:
            error_msg = str(e).lower()
            # Should suggest valid values or provide helpful context
            # Check for either the invalid value mentioned or suggestion keywords
            assert ("outstanding" in error_msg or
                    "valid" in error_msg or
                    "should" in error_msg or
                    "must be" in error_msg)


class TestDataIntegrity:
    """Test data integrity and structure validation."""

    def test_deserialize_and_check_criteria_count(self, deserializer):
        """
        Test that the correct number of criteria are deserialized.

        Verifies that all criteria from the input are preserved
        in the output without duplication or loss.
        """
        # Arrange
        complex_scheme = get_complex_scheme()
        expected_count = len(complex_scheme["criteria"])
        json_string = json.dumps(complex_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert len(result["criteria"]) == expected_count
        assert len(result["criteria"]) == 6  # Complex scheme has 6 criteria

    def test_deserialize_preserves_numeric_values(self, deserializer):
        """
        Test that Decimal/float values are preserved with correct precision.

        Numeric values like weights and point values should maintain
        their precision during deserialization.
        """
        # Arrange
        medium_scheme = get_medium_scheme()
        json_string = json.dumps(medium_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert - check specific numeric values
        first_criterion = result["criteria"][0]
        assert first_criterion["weight"] == 0.25
        assert first_criterion["point_value"] == 25

        # Check descriptor points
        first_descriptor = first_criterion["descriptors"][0]
        assert first_descriptor["points"] == 25

        # Verify numeric types are preserved
        assert isinstance(first_criterion["weight"], (int, float, Decimal))
        assert isinstance(first_criterion["point_value"], (int, float, Decimal))

    def test_deserialize_handles_large_scheme(self, deserializer):
        """
        Test that schemes with 50+ criteria are handled correctly.

        Verifies that the deserializer can handle large marking schemes
        without performance issues or data loss.
        """
        # Arrange - create a large scheme with 50+ criteria
        large_scheme = get_complex_scheme()

        # Duplicate criteria to reach 50+
        base_criterion = large_scheme["criteria"][0].copy()
        large_criteria = []
        for i in range(52):
            criterion = deepcopy(base_criterion)
            criterion["id"] = f"c{i+1}-large"
            criterion["name"] = f"Criterion {i+1}"
            large_criteria.append(criterion)

        large_scheme["criteria"] = large_criteria
        json_string = json.dumps(large_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert len(result["criteria"]) == 52
        # Check first and last criteria are correct
        assert result["criteria"][0]["id"] == "c1-large"
        assert result["criteria"][51]["id"] == "c52-large"
        # Verify all criteria have required fields
        for criterion in result["criteria"]:
            assert "id" in criterion
            assert "name" in criterion
            assert "descriptors" in criterion


class TestRoundTrip:
    """Test round-trip serialization and deserialization."""

    def test_export_then_import_identical(self, deserializer):
        """
        Test that export → serialize → import → verify produces same data.

        A marking scheme should be able to be exported to JSON and then
        imported back without any data loss or transformation errors.
        """
        # Arrange
        original_scheme = get_medium_scheme()

        # Act - Simulate export and re-import
        # First convert to JSON string (export)
        json_string = json.dumps(original_scheme)
        # Then deserialize back (import)
        imported_scheme = deserializer.deserialize(json_string)

        # Assert - imported should match original
        assert imported_scheme["version"] == original_scheme["version"]
        assert imported_scheme["metadata"]["name"] == original_scheme["metadata"]["name"]
        assert len(imported_scheme["criteria"]) == len(original_scheme["criteria"])

        # Deep check on first criterion
        orig_criterion = original_scheme["criteria"][0]
        import_criterion = imported_scheme["criteria"][0]
        assert import_criterion["id"] == orig_criterion["id"]
        assert import_criterion["name"] == orig_criterion["name"]
        assert import_criterion["weight"] == orig_criterion["weight"]
        assert import_criterion["point_value"] == orig_criterion["point_value"]

    def test_import_creates_valid_orm_object(self, deserializer):
        """
        Test that deserializer returns data structure ready for ORM object creation.

        The output of deserialization should be in a format that can be
        directly used to create database model instances without further
        transformation.
        """
        # Arrange
        simple_scheme = get_simple_scheme()
        json_string = json.dumps(simple_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert - check structure is ORM-ready
        # Should have top-level fields
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "criteria" in result

        # Metadata should be dict-like
        metadata = result["metadata"]
        assert isinstance(metadata, dict)
        assert "name" in metadata

        # Criteria should be list of dicts
        criteria = result["criteria"]
        assert isinstance(criteria, list)
        for criterion in criteria:
            assert isinstance(criterion, dict)
            assert "id" in criterion
            assert "name" in criterion
            assert "descriptors" in criterion
            assert isinstance(criterion["descriptors"], list)

            # Each descriptor should be dict-like
            for descriptor in criterion["descriptors"]:
                assert isinstance(descriptor, dict)
                assert "level" in descriptor
                assert "description" in descriptor


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_deserialize_with_unicode_characters(self, deserializer):
        """
        Test that Unicode characters in descriptions are handled correctly.

        Marking schemes may contain non-ASCII characters in various languages,
        and these should be preserved during deserialization.
        """
        # Arrange
        unicode_scheme = get_simple_scheme()
        unicode_scheme["metadata"]["description"] = "Évaluation des essais français avec des caractères spéciaux: €, ñ, 中文"
        unicode_scheme["criteria"][0]["description"] = "Organisation et structure du texte français"
        json_string = json.dumps(unicode_scheme, ensure_ascii=False)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert "français" in result["metadata"]["description"]
        assert "€" in result["metadata"]["description"]
        assert "中文" in result["metadata"]["description"]
        assert "français" in result["criteria"][0]["description"]

    def test_deserialize_with_zero_weight_criteria(self, deserializer):
        """
        Test that criteria with zero weight are handled correctly.

        While unusual, zero-weight criteria should be valid per the schema
        (minimum: 0) and may be used for informational criteria.
        """
        # Arrange
        scheme = get_simple_scheme()
        scheme["criteria"][0]["weight"] = 0
        json_string = json.dumps(scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        assert result["criteria"][0]["weight"] == 0

    def test_deserialize_preserves_criteria_order(self, deserializer):
        """
        Test that the order of criteria is preserved during deserialization.

        Display order is important for marking schemes, so the deserializer
        should maintain the original sequence from the JSON.
        """
        # Arrange
        complex_scheme = get_complex_scheme()
        original_names = [c["name"] for c in complex_scheme["criteria"]]
        json_string = json.dumps(complex_scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        deserialized_names = [c["name"] for c in result["criteria"]]
        assert deserialized_names == original_names

    def test_deserialize_with_float_precision(self, deserializer):
        """
        Test that floating-point precision is maintained for weights and points.

        Weights like 0.333333 should be preserved with sufficient precision
        to avoid rounding errors in calculations.
        """
        # Arrange
        scheme = get_simple_scheme()
        # Set a weight with high precision
        scheme["criteria"][0]["weight"] = 0.333333333
        scheme["criteria"][0]["descriptors"][0]["points"] = 18.75
        json_string = json.dumps(scheme)

        # Act
        result = deserializer.deserialize(json_string)

        # Assert
        # Should preserve reasonable precision (may not be exact due to JSON float limitations)
        assert abs(result["criteria"][0]["weight"] - 0.333333333) < 0.0001
        assert result["criteria"][0]["descriptors"][0]["points"] == 18.75

    def test_deserialize_empty_descriptor_array_fails(self, deserializer):
        """
        Test that criteria without descriptors are rejected.

        Per the schema, each criterion must have at least one descriptor (minItems: 1).
        """
        # Arrange
        invalid_scheme = get_simple_scheme()
        invalid_scheme["criteria"][0]["descriptors"] = []  # Empty descriptors
        json_string = json.dumps(invalid_scheme)

        # Act & Assert
        with pytest.raises((ValueError, Exception)) as exc_info:
            deserializer.deserialize(json_string)

        error_msg = str(exc_info.value).lower()
        assert "descriptor" in error_msg or "empty" in error_msg or "required" in error_msg
