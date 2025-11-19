"""
Create SchemeShare table for marking scheme sharing.

Represents sharing relationships between schemes and users/groups.
Supports three permission levels: VIEW_ONLY, EDITABLE, COPY

This is part of feature 005: Marking Schemes as Files
- Implements User Story 5: Share with Users
- Implements User Story 6: Share with Groups
- Web version only
"""

from alembic import op
import sqlalchemy as sa


revision = '006_create_scheme_share_table'
down_revision = '005_marking_scheme_ownership'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create scheme_share table with proper constraints and indexes.
    """
    op.create_table(
        'scheme_share',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('scheme_id', sa.String(36), sa.ForeignKey('marking_scheme.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=True),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('user_group.id', ondelete='CASCADE'), nullable=True),
        sa.Column('permission', sa.String(20), nullable=False),
        sa.Column('shared_by_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('shared_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('revoked_at', sa.DateTime, nullable=True),
        sa.Column('revoked_by_id', sa.String(36), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Constraints
    # Only one of user_id or group_id can be set (XOR constraint)
    op.execute(
        """
        ALTER TABLE scheme_share
        ADD CONSTRAINT check_user_or_group
        CHECK (
            (user_id IS NOT NULL AND group_id IS NULL) OR
            (user_id IS NULL AND group_id IS NOT NULL)
        )
        """
    )

    # Permission enum constraint
    op.execute(
        """
        ALTER TABLE scheme_share
        ADD CONSTRAINT check_permission
        CHECK (permission IN ('VIEW_ONLY', 'EDITABLE', 'COPY'))
        """
    )

    # Unique constraints (no duplicate shares)
    op.execute(
        """
        CREATE UNIQUE INDEX idx_scheme_user_unique
        ON scheme_share(scheme_id, user_id)
        WHERE user_id IS NOT NULL
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX idx_scheme_group_unique
        ON scheme_share(scheme_id, group_id)
        WHERE group_id IS NOT NULL
        """
    )

    # Regular indexes for queries
    op.create_index('idx_scheme_share_scheme', 'scheme_share', ['scheme_id'])
    op.create_index('idx_scheme_share_user', 'scheme_share', ['user_id'])
    op.create_index('idx_scheme_share_group', 'scheme_share', ['group_id'])
    op.create_index('idx_scheme_share_revoked', 'scheme_share', ['revoked_at'])
    op.create_index('idx_scheme_share_permission', 'scheme_share', ['permission'])


def downgrade():
    """
    Drop scheme_share table.
    """
    op.drop_table('scheme_share')
