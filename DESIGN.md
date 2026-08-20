# Design Doc — AI Image Understanding & Content Matching Engine

## 1. Problem
Given a library of ~50 images and a set of blog posts, automatically match each post
to the most relevant image based on *meaning*, not filenames or keywords. Reject a
match when no image is confidently relevant, instead of guessing. Core risk to guard
against: near-miss confusion (e.g. wolf image suggested for a fox post).

## 2. Data model (see `db/schema.sql` for DDL)
- **images** — raw file + extracted tags (subject, category, attributes, caption, confidence)
- **image_vectors** — embedding of each image's caption, one row per image
- **posts** — title + content
- **post_vectors** — embedding of each post's content, one row per post
- **suggestions** — a ranked (post, image) pair with similarity score, guard decision,
  guard reason, and human review status (pending / approved / rejected)

## 3. API surface (v1)
| Method | Path | Purpose |
|---|---|---|
| POST | `/images/ingest` | Enqueue a batch job to tag + embed all images in the corpus |
| GET | `/jobs/{job_id}` | Poll batch job status (progress, retries, cost so far) |
| POST | `/posts` | Create a post (triggers embedding) |
| GET | `/posts/{id}/images` | Get ranked image suggestions for a post (guard already applied) |
| POST | `/suggestions/{id}/approve` | Human approves a suggestion |
| POST | `/suggestions/{id}/reject` | Human rejects a suggestion |
| GET | `/costs` | Per-call cost log (vision + embedding calls) |

## 4. Layer sketch
```
HTTP layer      → FastAPI routers (request validation, status codes only)
Service layer   → ingestion service, matching service, guard service
Data layer      → SQLAlchemy models + repositories (Postgres)
AI layer        → vision client (Gemini Flash / Ollama), embedding client
Jobs layer      → background batch runner (retries, progress, cost tracking)
```
Swapping the vision provider (Gemini ↔ Ollama) or the DB should never require
touching the service layer — only the AI layer / data layer respectively.

## 5. Non-goal
No frontend build. The review workflow is API endpoints (+ optionally a bare
admin table), not a UI. Comparing multiple vision/embedding models is a stretch
goal, not core scope.

## 6. Confidence & guard thresholds (initial — tune with eval set in Phase 4)
- `confidence < 0.6` at ingestion → image flagged for manual review, not auto-used
- `cosine_similarity < 0.55` between post and image embedding → guard rejects
- Category mismatch between post's detected topic and image's `category`/`subject`
  → guard rejects regardless of similarity score, with explanation

## 7. Initial dataset plan
~50 images, licensed-free (Unsplash/Pexels), animal category to start:
red fox, wolf, dog, bear, deer (~10 each). Small labeled eval set (Phase 4) will
mark, per test post, which image is the "correct" one — used to compute top-1 precision.
