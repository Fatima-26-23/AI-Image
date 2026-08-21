# FlyRank Capstone — AI Image Understanding & Content Matching Engine

Matches blog posts to the right image from a small corpus, using vision tagging +
semantic embeddings, with a mismatch guard that refuses low-confidence or
category-mismatched pairings instead of guessing.

## Status
Phases 1-4 implemented. See `EVIDENCE.md` for per-checkbox proof and
`BUILDLOG.md` for the AI-assisted build history.

**Top-1 precision: TODO%** -- run `python -m eval.run_eval` and paste the
number here (see `eval/run_eval.py`).

## Stack
Python + FastAPI · Gemini Flash (free tier) or Ollama/`llava` (local) for
vision · Gemini embeddings or Ollama/`all-minilm` (local) for embeddings ·
PostgreSQL

## Architecture

```
Images ─(batch job)─► Vision Model ─► {tags, caption, confidence} ─► image_metadata
        │                                                          └─► embed(caption) ──► image_vectors
Posts ──┴──────────────► embed(post text) ──────────────────────────────────────────────► post_vectors

GET /posts/:id/images
  └─► Similarity Ranking (image_vectors × post_vector, cosine similarity)
        └─► Mismatch Guard (flagged check → similarity threshold → subject/category overlap)
              ├─► Suggested image (ranked, explained)
              └─► "No good match" + explanation
  └─► Review API: GET /suggestions/:id · POST approve · POST reject
```

Layers (see `DESIGN.md` §4 for the full sketch):
```
HTTP layer      → FastAPI routers (app/routers/*)      — request validation, status codes only
Service layer   → app/services/*                       — ingestion, matching, guard, suggestions
Data layer      → app/models.py + app/db.py             — SQLAlchemy models (Postgres)
AI layer        → app/ai/*                              — vision client, embedding client (Gemini ↔ Ollama)
Jobs layer      → app/jobs/ingestion_job.py              — background batch runner, retries, cost tracking
```
Swapping the vision/embedding provider (Gemini ↔ Ollama) never touches the
service layer -- only `app/ai/*`.

## Setup

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Start Postgres** (Docker, simplest):
   ```
   docker run --name flyrank-pg -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=flyrank_capstone -p 5432:5432 -d postgres
   ```

3. **Configure `.env`** (copy `.env.example` and fill in):
   ```
   cp .env.example .env
   ```
   Set `VISION_PROVIDER` to `gemini` or `ollama`. For Ollama, make sure
   `ollama serve` is running and you've pulled the models:
   ```
   ollama pull llava
   ollama pull all-minilm
   ```

4. **Apply the schema:**
   ```
   psql postgresql://user:password@localhost:5432/flyrank_capstone -f db/schema.sql
   ```
   (Optional -- `app/main.py` also auto-creates tables on first run via
   `Base.metadata.create_all`.)

## Run

```
uvicorn app.main:app --reload
```

Server at `http://127.0.0.1:8000`. Check `GET /health`.

## Seed

Ingest and tag the image corpus (54 images across 5 animal categories --
fox, wolf, dog, bear, deer):
```
curl -X POST http://127.0.0.1:8000/images/ingest
```
Returns a `job_id`; poll `GET /jobs/{job_id}` until `"status": "completed"`.
With a local vision model this can take several minutes for the full corpus.

## Try it

```
curl -X POST http://127.0.0.1:8000/posts -H "Content-Type: application/json" \
  -d '{"title": "red fox", "content": "An article about the behavior and habitat of red foxes in the wild."}'

curl http://127.0.0.1:8000/posts/{id}/images
```

## Test

```
python -m pytest tests/ -v
```

## Evaluate

```
python -m eval.run_eval
```
Runs the labeled set in `eval/eval_set.json` against a live server and
reports top-1 precision.

## Limitations
- No pgvector -- cosine similarity runs in Python, which is fine at ~50
  images but won't scale past a few hundred without a real vector index.
- The category-mismatch check in the guard (`guard_service._subjects_match`)
  is deliberately simple word-overlap, not a second AI call -- this is a
  tradeoff for a fast, independent second signal, but it means subject
  labels that don't share any words (e.g. "canine" vs "fox") won't be
  caught by this check alone; the similarity threshold is the backstop.
- `cost_usd` is hardcoded to `0.0` for both Gemini's free tier and Ollama's
  local calls -- the *call* is tracked and attributed (Probe 6), but real
  paid-tier cost estimation isn't implemented since this project never
  leaves the free tier.
- No pagination on `/costs` or `/posts/{id}/suggestions` -- fine at this
  corpus size, would need it at scale.
