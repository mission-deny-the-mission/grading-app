"""
Create DocumentUploadLog table for audit trail.

Tracks all document upload and conversion requests with metadata.
Used for LLM provider tracking, status monitoring, and audit trail.

This is part of feature 005: Marking Schemes as Files
- Implements User Story 3: Document Upload & Convert
- Audit trail requirement from constitution
"""

from alembic import op
import sqlalchemy as sa


revision = '007_create_document_upload_log_table'
down_revision = '006_create_scheme_share_table'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create document_upload_log table.
    """
    op.create_table(
        'document_upload_log',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=True),  # SHA256
        sa.Column('upload_at', sa.DateTime, server_default=sa.func.now(), nullable=False),

        # LLM tracking
        sa.Column('llm_provider', sa.String(50), nullable=False),
        sa.Column('llm_model', sa.String(100), nullable=False),
        sa.Column('llm_request_tokens', sa.Integer, nullable=True),
        sa.Column('llm_response_tokens', sa.Integer, nullable=True),

        # Conversion status
        sa.Column('conversion_status', sa.String(20), nullable=False),
        sa.Column('conversion_time_ms', sa.Integer, nullable=True),

        # Results and errors
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('extracted_scheme_preview', sa.Text, nullable=True),
        sa.Column('uncertainty_flags', sa.Text, nullable=True),  # JSON

        # Metadata
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Constraints
    op.execute(
        """
        ALTER TABLE document_upload_log
        ADD CONSTRAINT check_conversion_status
        CHECK (conversion_status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED'))
        """
    )

    op.execute(
        """
        ALTER TABLE document_upload_log
        ADD CONSTRAINT check_file_size
        CHECK (file_size_bytes > 0 AND file_size_bytes < 52428800)
        """
    )

    # Indexes
    op.create_index('idx_user_upload', 'document_upload_log', ['user_id', 'upload_at'])
    op.create_index('idx_conversion_status', 'document_upload_log', ['conversion_status'])
    op.create_index('idx_upload_at', 'document_upload_log', ['upload_at'])
    op.create_index('idx_file_hash', 'document_upload_log', ['file_hash'])


def downgrade():
    """
    Drop document_upload_log table.
    """
    op.drop_table('document_upload_log')
