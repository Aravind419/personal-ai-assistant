import re
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Memory
from app.memory.schemas import MemoryCreate, MemoryResponse, MemoryCategory
from app.memory.service import MemoryService, _to_memory_response
from app.memory.repository import MemoryRepository
from app.memory.embeddings import get_default_embedding_provider, cosine_similarity
from app.core.logging import logger


# Sensitive pattern detector to prevent saving secrets into long-term memory
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)\b(password|passwd|pwd|api[_-]?key|secret[_-]?key|access[_-]?token)\b(\s*[:=]|\s+is\s+)\S+"),
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}"),
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),  # Credit card numbers
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),       # SSN
]

# Trivial conversational chatter patterns
CHATTER_PATTERNS = [
    re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay|cool|bye|goodbye|see you)[.!]?$", re.IGNORECASE),
]


def is_sensitive_or_trivial(text: str) -> bool:
    """Returns True if text contains credentials, keys, or is purely trivial chatter."""
    clean = text.strip()
    if len(clean) < 8:
        return True

    for chatter in CHATTER_PATTERNS:
        if chatter.match(clean):
            return True

    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(clean):
            logger.info("Filtered sensitive information pattern from memory candidate")
            return True

    return False


def extract_heuristic_candidates(user_text: str, assistant_text: str) -> List[Dict[str, Any]]:
    """
    Fast rule-based heuristic extractor extracting durable preferences, profile items,
    learning goals, and active project information.
    """
    candidates: List[Dict[str, Any]] = []

    # 1. Preferences
    pref_patterns = [
        (r"(?i)\b(?:i prefer|i like to|i always use|i enjoy)\s+([^.!?\n]{5,120})", MemoryCategory.PREFERENCES.value, 0.8),
        (r"(?i)\b(?:i dislike|i avoid|i hate|don't ever use)\s+([^.!?\n]{5,120})", MemoryCategory.PREFERENCES.value, 0.8),
    ]
    for pattern, cat, imp in pref_patterns:
        matches = re.finditer(pattern, user_text)
        for m in matches:
            content = f"User preference: {m.group(0).strip()}."
            if not is_sensitive_or_trivial(content):
                candidates.append({"content": content, "category": cat, "importance": imp, "confidence": 0.9})

    # 2. Profile
    profile_patterns = [
        (r"(?i)\b(?:my name is|i am a|i work as|i live in)\s+([^.!?\n]{3,80})", MemoryCategory.PROFILE.value, 0.9),
    ]
    for pattern, cat, imp in profile_patterns:
        matches = re.finditer(pattern, user_text)
        for m in matches:
            content = f"User profile: {m.group(0).strip()}."
            if not is_sensitive_or_trivial(content):
                candidates.append({"content": content, "category": cat, "importance": imp, "confidence": 0.95})

    # 3. Projects
    project_patterns = [
        (r"(?i)\b(?:i am building|i am working on|my project is|we are developing)\s+([^.!?\n]{5,120})", MemoryCategory.PROJECTS.value, 0.85),
    ]
    for pattern, cat, imp in project_patterns:
        matches = re.finditer(pattern, user_text)
        for m in matches:
            content = f"Active project: {m.group(0).strip()}."
            if not is_sensitive_or_trivial(content):
                candidates.append({"content": content, "category": cat, "importance": imp, "confidence": 0.9})

    # 4. Goals & Learning
    goal_patterns = [
        (r"(?i)\b(?:my goal is|i want to learn|i am learning|i have completed)\s+([^.!?\n]{5,120})", MemoryCategory.GOALS.value, 0.75),
    ]
    for pattern, cat, imp in goal_patterns:
        matches = re.finditer(pattern, user_text)
        for m in matches:
            content = f"User goal: {m.group(0).strip()}."
            if not is_sensitive_or_trivial(content):
                candidates.append({"content": content, "category": cat, "importance": imp, "confidence": 0.85})

    # 5. Technical Knowledge from Assistant confirmations
    tech_patterns = [
        (r"(?i)\b(?:decided to use|architecture decision|configured to use)\s+([^.!?\n]{5,120})", MemoryCategory.TECHNICAL_KNOWLEDGE.value, 0.8),
    ]
    for pattern, cat, imp in tech_patterns:
        matches = re.finditer(pattern, user_text + " " + assistant_text)
        for m in matches:
            content = f"Technical knowledge: {m.group(0).strip()}."
            if not is_sensitive_or_trivial(content):
                candidates.append({"content": content, "category": cat, "importance": imp, "confidence": 0.85})

    return candidates


