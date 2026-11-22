"""Add requested_by and execution tracking to tool_approvals

Revision ID: 007_approval_security_hardening
Revises: 006_tool_execution_and_approvals
Create Date: 2026-11-22 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_approval_security_hardening'
down_revision: Union[str, None] = '006_tool_execution_and_approvals'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tool_approvals', sa.Column('requested_by', sa.String(length=64), server_default='personal_user', nullable=False))
    op.add_column('tool_approvals', sa.Column('is_executed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('tool_approvals', sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_tool_approvals_is_executed'), 'tool_approvals', ['is_executed'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tool_approvals_is_executed'), table_name='tool_approvals')
    op.drop_column('tool_approvals', 'executed_at')
    op.drop_column('tool_approvals', 'is_executed')
    op.drop_column('tool_approvals', 'requested_by')
