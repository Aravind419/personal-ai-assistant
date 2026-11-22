import uuid
import time
import json
import asyncio
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import (
    ExecutionStatus,
    ToolExecutionResponse,
    PermissionLevel,
)
from app.tools.validator import ToolSchemaValidator, SecretSanitizer, CanonicalArgumentHasher
from app.tools.permissions import ToolPermissionEngine
from app.tools.approval_manager import ApprovalManager
from app.models.tool import ToolExecution, ToolApproval
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import logger


class ToolExecutionEngine:
    """
    Centralized, provider-independent Tool Execution Engine.
    Coordinates schema validation, permission checks, approval gating,
    timeouts, retries, idempotency, and audit logging.
    """

    @classmethod
    async def execute_tool(
        cls,
        tool_id: str,
        arguments: Dict[str, Any],
        conversation_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        force_skip_approval: bool = False,
        user_identity: str = "personal_user",
        db: Optional[AsyncSession] = None,
    ) -> ToolExecutionResponse:
        start_time = time.perf_counter()
        now = datetime.datetime.now(datetime.timezone.utc)

        # 1. Lookup tool in registry
        tool: Optional[BaseTool] = ToolRegistry.get(tool_id)
        if not tool:
            raise ResourceNotFoundException(f"Tool '{tool_id}' is not registered.")

        # 2. Check Idempotency Key
        if idempotency_key and db:
            stmt = select(ToolExecution).where(
                ToolExecution.idempotency_key == idempotency_key,
                ToolExecution.status == ExecutionStatus.SUCCEEDED.value,
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                logger.info(f"Idempotent tool execution match found for key: {idempotency_key}")
                parsed_res = None
                if existing.result_json:
                    try:
                        parsed_res = json.loads(existing.result_json)
                    except Exception:
                        parsed_res = existing.result_json
                return ToolExecutionResponse(
                    id=existing.id,
                    tool_id=existing.tool_id,
                    tool_name=existing.tool_name,
                    status=ExecutionStatus.SUCCEEDED,
                    success=True,
                    result=parsed_res,
                    duration_ms=existing.duration_ms,
                    approval_id=existing.approval_id,
                    approval_required=False,
                    started_at=existing.started_at,
                    completed_at=existing.completed_at,
                )

        # 3. Strict Schema Validation
        valid, err_msg = ToolSchemaValidator.validate(tool.parameters_schema, arguments)
        if not valid:
            exec_id = str(uuid.uuid4())
            sanitized_args = json.dumps(SecretSanitizer.sanitize_dict(arguments))
            if db:
                failed_exec = ToolExecution(
                    id=exec_id,
                    conversation_id=conversation_id,
                    tool_id=tool.id,
                    tool_name=tool.name,
                    requested_arguments=sanitized_args,
                    validated_arguments="{}",
                    status=ExecutionStatus.FAILED.value,
                    started_at=now,
                    completed_at=datetime.datetime.now(datetime.timezone.utc),
                    duration_ms=0.0,
                    error_details=err_msg,
                    idempotency_key=idempotency_key,
                    user_identity=user_identity,
                    execution_environment=tool.execution_environment.value,
                )
                db.add(failed_exec)
                await db.commit()

            return ToolExecutionResponse(
                id=exec_id,
                tool_id=tool.id,
                tool_name=tool.name,
                status=ExecutionStatus.FAILED,
                success=False,
                error=err_msg,
                duration_ms=0.0,
                approval_required=False,
                started_at=now,
                completed_at=now,
            )

        # 4. Permission & Approval Evaluation
        is_authorized, reason, approval = await ToolPermissionEngine.evaluate_execution(
            tool=tool,
            arguments=arguments,
            approval_id=approval_id,
            force_skip_approval=force_skip_approval,
            db=db,
        )

        sanitized_args = json.dumps(SecretSanitizer.sanitize_dict(arguments))
        canonical_args = CanonicalArgumentHasher.serialize_canonical(arguments)

        if not is_authorized:
            # Need approval or rejected
            active_approval = approval
            if not active_approval and db:
                # Create a new approval request
                active_approval = await ApprovalManager.create_approval(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    action=f"execute_{tool.name}",
                    arguments=arguments,
                    permission_level=tool.permission_level,
                    risk_level=tool.risk_classification,
                    reason=reason or "Human confirmation required.",
                    target_resource=tool.extract_target_resource(arguments),
                    expected_consequences=tool.build_consequence_summary(arguments),
                    conversation_id=conversation_id,
                    requested_by=user_identity,
                    db=db,
                )

            exec_id = str(uuid.uuid4())
            if db:
                awaiting_exec = ToolExecution(
                    id=exec_id,
                    conversation_id=conversation_id,
                    tool_id=tool.id,
                    tool_name=tool.name,
                    requested_arguments=sanitized_args,
                    validated_arguments=canonical_args,
                    status=ExecutionStatus.AWAITING_APPROVAL.value,
                    approval_id=active_approval.id if active_approval else None,
                    started_at=now,
                    idempotency_key=idempotency_key,
                    user_identity=user_identity,
                    execution_environment=tool.execution_environment.value,
                )
                db.add(awaiting_exec)
                if active_approval:
                    active_approval.execution_id = exec_id
                await db.commit()

            return ToolExecutionResponse(
                id=exec_id,
                tool_id=tool.id,
                tool_name=tool.name,
                status=ExecutionStatus.AWAITING_APPROVAL,
                success=False,
                error=reason,
                approval_id=active_approval.id if active_approval else None,
                approval_required=True,
                started_at=now,
            )

        # 5. Authorized Execution
        exec_id = str(uuid.uuid4())
        execution_record = None
        if db:
            if approval:
                # Atomically claim the approval so it can never be executed twice
                try:
                    await ApprovalManager.mark_approval_executed(approval.id, exec_id, db)
                except ValidationException as claim_err:
                    return ToolExecutionResponse(
                        id=exec_id,
                        tool_id=tool.id,
                        tool_name=tool.name,
                        status=ExecutionStatus.FAILED,
                        success=False,
                        error=str(claim_err.message),
                        approval_id=approval.id,
                        approval_required=False,
                        started_at=now,
                        completed_at=datetime.datetime.now(datetime.timezone.utc),
                    )

            execution_record = ToolExecution(
                id=exec_id,
                conversation_id=conversation_id,
                tool_id=tool.id,
                tool_name=tool.name,
                requested_arguments=sanitized_args,
                validated_arguments=canonical_args,
                status=ExecutionStatus.RUNNING.value,
                approval_id=approval.id if approval else None,
                started_at=now,
                idempotency_key=idempotency_key,
                user_identity=user_identity,
                execution_environment=tool.execution_environment.value,
            )
            db.add(execution_record)
            await db.commit()

        # 6. Run tool with timeout
        exec_status = ExecutionStatus.SUCCEEDED
        raw_result = None
        err_msg = None
        try:
            raw_result = await asyncio.wait_for(
                tool.run(**arguments),
                timeout=tool.timeout_seconds,
            )
        except asyncio.TimeoutError:
            exec_status = ExecutionStatus.TIMED_OUT
            err_msg = f"Tool '{tool.name}' timed out after {tool.timeout_seconds} seconds."
            logger.warning(err_msg)
        except Exception as exc:
            exec_status = ExecutionStatus.FAILED
            err_msg = f"Tool execution failed: {str(exc)}"
            logger.warning(err_msg)

        completed_at = datetime.datetime.now(datetime.timezone.utc)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        sanitized_result = SecretSanitizer.sanitize_dict(raw_result) if raw_result is not None else None

        # 7. Persist final execution status
        if db and execution_record:
            execution_record.status = exec_status.value
            execution_record.completed_at = completed_at
            execution_record.duration_ms = duration_ms
            execution_record.result_json = json.dumps(sanitized_result) if sanitized_result is not None else None
            execution_record.error_details = err_msg
            await db.commit()

        return ToolExecutionResponse(
            id=exec_id,
            tool_id=tool.id,
            tool_name=tool.name,
            status=exec_status,
            success=(exec_status == ExecutionStatus.SUCCEEDED),
            result=sanitized_result,
            error=err_msg,
            duration_ms=duration_ms,
            approval_id=approval.id if approval else None,
            approval_required=False,
            started_at=now,
            completed_at=completed_at,
        )
