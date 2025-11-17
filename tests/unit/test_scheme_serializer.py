"""
Unit tests for MarkingSchemeSerializer class.

Tests the serialization of marking schemes to JSON format for export functionality.
These tests follow TDD principles - they are written before the implementation.
"""

import json
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import UUID

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from services.scheme_serializer import MarkingSchemeSerializer, MarkingSchemeEncoder
from tests.unit.fixtures.sample_schemes import (
    get_simple_scheme,
    get_medium_scheme,
    get_complex_scheme,
)


@pytest.fixture
def serializer():
    """Create a MarkingSchemeSerializer instance for testing."""
    return MarkingSchemeSerializer()


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


class TestBasicSerialization:
    """Test basic serialization functionality."""

    def test_serialize_simple_scheme_returns_dict(self, serializer):
        """
        Test that serialize() returns a dictionary for a simple scheme.

        Verifies that the serializer can convert a simple marking scheme
        with basic criteria into a dictionary structure.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        assert isinstance(result, dict)
        assert "version" in result
        assert "metadata" in result
        assert "criteria" in result

    def test_serialize_includes_version(self, serializer):
        """
        Test that serialized output includes the version field.

        The version field is required for backward compatibility and
        should follow semantic versioning (e.g., "1.0.0").
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        assert "version" in result
        assert result["version"] == "1.0.0"
        # Verify semantic versioning pattern
        assert isinstance(result["version"], str)
        parts = result["version"].split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestMetadataSerialization:
    """Test metadata field serialization."""

    def test_serialize_metadata_fields(self, serializer):
        """
        Test that all required metadata fields are serialized correctly.

        Metadata should include name, description, exported_at, and
        exported_by fields as per the JSON schema.
        """
        # Arrange
        medium_scheme = get_medium_scheme()

        # Act
        result = serializer.serialize(medium_scheme)

        # Assert
        assert "metadata" in result
        metadata = result["metadata"]
        assert "name" in metadata
        assert "description" in metadata
        assert "exported_at" in metadata
        assert metadata["name"] == medium_scheme["metadata"]["name"]
        assert metadata["description"] == medium_scheme["metadata"]["description"]

    def test_datetime_formatting_to_iso(self, serializer):
        """
        Test that datetime fields are formatted to ISO 8601 format.

        The exported_at field should be a valid ISO 8601 timestamp string
        that can be parsed back to a datetime object.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        exported_at = result["metadata"]["exported_at"]
        assert isinstance(exported_at, str)
        # Verify it's a valid ISO format datetime
        parsed_datetime = datetime.fromisoformat(exported_at.replace("Z", "+00:00"))
        assert isinstance(parsed_datetime, datetime)


class TestCriteriaSerialization:
    """Test criteria serialization with all fields."""

    def test_serialize_criteria_with_all_fields(self, serializer):
        """
        Test that criteria are serialized with all required and optional fields.

        Criteria should include id, name, description (optional), weight,
        point_value, and descriptors arrays.
        """
        # Arrange
        complex_scheme = get_complex_scheme()

        # Act
        result = serializer.serialize(complex_scheme)

        # Assert
        assert "criteria" in result
        assert isinstance(result["criteria"], list)
        assert len(result["criteria"]) == len(complex_scheme["criteria"])

        # Check first criterion has all expected fields
        first_criterion = result["criteria"][0]
        assert "id" in first_criterion
        assert "name" in first_criterion
        assert "weight" in first_criterion
        assert "point_value" in first_criterion
        assert "descriptors" in first_criterion

    def test_criteria_weights_are_numeric(self, serializer):
        """
        Test that criteria weights are properly serialized as numbers.

        Weights should be numeric values between 0 and 1, representing
        the relative importance of each criterion.
        """
        # Arrange
        medium_scheme = get_medium_scheme()

        # Act
        result = serializer.serialize(medium_scheme)

        # Assert
        for criterion in result["criteria"]:
            assert "weight" in criterion
            weight = criterion["weight"]
            assert isinstance(weight, (int, float, Decimal))
            assert 0 <= weight <= 1

    def test_criteria_point_values_are_numeric(self, serializer):
        """
        Test that point values are properly serialized as numbers.

        Point values should be non-negative numbers representing the
        total points available for each criterion.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        for criterion in result["criteria"]:
            assert "point_value" in criterion
            point_value = criterion["point_value"]
            assert isinstance(point_value, (int, float, Decimal))
            assert point_value >= 0


