import json
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Memory
from app.memory.embeddings import cosine_similarity


class MemoryRepository:
    """
    Data access layer for Semantic Memory entities and pgvector vector search.
    """

    @staticmethod
    async def create(session: AsyncSession, memory: Memory) -> Memory:
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        return memory

    @staticmethod
    async def get_by_id(session: AsyncSession, memory_id: str) -> Optional[Memory]:
        stmt = select(Memory).where(Memory.id == memory_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update(session: AsyncSession, memory: Memory) -> Memory:
        memory.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(memory)
        return memory

    @staticmethod
    async def delete(session: AsyncSession, memory_id: str) -> bool:
        stmt = delete(Memory).where(Memory.id == memory_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_memories(
        session: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_archived: Optional[bool] = False,
        temporal_scope: Optional[str] = None,
        is_current: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Memory], int]:
        filters = []
        if is_archived is not None:
            filters.append(Memory.is_archived == is_archived)
        if is_current is not None:
            filters.append(Memory.is_current == is_current)
        if temporal_scope and temporal_scope.strip():
            filters.append(Memory.temporal_scope == temporal_scope.strip().lower())
        if category and category.strip():
            filters.append(Memory.category == category.strip().lower())
        if search and search.strip():
            search_pattern = f"%{search.strip().lower()}%"
            filters.append(func.lower(Memory.content).like(search_pattern))

        # Total count query
        count_stmt = select(func.count(Memory.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total_res = await session.execute(count_stmt)
        total = total_res.scalar() or 0

        # Items query
        items_stmt = select(Memory)
        if filters:
            items_stmt = items_stmt.where(and_(*filters))
        items_stmt = items_stmt.order_by(Memory.importance.desc(), Memory.created_at.desc())
        items_stmt = items_stmt.limit(limit).offset(offset)

        result = await session.execute(items_stmt)
        memories = list(result.scalars().all())
        return memories, total

    @staticmethod
    async def get_stats(session: AsyncSession) -> Dict[str, Any]:
        # Active vs Archived counts
        active_stmt = select(func.count(Memory.id)).where(Memory.is_archived == False)
        archived_stmt = select(func.count(Memory.id)).where(Memory.is_archived == True)
        
        active_res = await session.execute(active_stmt)
        archived_res = await session.execute(archived_stmt)
        
        total_active = active_res.scalar() or 0
        total_archived = archived_res.scalar() or 0

        # Category distribution for active memories
        cat_stmt = (
            select(Memory.category, func.count(Memory.id))
            .where(Memory.is_archived == False)
            .group_by(Memory.category)
        )
        cat_res = await session.execute(cat_stmt)
        category_distribution = {cat: count for cat, count in cat_res.all()}

        # 5 most recent memories
        recent_stmt = (
            select(Memory)
            .where(Memory.is_archived == False)
            .order_by(Memory.created_at.desc())
            .limit(5)
        )
        recent_res = await session.execute(recent_stmt)
        recent_memories = list(recent_res.scalars().all())

        return {
            "total_active": total_active,
            "total_archived": total_archived,
            "category_distribution": category_distribution,
            "recent_memories": recent_memories,
        }

    @staticmethod
    async def vector_search(
        session: AsyncSession,
        query_vector: List[float],
        category: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.4,
        include_archived: bool = False,
    ) -> List[Tuple[Memory, float]]:
        """
        Executes semantic vector search using pgvector cosine distance `<=>`.
        Returns matching memories and their calculated cosine similarity scores.
        """
        filters = []
        if not include_archived:
            filters.append(Memory.is_archived == False)
        if category and category.strip():
            filters.append(Memory.category == category.strip().lower())
        filters.append(Memory.embedding != None)

        try:
            # Native pgvector cosine distance
            cosine_dist = Memory.embedding.cosine_distance(query_vector)
            stmt = (
                select(Memory, cosine_dist.label("distance"))
                .where(and_(*filters))
                .order_by(cosine_dist.asc())
                .limit(limit * 2)  # fetch buffer for threshold check
            )
            result = await session.execute(stmt)
            rows = result.all()
            
            matched = []
            for mem, dist in rows:
                dist_val = float(dist) if dist is not None else 1.0
                similarity = max(0.0, min(1.0, 1.0 - dist_val))
                if similarity >= threshold:
                    matched.append((mem, similarity))
                if len(matched) >= limit:
                    break
            return matched

        except Exception:
            # Fallback for environments where native pgvector operator is unavailable
            stmt = select(Memory).where(and_(*filters)).limit(100)
            result = await session.execute(stmt)
            memories = result.scalars().all()

            scored = []
            for mem in memories:
                if mem.embedding is not None:
                    sim = cosine_similarity(query_vector, list(mem.embedding))
                    if sim >= threshold:
                        scored.append((mem, sim))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:limit]
