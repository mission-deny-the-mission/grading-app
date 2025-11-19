"""Project sharing and permission tests."""

import pytest

from models import db
from services.deployment_service import DeploymentService
from services.sharing_service import SharingService
from tests.factories import ProjectFactory, ShareFactory, TestScenarios, UserFactory


class TestProjectSharing:
    """Test project sharing functionality."""

    def test_share_project_success(self, app):
        """Test successful project sharing."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            share = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            assert share is not None
            assert share.project_id == project.id
            assert share.user_id == recipient.id
            assert share.permission_level == "read"
            assert share.granted_by == owner.id

    def test_share_project_write_permission(self, app):
        """Test sharing project with write permission."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            share = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="write",
            )

            assert share.permission_level == "write"

    def test_share_project_invalid_permission(self, app):
        """Test sharing with invalid permission fails."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            with pytest.raises(ValueError, match="Invalid permission level"):
                SharingService.share_project(
                    project_id=project.id,
                    owner_id=owner.id,
                    recipient_id=recipient.id,
                    permission_level="admin",  # Invalid
                )

    def test_share_project_with_self_fails(self, app):
        """Test cannot share project with self."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            with pytest.raises(ValueError, match="Cannot share project with self"):
                SharingService.share_project(
                    project_id=project.id,
                    owner_id=owner.id,
                    recipient_id=owner.id,
                    permission_level="read",
                )

    def test_share_project_nonexistent_user_fails(self, app):
        """Test sharing with nonexistent user fails."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            with pytest.raises(ValueError, match="User .* not found"):
                SharingService.share_project(
                    project_id=project.id,
                    owner_id=owner.id,
                    recipient_id="nonexistent-user-id",
                    permission_level="read",
                )

    def test_share_project_updates_existing(self, app):
        """Test re-sharing project updates existing share."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            # Initial share with read permission
            share1 = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            # Update to write permission
            share2 = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="write",
            )

            # Should be same share, updated
            assert share1.id == share2.id
            assert share2.permission_level == "write"


class TestSharedProjectAccess:
    """Test shared project access."""

    def test_shared_project_appears_in_list(self, app):
        """Test shared projects appear in user's accessible projects."""
        with app.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            reader = scenario["collaborators"][0]
            project = scenario["project"]

            accessible = SharingService.get_user_accessible_projects(user_id=reader.id)

            shared_projects = accessible["shared_projects"]
            project_ids = [p["project_id"] for p in shared_projects]

            assert project.id in project_ids

    def test_get_project_shares_returns_all(self, app):
        """Test getting all shares for a project."""
        with app.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            project = scenario["project"]

            shares = SharingService.get_project_shares(project_id=project.id)

            assert len(shares) == 2  # Read and write shares


class TestUpdateSharePermissions:
    """Test updating share permissions."""

    def test_update_share_from_read_to_write(self, app):
        """Test updating share from read to write permission."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            # Create read share
            share = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            # Update to write
            updated = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="write",
            )

            assert updated.id == share.id
            assert updated.permission_level == "write"

    def test_update_share_from_write_to_read(self, app):
        """Test updating share from write to read permission."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            # Create write share
            share = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="write",
            )

            # Downgrade to read
            updated = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            assert updated.id == share.id
            assert updated.permission_level == "read"


class TestRevokeShare:
    """Test revoking project access."""

    def test_revoke_share_success(self, app):
        """Test successfully revoking project share."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            share = SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            # Revoke the share
            result = SharingService.revoke_share(project_id=project.id, share_id=share.id)

            assert result is True

            # Verify user no longer has access
            can_access = SharingService.can_access_project(
                user_id=recipient.id, project_id=project.id
            )
            assert can_access is False

    def test_revoke_share_nonexistent_fails(self, app):
        """Test revoking nonexistent share fails."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            with pytest.raises(ValueError, match="Share .* not found"):
                SharingService.revoke_share(
                    project_id=project.id, share_id="nonexistent-share-id"
                )


class TestAccessPermissions:
    """Test access permission checking."""

    def test_can_access_with_read_permission(self, app):
        """Test users with read permission can access."""
        with app.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            reader = scenario["collaborators"][0]
            project = scenario["project"]

            can_access = SharingService.can_access_project(
                user_id=reader.id, project_id=project.id
            )

            assert can_access is True

    def test_can_access_with_write_permission(self, app):
        """Test users with write permission can access."""
        with app.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            writer = scenario["collaborators"][1]
            project = scenario["project"]

            can_access = SharingService.can_access_project(
                user_id=writer.id, project_id=project.id
            )

            assert can_access is True

    def test_cannot_access_without_permission(self, app):
        """Test users without permission cannot access."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            other_user = UserFactory.create(email="other@example.com")
            project = ProjectFactory.create(job_name="Private Project", owner_id=owner.id)

            can_access = SharingService.can_access_project(
                user_id=other_user.id, project_id=project.id
            )

            assert can_access is False


class TestModifyPermissions:
    """Test modification permission checking."""

    def test_cannot_modify_with_read_only(self, app):
        """Test users with read-only permission cannot modify."""
        with app.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            reader = scenario["collaborators"][0]
            project = scenario["project"]

            can_modify = SharingService.can_modify_project(
                user_id=reader.id, project_id=project.id
            )

            assert can_modify is False

    def test_can_modify_with_write_permission(self, app):
        """Test users with write permission can modify."""
        with app.app_context():
            scenario = TestScenarios.create_multi_user_project_scenario()
            writer = scenario["collaborators"][1]
            project = scenario["project"]

            can_modify = SharingService.can_modify_project(
                user_id=writer.id, project_id=project.id
            )

            assert can_modify is True


class TestUserShareCleanup:
    """Test cleanup when users are deleted."""

    def test_delete_user_shares_removes_all(self, app):
        """Test deleting user shares removes all related shares."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient1 = UserFactory.create(email="recipient1@example.com")
            recipient2 = UserFactory.create(email="recipient2@example.com")

            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            # Owner shares with two users
            SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient1.id,
                permission_level="read",
            )
            SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient2.id,
                permission_level="write",
            )

            # Delete owner's shares
            count = SharingService.delete_user_shares(user_id=owner.id)

            assert count == 2

            # Verify shares removed
            shares = SharingService.get_project_shares(project_id=project.id)
            assert len(shares) == 0

    def test_delete_recipient_shares(self, app):
        """Test deleting recipient removes their access."""
        with app.app_context():
            owner = UserFactory.create(email="owner@example.com")
            recipient = UserFactory.create(email="recipient@example.com")

            project = ProjectFactory.create(job_name="Test Project", owner_id=owner.id)

            SharingService.share_project(
                project_id=project.id,
                owner_id=owner.id,
                recipient_id=recipient.id,
                permission_level="read",
            )

            # Delete recipient's shares
            count = SharingService.delete_user_shares(user_id=recipient.id)

            assert count == 1

            # Verify recipient no longer has access
            can_access = SharingService.can_access_project(
                user_id=recipient.id, project_id=project.id
            )
            assert can_access is False
