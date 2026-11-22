import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Float, Integer, Text, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin


class AIModelPolicy(Base, TimestampMixin):
    """
    Persisted policy controlling model execution modes, fallback chains, and cost guardrails.
    Single-user personal configuration.
    """
    __tablename__ = "ai_model_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="free_only",  # "free_only", "paid_enabled", "manual"
    )
    selected_model: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="meta-llama/llama-3.3-70b-instruct:free",
    )
    fallback_models_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["google/gemini-2.0-flash-exp:free", "deepseek/deepseek-chat:free", "qwen/qwen-2.5-coder-32b-instruct:free"]',
    )
    enable_fallback: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_cost_per_request: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    monthly_budget_limit: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)

    def __repr__(self) -> str:
        return f"<AIModelPolicy mode={self.model_mode} model={self.selected_model}>"


class ModelExecutionMetric(Base):
    """
    Tracks token usage, estimated costs, provider errors, latency, and model performance.
    """
    __tablename__ = "model_execution_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    pricing_category: Mapped[str] = mapped_column(String(32), nullable=False)  # "free", "paid"
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "success", "fallback", "error"
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ModelExecutionMetric model={self.model_id} status={self.status} cost=${self.estimated_cost_usd:.6f}>"
