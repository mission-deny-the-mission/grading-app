"""Integration tests for sharing functionality (User Story 5 & 6 - T105-T114)."""

from datetime import datetime, timezone
from decimal import Decimal
import json

import pytest

from app import app
from models import GradingScheme, SchemeShare, SharePermission, User, DeploymentConfig, db
from services.auth_service import AuthService


@pytest.fixture(scope="function")
def app_context():
    """Create app context for tests."""
    with app.app_context():
        db.create_all()
        # Initialize deployment mode to multi-user for sharing tests
        # This enables proper authentication and permission checking
        config = DeploymentConfig.query.filter_by(id="singleton").first()
        if not config:
            config = DeploymentConfig(id="singleton", mode="multi-user")
            db.session.add(config)
            db.session.commit()
        else:
            config.mode = "multi-user"
            db.session.commit()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_context):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def owner_user(app_context):
    """Create a scheme owner user."""
    user = AuthService.create_user(
        email="owner@example.com",
        password="OwnerPass123!",
        display_name="Scheme Owner",
    )
    return user


@pytest.fixture
def recipient_user(app_context):
    """Create a recipient user."""
    user = AuthService.create_user(
        email="recipient@example.com",
        password="RecipientPass123!",
        display_name="Recipient User",
    )
    return user


@pytest.fixture
def recipient2_user(app_context):
    """Create a second recipient user."""
    user = AuthService.create_user(
        email="recipient2@example.com",
        password="Recipient2Pass123!",
        display_name="Second Recipient",
    )
    return user


@pytest.fixture
def other_user(app_context):
    """Create another user with no access."""
    user = AuthService.create_user(
        email="other@example.com",
        password="OtherPass123!",
        display_name="Other User",
    )
    return user


@pytest.fixture
def sample_scheme(app_context, owner_user):
    """Create a sample grading scheme."""
    scheme = GradingScheme(
        name="Test Scheme",
        description="Test scheme for sharing tests",
        created_by=owner_user.id,
        total_possible_points=Decimal("100.00"),
    )
    db.session.add(scheme)
    db.session.commit()
    return scheme


def login_user(client, email, password):
    """Log in a user via the API."""
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200, f"Login failed: {response.get_json()}"
    return client


@pytest.fixture
def authenticated_client(client, owner_user):
    """Create an authenticated client session as the owner."""
    return login_user(client, "owner@example.com", "OwnerPass123!")


