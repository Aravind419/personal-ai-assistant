from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional
from app.providers.schemas import (
    ProviderType,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamChunk,
    ModelInfo,
    ProviderTestResult,
)


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for all LLM providers.
    Every provider (OpenRouter, NVIDIA, Ollama, etc.) must implement this interface.
    The core agent interacts exclusively with this interface.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """The canonical type of the provider."""
        pass

    @abstractmethod
    async def test_connection(self) -> ProviderTestResult:
        """
        Tests the connection to the provider and verifies credentials.
        Returns latency and descriptive diagnostic status.
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        Returns a list of supported or available models from the provider.
        """
        pass

    @abstractmethod
    async def chat_complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Performs a non-streaming chat completion request.
        """
        pass

    @abstractmethod
    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatStreamChunk]:
        """
        Streams chat completion tokens asynchronously.
        """
        pass
