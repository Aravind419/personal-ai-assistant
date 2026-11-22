from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    MEMORY_EXTRACTION = "memory_extraction"
    EMBEDDING_REINDEX = "embedding_reindex"
    SYSTEM_MAINTENANCE = "system_maintenance"


class BackgroundTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    celery_task_id: Optional[str] = None
    task_name: str
    task_type: str
    status: str
    input_params_json: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    result_metadata_json: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    # Extended telemetry & source inspectability
    source_conversation_id: Optional[str] = None
    source_conversation_title: Optional[str] = None
    source_message_id: Optional[str] = None
    execution_mode: Optional[str] = None
    worker_id: Optional[str] = None
    queue_wait_ms: Optional[float] = None


class TaskListResponse(BaseModel):
    items: List[BackgroundTaskResponse]
    total: int
    limit: int
    offset: int


class TaskStatsResponse(BaseModel):
    total: int
    queued: int
    running: int
    succeeded: int
    failed: int
    cancelled: int
    oldest_queued_wait_seconds: Optional[float] = None
    average_wait_seconds: Optional[float] = None
    stale_queued_count: int = 0


class WorkerHealthResponse(BaseModel):
    redis_connected: bool
    redis_latency_ms: Optional[float] = None
    celery_online: bool
    worker_count: int = 0
    active_workers: List[str] = []
    registered_task_types: List[str] = []
    active_tasks_count: int = 0
    reserved_tasks_count: int = 0
    last_heartbeat: Optional[datetime] = None
    last_successful_task: Optional[Dict[str, Any]] = None


class SweepStaleTasksResponse(BaseModel):
    swept_count: int
    task_ids: List[str]
    message: str
