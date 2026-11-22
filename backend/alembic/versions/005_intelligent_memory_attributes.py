"""Add intelligent memory attributes: subcategory, temporal_scope, valid_from, valid_until, is_current, original_statement

Revision ID: 005_intelligent_memory_attrs
Revises: 004_semantic_memory_and_tasks
Create Date: 2026-11-22 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_intelligent_memory_attrs'
down_revision: Union[str, None] = '004_semantic_memory_and_tasks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new intelligent attributes with safe server defaults
    op.add_column('memories', sa.Column('subcategory', sa.String(length=64), nullable=True))
    op.add_column('memories', sa.Column('temporal_scope', sa.String(length=32), nullable=False, server_default='permanent'))
    op.add_column('memories', sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True))
    op.add_column('memories', sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('memories', sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('memories', sa.Column('original_statement', sa.Text(), nullable=True))

    # Add indexes for query and temporal filtering
    op.create_index(op.f('ix_memories_subcategory'), 'memories', ['subcategory'], unique=False)
    op.create_index(op.f('ix_memories_temporal_scope'), 'memories', ['temporal_scope'], unique=False)
    op.create_index(op.f('ix_memories_is_current'), 'memories', ['is_current'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_memories_is_current'), table_name='memories')
    op.drop_index(op.f('ix_memories_temporal_scope'), table_name='memories')
    op.drop_index(op.f('ix_memories_subcategory'), table_name='memories')
    op.drop_column('memories', 'original_statement')
    op.drop_column('memories', 'is_current')
    op.drop_column('memories', 'valid_until')
    op.drop_column('memories', 'valid_from')
    op.drop_column('memories', 'temporal_scope')
    op.drop_column('memories', 'subcategory')