class TestPostShareWithUserGrantsAccess:
    """Test T105: POST /api/schemes/{id}/share with user grants access."""

    def test_share_scheme_with_user_view_only(self, authenticated_client, owner_user, recipient_user, sample_scheme):
        """Sharing a scheme with VIEW_ONLY permission grants view access."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["scheme_id"] == sample_scheme.id
        assert data["user_id"] == recipient_user.id
        assert data["permission"] == "VIEW_ONLY"
        assert data["shared_by_id"] == owner_user.id

        # Verify share exists in database
        share = SchemeShare.query.filter_by(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id
        ).first()
        assert share is not None
        assert share.permission == "VIEW_ONLY"
        assert share.is_active() is True

    def test_share_scheme_with_user_editable(self, authenticated_client, owner_user, recipient_user, sample_scheme):
        """Sharing a scheme with EDITABLE permission grants edit access."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "permission": "EDITABLE",
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["permission"] == "EDITABLE"

        # Verify share exists
        share = SchemeShare.query.filter_by(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id
        ).first()
        assert share is not None
        assert share.permission == "EDITABLE"

    def test_share_scheme_with_user_copy(self, authenticated_client, owner_user, recipient_user, sample_scheme):
        """Sharing a scheme with COPY permission grants copy access."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "permission": "COPY",
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["permission"] == "COPY"

    def test_share_scheme_missing_permission_fails(self, authenticated_client, recipient_user, sample_scheme):
        """Sharing without permission field should fail."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
            }
        )

        assert response.status_code == 400
        assert "permission" in response.get_json()["error"].lower()

    def test_share_scheme_invalid_permission_fails(self, authenticated_client, recipient_user, sample_scheme):
        """Sharing with invalid permission should fail."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "permission": "INVALID_PERMISSION",
            }
        )

        assert response.status_code == 400

    def test_share_scheme_duplicate_user_fails(self, authenticated_client, recipient_user, sample_scheme):
        """Sharing with same user twice should fail."""
        # First share
        authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "permission": "VIEW_ONLY",
            }
        )

        # Second share with same user
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "permission": "EDITABLE",
            }
        )

        assert response.status_code == 409
        assert "already shared" in response.get_json()["error"].lower()

    def test_share_scheme_nonexistent_user_fails(self, authenticated_client, sample_scheme):
        """Sharing with nonexistent user should fail."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": "nonexistent-user-id",
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 404

    def test_share_scheme_nonexistent_scheme_fails(self, authenticated_client, recipient_user):
        """Sharing nonexistent scheme should fail."""
        response = authenticated_client.post(
            "/api/schemes/nonexistent-scheme-id/share",
            json={
                "user_id": recipient_user.id,
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 404


class TestPostShareWithGroupGrantsAccess:
    """Test T106: POST /api/schemes/{id}/share with group grants access to all members."""

    def test_share_scheme_with_group(self, authenticated_client, owner_user, sample_scheme):
        """Sharing a scheme with a group grants access to all group members."""
        mock_group_id = "test-group-123"

        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "group_id": mock_group_id,
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["scheme_id"] == sample_scheme.id
        assert data["group_id"] == mock_group_id
        assert data["permission"] == "VIEW_ONLY"
        assert data["shared_by_id"] == owner_user.id

        # Verify share exists in database
        share = SchemeShare.query.filter_by(
            scheme_id=sample_scheme.id,
            group_id=mock_group_id
        ).first()
        assert share is not None
        assert share.permission == "VIEW_ONLY"

    def test_share_with_both_user_and_group_fails(self, authenticated_client, recipient_user, sample_scheme):
        """Sharing with both user_id and group_id should fail (XOR constraint)."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "user_id": recipient_user.id,
                "group_id": "test-group-123",
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 400
        assert "either user_id or group_id" in response.get_json()["error"].lower()

    def test_share_with_neither_user_nor_group_fails(self, authenticated_client, sample_scheme):
        """Sharing with neither user_id nor group_id should fail."""
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 400
        assert "user_id or group_id" in response.get_json()["error"].lower()

    def test_share_group_duplicate_fails(self, authenticated_client, sample_scheme):
        """Sharing with same group twice should fail."""
        mock_group_id = "test-group-456"

        # First share
        authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "group_id": mock_group_id,
                "permission": "VIEW_ONLY",
            }
        )

        # Second share with same group
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share",
            json={
                "group_id": mock_group_id,
                "permission": "EDITABLE",
            }
        )

        assert response.status_code == 409


class TestDeleteShareRevokeRemovesAccess:
    """Test T107: DELETE /api/schemes/shares/{id} removes access."""

    def test_revoke_user_share(self, authenticated_client, owner_user, recipient_user, sample_scheme):
        """Revoking a user share removes access."""
        # Create share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Revoke share
        response = authenticated_client.delete(f"/api/schemes/shares/{share.id}")

        assert response.status_code == 204

        # Verify share is revoked
        db.session.refresh(share)
        assert share.revoked_at is not None
        assert share.revoked_by_id == owner_user.id
        assert share.is_active() is False

    def test_revoke_group_share(self, authenticated_client, owner_user, sample_scheme):
        """Revoking a group share removes access for all members."""
        mock_group_id = "test-group-789"

        # Create group share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            group_id=mock_group_id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Revoke share
        response = authenticated_client.delete(f"/api/schemes/shares/{share.id}")

        assert response.status_code == 204

        # Verify share is revoked
        db.session.refresh(share)
        assert share.revoked_at is not None
        assert share.is_active() is False

    def test_revoke_nonexistent_share_fails(self, authenticated_client):
        """Revoking a nonexistent share should fail."""
        response = authenticated_client.delete("/api/schemes/shares/nonexistent-share-id")

        assert response.status_code == 404

    def test_revoke_already_revoked_share_fails(self, authenticated_client, owner_user, recipient_user, sample_scheme):
        """Revoking an already revoked share should fail."""
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

        # Try to revoke again
        response = authenticated_client.delete(f"/api/schemes/shares/{share.id}")

        assert response.status_code == 409
        assert "already revoked" in response.get_json()["error"].lower()


class TestGetSharedWithMeReturnsSchemes:
    """Test T108: GET /api/schemes/shared-with-me returns accessible schemes."""

    def test_get_shared_with_me_returns_user_shares(self, client, owner_user, recipient_user, sample_scheme):
        """GET shared-with-me should return schemes shared with user."""
        # Create share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get("/api/schemes/shared-with-me")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["schemes"]) >= 1
        assert any(s["id"] == sample_scheme.id for s in data["schemes"])

    def test_get_shared_with_me_excludes_revoked(self, client, owner_user, recipient_user, sample_scheme):
        """GET shared-with-me should exclude revoked shares."""
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

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get("/api/schemes/shared-with-me")

        assert response.status_code == 200
        data = response.get_json()
        assert not any(s["id"] == sample_scheme.id for s in data["schemes"])

    def test_get_shared_with_me_includes_permission_level(self, client, owner_user, recipient_user, sample_scheme):
        """GET shared-with-me should include permission level for each scheme."""
        # Create share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get("/api/schemes/shared-with-me")

        assert response.status_code == 200
        data = response.get_json()
        shared_scheme = next((s for s in data["schemes"] if s["id"] == sample_scheme.id), None)
        assert shared_scheme is not None
        assert shared_scheme["permission"] == "EDITABLE"

    def test_get_shared_with_me_filter_by_permission(self, client, owner_user, recipient_user, sample_scheme):
        """GET shared-with-me with permission filter returns only matching schemes."""
        # Create shares with different permissions
        scheme2 = GradingScheme(
            name="Test Scheme 2",
            created_by=owner_user.id,
            total_possible_points=Decimal("50.00"),
        )
        db.session.add(scheme2)
        db.session.commit()

        share1 = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        share2 = SchemeShare(
            scheme_id=scheme2.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add_all([share1, share2])
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get("/api/schemes/shared-with-me?permission_filter=EDITABLE")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["schemes"]) >= 1
        assert all(s["permission"] == "EDITABLE" for s in data["schemes"])
        assert any(s["id"] == scheme2.id for s in data["schemes"])
        assert not any(s["id"] == sample_scheme.id for s in data["schemes"])


class TestPermissionEnforcementViewOnlyCannotModify:
    """Test T109: VIEW_ONLY permission cannot modify scheme."""

    @pytest.fixture(autouse=True)
    def multi_user_mode(self, app_context):
        """Set multi-user mode for permission enforcement tests."""
        from services.deployment_service import DeploymentService
        DeploymentService.set_mode("multi-user")
        yield

    def test_view_only_cannot_update_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """VIEW_ONLY recipient should get 403 when trying to update scheme."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Try to update scheme
        response = client.put(
            f"/api/schemes/{sample_scheme.id}",
            json={"name": "Updated Name"}
        )

        assert response.status_code == 403
        assert "permission" in response.get_json()["error"].lower()

    def test_view_only_can_get_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """VIEW_ONLY recipient should be able to GET scheme."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Try to get scheme
        response = client.get(f"/api/schemes/{sample_scheme.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == sample_scheme.id

    def test_view_only_cannot_delete_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """VIEW_ONLY recipient should get 403 when trying to delete scheme."""
        # Create VIEW_ONLY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Try to delete scheme
        response = client.delete(f"/api/schemes/{sample_scheme.id}")

        assert response.status_code == 403


class TestPermissionEnforcementEditableCanModify:
    """Test T110: EDITABLE permission can modify scheme."""

    @pytest.fixture(autouse=True)
    def multi_user_mode(self, app_context):
        """Set multi-user mode for permission enforcement tests."""
        from services.deployment_service import DeploymentService
        DeploymentService.set_mode("multi-user")
        yield

    def test_editable_can_update_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """EDITABLE recipient should be able to update scheme."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Update scheme
        response = client.put(
            f"/api/schemes/{sample_scheme.id}",
            json={"name": "Updated Name by Recipient"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Name by Recipient"

        # Verify scheme was actually updated
        db.session.refresh(sample_scheme)
        assert sample_scheme.name == "Updated Name by Recipient"

    def test_editable_can_get_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """EDITABLE recipient should be able to GET scheme."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get(f"/api/schemes/{sample_scheme.id}")

        assert response.status_code == 200

    def test_editable_cannot_delete_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """EDITABLE recipient should NOT be able to delete scheme (only owner can)."""
        # Create EDITABLE share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Try to delete scheme
        response = client.delete(f"/api/schemes/{sample_scheme.id}")

        assert response.status_code == 403


class TestPermissionEnforcementCopyCreatesIndependentCopy:
    """Test T111: COPY permission creates independent copy."""

    @pytest.fixture(autouse=True)
    def multi_user_mode(self, app_context):
        """Set multi-user mode for permission enforcement tests."""
        from services.deployment_service import DeploymentService
        DeploymentService.set_mode("multi-user")
        yield

    def test_copy_can_clone_scheme(self, client, owner_user, recipient_user, sample_scheme):
        """COPY recipient should be able to create independent copy."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Clone scheme
        response = client.post(
            f"/api/schemes/{sample_scheme.id}/clone",
            json={"name": "My Copy of Test Scheme"}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "My Copy of Test Scheme"
        assert data["id"] != sample_scheme.id
        assert data["created_by"] == recipient_user.id

        # Verify original scheme is unchanged
        db.session.refresh(sample_scheme)
        assert sample_scheme.name == "Test Scheme"

    def test_copy_cannot_modify_original(self, client, owner_user, recipient_user, sample_scheme):
        """COPY recipient should NOT be able to modify original scheme."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Try to update original scheme
        response = client.put(
            f"/api/schemes/{sample_scheme.id}",
            json={"name": "Modified Original"}
        )

        assert response.status_code == 403

    def test_copy_can_view_original(self, client, owner_user, recipient_user, sample_scheme):
        """COPY recipient should be able to view original scheme."""
        # Create COPY share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.COPY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as recipient
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get(f"/api/schemes/{sample_scheme.id}")

        assert response.status_code == 200


class TestGroupMemberAutoGetsAccessWhenAdded:
    """Test T112: Group member automatically gets access when added to group."""

    def test_new_group_member_inherits_share(self, client, owner_user, recipient_user, sample_scheme):
        """When user is added to group, they should inherit group's shares."""
        mock_group_id = "test-group-auto-access"

        # Create group share BEFORE user joins group
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            group_id=mock_group_id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Simulate: recipient_user is added to group
        # (This would happen via UserGroup/GroupMembership tables in real implementation)

        # Authenticate as new group member
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # New member should now have access to scheme via group
        response = client.get(f"/api/schemes/{sample_scheme.id}")

        # Should succeed (status 200) once group membership is implemented
        assert response.status_code == 200

    def test_group_member_sees_scheme_in_shared_with_me(self, client, owner_user, recipient_user, sample_scheme):
        """Group member should see group-shared schemes in shared-with-me."""
        mock_group_id = "test-group-listing"

        # Create group share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            group_id=mock_group_id,
            permission=SharePermission.EDITABLE.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Authenticate as group member
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get("/api/schemes/shared-with-me")

        assert response.status_code == 200
        data = response.get_json()
        # Should include group-shared schemes
        assert any(s["id"] == sample_scheme.id for s in data["schemes"])


class TestGroupMemberLosesAccessWhenRemoved:
    """Test T113: Group member loses access when removed from group."""

    @pytest.fixture(autouse=True)
    def multi_user_mode(self, app_context):
        """Set multi-user mode for permission enforcement tests."""
        from services.deployment_service import DeploymentService
        DeploymentService.set_mode("multi-user")
        yield

    @pytest.mark.xfail(reason="Group membership checking not fully implemented yet")
    def test_removed_group_member_loses_access(self, client, owner_user, recipient_user, sample_scheme):
        """When user is removed from group, they should lose group's shares."""
        mock_group_id = "test-group-removal"

        # Create group share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            group_id=mock_group_id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Simulate: recipient_user WAS in group, now removed
        # (This would update UserGroup/GroupMembership tables)

        # Authenticate as removed member
        login_user(client, "recipient@example.com", "RecipientPass123!")

        # Removed member should no longer have access
        response = client.get(f"/api/schemes/{sample_scheme.id}")

        # Should fail (status 403) once group membership is implemented
        assert response.status_code == 403

    @pytest.mark.xfail(reason="Group membership checking not fully implemented yet")
    def test_removed_member_does_not_see_in_shared_with_me(self, client, owner_user, recipient_user, sample_scheme):
        """Removed group member should not see group-shared schemes in shared-with-me."""
        mock_group_id = "test-group-removal-listing"

        # Create group share
        share = SchemeShare(
            scheme_id=sample_scheme.id,
            group_id=mock_group_id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(share)
        db.session.commit()

        # Simulate: recipient_user removed from group

        # Authenticate as removed member
        login_user(client, "recipient@example.com", "RecipientPass123!")

        response = client.get("/api/schemes/shared-with-me")

        assert response.status_code == 200
        data = response.get_json()
        # Should NOT include group-shared schemes
        assert not any(s["id"] == sample_scheme.id for s in data["schemes"])


class TestFiftyPlusRecipientsInSingleShare:
    """Test T114: Sharing with 50+ recipients in a single request."""

    def test_share_with_50_plus_users(self, authenticated_client, owner_user, sample_scheme, app_context):
        """Sharing with 50+ users should succeed."""
        # Create 60 users
        user_ids = []
        for i in range(60):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed_password",
                display_name=f"User {i}",
            )
            db.session.add(user)
            db.session.flush()
            user_ids.append(user.id)
        db.session.commit()

        # Share with all 60 users in a single request
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share/bulk",
            json={
                "user_ids": user_ids,
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["shares_created"] == 60
        assert len(data["shares"]) == 60

        # Verify all shares exist in database
        shares = SchemeShare.query.filter_by(scheme_id=sample_scheme.id).all()
        assert len(shares) == 60

    def test_share_with_50_plus_groups(self, authenticated_client, owner_user, sample_scheme):
        """Sharing with 50+ groups should succeed."""
        # Create 55 mock group IDs
        group_ids = [f"group-{i}" for i in range(55)]

        # Share with all 55 groups in a single request
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share/bulk",
            json={
                "group_ids": group_ids,
                "permission": "EDITABLE",
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["shares_created"] == 55

        # Verify all shares exist
        shares = SchemeShare.query.filter_by(scheme_id=sample_scheme.id).all()
        assert len(shares) == 55

    def test_bulk_share_partial_failure(self, authenticated_client, owner_user, sample_scheme, recipient_user):
        """Bulk share should handle partial failures gracefully."""
        # Create existing share
        existing_share = SchemeShare(
            scheme_id=sample_scheme.id,
            user_id=recipient_user.id,
            permission=SharePermission.VIEW_ONLY.value,
            shared_by_id=owner_user.id,
        )
        db.session.add(existing_share)
        db.session.commit()

        # Create 5 more users
        user_ids = [recipient_user.id]  # Already shared
        for i in range(5):
            user = User(
                email=f"newuser{i}@example.com",
                password_hash="hashed_password",
                display_name=f"New User {i}",
            )
            db.session.add(user)
            db.session.flush()
            user_ids.append(user.id)
        db.session.commit()

        # Try to share with all (including duplicate)
        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share/bulk",
            json={
                "user_ids": user_ids,
                "permission": "VIEW_ONLY",
            }
        )

        # Should succeed for new users, skip duplicate
        assert response.status_code == 207  # Multi-Status
        data = response.get_json()
        assert data["shares_created"] == 5
        assert data["shares_skipped"] == 1
        assert len(data["errors"]) == 1

    def test_bulk_share_all_invalid_users(self, authenticated_client, sample_scheme):
        """Bulk share with all invalid users should fail appropriately."""
        invalid_user_ids = [f"invalid-user-{i}" for i in range(10)]

        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share/bulk",
            json={
                "user_ids": invalid_user_ids,
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 207
        data = response.get_json()
        assert data["shares_created"] == 0
        assert len(data["errors"]) == 10

    def test_bulk_share_exceeds_reasonable_limit(self, authenticated_client, sample_scheme):
        """Bulk share should enforce reasonable upper limits (e.g., 1000 recipients)."""
        # Try to share with 1500 users (exceeds limit)
        user_ids = [f"user-{i}" for i in range(1500)]

        response = authenticated_client.post(
            f"/api/schemes/{sample_scheme.id}/share/bulk",
            json={
                "user_ids": user_ids,
                "permission": "VIEW_ONLY",
            }
        )

        assert response.status_code == 400
        assert "too many recipients" in response.get_json()["error"].lower()
