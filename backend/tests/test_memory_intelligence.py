import pytest
from httpx import AsyncClient
from app.database.session import async_session_factory
from app.memory.extraction import (
    is_sensitive_or_trivial,
    extract_heuristic_candidates,
    extract_and_reconcile_memories,
)
from app.memory.retrieval import retrieve_relevant_memory_context
from app.memory.service import MemoryService
from app.memory.schemas import MemoryCreate


@pytest.mark.asyncio
async def test_sensitive_and_trivial_filtering():
    # Sensitive items should be filtered
    assert is_sensitive_or_trivial("My password is SuperSecret123!") is True
    assert is_sensitive_or_trivial("API_KEY: sk-abcdef1234567890abcdef1234567890") is True
    assert is_sensitive_or_trivial("Use Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6") is True

    # Trivial chatter should be filtered
    assert is_sensitive_or_trivial("hello") is True
    assert is_sensitive_or_trivial("thanks") is True
    assert is_sensitive_or_trivial("ok") is True

    # Real knowledge should NOT be filtered
    assert is_sensitive_or_trivial("I prefer writing clean asynchronous Python 3.13 code.") is False
    assert is_sensitive_or_trivial("My active project is developing the personal AI assistant.") is False


@pytest.mark.asyncio
async def test_memory_extraction_and_conflict_superseding():
    async with async_session_factory() as session:
        # Step 1: Initial conversation turn
        user_msg_1 = "I am working on my project is personal assistant app and my goal is to learn React."
        assistant_resp_1 = "That sounds like a great plan!"

        memories_1 = await extract_and_reconcile_memories(
            user_message=user_msg_1,
            assistant_response=assistant_resp_1,
            conversation_id=None,
            message_id=None,
            session=session,
        )
        assert len(memories_1) >= 1
        initial_goal_mem = next((m for m in memories_1 if m.category == "goals"), None)
        assert initial_goal_mem is not None
        assert "React" in initial_goal_mem.content

        # Step 2: Subsequent conversation turn with superseding information
        user_msg_2 = "Update: my goal is to learn Flutter and mobile architecture."
        assistant_resp_2 = "Great progress transitioning to Flutter!"

        memories_2 = await extract_and_reconcile_memories(
            user_message=user_msg_2,
            assistant_response=assistant_resp_2,
            conversation_id=None,
            message_id=None,
            session=session,
        )
        assert len(memories_2) >= 1
        updated_goal_mem = next((m for m in memories_2 if m.category == "goals"), None)
        assert updated_goal_mem is not None
        # Should supersede the goal with Flutter
        assert "Flutter" in updated_goal_mem.content

        # Verify historical trace in metadata
        fetched = await MemoryService.get_memory(session, updated_goal_mem.id)
        if fetched.metadata:
            assert "history" in fetched.metadata or "previous_content" in str(fetched.metadata)

        # Cleanup
        for m in memories_1 + memories_2:
            try:
                await MemoryService.delete_memory(session, m.id)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_memory_context_retrieval_and_formatting():
    async with async_session_factory() as session:
        # Create unique memory
        mem = await MemoryService.create_memory(
            session,
            MemoryCreate(
                content="User prefers using PostgreSQL with pgvector for vector search.",
                category="technical_knowledge",
                importance=0.9,
                confidence=0.95,
            ),
        )

        try:
            # Query relevant context
            ctx = await retrieve_relevant_memory_context(
                query="Tell me about the user vector search and PostgreSQL database preference.",
                session=session,
                threshold=0.30,
            )
            assert "<retrieved_context>" in ctx
            assert "</retrieved_context>" in ctx
            assert "PostgreSQL" in ctx or "pgvector" in ctx
            assert "Technical Knowledge" in ctx

            # Unrelated query should return empty or not overwhelm
            unrelated_ctx = await retrieve_relevant_memory_context(
                query="What is the speed of light in deep space vacuum?",
                session=session,
                threshold=0.50,
            )
            assert "PostgreSQL" not in unrelated_ctx

        finally:
            await MemoryService.delete_memory(session, mem.id)
