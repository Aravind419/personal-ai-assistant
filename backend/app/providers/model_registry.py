import re
from typing import Dict, List, Optional, Tuple, Any
from app.providers.schemas import (
    ProviderType,
    PricingCategory,
    ModelMode,
    ModelCapability,
    CentralModelInfo,
    ModelInfo,
)

# Central curated models catalog
# Built-in free models are prioritized for zero-cost development
CENTRAL_MODELS_CATALOG: Dict[str, CentralModelInfo] = {
    # --- FREE MODELS (Default for zero-cost development) ---
    "nvidia/nemotron-3.5-lightning:free": CentralModelInfo(
        id="nvidia/nemotron-3.5-lightning:free",
        name="NVIDIA: Nemotron 3.5 Lightning (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=131072,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.CODE.value,
            ModelCapability.REASONING.value,
        ],
        is_available=True,
        is_default=True,
        description="High-throughput open reasoning model by NVIDIA with lightning-fast inference at zero cost.",
    ),
    "openrouter/free": CentralModelInfo(
        id="openrouter/free",
        name="OpenRouter: Free Models Router",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=131072,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.TOOLS.value,
            ModelCapability.REASONING.value,
        ],
        is_available=True,
        is_default=False,
        description="Official OpenRouter dynamic router that automatically routes to high-availability free models at zero cost.",
    ),
    "google/gemma-4-31b-it:free": CentralModelInfo(
        id="google/gemma-4-31b-it:free",
        name="Google: Gemma 4 31B (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=32768,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.CODE.value,
        ],
        is_available=True,
        is_default=False,
        description="Google's open-weights 31B instruction-tuned model at zero cost.",
    ),
    "meta-llama/llama-3.3-70b-instruct:free": CentralModelInfo(
        id="meta-llama/llama-3.3-70b-instruct:free",
        name="Meta: Llama 3.3 70B Instruct (Free - Retired)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=131072,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.TOOLS.value,
        ],
        is_available=False,
        is_default=False,
        description="State-of-the-art open weights 70B model with full tool calling and reasoning support (historical catalog).",
    ),
    "google/gemini-2.0-flash-exp:free": CentralModelInfo(
        id="google/gemini-2.0-flash-exp:free",
        name="Google: Gemini 2.0 Flash Exp (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=1048576,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.VISION.value,
        ],
        is_available=True,
        is_default=False,
        description="Ultra high-speed multimodal reasoning model with 1M context window at zero cost.",
    ),
    "deepseek/deepseek-r1:free": CentralModelInfo(
        id="deepseek/deepseek-r1:free",
        name="DeepSeek: R1 Reasoning (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=65536,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.REASONING.value,
        ],
        is_available=True,
        is_default=False,
        description="DeepSeek's premier chain-of-thought mathematical and logic reasoning model.",
    ),
    "deepseek/deepseek-chat:free": CentralModelInfo(
        id="deepseek/deepseek-chat:free",
        name="DeepSeek: V3 Chat (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=65536,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.CODE.value,
        ],
        is_available=True,
        is_default=False,
        description="Powerful general dialogue and coding model from DeepSeek.",
    ),
    "qwen/qwen-2.5-coder-32b-instruct:free": CentralModelInfo(
        id="qwen/qwen-2.5-coder-32b-instruct:free",
        name="Qwen: 2.5 Coder 32B (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=32768,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.CODE.value,
        ],
        is_available=True,
        is_default=False,
        description="Specialized code generation, debugging, and syntax reasoning model.",
    ),
    "mistralai/mistral-7b-instruct:free": CentralModelInfo(
        id="mistralai/mistral-7b-instruct:free",
        name="Mistral: 7B Instruct (Free)",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.FREE,
        cost_per_million_input=0.0,
        cost_per_million_output=0.0,
        context_limit=32768,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
        ],
        is_available=True,
        is_default=False,
        description="Fast and responsive lightweight conversational model.",
    ),

    # --- PAID MODELS (Optional Capability) ---
    "openai/gpt-4o-mini": CentralModelInfo(
        id="openai/gpt-4o-mini",
        name="OpenAI: GPT-4o Mini",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.PAID,
        cost_per_million_input=0.15,
        cost_per_million_output=0.60,
        context_limit=128000,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.TOOLS.value,
            ModelCapability.VISION.value,
        ],
        is_available=True,
        is_default=False,
        description="Fast, highly capable, and cost-efficient general assistant model.",
    ),
    "openai/gpt-4o": CentralModelInfo(
        id="openai/gpt-4o",
        name="OpenAI: GPT-4o Flagship",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.PAID,
        cost_per_million_input=2.50,
        cost_per_million_output=10.00,
        context_limit=128000,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.TOOLS.value,
            ModelCapability.VISION.value,
        ],
        is_available=True,
        is_default=False,
        description="OpenAI's flagship multimodal intelligence model.",
    ),
    "anthropic/claude-3.5-haiku": CentralModelInfo(
        id="anthropic/claude-3.5-haiku",
        name="Anthropic: Claude 3.5 Haiku",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.PAID,
        cost_per_million_input=0.80,
        cost_per_million_output=4.00,
        context_limit=200000,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.TOOLS.value,
        ],
        is_available=True,
        is_default=False,
        description="High-speed, intelligent lightweight model from Anthropic.",
    ),
    "anthropic/claude-3.5-sonnet": CentralModelInfo(
        id="anthropic/claude-3.5-sonnet",
        name="Anthropic: Claude 3.5 Sonnet",
        provider_type=ProviderType.OPENROUTER,
        pricing_category=PricingCategory.PAID,
        cost_per_million_input=3.00,
        cost_per_million_output=15.00,
        context_limit=200000,
        supported_capabilities=[
            ModelCapability.CHAT.value,
            ModelCapability.STREAMING.value,
            ModelCapability.TOOLS.value,
            ModelCapability.CODE.value,
            ModelCapability.VISION.value,
        ],
        is_available=True,
        is_default=False,
        description="Industry-leading code, reasoning, and synthesis model.",
    ),
}


