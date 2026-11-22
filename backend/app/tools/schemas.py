from enum import Enum
from typing import Dict, Any, Optional, List
import datetime
from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    SAFE = "safe"              # Level 1: Automatic execution under authorized permissions
    SENSITIVE = "sensitive"    # Level 2: Requires explicit user approval
    CRITICAL = "critical"      # Level 3: Requires explicit action-specific confirmation


class ToolCategory(str, Enum):
    SYSTEM = "system"
    MATH = "math"
    TEXT = "text"
    FILE = "file"
    WEB = "web"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    DEVELOPER = "developer"
    DATABASE = "database"
    MCP = "mcp"
    CUSTOM = "custom"


class ExecutionEnvironment(str, Enum):
    BUILTIN = "builtin"
    MCP = "mcp"
    EXTERNAL_API = "external_api"
    CUSTOM = "custom"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


# Tool Definition Schemas
class ToolDefinitionResponse(BaseModel):
    id: str
    name: str
    description: str
    category: ToolCategory
    parameters_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    permission_level: PermissionLevel
    risk_classification: str
    timeout_seconds: float
    requires_approval: bool
    is_enabled: bool
    execution_environment: ExecutionEnvironment
    availability_status: str


# Execution Request & Response
class ToolExecuteRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    force_skip_approval: bool = False  # For automated test or authorized service execution


class ToolExecutionResponse(BaseModel):
    id: str
    tool_id: str
    tool_name: str
    status: ExecutionStatus
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    approval_id: Optional[str] = None
    approval_required: bool = False
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None


class ToolExecutionSummary(BaseModel):
    id: str
    conversation_id: Optional[str] = None
    tool_id: str
    tool_name: str
    requested_arguments: Dict[str, Any]
    status: ExecutionStatus
    approval_id: Optional[str] = None
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    duration_ms: Optional[float] = None
    result_summary: Optional[str] = None
    error_details: Optional[str] = None
    user_identity: str
    execution_environment: str


# Approval Schemas
class ApprovalResponse(BaseModel):
    id: str
    conversation_id: Optional[str] = None
    tool_id: str
    tool_name: str
    action: str
    arguments: Dict[str, Any]
    arguments_hash: str
    target_resource: Optional[str] = None
    expected_consequences: Optional[str] = None
    permission_level: PermissionLevel
    risk_level: str
    reason: str
    status: ApprovalStatus
    requested_by: str = "personal_user"
    created_at: datetime.datetime
    expires_at: datetime.datetime
    decided_at: Optional[datetime.datetime] = None
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None
    execution_id: Optional[str] = None
    is_executed: bool = False
    executed_at: Optional[datetime.datetime] = None


class ApprovalDecisionRequest(BaseModel):
    reason: Optional[str] = None
    execute_now: bool = True
    confirm_critical: bool = False
    decided_by: str = "personal_user"


# MCP Server Schemas
class McpServerCreate(BaseModel):
    name: str
    server_type: str = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    is_enabled: bool = True


class McpServerUpdate(BaseModel):
    name: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    is_enabled: Optional[bool] = None


class McpServerResponse(BaseModel):
    id: str
    name: str
    server_type: str
    command: Optional[str] = None
    url: Optional[str] = None
    is_enabled: bool
    status: str
    last_health_check: Optional[datetime.datetime] = None
    last_error: Optional[str] = None
    discovered_tools_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
