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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(medium_scheme)

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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(complex_scheme)

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
        result = serializer.to_dict(medium_scheme)

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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(medium_scheme)

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
        result = serializer.to_dict(scheme)

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
        result = serializer.to_dict(scheme)

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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(simple_scheme)

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
        result = serializer.to_dict(medium_scheme)

        # Assert
        jsonschema.validate(instance=result, schema=json_schema)

    def test_complex_scheme_validates_against_schema(self, serializer, json_schema):
        """
        Test that a complex scheme with many criteria validates against the schema.
        """
        # Arrange
        complex_scheme = get_complex_scheme()

        # Act
        result = serializer.to_dict(complex_scheme)

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
        result = serializer.to_dict(minimal_scheme)

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
        result = serializer.to_dict(scheme)

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
        result = serializer.to_dict(complex_scheme)

        # Assert
        serialized_names = [c["name"] for c in result["criteria"]]
        assert serialized_names == original_names


class TestEncoderEdgeCases:
    """Test edge cases for the MarkingSchemeEncoder."""

    def test_encoder_handles_unknown_type(self):
        """Test that encoder raises TypeError for unknown types."""
        encoder = MarkingSchemeEncoder()

        # Create a custom class that json.JSONEncoder doesn't know about
        class CustomObject:
            pass

        with pytest.raises(TypeError):
            encoder.default(CustomObject())

    def test_encoder_handles_decimal(self):
        """Test that encoder converts Decimal to float."""
        encoder = MarkingSchemeEncoder()
        result = encoder.default(Decimal("10.5"))
        assert result == 10.5
        assert isinstance(result, float)

    def test_encoder_handles_datetime(self):
        """Test that encoder converts datetime to ISO string."""
        encoder = MarkingSchemeEncoder()
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = encoder.default(dt)
        assert "2024-01-15" in result
        assert isinstance(result, str)

    def test_encoder_handles_uuid(self):
        """Test that encoder converts UUID to string."""
        encoder = MarkingSchemeEncoder()
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        result = encoder.default(test_uuid)
        assert result == "12345678-1234-5678-1234-567812345678"
        assert isinstance(result, str)


class TestNoneAndEmptyInputs:
    """Test handling of None and empty inputs."""

    def test_to_dict_returns_none_for_none_input(self, serializer):
        """Test that to_dict returns None when passed None."""
        result = serializer.to_dict(None)
        assert result is None

    def test_to_dict_handles_empty_criteria_list(self, serializer):
        """Test that to_dict handles schemes with empty criteria."""
        scheme = {
            "version": "1.0.0",
            "metadata": {"name": "Empty Scheme"},
            "criteria": []
        }
        result = serializer.to_dict(scheme)
        assert result["criteria"] == []


class TestDictToDictConversion:
    """Test _dict_to_dict method for various input formats."""

    def test_dict_to_dict_adds_exported_at_to_existing_format(self, serializer):
        """Test that exported_at is added to existing export format if missing."""
        scheme = {
            "version": "1.0.0",
            "metadata": {"name": "Test Scheme"},  # No exported_at
            "criteria": []
        }
        result = serializer.to_dict(scheme)
        assert "exported_at" in result["metadata"]

    def test_dict_to_dict_preserves_existing_exported_at(self, serializer):
        """Test that existing exported_at is preserved."""
        scheme = {
            "version": "1.0.0",
            "metadata": {"name": "Test Scheme", "exported_at": "2024-01-01T00:00:00"},
            "criteria": []
        }
        result = serializer.to_dict(scheme)
        assert result["metadata"]["exported_at"] == "2024-01-01T00:00:00"

    def test_dict_to_dict_converts_internal_format(self, serializer):
        """Test conversion of internal format without version/metadata/criteria structure."""
        scheme = {
            "name": "Internal Format Scheme",
            "criteria": [
                {"id": "1", "name": "Criterion 1", "point_value": 10}
            ]
        }
        result = serializer.to_dict(scheme)
        assert result["version"] == "1.0.0"
        assert result["metadata"]["name"] == "Internal Format Scheme"
        assert "exported_at" in result["metadata"]

    def test_dict_to_dict_handles_metadata_in_internal_format(self, serializer):
        """Test handling metadata in internal format."""
        scheme = {
            "metadata": {"name": "From Metadata"},
            "criteria": []
        }
        result = serializer.to_dict(scheme)
        assert result["metadata"]["name"] == "From Metadata"


