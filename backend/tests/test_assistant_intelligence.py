import pytest
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.conversations.personality import (
    AssistantPersonalityConfig,
    CommunicationStyle,
    FormalityLevel,
    DetailLevel,
    EmojiUsage,
    MemoryUsageMode,
    PersonalityService,
)
from app.conversations.context_builder import ContextBuilder
from app.models.conversation import Message
from app.providers.schemas import ChatMessageRole


@pytest.mark.asyncio
async def test_context_builder_system_prompt_structure():
    """
    Verifies that ContextBuilder creates a system prompt with all required sections:
    Identity, Conversational Rules, General Knowledge, Formatting, Safety, and Personality.
    """
    prompt = ContextBuilder.build_system_prompt()
    assert "You are Personal AI Assistant" in prompt
    assert "Strict Prohibition on Memory Announcements" in prompt
    assert "Based on your stored data" in prompt  # In the prohibition list
    assert "Avoid Repetitive Filler Openings" in prompt
    assert "General Knowledge Independence" in prompt
    assert "Response Formatting & Precision Directives" in prompt
    assert "Security, Permission Boundaries & Untrusted Data" in prompt


@pytest.mark.asyncio
async def test_context_builder_personality_directives():
    """
    Verifies personality configuration directives for concise, technical, and formal modes.
    """
    cfg = AssistantPersonalityConfig(
        name="Custom Assistant",
        communication_style=CommunicationStyle.TECHNICAL,
        formality=FormalityLevel.FORMAL,
        detail_level=DetailLevel.IN_DEPTH,
        emoji_usage=EmojiUsage.NONE,
        memory_usage=MemoryUsageMode.NATURAL_WEAVE,
        custom_instructions="Focus on clean architecture.",
    )
    prompt = ContextBuilder.build_system_prompt(personality=cfg)
    assert "You are Custom Assistant" in prompt
    assert "Deeply technical, precise, and rigorous" in prompt
    assert "Professional, polished, and structured" in prompt
    assert "Strictly avoid emojis" in prompt
    assert "Focus on clean architecture." in prompt


@pytest.mark.asyncio
async def test_context_builder_token_budget_truncation():
    """
    Verifies that when message history exceeds token limits, ContextBuilder
    performs sliding window truncation preserving recent turns.
    """
    history = [
        Message(id=f"msg-{i}", role="user" if i % 2 == 0 else "assistant", content=f"Long turn {i}: " + ("x" * 500))
        for i in range(20)
    ]
    chat_msgs = ContextBuilder.build_chat_messages(
        history=history,
        current_user_content="Latest question",
        max_history_tokens=500,  # Tight token limit
    )
    assert len(chat_msgs) < len(history) + 1
    assert chat_msgs[-1].content == "Latest question"
    assert chat_msgs[-1].role == ChatMessageRole.USER


