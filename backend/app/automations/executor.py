import uuid
import json
import time
import socket
import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.automation import (
    Automation,
    AutomationExecution,
    Notification,
)
from app.models.tool import ToolApproval
from app.tools.base import ToolRegistry, BaseTool
from app.tools.engine import ToolExecutionEngine
from app.tools.permissions import ToolPermissionEngine
from app.tools.approval_manager import ApprovalManager
from app.tools.schemas import PermissionLevel, ExecutionStatus as ToolExecStatus, ApprovalStatus
from app.automations.schemas import ExecutionStatus
from app.automations.scheduler_utils import compute_next_run_at
from app.core.logging import logger


class AutomationExecutor:
    """
    Executes automation workflows with step-by-step tool dispatch,
    idempotency enforcement, permission gating, and approval pausing.
    """

    @classmethod
    async def execute(
        cls,
        execution_id: str,
        db: AsyncSession,
        approval_id: Optional[str] = None,
        force_skip_approval: bool = False,
    ) -> AutomationExecution:
        start_time = time.perf_counter()
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        stmt = select(AutomationExecution).where(AutomationExecution.id == execution_id)
        res = await db.execute(stmt)
        exec_record = res.scalar_one_or_none()
        if not exec_record:
            raise ValueError(f"Execution {execution_id} not found.")

        stmt_auto = select(Automation).where(Automation.id == exec_record.automation_id)
        res_auto = await db.execute(stmt_auto)
        auto = res_auto.scalar_one_or_none()
        if not auto:
            raise ValueError(f"Automation {exec_record.automation_id} not found.")

        # Update status to RUNNING
        exec_record.status = ExecutionStatus.RUNNING.value
        exec_record.started_at = now_utc
        exec_record.worker_id = socket.gethostname()
        await db.commit()

        actions_list = json.loads(exec_record.actions_snapshot) if exec_record.actions_snapshot else []
        results: List[Dict[str, Any]] = []

        try:
            for step_idx, action_item in enumerate(actions_list):
                tool_id = action_item.get("tool")
                raw_args = action_item.get("arguments", {})

                tool = ToolRegistry.get(tool_id)
                if not tool:
                    raise ValueError(f"Step {step_idx + 1}: Tool '{tool_id}' is not registered.")

                # Evaluate permissions
                # If approval_id is passed, check if it matches this step
                is_auth, denial_reason, approval = await ToolPermissionEngine.evaluate_execution(
                    tool=tool,
                    arguments=raw_args,
                    approval_id=approval_id,
                    force_skip_approval=force_skip_approval,
                    db=db,
                )

                if not is_auth:
                    # Sensitive or Critical action requiring approval
                    risk_level = tool.risk_classification if hasattr(tool, "risk_classification") else "medium"
                    action_name = f"automation_step_{step_idx + 1}_{tool.id}"

                    new_approval = await ApprovalManager.create_approval(
                        tool_id=tool.id,
                        tool_name=tool.name,
                        action=action_name,
                        arguments=raw_args,
                        permission_level=tool.permission_level,
                        risk_level=risk_level,
                        reason=denial_reason or f"Automation '{auto.name}' requested action '{tool.name}'",
                        target_resource=action_item.get("description"),
                        expected_consequences=f"Step {step_idx + 1} of automation '{auto.name}'",
                        requested_by="automation_executor",
                        db=db,
                    )

                    exec_record.status = ExecutionStatus.WAITING_FOR_APPROVAL.value
                    exec_record.approval_id = new_approval.id
                    exec_record.execution_context = json.dumps({
                        "paused_at_step": step_idx,
                        "tool_id": tool_id,
                        "approval_id": new_approval.id,
                        "results_so_far": results,
                    })
                    exec_record.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    auto.last_status = "waiting_for_approval"

                    # Create Notification
                    notif = Notification(
                        id=str(uuid.uuid4()),
                        title=f"Approval Required: {auto.name}",
                        message=f"Automation '{auto.name}' paused at step '{tool.name}'. Please approve or reject.",
                        notification_type="automation_waiting_for_approval",
                        severity="warning",
                        automation_id=auto.id,
                        execution_id=exec_record.id,
                        metadata_json=json.dumps({"approval_id": new_approval.id, "tool": tool.id}),
                    )
                    db.add(notif)
                    await db.commit()
                    await db.refresh(exec_record)
                    logger.info(f"Execution {exec_record.id} paused waiting for approval {new_approval.id}")
                    return exec_record

                # Action is authorized: Execute tool
                step_idemp = f"{exec_record.id}:step_{step_idx}"
                exec_resp = await ToolExecutionEngine.execute_tool(
                    tool_id=tool_id,
                    arguments=raw_args,
                    approval_id=approval_id,
                    idempotency_key=step_idemp,
                    force_skip_approval=force_skip_approval,
                    user_identity="automation_executor",
                    db=db,
                )

                results.append({
                    "step": step_idx + 1,
                    "tool": tool_id,
                    "success": exec_resp.success,
                    "result": exec_resp.result,
                    "duration_ms": exec_resp.duration_ms,
                })

                if not exec_resp.success:
                    raise RuntimeError(f"Step {step_idx + 1} ({tool_id}) failed: {exec_resp.result}")

            # All steps succeeded
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            exec_record.status = ExecutionStatus.SUCCEEDED.value
            exec_record.completed_at = datetime.datetime.now(datetime.timezone.utc)
            exec_record.duration_ms = duration
            exec_record.results_json = json.dumps(results)

            # Update automation statistics
            auto.last_run_at = exec_record.completed_at
            auto.last_status = "succeeded"
            auto.execution_count += 1
            auto.consecutive_failures = 0

            # Advance next_run_at
            sched_cfg = json.loads(auto.schedule_config) if auto.schedule_config else {}
            auto.next_run_at = compute_next_run_at(
                trigger_type=auto.trigger_type,
                schedule_config=sched_cfg,
                tz_name=auto.timezone,
            )

            # Create completion notification
            notif = Notification(
                id=str(uuid.uuid4()),
                title=f"Automation Completed: {auto.name}",
                message=f"Successfully executed all {len(actions_list)} steps in {duration}ms.",
                notification_type="automation_completed",
                severity="success",
                automation_id=auto.id,
                execution_id=exec_record.id,
            )
            db.add(notif)

            await db.commit()
            await db.refresh(exec_record)
            logger.info(f"Execution {exec_record.id} succeeded in {duration}ms.")
            return exec_record

        except Exception as exc:
            duration = round((time.perf_counter() - start_time) * 1000, 2)
            err_msg = str(exc)
            logger.error(f"Execution {exec_record.id} failed: {err_msg}")

            exec_record.status = ExecutionStatus.FAILED.value
            exec_record.completed_at = datetime.datetime.now(datetime.timezone.utc)
            exec_record.duration_ms = duration
            exec_record.error_message = err_msg
            exec_record.results_json = json.dumps(results)

            auto.last_run_at = exec_record.completed_at
            auto.last_status = "failed"
            auto.consecutive_failures += 1

            # Advance next_run_at for recurring tasks
            sched_cfg = json.loads(auto.schedule_config) if auto.schedule_config else {}
            auto.next_run_at = compute_next_run_at(
                trigger_type=auto.trigger_type,
                schedule_config=sched_cfg,
                tz_name=auto.timezone,
            )

            notif = Notification(
                id=str(uuid.uuid4()),
                title=f"Automation Failed: {auto.name}",
                message=f"Execution error: {err_msg}",
                notification_type="automation_failed",
                severity="error",
                automation_id=auto.id,
                execution_id=exec_record.id,
            )
            db.add(notif)

            await db.commit()
            await db.refresh(exec_record)
            return exec_record
