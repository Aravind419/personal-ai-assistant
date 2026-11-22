import asyncio
import time
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from celery import Celery

from app.core.config import settings
from app.core.logging import logger

celery_app = Celery(
    "personal_ai_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=120,        # Hard timeout 120s
    task_soft_time_limit=60,    # Soft timeout 60s
    broker_connection_retry_on_startup=True,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def extract_memory_celery_task(
    self,
    db_task_id: str,
    user_content: str,
    assistant_content: str,
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
):
    """
    Celery background worker task for automatic memory extraction.
    Updates persistent background_tasks state in PostgreSQL.
    """
    start_time = time.perf_counter()

    async def _run():
        from app.database.session import async_session_factory
        from app.tasks.models import BackgroundTask
        from app.memory.extraction import extract_and_reconcile_memories
        from sqlalchemy import select

        async with async_session_factory() as session:
            # Mark running
            stmt = select(BackgroundTask).where(BackgroundTask.id == db_task_id)
            res = await session.execute(stmt)
            task_rec = res.scalar_one_or_none()
            if task_rec:
                task_rec.status = "running"
                task_rec.started_at = datetime.now(timezone.utc)
                await session.commit()

            try:
                memories = await extract_and_reconcile_memories(
                    user_message=user_content,
                    assistant_response=assistant_content,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    session=session,
                )

                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if task_rec:
                    task_rec.status = "succeeded"
                    task_rec.completed_at = datetime.now(timezone.utc)
                    task_rec.duration_ms = duration_ms
                    task_rec.result_metadata_json = json.dumps({
                        "memories_extracted": len(memories),
                        "memory_ids": [m.id for m in memories],
                    })
                    await session.commit()

                return {"status": "succeeded", "memories_count": len(memories)}

            except Exception as exc:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if task_rec:
                    task_rec.retry_count += 1
                    task_rec.error_message = str(exc)
                    if task_rec.retry_count >= task_rec.max_retries:
                        task_rec.status = "failed"
                        task_rec.completed_at = datetime.now(timezone.utc)
                    task_rec.duration_ms = duration_ms
                    await session.commit()
                raise exc

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.warning(f"Task {db_task_id} failed on try {self.request.retries + 1}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        raise exc


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def reindex_embeddings_celery_task(self, db_task_id: str):
    """
    Worker task to regenerate or re-verify vector embeddings for stored memories.
    """
    start_time = time.perf_counter()

    async def _run():
        from app.database.session import async_session_factory
        from app.tasks.models import BackgroundTask
        from app.memory.models import Memory
        from app.memory.embeddings import get_default_embedding_provider
        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = select(BackgroundTask).where(BackgroundTask.id == db_task_id)
            res = await session.execute(stmt)
            task_rec = res.scalar_one_or_none()
            if task_rec:
                task_rec.status = "running"
                task_rec.started_at = datetime.now(timezone.utc)
                await session.commit()

            try:
                mem_stmt = select(Memory).where(Memory.is_archived == False)
                mem_res = await session.execute(mem_stmt)
                memories = mem_res.scalars().all()

                provider = get_default_embedding_provider()
                reindexed_count = 0

                for mem in memories:
                    mem.embedding = await provider.embed_text(mem.content)
                    mem.embedding_model = provider.model_name
                    mem.embedding_dim = len(mem.embedding)
                    reindexed_count += 1

                await session.commit()
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if task_rec:
                    task_rec.status = "succeeded"
                    task_rec.completed_at = datetime.now(timezone.utc)
                    task_rec.duration_ms = duration_ms
                    task_rec.result_metadata_json = json.dumps({"reindexed_count": reindexed_count})
                    await session.commit()

                return {"status": "succeeded", "reindexed": reindexed_count}

            except Exception as exc:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if task_rec:
                    task_rec.status = "failed"
                    task_rec.completed_at = datetime.now(timezone.utc)
                    task_rec.error_message = str(exc)
                    task_rec.duration_ms = duration_ms
                    await session.commit()
                raise exc

    try:
        return asyncio.run(_run())
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise exc
