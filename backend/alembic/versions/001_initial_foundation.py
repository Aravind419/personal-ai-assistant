"""Initial foundation migration

Revision ID: 001_initial_foundation
Revises: 
Create Date: 2026-11-22 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_foundation'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely enable pgvector extension if supported on PostgreSQL instance
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # Initial foundation metadata table
    op.create_table(
        'system_metadata',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index(op.f('ix_system_metadata_key'), 'system_metadata', ['key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_system_metadata_key'), table_name='system_metadata')
    op.drop_table('system_metadata')
