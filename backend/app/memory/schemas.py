from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MemoryCategory(str, Enum):
    PROFILE = "profile"
    PREFERENCES = "preferences"
    PROJECTS = "projects"
    TECHNICAL_KNOWLEDGE = "technical_knowledge"
    GOALS = "goals"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    GENERAL = "general"


class MemoryBase(BaseModel):
    content: str = Field(..., min_length=1, description="Meaningful extracted knowledge or fact.")
    category: str = Field(default=MemoryCategory.GENERAL.value, description="Memory category.")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score from 0.0 to 1.0.")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0.")
    source_conversation_id: Optional[str] = Field(None, description="Optional UUID of origin conversation.")
    source_message_id: Optional[str] = Field(None, description="Optional UUID of origin message.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional custom metadata/attributes.")


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, description="Updated memory text.")
    category: Optional[str] = Field(None, description="Updated category.")
    importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated importance score.")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Updated confidence score.")
    is_archived: Optional[bool] = Field(None, description="Archive or unarchive flag.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata.")


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    category: str
    importance: float
    confidence: float
    source_conversation_id: Optional[str] = None
    source_message_id: Optional[str] = None
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
