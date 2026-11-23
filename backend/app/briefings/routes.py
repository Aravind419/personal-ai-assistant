from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.briefings.service import BriefingService, BriefingResponse

router = APIRouter(prefix="/briefings", tags=["Briefings"])


@router.get("/latest", response_model=Optional[BriefingResponse])
async def get_latest_briefing(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the most recently generated briefing."""
    return await BriefingService.get_latest_briefing(db)


@router.get("", response_model=List[BriefingResponse])
async def list_briefings(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List historical briefings."""
    return await BriefingService.list_briefings(db, limit=limit, offset=offset)


@router.get("/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(
    briefing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details and Markdown content for a specific briefing."""
    return await BriefingService.get_briefing(db, briefing_id)


@router.post("/generate", response_model=BriefingResponse, status_code=status.HTTP_201_CREATED)
async def generate_briefing_now(
    db: AsyncSession = Depends(get_db),
):
    """Generate a fresh morning briefing immediately on demand."""
    return await BriefingService.generate_morning_briefing(db)
