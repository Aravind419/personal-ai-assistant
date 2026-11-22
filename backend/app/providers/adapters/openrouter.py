import time
import json
from typing import AsyncIterator, List, Optional
import httpx

from app.providers.base import BaseLLMProvider
from app.providers.schemas import (
    ProviderType,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamChunk,
    ModelInfo,
    ProviderTestResult,
)
from app.core.logging import logger

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

# Fallback curated models for OpenRouter in case of offline/local diagnostics
CURATED_OPENROUTER_MODELS = [
    ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct:free",
        name="Meta: Llama 3.3 70B Instruct (Free)",
        context_length=131072,
        description="State-of-the-art open weights model from Meta with zero cost.",
    ),
    ModelInfo(
        id="google/gemini-2.0-flash-exp:free",
        name="Google: Gemini 2.0 Flash (Free)",
        context_length=1048576,
        description="High-speed multimodal next-generation reasoning model at zero cost.",
    ),
    ModelInfo(
        id="deepseek/deepseek-r1:free",
        name="DeepSeek: R1 Reasoning (Free)",
        context_length=65536,
        description="Chain-of-thought mathematical and logic reasoning model.",
    ),
    ModelInfo(
        id="deepseek/deepseek-chat:free",
        name="DeepSeek: V3 Chat (Free)",
        context_length=65536,
        description="High-performance general dialogue and coding model.",
    ),
    ModelInfo(
        id="openai/gpt-4o-mini",
        name="OpenAI: GPT-4o Mini",
        context_length=128000,
        description="Fast, highly capable, and economical model for general assistant tasks.",
    ),
    ModelInfo(
        id="openai/gpt-4o",
        name="OpenAI: GPT-4o",
        context_length=128000,
        description="Flagship multimodal intelligence model from OpenAI.",
    ),
    ModelInfo(
        id="anthropic/claude-3.5-haiku",
        name="Anthropic: Claude 3.5 Haiku",
        context_length=200000,
        description="Rapid response, high intelligence lightweight model from Anthropic.",
    ),
    ModelInfo(
        id="anthropic/claude-3.5-sonnet",
        name="Anthropic: Claude 3.5 Sonnet",
        context_length=200000,
        description="Industry-leading code, reasoning, and analysis model from Anthropic.",
    ),
]