class CentralModelRegistry:
    """
    Central repository for AI model discovery, pricing categories, context limits,
    capability tags, and cost calculation.
    """

    @classmethod
    def is_free_model(cls, model_id: str, pricing_dict: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determines whether a model is free:
        1. ID ends with :free, contains :free, is 'openrouter/free', or ends with /free
        2. Pricing dict explicitly specifies prompt == 0 and completion == 0
        3. Registered in catalog as PricingCategory.FREE
        """
        m_lower = model_id.lower()
        if ":free" in m_lower or m_lower == "openrouter/free" or m_lower.endswith("/free"):
            return True

        if pricing_dict:
            try:
                p_in = float(pricing_dict.get("prompt", 0))
                p_out = float(pricing_dict.get("completion", 0))
                if p_in == 0.0 and p_out == 0.0:
                    return True
            except (ValueError, TypeError):
                pass

        registered = CENTRAL_MODELS_CATALOG.get(model_id)
        if registered and registered.pricing_category == PricingCategory.FREE:
            return True

        return False

    @classmethod
    def get_model(cls, model_id: str) -> Optional[CentralModelInfo]:
        """
        Retrieves model metadata from the catalog, synthesizing on-the-fly if missing.
        """
        if model_id in CENTRAL_MODELS_CATALOG:
            return CENTRAL_MODELS_CATALOG[model_id]

        # On-the-fly synthesis for dynamically queried models
        is_free = cls.is_free_model(model_id)
        category = PricingCategory.FREE if is_free else PricingCategory.PAID
        clean_name = model_id.split("/")[-1].replace("-", " ").title()

        return CentralModelInfo(
            id=model_id,
            name=f"Dynamic: {clean_name}",
            provider_type=ProviderType.OPENROUTER,
            pricing_category=category,
            cost_per_million_input=0.0 if is_free else 1.0,
            cost_per_million_output=0.0 if is_free else 2.0,
            context_limit=128000,
            supported_capabilities=[ModelCapability.CHAT.value, ModelCapability.STREAMING.value],
            is_available=True,
            is_default=False,
            description="Dynamically queried model from OpenRouter catalog.",
        )

    @classmethod
    def list_models(
        cls,
        provider_type: Optional[ProviderType] = None,
        pricing_category: Optional[PricingCategory] = None,
        mode: Optional[ModelMode] = None,
    ) -> List[CentralModelInfo]:
        """
        Lists models filtered by provider, pricing category, or operational mode.
        """
        models = list(CENTRAL_MODELS_CATALOG.values())

        if provider_type:
            models = [m for m in models if m.provider_type == provider_type]

        if pricing_category:
            models = [m for m in models if m.pricing_category == pricing_category]

        if mode == ModelMode.FREE_ONLY:
            models = [m for m in models if m.pricing_category == PricingCategory.FREE]

        return models

    @classmethod
    def get_default_model(cls, mode: ModelMode = ModelMode.FREE_ONLY) -> str:
        """
        Returns the appropriate default model ID based on mode.
        Guarantees a free model when mode is free_only.
        """
        return "nvidia/nemotron-3.5-lightning:free"

    @classmethod
    def validate_model_for_mode(cls, model_id: str, mode: ModelMode) -> Tuple[bool, Optional[str]]:
        """
        Strictly enforces mode restrictions.
        Under FREE_ONLY, paid models are rejected with 100% certainty.
        """
        model = cls.get_model(model_id)
        if not model:
            # Check ID pattern
            if mode == ModelMode.FREE_ONLY and not cls.is_free_model(model_id):
                return False, f"Model '{model_id}' is not recognized as a free model, and Free-Only mode is active."
            return True, None

        if mode == ModelMode.FREE_ONLY and model.pricing_category == PricingCategory.PAID:
            return (
                False,
                f"Cannot use paid model '{model.name}' ({model_id}) because Free-Only mode is active. "
                f"Switch to 'Paid-Enabled' mode in Settings to use premium models.",
            )

        return True, None

    @classmethod
    def filter_fallback_chain(cls, fallback_models: List[str], mode: ModelMode) -> List[str]:
        """
        Filters the fallback chain based on active mode.
        Never allows paid models in the chain when mode is FREE_ONLY.
        """
        filtered = []
        for m_id in fallback_models:
            if not m_id:
                continue
            if mode == ModelMode.FREE_ONLY:
                if cls.is_free_model(m_id):
                    filtered.append(m_id)
            else:
                filtered.append(m_id)
        return filtered

    @classmethod
    def estimate_cost(cls, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimates total execution cost in USD.
        Free models return exactly 0.0.
        """
        model = cls.get_model(model_id)
        if not model or model.pricing_category == PricingCategory.FREE:
            return 0.0

        cost_in = (prompt_tokens / 1_000_000.0) * model.cost_per_million_input
        cost_out = (completion_tokens / 1_000_000.0) * model.cost_per_million_output
        return round(cost_in + cost_out, 6)

    @classmethod
    def enrich_from_openrouter_catalog(cls, raw_models: List[Dict[str, Any]]):
        """
        Dynamically merges live OpenRouter model catalog into the central registry.
        """
        for m in raw_models:
            m_id = m.get("id")
            if not m_id or m_id in CENTRAL_MODELS_CATALOG:
                continue

            pricing = m.get("pricing") or {}
            is_free = cls.is_free_model(m_id, pricing)
            category = PricingCategory.FREE if is_free else PricingCategory.PAID

            try:
                p_in = float(pricing.get("prompt", 0)) * 1_000_000.0
                p_out = float(pricing.get("completion", 0)) * 1_000_000.0
            except (ValueError, TypeError):
                p_in = 0.0 if is_free else 1.0
                p_out = 0.0 if is_free else 2.0

            CENTRAL_MODELS_CATALOG[m_id] = CentralModelInfo(
                id=m_id,
                name=m.get("name", m_id),
                provider_type=ProviderType.OPENROUTER,
                pricing_category=category,
                cost_per_million_input=round(p_in, 4),
                cost_per_million_output=round(p_out, 4),
                context_limit=m.get("context_length") or 128000,
                supported_capabilities=[ModelCapability.CHAT.value, ModelCapability.STREAMING.value],
                is_available=True,
                is_default=False,
                description=m.get("description"),
            )
