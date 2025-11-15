"""Project sharing service for managing access permissions."""

import logging

from models import ProjectShare, User, db

logger = logging.getLogger(__name__)


class SharingService:
    """Service for managing project sharing and permissions."""

    @staticmethod
    def share_project(project_id, owner_id, recipient_id, permission_level="read"):
        """
        Share a project with another user.

        Args:
            project_id: str - Project ID
            owner_id: str - Owner's user ID
            recipient_id: str - Recipient's user ID
            permission_level: str - "read" or "write"

        Returns:
            ProjectShare: Created share record

        Raises:
            ValueError: If share parameters are invalid
        """
        # Validate inputs
        if permission_level not in ("read", "write"):
            raise ValueError(f"Invalid permission level: {permission_level}")

        if owner_id == recipient_id:
            raise ValueError("Cannot share project with self")

        # Verify recipient exists
        recipient = User.query.get(recipient_id)
        if not recipient:
            raise ValueError(f"User {recipient_id} not found")

        try:
            # Check if already shared
            existing = ProjectShare.query.filter_by(project_id=project_id, user_id=recipient_id).first()

            if existing:
                # Update existing share
                existing.permission_level = permission_level
                db.session.commit()
                logger.info(f"Share updated: {project_id} to {recipient_id} ({permission_level})")
                return existing

            # Create new share
            share = ProjectShare(
                project_id=project_id,
                user_id=recipient_id,
                permission_level=permission_level,
                granted_by=owner_id,
            )
            db.session.add(share)
            db.session.commit()
            logger.info(f"Project shared: {project_id} to {recipient_id} ({permission_level})")
            return share
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sharing project: {e}")
            raise

    @staticmethod
    def can_access_project(user_id, project_id, owner_id=None):
        """
        Check if user can access a project.

        Args:
            user_id: str - User ID
            project_id: str - Project ID
            owner_id: str - Optional project owner ID for optimization

        Returns:
            bool: True if user can access project
        """
        # Owner always has access
        if owner_id and user_id == owner_id:
            return True

        # Check for share
        share = ProjectShare.query.filter_by(project_id=project_id, user_id=user_id).first()
        return share is not None

    @staticmethod
    def can_modify_project(user_id, project_id, owner_id=None):
        """
        Check if user can modify a project.

        Args:
            user_id: str - User ID
            project_id: str - Project ID
            owner_id: str - Optional project owner ID

        Returns:
            bool: True if user can modify project
        """
        # Owner can always modify
        if owner_id and user_id == owner_id:
            return True

        # Check for write permission
        share = ProjectShare.query.filter_by(project_id=project_id, user_id=user_id).first()
        return share is not None and share.permission_level == "write"

    @staticmethod
    def get_project_shares(project_id):
        """
        Get all shares for a project.

        Args:
            project_id: str - Project ID

        Returns:
            list: Share records
        """
        shares = ProjectShare.query.filter_by(project_id=project_id).all()
        return [s.to_dict() for s in shares]

    @staticmethod
    def revoke_share(project_id, share_id):
        """
        Revoke access to a project.

        Args:
            project_id: str - Project ID
            share_id: str - Share record ID

        Returns:
            bool: True if successful
        """
        try:
            share = ProjectShare.query.filter_by(id=share_id, project_id=project_id).first()

            if not share:
                raise ValueError(f"Share {share_id} not found for project {project_id}")

            db.session.delete(share)
            db.session.commit()
            logger.info(f"Share revoked: {project_id}, share_id {share_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error revoking share: {e}")
            raise

    @staticmethod
    def get_user_accessible_projects(user_id):
        """
        Get all projects accessible to a user (owned + shared).

        Args:
            user_id: str - User ID

        Returns:
            dict: {
                "owned_projects": list of project IDs,
                "shared_projects": list of {"project_id", "permission_level"} dicts
            }
        """
        # Get shared projects
        shares = (
            ProjectShare.query.filter_by(user_id=user_id).with_entities(ProjectShare.project_id, ProjectShare.permission_level).all()
        )

        shared_projects = [{"project_id": s[0], "permission_level": s[1]} for s in shares]

        return {
            "user_id": user_id,
            "shared_projects": shared_projects,
            # Note: owned_projects should be fetched from GradingJob table
            # This is just the shared access information
        }

    @staticmethod
    def delete_user_shares(user_id):
        """
        Delete all shares for a user (when user is deleted).

        Args:
            user_id: str - User ID to remove shares for

        Returns:
            int: Number of shares deleted
        """
        try:
            # Find all shares given by this user
            shares = ProjectShare.query.filter_by(granted_by=user_id).all()
            count = len(shares)

            for share in shares:
                db.session.delete(share)

            # Also delete shares to this user
            user_shares = ProjectShare.query.filter_by(user_id=user_id).all()
            count += len(user_shares)

            for share in user_shares:
                db.session.delete(share)

            db.session.commit()
            logger.info(f"Deleted {count} project shares for user {user_id}")
            return count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting user shares: {e}")
            raise
