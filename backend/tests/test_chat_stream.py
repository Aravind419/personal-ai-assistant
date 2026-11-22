import pytest
import json
from typing import AsyncIterator
from httpx import AsyncClient
from app.providers.base import BaseLLMProvider
from app.providers.schemas import (
    ProviderType,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamChunk,
    ModelInfo,
    ProviderTestResult,
)
from app.providers.registry import ProviderRegistry


class MockStreamingProvider(BaseLLMProvider):
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER

    async def test_connection(self) -> ProviderTestResult:
        return ProviderTestResult(success=True, message="Mock connected")

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id="mock-model", name="Mock Model")]

    async def chat_complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        return ChatCompletionResponse(
            id="mock-1",
            model="mock-model",
            content="Mock full response",
        )

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatStreamChunk]:
        tokens = ["Hello", " world", "!", " I", " am", " your", " AI", " assistant."]
        for token in tokens:
            yield ChatStreamChunk(id="mock-stream", delta=token)
        yield ChatStreamChunk(id="mock-stream", delta="", finish_reason="stop")


@pytest.mark.asyncio
async def test_chat_streaming_and_persistence(async_client: AsyncClient):
    # Temporarily register mock provider as OPENROUTER to test streaming without live credentials
    original_adapter = ProviderRegistry._adapters.get(ProviderType.OPENROUTER)
    ProviderRegistry.register_adapter(ProviderType.OPENROUTER, MockStreamingProvider)

    try:
        # Create a conversation
        create_res = await async_client.post(
            "/api/v1/conversations",
            json={"title": "Streaming Test", "model": "mock-model"},
        )
        assert create_res.status_code == 201
        conv_id = create_res.json()["id"]

        # Send message and consume SSE stream
        stream_res = await async_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Introduce yourself."},
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers.get("content-type", "")

        body_text = stream_res.text
        lines = [line.strip() for line in body_text.split("\n") if line.strip()]

        tokens_received = []
        done_received = False
        for line in lines:
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if payload.get("type") == "token":
                    tokens_received.append(payload.get("delta", ""))
                elif payload.get("type") == "done":
                    done_received = True

        assert len(tokens_received) > 0
        assert "".join(tokens_received) == "Hello world! I am your AI assistant."
        assert done_received is True

        # Verify messages persisted in PostgreSQL
        get_res = await async_client.get(f"/api/v1/conversations/{conv_id}")
        assert get_res.status_code == 200
        messages = get_res.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Introduce yourself."
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hello world! I am your AI assistant."

    finally:
        # Restore real adapter
        if original_adapter:
            ProviderRegistry.register_adapter(ProviderType.OPENROUTER, original_adapter)
