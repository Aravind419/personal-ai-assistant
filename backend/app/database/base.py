from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime


class Base(DeclarativeBase):
    """Base model for all SQLAlchemy models."""
    pass


class TimestampMixin:
    """Reusable mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
