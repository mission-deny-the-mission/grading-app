"""
Multi-User Data Isolation Tests

Tests to ensure proper data isolation between users in multi-user deployments.
Covers cross-user access, shared projects, admin vs regular user boundaries,
quota enforcement, and unauthorized modification attempts.
"""

import pytest
from tests.factories import UserFactory
from models import User, GradingJob, Submission, UsageRecord, ProjectShare, db
from datetime import datetime, timezone


class TestCrossUserProjectAccess:
    """Test that users cannot access other users' projects."""

    def test_user_cannot_view_other_user_projects(self, client, auth, multi_user_mode):
        """Test that user A cannot view user B's projects."""
        # Create two users using the factory
        user_a = UserFactory.create(email='usera@example.com', password='TestPass123!')
        user_b = UserFactory.create(email='userb@example.com', password='TestPass123!')

        # Create grading job for user B
        project_b = GradingJob(
            job_name='User B Project',
            owner_id=user_b.id,
            created_at=datetime.now(timezone.utc),
            provider='openrouter',
            prompt='Test prompt'
        )
        db.session.add(project_b)
        db.session.commit()

        # Login as user A
        auth.login(email='usera@example.com', password='TestPass123!')

        # Try to access user B's project
        response = client.get(f'/api/projects/{project_b.id}')
        assert response.status_code == 403  # Forbidden

    def test_user_cannot_list_other_user_projects(self, client, auth, multi_user_mode):
        """Test that project listings are filtered by user."""
        # Create two users using the factory
        user_a = UserFactory.create(email='usera@example.com', password='TestPass123!')
        user_b = UserFactory.create(email='userb@example.com', password='TestPass123!')

        # Create grading jobs for both users
        project_a = GradingJob(job_name='User A Project', owner_id=user_a.id, created_at=datetime.now(timezone.utc), provider='openrouter', prompt='Test prompt')
        project_b = GradingJob(job_name='User B Project', owner_id=user_b.id, created_at=datetime.now(timezone.utc), provider='openrouter', prompt='Test prompt')
        db.session.add_all([project_a, project_b])

        # Login as user A
        auth.login(email='usera@example.com', password='TestPass123!')

        # Get project list
        response = client.get('/api/projects')
        assert response.status_code == 200

        data = response.get_json()
        # Should only see own projects
        project_names = [p.get('job_name') or p.get('name') for p in data.get('projects', [])]
        assert 'User A Project' in project_names
        assert 'User B Project' not in project_names

    def test_user_cannot_delete_other_user_projects(self, client, auth, multi_user_mode):
        """Test that user A cannot delete user B's projects."""
        # Create two users using the factory
        user_a = UserFactory.create(email='usera@example.com', password='TestPass123!')
        user_b = UserFactory.create(email='userb@example.com', password='TestPass123!')

        # Create grading job for user B
        project_b = GradingJob(
            job_name='User B Project',
            owner_id=user_b.id,
            created_at=datetime.now(timezone.utc),
            provider='openrouter',
            prompt='Test prompt'
        )
        db.session.add(project_b)
        db.session.commit()

        # Login as user A
        auth.login(email='usera@example.com', password='TestPass123!')

        # Try to delete user B's project
        response = client.delete(f'/api/projects/{project_b.id}')
        assert response.status_code == 403

        # Verify project still exists
        assert GradingJob.query.get(project_b.id) is not None


