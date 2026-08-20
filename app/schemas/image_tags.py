"""
Schema for validated vision-model output.

Every response from the vision model MUST be parsed through this schema
before it is trusted anywhere else in the system. Use:

    from app.schemas.image_tags import ImageTags
    tags = ImageTags.model_validate_json(raw_model_output)

If validation fails, retry the vision call (with a stricter prompt) or
mark the image as failed — never fall back to unvalidated text.
"""

from pydantic import BaseModel, Field

# Images below this confidence are flagged for human review instead of
# being trusted automatically. Tune this once the Phase 4 eval set exists.
LOW_CONFIDENCE_THRESHOLD = 0.6


class ImageTags(BaseModel):
    subject: str = Field(
        ..., min_length=1, max_length=100,
        description="Main subject of the image, e.g. 'red fox'",
    )
    category: str = Field(
        ..., min_length=1, max_length=50,
        description="Broad category, e.g. 'animal'",
    )
    attributes: list[str] = Field(
        default_factory=list, max_length=8,
        description="Descriptive tags, e.g. ['orange fur', 'wild', 'forest']",
    )
    caption: str = Field(
        ..., min_length=1, max_length=200,
        description="One-sentence natural-language description, used for embedding",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model's own confidence estimate for this classification",
    )

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < LOW_CONFIDENCE_THRESHOLD
