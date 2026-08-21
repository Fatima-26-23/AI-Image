"""
Embedding layer. Same provider-swap shape as app.ai.vision_client — the
service layer never branches on Gemini vs Ollama, it just calls embed_text().

Both providers return a plain list[float]. Dimensions differ by provider/model
(Gemini text-embedding-004 = 768 dims, Ollama all-minilm = 384 dims) — this is
fine as long as image embeddings and post embeddings always come from the same
provider, since cosine similarity requires matching dimensionality. If you ever
switch providers mid-project, re-embed everything, don't mix dimensions.
"""

from abc import ABC, abstractmethod

import httpx

from app.config import settings


class EmbeddingClient(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Return an embedding vector for the given text."""
        raise NotImplementedError


class GeminiEmbeddingClient(EmbeddingClient):
    def __init__(self, api_key: str | None = None):
        from google import genai  # imported lazily, same reason as vision_client

        self.client = genai.Client(api_key=api_key or settings.gemini_api_key)

    def embed_text(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return list(response.embeddings[0].values)


class OllamaEmbeddingClient(EmbeddingClient):
    def __init__(self, base_url: str | None = None, model: str = "all-minilm"):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model

    def embed_text(self, text: str) -> list[float]:
        resp = httpx.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


def get_embedding_client() -> EmbeddingClient:
    """Factory — reads app.config.settings, mirrors get_vision_client()."""
    if settings.vision_provider == "ollama":
        return OllamaEmbeddingClient()
    return GeminiEmbeddingClient()
