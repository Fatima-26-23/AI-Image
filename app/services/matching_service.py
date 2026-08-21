"""
Semantic matching. Given a post's embedding, rank all tagged, non-flagged
images by cosine similarity to the post.

No pgvector at this scale (~50 images, see DESIGN.md) — cosine similarity is
computed in Python over image_vectors pulled from the DB. This is a stretch
goal (pgvector) location if the corpus ever grows past a few hundred images;
for now it's correct and fast enough to not matter.
"""

import math

from sqlalchemy.orm import Session

from app.models import Image, ImageVector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"embedding dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_images_for_post(db: Session, post_embedding: list[float]) -> list[tuple[Image, float]]:
    """Return (image, similarity_score) pairs, highest similarity first.

    Excludes flagged images (low-confidence at ingestion) from ranking —
    an unreliable tag shouldn't be surfaced as a confident suggestion.
    """
    rows = (
        db.query(Image, ImageVector)
        .join(ImageVector, ImageVector.image_id == Image.id)
        .filter(Image.flagged.is_(False))
        .all()
    )

    scored = [
        (image, cosine_similarity(post_embedding, vector.embedding))
        for image, vector in rows
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
