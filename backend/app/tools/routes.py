import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.database.session import get_db
from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import (
    ToolDefinitionResponse,
    ToolExecuteRequest,
    ToolExecutionResponse,
    ToolExecutionSummary,
    ApprovalResponse,
    ApprovalDecisionRequest,
    McpServerCreate,
    McpServerUpdate,
    McpServerResponse,
    ExecutionStatus,
    ApprovalStatus,
)
from app.tools.engine import ToolExecutionEngine
from app.tools.approval_manager import ApprovalManager
from app.tools.mcp import McpServerManager
from app.models.tool import ToolExecution, ToolApproval, McpServerConfiguration
from app.core.exceptions import ResourceNotFoundException, ValidationException

tools_router = APIRouter(prefix="/tools", tags=["Tools"])
approvals_router = APIRouter(prefix="/approvals", tags=["Approvals"])


# ==========================================
# Tools Endpoints
# ==========================================

@tools_router.get("", response_model=List[ToolDefinitionResponse], summary="List all registered tools")
async def list_tools():
    return ToolRegistry.list_all_definitions()


@tools_router.get("/health", summary="Tools engine and MCP servers health status")
async def get_tools_health(db: AsyncSession = Depends(get_db)):
    tools = ToolRegistry.list_all_definitions()
    stmt = select(McpServerConfiguration)
    res = await db.execute(stmt)
    servers = res.scalars().all()

    return {
        "status": "healthy",
        "total_tools_count": len(tools),
        "enabled_tools_count": sum(1 for t in tools if t.is_enabled),
        "mcp_servers_count": len(servers),
        "connected_mcp_servers": sum(1 for s in servers if s.status == "connected"),
    }


@tools_router.get("/{tool_id}", response_model=ToolDefinitionResponse, summary="Get single tool definition")
async def get_tool(tool_id: str):
    tool = ToolRegistry.get(tool_id)
    if not tool:
        raise ResourceNotFoundException(f"Tool '{tool_id}' not found.")
    defn = tool.to_definition_response()
    if not ToolRegistry.is_enabled(tool.name):
        defn.is_enabled = False
    return defn