class TestORMObjectSerialization:
    """Test serialization of ORM-like objects."""

    def test_orm_to_dict_with_owner_id(self, serializer):
        """Test that owner_id is added as exported_by."""
        class MockScheme:
            name = "ORM Scheme"
            description = "A test description"
            owner_id = "user-123"
            criteria = None
            questions = None

        scheme = MockScheme()
        result = serializer.to_dict(scheme)
        assert result["metadata"]["exported_by"] == "user-123"
        assert result["metadata"]["description"] == "A test description"

    def test_orm_to_dict_with_criteria(self, serializer):
        """Test serialization of ORM object with criteria."""
        class MockCriterion:
            id = "crit-1"
            name = "Criterion 1"
            description = "Test criterion"
            weight = Decimal("0.5")
            point_value = Decimal("10.0")
            descriptors = None

        class MockScheme:
            name = "ORM Scheme"
            description = None
            owner_id = None
            criteria = [MockCriterion()]
            questions = None

        scheme = MockScheme()
        result = serializer.to_dict(scheme)
        assert len(result["criteria"]) == 1
        assert result["criteria"][0]["name"] == "Criterion 1"
        assert result["criteria"][0]["weight"] == 0.5
        assert result["criteria"][0]["point_value"] == 10.0

    def test_orm_to_dict_with_questions_containing_criteria(self, serializer):
        """Test serialization of ORM object with questions containing criteria."""
        class MockCriterion:
            id = "crit-1"
            name = "Question Criterion"
            description = None
            weight = None
            max_points = Decimal("20.0")
            descriptors = None

        class MockQuestion:
            criteria = [MockCriterion()]

        class MockScheme:
            name = "ORM Scheme"
            description = None
            owner_id = None
            criteria = None
            questions = [MockQuestion()]

        scheme = MockScheme()
        result = serializer.to_dict(scheme)
        assert len(result["criteria"]) == 1
        assert result["criteria"][0]["point_value"] == 20.0


class TestEncodeCriteria:
    """Test encode_criteria method."""

    def test_encode_criteria_returns_empty_for_none(self, serializer):
        """Test that encode_criteria returns empty list for None input."""
        result = serializer.encode_criteria(None)
        assert result == []

    def test_encode_criteria_returns_empty_for_empty_list(self, serializer):
        """Test that encode_criteria returns empty list for empty input."""
        result = serializer.encode_criteria([])
        assert result == []

    def test_encode_criteria_with_levels_attribute(self, serializer):
        """Test encoding criterion with levels instead of descriptors."""
        class MockLevel:
            level = "excellent"
            description = "Outstanding work"
            points = Decimal("10.0")

        class MockCriterion:
            id = "crit-1"
            name = "Criterion with Levels"
            description = "Test"
            weight = None
            point_value = Decimal("10.0")
            descriptors = None
            levels = [MockLevel()]

        result = serializer.encode_criteria([MockCriterion()])
        assert len(result) == 1
        assert len(result[0]["descriptors"]) == 1
        assert result[0]["descriptors"][0]["level"] == "excellent"

    def test_encode_criteria_generates_default_descriptor(self, serializer):
        """Test that criteria without descriptors get a default one."""
        class MockCriterion:
            id = "crit-1"
            name = "No Descriptors"
            description = None
            weight = None
            point_value = Decimal("10.0")

        result = serializer.encode_criteria([MockCriterion()])
        assert len(result) == 1
        assert len(result[0]["descriptors"]) == 1
        assert result[0]["descriptors"][0]["level"] == "excellent"


class TestEncodeDescriptors:
    """Test encode_descriptors method."""

    def test_encode_descriptors_returns_empty_for_none(self, serializer):
        """Test that encode_descriptors returns empty list for None input."""
        result = serializer.encode_descriptors(None)
        assert result == []

    def test_encode_descriptors_returns_empty_for_empty_list(self, serializer):
        """Test that encode_descriptors returns empty list for empty input."""
        result = serializer.encode_descriptors([])
        assert result == []

    def test_encode_descriptors_with_object_attributes(self, serializer):
        """Test encoding descriptors from objects with attributes."""
        class MockDescriptor:
            level = "good"
            description = "Good performance"
            points = Decimal("8.0")

        result = serializer.encode_descriptors([MockDescriptor()])
        assert len(result) == 1
        assert result[0]["level"] == "good"
        assert result[0]["description"] == "Good performance"
        assert result[0]["points"] == 8.0

    def test_encode_descriptors_from_dict(self, serializer):
        """Test encoding descriptors from dictionaries."""
        descriptors = [
            {"level": "excellent", "description": "Outstanding", "points": 10.0},
            {"level": "good", "description": "Good work", "points": 8.0},
        ]
        result = serializer.encode_descriptors(descriptors)
        assert len(result) == 2
        assert result[0]["level"] == "excellent"
        assert result[1]["level"] == "good"

    def test_encode_descriptors_skips_without_level(self, serializer):
        """Test that descriptors without level are skipped."""
        class MockDescriptorNoLevel:
            description = "No level descriptor"
            points = Decimal("5.0")

        result = serializer.encode_descriptors([MockDescriptorNoLevel()])
        assert result == []

    def test_encode_descriptors_generates_description_if_missing(self, serializer):
        """Test that missing description is generated from level."""
        class MockDescriptor:
            level = "excellent"
            points = Decimal("10.0")

        result = serializer.encode_descriptors([MockDescriptor()])
        assert len(result) == 1
        assert result[0]["description"] == "Excellent performance"

    def test_encode_descriptors_handles_none_points(self, serializer):
        """Test that None points are handled correctly."""
        class MockDescriptor:
            level = "good"
            description = "Good work"
            points = None

        result = serializer.encode_descriptors([MockDescriptor()])
        assert len(result) == 1
        assert "points" not in result[0]
