import os
from typing import Dict, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.providers.base import BaseLLMProvider
from app.providers.schemas import ProviderType
from app.providers.adapters.openrouter import OpenRouterProvider
from app.providers.adapters.nvidia import NvidiaProvider
from app.providers.adapters.ollama import OllamaProvider
from app.models.provider import ProviderConfiguration
from app.core.security import decrypt_secret
from app.core.logging import logger


class ProviderRegistry:
    """
    Central registry for LLM provider adapters.
    Manages registration, discovery, and instantiation with persisted encrypted credentials.
    """
    _adapters: Dict[ProviderType, Type[BaseLLMProvider]] = {
        ProviderType.OPENROUTER: OpenRouterProvider,
        ProviderType.NVIDIA: NvidiaProvider,
        ProviderType.OLLAMA: OllamaProvider,
    }

    @classmethod
    def register_adapter(cls, provider_type: ProviderType, adapter_cls: Type[BaseLLMProvider]):
        cls._adapters[provider_type] = adapter_cls

    @classmethod
    def list_supported_providers(cls) -> List[ProviderType]:
        return list(cls._adapters.keys())

    @classmethod
    async def get_adapter_instance(
        cls,
        provider_type: ProviderType,
        db: Optional[AsyncSession] = None,
        override_api_key: Optional[str] = None,
        override_base_url: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> BaseLLMProvider:
        adapter_cls = cls._adapters.get(provider_type)
        if not adapter_cls:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        api_key = override_api_key
        base_url = override_base_url
        default_model = override_model

        # If not overridden and DB session provided, load from persisted configuration
        if db is not None:
            stmt = select(ProviderConfiguration).where(ProviderConfiguration.provider_type == provider_type.value)
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                if not api_key and config.encrypted_api_key:
                    api_key = decrypt_secret(config.encrypted_api_key)
                if not base_url and config.base_url:
                    base_url = config.base_url
                if not default_model and config.default_model:
                    default_model = config.default_model

        # Fallback to environment variables if still missing
        if not api_key:
            if provider_type == ProviderType.OPENROUTER:
                api_key = os.getenv("OPENROUTER_API_KEY")
            elif provider_type == ProviderType.NVIDIA:
                api_key = os.getenv("NVIDIA_API_KEY")

        return adapter_cls(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
        )

    @classmethod
    async def get_active_provider(cls, db: AsyncSession) -> BaseLLMProvider:
        """
        Retrieves the currently active configured provider from the database.
        Falls back to OpenRouter if no explicit active provider is marked.
        """
        stmt = select(ProviderConfiguration).where(
            ProviderConfiguration.is_active == True,
            ProviderConfiguration.enabled == True,
        )
        result = await db.execute(stmt)
        active_config = result.scalar_one_or_none()

        if active_config:
            p_type = ProviderType(active_config.provider_type)
            return await cls.get_adapter_instance(p_type, db=db)

        # Fallback to OpenRouter as default provider
        return await cls.get_adapter_instance(ProviderType.OPENROUTER, db=db)