async def reconcile_and_store_memory(
    candidate: Dict[str, Any],
    conversation_id: Optional[str],
    message_id: Optional[str],
    session: AsyncSession,
) -> MemoryResponse:
    """
    Evaluates a candidate memory against existing memories in the database:
    - If near-identical (similarity >= 0.85): updates confidence, last_accessed_at, or supersedes previous fact.
    - If new/distinct: stores as a new memory.
    """
    content = candidate["content"].strip()
    category = candidate.get("category", MemoryCategory.GENERAL.value).strip().lower()
    importance = float(candidate.get("importance", 0.5))
    confidence = float(candidate.get("confidence", 0.9))

    provider = get_default_embedding_provider()
    embedding = await provider.embed_text(content)

    # Check for existing similar memory in the same category
    existing_matches = await MemoryRepository.vector_search(
        session=session,
        query_vector=embedding,
        category=category,
        limit=3,
        threshold=0.80,
        include_archived=False,
    )

    now = datetime.now(timezone.utc)

    if existing_matches:
        top_mem, top_sim = existing_matches[0]
        logger.info(f"Existing memory match found (similarity={top_sim:.3f}): '{top_mem.content}'")

        # Conflict / Superseding check:
        # If new text has different content but high similarity, check if it updates or supersedes
        if top_mem.content.lower() != content.lower():
            # Update existing memory with superseding content
            prev_meta = {}
            if top_mem.metadata_json:
                try:
                    prev_meta = json.loads(top_mem.metadata_json)
                except Exception:
                    pass

            history = prev_meta.get("history", [])
            history.append({
                "previous_content": top_mem.content,
                "superseded_at": now.isoformat(),
            })
            prev_meta["history"] = history
            prev_meta["last_updated_reason"] = "superseded_by_newer_conversation"

            top_mem.content = content
            top_mem.embedding = embedding
            top_mem.importance = max(top_mem.importance, importance)
            top_mem.confidence = confidence
            top_mem.last_accessed_at = now
            top_mem.metadata_json = json.dumps(prev_meta)
            top_mem.source_conversation_id = conversation_id or top_mem.source_conversation_id
            top_mem.source_message_id = message_id or top_mem.source_message_id

            updated = await MemoryRepository.update(session, top_mem)
            return _to_memory_response(updated)
        else:
            # Identical fact confirmed again: bump confidence slightly and touch last_accessed_at
            top_mem.confidence = min(1.0, top_mem.confidence + 0.05)
            top_mem.last_accessed_at = now
            updated = await MemoryRepository.update(session, top_mem)
            return _to_memory_response(updated)

    # Distinct memory: save fresh
    new_mem = Memory(
        content=content,
        category=category,
        embedding=embedding,
        importance=importance,
        confidence=confidence,
        source_conversation_id=conversation_id,
        source_message_id=message_id,
        embedding_model=provider.model_name,
        embedding_dim=len(embedding),
        last_accessed_at=now,
    )
    saved = await MemoryRepository.create(session, new_mem)
    return _to_memory_response(saved)


async def extract_and_reconcile_memories(
    user_message: str,
    assistant_response: str,
    conversation_id: Optional[str],
    message_id: Optional[str],
    session: AsyncSession,
) -> List[MemoryResponse]:
    """
    Main extraction orchestrator:
    Extracts durable candidates, sanitizes secrets, reconciles duplicates, and persists.
    """
    if is_sensitive_or_trivial(user_message):
        return []

    candidates = extract_heuristic_candidates(user_message, assistant_response)
    if not candidates:
        return []

    saved_memories: List[MemoryResponse] = []
    for cand in candidates:
        try:
            mem = await reconcile_and_store_memory(
                candidate=cand,
                conversation_id=conversation_id,
                message_id=message_id,
                session=session,
            )
            saved_memories.append(mem)
        except Exception as exc:
            logger.error(f"Failed to reconcile and store memory candidate: {exc}")

    return saved_memories
