from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.automations.schemas import (
    AutomationCreate,
    AutomationUpdate,
    AutomationResponse,
    AutomationExecutionResponse,
    AutomationStatsResponse,
    ParseInstructionRequest,
    ParseInstructionResponse,
    ManualRunRequest,
)
from app.automations.service import AutomationService
from app.automations.parser import AutomationInstructionParser

router = APIRouter(prefix="/automations", tags=["Automations"])


@router.post("", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
async def create_automation(
    payload: AutomationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new automation workflow."""
    return await AutomationService.create_automation(db, payload)


@router.get("", response_model=List[AutomationResponse])
async def list_automations(
    is_enabled: Optional[bool] = Query(None, description="Filter by active status"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all configured automations."""
    return await AutomationService.list_automations(
        db, is_enabled=is_enabled, trigger_type=trigger_type, limit=limit, offset=offset
    )


@router.get("/stats", response_model=AutomationStatsResponse)
async def get_automation_stats(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve summary metrics and status for the automations dashboard."""
    return await AutomationService.get_stats(db)


@router.post("/parse", response_model=ParseInstructionResponse)
async def parse_automation_instruction(
    payload: ParseInstructionRequest,
):
    """
    Parse a natural language instruction into structured automation configuration,
    validating requested tools against the ToolRegistry.
    """
    return AutomationInstructionParser.parse(payload.instruction, user_timezone=payload.timezone)


@router.get("/executions", response_model=List[AutomationExecutionResponse])
async def list_all_executions(
    status: Optional[str] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List execution history across all automations."""
    return await AutomationService.list_executions(
        db, automation_id=None, status=status, limit=limit, offset=offset
    )


@router.get("/executions/{execution_id}", response_model=AutomationExecutionResponse)
async def get_execution_details(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific automation execution."""
    return await AutomationService.get_execution(db, execution_id)


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve an automation by ID."""
    return await AutomationService.get_automation(db, automation_id)


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: str,
    payload: AutomationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing automation configuration."""
    return await AutomationService.update_automation(db, automation_id, payload)


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    automation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete an automation and its execution history."""
    await AutomationService.delete_automation(db, automation_id)
    return None


@router.post("/{automation_id}/enable", response_model=AutomationResponse)
async def enable_automation(
    automation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Enable a paused automation and schedule its next execution."""
    return await AutomationService.set_enabled(db, automation_id, enabled=True)


@router.post("/{automation_id}/disable", response_model=AutomationResponse)
async def disable_automation(
    automation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Disable/pause an active automation."""
    return await AutomationService.set_enabled(db, automation_id, enabled=False)


@router.post("/{automation_id}/run", response_model=AutomationExecutionResponse)
async def run_automation_now(
    automation_id: str,
    payload: Optional[ManualRunRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Trigger immediate manual execution of an automation."""
    force_skip = payload.force_skip_approval if payload else False
    return await AutomationService.trigger_run(
        db=db,
        automation_id=automation_id,
        trigger_type="manual",
        force_skip_approval=force_skip,
        background=False,  # Return directly for immediate response in manual run API
    )


@router.post("/executions/{execution_id}/cancel", response_model=AutomationExecutionResponse)
async def cancel_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or queued automation execution."""
    return await AutomationService.cancel_execution(db, execution_id)


@router.get("/{automation_id}/executions", response_model=List[AutomationExecutionResponse])
async def list_automation_executions(
    automation_id: str,
    status: Optional[str] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List execution history for a specific automation."""
    return await AutomationService.list_executions(
        db, automation_id=automation_id, status=status, limit=limit, offset=offset
    )
