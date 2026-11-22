import json
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import SystemMetadata
from app.core.logging import logger


class CommunicationStyle(str, Enum):
    NATURAL = "natural"
    CONCISE = "concise"
    TECHNICAL = "technical"
    DETAILED = "detailed"


class FormalityLevel(str, Enum):
    BALANCED = "balanced"
    CASUAL = "casual"
    FORMAL = "formal"


class DetailLevel(str, Enum):
    BALANCED = "balanced"
    CONCISE = "concise"
    IN_DEPTH = "in_depth"


class MemoryUsageMode(str, Enum):
    NATURAL_WEAVE = "natural_weave"
    MINIMAL = "minimal"
    EXPLICIT = "explicit"


class EmojiUsage(str, Enum):
    MINIMAL = "minimal"
    NONE = "none"
    EXPRESSIVE = "expressive"


class AssistantPersonalityConfig(BaseModel):
    name: str = Field(default="Personal AI Assistant", max_length=64)
    communication_style: CommunicationStyle = CommunicationStyle.NATURAL
    formality: FormalityLevel = FormalityLevel.BALANCED
    detail_level: DetailLevel = DetailLevel.BALANCED
    memory_usage: MemoryUsageMode = MemoryUsageMode.NATURAL_WEAVE
    emoji_usage: EmojiUsage = EmojiUsage.MINIMAL
    custom_instructions: Optional[str] = Field(default=None, max_length=2000)


class PersonalityService:
    CONFIG_KEY = "assistant_personality"

    @classmethod
    async def get_personality(cls, session: AsyncSession) -> AssistantPersonalityConfig:
        """
        Retrieves active assistant personality settings from system_metadata.
        Falls back to default config if not configured.
        """
        try:
            stmt = select(SystemMetadata).where(SystemMetadata.key == cls.CONFIG_KEY)
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            if entry and entry.value:
                data = json.loads(entry.value)
                return AssistantPersonalityConfig(**data)
        except Exception as exc:
            logger.warning(f"Failed to load assistant personality config, using default: {exc}")

        return AssistantPersonalityConfig()

    @classmethod
    async def update_personality(
        cls,
        config: AssistantPersonalityConfig,
        session: AsyncSession,
    ) -> AssistantPersonalityConfig:
        """
        Persists assistant personality settings to system_metadata.
        """
        stmt = select(SystemMetadata).where(SystemMetadata.key == cls.CONFIG_KEY)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()

        serialized = config.model_dump_json()

        if entry:
            entry.value = serialized
            entry.description = "Configurable assistant personality and communication style settings"
        else:
            entry = SystemMetadata(
                key=cls.CONFIG_KEY,
                value=serialized,
                description="Configurable assistant personality and communication style settings",
            )
            session.add(entry)

        await session.commit()
        await session.refresh(entry)
        return config
