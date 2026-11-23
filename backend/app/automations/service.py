import uuid
import json
import time
import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from app.models.automation import (
    Automation,
    AutomationExecution,
    Notification,
)
from app.automations.schemas import (
    AutomationCreate,
    AutomationUpdate,
    AutomationResponse,
    AutomationExecutionResponse,
    AutomationAction,
    TriggerType,
    ExecutionStatus,
    AutomationStatsResponse,
)
from app.automations.scheduler_utils import compute_next_run_at, get_safe_timezone
from app.tools.base import ToolRegistry
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import logger


class AutomationService:
    """
    Core service managing automation lifecycles, schedule calculations,
    and historical executions.
    """

    @classmethod
    async def create_automation(cls, db: AsyncSession, data: AutomationCreate) -> AutomationResponse:
        # Validate that all requested actions exist in ToolRegistry
        for action in data.actions:
            if not ToolRegistry.has(action.tool):
                raise ValidationException(
                    f"Tool '{action.tool}' is not registered in ToolRegistry. "
                    "Ensure tools are properly registered before adding them to automations."
                )

        # Compute associated tools
        tools_list = data.associated_tools or [a.tool for a in data.actions]
        # Deduplicate
        tools_list = list(dict.fromkeys(tools_list))

        # Validate timezone
        tz = get_safe_timezone(data.timezone)
        tz_name = tz.key if hasattr(tz, "key") else str(tz)

        # Compute next run time
        next_run = compute_next_run_at(
            trigger_type=data.trigger_type.value,
            schedule_config=data.schedule_config,
            tz_name=tz_name,
        ) if data.is_enabled else None

        actions_data = [a.model_dump() for a in data.actions]

        auto = Automation(
            id=str(uuid.uuid4()),
            name=data.name.strip(),
            description=data.description,
            natural_instruction=data.natural_instruction,
            trigger_type=data.trigger_type.value,
            schedule_config=json.dumps(data.schedule_config),
            timezone=tz_name,
            is_enabled=data.is_enabled,
            actions_json=json.dumps(actions_data),
            associated_tools=json.dumps(tools_list),
            approval_policy=data.approval_policy,
            next_run_at=next_run,
            owner_identity="personal_user",
        )

        db.add(auto)
        await db.commit()
        await db.refresh(auto)
        logger.info(f"Created automation '{auto.name}' (id={auto.id}, next_run={next_run})")
        return cls._to_response(auto)

    @classmethod
    async def get_automation(cls, db: AsyncSession, automation_id: str) -> AutomationResponse:
        stmt = select(Automation).where(Automation.id == automation_id)
        res = await db.execute(stmt)
        auto = res.scalar_one_or_none()
        if not auto:
            raise ResourceNotFoundException(f"Automation '{automation_id}' not found.")
        return cls._to_response(auto)

    @classmethod
    async def list_automations(
        cls,
        db: AsyncSession,
        is_enabled: Optional[bool] = None,
        trigger_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AutomationResponse]:
        stmt = select(Automation).order_by(Automation.created_at.desc())
        if is_enabled is not None:
            stmt = stmt.where(Automation.is_enabled == is_enabled)
        if trigger_type is not None:
            stmt = stmt.where(Automation.trigger_type == trigger_type)
        stmt = stmt.offset(offset).limit(limit)

        res = await db.execute(stmt)
        automations = res.scalars().all()
        return [cls._to_response(a) for a in automations]

    @classmethod
    async def update_automation(
        cls, db: AsyncSession, automation_id: str, data: AutomationUpdate
    ) -> AutomationResponse:
        stmt = select(Automation).where(Automation.id == automation_id)
        res = await db.execute(stmt)
        auto = res.scalar_one_or_none()
        if not auto:
            raise ResourceNotFoundException(f"Automation '{automation_id}' not found.")

        if data.name is not None:
            auto.name = data.name.strip()
        if data.description is not None:
            auto.description = data.description
        if data.natural_instruction is not None:
            auto.natural_instruction = data.natural_instruction
        if data.trigger_type is not None:
            auto.trigger_type = data.trigger_type.value
        if data.schedule_config is not None:
            auto.schedule_config = json.dumps(data.schedule_config)
        if data.timezone is not None:
            tz = get_safe_timezone(data.timezone)
            auto.timezone = tz.key if hasattr(tz, "key") else str(tz)
        if data.approval_policy is not None:
            auto.approval_policy = data.approval_policy
        if data.is_enabled is not None:
            auto.is_enabled = data.is_enabled

        if data.actions is not None:
            for action in data.actions:
                if not ToolRegistry.has(action.tool):
                    raise ValidationException(f"Tool '{action.tool}' is not registered in ToolRegistry.")
            actions_data = [a.model_dump() for a in data.actions]
            auto.actions_json = json.dumps(actions_data)
            tools_list = data.associated_tools or [a.tool for a in data.actions]
            auto.associated_tools = json.dumps(list(dict.fromkeys(tools_list)))

        # Recompute next_run_at
        if auto.is_enabled:
            sched_cfg = json.loads(auto.schedule_config)
            auto.next_run_at = compute_next_run_at(
                trigger_type=auto.trigger_type,
                schedule_config=sched_cfg,
                tz_name=auto.timezone,
            )
        else:
            auto.next_run_at = None

        await db.commit()
        await db.refresh(auto)
        return cls._to_response(auto)

    @classmethod
    async def delete_automation(cls, db: AsyncSession, automation_id: str) -> bool:
        stmt = select(Automation).where(Automation.id == automation_id)
        res = await db.execute(stmt)
        auto = res.scalar_one_or_none()
        if not auto:
            raise ResourceNotFoundException(f"Automation '{automation_id}' not found.")

        await db.delete(auto)
        await db.commit()
        logger.info(f"Deleted automation '{automation_id}'")
        return True

    @classmethod
    async def set_enabled(cls, db: AsyncSession, automation_id: str, enabled: bool) -> AutomationResponse:
        stmt = select(Automation).where(Automation.id == automation_id)
        res = await db.execute(stmt)
        auto = res.scalar_one_or_none()
        if not auto:
            raise ResourceNotFoundException(f"Automation '{automation_id}' not found.")

        auto.is_enabled = enabled
        if enabled:
            sched_cfg = json.loads(auto.schedule_config)
            auto.next_run_at = compute_next_run_at(
                trigger_type=auto.trigger_type,
                schedule_config=sched_cfg,
                tz_name=auto.timezone,
            )
        else:
            auto.next_run_at = None

        await db.commit()
        await db.refresh(auto)
        return cls._to_response(auto)

    @classmethod
    async def trigger_run(
        cls,
        db: AsyncSession,
        automation_id: str,
        trigger_type: str = "manual",
        force_skip_approval: bool = False,
        approval_id: Optional[str] = None,
        background: bool = True,
    ) -> AutomationExecutionResponse:
        """
        Dispatches an execution for the given automation.
        Enforces idempotency, creates an execution record, and dispatches via Celery
        or executes with asynchronous fallback if Celery is unavailable.
        """
        stmt = select(Automation).where(Automation.id == automation_id)
        res = await db.execute(stmt)
        auto = res.scalar_one_or_none()
        if not auto:
            raise ResourceNotFoundException(f"Automation '{automation_id}' not found.")

        exec_id = str(uuid.uuid4())
        idempotency_key = f"{automation_id}:{int(time.time() * 1000)}"

        execution = AutomationExecution(
            id=exec_id,
            automation_id=auto.id,
            trigger_type=trigger_type,
            idempotency_key=idempotency_key,
            status=ExecutionStatus.QUEUED.value,
            actions_snapshot=auto.actions_json,
            approval_id=approval_id,
            retry_count=0,
            max_retries=3,
        )
        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        # If synchronous immediate execution is requested (e.g. manual Run Now)
        if not background:
            from app.automations.executor import AutomationExecutor
            await AutomationExecutor.execute(
                execution_id=exec_id,
                db=db,
                approval_id=approval_id,
                force_skip_approval=force_skip_approval,
            )
            await db.refresh(execution)
            return cls._to_execution_response(execution)

        # Dispatch via Celery or Fallback for asynchronous execution
        dispatched_celery = False
        try:
            from app.tasks.celery_app import celery_app, run_automation_celery_task
            # Try to dispatch to Celery
            run_automation_celery_task.delay(
                execution_id=exec_id,
                approval_id=approval_id,
                force_skip_approval=force_skip_approval,
            )
            dispatched_celery = True
            logger.info(f"Dispatched automation execution {exec_id} to Celery worker.")
        except Exception as exc:
            logger.info(f"Celery dispatch failed ({exc}), falling back to direct asynchronous executor.")

        if not dispatched_celery:
            from app.automations.executor import AutomationExecutor
            import asyncio
            from app.database.session import async_session_factory

            async def _bg_run():
                async with async_session_factory() as sess:
                    await AutomationExecutor.execute(
                        execution_id=exec_id,
                        db=sess,
                        approval_id=approval_id,
                        force_skip_approval=force_skip_approval,
                    )
            asyncio.create_task(_bg_run())

        return cls._to_execution_response(execution)

    @classmethod
    async def dispatch_due_automations(cls, db: AsyncSession) -> List[str]:
        """
        Finds all active automations that are due for execution (next_run_at <= now)
        and dispatches them.
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        stmt = select(Automation).where(
            Automation.is_enabled == True,
            Automation.next_run_at != None,
            Automation.next_run_at <= now_utc,
        )
        res = await db.execute(stmt)
        due_automations = res.scalars().all()

        dispatched_ids: List[str] = []
        for auto in due_automations:
            # Advance next_run_at immediately to avoid duplicate dispatch
            sched_cfg = json.loads(auto.schedule_config) if auto.schedule_config else {}
            auto.next_run_at = compute_next_run_at(
                trigger_type=auto.trigger_type,
                schedule_config=sched_cfg,
                tz_name=auto.timezone,
            )
            await db.commit()

            exec_resp = await cls.trigger_run(
                db=db,
                automation_id=auto.id,
                trigger_type="scheduled",
                background=True,
            )
            dispatched_ids.append(exec_resp.id)

        return dispatched_ids

    @classmethod
    async def list_executions(
        cls,
        db: AsyncSession,
        automation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AutomationExecutionResponse]:
        stmt = select(AutomationExecution).order_by(AutomationExecution.created_at.desc())
        if automation_id:
            stmt = stmt.where(AutomationExecution.automation_id == automation_id)
        if status:
            stmt = stmt.where(AutomationExecution.status == status)
        stmt = stmt.offset(offset).limit(limit)

        res = await db.execute(stmt)
        executions = res.scalars().all()
        return [cls._to_execution_response(e) for e in executions]

    @classmethod
    async def get_execution(cls, db: AsyncSession, execution_id: str) -> AutomationExecutionResponse:
        stmt = select(AutomationExecution).where(AutomationExecution.id == execution_id)
        res = await db.execute(stmt)
        exec_record = res.scalar_one_or_none()
        if not exec_record:
            raise ResourceNotFoundException(f"Automation execution '{execution_id}' not found.")
        return cls._to_execution_response(exec_record)

    @classmethod
    async def cancel_execution(cls, db: AsyncSession, execution_id: str) -> AutomationExecutionResponse:
        stmt = select(AutomationExecution).where(AutomationExecution.id == execution_id)
        res = await db.execute(stmt)
        exec_record = res.scalar_one_or_none()
        if not exec_record:
            raise ResourceNotFoundException(f"Automation execution '{execution_id}' not found.")

        if exec_record.status in ("SUCCEEDED", "FAILED", "CANCELLED", "SKIPPED"):
            return cls._to_execution_response(exec_record)

        exec_record.status = "CANCELLED"
        exec_record.completed_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(exec_record)
        return cls._to_execution_response(exec_record)

    @classmethod
    async def get_stats(cls, db: AsyncSession) -> AutomationStatsResponse:
        # Total automations
        tot_stmt = select(func.count(Automation.id))
        total_automations = (await db.execute(tot_stmt)).scalar() or 0

        # Active automations
        active_stmt = select(func.count(Automation.id)).where(Automation.is_enabled == True)
        active_automations = (await db.execute(active_stmt)).scalar() or 0

        # Paused automations
        paused_automations = total_automations - active_automations

        # Failed executions
        fail_stmt = select(func.count(AutomationExecution.id)).where(AutomationExecution.status == "FAILED")
        failed_executions = (await db.execute(fail_stmt)).scalar() or 0

        # Next scheduled run
        next_stmt = select(func.min(Automation.next_run_at)).where(
            Automation.is_enabled == True,
            Automation.next_run_at != None,
        )
        next_scheduled_run = (await db.execute(next_stmt)).scalar()

        # Recent executions
        rec_stmt = select(func.count(AutomationExecution.id))
        recent_count = (await db.execute(rec_stmt)).scalar() or 0

        return AutomationStatsResponse(
            total_automations=total_automations,
            active_automations=active_automations,
            paused_automations=paused_automations,
            failed_executions=failed_executions,
            next_scheduled_run=next_scheduled_run,
            recent_executions_count=recent_count,
        )

    @classmethod
    def _to_response(cls, auto: Automation) -> AutomationResponse:
        actions_raw = json.loads(auto.actions_json) if auto.actions_json else []
        tools_raw = json.loads(auto.associated_tools) if auto.associated_tools else []
        sched_raw = json.loads(auto.schedule_config) if auto.schedule_config else {}

        actions = [
            AutomationAction(
                tool=a.get("tool", ""),
                arguments=a.get("arguments", {}),
                description=a.get("description"),
            )
            for a in actions_raw
        ]

        return AutomationResponse(
            id=auto.id,
            name=auto.name,
            description=auto.description,
            natural_instruction=auto.natural_instruction,
            trigger_type=TriggerType(auto.trigger_type),
            schedule_config=sched_raw,
            timezone=auto.timezone,
            is_enabled=auto.is_enabled,
            actions=actions,
            associated_tools=tools_raw,
            approval_policy=auto.approval_policy,
            next_run_at=auto.next_run_at,
            last_run_at=auto.last_run_at,
            last_status=auto.last_status,
            execution_count=auto.execution_count,
            consecutive_failures=auto.consecutive_failures,
            owner_identity=auto.owner_identity,
            created_at=auto.created_at,
            updated_at=auto.updated_at,
        )

    @classmethod
    def _to_execution_response(cls, e: AutomationExecution) -> AutomationExecutionResponse:
        actions_snapshot = json.loads(e.actions_snapshot) if e.actions_snapshot else []
        results = json.loads(e.results_json) if e.results_json else None
        context = json.loads(e.execution_context) if e.execution_context else None

        return AutomationExecutionResponse(
            id=e.id,
            automation_id=e.automation_id,
            trigger_type=e.trigger_type,
            idempotency_key=e.idempotency_key,
            status=ExecutionStatus(e.status),
            actions_snapshot=actions_snapshot,
            results=results,
            execution_context=context,
            error_message=e.error_message,
            approval_id=e.approval_id,
            retry_count=e.retry_count,
            max_retries=e.max_retries,
            started_at=e.started_at,
            completed_at=e.completed_at,
            duration_ms=e.duration_ms,
            worker_id=e.worker_id,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
