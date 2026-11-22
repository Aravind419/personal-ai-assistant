from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.providers.schemas import (
    ProviderType,
    PricingCategory,
    ModelMode,
    CentralModelInfo,
    ModelPolicyResponse,
    ModelPolicyUpdate,
    ModelUsageSummary,
)
from app.providers.model_registry import CentralModelRegistry
from app.providers.model_service import ModelService

router = APIRouter(prefix="/models", tags=["Model Registry & Policy"])


@router.get(
    "",
    response_model=List[CentralModelInfo],
    summary="List all models in the central model registry",
)
async def list_models(
    pricing_category: Optional[PricingCategory] = Query(None, description="Filter by 'free' or 'paid'"),
    provider_type: Optional[ProviderType] = Query(None, description="Filter by provider"),
    mode: Optional[ModelMode] = Query(None, description="Filter according to operational mode"),
):
    return CentralModelRegistry.list_models(
        provider_type=provider_type,
        pricing_category=pricing_category,
        mode=mode,
    )


@router.get(
    "/policy",
    response_model=ModelPolicyResponse,
    summary="Get current AI model policy, operating mode, and fallback settings",
)
async def get_model_policy(db: AsyncSession = Depends(get_db)):
    return await ModelService.get_or_create_policy(db)


@router.put(
    "/policy",
    response_model=ModelPolicyResponse,
    summary="Update operational mode (free-only/paid-enabled/manual), fallback chain, and cost limits",
)
async def update_model_policy(
    payload: ModelPolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await ModelService.update_policy(payload, db)


@router.get(
    "/metrics",
    response_model=ModelUsageSummary,
    summary="Get aggregated token usage, estimated costs, latency, and model performance",
)
async def get_model_metrics(db: AsyncSession = Depends(get_db)):
    return await ModelService.get_usage_metrics(db)
