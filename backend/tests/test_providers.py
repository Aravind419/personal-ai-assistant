import pytest
from app.providers.schemas import (
    ProviderType,
    ChatCompletionRequest,
    ChatMessage,
    ChatMessageRole,
    ChatStreamChunk,
)
from app.providers.base import BaseLLMProvider
from app.providers.registry import ProviderRegistry
from app.providers.adapters.openrouter import OpenRouterProvider


@pytest.mark.asyncio
async def test_provider_registry_supported_list():
    providers = ProviderRegistry.list_supported_providers()
    assert ProviderType.OPENROUTER in providers
    assert ProviderType.NVIDIA in providers
    assert ProviderType.OLLAMA in providers


@pytest.mark.asyncio
async def test_openrouter_missing_credentials():
    adapter = OpenRouterProvider(api_key=None)
    result = await adapter.test_connection()
    assert result.success is False
    assert "not configured" in result.message.lower()


@pytest.mark.asyncio
async def test_openrouter_stream_without_key():
    adapter = OpenRouterProvider(api_key=None)
    req = ChatCompletionRequest(
        messages=[ChatMessage(role=ChatMessageRole.USER, content="Hello")],
        model="openai/gpt-4o-mini",
    )
    chunks = []
    async for chunk in adapter.chat_stream(req):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].error is not None
    assert "api key is not configured" in chunks[0].error.lower()


@pytest.mark.asyncio
async def test_openrouter_error_formatting():
    adapter = OpenRouterProvider(api_key="dummy")
    msg_401 = adapter._format_error_message(401, '{"error": {"message": "Invalid API key"}}')
    assert "Invalid API key" in msg_401

    msg_402 = adapter._format_error_message(402, "{}")
    assert "Insufficient credits" in msg_402