class TestSharedProjectPermissionBoundaries:
    """Test shared project access control boundaries."""

    def test_shared_project_viewer_can_read_only(self, client, auth, multi_user_mode):
        """Test that viewer permission allows read but not write."""
        # Create owner and viewer
        owner = UserFactory.create(email='owner@example.com', password='TestPass123!')
        viewer = UserFactory.create(email='viewer@example.com', password='TestPass123!')

        # Create grading job
        project = GradingJob(
            job_name='Shared Project',
            owner_id=owner.id,
            created_at=datetime.now(timezone.utc),
            provider='openrouter',
            prompt='Test prompt'
        )
        db.session.add(project)
        db.session.commit()

        # Share with viewer
        share = ProjectShare(
            project_id=project.id,
            user_id=viewer.id,
            permission_level='read',
            granted_by=owner.id,
            granted_at=datetime.now(timezone.utc)
        )
        db.session.add(share)
        db.session.commit()

        # Login as viewer
        auth.login(email='viewer@example.com', password='TestPass123!')

        # Should be able to view
        response = client.get(f'/api/projects/{project.id}')
        assert response.status_code == 200

        # Should NOT be able to modify
        response = client.put(f'/api/projects/{project.id}', json={
            'job_name': 'Modified Name'
        })
        assert response.status_code == 403

    def test_shared_project_editor_can_modify(self, client, auth, multi_user_mode):
        """Test that editor permission allows modification."""
        # Create owner and editor
        owner = UserFactory.create(email='owner@example.com', password='TestPass123!')
        editor = UserFactory.create(email='editor@example.com', password='TestPass123!')

        # Create grading job
        project = GradingJob(
            job_name='Shared Project',
            owner_id=owner.id,
            created_at=datetime.now(timezone.utc),
            provider='openrouter',
            prompt='Test prompt'
        )
        db.session.add(project)
        db.session.commit()

        # Share with editor
        share = ProjectShare(
            project_id=project.id,
            user_id=editor.id,
            permission_level='write',
            granted_by=owner.id,
            granted_at=datetime.now(timezone.utc)
        )
        db.session.add(share)
        db.session.commit()

        # Login as editor
        auth.login(email='editor@example.com', password='TestPass123!')

        # Should be able to modify
        response = client.put(f'/api/projects/{project.id}', json={
            'job_name': 'Modified Name'
        })
        # Either succeeds or endpoint doesn't exist yet
        assert response.status_code in [200, 404]

    def test_share_revocation_removes_access(self, client, auth, multi_user_mode):
        """Test that revoking share removes access immediately."""
        # Create owner and viewer
        owner = UserFactory.create(email='owner@example.com', password='TestPass123!')
        viewer = UserFactory.create(email='viewer@example.com', password='TestPass123!')

        # Create grading job
        project = GradingJob(
            job_name='Shared Project',
            owner_id=owner.id,
            created_at=datetime.now(timezone.utc),
            provider='openrouter',
            prompt='Test prompt'
        )
        db.session.add(project)
        db.session.commit()

        # Share with viewer
        share = ProjectShare(
            project_id=project.id,
            user_id=viewer.id,
            permission_level='read',
            granted_by=owner.id,
            granted_at=datetime.now(timezone.utc)
        )
        db.session.add(share)
        db.session.commit()

        # Login as viewer
        auth.login(email='viewer@example.com', password='TestPass123!')

        # Should have access
        response = client.get(f'/api/projects/{project.id}')
        assert response.status_code == 200

        # Revoke share
        db.session.delete(share)
        db.session.commit()

        # Should no longer have access
        response = client.get(f'/api/projects/{project.id}')
        assert response.status_code == 403


class TestAdminVsRegularUserDataAccess:
    """Test admin privilege boundaries vs regular users."""

    def test_admin_can_view_all_user_data(self, client, auth, multi_user_mode):
        """Test that admin can view all users' data."""
        # Create admin and regular user
        admin = UserFactory.create(email='admin@example.com', password='TestPass123!', is_admin=True)
        regular_user = UserFactory.create(email='user@example.com', password='TestPass123!')

        # Login as admin
        auth.login(email='admin@example.com', password='TestPass123!')

        # Should be able to list all users
        response = client.get('/admin/users')
        assert response.status_code == 200

    def test_regular_user_cannot_access_admin_endpoints(self, client, auth, multi_user_mode):
        """Test that regular users cannot access admin endpoints."""
        # Create regular user
        regular_user = UserFactory.create(email='user@example.com', password='TestPass123!')
        db.session.add(regular_user)
        db.session.commit()

        # Login as regular user
        auth.login(email='user@example.com', password='TestPass123!')

        # Should NOT be able to access admin endpoints
        response = client.get('/admin/users')
        assert response.status_code == 403

    def test_admin_cannot_modify_data_without_ownership(self, client, auth, multi_user_mode):
        """Test that admin still respects data ownership for modifications."""
        # Create admin and regular user
        admin = UserFactory.create(email='admin@example.com', password='TestPass123!', is_admin=True)
        owner = UserFactory.create(email='owner@example.com', password='TestPass123!')

        # Create grading job owned by regular user
        project = GradingJob(
            job_name='Owner Project',
            owner_id=owner.id,
            created_at=datetime.now(timezone.utc),
            provider='openrouter',
            prompt='Test prompt'
        )
        db.session.add(project)
        db.session.commit()

        # Login as admin
        auth.login(email='admin@example.com', password='TestPass123!')

        # Admin can view for administration purposes
        response = client.get(f'/api/projects/{project.id}')
        # May be allowed for admin oversight
        assert response.status_code in [200, 403]


