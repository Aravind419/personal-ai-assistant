import uuid
import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin


class ToolApproval(Base, TimestampMixin):
    """
    Human-in-the-loop approval requests for sensitive and critical actions.
    """
    __tablename__ = "tool_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Exact arguments in canonical JSON and its SHA-256 hash for tamper detection
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    arguments_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    target_resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_consequences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Permission & Risk classification
    permission_level: Mapped[str] = mapped_column(String(32), nullable=False, default="sensitive")  # safe, sensitive, critical
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")  # low, medium, high, critical
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    
    # State: pending, approved, rejected, expired, cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    execution_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    executions: Mapped[list["ToolExecution"]] = relationship(
        "ToolExecution",
        back_populates="approval",
        foreign_keys="ToolExecution.approval_id",
    )

    def is_expired(self) -> bool:
        now = datetime.datetime.now(datetime.timezone.utc)
        if self.expires_at.tzinfo is None:
            now = datetime.datetime.utcnow()
        return now > self.expires_at


class ToolExecution(Base, TimestampMixin):
    """
    Historical log of every tool execution with duration, status, and sanitized payloads.
    """
    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    requested_arguments: Mapped[str] = mapped_column(Text, nullable=False)
    validated_arguments: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status: pending, awaiting_approval, approved, running, succeeded, failed, rejected, cancelled, timed_out
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    
    approval_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tool_approvals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    user_identity: Mapped[str] = mapped_column(String(64), nullable=False, default="personal_user")
    execution_environment: Mapped[str] = mapped_column(String(32), nullable=False, default="builtin")  # builtin, mcp, external_api, custom

    approval: Mapped[Optional["ToolApproval"]] = relationship(
        "ToolApproval",
        back_populates="executions",
        foreign_keys=[approval_id],
    )


class McpServerConfiguration(Base, TimestampMixin):
    """
    Configuration and operational health status for Model Context Protocol (MCP) servers.
    """
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    server_type: Mapped[str] = mapped_column(String(32), nullable=False, default="stdio")  # stdio, sse, http
    
    command: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    args_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    headers_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    env_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disconnected")  # connected, disconnected, error, disabled
    last_health_check: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discovered_tools_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
