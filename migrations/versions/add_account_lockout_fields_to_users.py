"""Add account lockout fields to users table

Revision ID: account_lockout_001
Revises: 172aa1a4d8f3
Create Date: 2025-11-15 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'account_lockout_001'
down_revision = '172aa1a4d8f3'
branch_labels = None
depends_on = None


def upgrade():
    # Add account lockout fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))

    # Set default value for existing rows
    op.execute('UPDATE users SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL')


def downgrade():
    # Remove account lockout fields from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
