import uuid
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database.base import Base, TimestampMixin
from app.core.config import settings


class Memory(Base, TimestampMixin):
    """
    Semantic Memory entity storing extracted facts, preferences, knowledge,
    and their dense vector embeddings in PostgreSQL via pgvector.
    """
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general", index=True)
    
    # Vector embedding column matching configured dimension (default 384)
    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    
    source_conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_message_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    last_accessed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    embedding_model: Mapped[str] = mapped_column(String(128), default=settings.DEFAULT_EMBEDDING_MODEL, nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, default=settings.EMBEDDING_DIMENSION, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    source_conversation = relationship("Conversation", foreign_keys=[source_conversation_id], lazy="selectin")
    source_message = relationship("Message", foreign_keys=[source_message_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<Memory id={self.id} category={self.category!r} importance={self.importance}>"
