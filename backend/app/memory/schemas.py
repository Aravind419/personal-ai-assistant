from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MemoryCategory(str, Enum):
    # Core User Domain Categories (ChatGPT-style Intelligent Categories)
    PERSONAL_IDENTITY = "personal_identity"
    PERSONAL_FACTS = "personal_facts"
    RELATIONSHIPS = "relationships"
    LOCATION = "location"
    EDUCATION = "education"
    CAREER = "career"
    CAREER_GOALS = "career_goals"
    TECHNICAL_SKILLS = "technical_skills"
    PREFERENCES = "preferences"
    PROJECTS = "projects"
    ACTIVITIES_AND_EVENTS = "activities_and_events"
    IMPORTANT_EVENTS = "important_events"
    DECISIONS_AND_PLANS = "decisions_and_plans"
    DECISIONS = "decisions"
    ONGOING_ACTIVITIES = "ongoing_activities"
    COMMUNICATION_PREFERENCES = "communication_preferences"
    RELEVANT_CONTEXT = "relevant_context"
    OTHER_CONTEXT = "other_context"

    # Backward-compatible existing aliases
    PROFILE = "profile"
    TECHNICAL_KNOWLEDGE = "technical_knowledge"
    GOALS = "goals"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    GENERAL = "general"


class MemoryBase(BaseModel):
    content: str = Field(..., min_length=1, description="Meaningful extracted knowledge or fact.")
    category: str = Field(default=MemoryCategory.GENERAL.value, description="Memory category.")
    subcategory: Optional[str] = Field(None, description="Optional subcategory (e.g. current_location, friend).")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score from 0.0 to 1.0.")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0.")
    source_conversation_id: Optional[str] = Field(None, description="Optional UUID of origin conversation.")
    source_message_id: Optional[str] = Field(None, description="Optional UUID of origin message.")
    temporal_scope: str = Field(default="permanent", description="Temporal scope: current, permanent, temporary, previous.")
    valid_from: Optional[datetime] = Field(None, description="Timestamp from which memory became valid.")
    valid_until: Optional[datetime] = Field(None, description="Expiration or obsolescence timestamp.")
    is_current: bool = Field(default=True, description="Whether memory represents active current state.")
    original_statement: Optional[str] = Field(None, description="Original user statement or source quote.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional custom metadata/attributes.")


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, description="Updated memory text.")
    category: Optional[str] = Field(None, description="Updated category.")
    subcategory: Optional[str] = Field(None, description="Updated subcategory.")
    importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated importance score.")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated confidence score.")
    temporal_scope: Optional[str] = Field(None, description="Updated temporal scope.")
    valid_from: Optional[datetime] = Field(None, description="Updated valid from.")
    valid_until: Optional[datetime] = Field(None, description="Updated valid until.")
    is_current: Optional[bool] = Field(None, description="Updated current state flag.")
    is_archived: Optional[bool] = Field(None, description="Archive or unarchive flag.")
    original_statement: Optional[str] = Field(None, description="Updated original statement.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata.")


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    category: str
    subcategory: Optional[str] = None
    importance: float
    confidence: float
    source_conversation_id: Optional[str] = None
    source_message_id: Optional[str] = None
    temporal_scope: str = "permanent"
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_current: bool = True
    original_statement: Optional[str] = None
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_archived: bool
    embedding_model: str
    embedding_dim: int
    metadata_json: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
    limit: int
    offset: int


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0).")
    relevance_score: float = Field(..., description="Combined multi-factor retrieval score.")


class MemorySearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query text.")
    category: Optional[str] = Field(None, description="Filter by category.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of memories to retrieve.")
    threshold: float = Field(default=0.4, ge=0.0, le=1.0, description="Minimum similarity threshold.")
    include_archived: bool = Field(default=False, description="Include archived memories.")


class MemoryStatsResponse(BaseModel):
    total_active: int
    total_archived: int
    category_distribution: Dict[str, int]
    recent_memories: List[MemoryResponse]
