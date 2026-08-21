"""
The mismatch guard. This is the production-critical layer the whole
capstone is built around (see brief §4.3): a similarity score alone is not
enough to trust a suggestion. Two failure modes it exists to catch:

  1. Near-miss confusion — a wolf image scores decently high on a fox post
     because "wild animal in forest" embeddings are close, even though the
     subject is wrong. Similarity alone would accept this; the guard won't.
  2. Low-confidence tags — an image flagged at ingestion (confidence < 0.6)
     should never be silently suggested, even if its embedding happens to
     rank well.

Every decision returns a human-readable reason — accepted or rejected —
because "why was this suggested / refused" is a Definition-of-Done
requirement (§6), not a nice-to-have.
"""

from dataclasses import dataclass

from app.config import settings
from app.models import Image


@dataclass
class GuardResult:
    decision: str  # "accepted" | "rejected"
    reason: str


def evaluate_guard(image: Image, similarity_score: float, post_subject_hint: str | None = None) -> GuardResult:
    """Decide whether a candidate image is a good enough match for a post.

    post_subject_hint: an optional detected/declared subject for the post
    (e.g. "red fox"), used for the category-mismatch check. If the caller
    doesn't have one, only the similarity + confidence checks apply.
    """
    if image.flagged:
        return GuardResult(
            decision="rejected",
            reason=f"Image {image.id} was flagged for low classification confidence at ingestion "
                    f"(confidence={image.confidence:.2f}) and is never auto-suggested.",
        )

    if similarity_score < settings.similarity_threshold:
        return GuardResult(
            decision="rejected",
            reason=f"Similarity below threshold: {similarity_score:.2f} < {settings.similarity_threshold:.2f}.",
        )

    if post_subject_hint and image.subject:
        if not _subjects_match(post_subject_hint, image.subject):
            return GuardResult(
                decision="rejected",
                reason=f"Category mismatch: expected subject related to '{post_subject_hint}', "
                       f"detected '{image.subject}'.",
            )

    return GuardResult(
        decision="accepted",
        reason=f"Similarity {similarity_score:.2f} clears threshold; subject '{image.subject}' "
               f"matches; confidence {image.confidence:.2f}.",
    )


def _subjects_match(post_subject: str, image_subject: str) -> bool:
    """Cheap lexical guard on top of the semantic similarity check.

    This is intentionally simple (substring/token overlap), not another
    embedding call — the whole point is a second, *different* signal from
    similarity, so a wolf/fox near-miss on embeddings still gets caught by
    tags disagreeing. If this proves too strict/loose against the Phase 4
    eval set, tune here — not by changing the similarity threshold, since
    that's a different failure mode.
    """
    post_tokens = set(post_subject.lower().split())
    image_tokens = set(image_subject.lower().split())
    return bool(post_tokens & image_tokens)
