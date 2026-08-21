"""
Runs the labeled eval set (eval/eval_set.json) against a live instance of
the API and reports top-1 precision -- the headline number required in
README.md (Definition of Done, Probe 5).

Usage:
    python -m eval.run_eval
    python -m eval.run_eval --base-url http://127.0.0.1:8000

Requires the server running AND the image corpus already ingested
(POST /images/ingest completed) -- this script only creates posts and reads
suggestions, it does not tag images itself.

Methodology: for each labeled post, we create it, fetch its top-N ranked
suggestions, and check whether the guard's ACCEPTED top-1 candidate's
subject contains the expected substring (case-insensitive). A post with
expected_subject_contains = null is correct only if the system returns NO
accepted match -- this is what tests the "safe rejection" half of the
Definition of Done, not just "did it find something".
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"


def run_eval(base_url: str) -> None:
    eval_set = json.loads(EVAL_SET_PATH.read_text())
    client = httpx.Client(base_url=base_url, timeout=30.0)

    correct = 0
    results = []

    for case in eval_set:
        resp = client.post("/posts", json={"title": case["title"], "content": case["content"]})
        resp.raise_for_status()
        post_id = resp.json()["id"]

        resp = client.get(f"/posts/{post_id}/images", params={"top_n": 10})
        resp.raise_for_status()
        data = resp.json()

        expected = case["expected_subject_contains"]
        match = data.get("match")

        if expected is None:
            # Correct only if the system correctly found NO confident match.
            is_correct = match is None
            actual = "no match" if match is None else f"matched '{match['subject']}' (should have refused)"
        else:
            is_correct = match is not None and expected.lower() in (match.get("subject") or "").lower()
            actual = match["subject"] if match else "no match (expected one)"

        if is_correct:
            correct += 1

        results.append({
            "title": case["title"],
            "expected": expected or "(no confident match)",
            "actual": actual,
            "correct": is_correct,
        })

    precision = correct / len(eval_set) if eval_set else 0.0

    print(f"\n{'Post':<45} {'Expected':<20} {'Actual':<30} {'OK'}")
    print("-" * 105)
    for r in results:
        mark = "✓" if r["correct"] else "✗"
        print(f"{r['title'][:44]:<45} {r['expected'][:19]:<20} {str(r['actual'])[:29]:<30} {mark}")

    print(f"\nTop-1 precision: {precision:.0%} ({correct}/{len(eval_set)})")
    print("Paste this number into README.md and this run's output into EVIDENCE.md.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    try:
        run_eval(args.base_url)
    except httpx.ConnectError:
        print(f"Could not reach {args.base_url} -- is the server running?", file=sys.stderr)
        sys.exit(1)
