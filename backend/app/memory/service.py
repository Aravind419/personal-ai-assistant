import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Memory
from app.memory.schemas import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    MemoryListResponse,
    MemorySearchResult,
    MemoryStatsResponse,
)
from app.memory.repository import MemoryRepository
from app.memory.embeddings import get_default_embedding_provider
from app.core.exceptions import ResourceNotFoundException, AppException


def _to_memory_response(memory: Memory) -> MemoryResponse:
    parsed_meta = None
    if memory.metadata_json:
        try:
            parsed_meta = json.loads(memory.metadata_json)
        except Exception:
            parsed_meta = None

    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        category=memory.category,
        importance=memory.importance,
        confidence=memory.confidence,
        source_conversation_id=memory.source_conversation_id,
        source_message_id=memory.source_message_id,
        last_accessed_at=memory.last_accessed_at,
        expires_at=memory.expires_at,
        is_archived=memory.is_archived,
        embedding_model=memory.embedding_model,
        embedding_dim=memory.embedding_dim,
        metadata_json=memory.metadata_json,
        metadata=parsed_meta,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


class MemoryService:
    """
    Business service layer for Memory lifecycle, embeddings, and retrieval.
    """

    @classmethod
    async def create_memory(cls, session: AsyncSession, data: MemoryCreate) -> MemoryResponse:
        provider = get_default_embedding_provider()
        embedding = await provider.embed_text(data.content)

        meta_json = json.dumps(data.metadata) if data.metadata else None

        memory = Memory(
            content=data.content.strip(),
            category=data.category.strip().lower(),
            embedding=embedding,
            importance=data.importance,
            confidence=data.confidence,
            source_conversation_id=data.source_conversation_id,
            source_message_id=data.source_message_id,
            embedding_model=provider.model_name,
            embedding_dim=len(embedding),
            metadata_json=meta_json,
        )

        saved = await MemoryRepository.create(session, memory)
        return _to_memory_response(saved)

    @classmethod
    async def get_memory(cls, session: AsyncSession, memory_id: str) -> MemoryResponse:
        memory = await MemoryRepository.get_by_id(session, memory_id)
        if not memory:
            raise ResourceNotFoundException("Memory", memory_id)
        return _to_memory_response(memory)

    @classmethod
    async def update_memory(
        cls, session: AsyncSession, memory_id: str, data: MemoryUpdate
    ) -> MemoryResponse:
        memory = await MemoryRepository.get_by_id(session, memory_id)
        if not memory:
            raise ResourceNotFoundException("Memory", memory_id)

        if data.content is not None and data.content.strip():
            new_content = data.content.strip()
            if new_content != memory.content:
                memory.content = new_content
                provider = get_default_embedding_provider()
                memory.embedding = await provider.embed_text(new_content)
                memory.embedding_model = provider.model_name
                memory.embedding_dim = len(memory.embedding)

        if data.category is not None:
            memory.category = data.category.strip().lower()
        if data.importance is not None:
            memory.importance = data.importance
        if data.confidence is not None:
            memory.confidence = data.confidence
        if data.is_archived is not None:
            memory.is_archived = data.is_archived
        if data.metadata is not None:
            memory.metadata_json = json.dumps(data.metadata)

        updated = await MemoryRepository.update(session, memory)
        return _to_memory_response(updated)

    @classmethod
    async def delete_memory(cls, session: AsyncSession, memory_id: str) -> bool:
        memory = await MemoryRepository.get_by_id(session, memory_id)
        if not memory:
            raise ResourceNotFoundException("Memory", memory_id)
        return await MemoryRepository.delete(session, memory_id)

    @classmethod
    async def archive_memory(
        cls, session: AsyncSession, memory_id: str, is_archived: bool = True
    ) -> MemoryResponse:
        memory = await MemoryRepository.get_by_id(session, memory_id)
        if not memory:
            raise ResourceNotFoundException("Memory", memory_id)
        memory.is_archived = is_archived
        updated = await MemoryRepository.update(session, memory)
        return _to_memory_response(updated)

    @classmethod
    async def list_memories(
        cls,
        session: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_archived: Optional[bool] = False,
        limit: int = 50,
        offset: int = 0,
    ) -> MemoryListResponse:
        memories, total = await MemoryRepository.list_memories(
            session=session,
            category=category,
            search=search,
            is_archived=is_archived,
            limit=limit,
            offset=offset,
        )
        items = [_to_memory_response(m) for m in memories]
        return MemoryListResponse(items=items, total=total, limit=limit, offset=offset)

    @classmethod
    async def get_stats(cls, session: AsyncSession) -> MemoryStatsResponse:
        stats = await MemoryRepository.get_stats(session)
        recent = [_to_memory_response(m) for m in stats["recent_memories"]]
        return MemoryStatsResponse(
            total_active=stats["total_active"],
            total_archived=stats["total_archived"],
            category_distribution=stats["category_distribution"],
            recent_memories=recent,
        )

    @classmethod
    async def search_memories(
        cls,
        session: AsyncSession,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.4,
        include_archived: bool = False,
    ) -> List[MemorySearchResult]:
        provider = get_default_embedding_provider()
        query_vector = await provider.embed_text(query)

        raw_results = await MemoryRepository.vector_search(
            session=session,
            query_vector=query_vector,
            category=category,
            limit=limit,
            threshold=threshold,
            include_archived=include_archived,
        )

        scored_results: List[MemorySearchResult] = []
        now = datetime.now(timezone.utc)

        for memory, similarity in raw_results:
            # Multi-factor score combining semantic similarity, importance, and confidence
            relevance = (
                0.60 * similarity
                + 0.25 * memory.importance
                + 0.15 * memory.confidence
            )
            # Update last accessed time asynchronously
            memory.last_accessed_at = now
            await MemoryRepository.update(session, memory)

            scored_results.append(
                MemorySearchResult(
                    memory=_to_memory_response(memory),
                    similarity_score=round(similarity, 4),
                    relevance_score=round(relevance, 4),
                )
            )

        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_results
