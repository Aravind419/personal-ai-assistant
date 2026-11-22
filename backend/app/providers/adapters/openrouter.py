import time
import json
import socket
import asyncio
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
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3.5-lightning:free"

# Fallback curated models for OpenRouter in case of offline/local diagnostics
CURATED_OPENROUTER_MODELS = [
    ModelInfo(
        id="nvidia/nemotron-3.5-lightning:free",
        name="NVIDIA: Nemotron 3.5 Lightning (Free)",
        context_length=131072,
        description="High-throughput reasoning model by NVIDIA with lightning-fast inference at zero cost.",
    ),
    ModelInfo(
        id="openrouter/free",
        name="OpenRouter: Free Models Router",
        context_length=131072,
        description="Official OpenRouter dynamic router that automatically selects available free models at zero cost.",
    ),
    ModelInfo(
        id="google/gemma-4-31b-it:free",
        name="Google: Gemma 4 31B (Free)",
        context_length=32768,
        description="Google's open-weights 31B instruction-tuned model at zero cost.",
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

        max_retries = 2
        last_exc: Optional[Exception] = None

        for attempt in range(max_retries + 1):
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
            except (httpx.ConnectError, httpx.NetworkError, socket.gaierror) as net_err:
                last_exc = net_err
                if attempt < max_retries:
                    logger.warning(
                        f"Transient connection glitch to OpenRouter test ({attempt + 1}/{max_retries + 1}): {net_err}. Retrying in 0.5s..."
                    )
                    await asyncio.sleep(0.5)
                    continue
                break
            except Exception as exc:
                last_exc = exc
                break

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_str = str(last_exc) if last_exc else "Unknown connection error"
        logger.warning(f"OpenRouter connection test failed: {err_str}")
        if "11001" in err_str or "getaddrinfo" in err_str.lower():
            user_msg = (
                "Unable to resolve openrouter.ai (DNS lookup failed: [Errno 11001]). "
                "Please check your internet connection or DNS settings."
            )
        else:
            user_msg = f"Unable to reach OpenRouter API: {err_str}"

        return ProviderTestResult(
            success=False,
            latency_ms=latency_ms,
            message=user_msg,
            error=err_str,
        )

    async def list_models(self) -> List[ModelInfo]:
        from app.providers.model_registry import CentralModelRegistry
        from app.providers.schemas import PricingCategory

        url = f"{self.base_url}/models"
        max_retries = 2
        for attempt in range(max_retries + 1):
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
                    break
            except (httpx.ConnectError, httpx.NetworkError, socket.gaierror) as net_err:
                if attempt < max_retries:
                    logger.warning(
                        f"Transient connection glitch fetching models ({attempt + 1}/{max_retries + 1}): {net_err}. Retrying..."
                    )
                    await asyncio.sleep(0.5)
                    continue
                logger.warning(f"Failed to fetch dynamic models from OpenRouter after retries: {net_err}. Using curated list.")
            except Exception as exc:
                logger.warning(f"Error fetching dynamic models from OpenRouter: {exc}. Using curated list.")
                break

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

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=payload, headers=self._get_headers())
                    if response.status_code != 200:
                        self._handle_http_error(response)

                    data = response.json()
                    choice = data.get("choices", [{}])[0]
                    message_obj = choice.get("message", {})
                    content = message_obj.get("content") or message_obj.get("reasoning") or ""
                    return ChatCompletionResponse(
                        id=data.get("id", "res-unknown"),
                        model=data.get("model", request.model),
                        content=content,
                        finish_reason=choice.get("finish_reason"),
                        usage=data.get("usage"),
                    )
            except (httpx.ConnectError, httpx.NetworkError, socket.gaierror) as net_err:
                if attempt < max_retries:
                    logger.warning(
                        f"Transient connection glitch in chat_complete ({attempt + 1}/{max_retries + 1}): {net_err}. Retrying..."
                    )
                    await asyncio.sleep(0.5)
                    continue
                err_str = str(net_err)
                if "11001" in err_str or "getaddrinfo" in err_str.lower():
                    raise RuntimeError(
                        "Unable to reach openrouter.ai (DNS lookup failed: [Errno 11001]). "
                        "Please verify your internet connection and DNS settings."
                    )
                raise RuntimeError(f"Network connection error contacting OpenRouter: {err_str}")

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

        max_retries = 2
        for attempt in range(max_retries + 1):
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
                return
            except (httpx.ConnectError, httpx.NetworkError, socket.gaierror) as net_err:
                if attempt < max_retries:
                    logger.warning(
                        f"Transient connection glitch in chat_stream ({attempt + 1}/{max_retries + 1}): {net_err}. Retrying in 0.5s..."
                    )
                    await asyncio.sleep(0.5)
                    continue
                err_str = str(net_err)
                if "11001" in err_str or "getaddrinfo" in err_str.lower():
                    friendly = (
                        "Unable to reach openrouter.ai (DNS lookup failed: [Errno 11001]). "
                        "Please verify your internet connection and DNS settings."
                    )
                else:
                    friendly = f"Connection error reaching OpenRouter: {err_str}"
                yield ChatStreamChunk(delta="", error=friendly)
                return
            except httpx.TimeoutException:
                yield ChatStreamChunk(delta="", error="Request to OpenRouter timed out.")
                return
            except Exception as exc:
                yield ChatStreamChunk(delta="", error=f"Streaming error: {str(exc)}")
                return

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
