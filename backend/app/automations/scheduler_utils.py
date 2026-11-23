import datetime
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional, Dict, Any, List
import croniter

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.core.logging import logger


def get_safe_timezone(tz_name: Optional[str]) -> ZoneInfo:
    """
    Resolves a timezone name into a valid ZoneInfo instance.
    Falls back to settings.DEFAULT_TIMEZONE or UTC.
    """
    target = tz_name or getattr(settings, "DEFAULT_TIMEZONE", "UTC") or "UTC"
    try:
        return ZoneInfo(target)
    except (ZoneInfoNotFoundError, ValueError, Exception):
        try:
            return ZoneInfo(getattr(settings, "DEFAULT_TIMEZONE", "UTC"))
        except Exception:
            return ZoneInfo("UTC")


def compute_next_run_at(
    trigger_type: str,
    schedule_config: Dict[str, Any],
    tz_name: Optional[str] = None,
    from_time: Optional[datetime.datetime] = None,
) -> Optional[datetime.datetime]:
    """
    Computes the next execution timestamp (UTC) for an automation schedule.
    Handles DST transitions and returns timezone-aware UTC datetime.
    """
    tz = get_safe_timezone(tz_name)
    now_utc = from_time if from_time else datetime.datetime.now(datetime.timezone.utc)
    now_local = now_utc.astimezone(tz)

    if trigger_type == "manual":
        return None

    elif trigger_type == "one_time":
        run_at_str = schedule_config.get("run_at")
        if not run_at_str:
            return None
        try:
            target_dt = datetime.datetime.fromisoformat(run_at_str)
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=tz)
            target_utc = target_dt.astimezone(datetime.timezone.utc)
            return target_utc if target_utc > now_utc else None
        except Exception as exc:
            logger.warning(f"Failed to parse one_time run_at '{run_at_str}': {exc}")
            return None

    elif trigger_type == "interval":
        interval_seconds = int(schedule_config.get("interval_seconds", 0))
        if interval_seconds <= 0:
            interval_minutes = int(schedule_config.get("interval_minutes", 0))
            interval_seconds = interval_minutes * 60
        if interval_seconds <= 0:
            interval_hours = int(schedule_config.get("interval_hours", 0))
            interval_seconds = interval_hours * 3600
        if interval_seconds <= 0:
            return None
        return now_utc + datetime.timedelta(seconds=interval_seconds)

    elif trigger_type == "daily":
        time_str = schedule_config.get("time", "08:00")
        try:
            hour_str, min_str = time_str.split(":")[:2]
            hour = int(hour_str)
            minute = int(min_str)
        except Exception:
            hour, minute = 8, 0

        candidate_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate_local <= now_local:
            candidate_local += datetime.timedelta(days=1)
        return candidate_local.astimezone(datetime.timezone.utc)

    elif trigger_type == "weekly":
        time_str = schedule_config.get("time", "08:00")
        try:
            hour_str, min_str = time_str.split(":")[:2]
            hour = int(hour_str)
            minute = int(min_str)
        except Exception:
            hour, minute = 8, 0

        # Day map (0=Monday, 6=Sunday)
        day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        raw_days = schedule_config.get("days", ["mon"])
        target_weekdays = set()
        for d in raw_days:
            if isinstance(d, int) and 0 <= d <= 6:
                target_weekdays.add(d)
            elif isinstance(d, str):
                d_clean = d.strip()[:3].lower()
                if d_clean in day_names:
                    target_weekdays.add(day_names.index(d_clean))

        if not target_weekdays:
            target_weekdays = {0}  # Default Monday

        # Find nearest upcoming day
        for offset in range(0, 8):
            candidate = (now_local + datetime.timedelta(days=offset)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if candidate.weekday() in target_weekdays and candidate > now_local:
                return candidate.astimezone(datetime.timezone.utc)

        # Fallback 7 days ahead
        fallback = (now_local + datetime.timedelta(days=7)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return fallback.astimezone(datetime.timezone.utc)

    elif trigger_type == "monthly":
        time_str = schedule_config.get("time", "08:00")
        day_of_month = int(schedule_config.get("day_of_month", 1))
        try:
            hour_str, min_str = time_str.split(":")[:2]
            hour = int(hour_str)
            minute = int(min_str)
        except Exception:
            hour, minute = 8, 0

        # Try this month
        year = now_local.year
        month = now_local.month
        # Clamp to max day of month
        import calendar
        max_day = calendar.monthrange(year, month)[1]
        clamped_day = min(day_of_month, max_day)

        candidate = now_local.replace(day=clamped_day, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now_local:
            # Advance month
            month += 1
            if month > 12:
                month = 1
                year += 1
            max_day = calendar.monthrange(year, month)[1]
            clamped_day = min(day_of_month, max_day)
            candidate = candidate.replace(year=year, month=month, day=clamped_day)

        return candidate.astimezone(datetime.timezone.utc)

    elif trigger_type == "cron":
        cron_expr = schedule_config.get("cron", "0 8 * * *")
        try:
            # Use croniter with base local time
            iter_cron = croniter.croniter(cron_expr, now_local)
            next_local = iter_cron.get_next(datetime.datetime)
            if next_local.tzinfo is None:
                next_local = next_local.replace(tzinfo=tz)
            return next_local.astimezone(datetime.timezone.utc)
        except Exception as exc:
            logger.warning(f"Invalid cron expression '{cron_expr}': {exc}")
            raise ValidationException(f"Invalid cron expression '{cron_expr}': {exc}")

    return None
