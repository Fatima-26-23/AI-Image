"""
Per-call cost tracking. Every vision or embedding call gets logged here —
even on the free tier — so /costs is honest and PROBE 6 in the brief
("every vision/embedding call attributed with a cost entry") passes.

Gemini Flash free-tier calls cost $0, but we still log a row with cost_usd=0
so the *call itself* is auditable, not just paid usage.
"""

from sqlalchemy.orm import Session

from app.models import CostLog

# Approximate paid-tier pricing, used only if you switch off the free tier.
# Free-tier calls should pass cost_usd=0.0 explicitly.
GEMINI_FLASH_VISION_COST_PER_CALL = 0.0
GEMINI_EMBEDDING_COST_PER_CALL = 0.0


def log_cost(db: Session, call_type: str, reference_id: int, cost_usd: float = 0.0) -> CostLog:
    if call_type not in ("vision", "embedding"):
        raise ValueError(f"invalid call_type: {call_type}")

    entry = CostLog(call_type=call_type, reference_id=reference_id, cost_usd=cost_usd)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def total_cost(db: Session) -> float:
    return sum(row.cost_usd for row in db.query(CostLog).all())
