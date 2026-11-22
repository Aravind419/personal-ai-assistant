import pytest
import json
from httpx import AsyncClient
from app.database.session import async_session_factory
from app.memory.extraction import (
    is_sensitive_or_trivial,
    is_question_or_hypothetical,
    extract_heuristic_candidates,
    extract_and_reconcile_memories,
    extract_and_reconcile_memories_with_trace,
)
from app.memory.retrieval import retrieve_relevant_memory_context
from app.memory.service import MemoryService
from app.memory.schemas import MemoryCreate, MemoryCategory
from app.memory.repository import MemoryRepository


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

    # Real personal knowledge should NOT be filtered
    assert is_sensitive_or_trivial("my friend name is sarguna") is False
    assert is_sensitive_or_trivial("My brother studies mechanical engineering") is False
    assert is_sensitive_or_trivial("My birthday is in June") is False
    assert is_sensitive_or_trivial("I am preparing for placements") is False
    assert is_sensitive_or_trivial("I prefer writing clean asynchronous Python 3.13 code.") is False
    assert is_sensitive_or_trivial("My active project is developing the personal AI assistant.") is False
    assert is_sensitive_or_trivial("I am in Kasiriganapalli") is False


@pytest.mark.asyncio
async def test_rejection_of_questions_and_hypotheticals():
    # Questions should not be saved as memories
    q1, r1 = is_question_or_hypothetical("What is the capital of France?")
    assert q1 is True

    q2, r2 = is_question_or_hypothetical("Explain Python loops.")
    assert q2 is True

    q3, r3 = is_question_or_hypothetical("Give me an example of SQL.")
    assert q3 is True

    q4, r4 = is_question_or_hypothetical("What is the weather today?")
    assert q4 is True

    # Python decorator informational query regression
    q5, r5 = is_question_or_hypothetical("What is a python decorator?")
    assert q5 is True

    # Hypothetical scenarios should not be saved as memories
    h1, rh1 = is_question_or_hypothetical("If I had a friend named Bob, would you remember him?")
    assert h1 is True

    h2, rh2 = is_question_or_hypothetical("Suppose that my brother is a doctor, what would he do?")
    assert h2 is True

    # Declarative user facts should NOT be rejected
    d1, _ = is_question_or_hypothetical("my friend name is sarguna")
    assert d1 is False

    d2, _ = is_question_or_hypothetical("I decided to use PostgreSQL")
    assert d2 is False

    d3, _ = is_question_or_hypothetical("i am in kasiriganapalli")
    assert d3 is False

    # Trace test for question rejection
    async with async_session_factory() as session:
        mems, trace = await extract_and_reconcile_memories_with_trace(
            user_message="What is a python decorator?",
            assistant_response="A decorator in Python is a design pattern used to extend the behavior of a function.",
            conversation_id=None,
            message_id=None,
            session=session,
        )
        assert len(mems) == 0
        assert trace["memories_extracted"] == 0
        assert len(trace["rejected_candidates"]) >= 1


