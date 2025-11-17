"""
Permission Checking Service

Handles authorization checks for shared marking schemes.
Implements User Story 5 (Share with Users) and User Story 6 (Share with Groups).
Web version only.
"""

from typing import List, Tuple
from enum import Enum


class SharePermission(Enum):
    """Permission levels for shared schemes."""
    VIEW_ONLY = "VIEW_ONLY"      # Can view and use; cannot modify
    EDITABLE = "EDITABLE"        # Can view, use, and modify (affects shared version)
    COPY = "COPY"                # Can create independent copy


class PermissionChecker:
    """Checks authorization for scheme access and modifications."""

    @staticmethod
    def check_scheme_permission(user_id: str, scheme_id: str, required_permission: str) -> bool:
        """
        Check if user has required permission on scheme.

        Args:
            user_id: User ID to check
            scheme_id: Scheme ID to access
            required_permission: Required permission level

        Returns:
            bool: True if user has permission
        """
        # TODO: Implement permission check (T115)
        pass

    @staticmethod
    def can_view_scheme(user_id: str, scheme_id: str) -> bool:
        """
        Check if user can view scheme.

        Returns True if user is owner or has VIEW_ONLY or higher.

        Args:
            user_id: User ID
            scheme_id: Scheme ID

        Returns:
            bool: True if can view
        """
        # TODO: Implement view permission check (T116)
        pass

    @staticmethod
    def can_edit_scheme(user_id: str, scheme_id: str) -> bool:
        """
        Check if user can edit scheme.

        Returns True if user is owner or has EDITABLE permission
        (NOT COPY, NOT VIEW_ONLY).

        Args:
            user_id: User ID
            scheme_id: Scheme ID

        Returns:
            bool: True if can edit
        """
        # TODO: Implement edit permission check (T116)
        pass

    @staticmethod
    def can_copy_scheme(user_id: str, scheme_id: str) -> bool:
        """
        Check if user can copy scheme.

        Returns True if user has COPY permission.

        Args:
            user_id: User ID
            scheme_id: Scheme ID

        Returns:
            bool: True if can copy
        """
        # TODO: Implement copy permission check (T116)
        pass

    @staticmethod
    def get_user_accessible_schemes(user_id: str) -> List[Tuple]:
        """
        Get all schemes accessible to user.

        Includes:
        - Schemes owned by user (full access)
        - Schemes shared with user (via SchemeShare)
        - Schemes shared with user's groups

        Args:
            user_id: User ID

        Returns:
            list: [(MarkingScheme, permission_level), ...] sorted by shared_at DESC
        """
        # TODO: Implement accessible schemes query (T117)
        pass

    @staticmethod
    def is_owner(user_id: str, scheme_id: str) -> bool:
        """
        Check if user owns scheme.

        Args:
            user_id: User ID
            scheme_id: Scheme ID

        Returns:
            bool: True if user is owner
        """
        # TODO: Implement owner check (T115)
        pass

    @staticmethod
    def has_active_share(user_id: str, scheme_id: str) -> bool:
        """
        Check if active share exists for user on scheme.

        Args:
            user_id: User ID
            scheme_id: Scheme ID

        Returns:
            bool: True if active (non-revoked) share exists
        """
        # TODO: Implement active share check (T115)
        pass
