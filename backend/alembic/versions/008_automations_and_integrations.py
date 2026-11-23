"""Phase 4 Automations, Integrations, Notifications, and Briefings

Revision ID: 008_automations_and_integrations
Revises: 007_approval_security_hardening
Create Date: 2026-11-22 22:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_automations_and_integrations'
down_revision: Union[str, None] = '007_approval_security_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. automations table
    op.create_table(
        'automations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('natural_instruction', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(length=32), nullable=False, server_default='daily'),
        sa.Column('schedule_config', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('actions_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('associated_tools', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('approval_policy', sa.String(length=32), nullable=False, server_default='inherit_tool_permissions'),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', sa.String(length=32), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('owner_identity', sa.String(length=64), nullable=False, server_default='personal_user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automations_name'), 'automations', ['name'], unique=False)
    op.create_index(op.f('ix_automations_trigger_type'), 'automations', ['trigger_type'], unique=False)
    op.create_index(op.f('ix_automations_is_enabled'), 'automations', ['is_enabled'], unique=False)
    op.create_index(op.f('ix_automations_next_run_at'), 'automations', ['next_run_at'], unique=False)

    # 2. automation_executions table
    op.create_table(
        'automation_executions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('automation_id', sa.String(length=36), nullable=False),
        sa.Column('trigger_type', sa.String(length=32), nullable=False, server_default='scheduled'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('actions_snapshot', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('results_json', sa.Text(), nullable=True),
        sa.Column('execution_context', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('approval_id', sa.String(length=36), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('worker_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['automation_id'], ['automations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approval_id'], ['tool_approvals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_executions_automation_id'), 'automation_executions', ['automation_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_status'), 'automation_executions', ['status'], unique=False)
    op.create_index(op.f('ix_automation_executions_idempotency_key'), 'automation_executions', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_automation_executions_approval_id'), 'automation_executions', ['approval_id'], unique=False)

    # 3. integration_connections table
    op.create_table(
        'integration_connections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('provider_id', sa.String(length=64), nullable=False),
        sa.Column('provider_name', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='disconnected'),
        sa.Column('requested_scopes', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('granted_scopes', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('encrypted_credentials', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_successful_connection', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('user_identity', sa.String(length=64), nullable=False, server_default='personal_user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_connections_provider_id'), 'integration_connections', ['provider_id'], unique=True)
    op.create_index(op.f('ix_integration_connections_status'), 'integration_connections', ['status'], unique=False)

    # 4. integration_sync_logs table
    op.create_table(
        'integration_sync_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('connection_id', sa.String(length=36), nullable=False),
        sa.Column('service_name', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='succeeded'),
        sa.Column('items_synced', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['connection_id'], ['integration_connections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_sync_logs_connection_id'), 'integration_sync_logs', ['connection_id'], unique=False)
    op.create_index(op.f('ix_integration_sync_logs_service_name'), 'integration_sync_logs', ['service_name'], unique=False)
    op.create_index(op.f('ix_integration_sync_logs_status'), 'integration_sync_logs', ['status'], unique=False)

    # 5. notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default='info'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('automation_id', sa.String(length=36), nullable=True),
        sa.Column('execution_id', sa.String(length=36), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['automation_id'], ['automations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['execution_id'], ['automation_executions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_is_dismissed'), 'notifications', ['is_dismissed'], unique=False)
    op.create_index(op.f('ix_notifications_automation_id'), 'notifications', ['automation_id'], unique=False)
    op.create_index(op.f('ix_notifications_execution_id'), 'notifications', ['execution_id'], unique=False)

    # 6. briefings table
    op.create_table(
        'briefings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('briefing_type', sa.String(length=32), nullable=False, server_default='morning'),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('sections_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('generated_by_model', sa.String(length=128), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('user_identity', sa.String(length=64), nullable=False, server_default='personal_user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_briefings_briefing_type'), 'briefings', ['briefing_type'], unique=False)


def downgrade() -> None:
    op.drop_table('briefings')
    op.drop_table('notifications')
    op.drop_table('integration_sync_logs')
    op.drop_table('integration_connections')
    op.drop_table('automation_executions')
    op.drop_table('automations')
