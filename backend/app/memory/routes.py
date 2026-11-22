from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.memory.schemas import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    MemoryListResponse,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryStatsResponse,
)
from app.memory.service import MemoryService

router = APIRouter(prefix="/memories", tags=["Semantic Memory"])


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new persistent memory item with vector embedding."""
    return await MemoryService.create_memory(db, data)


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search memory content text"),
    is_archived: Optional[bool] = Query(False, description="Filter by archived status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List persistent memories with optional category filtering and search."""
    return await MemoryService.list_memories(
        session=db,
        category=category,
        search=search,
        is_archived=is_archived,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve aggregate statistics and category distribution for memories."""
    return await MemoryService.get_stats(db)


@router.post("/search", response_model=List[MemorySearchResult])
async def search_memories(
    query_data: MemorySearchQuery,
    db: AsyncSession = Depends(get_db),
):
    """Execute semantic vector search against stored memories using pgvector."""
    return await MemoryService.search_memories(
        session=db,
        query=query_data.query,
        category=query_data.category,
        limit=query_data.limit,
        threshold=query_data.threshold,
        include_archived=query_data.include_archived,
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single memory item by ID."""
    return await MemoryService.get_memory(db, memory_id)


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    data: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a memory's content, category, importance, or archived status."""
    return await MemoryService.update_memory(db, memory_id, data)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a memory and its vector embedding."""
    await MemoryService.delete_memory(db, memory_id)


@router.post("/{memory_id}/archive", response_model=MemoryResponse)
async def toggle_archive_memory(
    memory_id: str,
    is_archived: bool = Query(True, description="Archive status"),
    db: AsyncSession = Depends(get_db),
):
    """Archive or unarchive a memory."""
    return await MemoryService.archive_memory(db, memory_id, is_archived=is_archived)