@pytest.mark.asyncio
async def test_sarguna_actual_failed_example_regression():
    """
    Regression test verifying the exact user failed example:
    Input:
    {
      'user_content': 'my friend name is sarguna',
      'assistant_content': "Got it! Your friend's name is Sarguna.",
      'conversation_id': 'ea72eb62-5392-4505-bb2a-8ead75f0f5ea',
      'message_id': '596bd71f-b065-4ce4-a2d1-cf4188c788c7'
    }
    """
    async with async_session_factory() as session:
        user_content = "my friend name is sarguna"
        assistant_content = "Got it! Your friend's name is Sarguna."
        conv_id = "ea72eb62-5392-4505-bb2a-8ead75f0f5ea"
        msg_id = "596bd71f-b065-4ce4-a2d1-cf4188c788c7"

        # Clean up any pre-existing test memory with Sarguna to guarantee test isolation
        existing_sargunas, _ = await MemoryRepository.list_memories(session, category="relationships", search="Sarguna")
        for em in existing_sargunas:
            await MemoryService.delete_memory(session, em.id)

        saved_mems, trace = await extract_and_reconcile_memories_with_trace(
            user_message=user_content,
            assistant_response=assistant_content,
            conversation_id=conv_id,
            message_id=msg_id,
            session=session,
        )

        try:
            # 1. Extraction count & trace verification
            assert len(saved_mems) == 1
            assert trace["memories_extracted"] == 1
            assert len(trace["created_memories"]) == 1
            assert len(trace["rejected_candidates"]) == 0
            assert len(trace["filtered_candidates"]) == 0

            # 2. Fact content, category, importance & confidence
            created_detail = trace["created_memories"][0]
            assert created_detail["content"] == "The user's friend is named Sarguna."
            assert created_detail["category"] == MemoryCategory.RELATIONSHIPS.value
            assert created_detail["importance"] == 0.6
            assert created_detail["confidence"] == 0.95
            assert created_detail["status"] == "persisted"

            # 3. Database persistence verification
            persisted_id = created_detail["id"]
            db_mem = await MemoryRepository.get_by_id(session, persisted_id)
            assert db_mem is not None
            assert db_mem.content == "The user's friend is named Sarguna."
            assert db_mem.category == "relationships"
            assert db_mem.importance == 0.6
            assert db_mem.embedding is not None
            assert len(db_mem.embedding) == 384

        finally:
            for m in saved_mems:
                try:
                    await MemoryService.delete_memory(session, m.id)
                except Exception:
                    pass


@pytest.mark.asyncio
async def test_diverse_personal_fact_extraction_examples():
    """Verifies all domain examples from Section 3."""
    test_cases = [
        ("My friend name is Sarguna", "The user's friend is named Sarguna.", "relationships"),
        ("My brother studies mechanical engineering", "The user's brother studies mechanical engineering.", "relationships"),
        ("I am learning Python", "The user is learning Python.", "technical_skills"),
        ("I prefer dark themes", "The user prefers dark themes.", "preferences"),
        ("My birthday is in June", "The user's birthday is in June.", "personal_facts"),
        ("I am preparing for placements", "The user is preparing for placements.", "career_goals"),
        ("I am building a chat application", "The user is building a chat application.", "projects"),
        ("I decided to use PostgreSQL", "The user decided to use PostgreSQL.", "decisions"),
    ]

    for user_msg, expected_content, expected_cat in test_cases:
        candidates = extract_heuristic_candidates(user_msg, "Noted.")
        assert len(candidates) >= 1, f"Failed to extract candidate for: '{user_msg}'"
        match = next((c for c in candidates if c["category"] == expected_cat), candidates[0])
        assert match["content"] == expected_content, f"Content mismatch for '{user_msg}': got '{match['content']}', expected '{expected_content}'"
        assert match["category"] == expected_cat, f"Category mismatch for '{user_msg}': got '{match['category']}', expected '{expected_cat}'"


