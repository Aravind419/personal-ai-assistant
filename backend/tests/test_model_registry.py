import pytest
import json
from httpx import AsyncClient

from app.providers.schemas import (
    ProviderType,
    PricingCategory,
    ModelMode,
    ChatStreamChunk,
)
from app.providers.model_registry import CentralModelRegistry
from app.providers.base import BaseLLMProvider
from app.providers.registry import ProviderRegistry


def test_central_model_registry_classification():
    # Test free models
    assert CentralModelRegistry.is_free_model("meta-llama/llama-3.3-70b-instruct:free") is True
    assert CentralModelRegistry.is_free_model("google/gemini-2.0-flash-exp:free") is True
    assert CentralModelRegistry.is_free_model("deepseek/deepseek-r1:free") is True
    assert CentralModelRegistry.is_free_model("custom/model", {"prompt": "0", "completion": "0"}) is True

    # Test paid models
    assert CentralModelRegistry.is_free_model("openai/gpt-4o-mini") is False
    assert CentralModelRegistry.is_free_model("anthropic/claude-3.5-sonnet") is False
    assert CentralModelRegistry.is_free_model("meta-llama/llama-3.3-70b-instruct") is False


def test_mode_validation_enforcement():
    # FREE_ONLY mode strictly disallows paid models
    allowed, reason = CentralModelRegistry.validate_model_for_mode(
        "openai/gpt-4o", ModelMode.FREE_ONLY
    )
    assert allowed is False
    assert "Free-Only mode is active" in reason

    # FREE_ONLY mode allows free models
    allowed, reason = CentralModelRegistry.validate_model_for_mode(
        "meta-llama/llama-3.3-70b-instruct:free", ModelMode.FREE_ONLY
    )
    assert allowed is True
    assert reason is None

    # PAID_ENABLED mode allows both
    allowed, _ = CentralModelRegistry.validate_model_for_mode(
        "openai/gpt-4o", ModelMode.PAID_ENABLED
    )
    assert allowed is True


def test_fallback_chain_filtering():
    raw_chain = [
        "openai/gpt-4o",
        "meta-llama/llama-3.3-70b-instruct:free",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-2.0-flash-exp:free",
    ]

    # Under FREE_ONLY, all paid models must be purged from the fallback chain
    free_chain = CentralModelRegistry.filter_fallback_chain(raw_chain, ModelMode.FREE_ONLY)
    assert free_chain == [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
    ]

    # Under PAID_ENABLED, all candidates remain
    paid_chain = CentralModelRegistry.filter_fallback_chain(raw_chain, ModelMode.PAID_ENABLED)
    assert len(paid_chain) == 4


def test_cost_calculation():
    # Free model must always return 0.0 regardless of token volume
    free_cost = CentralModelRegistry.estimate_cost(
        "meta-llama/llama-3.3-70b-instruct:free", prompt_tokens=10000, completion_tokens=5000
    )
    assert free_cost == 0.0

    # Paid model calculation (gpt-4o-mini: $0.15/1M in, $0.60/1M out)
    # 1,000,000 in = $0.15, 1,000,000 out = $0.60 -> Total $0.75
    paid_cost = CentralModelRegistry.estimate_cost(
        "openai/gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000
    )
    assert round(paid_cost, 2) == 0.75


