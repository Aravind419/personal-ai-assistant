"""Add tool approvals, tool executions, and MCP servers

Revision ID: 006_tool_execution_and_approvals
Revises: 005_intelligent_memory_attrs
Create Date: 2026-11-22 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_tool_execution_and_approvals'
down_revision: Union[str, None] = '005_intelligent_memory_attrs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tool_approvals table
    op.create_table(
        'tool_approvals',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('conversation_id', sa.String(length=36), sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tool_id', sa.String(length=128), nullable=False),
        sa.Column('tool_name', sa.String(length=128), nullable=False),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('arguments_json', sa.Text(), nullable=False),
        sa.Column('arguments_hash', sa.String(length=64), nullable=False),
        sa.Column('target_resource', sa.String(length=255), nullable=True),
        sa.Column('expected_consequences', sa.Text(), nullable=True),
        sa.Column('permission_level', sa.String(length=32), nullable=False, server_default='sensitive'),
        sa.Column('risk_level', sa.String(length=32), nullable=False, server_default='medium'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', sa.String(length=64), nullable=True),
        sa.Column('decision_reason', sa.Text(), nullable=True),
        sa.Column('execution_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_tool_approvals_conversation_id'), 'tool_approvals', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_tool_approvals_tool_id'), 'tool_approvals', ['tool_id'], unique=False)
    op.create_index(op.f('ix_tool_approvals_arguments_hash'), 'tool_approvals', ['arguments_hash'], unique=False)
    op.create_index(op.f('ix_tool_approvals_status'), 'tool_approvals', ['status'], unique=False)

    # 2. tool_executions table
    op.create_table(
        'tool_executions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('conversation_id', sa.String(length=36), sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tool_id', sa.String(length=128), nullable=False),
        sa.Column('tool_name', sa.String(length=128), nullable=False),
        sa.Column('requested_arguments', sa.Text(), nullable=False),
        sa.Column('validated_arguments', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('approval_id', sa.String(length=36), sa.ForeignKey('tool_approvals.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('user_identity', sa.String(length=64), nullable=False, server_default='personal_user'),
        sa.Column('execution_environment', sa.String(length=32), nullable=False, server_default='builtin'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_tool_executions_conversation_id'), 'tool_executions', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_tool_executions_tool_id'), 'tool_executions', ['tool_id'], unique=False)
    op.create_index(op.f('ix_tool_executions_status'), 'tool_executions', ['status'], unique=False)
    op.create_index(op.f('ix_tool_executions_approval_id'), 'tool_executions', ['approval_id'], unique=False)
    op.create_index(op.f('ix_tool_executions_idempotency_key'), 'tool_executions', ['idempotency_key'], unique=False)

    # 3. mcp_servers table
    op.create_table(
        'mcp_servers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=128), unique=True, nullable=False),
        sa.Column('server_type', sa.String(length=32), nullable=False, server_default='stdio'),
        sa.Column('command', sa.String(length=255), nullable=True),
        sa.Column('args_json', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=512), nullable=True),
        sa.Column('headers_json', sa.Text(), nullable=True),
        sa.Column('env_json', sa.Text(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='disconnected'),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('discovered_tools_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('mcp_servers')
    op.drop_table('tool_executions')
    op.drop_table('tool_approvals')