@pytest.mark.asyncio
async def test_relationship_duplicate_enrichment_and_correction():
    """
    Verifies:
    1. Initial creation of Sarguna
    2. Duplicate detection for 'Sarguna is my friend'
    3. Enrichment for 'Sarguna is my college friend'
    4. Correction handling for 'Actually, my friend's name is Saranya, not Sarguna'
    5. Disambiguation: adding another friend 'My friend name is Rahul' does NOT overwrite Saranya
    """
    async with async_session_factory() as session:
        created_ids = []
        try:
            # 1. Initial creation
            mems_1, trace_1 = await extract_and_reconcile_memories_with_trace(
                user_message="My friend name is Sarguna.",
                assistant_response="Got it!",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_1) == 1
            mem_1 = mems_1[0]
            created_ids.append(mem_1.id)
            assert mem_1.content == "The user's friend is named Sarguna."
            assert len(trace_1["created_memories"]) == 1

            # 2. Duplicate detection
            mems_2, trace_2 = await extract_and_reconcile_memories_with_trace(
                user_message="Sarguna is my friend.",
                assistant_response="Yes, I remember!",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_2) == 1
            assert mems_2[0].id == mem_1.id
            assert len(trace_2["duplicate_memories"]) == 1
            assert len(trace_2["created_memories"]) == 0

            # 3. Enrichment
            mems_3, trace_3 = await extract_and_reconcile_memories_with_trace(
                user_message="Sarguna is my college friend.",
                assistant_response="Nice!",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_3) == 1
            assert mems_3[0].id == mem_1.id
            assert "college friend" in mems_3[0].content
            assert len(trace_3["updated_memories"]) == 1

            # 4. Correction: "Actually, my friend's name is Saranya, not Sarguna."
            mems_4, trace_4 = await extract_and_reconcile_memories_with_trace(
                user_message="Actually, my friend's name is Saranya, not Sarguna.",
                assistant_response="Understood, updated!",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_4) == 1
            assert mems_4[0].id == mem_1.id
            assert mems_4[0].content == "The user's friend is named Saranya."
            assert len(trace_4["updated_memories"]) == 1

            # Verify history in database
            fetched = await MemoryRepository.get_by_id(session, mem_1.id)
            assert "history" in str(fetched.metadata_json)

            # 5. Disambiguation: adding another distinct friend
            mems_5, trace_5 = await extract_and_reconcile_memories_with_trace(
                user_message="My friend name is Rahul.",
                assistant_response="Nice to know Rahul!",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_5) == 1
            mem_rahul = mems_5[0]
            created_ids.append(mem_rahul.id)
            assert mem_rahul.id != mem_1.id
            assert mem_rahul.content == "The user's friend is named Rahul."

            # Verify both friends remain distinct and active
            active_saranya = await MemoryRepository.get_by_id(session, mem_1.id)
            active_rahul = await MemoryRepository.get_by_id(session, mem_rahul.id)
            assert active_saranya.content == "The user's friend is named Saranya."
            assert active_rahul.content == "The user's friend is named Rahul."

        finally:
            for mid in created_ids:
                try:
                    await MemoryService.delete_memory(session, mid)
                except Exception:
                    pass


@pytest.mark.asyncio
async def test_location_intelligence_kasiriganapalli_and_relocation_to_bangalore():
    """
    Verifies Section 4 & Section 11 Location Intelligence:
    1. 'i am in kasiriganapalli' -> classified as location, current_location, temporal_scope: current, is_current: True
    2. 'actually i moved to bangalore' -> marks Kasiriganapalli as previous, is_current: False, and Bangalore as current.
    """
    async with async_session_factory() as session:
        created_ids = []
        try:
            # Turn 1: Current presence in Kasiriganapalli
            mems_1, trace_1 = await extract_and_reconcile_memories_with_trace(
                user_message="i am in kasiriganapalli",
                assistant_response="Understood, noted your current location.",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_1) == 1
            mem_kasiri = mems_1[0]
            created_ids.append(mem_kasiri.id)
            assert mem_kasiri.category == "location"
            assert mem_kasiri.subcategory == "current_location"
            assert mem_kasiri.temporal_scope == "current"
            assert mem_kasiri.is_current is True
            assert "Kasiriganapalli" in mem_kasiri.content

            # Turn 2: Relocation to Bangalore
            mems_2, trace_2 = await extract_and_reconcile_memories_with_trace(
                user_message="actually i moved to bangalore",
                assistant_response="Got it! Updated your current location to Bangalore.",
                conversation_id=None,
                message_id=None,
                session=session,
            )
            assert len(mems_2) == 1
            mem_bangalore = mems_2[0]
            created_ids.append(mem_bangalore.id)
            assert mem_bangalore.category == "location"
            assert mem_bangalore.subcategory == "current_location"
            assert mem_bangalore.temporal_scope == "current"
            assert mem_bangalore.is_current is True
            assert "Bangalore" in mem_bangalore.content

            # Verify historical transition on Kasiriganapalli
            old_mem = await MemoryRepository.get_by_id(session, mem_kasiri.id)
            assert old_mem.temporal_scope == "previous"
            assert old_mem.is_current is False
            meta = json.loads(old_mem.metadata_json or "{}")
            assert "history" in meta
            assert any("relocated" in h.get("reason", "") for h in meta.get("history", []))

        finally:
            for mid in created_ids:
                try:
                    await MemoryService.delete_memory(session, mid)
                except Exception:
                    pass


