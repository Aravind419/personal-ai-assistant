from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.tasks.schemas import (
    BackgroundTaskResponse,
    TaskListResponse,
    TaskStatsResponse,
    WorkerHealthResponse,
    SweepStaleTasksResponse,
)
from app.tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    search: Optional[str] = Query(None, description="Search term matching task name or ID"),
    sort_by: Optional[str] = Query("created_desc", description="Sort order: created_desc, created_asc, duration_desc, duration_asc"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List asynchronous background tasks with pagination, search, and status filters."""
    return await TaskService.list_tasks(
        session=db,
        status=status,
        task_type=task_type,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )


@router.get("/health", response_model=WorkerHealthResponse)
async def get_worker_health(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve live Redis broker connection status and Celery worker health."""
    return await TaskService.get_worker_health(db)


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve execution metrics, status counts, and queue wait times for background tasks."""
    return await TaskService.get_stats(db)


@router.post("/sweep-stale", response_model=SweepStaleTasksResponse)
async def sweep_stale_tasks(
    max_stale_seconds: int = Query(10, ge=0, description="Process tasks queued longer than this threshold in seconds"),
    db: AsyncSession = Depends(get_db),
):
    """Sweeps and processes queued tasks that have remained unconsumed."""
    return await TaskService.sweep_stale_tasks(db, max_stale_seconds=max_stale_seconds)


@router.get("/{task_id}", response_model=BackgroundTaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details, execution duration, and metadata for a specific task."""
    return await TaskService.get_task(db, task_id)


@router.post("/{task_id}/retry", response_model=BackgroundTaskResponse)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retry an eligible failed or cancelled background task."""
    return await TaskService.retry_task(db, task_id)


@router.post("/{task_id}/cancel", response_model=BackgroundTaskResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active or queued background task."""
    return await TaskService.cancel_task(db, task_id)
