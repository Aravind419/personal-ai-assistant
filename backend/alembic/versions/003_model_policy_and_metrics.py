"""Create ai_model_policies and model_execution_metrics tables

Revision ID: 003_model_policy_and_metrics
Revises: 002_conversations_and_providers
Create Date: 2026-11-22 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_model_policy_and_metrics'
down_revision: Union[str, None] = '002_conversations_and_providers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ai_model_policies
    op.create_table(
        'ai_model_policies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('model_mode', sa.String(length=32), nullable=False, server_default='free_only'),
        sa.Column('selected_model', sa.String(length=128), nullable=False, server_default='meta-llama/llama-3.3-70b-instruct:free'),
        sa.Column('fallback_models_json', sa.Text(), nullable=False, server_default='["google/gemini-2.0-flash-exp:free", "deepseek/deepseek-chat:free", "qwen/qwen-2.5-coder-32b-instruct:free"]'),
        sa.Column('enable_fallback', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_cost_per_request', sa.Float(), nullable=False, server_default='0.05'),
        sa.Column('monthly_budget_limit', sa.Float(), nullable=False, server_default='10.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. model_execution_metrics
    op.create_table(
        'model_execution_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=True),
        sa.Column('provider_type', sa.String(length=64), nullable=False),
        sa.Column('model_id', sa.String(length=128), nullable=False),
        sa.Column('pricing_category', sa.String(length=32), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('error_type', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_execution_metrics_conversation_id'), 'model_execution_metrics', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_model_execution_metrics_provider_type'), 'model_execution_metrics', ['provider_type'], unique=False)
    op.create_index(op.f('ix_model_execution_metrics_model_id'), 'model_execution_metrics', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_execution_metrics_created_at'), 'model_execution_metrics', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_execution_metrics_created_at'), table_name='model_execution_metrics')
    op.drop_index(op.f('ix_model_execution_metrics_model_id'), table_name='model_execution_metrics')
    op.drop_index(op.f('ix_model_execution_metrics_provider_type'), table_name='model_execution_metrics')
    op.drop_index(op.f('ix_model_execution_metrics_conversation_id'), table_name='model_execution_metrics')
    op.drop_table('model_execution_metrics')
    op.drop_table('ai_model_policies')
