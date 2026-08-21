# BUILDLOG.md

Honest log of where AI (Claude) helped, where it was wrong, and what was
changed. Per the brief: "The AI wrote it" is not an answer at the demo --
this file is what lets you actually explain any 2-3 lines an evaluator
picks.

---

## Phase 1 -- Design
- AI drafted the initial `DESIGN.md` structure and `db/schema.sql` from the
  brief's data model description.
- I reviewed and confirmed the threshold values (0.6 confidence, 0.55
  similarity) as reasonable starting points -- these are explicitly meant
  to be re-tuned in Phase 4 against the real eval set, not treated as final.

## Phase 2 -- Vision pipeline
- AI wrote `vision_client.py` (Gemini + Ollama provider split) and
  `ingestion_job.py` (retry/backoff loop, per-image error isolation).
- Caught and fixed myself: initial run used the wrong `VISION_PROVIDER` env
  value (defaulted to Gemini in code, but I'm actually running Ollama
  locally) -- this caused `ConnectionRefusedError` against Gemini's
  non-existent local endpoint. Fixed by explicitly setting
  `VISION_PROVIDER=ollama` in `.env` and pulling `llava` + `all-minilm`.
- Real corpus run: 54/54 images tagged, 0 failures, ~9 minutes locally on
  `llava` (see EVIDENCE.md for the job output).

## Phase 3 -- Matching engine
- AI wrote `embedding_client.py`, `matching_service.py` (cosine similarity
  + ranking), `guard_service.py` (the mismatch guard), and
  `suggestion_service.py` (orchestration).
- I reviewed the guard's decision order (flagged check -> similarity
  threshold -> subject overlap) and agreed with AI's reasoning that subject
  overlap needs to be a *separate, non-embedding* signal -- if it reused
  the same embedding comparison, a near-miss like wolf/fox that fools the
  embedding would also fool the guard, defeating the point.
- Verified live against the real corpus: fox post (`/posts/3/images`)
  correctly surfaced 5 fox images, all accepted, similarity 0.65-0.73,
  before the corpus was tagged it correctly returned "no confident match"
  against 2 irrelevant leftover test images -- see EVIDENCE.md.

## Phase 4 -- Production layer
- AI wrote `suggestions.py` (review API), the pytest suite
  (`tests/test_schema_validation.py`, `test_guard_service.py`,
  `test_matching_service.py`), `eval/eval_set.json`, and
  `eval/run_eval.py`.
- One thing I changed from AI's first draft: the human-override behavior on
  `POST /suggestions/{id}/approve` -- AI initially had it silently approve
  a guard-rejected suggestion with no trace. I asked for the override to be
  visibly logged in `guard_reason` instead, since a silent override would
  make EVIDENCE.md/audit trail dishonest about what the guard actually
  decided vs what a human overrode.
- [TODO once you run eval/run_eval.py]: note here if any eval cases needed
  threshold retuning, and what you changed and why.

---

*Update this file as you go, not in a panic before submission -- per the
brief's own advice.*
