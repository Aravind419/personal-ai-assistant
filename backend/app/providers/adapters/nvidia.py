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

DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"


class NvidiaProvider(BaseLLMProvider):
    """
    Adapter structure prepared for NVIDIA NIM API integration.
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
            base_url=base_url or DEFAULT_NVIDIA_BASE_URL,
            default_model=default_model or DEFAULT_NVIDIA_MODEL,
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.NVIDIA

    async def test_connection(self) -> ProviderTestResult:
        return ProviderTestResult(
            success=False,
            message="NVIDIA provider integration is prepared but pending activation in next milestone.",
            error="Provider not yet active",
        )

    async def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="meta/llama-3.1-70b-instruct",
                name="NVIDIA: Llama 3.1 70B Instruct",
                context_length=128000,
                description="NVIDIA NIM hosted enterprise Llama model.",
            ),
            ModelInfo(
                id="nvidia/nemotron-4-340b-instruct",
                name="NVIDIA: Nemotron-4 340B Instruct",
                context_length=4096,
                description="NVIDIA frontier synthetic data and reasoning model.",
            ),
        ]

    async def chat_complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        raise NotImplementedError("NVIDIA adapter implementation scheduled for future provider release.")

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatStreamChunk]:
        yield ChatStreamChunk(
            delta="",
            error="NVIDIA provider integration is prepared but pending activation in next milestone.",
        )
