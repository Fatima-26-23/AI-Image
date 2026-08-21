"""
Definition of Done: "The mismatch guard rejects incorrect recommendations
-- the wolf-on-a-fox-post scenario provably fails. Rejections include a
human-readable explanation."

These construct Image model instances directly (no DB needed) since
evaluate_guard() takes an Image object + score, not a session.
"""

from app.config import settings
from app.models import Image
from app.services.guard_service import evaluate_guard


def make_image(**overrides) -> Image:
    defaults = dict(
        filepath="data/images/img_red_fox_1.jpg",
        subject="red fox",
        category="animal",
        attributes=["orange fur", "wild"],
        caption="A red fox in a forest",
        confidence=0.9,
        flagged=False,
    )
    defaults.update(overrides)
    return Image(**defaults)


def test_wolf_on_fox_post_rejected():
    """The exact scenario named in the brief: a wolf candidate for a fox post."""
    wolf = make_image(subject="gray wolf", category="animal", confidence=0.9)
    result = evaluate_guard(wolf, similarity_score=0.7, post_subject_hint="red fox")
    assert result.decision == "rejected"
    assert "mismatch" in result.reason.lower()
    assert result.reason  # never an empty/unexplained rejection


def test_matching_fox_accepted():
    fox = make_image(subject="red fox", category="animal", confidence=0.9)
    result = evaluate_guard(fox, similarity_score=0.7, post_subject_hint="red fox")
    assert result.decision == "accepted"
    assert result.reason


def test_low_similarity_rejected_even_if_subject_matches():
    fox = make_image(subject="red fox", confidence=0.9)
    result = evaluate_guard(fox, similarity_score=0.1, post_subject_hint="red fox")
    assert result.decision == "rejected"
    assert "similarity" in result.reason.lower()


def test_flagged_image_never_suggested_even_with_high_similarity():
    """A low-confidence-at-ingestion image must never be auto-suggested,
    regardless of how well its embedding happens to rank."""
    flagged_fox = make_image(subject="red fox", confidence=0.3, flagged=True)
    result = evaluate_guard(flagged_fox, similarity_score=0.95, post_subject_hint="red fox")
    assert result.decision == "rejected"
    assert "flagged" in result.reason.lower() or "confidence" in result.reason.lower()


def test_similarity_exactly_at_threshold_accepted():
    fox = make_image(subject="red fox", confidence=0.9)
    result = evaluate_guard(fox, similarity_score=settings.similarity_threshold, post_subject_hint="red fox")
    assert result.decision == "accepted"


def test_no_subject_hint_skips_category_check():
    """If the caller has no post-subject hint, only similarity + confidence
    gate the decision -- the category check is best-effort, not mandatory."""
    wolf = make_image(subject="gray wolf", confidence=0.9)
    result = evaluate_guard(wolf, similarity_score=0.9, post_subject_hint=None)
    assert result.decision == "accepted"


def test_rejection_reason_always_present():
    """Every rejection path must explain itself -- the brief calls this out
    explicitly as a Definition-of-Done box, not an implementation detail."""
    cases = [
        make_image(flagged=True),
        make_image(subject="red fox"),  # will fail on similarity below
    ]
    for image, score in zip(cases, [0.9, 0.1]):
        result = evaluate_guard(image, similarity_score=score, post_subject_hint="red fox")
        if result.decision == "rejected":
            assert len(result.reason) > 10
