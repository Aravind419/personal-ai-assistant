from enum import Enum
import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    ONE_TIME = "one_time"
    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"
    MANUAL = "manual"


class ExecutionStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    TIMED_OUT = "TIMED_OUT"


class AutomationAction(BaseModel):
    tool: str = Field(..., description="Unique tool identifier registered in ToolRegistry")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to tool")
    description: Optional[str] = None


class AutomationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    natural_instruction: Optional[str] = None
    trigger_type: TriggerType = TriggerType.DAILY
    schedule_config: Dict[str, Any] = Field(default_factory=dict)
    timezone: str = "UTC"
    actions: List[AutomationAction] = Field(default_factory=list)
    associated_tools: Optional[List[str]] = None
    approval_policy: str = "inherit_tool_permissions"
    is_enabled: bool = True


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    natural_instruction: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    schedule_config: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None
    actions: Optional[List[AutomationAction]] = None
    associated_tools: Optional[List[str]] = None
    approval_policy: Optional[str] = None
    is_enabled: Optional[bool] = None


class AutomationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    natural_instruction: Optional[str] = None
    trigger_type: TriggerType
    schedule_config: Dict[str, Any]
    timezone: str
    is_enabled: bool
    actions: List[AutomationAction]
    associated_tools: List[str]
    approval_policy: str
    next_run_at: Optional[datetime.datetime] = None
    last_run_at: Optional[datetime.datetime] = None
    last_status: Optional[str] = None
    execution_count: int
    consecutive_failures: int
    owner_identity: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AutomationExecutionResponse(BaseModel):
    id: str
    automation_id: str
    trigger_type: str
    idempotency_key: Optional[str] = None
    status: ExecutionStatus
    actions_snapshot: List[Dict[str, Any]]
    results: Optional[List[Dict[str, Any]]] = None
    execution_context: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    approval_id: Optional[str] = None
    retry_count: int
    max_retries: int
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    duration_ms: Optional[float] = None
    worker_id: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ParseInstructionRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=1000)
    timezone: Optional[str] = None


class ParseInstructionResponse(BaseModel):
    success: bool
    name: str
    description: str
    natural_instruction: str
    trigger_type: TriggerType
    schedule_config: Dict[str, Any]
    timezone: str
    actions: List[AutomationAction]
    associated_tools: List[str]
    approval_policy: str
    validation_errors: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    confidence: float = 1.0


class ManualRunRequest(BaseModel):
    force_skip_approval: bool = False
    arguments_override: Optional[Dict[str, Any]] = None


class AutomationStatsResponse(BaseModel):
    total_automations: int
    active_automations: int
    paused_automations: int
    failed_executions: int
    next_scheduled_run: Optional[datetime.datetime] = None
    recent_executions_count: int
