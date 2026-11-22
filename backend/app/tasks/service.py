import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.models import BackgroundTask
from app.tasks.schemas import (
    TaskStatus,
    TaskType,
    BackgroundTaskResponse,
    TaskListResponse,
    TaskStatsResponse,
)
from app.core.exceptions import ResourceNotFoundException, AppException
from app.core.logging import logger


def _to_task_response(task: BackgroundTask) -> BackgroundTaskResponse:
    parsed_input = None
    if task.input_params_json:
        try:
            parsed_input = json.loads(task.input_params_json)
        except Exception:
            parsed_input = None

    parsed_result = None
    if task.result_metadata_json:
        try:
            parsed_result = json.loads(task.result_metadata_json)
        except Exception:
            parsed_result = None

    # Sanitize error message to prevent leaking tracebacks or secrets
    clean_error = None
    if task.error_message:
        lines = task.error_message.strip().split("\n")
        clean_error = lines[-1][:300] if lines else None

    return BackgroundTaskResponse(
        id=task.id,
        celery_task_id=task.celery_task_id,
        task_name=task.task_name,
        task_type=task.task_type,
        status=task.status,
        input_params_json=task.input_params_json,
        input_params=parsed_input,
        result_metadata_json=task.result_metadata_json,
        result_metadata=parsed_result,
        error_message=clean_error,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        started_at=task.started_at,
        completed_at=task.completed_at,
        duration_ms=task.duration_ms,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


class TaskService:
    """
    Service layer for managing asynchronous background tasks and Celery task execution.
    """

    @classmethod
    async def create_and_dispatch_task(
        cls,
        session: AsyncSession,
        task_name: str,
        task_type: str,
        input_params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> BackgroundTaskResponse:
        input_json = json.dumps(input_params) if input_params else None

        task = BackgroundTask(
            task_name=task_name,
            task_type=task_type,
            status=TaskStatus.QUEUED.value,
            input_params_json=input_json,
            max_retries=max_retries,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        # Dispatch task to Celery or fallback to local async execution
        cls._dispatch_to_worker(task.id, task_type, input_params or {})

        return _to_task_response(task)

    @classmethod
    def _dispatch_to_worker(cls, db_task_id: str, task_type: str, input_params: Dict[str, Any]) -> None:
        try:
            from app.tasks.celery_app import (
                extract_memory_celery_task,
                reindex_embeddings_celery_task,
            )

            if task_type == TaskType.MEMORY_EXTRACTION.value:
                res = extract_memory_celery_task.delay(
                    db_task_id=db_task_id,
                    user_content=input_params.get("user_content", ""),
                    assistant_content=input_params.get("assistant_content", ""),
                    conversation_id=input_params.get("conversation_id"),
                    message_id=input_params.get("message_id"),
                )
                asyncio.create_task(cls._update_celery_task_id(db_task_id, res.id))
            elif task_type == TaskType.EMBEDDING_REINDEX.value:
                res = reindex_embeddings_celery_task.delay(db_task_id=db_task_id)
                asyncio.create_task(cls._update_celery_task_id(db_task_id, res.id))

        except Exception as exc:
            logger.warning(
                f"Celery queue dispatch not reachable ({exc}). Running task in local asynchronous fallback runtime."
            )
            asyncio.create_task(cls._execute_local_fallback(db_task_id, task_type, input_params))

    @classmethod
    async def _update_celery_task_id(cls, db_task_id: str, celery_id: str) -> None:
        try:
            from app.database.session import async_session_factory
            async with async_session_factory() as session:
                stmt = select(BackgroundTask).where(BackgroundTask.id == db_task_id)
                res = await session.execute(stmt)
                task = res.scalar_one_or_none()
                if task:
                    task.celery_task_id = celery_id
                    await session.commit()
        except Exception:
            pass

    @classmethod
    async def _execute_local_fallback(
        cls, db_task_id: str, task_type: str, input_params: Dict[str, Any]
    ) -> None:
        """Executes the task in local async loop if Celery worker is offline."""
        from app.database.session import async_session_factory
        from app.memory.extraction import extract_and_reconcile_memories

        start_time = time.perf_counter()
        async with async_session_factory() as session:
            stmt = select(BackgroundTask).where(BackgroundTask.id == db_task_id)
            res = await session.execute(stmt)
            task = res.scalar_one_or_none()
            if not task:
                return

            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.now(timezone.utc)
            await session.commit()

            try:
                if task_type == TaskType.MEMORY_EXTRACTION.value:
                    memories = await extract_and_reconcile_memories(
                        user_message=input_params.get("user_content", ""),
                        assistant_response=input_params.get("assistant_content", ""),
                        conversation_id=input_params.get("conversation_id"),
                        message_id=input_params.get("message_id"),
                        session=session,
                    )
                    task.status = TaskStatus.SUCCEEDED.value
                    task.completed_at = datetime.now(timezone.utc)
                    task.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    task.result_metadata_json = json.dumps({
                        "memories_extracted": len(memories),
                        "memory_ids": [m.id for m in memories],
                    })
                    await session.commit()
                else:
                    task.status = TaskStatus.SUCCEEDED.value
                    task.completed_at = datetime.now(timezone.utc)
                    task.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    await session.commit()
            except Exception as exc:
                task.status = TaskStatus.FAILED.value
                task.completed_at = datetime.now(timezone.utc)
                task.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                task.error_message = str(exc)
                await session.commit()

    @classmethod
    async def get_task(cls, session: AsyncSession, task_id: str) -> BackgroundTaskResponse:
        stmt = select(BackgroundTask).where(BackgroundTask.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise ResourceNotFoundException("BackgroundTask", task_id)
        return _to_task_response(task)

    @classmethod
    async def list_tasks(
        cls,
        session: AsyncSession,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TaskListResponse:
        filters = []
        if status and status.strip():
            filters.append(BackgroundTask.status == status.strip().lower())
        if task_type and task_type.strip():
            filters.append(BackgroundTask.task_type == task_type.strip().lower())

        count_stmt = select(func.count(BackgroundTask.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total_res = await session.execute(count_stmt)
        total = total_res.scalar() or 0

        items_stmt = select(BackgroundTask)
        if filters:
            items_stmt = items_stmt.where(and_(*filters))
        items_stmt = items_stmt.order_by(desc(BackgroundTask.created_at)).limit(limit).offset(offset)

        result = await session.execute(items_stmt)
        tasks = list(result.scalars().all())
        return TaskListResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            limit=limit,
            offset=offset,
        )

    @classmethod
    async def get_stats(cls, session: AsyncSession) -> TaskStatsResponse:
        stmt = select(BackgroundTask.status, func.count(BackgroundTask.id)).group_by(BackgroundTask.status)
        result = await session.execute(stmt)
        counts = {s: c for s, c in result.all()}

        total = sum(counts.values())
        return TaskStatsResponse(
            total=total,
            queued=counts.get(TaskStatus.QUEUED.value, 0),
            running=counts.get(TaskStatus.RUNNING.value, 0),
            succeeded=counts.get(TaskStatus.SUCCEEDED.value, 0),
            failed=counts.get(TaskStatus.FAILED.value, 0),
            cancelled=counts.get(TaskStatus.CANCELLED.value, 0),
        )

    @classmethod
    async def cancel_task(cls, session: AsyncSession, task_id: str) -> BackgroundTaskResponse:
        stmt = select(BackgroundTask).where(BackgroundTask.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise ResourceNotFoundException("BackgroundTask", task_id)

        if task.status in (TaskStatus.SUCCEEDED.value, TaskStatus.CANCELLED.value):
            raise AppException(f"Cannot cancel task in '{task.status}' state.")

        if task.celery_task_id:
            try:
                from app.tasks.celery_app import celery_app
                celery_app.control.revoke(task.celery_task_id, terminate=True)
            except Exception:
                pass

        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(task)
        return _to_task_response(task)

    @classmethod
    async def retry_task(cls, session: AsyncSession, task_id: str) -> BackgroundTaskResponse:
        stmt = select(BackgroundTask).where(BackgroundTask.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            raise ResourceNotFoundException("BackgroundTask", task_id)

        if task.status not in (TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            raise AppException(f"Only failed or cancelled tasks can be retried (current: '{task.status}').")

        input_params = {}
        if task.input_params_json:
            try:
                input_params = json.loads(task.input_params_json)
            except Exception:
                pass

        task.status = TaskStatus.QUEUED.value
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        task.duration_ms = None
        await session.commit()
        await session.refresh(task)

        cls._dispatch_to_worker(task.id, task.task_type, input_params)
        return _to_task_response(task)
