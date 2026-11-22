from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPENROUTER = "openrouter"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class ChatMessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: ChatMessageRole
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: str
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    stream: bool = False
    system_prompt: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class ChatStreamChunk(BaseModel):
    id: Optional[str] = None
    delta: str
    finish_reason: Optional[str] = None
    error: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    context_length: Optional[int] = None
    description: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None


class ProviderTestResult(BaseModel):
    success: bool
    latency_ms: Optional[float] = None
    message: str
    models_found: Optional[int] = None
    error: Optional[str] = None


class ProviderConfigBase(BaseModel):
    name: str
    base_url: Optional[str] = None
    default_model: str
    is_active: bool = False
    enabled: bool = True


class ProviderConfigCreate(ProviderConfigBase):
    api_key: Optional[str] = None


class ProviderConfigUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    is_active: Optional[bool] = None
    enabled: Optional[bool] = None


class ProviderConfigResponse(ProviderConfigBase):
    provider_type: ProviderType
    has_api_key: bool
    masked_api_key: Optional[str] = None
