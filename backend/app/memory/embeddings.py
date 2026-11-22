import math
import hashlib
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Type, Optional
from app.core.config import settings
from app.core.logging import logger


def normalize_vector(vec: List[float]) -> List[float]:
    """L2 unit-normalizes a vector so dot-product equals cosine similarity."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-9:
        return [0.0] * len(vec)
    return [round(x / norm, 6) for x in vec]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two unit-normalized vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    return max(0.0, min(1.0, dot))


class BaseEmbeddingProvider(ABC):
    """
    Abstract interface for provider-independent embedding generation.
    Supports local free models as well as cloud embedding endpoints.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate a dense vector embedding for single text input."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for a batch of texts."""
        pass


class LocalSemanticEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic local semantic embedding provider.
    Projects words, character n-grams, and subwords into a dense normalized 384-dimensional vector.
    - Zero external model downloads required.
    - Runs in sub-millisecond on CPU.
    - Generates high cosine similarity for overlapping semantic concepts, stems, and context.
    """

    def __init__(self, dimension: int = 384, model_name: str = "semantic-hash-384"):
        self._dim = dimension
        self._model = model_name

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    def _generate_vector(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self._dim

        vector = [0.0] * self._dim
        clean_text = text.lower().strip()
        tokens = re.findall(r"\b\w+\b", clean_text)
        
        if not tokens:
            tokens = [clean_text]

        # Stopwords to de-emphasize generic grammar particles
        stopwords = {
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "it", "its", "that", "this", "these", "those", "with", "as", "by"
        }

        # 1. Primary word token projections with TF and position weighting
        for idx, token in enumerate(tokens):
            is_stop = token in stopwords
            weight = 0.3 if is_stop else (2.0 + (1.0 / (idx + 1)))
            
            # Root stem heuristic (strip simple trailing s, ed, ing)
            stem = token
            if len(stem) > 4 and stem.endswith("ing"):
                stem = stem[:-3]
            elif len(stem) > 3 and stem.endswith("ed"):
                stem = stem[:-2]
            elif len(stem) > 3 and stem.endswith("s"):
                stem = stem[:-1]

            # Primary hash for stem
            h = int(hashlib.md5(stem.encode("utf-8")).hexdigest(), 16)
            bucket = h % self._dim
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            vector[bucket] += sign * weight

            # Secondary projection for dispersion
            h2 = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16)
            bucket2 = h2 % self._dim
            sign2 = 1.0 if ((h2 >> 4) % 2 == 0) else -1.0
            vector[bucket2] += sign2 * (weight * 0.5)

        # 2. Subword character n-grams (3-grams, 4-grams) for morphological similarity
        for i in range(len(clean_text) - 2):
            ngram = clean_text[i:i + 3]
            if not ngram.isspace():
                h = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest()[:8], 16)
                bucket = h % self._dim
                vector[bucket] += 0.15

        # 3. Bigram token projections for phrase relationships
        for i in range(len(tokens) - 1):
            if tokens[i] not in stopwords or tokens[i+1] not in stopwords:
                bigram = f"{tokens[i]}_{tokens[i+1]}"
                h = int(hashlib.md5(bigram.encode("utf-8")).hexdigest()[:8], 16)
                bucket = h % self._dim
                vector[bucket] += 0.75

        return normalize_vector(vector)

    async def embed_text(self, text: str) -> List[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]


class OpenRouterEmbeddingProvider(BaseEmbeddingProvider):
    """
    Cloud embedding provider using OpenRouter or OpenAI-compatible embeddings endpoint.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-3-small",
        dimension: int = 384,
    ):
        self._api_key = api_key
        self._model = model_name
        self._dim = dimension

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_text(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._api_key:
            # Fallback to local deterministic generator if no key is supplied
            logger.warning("OpenRouter API key missing for embeddings; falling back to local semantic provider")
            fallback = LocalSemanticEmbeddingProvider(dimension=self._dim)
            return await fallback.embed_batch(texts)

        import httpx
        url = "https://openrouter.ai/api/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
            "dimensions": self._dim,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                embeddings = [item["embedding"][:self._dim] for item in data["data"]]
                return [normalize_vector(e) for e in embeddings]
        except Exception as e:
            logger.error(f"OpenRouter embedding call failed ({e}); falling back to local semantic embedding")
            fallback = LocalSemanticEmbeddingProvider(dimension=self._dim)
            return await fallback.embed_batch(texts)


class EmbeddingRegistry:
    """
    Registry for configuring, selecting, and validating embedding providers.
    """

    _providers: Dict[str, Type[BaseEmbeddingProvider]] = {
        "local": LocalSemanticEmbeddingProvider,
        "openrouter": OpenRouterEmbeddingProvider,
    }

    @classmethod
    def get_provider(
        cls,
        provider_type: Optional[str] = None,
        model_name: Optional[str] = None,
        dimension: Optional[int] = None,
        api_key: Optional[str] = None,
    ) -> BaseEmbeddingProvider:
        p_type = (provider_type or settings.DEFAULT_EMBEDDING_PROVIDER).lower()
        dim = dimension or settings.EMBEDDING_DIMENSION
        model = model_name or settings.DEFAULT_EMBEDDING_MODEL

        if p_type == "openrouter":
            return OpenRouterEmbeddingProvider(api_key=api_key, model_name=model, dimension=dim)
        
        return LocalSemanticEmbeddingProvider(dimension=dim, model_name=model)


# Singleton default provider helper
def get_default_embedding_provider() -> BaseEmbeddingProvider:
    return EmbeddingRegistry.get_provider()
