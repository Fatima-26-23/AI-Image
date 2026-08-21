from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.jobs.ingestion_job import run_ingestion_job
from app.models import CostLog, Job

router = APIRouter()


def _run_job_in_own_session(job_id: int) -> None:
    """Background tasks get their own DB session — never reuse the request's,
    since the request may have already returned by the time this runs."""
    db = SessionLocal()
    try:
        run_ingestion_job(db, job_id)
    finally:
        db.close()


@router.post("/images/ingest", status_code=202)
def ingest_images(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = Job(job_type="ingestion", status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_job_in_own_session, job.id)

    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "failed_items": job.failed_items,
        "error_log": job.error_log,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/costs")
def get_costs(db: Session = Depends(get_db)):
    rows = db.query(CostLog).all()
    return {
        "total_cost_usd": sum(r.cost_usd for r in rows),
        "call_count": len(rows),
        "entries": [
            {"id": r.id, "call_type": r.call_type, "reference_id": r.reference_id, "cost_usd": r.cost_usd}
            for r in rows
        ],
    }
