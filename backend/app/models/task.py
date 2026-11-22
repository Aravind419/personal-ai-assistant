import uuid
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class BackgroundTask(Base, TimestampMixin):
    """
    Persistent execution log and lifecycle record for asynchronous background tasks
    (Celery jobs, memory extraction, vector reindexing, maintenance).
    """
    __tablename__ = "background_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Task status: queued, running, succeeded, failed, cancelled
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    
    input_params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    started_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<BackgroundTask id={self.id} type={self.task_type!r} status={self.status!r}>"
