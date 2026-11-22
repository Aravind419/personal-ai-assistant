from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.providers.schemas import (
    ProviderType,
    ProviderConfigCreate,
    ProviderConfigResponse,
    ProviderTestResult,
    ModelInfo,
)
from app.providers.service import ProviderService

router = APIRouter(prefix="/providers", tags=["AI Providers"])


class TestProviderRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@router.get(
    "",
    response_model=List[ProviderConfigResponse],
    summary="List supported and configured AI providers",
)
async def list_providers(db: AsyncSession = Depends(get_db)):
    return await ProviderService.list_providers(db)


@router.post(
    "/{provider_type}",
    response_model=ProviderConfigResponse,
    summary="Configure an AI provider and save credentials securely",
)
async def save_provider(
    provider_type: ProviderType,
    payload: ProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    return await ProviderService.save_provider_config(provider_type, payload, db)


@router.post(
    "/{provider_type}/activate",
    response_model=ProviderConfigResponse,
    summary="Set provider as the active global default",
)
async def activate_provider(
    provider_type: ProviderType,
    db: AsyncSession = Depends(get_db),
):
    return await ProviderService.set_active_provider(provider_type, db)


@router.post(
    "/{provider_type}/test",
    response_model=ProviderTestResult,
    summary="Test connectivity to an AI provider with saved or ephemeral key",
)
async def test_provider_connection(
    provider_type: ProviderType,
    payload: Optional[TestProviderRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    api_key = payload.api_key if payload else None
    base_url = payload.base_url if payload else None
    return await ProviderService.test_provider(
        provider_type,
        db=db,
        override_api_key=api_key,
        override_base_url=base_url,
    )


@router.get(
    "/{provider_type}/models",
    response_model=List[ModelInfo],
    summary="Retrieve available models for an AI provider",
)
async def get_provider_models(
    provider_type: ProviderType,
    db: AsyncSession = Depends(get_db),
):
    return await ProviderService.list_provider_models(provider_type, db)
