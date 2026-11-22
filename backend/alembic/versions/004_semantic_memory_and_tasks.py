"""Create memories and background_tasks tables with pgvector support

Revision ID: 004_semantic_memory_and_tasks
Revises: 003_model_policy_and_metrics
Create Date: 2026-11-22 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '004_semantic_memory_and_tasks'
down_revision: Union[str, None] = '003_model_policy_and_metrics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # 1. memories table
    op.create_table(
        'memories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='general'),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('source_conversation_id', sa.String(length=36), nullable=True),
        sa.Column('source_message_id', sa.String(length=36), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('embedding_model', sa.String(length=128), nullable=False, server_default='semantic-hash-384'),
        sa.Column('embedding_dim', sa.Integer(), nullable=False, server_default='384'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_conversation_id'], ['conversations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memories_category'), 'memories', ['category'], unique=False)
    op.create_index(op.f('ix_memories_importance'), 'memories', ['importance'], unique=False)
    op.create_index(op.f('ix_memories_is_archived'), 'memories', ['is_archived'], unique=False)
    op.create_index(op.f('ix_memories_source_conversation_id'), 'memories', ['source_conversation_id'], unique=False)
    op.create_index(op.f('ix_memories_source_message_id'), 'memories', ['source_message_id'], unique=False)
    op.create_index(op.f('ix_memories_created_at'), 'memories', ['created_at'], unique=False)

    # Add HNSW vector index in postgresql
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);"))

    # 2. background_tasks table
    op.create_table(
        'background_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('celery_task_id', sa.String(length=128), nullable=True),
        sa.Column('task_name', sa.String(length=128), nullable=False),
        sa.Column('task_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('input_params_json', sa.Text(), nullable=True),
        sa.Column('result_metadata_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_tasks_celery_task_id'), 'background_tasks', ['celery_task_id'], unique=False)
    op.create_index(op.f('ix_background_tasks_task_type'), 'background_tasks', ['task_type'], unique=False)
    op.create_index(op.f('ix_background_tasks_status'), 'background_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_background_tasks_created_at'), 'background_tasks', ['created_at'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS ix_memories_embedding;"))

    op.drop_index(op.f('ix_background_tasks_created_at'), table_name='background_tasks')
    op.drop_index(op.f('ix_background_tasks_status'), table_name='background_tasks')
    op.drop_index(op.f('ix_background_tasks_task_type'), table_name='background_tasks')
    op.drop_index(op.f('ix_background_tasks_celery_task_id'), table_name='background_tasks')
    op.drop_table('background_tasks')

    op.drop_index(op.f('ix_memories_created_at'), table_name='memories')
    op.drop_index(op.f('ix_memories_source_message_id'), table_name='memories')
    op.drop_index(op.f('ix_memories_source_conversation_id'), table_name='memories')
    op.drop_index(op.f('ix_memories_is_archived'), table_name='memories')
    op.drop_index(op.f('ix_memories_importance'), table_name='memories')
    op.drop_index(op.f('ix_memories_category'), table_name='memories')
    op.drop_table('memories')