class OpenRouterProvider(BaseLLMProvider):
    """
    Genuine, complete OpenRouter API provider adapter.
    Implements chat completions, model listing, credential validation,
    and Server-Sent Events (SSE) streaming token output.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        super().__init__(
            api_key=api_key,
            base_url=(base_url or DEFAULT_OPENROUTER_BASE_URL).rstrip("/"),
            default_model=default_model or DEFAULT_OPENROUTER_MODEL,
        )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Personal AI Assistant",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _normalize_messages(self, request: ChatCompletionRequest) -> list:
        payload_messages = []
        if request.system_prompt:
            payload_messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            payload_messages.append({"role": msg.role.value, "content": msg.content})
        return payload_messages

    async def test_connection(self) -> ProviderTestResult:
        if not self.api_key:
            return ProviderTestResult(
                success=False,
                message="OpenRouter API key is not configured.",
                error="Missing credentials",
            )

        start_time = time.perf_counter()
        url = f"{self.base_url}/auth/key"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers())
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if response.status_code == 200:
                    data = response.json()
                    limit_info = data.get("data", {}).get("label") or "Authorized"
                    return ProviderTestResult(
                        success=True,
                        latency_ms=latency_ms,
                        message=f"Connection successful: {limit_info}",
                    )
                elif response.status_code == 401:
                    return ProviderTestResult(
                        success=False,
                        latency_ms=latency_ms,
                        message="Authentication failed. Invalid OpenRouter API key.",
                        error="401 Unauthorized",
                    )
                else:
                    return ProviderTestResult(
                        success=False,
                        latency_ms=latency_ms,
                        message=f"OpenRouter returned status {response.status_code}.",
                        error=response.text,
                    )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"OpenRouter connection test failed: {exc}")
            return ProviderTestResult(
                success=False,
                latency_ms=latency_ms,
                message="Unable to reach OpenRouter API.",
                error=str(exc),
            )

    async def list_models(self) -> List[ModelInfo]:
        from app.providers.model_registry import CentralModelRegistry
        from app.providers.schemas import PricingCategory

        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    data = response.json()
                    raw_models = data.get("data", [])
                    CentralModelRegistry.enrich_from_openrouter_catalog(raw_models)
                    models = []
                    for m in raw_models:
                        model_id = m.get("id")
                        if model_id:
                            is_free = CentralModelRegistry.is_free_model(model_id, m.get("pricing"))
                            models.append(
                                ModelInfo(
                                    id=model_id,
                                    name=m.get("name", model_id),
                                    context_length=m.get("context_length"),
                                    description=m.get("description"),
                                    pricing=m.get("pricing"),
                                    pricing_category=PricingCategory.FREE if is_free else PricingCategory.PAID,
                                )
                            )
                    if models:
                        return models
        except Exception as exc:
            logger.warning(f"Error fetching dynamic models from OpenRouter: {exc}. Using curated list.")

        return CURATED_OPENROUTER_MODELS

    async def chat_complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.api_key:
            raise ValueError("OpenRouter API key is not configured.")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": request.model or self.default_model,
            "messages": self._normalize_messages(request),
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            if response.status_code != 200:
                self._handle_http_error(response)

            data = response.json()
            choice = data.get("choices", [{}])[0]
            message_obj = choice.get("message", {})
            return ChatCompletionResponse(
                id=data.get("id", "res-unknown"),
                model=data.get("model", request.model),
                content=message_obj.get("content", ""),
                finish_reason=choice.get("finish_reason"),
                usage=data.get("usage"),
            )

    async def chat_stream(self, request: ChatCompletionRequest) -> AsyncIterator[ChatStreamChunk]:
        if not self.api_key:
            yield ChatStreamChunk(
                delta="",
                error="OpenRouter API key is not configured. Please enter your API key in Settings.",
            )
            return

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": request.model or self.default_model,
            "messages": self._normalize_messages(request),
            "temperature": request.temperature,
            "stream": True,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                async with client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        err_msg = self._format_error_message(response.status_code, error_text.decode("utf-8"))
                        yield ChatStreamChunk(delta="", error=err_msg)
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        line = line.strip()
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                yield ChatStreamChunk(delta="", finish_reason="stop")
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                choice = chunk_json.get("choices", [{}])[0]
                                delta_content = choice.get("delta", {}).get("content", "")
                                finish_reason = choice.get("finish_reason")
                                if delta_content or finish_reason:
                                    yield ChatStreamChunk(
                                        id=chunk_json.get("id"),
                                        delta=delta_content or "",
                                        finish_reason=finish_reason,
                                    )
                            except json.JSONDecodeError:
                                continue
        except httpx.TimeoutException:
            yield ChatStreamChunk(delta="", error="Request to OpenRouter timed out.")
        except Exception as exc:
            yield ChatStreamChunk(delta="", error=f"Streaming error: {str(exc)}")

    def _format_error_message(self, status_code: int, error_body: str) -> str:
        try:
            parsed = json.loads(error_body)
            if "error" in parsed:
                err = parsed["error"]
                if isinstance(err, dict) and "message" in err:
                    return f"OpenRouter Error ({status_code}): {err['message']}"
                return f"OpenRouter Error ({status_code}): {err}"
        except Exception:
            pass

        if status_code == 401:
            return "OpenRouter Error: Authentication failed. Please verify your API key in Settings."
        elif status_code == 402:
            return "OpenRouter Error: Insufficient credits or payment required on your OpenRouter account."
        elif status_code == 429:
            return "OpenRouter Error: Rate limit exceeded. Please wait a moment before sending another prompt."
        return f"OpenRouter Error ({status_code}): {error_body[:200]}"

    def _handle_http_error(self, response: httpx.Response):
        err_msg = self._format_error_message(response.status_code, response.text)
        raise RuntimeError(err_msg)
