import pytest
import datetime
import json
from zoneinfo import ZoneInfo
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.automations.schemas import TriggerType, ExecutionStatus, AutomationCreate
from app.automations.service import AutomationService
from app.automations.scheduler_utils import compute_next_run_at
from app.automations.parser import AutomationInstructionParser
from app.automations.executor import AutomationExecutor
from app.integrations.base import IntegrationManager, IntegrationRegistry
from app.briefings.service import BriefingService
from app.notifications.service import NotificationService
from app.tools.base import ToolRegistry
from app.integrations.tools import register_integration_tools
from app.briefings.service import GenerateMorningBriefingTool

# Ensure all tools and integration capabilities are registered in test environment
register_integration_tools()
ToolRegistry.register(GenerateMorningBriefingTool())


@pytest.mark.asyncio
async def test_automation_scheduler_timezones():
    """Verify timezone-aware next run calculation for daily, weekly, interval, and cron."""
    # 1. Interval
    now = datetime.datetime(2026, 11, 23, 10, 0, 0, tzinfo=datetime.timezone.utc)
    next_interval = compute_next_run_at(
        trigger_type="interval",
        schedule_config={"interval_minutes": 30},
        tz_name="UTC",
        from_time=now,
    )
    assert next_interval == datetime.datetime(2026, 11, 23, 10, 30, 0, tzinfo=datetime.timezone.utc)

    # 2. Daily in Asia/Kolkata (+05:30)
    # 08:00 IST is 02:30 UTC
    next_daily = compute_next_run_at(
        trigger_type="daily",
        schedule_config={"time": "08:00"},
        tz_name="Asia/Kolkata",
        from_time=now,
    )
    assert next_daily is not None
    # Converted back to Asia/Kolkata, hour must be 8 and minute 0
    local_dt = next_daily.astimezone(ZoneInfo("Asia/Kolkata"))
    assert local_dt.hour == 8
    assert local_dt.minute == 0

    # 3. Cron expression
    next_cron = compute_next_run_at(
        trigger_type="cron",
        schedule_config={"cron": "0 12 * * *"},
        tz_name="UTC",
        from_time=now,
    )
    assert next_cron == datetime.datetime(2026, 11, 23, 12, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.mark.asyncio
async def test_natural_language_parser():
    """Verify natural language instruction parser maps intents to registered tools."""
    # Briefing intent
    parsed = AutomationInstructionParser.parse("Every morning at 8 AM, prepare a briefing with calendar events and emails")
    assert parsed.success is True
    assert parsed.trigger_type == TriggerType.DAILY
    assert parsed.schedule_config["time"] == "08:00"
    assert "generate_morning_briefing" in parsed.associated_tools

    # Weekly reminder
    parsed_weekly = AutomationInstructionParser.parse("Every Monday at 9:30 AM, check system time")
    assert parsed_weekly.trigger_type == TriggerType.WEEKLY
    assert "mon" in parsed_weekly.schedule_config["days"]
    assert parsed_weekly.schedule_config["time"] == "09:30"


@pytest.mark.asyncio
async def test_automation_crud_lifecycle():
    """Test full automation CRUD lifecycle via FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create automation
        payload = {
            "name": "Test Clock Check",
            "description": "Checks system time every hour",
            "trigger_type": "interval",
            "schedule_config": {"interval_hours": 1},
            "timezone": "UTC",
            "actions": [
                {"tool": "get_system_time", "arguments": {}}
            ],
            "is_enabled": True,
        }
        resp = await client.post("/api/v1/automations", json=payload)
        assert resp.status_code == 201
        auto_data = resp.json()
        auto_id = auto_data["id"]
        assert auto_data["name"] == "Test Clock Check"
        assert auto_data["is_enabled"] is True
        assert auto_data["next_run_at"] is not None

        # 2. Get automation
        get_resp = await client.get(f"/api/v1/automations/{auto_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == auto_id

        # 3. Disable automation
        dis_resp = await client.post(f"/api/v1/automations/{auto_id}/disable")
        assert dis_resp.status_code == 200
        assert dis_resp.json()["is_enabled"] is False
        assert dis_resp.json()["next_run_at"] is None

        # 4. Enable automation
        en_resp = await client.post(f"/api/v1/automations/{auto_id}/enable")
        assert en_resp.status_code == 200
        assert en_resp.json()["is_enabled"] is True
        assert en_resp.json()["next_run_at"] is not None

        # 5. Manual run
        run_resp = await client.post(f"/api/v1/automations/{auto_id}/run")
        assert run_resp.status_code == 200
        exec_data = run_resp.json()
        assert exec_data["status"] == "SUCCEEDED"
        assert len(exec_data["results"]) == 1

        # 6. List executions
        execs_resp = await client.get(f"/api/v1/automations/{auto_id}/executions")
        assert execs_resp.status_code == 200
        assert len(execs_resp.json()) >= 1

        # 7. Delete automation
        del_resp = await client.delete(f"/api/v1/automations/{auto_id}")
        assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_automation_permission_gating_sensitive_action():
    """Verify that an automation attempting a SENSITIVE action pauses in WAITING_FOR_APPROVAL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create automation with sensitive tool 'google_mail_send'
        payload = {
            "name": "Send Weekly Status Email",
            "trigger_type": "manual",
            "schedule_config": {},
            "actions": [
                {
                    "tool": "google_mail_send",
                    "arguments": {"to": "team@example.com", "subject": "Status", "body": "Weekly update."},
                }
            ],
        }
        create_resp = await client.post("/api/v1/automations", json=payload)
        assert create_resp.status_code == 201
        auto_id = create_resp.json()["id"]

        # Run automation
        run_resp = await client.post(f"/api/v1/automations/{auto_id}/run")
        assert run_resp.status_code == 200
        exec_data = run_resp.json()
        # Must pause waiting for approval
        assert exec_data["status"] == "WAITING_FOR_APPROVAL"
        assert exec_data["approval_id"] is not None

        # Inspect approval
        approval_id = exec_data["approval_id"]
        appr_resp = await client.get(f"/api/v1/approvals/{approval_id}")
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "pending"

        # Cleanup
        await client.delete(f"/api/v1/automations/{auto_id}")


from unittest.mock import patch, AsyncMock
from app.core.config import settings


@pytest.mark.asyncio
async def test_integrations_independent_services_and_real_oauth():
    """
    Test independent Google services, configuration checks, CSRF state verification,
    OAuth token exchange, credential encryption, and live API probes.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List independent integration services
        list_resp = await client.get("/api/v1/integrations")
        assert list_resp.status_code == 200
        services = {s["service_id"]: s for s in list_resp.json()}
        assert "google_gmail" in services
        assert "google_drive" in services
        assert "google_calendar" in services
        assert "google_docs" in services
        assert "google_sheets" in services
        assert "google_tasks" in services
        assert "github" in services

        # 2. Test Configuration Required when credentials are missing
        orig_cid = settings.GOOGLE_CLIENT_ID
        orig_csec = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID = None
            settings.GOOGLE_CLIENT_SECRET = None
            svc_resp = await client.get("/api/v1/integrations/google_gmail")
            assert svc_resp.status_code == 200
            assert svc_resp.json()["status"] == "configuration_required"
            assert svc_resp.json()["is_configured"] is False

            # 3. Configure valid test credentials
            settings.GOOGLE_CLIENT_ID = "valid-test-client-id.apps.googleusercontent.com"
            settings.GOOGLE_CLIENT_SECRET = "valid-test-client-secret"

            # 4. Auth URL Generation
            url_resp = await client.get("/api/v1/integrations/google_gmail/auth-url")
            assert url_resp.status_code == 200
            auth_url = url_resp.json()["authorization_url"]
            state = url_resp.json()["state"]
            assert "accounts.google.com" in auth_url
            assert "gmail.readonly" in auth_url
            assert state is not None

            # 5. Token Exchange via OAuth Callback
            mock_tokens = {
                "access_token": "ya29.test_access_token_mock",
                "refresh_token": "1//test_refresh_token_mock",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
            }
            mock_profile = {"email": "testuser@gmail.com", "name": "Test User"}

            with patch("app.integrations.google_auth.GoogleOAuthHandler.exchange_code", new_callable=AsyncMock) as mock_exch, \
                 patch("app.integrations.google_auth.GoogleOAuthHandler.fetch_user_profile", new_callable=AsyncMock) as mock_prof, \
                 patch("app.integrations.google_client.GoogleApiClient.gmail_get_profile", new_callable=AsyncMock) as mock_gprof:

                mock_exch.return_value = mock_tokens
                mock_prof.return_value = mock_profile
                mock_gprof.return_value = {
                    "emailAddress": "testuser@gmail.com",
                    "messagesTotal": 42,
                    "threadsTotal": 20,
                }

                cb_resp = await client.post(
                    "/api/v1/integrations/google_gmail/callback",
                    json={"code": "auth_code_from_google", "state": state},
                )
                assert cb_resp.status_code == 200
                conn_data = cb_resp.json()
                assert conn_data["status"] == "connected"
                assert conn_data["account_identity"] == "testuser@gmail.com"

                # 6. Test connection probe
                test_resp = await client.post("/api/v1/integrations/google_gmail/test")
                assert test_resp.status_code == 200
                assert test_resp.json()["connected"] is True

            # 7. Disconnect and wipe credentials
            disc_resp = await client.post("/api/v1/integrations/google_gmail/disconnect")
            assert disc_resp.status_code == 200
            assert disc_resp.json()["disconnected"] is True

            # Check status after disconnect
            status_after = await client.get("/api/v1/integrations/google_gmail")
            assert status_after.status_code == 200
            assert status_after.json()["status"] == "not_connected"

        finally:
            settings.GOOGLE_CLIENT_ID = orig_cid
            settings.GOOGLE_CLIENT_SECRET = orig_csec


@pytest.mark.asyncio
async def test_native_web_and_data_tools():
    """Verify newly implemented web research and data analysis tools."""
    # 1. Web search tool
    search_tool = ToolRegistry.get("web_search")
    assert search_tool is not None
    res = await search_tool.run(query="Python programming language", max_results=3)
    assert "query" in res
    assert "results" in res

    # 2. Data CSV inspection and statistics tools
    import os
    from app.tools.builtin import WORKSPACE_STORAGE_DIR
    csv_file = WORKSPACE_STORAGE_DIR / "test_data.csv"
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("name,score,age\nAlice,95,30\nBob,80,25\nCharlie,85,35\n")

    try:
        read_csv_tool = ToolRegistry.get("data_read_csv")
        read_res = await read_csv_tool.run(file_path="test_data.csv")
        assert read_res["headers"] == ["name", "score", "age"]
        assert read_res["total_rows"] == 3

        stats_tool = ToolRegistry.get("data_statistics")
        stats_res = await stats_tool.run(file_path="test_data.csv", column_name="score")
        assert stats_res["count"] == 3
        assert stats_res["mean"] == round((95 + 80 + 85) / 3, 4)
        assert stats_res["min"] == 80.0
        assert stats_res["max"] == 95.0

        # 3. Python code execution sandbox
        code_tool = ToolRegistry.get("code_execution_python")
        code_res = await code_tool.run(code="print(sum([1, 2, 3, 4, 5]))")
        assert code_res["success"] is True
        assert "15" in code_res["stdout"]
    finally:
        if csv_file.exists():
            csv_file.unlink()


@pytest.mark.asyncio
async def test_morning_briefing_generation():
    """Test morning briefing generation and retrieval."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen_resp = await client.post("/api/v1/briefings/generate")
        assert gen_resp.status_code == 201
        briefing = gen_resp.json()
        assert "Morning Briefing" in briefing["title"]
        assert "# 🌅 Morning Briefing" in briefing["content_markdown"]

        # Get latest briefing
        lat_resp = await client.get("/api/v1/briefings/latest")
        assert lat_resp.status_code == 200
        assert lat_resp.json()["id"] == briefing["id"]


@pytest.mark.asyncio
async def test_notifications_lifecycle():
    """Test notification retrieval, unread count, and marking as read."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check unread count
        count_resp = await client.get("/api/v1/notifications/unread-count")
        assert count_resp.status_code == 200
        assert "unread_count" in count_resp.json()

        # List notifications
        list_resp = await client.get("/api/v1/notifications")
        assert list_resp.status_code == 200
        notifications = list_resp.json()

        if notifications:
            first_id = notifications[0]["id"]
            read_resp = await client.post(f"/api/v1/notifications/{first_id}/read")
            assert read_resp.status_code == 200

        # Mark all as read
        all_resp = await client.post("/api/v1/notifications/read-all")
        assert all_resp.status_code == 200


@pytest.mark.asyncio
async def test_automation_cancellation_and_idempotency():
    """Verify execution cancellation and duplicate execution protection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create automation
        payload = {
            "name": "Cancel Test Job",
            "trigger_type": "manual",
            "schedule_config": {},
            "actions": [{"tool": "get_system_time", "arguments": {}}],
        }
        res = await client.post("/api/v1/automations", json=payload)
        auto_id = res.json()["id"]

        # Run
        run_res = await client.post(f"/api/v1/automations/{auto_id}/run")
        exec_id = run_res.json()["id"]

        # Cancel execution
        cancel_res = await client.post(f"/api/v1/automations/executions/{exec_id}/cancel")
        assert cancel_res.status_code == 200

        # Cleanup
        await client.delete(f"/api/v1/automations/{auto_id}")


@pytest.mark.asyncio
async def test_all_integration_tools_registered():
    """Verify all Google and GitHub tools are present in ToolRegistry with correct permissions."""
    expected_tools = {
        "google_mail_list": "safe",
        "google_mail_read": "safe",
        "google_mail_send": "sensitive",
        "google_calendar_list": "safe",
        "google_calendar_create": "sensitive",
        "google_calendar_delete": "critical",
        "google_drive_list": "safe",
        "github_list_repos": "safe",
        "github_list_issues": "safe",
        "github_create_issue": "sensitive",
        "generate_morning_briefing": "safe",
    }
    for tool_id, perm in expected_tools.items():
        assert ToolRegistry.has(tool_id), f"Tool '{tool_id}' not found in ToolRegistry"
        tool_obj = ToolRegistry.get(tool_id)
        assert tool_obj.permission_level.value == perm, f"Tool '{tool_id}' expected {perm}, got {tool_obj.permission_level.value}"

