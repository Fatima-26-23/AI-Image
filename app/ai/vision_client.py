"""
Vision AI layer. Swapping Gemini <-> Ollama should never touch the service
layer above it — both providers return the same thing: raw JSON text that
the caller must still validate against app.schemas.image_tags.ImageTags.

This module does NOT validate output. It only talks to the provider and
returns raw text. Validation is the ingestion service's job (schema trust
boundary lives one layer up, per DESIGN.md).
"""

import base64
from abc import ABC, abstractmethod

import httpx

from app.config import settings

VISION_PROMPT = """Look at this image and respond with ONLY a JSON object (no markdown, \
no prose) matching this exact shape:
{
  "subject": "<main subject, e.g. 'red fox'>",
  "category": "<broad category, e.g. 'animal'>",
  "attributes": ["<up to 8 short descriptive tags>"],
  "caption": "<one-sentence natural language description>",
  "confidence": <float 0.0-1.0, your own confidence in this classification>
}"""


class VisionClient(ABC):
    @abstractmethod
    def classify_image(self, image_path: str) -> str:
        """Return raw text output from the vision model. Caller validates it."""
        raise NotImplementedError


class GeminiVisionClient(VisionClient):
    def __init__(self, api_key: str | None = None):
        from google import genai  # imported lazily so Ollama-only users don't need it

        self.client = genai.Client(api_key=api_key or settings.gemini_api_key)

    def classify_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"inline_data": {"mime_type": _mime_type(image_path), "data": image_bytes}},
                VISION_PROMPT,
            ],
        )
        return response.text


class OllamaVisionClient(VisionClient):
    def __init__(self, base_url: str | None = None, model: str = "llava"):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model

    def classify_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        resp = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": VISION_PROMPT,
                "images": [image_b64],
                "stream": False,
                "format": "json",
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["response"]


def _mime_type(path: str) -> str:
    ext = path.lower().rsplit(".", 1)[-1]
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "image/jpeg"
    )


def get_vision_client() -> VisionClient:
    """Factory — reads app.config.settings so callers never branch on provider."""
    if settings.vision_provider == "ollama":
        return OllamaVisionClient()
    return GeminiVisionClient()
