import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.model_policy import AIModelPolicy, ModelExecutionMetric
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
from app.core.exceptions import BadRequestException
from app.core.logging import logger

DEFAULT_FALLBACK_CHAIN = [
    "openrouter/free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
]

RETIRED_FREE_SLUGS = {
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-chat:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
}


class ModelService:
    @staticmethod
    async def get_or_create_policy(db: AsyncSession) -> ModelPolicyResponse:
        """
        Retrieves the active model policy or initializes the default free-only policy.
        Automatically updates legacy retired model slugs to active free models.
        """
        stmt = select(AIModelPolicy)
        result = await db.execute(stmt)
        policy = result.scalar_one_or_none()

        if not policy:
            policy = AIModelPolicy(
                id=str(uuid.uuid4()),
                model_mode=ModelMode.FREE_ONLY.value,
                selected_model="nvidia/nemotron-3.5-lightning:free",
                fallback_models_json=json.dumps(DEFAULT_FALLBACK_CHAIN),
                enable_fallback=True,
                max_cost_per_request=0.05,
                monthly_budget_limit=10.0,
            )
            db.add(policy)
            await db.commit()
            await db.refresh(policy)
        else:
            # Auto-migrate retired free models in existing database rows
            updated = False
            if policy.selected_model in RETIRED_FREE_SLUGS:
                policy.selected_model = "nvidia/nemotron-3.5-lightning:free"
                updated = True
            try:
                current_fallbacks = json.loads(policy.fallback_models_json)
                if any(s in RETIRED_FREE_SLUGS for s in current_fallbacks):
                    cleaned = [s for s in current_fallbacks if s not in RETIRED_FREE_SLUGS]
                    for s in DEFAULT_FALLBACK_CHAIN:
                        if s not in cleaned:
                            cleaned.append(s)
                    policy.fallback_models_json = json.dumps(cleaned)
                    updated = True
            except Exception:
                policy.fallback_models_json = json.dumps(DEFAULT_FALLBACK_CHAIN)
                updated = True

            if updated:
                await db.commit()
                await db.refresh(policy)

        try:
            fallbacks = json.loads(policy.fallback_models_json)
        except Exception:
            fallbacks = DEFAULT_FALLBACK_CHAIN

        return ModelPolicyResponse(
            id=policy.id,
            model_mode=ModelMode(policy.model_mode),
            selected_model=policy.selected_model,
            fallback_models=fallbacks,
            enable_fallback=policy.enable_fallback,
            max_cost_per_request=policy.max_cost_per_request,
            monthly_budget_limit=policy.monthly_budget_limit,
        )

    @staticmethod
    async def update_policy(
        payload: ModelPolicyUpdate,
        db: AsyncSession,
    ) -> ModelPolicyResponse:
        stmt = select(AIModelPolicy)
        result = await db.execute(stmt)
        policy = result.scalar_one_or_none()

        if not policy:
            await ModelService.get_or_create_policy(db)
            result = await db.execute(stmt)
            policy = result.scalar_one()

        new_mode = payload.model_mode.value if payload.model_mode else policy.model_mode

        # If switching to free_only or in free_only mode, validate selected model
        if new_mode == ModelMode.FREE_ONLY.value:
            target_model = payload.selected_model or policy.selected_model
            allowed, reason = CentralModelRegistry.validate_model_for_mode(
                target_model, ModelMode.FREE_ONLY
            )
            if not allowed:
                # If target was invalid, fall back to default free model
                policy.selected_model = CentralModelRegistry.get_default_model(ModelMode.FREE_ONLY)
            elif payload.selected_model is not None:
                policy.selected_model = payload.selected_model
        else:
            if payload.selected_model is not None:
                policy.selected_model = payload.selected_model

        if payload.model_mode is not None:
            policy.model_mode = payload.model_mode.value

        if payload.fallback_models is not None:
            policy.fallback_models_json = json.dumps(payload.fallback_models)

        if payload.enable_fallback is not None:
            policy.enable_fallback = payload.enable_fallback

        if payload.max_cost_per_request is not None:
            if payload.max_cost_per_request < 0:
                raise BadRequestException("Max cost per request cannot be negative.")
            policy.max_cost_per_request = payload.max_cost_per_request

        if payload.monthly_budget_limit is not None:
            if payload.monthly_budget_limit < 0:
                raise BadRequestException("Monthly budget limit cannot be negative.")
            policy.monthly_budget_limit = payload.monthly_budget_limit

        await db.commit()
        await db.refresh(policy)

        try:
            fallbacks = json.loads(policy.fallback_models_json)
        except Exception:
            fallbacks = DEFAULT_FALLBACK_CHAIN

        return ModelPolicyResponse(
            id=policy.id,
            model_mode=ModelMode(policy.model_mode),
            selected_model=policy.selected_model,
            fallback_models=fallbacks,
            enable_fallback=policy.enable_fallback,
            max_cost_per_request=policy.max_cost_per_request,
            monthly_budget_limit=policy.monthly_budget_limit,
        )

    @staticmethod
    async def record_execution_metric(
        provider_type: str,
        model_id: str,
        pricing_category: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
        latency_ms: Optional[float],
        status: str,
        conversation_id: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ):
        """
        Records an execution metric entry in model_execution_metrics table.
        """
        if not db:
            return

        try:
            metric = ModelExecutionMetric(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                provider_type=provider_type,
                model_id=model_id,
                pricing_category=pricing_category,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=estimated_cost,
                latency_ms=latency_ms,
                status=status,
                error_type=error_type,
                error_message=error_message,
            )
            db.add(metric)
            await db.commit()
        except Exception as exc:
            logger.warning(f"Failed to record model execution metric: {exc}")

    @staticmethod
    async def get_usage_metrics(db: AsyncSession) -> ModelUsageSummary:
        """
        Calculates aggregate usage statistics, costs, error rates, and model breakdown.
        """
        # Overall aggregates
        stmt = select(
            func.count(ModelExecutionMetric.id).label("total_requests"),
            func.coalesce(func.sum(ModelExecutionMetric.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(ModelExecutionMetric.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(ModelExecutionMetric.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(ModelExecutionMetric.estimated_cost_usd), 0.0).label("total_cost"),
            func.avg(ModelExecutionMetric.latency_ms).label("avg_latency"),
        )
        result = await db.execute(stmt)
        row = result.one()

        # Status counts
        status_stmt = select(
            ModelExecutionMetric.status,
            func.count(ModelExecutionMetric.id)
        ).group_by(ModelExecutionMetric.status)
        status_res = await db.execute(status_stmt)
        status_counts = dict(status_res.all())

        successful = status_counts.get("success", 0)
        failed = status_counts.get("error", 0)
        fallback = status_counts.get("fallback", 0)

        # Model breakdown
        breakdown_stmt = select(
            ModelExecutionMetric.model_id,
            ModelExecutionMetric.pricing_category,
            func.count(ModelExecutionMetric.id).label("requests"),
            func.coalesce(func.sum(ModelExecutionMetric.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(ModelExecutionMetric.estimated_cost_usd), 0.0).label("cost"),
            func.avg(ModelExecutionMetric.latency_ms).label("avg_latency"),
        ).group_by(ModelExecutionMetric.model_id, ModelExecutionMetric.pricing_category).order_by(desc("requests"))

        breakdown_res = await db.execute(breakdown_stmt)
        model_breakdown = [
            {
                "model_id": b.model_id,
                "pricing_category": b.pricing_category,
                "requests": b.requests,
                "total_tokens": b.tokens,
                "estimated_cost_usd": round(b.cost, 6),
                "avg_latency_ms": round(b.avg_latency, 1) if b.avg_latency else None,
            }
            for b in breakdown_res.all()
        ]

        return ModelUsageSummary(
            total_requests=row.total_requests or 0,
            successful_requests=successful,
            failed_requests=failed,
            fallback_requests=fallback,
            total_prompt_tokens=row.prompt_tokens or 0,
            total_completion_tokens=row.completion_tokens or 0,
            total_tokens=row.total_tokens or 0,
            total_estimated_cost_usd=round(float(row.total_cost or 0.0), 6),
            average_latency_ms=round(float(row.avg_latency), 1) if row.avg_latency else None,
            model_breakdown=model_breakdown,
        )
