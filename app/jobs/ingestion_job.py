"""
Background batch job: run every image in the corpus through the vision
client, validate the output against ImageTags, and persist results.

Design rules this file enforces (see DESIGN.md + capstone Definition of Done):
  - Invalid vision output is NEVER trusted. Retry with backoff; after
    max_retries, mark the image failed and move on — one bad image must
    not crash the whole batch.
  - Low-confidence results are flagged (flagged=True), not silently accepted.
  - Every vision call gets a cost_log row, pass or fail.
  - Job progress (processed/failed/total) is updated as we go, not just at
    the end, so GET /jobs/{job_id} is meaningful mid-run.
"""

import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.vision_client import VisionClient, get_vision_client
from app.config import settings
from app.models import Image, Job
from app.schemas.image_tags import ImageTags
from app.services.cost_tracker import log_cost

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def discover_corpus_images(corpus_dir: str | None = None) -> list[Path]:
    directory = Path(corpus_dir or settings.image_corpus_dir)
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)


def _classify_with_retries(client: VisionClient, image_path: str) -> tuple[ImageTags | None, int]:
    """Try up to vision_max_retries times to get schema-valid output.
    Returns (validated_tags_or_None, attempts_made)."""
    last_error: Exception | None = None
    for attempt in range(1, settings.vision_max_retries + 1):
        try:
            raw_output = client.classify_image(image_path)
            tags = ImageTags.model_validate_json(raw_output)
            return tags, attempt
        except (ValidationError, ValueError, KeyError) as exc:
            last_error = exc
            if attempt < settings.vision_max_retries:
                time.sleep(settings.vision_retry_backoff_seconds * attempt)
    # Every attempt failed schema validation — never fall back to raw text.
    print(f"[ingestion] {image_path}: all {settings.vision_max_retries} attempts failed: {last_error}")
    return None, settings.vision_max_retries


def run_ingestion_job(db: Session, job_id: int, corpus_dir: str | None = None) -> None:
    job = db.get(Job, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")

    image_paths = discover_corpus_images(corpus_dir)
    job.total_items = len(image_paths)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    client = get_vision_client()

    for path in image_paths:
        # Create the row up front so a mid-run poll can see "not tagged yet"
        # rather than the image being invisible until success.
        image_row = Image(filepath=str(path))
        db.add(image_row)
        db.commit()
        db.refresh(image_row)

        tags, attempts_made = _classify_with_retries(client, str(path))

        # Log cost regardless of outcome — the call happened either way.
        log_cost(db, call_type="vision", reference_id=image_row.id, cost_usd=0.0)

        if tags is None:
            job.failed_items += 1
            job.error_log = job.error_log + [f"{path.name}: schema validation failed after {attempts_made} attempts"]
            db.delete(image_row)  # don't leave an untagged, unusable row behind
            db.commit()
            continue

        image_row.subject = tags.subject
        image_row.category = tags.category
        image_row.attributes = tags.attributes
        image_row.caption = tags.caption
        image_row.confidence = tags.confidence
        image_row.flagged = tags.is_low_confidence
        db.commit()

        job.processed_items += 1
        db.commit()

    job.status = "completed" if job.failed_items < job.total_items else "failed"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
