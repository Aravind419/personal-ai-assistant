from typing import AsyncIterator, List, Optional
from app.providers.base import BaseLLMProvider
from app.providers.schemas import (
    ProviderType,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamChunk,
    ModelInfo,
    ProviderTestResult,
)

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:latest"


class OllamaProvider(BaseLLMProvider):
    """
    Adapter structure prepared for local Ollama instance integration.
    Scheduled for complete implementation in subsequent milestone.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        super().__init__(
            api_key=api_key,
            base_url=(base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/"),
            default_model=default_model or DEFAULT_OLLAMA_MODEL,
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

    async def test_connection(self) -> ProviderTestResult:
        return ProviderTestResult(
            success=False,
            message="Ollama local provider integration is prepared but pending activation in next milestone.",
            error="Provider not yet active",
        )

    async def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="llama3.2:latest",
                name="Ollama: Llama 3.2 (Local)",
                context_length=128000,
                description="Local edge model running on host hardware.",
            ),
            ModelInfo(
                id="qwen2.5-coder:latest",
                name="Ollama: Qwen 2.5 Coder (Local)",
                context_length=32768,
                description="Local high-accuracy programming assistant.",
            ),
        ]

    async def chat_complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        raise NotImplementedError("Ollama adapter implementation scheduled for future provider release.")

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatStreamChunk]:
        yield ChatStreamChunk(
            delta="",
            error="Ollama provider integration is prepared but pending activation in next milestone.",
        )
