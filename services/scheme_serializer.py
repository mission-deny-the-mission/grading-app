"""
Marking Scheme Serialization Service

Handles conversion of MarkingScheme objects to JSON for export.
Implements serialization for User Story 1 (Export Marking Schemes).
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from uuid import UUID


class MarkingSchemeEncoder(json.JSONEncoder):
    """Custom JSON encoder for MarkingScheme serialization."""

    def default(self, obj):
        """
        Handle non-standard JSON types.

        Supports:
        - Decimal (point values) → float
        - datetime → ISO format string
        - UUID → string
        """
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def json_default(obj):
    """
    Helper function for custom JSON encoding.

    Handles non-standard types for json.dumps() default parameter.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class MarkingSchemeSerializer:
    """Serializes MarkingScheme objects to JSON format."""

    # Schema version for backward compatibility
    SCHEMA_VERSION = "1.0.0"

    def serialize(self, scheme) -> Dict[str, Any]:
        """
        Serialize a MarkingScheme to dictionary/JSON.

        Args:
            scheme: MarkingScheme ORM object

        Returns:
            dict: JSON-serializable MarkingScheme representation
        """
        return self.to_dict(scheme)

    def to_dict(self, scheme) -> Dict[str, Any]:
        """
        Convert MarkingScheme to dictionary.

        Includes all fields per JSON schema definition:
        - metadata (name, description, export_date, version)
        - criteria (with descriptors)

        Args:
            scheme: MarkingScheme ORM object or dict representation

        Returns:
            dict: Dictionary representation
        """
        if not scheme:
            return None

        # Handle both ORM objects and dictionaries
        if isinstance(scheme, dict):
            # Already a dictionary (from test fixtures)
            return self._dict_to_dict(scheme)
        else:
            # ORM object
            return self._orm_to_dict(scheme)

    def _dict_to_dict(self, scheme_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert scheme dictionary to exported format.

        Used when input is already a dictionary (test fixtures).
        """
        # If it already has the export format, return it
        if "version" in scheme_dict and "metadata" in scheme_dict and "criteria" in scheme_dict:
            # Ensure exported_at is present even in existing export format
            if "exported_at" not in scheme_dict["metadata"]:
                scheme_dict["metadata"]["exported_at"] = datetime.utcnow().isoformat()
            return scheme_dict

        # Otherwise, convert from internal format
        metadata = scheme_dict.get("metadata", {}).copy() if "metadata" in scheme_dict else {}

        # Ensure required metadata fields
        if "name" not in metadata and "name" in scheme_dict:
            metadata["name"] = scheme_dict["name"]
        if "exported_at" not in metadata:
            metadata["exported_at"] = datetime.utcnow().isoformat()

        # Handle criteria
        criteria = scheme_dict.get("criteria", [])
        if not criteria and "criteria" in scheme_dict:
            criteria = scheme_dict["criteria"]

        return {
            "version": scheme_dict.get("version", self.SCHEMA_VERSION),
            "metadata": metadata,
            "criteria": criteria
        }

    def _orm_to_dict(self, scheme) -> Dict[str, Any]:
        """
        Convert MarkingScheme ORM object to dictionary.

        Used when input is an actual ORM object.
        """
        # Build metadata section
        metadata = {
            "name": scheme.name if hasattr(scheme, 'name') else "Unnamed Scheme",
            "exported_at": datetime.utcnow().isoformat(),
        }

        # Add optional description if present
        if hasattr(scheme, 'description') and scheme.description:
            metadata["description"] = scheme.description

        # Add exported_by if user information is available
        if hasattr(scheme, 'owner_id') and scheme.owner_id:
            metadata["exported_by"] = scheme.owner_id

        # Build criteria section
        # Note: The actual scheme structure may vary; this assumes standard format
        criteria = []
        if hasattr(scheme, 'criteria') and scheme.criteria:
            criteria = self.encode_criteria(scheme.criteria)
        elif hasattr(scheme, 'questions') and scheme.questions:
            # Alternative structure: scheme has questions with criteria
            for question in scheme.questions:
                if hasattr(question, 'criteria'):
                    criteria.extend(self.encode_criteria(question.criteria))

        # Return full structure per JSON schema
        return {
            "version": self.SCHEMA_VERSION,
            "metadata": metadata,
            "criteria": criteria if criteria else []
        }

    def encode_criteria(self, criteria_list) -> list:
        """
        Encode criteria to JSON format.

        Args:
            criteria_list: List of SchemeCriterion objects

        Returns:
            list: Serialized criteria
        """
        if not criteria_list:
            return []

        encoded = []
        for criterion in criteria_list:
            criterion_dict = {
                "id": str(criterion.id) if hasattr(criterion, 'id') else str(criterion),
                "name": criterion.name if hasattr(criterion, 'name') else "Unnamed Criterion",
            }

            # Add optional description
            if hasattr(criterion, 'description') and criterion.description:
                criterion_dict["description"] = criterion.description

            # Add weight if present
            if hasattr(criterion, 'weight') and criterion.weight is not None:
                criterion_dict["weight"] = float(criterion.weight)

            # Add point value if present
            if hasattr(criterion, 'point_value') and criterion.point_value is not None:
                criterion_dict["point_value"] = float(criterion.point_value)
            elif hasattr(criterion, 'max_points') and criterion.max_points is not None:
                criterion_dict["point_value"] = float(criterion.max_points)

            # Encode descriptors
            descriptors = []
            if hasattr(criterion, 'descriptors'):
                descriptors = self.encode_descriptors(criterion.descriptors)
            elif hasattr(criterion, 'levels'):
                descriptors = self.encode_descriptors(criterion.levels)

            # Descriptors are required
            criterion_dict["descriptors"] = descriptors if descriptors else [
                {
                    "level": "excellent",
                    "description": "Excellent work",
                    "points": criterion_dict.get("point_value", 0)
                }
            ]

            encoded.append(criterion_dict)

        return encoded

    def encode_descriptors(self, descriptors_list) -> list:
        """
        Encode performance level descriptors.

        Args:
            descriptors_list: List of descriptor objects

        Returns:
            list: Serialized descriptors
        """
        if not descriptors_list:
            return []

        encoded = []
        for descriptor in descriptors_list:
            descriptor_dict = {}

            # Extract level (required)
            if hasattr(descriptor, 'level'):
                descriptor_dict["level"] = descriptor.level
            elif isinstance(descriptor, dict) and 'level' in descriptor:
                descriptor_dict["level"] = descriptor['level']
            else:
                # Skip descriptors without level
                continue

            # Extract description (required)
            if hasattr(descriptor, 'description'):
                descriptor_dict["description"] = descriptor.description
            elif isinstance(descriptor, dict) and 'description' in descriptor:
                descriptor_dict["description"] = descriptor['description']
            else:
                descriptor_dict["description"] = f"{descriptor_dict['level'].capitalize()} performance"

            # Extract points (optional)
            if hasattr(descriptor, 'points'):
                if descriptor.points is not None:
                    descriptor_dict["points"] = float(descriptor.points)
            elif isinstance(descriptor, dict) and 'points' in descriptor:
                descriptor_dict["points"] = float(descriptor['points'])

            encoded.append(descriptor_dict)

        return encoded

    def to_json_string(self, scheme, pretty=True) -> str:
        """
        Serialize scheme to JSON string.

        Args:
            scheme: MarkingScheme ORM object
            pretty: Whether to format with indentation

        Returns:
            str: JSON string
        """
        scheme_dict = self.to_dict(scheme)

        if pretty:
            return json.dumps(
                scheme_dict,
                cls=MarkingSchemeEncoder,
                indent=2,
                sort_keys=False,
                ensure_ascii=False
            )
        else:
            return json.dumps(
                scheme_dict,
                cls=MarkingSchemeEncoder,
                separators=(',', ':'),
                ensure_ascii=False
            )