@tools_router.post("/{tool_id}/execute", response_model=ToolExecutionResponse, summary="Execute a tool directly")
async def execute_tool(
    tool_id: str,
    payload: ToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    return await ToolExecutionEngine.execute_tool(
        tool_id=tool_id,
        arguments=payload.arguments,
        conversation_id=payload.conversation_id,
        idempotency_key=payload.idempotency_key,
        force_skip_approval=payload.force_skip_approval,
        db=db,
    )


@tools_router.get("/executions/history", response_model=List[ToolExecutionSummary], summary="List tool execution history")
async def list_executions(
    status: Optional[str] = None,
    tool_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ToolExecution).order_by(ToolExecution.started_at.desc())
    if status:
        stmt = stmt.where(ToolExecution.status == status)
    if tool_id:
        stmt = stmt.where(ToolExecution.tool_id == tool_id)
    if conversation_id:
        stmt = stmt.where(ToolExecution.conversation_id == conversation_id)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    records = result.scalars().all()

    summaries = []
    for r in records:
        req_args = {}
        try:
            req_args = json.loads(r.requested_arguments)
        except Exception:
            pass

        res_summary = None
        if r.result_json:
            res_summary = r.result_json[:200]
            if len(r.result_json) > 200:
                res_summary += "..."

        summaries.append(
            ToolExecutionSummary(
                id=r.id,
                conversation_id=r.conversation_id,
                tool_id=r.tool_id,
                tool_name=r.tool_name,
                requested_arguments=req_args,
                status=ExecutionStatus(r.status),
                approval_id=r.approval_id,
                started_at=r.started_at,
                completed_at=r.completed_at,
                duration_ms=r.duration_ms,
                result_summary=res_summary,
                error_details=r.error_details,
                user_identity=r.user_identity,
                execution_environment=r.execution_environment,
            )
        )
    return summaries


@tools_router.get("/executions/{execution_id}", response_model=ToolExecutionResponse, summary="Get execution details")
async def get_execution_details(execution_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ToolExecution).where(ToolExecution.id == execution_id)
    res = await db.execute(stmt)
    r = res.scalar_one_or_none()
    if not r:
        raise ResourceNotFoundException(f"Execution {execution_id} not found.")

    parsed_result = None
    if r.result_json:
        try:
            parsed_result = json.loads(r.result_json)
        except Exception:
            parsed_result = r.result_json

    return ToolExecutionResponse(
        id=r.id,
        tool_id=r.tool_id,
        tool_name=r.tool_name,
        status=ExecutionStatus(r.status),
        success=(r.status == ExecutionStatus.SUCCEEDED.value),
        result=parsed_result,
        error=r.error_details,
        duration_ms=r.duration_ms,
        approval_id=r.approval_id,
        approval_required=(r.status == ExecutionStatus.AWAITING_APPROVAL.value),
        started_at=r.started_at,
        completed_at=r.completed_at,
    )


# ==========================================
# MCP Server Management Endpoints
# ==========================================

@tools_router.get("/mcp/servers", response_model=List[McpServerResponse], summary="List configured MCP servers")
async def list_mcp_servers(db: AsyncSession = Depends(get_db)):
    stmt = select(McpServerConfiguration).order_by(McpServerConfiguration.created_at.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


@tools_router.post("/mcp/servers", response_model=McpServerResponse, status_code=status.HTTP_201_CREATED, summary="Add MCP server")
async def create_mcp_server(payload: McpServerCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(McpServerConfiguration).where(McpServerConfiguration.name == payload.name))
    if existing.scalar_one_or_none():
        raise ValidationException(f"MCP server with name '{payload.name}' already exists.")

    server = McpServerConfiguration(
        id=str(uuid.uuid4()),
        name=payload.name,
        server_type=payload.server_type,
        command=payload.command,
        args_json=json.dumps(payload.args) if payload.args else None,
        url=payload.url,
        headers_json=json.dumps(payload.headers) if payload.headers else None,
        env_json=json.dumps(payload.env) if payload.env else None,
        is_enabled=payload.is_enabled,
        status="disconnected",
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@tools_router.post("/mcp/servers/{server_id}/discover", summary="Discover tools from MCP server")
async def discover_mcp_tools(server_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(McpServerConfiguration).where(McpServerConfiguration.id == server_id)
    res = await db.execute(stmt)
    server = res.scalar_one_or_none()
    if not server:
        raise ResourceNotFoundException(f"MCP server {server_id} not found.")

    count = await McpServerManager.discover_and_register_server(server, db)
    return {
        "server_id": server.id,
        "name": server.name,
        "status": server.status,
        "discovered_tools_count": count,
    }


@tools_router.patch("/mcp/servers/{server_id}", response_model=McpServerResponse, summary="Update MCP server")
async def update_mcp_server(server_id: str, payload: McpServerUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(McpServerConfiguration).where(McpServerConfiguration.id == server_id)
    res = await db.execute(stmt)
    server = res.scalar_one_or_none()
    if not server:
        raise ResourceNotFoundException(f"MCP server {server_id} not found.")

    if payload.name is not None:
        server.name = payload.name
    if payload.command is not None:
        server.command = payload.command
    if payload.args is not None:
        server.args_json = json.dumps(payload.args)
    if payload.url is not None:
        server.url = payload.url
    if payload.headers is not None:
        server.headers_json = json.dumps(payload.headers)
    if payload.env is not None:
        server.env_json = json.dumps(payload.env)
    if payload.is_enabled is not None:
        server.is_enabled = payload.is_enabled
        if not server.is_enabled:
            server.status = "disabled"

    await db.commit()
    await db.refresh(server)
    return server


@tools_router.delete("/mcp/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete MCP server")
async def delete_mcp_server(server_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(McpServerConfiguration).where(McpServerConfiguration.id == server_id)
    res = await db.execute(stmt)
    server = res.scalar_one_or_none()
    if not server:
        raise ResourceNotFoundException(f"MCP server {server_id} not found.")

    await db.delete(server)
    await db.commit()


# ==========================================
# Human-in-the-Loop Approvals Endpoints
# ==========================================

def _to_approval_response(app: ToolApproval) -> ApprovalResponse:
    args_dict = {}
    try:
        args_dict = json.loads(app.arguments_json)
    except Exception:
        pass

    return ApprovalResponse(
        id=app.id,
        conversation_id=app.conversation_id,
        tool_id=app.tool_id,
        tool_name=app.tool_name,
        action=app.action,
        arguments=args_dict,
        arguments_hash=app.arguments_hash,
        target_resource=app.target_resource,
        expected_consequences=app.expected_consequences,
        permission_level=app.permission_level,
        risk_level=app.risk_level,
        reason=app.reason,
        status=ApprovalStatus(app.status),
        created_at=app.created_at,
        expires_at=app.expires_at,
        decided_at=app.decided_at,
        decided_by=app.decided_by,
        decision_reason=app.decision_reason,
        execution_id=app.execution_id,
    )


@approvals_router.get("", response_model=List[ApprovalResponse], summary="List approval requests")
async def list_approvals(
    status: Optional[str] = None,
    tool_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    apps = await ApprovalManager.list_approvals(
        db=db,
        status=status,
        tool_id=tool_id,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )
    return [_to_approval_response(a) for a in apps]


@approvals_router.get("/{approval_id}", response_model=ApprovalResponse, summary="Get approval details")
async def get_approval(approval_id: str, db: AsyncSession = Depends(get_db)):
    app = await ApprovalManager.get_approval(approval_id, db)
    return _to_approval_response(app)


@approvals_router.post("/{approval_id}/approve", summary="Approve action with optional execution")
async def approve_action(
    approval_id: str,
    payload: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    db: AsyncSession = Depends(get_db),
):
    app = await ApprovalManager.approve(
        approval_id=approval_id,
        db=db,
        decided_by="user",
        decision_reason=payload.reason or "Explicit user approval granted.",
    )

    execution_result = None
    if payload.execute_now:
        args = {}
        try:
            args = json.loads(app.arguments_json)
        except Exception:
            pass

        execution_result = await ToolExecutionEngine.execute_tool(
            tool_id=app.tool_id,
            arguments=args,
            conversation_id=app.conversation_id,
            approval_id=app.id,
            db=db,
        )

    return {
        "approval": _to_approval_response(app),
        "execution": execution_result,
    }


@approvals_router.post("/{approval_id}/reject", response_model=ApprovalResponse, summary="Reject action")
async def reject_action(
    approval_id: str,
    payload: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    db: AsyncSession = Depends(get_db),
):
    app = await ApprovalManager.reject(
        approval_id=approval_id,
        db=db,
        decided_by="user",
        decision_reason=payload.reason or "Rejected by user.",
    )
    return _to_approval_response(app)


@approvals_router.post("/{approval_id}/cancel", response_model=ApprovalResponse, summary="Cancel approval request")
async def cancel_action(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
):
    app = await ApprovalManager.cancel(
        approval_id=approval_id,
        db=db,
        decided_by="user",
    )
    return _to_approval_response(app)
