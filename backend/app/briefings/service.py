import uuid
import json
import time
import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.models.automation import Briefing, Notification, Automation
from app.models.tool import ToolApproval
from app.integrations.base import IntegrationManager
from app.integrations.tools import (
    GoogleCalendarListEventsTool as GoogleCalendarListTool,
    GmailListMessagesTool as GoogleMailListTool,
)
from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import PermissionLevel
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger


class BriefingResponse(BaseModel):
    id: str
    title: str
    briefing_type: str
    content_markdown: str
    sections: Dict[str, Any]
    generated_by_model: Optional[str] = None
    duration_ms: Optional[float] = None
    created_at: datetime.datetime


class BriefingService:
    """
    Synthesizes multi-source personalized daily briefings.
    """

    @classmethod
    async def generate_morning_briefing(
        cls,
        db: AsyncSession,
        user_identity: str = "personal_user",
    ) -> BriefingResponse:
        start_time = time.perf_counter()
        now = datetime.datetime.now(datetime.timezone.utc)
        date_str = now.strftime("%A, %B %d, %Y")
        title = f"Morning Briefing — {date_str}"

        sections: Dict[str, Any] = {}
        md_lines: List[str] = [
            f"# 🌅 Morning Briefing — {date_str}",
            "",
            "Here is your proactive daily digest covering schedule, communications, and pending activities.",
            "",
        ]

        # 1. Calendar Events
        conn_google = await IntegrationManager.get_connection(db, "google")
        if conn_google and conn_google.status == "connected":
            cal_tool = GoogleCalendarListTool()
            cal_res = await cal_tool.run(max_results=5)
            events = cal_res.get("events", [])
            sections["calendar"] = {"status": "connected", "events": events}
            md_lines.append("### 📅 Calendar Schedule")
            if events:
                for ev in events:
                    md_lines.append(f"- **{ev.get('summary', 'Untitled Event')}** ({ev.get('start', 'TBD')} - {ev.get('end', 'TBD')})")
            else:
                md_lines.append("- *No scheduled calendar events for today.*")
            md_lines.append("")
        else:
            sections["calendar"] = {"status": "not_connected", "events": []}
            md_lines.extend([
                "### 📅 Calendar Schedule",
                "- *Google Calendar is not connected. Connect in the Integrations dashboard to include your schedule.*",
                "",
            ])

        # 2. Important Emails
        if conn_google and conn_google.status == "connected":
            mail_tool = GoogleMailListTool()
            mail_res = await mail_tool.run(query="is:unread", max_results=5)
            emails = mail_res.get("emails", [])
            sections["emails"] = {"status": "connected", "emails": emails}
            md_lines.append("### ✉️ Important Unread Communications")
            if emails:
                for em in emails:
                    md_lines.append(f"- **{em.get('subject', 'No Subject')}** from `{em.get('from', 'Unknown')}`")
            else:
                md_lines.append("- *No unread emails found.*")
            md_lines.append("")
        else:
            sections["emails"] = {"status": "not_connected", "emails": []}
            md_lines.extend([
                "### ✉️ Important Unread Communications",
                "- *Gmail is not connected. Connect in the Integrations dashboard to include your unread email summary.*",
                "",
            ])

        # 3. Pending Approvals
        appr_stmt = select(ToolApproval).where(ToolApproval.status == "pending")
        appr_res = await db.execute(appr_stmt)
        approvals = appr_res.scalars().all()
        sections["pending_approvals"] = {"count": len(approvals)}
        md_lines.append("### 🛡️ Human-in-the-Loop Approvals")
        if approvals:
            md_lines.append(f"You have **{len(approvals)}** pending action(s) awaiting your decision:")
            for ap in approvals[:5]:
                md_lines.append(f"- **[{ap.permission_level.upper()}]** `{ap.tool_name}`: {ap.reason}")
        else:
            md_lines.append("- *No pending approvals. All systems operating normally.*")
        md_lines.append("")

        # 4. Scheduled Automations
        auto_stmt = select(Automation).where(Automation.is_enabled == True)
        auto_res = await db.execute(auto_stmt)
        active_autos = auto_res.scalars().all()
        sections["automations"] = {"active_count": len(active_autos)}
        md_lines.append("### ⚡ Active Workflows & Automations")
        if active_autos:
            for au in active_autos[:5]:
                next_str = au.next_run_at.isoformat() if au.next_run_at else "manual"
                md_lines.append(f"- **{au.name}** ({au.trigger_type}, next run: `{next_str}`)")
        else:
            md_lines.append("- *No recurring automations active. Create one from the Automations tab.*")
        md_lines.append("")

        duration = round((time.perf_counter() - start_time) * 1000, 2)
        full_md = "\n".join(md_lines)

        briefing = Briefing(
            id=str(uuid.uuid4()),
            title=title,
            briefing_type="morning",
            content_markdown=full_md,
            sections_json=json.dumps(sections),
            generated_by_model="heuristic-synthesizer",
            duration_ms=duration,
            user_identity=user_identity,
        )
        db.add(briefing)

        # Emit Notification
        notif = Notification(
            id=str(uuid.uuid4()),
            title=f"New Briefing: {title}",
            message="Your daily morning briefing is prepared and ready to read.",
            notification_type="morning_briefing_available",
            severity="info",
            metadata_json=json.dumps({"briefing_id": briefing.id}),
        )
        db.add(notif)

        await db.commit()
        await db.refresh(briefing)

        return BriefingResponse(
            id=briefing.id,
            title=briefing.title,
            briefing_type=briefing.briefing_type,
            content_markdown=briefing.content_markdown,
            sections=sections,
            generated_by_model=briefing.generated_by_model,
            duration_ms=briefing.duration_ms,
            created_at=briefing.created_at,
        )

    @classmethod
    async def get_latest_briefing(cls, db: AsyncSession) -> Optional[BriefingResponse]:
        stmt = select(Briefing).order_by(desc(Briefing.created_at)).limit(1)
        res = await db.execute(stmt)
        b = res.scalar_one_or_none()
        if not b:
            return None
        return BriefingResponse(
            id=b.id,
            title=b.title,
            briefing_type=b.briefing_type,
            content_markdown=b.content_markdown,
            sections=json.loads(b.sections_json) if b.sections_json else {},
            generated_by_model=b.generated_by_model,
            duration_ms=b.duration_ms,
            created_at=b.created_at,
        )

    @classmethod
    async def list_briefings(
        cls, db: AsyncSession, limit: int = 10, offset: int = 0
    ) -> List[BriefingResponse]:
        stmt = select(Briefing).order_by(desc(Briefing.created_at)).offset(offset).limit(limit)
        res = await db.execute(stmt)
        items = res.scalars().all()
        return [
            BriefingResponse(
                id=b.id,
                title=b.title,
                briefing_type=b.briefing_type,
                content_markdown=b.content_markdown,
                sections=json.loads(b.sections_json) if b.sections_json else {},
                generated_by_model=b.generated_by_model,
                duration_ms=b.duration_ms,
                created_at=b.created_at,
            )
            for b in items
        ]

    @classmethod
    async def get_briefing(cls, db: AsyncSession, briefing_id: str) -> BriefingResponse:
        stmt = select(Briefing).where(Briefing.id == briefing_id)
        res = await db.execute(stmt)
        b = res.scalar_one_or_none()
        if not b:
            raise ResourceNotFoundException(f"Briefing '{briefing_id}' not found.")
        return BriefingResponse(
            id=b.id,
            title=b.title,
            briefing_type=b.briefing_type,
            content_markdown=b.content_markdown,
            sections=json.loads(b.sections_json) if b.sections_json else {},
            generated_by_model=b.generated_by_model,
            duration_ms=b.duration_ms,
            created_at=b.created_at,
        )


class GenerateMorningBriefingTool(BaseTool):
    """
    Registered tool allowing automations to synthesize a morning briefing.
    """
    @property
    def id(self) -> str:
        return "generate_morning_briefing"

    @property
    def name(self) -> str:
        return "Generate Morning Briefing"

    @property
    def description(self) -> str:
        return "Synthesizes today's calendar events, emails, tasks, and system automations into a briefing."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["calendar", "emails", "tasks", "automations"],
                },
            },
        }

    async def run(self, **arguments) -> Any:
        from app.database.session import async_session_factory
        async with async_session_factory() as db:
            briefing = await BriefingService.generate_morning_briefing(db)
            return {
                "briefing_id": briefing.id,
                "title": briefing.title,
                "summary": briefing.content_markdown[:300] + "...",
            }


# Auto-register upon module load
ToolRegistry.register(GenerateMorningBriefingTool())
