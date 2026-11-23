from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPENROUTER = "openrouter"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class PricingCategory(str, Enum):
    FREE = "free"
    PAID = "paid"


class ModelMode(str, Enum):
    FREE_ONLY = "free_only"
    PAID_ENABLED = "paid_enabled"
    MANUAL = "manual"


class ModelCapability(str, Enum):
    CHAT = "chat"
    STREAMING = "streaming"
    TOOLS = "tools"
    VISION = "vision"
    REASONING = "reasoning"
    CODE = "code"


class ChatMessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: ChatMessageRole
    content: Optional[str] = ""
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: str
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    stream: bool = False
    system_prompt: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatStreamChunk(BaseModel):
    id: Optional[str] = None
    delta: str = ""
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    context_length: Optional[int] = None
    description: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None
    pricing_category: Optional[PricingCategory] = None
    capabilities: Optional[List[str]] = None


class CentralModelInfo(BaseModel):
    id: str
    name: str
    provider_type: ProviderType
    pricing_category: PricingCategory
    cost_per_million_input: float = 0.0
    cost_per_million_output: float = 0.0
    context_limit: int
    supported_capabilities: List[str]
    is_available: bool = True
    is_default: bool = False
    description: Optional[str] = None


class ModelPolicyResponse(BaseModel):
    id: str
    model_mode: ModelMode
    selected_model: str
    fallback_models: List[str]
    enable_fallback: bool
    max_cost_per_request: float
    monthly_budget_limit: float


class ModelPolicyUpdate(BaseModel):
    model_mode: Optional[ModelMode] = None
    selected_model: Optional[str] = None
    fallback_models: Optional[List[str]] = None
    enable_fallback: Optional[bool] = None
    max_cost_per_request: Optional[float] = None
    monthly_budget_limit: Optional[float] = None


class ModelUsageSummary(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    fallback_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: float
    average_latency_ms: Optional[float] = None
    model_breakdown: List[Dict[str, Any]] = []


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