class TestDescriptorSerialization:
    """Test descriptor array serialization."""

    def test_serialize_descriptors_array(self, serializer):
        """
        Test that descriptors are serialized as arrays with proper structure.

        Each descriptor should include level, description, and points fields.
        Descriptors represent different performance levels for a criterion.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        first_criterion = result["criteria"][0]
        assert "descriptors" in first_criterion
        descriptors = first_criterion["descriptors"]
        assert isinstance(descriptors, list)
        assert len(descriptors) > 0

        # Check descriptor structure
        for descriptor in descriptors:
            assert "level" in descriptor
            assert "description" in descriptor
            assert "points" in descriptor

    def test_descriptor_levels_are_valid(self, serializer):
        """
        Test that descriptor levels match the schema enum values.

        Valid levels are: excellent, good, satisfactory, poor, fail.
        """
        # Arrange
        medium_scheme = get_medium_scheme()
        valid_levels = {"excellent", "good", "satisfactory", "poor", "fail"}

        # Act
        result = serializer.serialize(medium_scheme)

        # Assert
        for criterion in result["criteria"]:
            for descriptor in criterion["descriptors"]:
                assert descriptor["level"] in valid_levels


class TestNullAndEmptyHandling:
    """Test handling of null and empty values."""

    def test_handle_missing_description_in_metadata(self, serializer):
        """
        Test that missing optional description field is handled gracefully.

        The description field in metadata is optional according to the schema.
        """
        # Arrange
        scheme = get_simple_scheme()
        # Remove description to test optional field handling
        if "description" in scheme["metadata"]:
            original_desc = scheme["metadata"]["description"]
            scheme["metadata"]["description"] = None

        # Act
        result = serializer.serialize(scheme)

        # Assert
        assert "metadata" in result
        # Either description is None or not present (both valid)
        assert result["metadata"].get("description") is None or "description" not in result["metadata"]

    def test_handle_missing_criterion_description(self, serializer):
        """
        Test that missing optional description in criteria is handled.

        Criterion descriptions are optional per the JSON schema.
        """
        # Arrange
        scheme = get_complex_scheme()
        # Find a criterion without description or set one to None
        for criterion in scheme["criteria"]:
            if "description" not in criterion:
                break

        # Act
        result = serializer.serialize(scheme)

        # Assert
        assert "criteria" in result
        assert len(result["criteria"]) > 0


class TestUUIDConversion:
    """Test UUID to string conversion."""

    def test_uuid_fields_converted_to_strings(self, serializer):
        """
        Test that UUID fields are converted to string format.

        Criterion IDs may be UUIDs in the database but should be
        serialized as strings in JSON output.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        for criterion in result["criteria"]:
            assert "id" in criterion
            criterion_id = criterion["id"]
            assert isinstance(criterion_id, str)
            # Verify it's a valid identifier format
            assert len(criterion_id) > 0