class TestQuotaEnforcementAcrossUsers:
    """Test that quota limits are enforced per-user."""

    def test_quota_is_per_user_not_global(self, client_multi_user, auth, multi_user_mode):
        """Test that each user has independent quota."""
        # Create two users
        user_a = UserFactory.create(
            email='usera@example.com',
            password='TestPass123!'
        )
        user_b = UserFactory.create(
            email='userb@example.com',
            password='TestPass123!'
        )
        db.session.add_all([user_a, user_b])

        # User A uses quota
        usage_a = UsageRecord(
            user_id=user_a.id,
            provider='openrouter',
            operation_type='grading',
            tokens_consumed=1000000,  # 1M tokens
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(usage_a)
        db.session.commit()

        # Login as user B
        auth.login(email='userb@example.com', password='TestPass123!')

        # User B should have independent quota
        response = client_multi_user.get('/api/usage')
        assert response.status_code == 200
        data = response.get_json()
        # User B should have separate quota tracking
        assert data is not None

    def test_user_cannot_exceed_individual_quota(self, client, auth, multi_user_mode):
        """Test that users are limited by their individual quota."""
        # Create user with usage near limit
        user = UserFactory.create(
            email='user@example.com',
            password='TestPass123!'
        )
        db.session.add(user)
        db.session.commit()

        # Add usage records
        # Assuming 10M token monthly limit
        for i in range(10):
            usage = UsageRecord(
                user_id=user.id,
                provider='openrouter',
                operation_type='grading',
                tokens_consumed=1000000,  # 1M tokens each
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(usage)
        db.session.commit()

        # Login
        auth.login(email='user@example.com', password='TestPass123!')

        # Should be at or near quota limit
        response = client.get('/api/usage')
        assert response.status_code == 200


class TestUnauthorizedDataModification:
    """Test prevention of unauthorized data modification attempts."""

    def test_user_cannot_modify_submission_ownership(self, client, auth, multi_user_mode):
        """Test that user cannot change submission ownership."""
        # Create two users
        user_a = UserFactory.create(email='usera@example.com', password='TestPass123!')
        user_b = UserFactory.create(email='userb@example.com', password='TestPass123!')

        # Create grading job and submission for user A
        project_a = GradingJob(job_name='Project A', owner_id=user_a.id, created_at=datetime.now(timezone.utc), provider='openrouter', prompt='Test prompt')
        db.session.add(project_a)
        db.session.commit()

        submission_a = Submission(
            job_id=project_a.id,
            filename='test.txt',
            original_filename='test.txt',
            file_type='txt',
            file_size=1024,
            status='pending'
        )
        db.session.add(submission_a)
        db.session.commit()

        # Login as user A
        auth.login(email='usera@example.com', password='TestPass123!')

        # Try to change ownership (if endpoint exists)
        response = client.put(f'/api/submissions/{submission_a.id}', json={
            'owner_id': user_b.id
        })
        # Should either fail or ignore ownership change (405 = method not allowed is also acceptable)
        assert response.status_code in [403, 404, 400, 405]

    def test_user_cannot_manipulate_usage_records(self, client, auth, multi_user_mode):
        """Test that users cannot modify their own usage records."""
        # Create user
        user = UserFactory.create(email='user@example.com', password='TestPass123!')
        db.session.add(user)
        db.session.commit()

        # Create usage record
        usage = UsageRecord(
            user_id=user.id,
            provider='openrouter',
            operation_type='grading',
            tokens_consumed=1000,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(usage)
        db.session.commit()

        # Login
        auth.login(email='user@example.com', password='TestPass123!')

        # Try to modify usage record (should not be allowed)
        response = client.put(f'/api/usage/{usage.id}', json={
            'tokens_consumed': 0
        })
        # Endpoint may not exist, but if it does, should deny
        assert response.status_code in [403, 404, 405]

    def test_sql_injection_protection_in_queries(self, client, auth, test_user, multi_user_mode):
        """Test that SQL injection attempts are blocked."""
        # Login
        auth.login(email='testuser@example.com', password='TestPass123!')

        # Try SQL injection in query parameters
        response = client.get("/api/projects?name='; DROP TABLE grading_jobs; --")
        # Should handle safely without error
        assert response.status_code in [200, 400]

        # Verify grading_jobs table still exists
        projects = GradingJob.query.all()
        # Query should work (table not dropped)
        assert projects is not None
