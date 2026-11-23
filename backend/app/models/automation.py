import uuid
import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Automation(Base, TimestampMixin):
    """
    Persistent automation definitions for recurring, scheduled, and reactive workflows.
    """
    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    natural_instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Trigger type: one_time, interval, daily, weekly, monthly, cron, manual
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, default="daily", index=True)

    # Schedule parameters in JSON (e.g. {"time": "08:00", "days": ["mon", "tue"]} or {"cron": "0 8 * * *"})
    schedule_config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Structured sequence of tool actions: [{"tool": "...", "arguments": {...}}]
    actions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    associated_tools: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Permission & approval requirements: inherit_tool_permissions, require_approval, auto_execute_safe
    approval_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="inherit_tool_permissions")

    next_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    owner_identity: Mapped[str] = mapped_column(String(64), nullable=False, default="personal_user")

    # Relationships
    executions: Mapped[List["AutomationExecution"]] = relationship(
        "AutomationExecution",
        back_populates="automation",
        cascade="all, delete-orphan",
        order_by="desc(AutomationExecution.created_at)",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="automation",
    )


class AutomationExecution(Base, TimestampMixin):
    """
    Historical execution record for each run of an automation.
    """
    __tablename__ = "automation_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    automation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("automations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True, index=True)

    # Status: SCHEDULED, QUEUED, RUNNING, WAITING_FOR_APPROVAL, SUCCEEDED, FAILED, CANCELLED, SKIPPED, TIMED_OUT
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)

    # Snapshots & execution payload
    actions_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    results_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pending or linked approval ID if waiting for approval
    approval_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tool_approvals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    automation: Mapped["Automation"] = relationship("Automation", back_populates="executions")


class IntegrationConnection(Base, TimestampMixin):
    """
    Configured third-party service connections (Google Workspace, GitHub, etc.)
    with Fernet-encrypted credentials.
    """
    __tablename__ = "integration_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Status: connected, disconnected, expired, error
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disconnected", index=True)

    requested_scopes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    granted_scopes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Symmetric encrypted JSON storing OAuth tokens (access_token, refresh_token, client_id, etc.)
    encrypted_credentials: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    last_successful_connection: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_identity: Mapped[str] = mapped_column(String(64), nullable=False, default="personal_user")

    sync_logs: Mapped[List["IntegrationSyncLog"]] = relationship(
        "IntegrationSyncLog",
        back_populates="connection",
        cascade="all, delete-orphan",
        order_by="desc(IntegrationSyncLog.created_at)",
    )


class IntegrationSyncLog(Base, TimestampMixin):
    """
    Audit and activity log of sync operations with external integrations.
    """
    __tablename__ = "integration_sync_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="succeeded", index=True)
    items_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    connection: Mapped["IntegrationConnection"] = relationship("IntegrationConnection", back_populates="sync_logs")


class Notification(Base, TimestampMixin):
    """
    Persistent internal notifications for completed runs, approvals, failures, and briefings.
    """
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # notification_type: automation_completed, automation_failed, automation_waiting_for_approval,
    # automation_skipped, integration_disconnected, oauth_authorization_required, morning_briefing_available, system_info
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="info")  # info, warning, error, success

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    automation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("automations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    execution_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("automation_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    automation: Mapped[Optional["Automation"]] = relationship("Automation", back_populates="notifications")


class Briefing(Base, TimestampMixin):
    """
    Generated personalized daily or periodic briefings (calendar, emails, tasks, status).
    """
    __tablename__ = "briefings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    briefing_type: Mapped[str] = mapped_column(String(32), nullable=False, default="morning", index=True)

    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    sections_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    generated_by_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    user_identity: Mapped[str] = mapped_column(String(64), nullable=False, default="personal_user")