@pytest.mark.asyncio
async def test_semantic_retrieval_for_location_queries():
    """
    Verifies Section 8:
    Saved memory: 'The user is currently in Kasiriganapalli.'
    Test queries:
    - 'Where am I currently?'
    - 'Which place did I mention?'
    - 'Where is the user?'
    """
    async with async_session_factory() as session:
        mem = await MemoryService.create_memory(
            session=session,
            data=MemoryCreate(
                content="The user is currently in Kasiriganapalli.",
                category="location",
                subcategory="current_location",
                temporal_scope="current",
                is_current=True,
                importance=0.75,
                confidence=0.95,
            ),
        )

        test_queries = [
            "Where am I currently?",
            "Which place did I mention?",
            "Where is the user?",
        ]

        try:
            for q in test_queries:
                ctx = await retrieve_relevant_memory_context(
                    query=q,
                    session=session,
                    threshold=0.20,
                )
                assert "Kasiriganapalli" in ctx, f"Query '{q}' failed to retrieve Kasiriganapalli location context. Got: {ctx}"
                assert "Location" in ctx
        finally:
            await MemoryService.delete_memory(session, mem.id)


@pytest.mark.asyncio
async def test_multi_fact_extraction_in_single_turn():
    """
    Verifies Section 5 & Section 11:
    Extract multiple distinct facts from compound natural language turn:
    'I am studying B.Tech IT and building a Flutter app'
    Should extract:
    1. Education: studies B.Tech IT
    2. Projects: building a Flutter app
    """
    user_msg = "I am studying B.Tech IT and building a Flutter app"
    candidates = extract_heuristic_candidates(user_msg, "Sounds great!")
    assert len(candidates) >= 2, f"Expected at least 2 candidates from compound sentence, got {len(candidates)}"

    categories = [c["category"] for c in candidates]
    assert MemoryCategory.EDUCATION.value in categories
    assert MemoryCategory.PROJECTS.value in categories


@pytest.mark.asyncio
async def test_dual_extraction_strategy_fallback():
    """
    Verifies Section 5:
    Memory extraction executes gracefully using fallback when offline / no LLM key.
    Trace contains 'extraction_strategy'.
    """
    async with async_session_factory() as session:
        mems, trace = await extract_and_reconcile_memories_with_trace(
            user_message="I prefer dark themes",
            assistant_response="Noted!",
            conversation_id=None,
            message_id=None,
            session=session,
        )
        assert len(mems) == 1
        assert "extraction_strategy" in trace
        assert trace["extraction_strategy"] in ["llm", "heuristic"]

        for m in mems:
            try:
                await MemoryService.delete_memory(session, m.id)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_semantic_retrieval_for_sarguna_queries():
    """
    Verifies Section 8 semantic retrieval:
    Saved memory: 'The user's friend is named Sarguna.'
    Test queries:
    - What is my friend's name?
    - Do you remember my friend?
    - Who is Sarguna?
    - Tell me the name of my friend.
    """
    async with async_session_factory() as session:
        mem = await MemoryService.create_memory(
            session=session,
            data=MemoryCreate(
                content="The user's friend is named Sarguna.",
                category="relationships",
                importance=0.6,
                confidence=0.95,
            ),
        )

        test_queries = [
            "What is my friend's name?",
            "Do you remember my friend?",
            "Who is Sarguna?",
            "Tell me the name of my friend.",
        ]

        try:
            for q in test_queries:
                ctx = await retrieve_relevant_memory_context(
                    query=q,
                    session=session,
                )
                assert "Sarguna" in ctx, f"Query '{q}' failed to retrieve memory mentioning Sarguna. Context: {ctx}"
                assert "Relationships" in ctx

        finally:
            await MemoryService.delete_memory(session, mem.id)


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

            # Unrelated query should return empty or not overwhelm
            unrelated_ctx = await retrieve_relevant_memory_context(
                query="What is the speed of light in deep space vacuum?",
                session=session,
                threshold=0.50,
            )
            assert "PostgreSQL" not in unrelated_ctx

        finally:
            await MemoryService.delete_memory(session, mem.id)
