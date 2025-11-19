"""
Add ownership and metadata fields to MarkingScheme table.

Adds columns: owner_id, created_at, updated_at, is_shared, description

This is part of feature 005: Marking Schemes as Files
- Enables tracking scheme ownership for sharing
- Enables audit trail with timestamps
- Enables flagging shared schemes
"""

from alembic import op
import sqlalchemy as sa


revision = '005_marking_scheme_ownership'
down_revision = 'add_account_lockout_fields_to_users'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add columns to marking_scheme table.
    """
    with op.batch_operations.batch_alter_table('marking_scheme', schema=None) as batch_op:
        # Add owner_id column (nullable for backward compatibility)
        batch_op.add_column(sa.Column('owner_id', sa.String(36), sa.ForeignKey('user.id'), nullable=True))

        # Add created_at and updated_at timestamps
        batch_op.add_column(sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False))

        # Add is_shared flag
        batch_op.add_column(sa.Column('is_shared', sa.Boolean, server_default=sa.false(), nullable=False))

        # Add description column
        batch_op.add_column(sa.Column('description', sa.Text, nullable=True))

        # Create index on owner_id for faster queries
        batch_op.create_index('ix_marking_scheme_owner_id', ['owner_id'])


def downgrade():
    """
    Reverse: Remove ownership and metadata fields from marking_scheme table.
    """
    with op.batch_operations.batch_alter_table('marking_scheme', schema=None) as batch_op:
        batch_op.drop_index('ix_marking_scheme_owner_id')
        batch_op.drop_column('description')
        batch_op.drop_column('is_shared')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('owner_id')
