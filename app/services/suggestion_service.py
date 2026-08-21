"""
Orchestrates the full match flow for a post: embed once (cached in
post_vectors), rank candidate images by similarity, run every candidate
through the mismatch guard, and persist the results as Suggestion rows so
the review API (Phase 4) has something to approve/reject.

This is a synchronous service (not a batch job) -- ranking ~50 images
against one post embedding is fast; only vision tagging and bulk embedding
generation need to be background work.
"""

from sqlalchemy.orm import Session

from app.ai.embedding_client import get_embedding_client
from app.models import Post, PostVector, Suggestion
from app.services.cost_tracker import log_cost
from app.services.guard_service import evaluate_guard
from app.services.matching_service import rank_images_for_post


def create_post_with_embedding(db: Session, title: str, content: str) -> Post:
    post = Post(title=title, content=content)
    db.add(post)
    db.commit()
    db.refresh(post)

    embedder = get_embedding_client()
    embedding = embedder.embed_text(content)
    db.add(PostVector(post_id=post.id, embedding=embedding))
    log_cost(db, call_type="embedding", reference_id=post.id, cost_usd=0.0)
    db.commit()

    return post


def get_ranked_suggestions(db: Session, post: Post, post_embedding: list[float], top_n: int = 5) -> dict:
    """Rank candidates, run the guard on each, persist Suggestion rows, and
    return a response shaped for the API: best accepted suggestion (if any)
    plus the full ranked list with each guard decision explained.
    """
    ranked = rank_images_for_post(db, post_embedding)[:top_n]

    results = []
    for image, score in ranked:
        guard = evaluate_guard(image, score, post_subject_hint=post.title)

        suggestion = Suggestion(
            post_id=post.id,
            image_id=image.id,
            similarity_score=score,
            guard_decision=guard.decision,
            guard_reason=guard.reason,
        )
        db.add(suggestion)
        db.commit()
        db.refresh(suggestion)

        results.append({
            "suggestion_id": suggestion.id,
            "image_id": image.id,
            "subject": image.subject,
            "category": image.category,
            "similarity_score": round(score, 4),
            "guard_decision": guard.decision,
            "guard_reason": guard.reason,
        })

    accepted = [r for r in results if r["guard_decision"] == "accepted"]

    if not accepted:
        return {
            "post_id": post.id,
            "match": None,
            "message": "No confident match found. Similarity below threshold, or detected "
                       "subjects do not match article topic.",
            "candidates": results,
        }

    return {
        "post_id": post.id,
        "match": accepted[0],
        "candidates": results,
    }
