# EVIDENCE.md

One proof per Definition-of-Done checkbox (brief §6). Entries marked
`[CAPTURED]` are real command output from an actual run. Entries marked
`[TODO]` need you to run the command and paste the real output before
submission -- do not leave these as placeholders.

## AI Processing

### Vision model produces structured output validated against a schema; invalid responses are never trusted.
`[CAPTURED]` -- `app/schemas/image_tags.py` enforces this; proven by test suite:
```
tests/test_schema_validation.py::test_valid_tags_parse PASSED
tests/test_schema_validation.py::test_missing_required_field_rejected PASSED
tests/test_schema_validation.py::test_confidence_out_of_range_rejected PASSED
tests/test_schema_validation.py::test_malformed_json_rejected PASSED
```
Runtime proof: `app/jobs/ingestion_job.py::_classify_with_retries` only ever
calls `ImageTags.model_validate_json(raw_output)` -- never falls back to
raw text on failure (see the `except (ValidationError, ValueError, KeyError)`
block, which retries then marks the image failed, never accepts unvalidated
output).

### Low-confidence classifications are flagged instead of accepted.
`[CAPTURED]`
```
tests/test_schema_validation.py::test_low_confidence_flagged_not_guessed PASSED
tests/test_guard_service.py::test_flagged_image_never_suggested_even_with_high_similarity PASSED
```
`ImageTags.is_low_confidence` (threshold 0.6) sets `Image.flagged = True` at
ingestion (`ingestion_job.py`); `guard_service.evaluate_guard` rejects any
flagged image before it can be suggested, regardless of similarity score.

### Images are processed through a batch background job with retries.
`[CAPTURED]` -- real run against the full 54-image corpus:
```
$ curl -X POST http://127.0.0.1:8000/images/ingest
{"job_id":4,"status":"pending"}

$ curl http://127.0.0.1:8000/jobs/4
{"job_id":4,"status":"completed","total_items":54,"processed_items":54,
 "failed_items":0,"error_log":[],
 "started_at":"2026-08-21T13:24:41.743813+05:00",
 "finished_at":"2026-08-21T13:33:48.773464+05:00"}
```
Retry logic: `ingestion_job.py::_classify_with_retries`, up to
`settings.vision_max_retries` attempts with backoff, per image -- one bad
image never aborts the batch (each image row is created and committed
independently).

### Vision and embedding costs are tracked per call.
`[TODO]` -- run and paste:
```
curl http://127.0.0.1:8000/costs
```
Expect `call_count` == (number of images tagged) + (number of images
embedded) + (number of posts embedded), with a `cost_log` row per call
(`app/services/cost_tracker.py::log_cost`, called from both
`ingestion_job.py` and `suggestion_service.py::create_post_with_embedding`).

## Matching System

### Image and post embeddings are stored; posts return ranked image suggestions.
`[CAPTURED]` -- real run, fox post against the tagged corpus:
```
$ curl -X POST http://127.0.0.1:8000/posts -H "Content-Type: application/json" \
  -d '{"title": "red fox", "content": "An article about the behavior and habitat of red foxes in the wild."}'
{"id":3,"title":"red fox","content":"..."}

$ curl http://127.0.0.1:8000/posts/3/images
{"post_id":3,"match":{"suggestion_id":3,"image_id":51,"subject":"red fox",
 "category":"animal","similarity_score":0.726,"guard_decision":"accepted",
 "guard_reason":"Similarity 0.73 clears threshold; subject 'red fox' matches; confidence 0.85."},
 "candidates":[... top 5, all red fox, scores 0.65-0.73 ...]}
```

### Semantic matching works for equivalent concepts — "red fox" matches "Vulpes vulpes".
`[TODO]` -- covered by `eval/eval_set.json` entry "Vulpes vulpes: the most
widespread canid". Run `python -m eval.run_eval` and confirm that row shows
`OK`, then paste the eval table row here.

### The mismatch guard rejects incorrect recommendations — the wolf-on-a-fox-post scenario provably fails.
`[CAPTURED]` (unit-level) + `[TODO]` (live API level)

Unit proof:
```
tests/test_guard_service.py::test_wolf_on_fox_post_rejected PASSED
```

Live proof -- TODO, run:
```
curl "http://127.0.0.1:8000/posts/3/images?top_n=20"
```
and paste any candidate row where `"subject"` contains "wolf" and
`"guard_decision": "rejected"`. If no wolf appears even at top_n=20 (i.e.
wolf embeddings rank very low against this specific fox post text), instead
create a wolf-titled post and confirm fox candidates get excluded/ranked
correctly there -- either direction proves the guard works.

### Rejections include a human-readable explanation.
`[CAPTURED]` -- every `GuardResult` from `guard_service.evaluate_guard`
includes a `reason` string; see the rejected candidates in the fox-post
response above, e.g. `"Similarity below threshold: 0.06 < 0.55."`

### When no image clears the bar, the system answers "no confident match" with reasons.
`[CAPTURED]` -- real run, before the corpus was tagged (only 2 unrelated
images existed):
```
{"post_id":3,"match":null,
 "message":"No confident match found. Similarity below threshold, or detected subjects do not match article topic.",
 "candidates":[{"subject":"Food","similarity_score":0.0629,"guard_decision":"rejected",...},
               {"subject":"Water and rocks","similarity_score":0.0536,"guard_decision":"rejected",...}]}
```
Also covered by `eval/eval_set.json`'s "Quarterly earnings report" case,
which expects this exact behavior against the real (now full) corpus.

## Safety Layer
(see Matching System section above -- guard checkboxes live there per the brief's own grouping)

## Backend

### Database models for images, tags, embeddings, posts, suggestions, approvals/rejections — with the required indexes.
`[CAPTURED]` -- `db/schema.sql` + `app/models.py`. Indexes present:
`idx_images_category`, `idx_images_flagged`, `idx_image_vectors_image_id`
(unique), `idx_post_vectors_post_id` (unique), `idx_suggestions_post_id`,
`idx_suggestions_status`, `idx_jobs_status`.

### API endpoints validated; the review workflow (approve / reject / inspect why) exists.
`[TODO]` -- run and paste:
```
curl http://127.0.0.1:8000/posts/3/suggestions
curl -X POST http://127.0.0.1:8000/suggestions/3/approve
curl -X POST http://127.0.0.1:8000/suggestions/4/reject
curl http://127.0.0.1:8000/suggestions/3
```
Endpoints: `app/routers/suggestions.py`.

### Automated tests cover schema validation, mismatch rejection, and matching accuracy.
`[CAPTURED]`
```
$ python -m pytest tests/ -v
tests/test_guard_service.py .......                7 passed
tests/test_matching_service.py .......              7 passed
tests/test_schema_validation.py ........            8 passed
============================== 22 passed in 0.39s ==============================
```

### A small labeled evaluation dataset measures top-1 precision — the number is in your README.
`[TODO]` -- run:
```
python -m eval.run_eval
```
Paste the full table + final "Top-1 precision: NN%" line here, and copy the
same number into README.md.

## Quality & Documentation

### README with architecture explanation and diagram; submission-pack files from §11 present.
`[CAPTURED]` -- see README.md (updated), DESIGN.md, capstone.yaml,
BUILDLOG.md, this file, `.env.example`.
