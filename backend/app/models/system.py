import uuid
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin


class SystemMetadata(Base, TimestampMixin):
    """
    Initial foundation table storing application state, schema version,
    and system status parameters.
    """
    __tablename__ = "system_metadata"

    key: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemMetadata key={self.key}>"
