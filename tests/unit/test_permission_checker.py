"""Unit tests for PermissionChecker service (User Story 5 & 6 - T099-T104)."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from models import GradingScheme, MarkingScheme, SchemeShare, SharePermission, User, db
from services.permission_checker import PermissionChecker


@pytest.fixture
def owner_user(app):
    """Create a scheme owner user."""
    user = User(
        email="owner@example.com",
        password_hash="hashed_password",
        display_name="Scheme Owner",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def recipient_user(app):
    """Create a recipient user."""
    user = User(
        email="recipient@example.com",
        password_hash="hashed_password",
        display_name="Recipient User",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_user(app):
    """Create another user with no access."""
    user = User(
        email="other@example.com",
        password_hash="hashed_password",
        display_name="Other User",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_scheme(app, owner_user):
    """Create a sample marking scheme."""
    scheme = MarkingScheme(
        name="Test Scheme",
        original_filename="test_scheme.txt",
        filename="test_scheme.txt",
        file_type="txt",
        file_size=1024,
        content="Test scheme content",
        owner_id=owner_user.id,
    )
    db.session.add(scheme)
    db.session.commit()
    return scheme


class TestHasPermissionForOwner:
    """Test T099: Owner always has permission."""

    def test_owner_has_view_permission(self, app, owner_user, sample_scheme):
        """Owner should always have VIEW_ONLY permission."""
        result = PermissionChecker.has_permission(
            owner_user.id, sample_scheme.id, SharePermission.VIEW_ONLY.value
        )
        assert result is True

    def test_owner_has_editable_permission(self, app, owner_user, sample_scheme):
        """Owner should always have EDITABLE permission."""
        result = PermissionChecker.has_permission(
            owner_user.id, sample_scheme.id, SharePermission.EDITABLE.value
        )
        assert result is True

    def test_owner_has_copy_permission(self, app, owner_user, sample_scheme):
        """Owner should always have COPY permission."""
        result = PermissionChecker.has_permission(
            owner_user.id, sample_scheme.id, SharePermission.COPY.value
        )
        assert result is True

    def test_owner_can_view_scheme(self, app, owner_user, sample_scheme):
        """Owner should be able to view scheme."""
        result = PermissionChecker.can_view_scheme(owner_user.id, sample_scheme.id)
        assert result is True

    def test_owner_can_edit_scheme(self, app, owner_user, sample_scheme):
        """Owner should be able to edit scheme."""
        result = PermissionChecker.can_edit_scheme(owner_user.id, sample_scheme.id)
        assert result is True

    def test_owner_can_copy_scheme(self, app, owner_user, sample_scheme):
        """Owner should be able to copy scheme."""
        result = PermissionChecker.can_copy_scheme(owner_user.id, sample_scheme.id)
        assert result is True


class TestHasPermissionViewOnly:
    """Test T100: VIEW_ONLY recipient restrictions."""

    def test_view_only_can_view(self, app, owner_user, recipient_user, sample_scheme):
        """VIEW_ONLY recipient should be able to view scheme."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_view_scheme(recipient_user.id, sample_scheme.id)
        assert result is True

    def test_view_only_cannot_edit(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """VIEW_ONLY recipient should NOT be able to edit scheme."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_edit_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_view_only_cannot_copy(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """VIEW_ONLY recipient should NOT be able to copy scheme."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_copy_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_view_only_has_view_permission(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """VIEW_ONLY recipient should have VIEW_ONLY permission."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.has_permission(
            recipient_user.id, sample_scheme.id, SharePermission.VIEW_ONLY.value
        )
        assert result is True


class TestHasPermissionEditable:
    """Test T101: EDITABLE recipient permissions."""

    def test_editable_can_view(self, app, owner_user, recipient_user, sample_scheme):
        """EDITABLE recipient should be able to view scheme."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_view_scheme(recipient_user.id, sample_scheme.id)
        assert result is True

    def test_editable_can_edit(self, app, owner_user, recipient_user, sample_scheme):
        """EDITABLE recipient should be able to edit scheme."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_edit_scheme(recipient_user.id, sample_scheme.id)
        assert result is True

    def test_editable_cannot_copy(self, app, owner_user, recipient_user, sample_scheme):
        """EDITABLE recipient should NOT be able to copy scheme (only COPY permission allows this)."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_copy_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_editable_has_editable_permission(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """EDITABLE recipient should have EDITABLE permission."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.has_permission(
            recipient_user.id, sample_scheme.id, SharePermission.EDITABLE.value
        )
        assert result is True


