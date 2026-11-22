import pytest
from httpx import AsyncClient
from app.database.session import async_session_factory
from app.tasks.service import TaskService
from app.tasks.schemas import TaskStatus, TaskType


@pytest.mark.asyncio
async def test_task_lifecycle_and_api(async_client: AsyncClient):
    # 1. Create a task via service
    async with async_session_factory() as session:
        task = await TaskService.create_and_dispatch_task(
            session=session,
            task_name="Manual Memory Extraction Test",
            task_type="memory_extraction",
            input_params={"user_content": "I like dark mode", "assistant_content": "Noted"},
        )
        task_id = task.id
        assert task.task_name == "Manual Memory Extraction Test"
        assert task.status in (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value, TaskStatus.SUCCEEDED.value)

    # 2. Get task via API
    get_res = await async_client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == task_id
    assert fetched["task_name"] == "Manual Memory Extraction Test"

    # 3. List tasks
    list_res = await async_client.get("/api/v1/tasks")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(t["id"] == task_id for t in list_data["items"])

    # 4. Get Task Stats
    stats_res = await async_client.get("/api/v1/tasks/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total" in stats
    assert "queued" in stats
    assert "running" in stats
    assert "succeeded" in stats
    assert "failed" in stats
    assert "cancelled" in stats
    assert stats["total"] >= 1


@pytest.mark.asyncio
async def test_task_cancellation_and_retry(async_client: AsyncClient):
    # 1. Create a task directly in queued status
    async with async_session_factory() as session:
        from app.tasks.models import BackgroundTask
        t = BackgroundTask(
            task_name="Cancellable Long Running Task",
            task_type="system_maintenance",
            status=TaskStatus.QUEUED.value,
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        test_task_id = t.id

    # 2. Cancel task via API
    cancel_res = await async_client.post(f"/api/v1/tasks/{test_task_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == TaskStatus.CANCELLED.value

    # 3. Retry task via API
    retry_res = await async_client.post(f"/api/v1/tasks/{test_task_id}/retry")
    assert retry_res.status_code == 200
    retried_status = retry_res.json()["status"]
    assert retried_status in (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value, TaskStatus.SUCCEEDED.value)


@pytest.mark.asyncio
async def test_task_error_sanitization(async_client: AsyncClient):
    # Simulate failed task with multiline error
    async with async_session_factory() as session:
        from app.tasks.models import BackgroundTask
        t = BackgroundTask(
            task_name="Failing Task With Sensitive Trace",
            task_type="memory_extraction",
            status=TaskStatus.FAILED.value,
            error_message="Traceback (most recent call last):\n  File 'secret.py', line 10\nValueError: Critical parsing error",
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        failed_id = t.id

    res = await async_client.get(f"/api/v1/tasks/{failed_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "failed"
    # Sanitized error should only include the clean summary line, not the multiline traceback header
    assert "Traceback" not in data["error_message"]
    assert "Critical parsing error" in data["error_message"]


@pytest.mark.asyncio
async def test_worker_health_and_queue_metrics(async_client: AsyncClient):
    # Test GET /api/v1/tasks/health
    res = await async_client.get("/api/v1/tasks/health")
    assert res.status_code == 200
    health = res.json()
    assert "redis_connected" in health
    assert "celery_online" in health
    assert "worker_count" in health
    assert isinstance(health["registered_task_types"], list)
    assert isinstance(health["active_workers"], list)

    # Test GET /api/v1/tasks/stats
    stats_res = await async_client.get("/api/v1/tasks/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "oldest_queued_wait_seconds" in stats
    assert "average_wait_seconds" in stats
    assert "stale_queued_count" in stats


@pytest.mark.asyncio
async def test_task_search_and_sort(async_client: AsyncClient):
    # Test task listing with search and sort
    search_res = await async_client.get("/api/v1/tasks?search=Memory&sort_by=created_desc")
    assert search_res.status_code == 200
    data = search_res.json()
    assert "items" in data
    assert "total" in data

    # Test stale task sweep endpoint
    sweep_res = await async_client.post("/api/v1/tasks/sweep-stale?max_stale_seconds=300")
    assert sweep_res.status_code == 200
    sweep_data = sweep_res.json()
    assert "swept_count" in sweep_data
    assert "message" in sweep_data