@pytest.mark.asyncio
async def test_model_policy_api_endpoints(async_client: AsyncClient):
    # 1. Reset / initialize policy to free_only baseline
    await async_client.put(
        "/api/v1/models/policy",
        json={"model_mode": "free_only"},
    )
    get_res = await async_client.get("/api/v1/models/policy")
    assert get_res.status_code == 200
    policy = get_res.json()
    assert policy["model_mode"] == "free_only"
    assert "free" in policy["selected_model"]
    assert policy["enable_fallback"] is True

    # 2. Update policy to paid_enabled with a paid model
    update_res = await async_client.put(
        "/api/v1/models/policy",
        json={
            "model_mode": "paid_enabled",
            "selected_model": "openai/gpt-4o-mini",
            "max_cost_per_request": 0.10,
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["model_mode"] == "paid_enabled"
    assert updated["selected_model"] == "openai/gpt-4o-mini"
    assert updated["max_cost_per_request"] == 0.10

    # 3. Switching back to free_only must automatically sanitize selected model to a free model
    switch_res = await async_client.put(
        "/api/v1/models/policy",
        json={
            "model_mode": "free_only",
            "selected_model": "openai/gpt-4o",  # Invalid for free_only
        },
    )
    assert switch_res.status_code == 200
    switched = switch_res.json()
    assert switched["model_mode"] == "free_only"
    assert ":free" in switched["selected_model"]


@pytest.mark.asyncio
async def test_model_catalog_endpoint(async_client: AsyncClient):
    # List all catalog models
    res = await async_client.get("/api/v1/models")
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 6

    # Filter free models only
    res_free = await async_client.get("/api/v1/models?pricing_category=free")
    assert res_free.status_code == 200
    free_models = res_free.json()
    assert all(m["pricing_category"] == "free" for m in free_models)


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient):
    res = await async_client.get("/api/v1/models/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "total_requests" in metrics
    assert "total_tokens" in metrics
    assert "total_estimated_cost_usd" in metrics
    assert isinstance(metrics["model_breakdown"], list)


class MockFallbackProvider(BaseLLMProvider):
    """
    Mock provider that fails on the first model, but succeeds on the fallback model.
    """
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER

    async def test_connection(self):
        return None

    async def list_models(self):
        return []

    async def chat_complete(self, request):
        return None

    async def chat_stream(self, request):
        if "failing-model" in request.model:
            yield ChatStreamChunk(delta="", error="Model quota exceeded or rate limit (429)")
            return

        yield ChatStreamChunk(delta="Fallback ", finish_reason=None)
        yield ChatStreamChunk(delta="response successful!", finish_reason="stop")


@pytest.mark.asyncio
async def test_streaming_fallback_chain(async_client: AsyncClient):
    # Register mock fallback provider
    orig_adapter = ProviderRegistry._adapters.get(ProviderType.OPENROUTER)
    ProviderRegistry.register_adapter(ProviderType.OPENROUTER, MockFallbackProvider)

    try:
        # Create a conversation
        c_res = await async_client.post(
            "/api/v1/conversations",
            json={
                "title": "Fallback Test Conversation",
                "model": "failing-model:free",
            },
        )
        assert c_res.status_code == 201
        conv_id = c_res.json()["id"]

        # Ensure policy has fallback enabled
        await async_client.put(
            "/api/v1/models/policy",
            json={
                "model_mode": "free_only",
                "enable_fallback": True,
                "fallback_models": ["google/gemini-2.0-flash-exp:free"],
            },
        )

        # Stream message
        stream_res = await async_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Trigger fallback mechanism"},
        )
        assert stream_res.status_code == 200
        raw_body = stream_res.text

        # Verify fallback notice and final successful completion
        assert "falling back to:" in raw_body.lower()
        assert "Fallback response successful!" in raw_body

        # Verify conversation history persisted the assistant response
        conv_check = await async_client.get(f"/api/v1/conversations/{conv_id}")
        assert conv_check.status_code == 200
        msgs = conv_check.json()["messages"]
        assert len(msgs) == 2
        assistant_msg = msgs[1]
        assert assistant_msg["role"] == "assistant"
        assert "Fallback response successful!" in assistant_msg["content"]
        assert assistant_msg["metadata_json"] is not None
        meta = json.loads(assistant_msg["metadata_json"])
        assert meta["fallback_used"] is True

    finally:
        if orig_adapter:
            ProviderRegistry.register_adapter(ProviderType.OPENROUTER, orig_adapter)
