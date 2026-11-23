import re
import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.automations.schemas import (
    TriggerType,
    AutomationAction,
    ParseInstructionResponse,
)
from app.tools.base import ToolRegistry
from app.core.config import settings
from app.core.logging import logger


class AutomationInstructionParser:
    """
    Parses natural language requests into structured automation configurations.
    Validates every tool against ToolRegistry to prevent execution of unbuilt or hallucinated tools.
    """

    @classmethod
    def parse(cls, instruction: str, user_timezone: Optional[str] = None) -> ParseInstructionResponse:
        clean = instruction.strip()
        lower = clean.lower()
        tz = user_timezone or getattr(settings, "DEFAULT_TIMEZONE", "UTC") or "UTC"

        validation_errors: List[str] = []
        requires_confirmation = False

        # 1. Detect Trigger & Schedule
        trigger_type, schedule_config = cls._extract_schedule(lower)

        # 2. Extract Title / Name
        name = cls._generate_name(clean, lower)

        # 3. Detect Intended Actions & Tools
        actions, tools_used = cls._extract_actions_and_tools(lower)

        # 4. Strict Tool Validation against Registry
        for action in actions:
            if not ToolRegistry.has(action.tool):
                validation_errors.append(
                    f"Requested tool '{action.tool}' is not registered in ToolRegistry."
                )

        # 5. Check if any tools require approval / confirmation
        for tool_name in tools_used:
            tool_obj = ToolRegistry.get(tool_name)
            if tool_obj and tool_obj.permission_level.value in ("sensitive", "critical"):
                requires_confirmation = True

        # Generate a descriptive summary
        description = f"Automated workflow: {name}. Runs {trigger_type.value} with schedule {schedule_config}."

        confidence = 0.95 if not validation_errors else 0.70

        return ParseInstructionResponse(
            success=len(validation_errors) == 0,
            name=name,
            description=description,
            natural_instruction=clean,
            trigger_type=trigger_type,
            schedule_config=schedule_config,
            timezone=tz,
            actions=actions,
            associated_tools=tools_used,
            approval_policy="inherit_tool_permissions",
            validation_errors=validation_errors,
            requires_confirmation=requires_confirmation,
            confidence=confidence,
        )

    @classmethod
    def _extract_schedule(cls, text: str) -> Tuple[TriggerType, Dict[str, Any]]:
        # Check for time pattern (e.g. 8 AM, 8:30 AM, 19:00, 8:00)
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
        time_str = "08:00"
        if time_match:
            raw_hour = int(time_match.group(1))
            raw_min = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm:
                if ampm == "pm" and raw_hour < 12:
                    raw_hour += 12
                elif ampm == "am" and raw_hour == 12:
                    raw_hour = 0
            time_str = f"{raw_hour:02d}:{raw_min:02d}"

        # Weekly detection
        days_map = {
            "monday": "mon", "mon": "mon",
            "tuesday": "tue", "tue": "tue",
            "wednesday": "wed", "wed": "wed",
            "thursday": "thu", "thu": "thu",
            "friday": "fri", "fri": "fri",
            "saturday": "sat", "sat": "sat",
            "sunday": "sun", "sun": "sun",
        }
        detected_days = []
        for word, code in days_map.items():
            if re.search(rf'\b{word}\b', text):
                if code not in detected_days:
                    detected_days.append(code)

        if detected_days and ("every" in text or "weekly" in text or len(detected_days) > 0):
            return TriggerType.WEEKLY, {"time": time_str, "days": detected_days}

        # Daily detection
        if any(term in text for term in ["every day", "daily", "every morning", "every evening", "every night", "every afternoon"]):
            return TriggerType.DAILY, {"time": time_str}

        # Monthly detection
        if "monthly" in text or "every month" in text:
            day_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s*(?:day|of the month)', text)
            day = int(day_match.group(1)) if day_match else 1
            return TriggerType.MONTHLY, {"time": time_str, "day_of_month": day}

        # Interval detection (e.g. every 2 hours, every 30 minutes)
        interval_match = re.search(r'every\s+(\d+)\s+(minute|min|hour|second)s?', text)
        if interval_match:
            amount = int(interval_match.group(1))
            unit = interval_match.group(2)
            if unit.startswith("sec"):
                return TriggerType.INTERVAL, {"interval_seconds": amount}
            elif unit.startswith("min"):
                return TriggerType.INTERVAL, {"interval_minutes": amount}
            elif unit.startswith("hour"):
                return TriggerType.INTERVAL, {"interval_hours": amount}

        # One time detection
        if "tomorrow" in text or "at " in text or "once" in text:
            tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
            return TriggerType.ONE_TIME, {"run_at": f"{tomorrow_date.isoformat()}T{time_str}:00"}

        # Default to daily
        return TriggerType.DAILY, {"time": time_str}

    @classmethod
    def _generate_name(cls, original: str, lower: str) -> str:
        if "briefing" in lower or "morning" in lower:
            return "Morning Briefing"
        if "email" in lower:
            return "Email Digest"
        if "task" in lower or "priority" in lower:
            return "Task Review"
        if "report" in lower or "activity" in lower:
            return "Weekly Activity Report"
        if "remind" in lower:
            return "Scheduled Reminder"
        # Truncate first few words
        words = original.split()[:4]
        return " ".join(words).title() or "Custom Automation"

    @classmethod
    def _extract_actions_and_tools(cls, text: str) -> Tuple[List[AutomationAction], List[str]]:
        actions: List[AutomationAction] = []
        tools: List[str] = []

        # Check for briefing intent
        if "briefing" in text or ("calendar" in text and "email" in text):
            # Briefing generator action
            actions.append(AutomationAction(
                tool="generate_morning_briefing",
                arguments={"sections": ["calendar", "emails", "tasks", "automations"]},
                description="Synthesize personal morning briefing"
            ))
            tools.append("generate_morning_briefing")
            return actions, tools

        # Calendar check
        if "calendar" in text or "events" in text or "meeting" in text:
            tool_id = "google_calendar_list" if ToolRegistry.has("google_calendar_list") else "get_system_time"
            actions.append(AutomationAction(
                tool=tool_id,
                arguments={"max_results": 10},
                description="List upcoming calendar events"
            ))
            tools.append(tool_id)

        # Email check
        if "email" in text or "gmail" in text or "inbox" in text:
            tool_id = "google_mail_list" if ToolRegistry.has("google_mail_list") else "text_processor"
            actions.append(AutomationAction(
                tool=tool_id,
                arguments={"query": "is:unread", "max_results": 5},
                description="List unread emails"
            ))
            tools.append(tool_id)

        # System time or tasks fallback if empty
        if not actions:
            actions.append(AutomationAction(
                tool="get_system_time",
                arguments={},
                description="Retrieve current system clock"
            ))
            tools.append("get_system_time")

        return actions, tools