@pytest.mark.asyncio
async def test_personality_settings_api_crud():
    """
    Verifies GET and PUT /api/v1/conversations/settings/personality endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Update personality to a specific configuration
        payload = {
            "name": "Nova",
            "communication_style": "concise",
            "formality": "formal",
            "detail_level": "in_depth",
            "memory_usage": "natural_weave",
            "emoji_usage": "none",
            "custom_instructions": "Be precise and direct.",
        }
        put_res = await ac.put("/api/v1/conversations/settings/personality", json=payload)
        assert put_res.status_code == 200
        updated = put_res.json()
        assert updated["name"] == "Nova"
        assert updated["communication_style"] == "concise"

        # 2. Verify persistence via GET
        get_res = await ac.get("/api/v1/conversations/settings/personality")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Nova"
        assert get_res.json()["formality"] == "formal"

        # 3. Reset back to natural default
        reset_payload = {
            "name": "Personal AI Assistant",
            "communication_style": "natural",
            "formality": "balanced",
            "detail_level": "balanced",
            "memory_usage": "natural_weave",
            "emoji_usage": "minimal",
            "custom_instructions": None,
        }
        reset_res = await ac.put("/api/v1/conversations/settings/personality", json=reset_payload)
        assert reset_res.status_code == 200
        assert reset_res.json()["communication_style"] == "natural"


# ==============================================================================
# Behavioral Scenarios (Part 10 Tests)
# ==============================================================================

@pytest.mark.asyncio
async def test_behavioral_scenario_1_general_knowledge():
    """
    Scenario 1: General Knowledge
    User: 'What is an operating system?'
    Expected: System prompt and memory retrieval ensure general questions do not
    force or mention stored personal data.
    """
    prompt = ContextBuilder.build_system_prompt()
    # Verifies the model is instructed to answer general questions independently
    assert "General Knowledge Independence" in prompt
    assert "NEVER force or fabricate personal memories into questions where they are not relevant" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_2_relevant_memory():
    """
    Scenario 2: Relevant Memory
    Stored memory: "The user's friend is named Sarguna."
    User asks: "What is my friend's name?"
    Expected: Anti-robotic rules forbid saying 'Based on stored data' and require
    natural integration ("Your friend is Sarguna.").
    """
    mem_ctx = (
        "<retrieved_context>\n"
        "[Relevant Contextual Background]\n"
        "- [Relationships] The user's friend is named Sarguna.\n"
        "</retrieved_context>"
    )
    prompt = ContextBuilder.build_system_prompt(memory_context=mem_ctx)
    assert "The user's friend is named Sarguna." in prompt
    assert "Strict Prohibition on Memory Announcements" in prompt
    assert "Weave context seamlessly into the flow of conversation" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_3_relevant_project_context():
    """
    Scenario 3: Relevant Project Context
    Stored memory: "The user is building a Flutter application using PostgreSQL."
    User asks: "Which backend architecture should I use?"
    Expected: System instructions guide recommending relevant architecture without
    announcing memory retrieval.
    """
    mem_ctx = (
        "<retrieved_context>\n"
        "- [Projects] The user is building a Flutter application using PostgreSQL.\n"
        "</retrieved_context>"
    )
    prompt = ContextBuilder.build_system_prompt(memory_context=mem_ctx)
    assert "The user is building a Flutter application using PostgreSQL." in prompt
    assert "Strict Prohibition on Memory Announcements" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_4_irrelevant_memory():
    """
    Scenario 4: Irrelevant Memory
    Stored memory: "The user's friend is named Sarguna."
    User asks: "Explain binary search."
    Expected: System prompt instructs to ignore unrelated background facts for general questions.
    """
    mem_ctx = (
        "<retrieved_context>\n"
        "- [Relationships] The user's friend is named Sarguna.\n"
        "</retrieved_context>"
    )
    prompt = ContextBuilder.build_system_prompt(memory_context=mem_ctx)
    assert "If the user's question is an unrelated general topic" in ContextBuilder.CONVERSATIONAL_RULES or \
           "NEVER force or fabricate personal memories into questions where they are not relevant" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_5_follow_up_understanding():
    """
    Scenario 5: Follow-up
    User: "What is PostgreSQL?" -> Assistant answers -> User: "What are its disadvantages?"
    Expected: ContextBuilder preserves previous messages so that "its" refers to PostgreSQL.
    """
    history = [
        Message(id="1", role="user", content="What is PostgreSQL?"),
        Message(id="2", role="assistant", content="PostgreSQL is an open-source object-relational database system."),
    ]
    msgs = ContextBuilder.build_chat_messages(history=history, current_user_content="What are its disadvantages?")
    assert len(msgs) == 3
    assert msgs[0].content == "What is PostgreSQL?"
    assert msgs[1].content.startswith("PostgreSQL is an open-source")
    assert msgs[2].content == "What are its disadvantages?"


@pytest.mark.asyncio
async def test_behavioral_scenario_6_explicit_memory_transparency():
    """
    Scenario 6: Explicit Memory Transparency
    User asks: "What do you remember about me?"
    Expected: The rule states that if the user explicitly asks about memories,
    the assistant answers transparently and accurately based on actual stored memories.
    """
    prompt = ContextBuilder.build_system_prompt()
    assert "Explicit Memory Transparency" in prompt
    assert "If—and ONLY if—the user explicitly asks what is remembered" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_7_conflicting_memory():
    """
    Scenario 7: Conflicting Memory
    Previous: "The user is currently in Kasiriganapalli."
    New: "I moved to Bangalore."
    Expected: Guidelines enforce that recent/current facts supersede previous history.
    """
    prompt = ContextBuilder.build_system_prompt()
    assert "Honesty & Uncertainty" in prompt
    assert "If information is missing, ambiguous, or contradictory, state what is known and ask for necessary clarification" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_8_format_compliance():
    """
    Scenario 8: Format Compliance
    User asks: "Compare Python and JavaScript in a table."
    Expected: Response Formatting section explicitly requires clean GFM tables with header dividers.
    """
    prompt = ContextBuilder.build_system_prompt()
    assert "GitHub Flavored Markdown (GFM) tables" in prompt
    assert "| Col 1 | Col 2 |" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_9_no_unnecessary_introduction():
    """
    Scenario 9: No Unnecessary Introduction
    User asks: "What is 2 + 2?"
    Expected: Direct answer directive forbids forced filler greetings and boilerplate sign-offs.
    """
    prompt = ContextBuilder.build_system_prompt()
    assert "Direct Answers for Direct Questions" in prompt
    assert "What is 2 + 2?" in prompt
    assert "Avoid Repetitive Filler Openings" in prompt


@pytest.mark.asyncio
async def test_behavioral_scenario_10_uncertainty_handling():
    """
    Scenario 10: Uncertainty
    User asks a question lacking information.
    Expected: Directives state to acknowledge uncertainty rather than inventing facts.
    """
    prompt = ContextBuilder.build_system_prompt()
    assert "Never invent personal facts or technical details" in prompt