class TestHasPermissionCopy:
    """Test T102: COPY recipient creates independent copy."""

    def test_copy_can_view(self, app, owner_user, recipient_user, sample_scheme):
        """COPY recipient should be able to view scheme."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_view_scheme(recipient_user.id, sample_scheme.id)
        assert result is True

    def test_copy_cannot_edit(self, app, owner_user, recipient_user, sample_scheme):
        """COPY recipient should NOT be able to edit the original scheme."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_edit_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_copy_can_copy(self, app, owner_user, recipient_user, sample_scheme):
        """COPY recipient should be able to copy scheme."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_copy_scheme(recipient_user.id, sample_scheme.id)
        assert result is True

    def test_copy_has_copy_permission(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """COPY recipient should have COPY permission."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.has_permission(
            recipient_user.id, sample_scheme.id, SharePermission.COPY.value
        )
        assert result is True


class TestRevokedAccessDenied:
    """Test T103: Revoked access denies permission."""

    def test_revoked_view_only_cannot_view(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """Revoked VIEW_ONLY share should deny view access."""
        # Create revoked share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
            revoked_at=datetime.now(timezone.utc),
            revoked_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_view_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_revoked_editable_cannot_edit(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """Revoked EDITABLE share should deny edit access."""
        # Create revoked share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
            revoked_at=datetime.now(timezone.utc),
            revoked_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_edit_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_revoked_copy_cannot_copy(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """Revoked COPY share should deny copy access."""
        # Create revoked share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
            revoked_at=datetime.now(timezone.utc),
            revoked_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.can_copy_scheme(recipient_user.id, sample_scheme.id)
        assert result is False

    def test_revoked_has_no_permission(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """Revoked share should deny all permissions."""
        # Create revoked share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
            revoked_at=datetime.now(timezone.utc),
            revoked_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        result = PermissionChecker.has_permission(
            recipient_user.id, sample_scheme.id, SharePermission.VIEW_ONLY.value
        )
        assert result is False

    def test_share_active_until_revoked(
        self, app, owner_user, recipient_user, sample_scheme
    ):
        """Share should be active until explicitly revoked."""
        # Create active share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Should have access
        result = PermissionChecker.can_view_scheme(recipient_user.id, sample_scheme.id)
        assert result is True

        # Revoke access
        share.revoked_at = datetime.now(timezone.utc)
        share.revoked_by_id = owner_user.id
        db.session.commit()

        # Should no longer have access
        result = PermissionChecker.can_view_scheme(recipient_user.id, sample_scheme.id)
        assert result is False


class TestNoPermission:
    """Test users with no permission."""

    def test_user_with_no_share_cannot_view(self, app, other_user, sample_scheme):
        """User with no share should NOT be able to view scheme."""
        result = PermissionChecker.can_view_scheme(other_user.id, sample_scheme.id)
        assert result is False

    def test_user_with_no_share_cannot_edit(self, app, other_user, sample_scheme):
        """User with no share should NOT be able to edit scheme."""
        result = PermissionChecker.can_edit_scheme(other_user.id, sample_scheme.id)
        assert result is False

    def test_user_with_no_share_cannot_copy(self, app, other_user, sample_scheme):
        """User with no share should NOT be able to copy scheme."""
        result = PermissionChecker.can_copy_scheme(other_user.id, sample_scheme.id)
        assert result is False

    def test_user_with_no_share_has_no_permission(self, app, other_user, sample_scheme):
        """User with no share should have no permissions."""
        result = PermissionChecker.has_permission(
            other_user.id, sample_scheme.id, SharePermission.VIEW_ONLY.value
        )
        assert result is False
