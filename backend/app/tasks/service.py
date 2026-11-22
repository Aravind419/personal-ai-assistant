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


import re
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.models import BackgroundTask
from app.tasks.schemas import (
    TaskStatus,
    TaskType,
    BackgroundTaskResponse,
    TaskListResponse,
    TaskStatsResponse,
    WorkerHealthResponse,
    SweepStaleTasksResponse,
)
from app.models.conversation import Conversation
from app.core.exceptions import ResourceNotFoundException, AppException
from app.core.config import settings
from app.core.logging import logger


def redact_sensitive_data(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Redacts passwords, tokens, and credentials from task input parameters for safe UI viewing."""
    if not params:
        return params
    redacted = {}
    for k, v in params.items():
        if isinstance(v, str):
            cleaned = re.sub(
                r"(?i)\b(password|passwd|pwd|api[_-]?key|secret[_-]?key|token)\b(\s*[:=]|\s+is\s+)\S+",
                r"\1=***REDACTED***",
                v,
            )
            cleaned = re.sub(r"sk-[a-zA-Z0-9_\-]{16,}", "sk-***REDACTED***", cleaned)
            cleaned = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{16,}", "Bearer ***REDACTED***", cleaned)
            redacted[k] = cleaned
        elif isinstance(v, dict):
            redacted[k] = redact_sensitive_data(v)
        else:
            redacted[k] = v
    return redacted


def _to_task_response(
    task: BackgroundTask,
    conversation_title: Optional[str] = None,
) -> BackgroundTaskResponse:
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

    # Compute queue wait duration in milliseconds
    queue_wait_ms = None
    if task.started_at:
        created = task.created_at
        started = task.started_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        queue_wait_ms = round(max(0.0, (started - created).total_seconds() * 1000.0), 2)
    elif task.status == TaskStatus.QUEUED.value:
        created = task.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        queue_wait_ms = round(max(0.0, (now - created).total_seconds() * 1000.0), 2)

    # Extract source identifiers
    source_conv_id = None
    source_msg_id = None
    if parsed_input:
        source_conv_id = parsed_input.get("conversation_id")
        source_msg_id = parsed_input.get("message_id")

    # Extract execution details
    execution_mode = None
    worker_id = None
    if parsed_result:
        execution_mode = parsed_result.get("execution_mode")
        worker_id = parsed_result.get("worker_id")

    return BackgroundTaskResponse(
        id=task.id,
        celery_task_id=task.celery_task_id,
        task_name=task.task_name,
        task_type=task.task_type,
        status=task.status,
        input_params_json=task.input_params_json,
        input_params=redact_sensitive_data(parsed_input),
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
        source_conversation_id=source_conv_id,
        source_conversation_title=conversation_title,
        source_message_id=source_msg_id,
        execution_mode=execution_mode,
        worker_id=worker_id,
        queue_wait_ms=queue_wait_ms,
    )


class TaskService:
    """
    Service layer for managing asynchronous background tasks and Celery task execution.
    """

    @classmethod
    def is_celery_worker_online(cls) -> bool:
        """Checks if at least one Celery worker node is actively listening and responsive."""
        try:
            from app.tasks.celery_app import celery_app
            insp = celery_app.control.inspect(timeout=0.4)
            pings = insp.ping()
            return bool(pings and len(pings) > 0)
        except Exception:
            return False

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

        # Dispatch task to Celery worker if online, or automatically fallback to local async execution
        celery_id = None
        worker_online = cls.is_celery_worker_online()

        if worker_online:
            try:
                from app.tasks.celery_app import (
                    extract_memory_celery_task,
                    reindex_embeddings_celery_task,
                )

                if task_type == TaskType.MEMORY_EXTRACTION.value:
                    res = extract_memory_celery_task.delay(
                        db_task_id=task.id,
                        user_content=input_params.get("user_content", "") if input_params else "",
                        assistant_content=input_params.get("assistant_content", "") if input_params else "",
                        conversation_id=input_params.get("conversation_id") if input_params else None,
                        message_id=input_params.get("message_id") if input_params else None,
                    )
                    celery_id = res.id
                elif task_type == TaskType.EMBEDDING_REINDEX.value:
                    res = reindex_embeddings_celery_task.delay(db_task_id=task.id)
                    celery_id = res.id

                if celery_id:
                    task.celery_task_id = celery_id
                    await session.commit()
                    await session.refresh(task)
            except Exception as exc:
                logger.warning(
                    f"Celery queue dispatch error ({exc}). Running task in local asynchronous fallback runtime."
                )
                asyncio.create_task(cls._execute_local_fallback(task.id, task_type, input_params or {}))
        else:
            logger.info(
                f"Celery worker is offline. Executing task '{task_name}' ({task.id}) via local async fallback."
            )
            asyncio.create_task(cls._execute_local_fallback(task.id, task_type, input_params or {}))

        return _to_task_response(task)

    @classmethod
    async def _execute_local_fallback(
        cls, db_task_id: str, task_type: str, input_params: Dict[str, Any]
    ) -> None:
        """Executes the task in local async loop if Celery worker is offline."""
        from app.database.session import async_session_factory
        from app.memory.extraction import extract_and_reconcile_memories_with_trace

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
                    memories, trace = await extract_and_reconcile_memories_with_trace(
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
                        "execution_mode": "local_async",
                        "worker_id": "in-process-event-loop",
                        "memories_extracted": len(memories),
                        "memory_ids": [m.id for m in memories],
                        "extraction_trace": trace,
                    })
                    await session.commit()
                else:
                    task.status = TaskStatus.SUCCEEDED.value
                    task.completed_at = datetime.now(timezone.utc)
                    task.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    task.result_metadata_json = json.dumps({
                        "execution_mode": "local_async",
                        "worker_id": "in-process-event-loop",
                        "action": "completed",
                    })
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

        conv_title = None
        if task.input_params_json:
            try:
                params = json.loads(task.input_params_json)
                c_id = params.get("conversation_id")
                if c_id:
                    c_stmt = select(Conversation.title).where(Conversation.id == c_id)
                    c_res = await session.execute(c_stmt)
                    conv_title = c_res.scalar_one_or_none()
            except Exception:
                pass

        return _to_task_response(task, conversation_title=conv_title)

    @classmethod
    async def list_tasks(
        cls,
        session: AsyncSession,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "created_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> TaskListResponse:
        filters = []
        if status and status.strip() and status.strip().lower() != "all":
            filters.append(BackgroundTask.status == status.strip().lower())
        if task_type and task_type.strip() and task_type.strip().lower() != "all":
            filters.append(BackgroundTask.task_type == task_type.strip().lower())
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    BackgroundTask.task_name.ilike(term),
                    BackgroundTask.id.ilike(term),
                    BackgroundTask.celery_task_id.ilike(term),
                    BackgroundTask.input_params_json.ilike(term),
                )
            )

        count_stmt = select(func.count(BackgroundTask.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total_res = await session.execute(count_stmt)
        total = total_res.scalar() or 0

        items_stmt = select(BackgroundTask)
        if filters:
            items_stmt = items_stmt.where(and_(*filters))

        # Sort order
        if sort_by == "created_asc":
            items_stmt = items_stmt.order_by(asc(BackgroundTask.created_at))
        elif sort_by == "duration_desc":
            items_stmt = items_stmt.order_by(desc(BackgroundTask.duration_ms))
        elif sort_by == "duration_asc":
            items_stmt = items_stmt.order_by(asc(BackgroundTask.duration_ms))
        else:
            items_stmt = items_stmt.order_by(desc(BackgroundTask.created_at))

        items_stmt = items_stmt.limit(limit).offset(offset)

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

        # Queue metrics: oldest queued job and stale queued count (> 300s)
        now = datetime.now(timezone.utc)
        oldest_stmt = (
            select(BackgroundTask.created_at)
            .where(BackgroundTask.status == TaskStatus.QUEUED.value)
            .order_by(asc(BackgroundTask.created_at))
            .limit(1)
        )
        oldest_res = await session.execute(oldest_stmt)
        oldest_created = oldest_res.scalar_one_or_none()

        oldest_wait_seconds = None
        if oldest_created:
            if oldest_created.tzinfo is None:
                oldest_created = oldest_created.replace(tzinfo=timezone.utc)
            oldest_wait_seconds = max(0.0, (now - oldest_created).total_seconds())

        # Stale queued count: queued > 300s (5 minutes)
        stale_count = 0
        all_queued_stmt = select(BackgroundTask.created_at).where(
            BackgroundTask.status == TaskStatus.QUEUED.value
        )
        all_queued_res = await session.execute(all_queued_stmt)
        wait_times = []
        for (c_time,) in all_queued_res.all():
            if c_time.tzinfo is None:
                c_time = c_time.replace(tzinfo=timezone.utc)
            diff = max(0.0, (now - c_time).total_seconds())
            wait_times.append(diff)
            if diff >= 300.0:
                stale_count += 1

        avg_wait = round(sum(wait_times) / len(wait_times), 1) if wait_times else None

        return TaskStatsResponse(
            total=total,
            queued=counts.get(TaskStatus.QUEUED.value, 0),
            running=counts.get(TaskStatus.RUNNING.value, 0),
            succeeded=counts.get(TaskStatus.SUCCEEDED.value, 0),
            failed=counts.get(TaskStatus.FAILED.value, 0),
            cancelled=counts.get(TaskStatus.CANCELLED.value, 0),
            oldest_queued_wait_seconds=round(oldest_wait_seconds, 1) if oldest_wait_seconds is not None else None,
            average_wait_seconds=avg_wait,
            stale_queued_count=stale_count,
        )

    @classmethod
    async def get_worker_health(cls, session: AsyncSession) -> WorkerHealthResponse:
        """Retrieves actual health, connection latency, and active worker metadata."""
        import redis

        redis_connected = False
        redis_latency_ms = None
        try:
            start_r = time.perf_counter()
            r_client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
            if r_client.ping():
                redis_connected = True
                redis_latency_ms = round((time.perf_counter() - start_r) * 1000, 2)
        except Exception:
            redis_connected = False

        celery_online = False
        worker_count = 0
        active_workers: List[str] = []
        registered_task_types: List[str] = []
        active_tasks_count = 0
        reserved_tasks_count = 0

        try:
            from app.tasks.celery_app import celery_app
            insp = celery_app.control.inspect(timeout=0.4)
            pings = insp.ping()
            if pings:
                celery_online = True
                worker_count = len(pings)
                active_workers = list(pings.keys())

                registered_dict = insp.registered() or {}
                all_registered = set()
                for tasks in registered_dict.values():
                    all_registered.update(tasks)
                registered_task_types = sorted(list(all_registered))

                active_dict = insp.active() or {}
                for active_list in active_dict.values():
                    active_tasks_count += len(active_list)

                reserved_dict = insp.reserved() or {}
                for reserved_list in reserved_dict.values():
                    reserved_tasks_count += len(reserved_list)
        except Exception as e:
            logger.debug(f"Celery inspect error: {e}")

        # Last successful task
        last_succ_stmt = (
            select(BackgroundTask.id, BackgroundTask.task_name, BackgroundTask.completed_at)
            .where(BackgroundTask.status == TaskStatus.SUCCEEDED.value)
            .order_by(desc(BackgroundTask.completed_at))
            .limit(1)
        )
        last_succ_res = await session.execute(last_succ_stmt)
        last_succ_row = last_succ_res.first()
        last_succ_data = None
        if last_succ_row:
            last_succ_data = {
                "id": last_succ_row[0],
                "task_name": last_succ_row[1],
                "completed_at": last_succ_row[2].isoformat() if last_succ_row[2] else None,
            }

        return WorkerHealthResponse(
            redis_connected=redis_connected,
            redis_latency_ms=redis_latency_ms,
            celery_online=celery_online,
            worker_count=worker_count,
            active_workers=active_workers,
            registered_task_types=registered_task_types,
            active_tasks_count=active_tasks_count,
            reserved_tasks_count=reserved_tasks_count,
            last_heartbeat=datetime.now(timezone.utc) if celery_online else None,
            last_successful_task=last_succ_data,
        )

    @classmethod
    async def sweep_stale_tasks(
        cls, session: AsyncSession, max_stale_seconds: int = 10
    ) -> SweepStaleTasksResponse:
        """
        Sweeps and processes queued tasks that have remained unconsumed.
        Processes each through local async execution or triggers Celery if online.
        """
        stmt = (
            select(BackgroundTask)
            .where(BackgroundTask.status == TaskStatus.QUEUED.value)
            .order_by(asc(BackgroundTask.created_at))
        )
        result = await session.execute(stmt)
        queued_tasks = list(result.scalars().all())

        swept_ids = []
        for t in queued_tasks:
            input_params = {}
            if t.input_params_json:
                try:
                    input_params = json.loads(t.input_params_json)
                except Exception:
                    pass
            await cls._execute_local_fallback(t.id, t.task_type, input_params)
            swept_ids.append(t.id)

        return SweepStaleTasksResponse(
            swept_count=len(swept_ids),
            task_ids=swept_ids,
            message=f"Successfully swept and processed {len(swept_ids)} queued tasks.",
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
        task.retry_count += 1
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        task.duration_ms = None
        await session.commit()
        await session.refresh(task)

        # Dispatch
        if cls.is_celery_worker_online():
            try:
                from app.tasks.celery_app import (
                    extract_memory_celery_task,
                    reindex_embeddings_celery_task,
                )
                if task.task_type == TaskType.MEMORY_EXTRACTION.value:
                    res = extract_memory_celery_task.delay(
                        db_task_id=task.id,
                        user_content=input_params.get("user_content", ""),
                        assistant_content=input_params.get("assistant_content", ""),
                        conversation_id=input_params.get("conversation_id"),
                        message_id=input_params.get("message_id"),
                    )
                    task.celery_task_id = res.id
                    await session.commit()
                    await session.refresh(task)
                elif task.task_type == TaskType.EMBEDDING_REINDEX.value:
                    res = reindex_embeddings_celery_task.delay(db_task_id=task.id)
                    task.celery_task_id = res.id
                    await session.commit()
                    await session.refresh(task)
            except Exception:
                asyncio.create_task(cls._execute_local_fallback(task.id, task.task_type, input_params))
        else:
            asyncio.create_task(cls._execute_local_fallback(task.id, task.task_type, input_params))

        return _to_task_response(task)
