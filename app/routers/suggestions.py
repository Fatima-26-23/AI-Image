"""
Review API (brief §4.5). A suggestion already carries its guard decision and
reason from the matching step (app.services.suggestion_service) -- this
router is the human-in-the-loop layer on top: approve, reject, or inspect
why a suggestion was ranked/accepted/rejected the way it was.

Deliberately no UI (per brief §7 -- "API endpoints ... are enough"). GET
/suggestions/{id} covers "inspect why an image was selected or refused".
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Suggestion

router = APIRouter()


def _serialize(s: Suggestion) -> dict:
    return {
        "suggestion_id": s.id,
        "post_id": s.post_id,
        "image_id": s.image_id,
        "similarity_score": s.similarity_score,
        "guard_decision": s.guard_decision,
        "guard_reason": s.guard_reason,
        "status": s.status,
        "created_at": s.created_at,
    }


@router.get("/suggestions/{suggestion_id}")
def get_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    """Inspect why an image was selected or refused for a post."""
    suggestion = db.get(Suggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="suggestion not found")
    return _serialize(suggestion)


@router.post("/suggestions/{suggestion_id}/approve")
def approve_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    suggestion = db.get(Suggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="suggestion not found")
    if suggestion.guard_decision == "rejected":
        # A human can still override the guard -- that's the point of a
        # review workflow -- but it must be a deliberate, visible act, not
        # silently possible. Log it as an explicit override in the reason.
        suggestion.guard_reason = (suggestion.guard_reason or "") + " [human override: approved despite guard rejection]"
    suggestion.status = "approved"
    db.commit()
    db.refresh(suggestion)
    return _serialize(suggestion)


@router.post("/suggestions/{suggestion_id}/reject")
def reject_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    suggestion = db.get(Suggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="suggestion not found")
    suggestion.status = "rejected"
    db.commit()
    db.refresh(suggestion)
    return _serialize(suggestion)


@router.get("/posts/{post_id}/suggestions")
def list_suggestions_for_post(post_id: int, db: Session = Depends(get_db)):
    """Full review trail for a post -- every candidate ever suggested, not
    just the currently-ranked top N. Useful for the demo's 'approve one,
    reject another' beat (brief §13)."""
    rows = db.query(Suggestion).filter(Suggestion.post_id == post_id).all()
    return {"post_id": post_id, "suggestions": [_serialize(s) for s in rows]}
