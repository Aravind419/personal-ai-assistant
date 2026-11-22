import os
from pathlib import Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.provider import ProviderConfiguration
from app.providers.schemas import (
    ProviderType,
    ProviderConfigCreate,
    ProviderConfigUpdate,
    ProviderConfigResponse,
    ProviderTestResult,
    ModelInfo,
)
from app.providers.registry import ProviderRegistry
from app.core.security import encrypt_secret, decrypt_secret, mask_secret
from app.core.logging import logger

DEFAULT_PROVIDER_METADATA = {
    ProviderType.OPENROUTER: {
        "name": "OpenRouter",
        "default_model": "nvidia/nemotron-3.5-lightning:free",
        "base_url": "https://openrouter.ai/api/v1",
    },
    ProviderType.NVIDIA: {
        "name": "NVIDIA NIM",
        "default_model": "meta/llama-3.1-70b-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    ProviderType.OLLAMA: {
        "name": "Ollama (Local)",
        "default_model": "llama3.2:latest",
        "base_url": "http://localhost:11434",
    },
}


class ProviderService:
    @staticmethod
    async def list_providers(db: AsyncSession) -> List[ProviderConfigResponse]:
        """
        Lists all supported providers along with their configuration status.
        Never returns plaintext API keys.
        """
        stmt = select(ProviderConfiguration)
        result = await db.execute(stmt)
        configs = {c.provider_type: c for c in result.scalars().all()}

        response: List[ProviderConfigResponse] = []
        for p_type in ProviderRegistry.list_supported_providers():
            meta = DEFAULT_PROVIDER_METADATA.get(p_type, {
                "name": p_type.value.capitalize(),
                "default_model": "default",
                "base_url": None,
            })
            config = configs.get(p_type.value)

            if config:
                decrypted = decrypt_secret(config.encrypted_api_key)
                response.append(
                    ProviderConfigResponse(
                        provider_type=p_type,
                        name=config.name,
                        base_url=config.base_url,
                        default_model=config.default_model,
                        is_active=config.is_active,
                        enabled=config.enabled,
                        has_api_key=bool(config.encrypted_api_key),
                        masked_api_key=mask_secret(decrypted) if decrypted else None,
                    )
                )
            else:
                # Default unpersisted entry
                response.append(
                    ProviderConfigResponse(
                        provider_type=p_type,
                        name=meta["name"],
                        base_url=meta["base_url"],
                        default_model=meta["default_model"],
                        is_active=(p_type == ProviderType.OPENROUTER),
                        enabled=True,
                        has_api_key=False,
                        masked_api_key=None,
                    )
                )

        return response

    @staticmethod
    async def save_provider_config(
        provider_type: ProviderType,
        payload: ProviderConfigCreate,
        db: AsyncSession,
    ) -> ProviderConfigResponse:
        stmt = select(ProviderConfiguration).where(ProviderConfiguration.provider_type == provider_type.value)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        encrypted_key = encrypt_secret(payload.api_key) if payload.api_key else None

        if config:
            config.name = payload.name
            config.base_url = payload.base_url
            if payload.api_key:
                config.encrypted_api_key = encrypted_key
            config.default_model = payload.default_model
            config.enabled = payload.enabled
            if payload.is_active:
                # Deactivate all others
                await db.execute(
                    update(ProviderConfiguration).values(is_active=False)
                )
                config.is_active = True
        else:
            if payload.is_active:
                await db.execute(
                    update(ProviderConfiguration).values(is_active=False)
                )

            config = ProviderConfiguration(
                provider_type=provider_type.value,
                name=payload.name,
                base_url=payload.base_url,
                encrypted_api_key=encrypted_key,
                default_model=payload.default_model,
                is_active=payload.is_active,
                enabled=payload.enabled,
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)

        decrypted = decrypt_secret(config.encrypted_api_key)
        return ProviderConfigResponse(
            provider_type=provider_type,
            name=config.name,
            base_url=config.base_url,
            default_model=config.default_model,
            is_active=config.is_active,
            enabled=config.enabled,
            has_api_key=bool(config.encrypted_api_key),
            masked_api_key=mask_secret(decrypted) if decrypted else None,
        )

    @staticmethod
    async def set_active_provider(
        provider_type: ProviderType,
        db: AsyncSession,
    ) -> ProviderConfigResponse:
        # Deactivate all providers
        await db.execute(update(ProviderConfiguration).values(is_active=False))

        stmt = select(ProviderConfiguration).where(ProviderConfiguration.provider_type == provider_type.value)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            # Create baseline record if it wasn't customized yet
            meta = DEFAULT_PROVIDER_METADATA.get(provider_type, {
                "name": provider_type.value.capitalize(),
                "default_model": "default",
                "base_url": None,
            })
            config = ProviderConfiguration(
                provider_type=provider_type.value,
                name=meta["name"],
                base_url=meta["base_url"],
                encrypted_api_key=None,
                default_model=meta["default_model"],
                is_active=True,
                enabled=True,
            )
            db.add(config)
        else:
            config.is_active = True

        await db.commit()
        await db.refresh(config)

        decrypted = decrypt_secret(config.encrypted_api_key)
        return ProviderConfigResponse(
            provider_type=provider_type,
            name=config.name,
            base_url=config.base_url,
            default_model=config.default_model,
            is_active=config.is_active,
            enabled=config.enabled,
            has_api_key=bool(config.encrypted_api_key),
            masked_api_key=mask_secret(decrypted) if decrypted else None,
        )

    @staticmethod
    async def test_provider(
        provider_type: ProviderType,
        db: AsyncSession,
        override_api_key: Optional[str] = None,
        override_base_url: Optional[str] = None,
    ) -> ProviderTestResult:
        adapter = await ProviderRegistry.get_adapter_instance(
            provider_type,
            db=db,
            override_api_key=override_api_key,
            override_base_url=override_base_url,
        )
        return await adapter.test_connection()

    @staticmethod
    async def list_provider_models(
        provider_type: ProviderType,
        db: AsyncSession,
    ) -> List[ModelInfo]:
        adapter = await ProviderRegistry.get_adapter_instance(provider_type, db=db)
        return await adapter.list_models()