class TestJSONFormatting:
    """Test JSON string formatting and pretty-printing."""

    def test_to_json_string_returns_valid_json(self, serializer):
        """
        Test that to_json_string() produces valid JSON.

        The output should be parseable as JSON and match the original structure.
        """
        # Arrange
        medium_scheme = get_medium_scheme()

        # Act
        json_string = serializer.to_json_string(medium_scheme, pretty=False)

        # Assert
        assert isinstance(json_string, str)
        # Verify it's valid JSON by parsing it
        parsed = json.loads(json_string)
        assert isinstance(parsed, dict)
        assert "version" in parsed
        assert "metadata" in parsed
        assert "criteria" in parsed

    def test_pretty_printing_with_indentation(self, serializer):
        """
        Test that pretty=True produces formatted JSON with indentation.

        Pretty-printed JSON should have newlines and proper indentation
        for human readability.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        pretty_json = serializer.to_json_string(simple_scheme, pretty=True)
        ugly_json = serializer.to_json_string(simple_scheme, pretty=False)

        # Assert
        assert isinstance(pretty_json, str)
        assert isinstance(ugly_json, str)
        # Pretty version should have more characters (whitespace)
        assert len(pretty_json) > len(ugly_json)
        # Pretty version should have newlines
        assert "\n" in pretty_json
        # Verify both parse to same structure
        assert json.loads(pretty_json) == json.loads(ugly_json)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestSchemaValidation:
    """Test that serialized output validates against the JSON schema."""

    def test_simple_scheme_validates_against_schema(self, serializer, json_schema):
        """
        Test that a simple scheme validates against the JSON schema.

        The serialized output must conform to the schema defined in
        specs/005-marking-schema-as-file/json-schema.json.
        """
        # Arrange
        simple_scheme = get_simple_scheme()

        # Act
        result = serializer.serialize(simple_scheme)

        # Assert
        # Should not raise validation error
        jsonschema.validate(instance=result, schema=json_schema)

    def test_medium_scheme_validates_against_schema(self, serializer, json_schema):
        """
        Test that a medium complexity scheme validates against the schema.
        """
        # Arrange
        medium_scheme = get_medium_scheme()

        # Act
        result = serializer.serialize(medium_scheme)

        # Assert
        jsonschema.validate(instance=result, schema=json_schema)

    def test_complex_scheme_validates_against_schema(self, serializer, json_schema):
        """
        Test that a complex scheme with many criteria validates against the schema.
        """
        # Arrange
        complex_scheme = get_complex_scheme()

        # Act
        result = serializer.serialize(complex_scheme)

        # Assert
        jsonschema.validate(instance=result, schema=json_schema)


class TestCustomJSONEncoder:
    """Test the custom JSON encoder functionality."""

    def test_encoder_handles_decimal_types(self):
        """
        Test that MarkingSchemeEncoder properly handles Decimal types.

        Decimal values (used for precise point calculations) should be
        converted to floats for JSON serialization.
        """
        # Arrange
        encoder = MarkingSchemeEncoder()
        test_data = {"value": Decimal("25.50")}

        # Act
        json_string = json.dumps(test_data, cls=MarkingSchemeEncoder)
        result = json.loads(json_string)

        # Assert
        assert isinstance(result["value"], (int, float))
        assert result["value"] == 25.50

    def test_encoder_handles_datetime_types(self):
        """
        Test that MarkingSchemeEncoder properly handles datetime types.

        Datetime objects should be converted to ISO 8601 format strings.
        """
        # Arrange
        encoder = MarkingSchemeEncoder()
        test_datetime = datetime(2025, 11, 17, 12, 30, 45)
        test_data = {"timestamp": test_datetime}

        # Act
        json_string = json.dumps(test_data, cls=MarkingSchemeEncoder)
        result = json.loads(json_string)

        # Assert
        assert isinstance(result["timestamp"], str)
        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(result["timestamp"])
        assert isinstance(parsed, datetime)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_serialize_minimum_valid_scheme(self, serializer):
        """
        Test serialization of a minimal valid scheme with one criterion.

        The schema requires at least one criterion, so this tests the
        minimum valid configuration.
        """
        # Arrange
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

        # Act
        result = serializer.serialize(minimal_scheme)

        # Assert
        assert "version" in result
        assert "metadata" in result
        assert "criteria" in result
        assert len(result["criteria"]) == 1

    def test_serialize_scheme_with_zero_point_value(self, serializer):
        """
        Test that criteria with 0 points are handled correctly.

        While unusual, 0-point criteria should be valid per the schema
        (minimum: 0 in JSON schema).
        """
        # Arrange
        scheme = get_simple_scheme()
        # Set a point value to 0
        scheme["criteria"][0]["point_value"] = 0

        # Act
        result = serializer.serialize(scheme)

        # Assert
        assert result["criteria"][0]["point_value"] == 0

    def test_serialize_preserves_criteria_order(self, serializer):
        """
        Test that the order of criteria is preserved during serialization.

        Display order is important for marking schemes, so the serializer
        should maintain the original sequence.
        """
        # Arrange
        complex_scheme = get_complex_scheme()
        original_names = [c["name"] for c in complex_scheme["criteria"]]

        # Act
        result = serializer.serialize(complex_scheme)

        # Assert
        serialized_names = [c["name"] for c in result["criteria"]]
        assert serialized_names == original_names
