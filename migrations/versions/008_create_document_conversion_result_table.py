"""
Create DocumentConversionResult table for in-progress conversions.

Transient storage for document conversion status and results.
Used for UI polling and result retrieval.

This is part of feature 005: Marking Schemes as Files
- Implements User Story 3: Document Upload & Convert
- Supports async Celery task processing and status polling
"""

from alembic import op
import sqlalchemy as sa


revision = '008_create_document_conversion_result_table'
down_revision = '007_create_document_upload_log_table'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create document_conversion_result table.
    """
    op.create_table(
        'document_conversion_result',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('upload_log_id', sa.String(36), sa.ForeignKey('document_upload_log.id', ondelete='CASCADE'), nullable=False, unique=True),

        # Status
        sa.Column('status', sa.String(20), nullable=False),

        # Results
        sa.Column('llm_response', sa.Text, nullable=True),  # Raw LLM output
        sa.Column('extracted_scheme', sa.JSON, nullable=True),  # Draft MarkingScheme object
        sa.Column('uncertainty_flags', sa.JSON, nullable=True),  # Array of confidence ratings

        # Errors
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )

    # Constraints
    op.execute(
        """
        ALTER TABLE document_conversion_result
        ADD CONSTRAINT check_status
        CHECK (status IN ('PENDING', 'QUEUED', 'PROCESSING', 'SUCCESS', 'FAILED'))
        """
    )

    # Indexes
    op.create_index('idx_result_status', 'document_conversion_result', ['status'])
    op.create_index('idx_result_completed', 'document_conversion_result', ['completed_at'])
    op.create_index('idx_result_upload_log', 'document_conversion_result', ['upload_log_id'])


def downgrade():
    """
    Drop document_conversion_result table.
    """
    op.drop_table('document_conversion_result')
