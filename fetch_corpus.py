#!/usr/bin/env python3
"""
Fetch ~50 corpus images from Pexels, split across categories.

Usage (cmd.exe):
    set PEXELS_API_KEY=your_key_here
    python fetch_corpus.py

Usage (PowerShell):
    $env:PEXELS_API_KEY="your_key_here"
    python fetch_corpus.py

Naming: img_<category>_<n>.jpg -- makes it easy to eyeball wrong tags later,
and to build your labeled eval set (Phase 4) without guessing what's in each file.
"""

import os
import sys
import time
import urllib.parse
import urllib.request
import json

API_KEY = os.environ.get("PEXELS_API_KEY")
if not API_KEY:
    print("ERROR: Set PEXELS_API_KEY first.")
    print('  cmd.exe:     set PEXELS_API_KEY=your_key_here')
    print('  PowerShell:  $env:PEXELS_API_KEY="your_key_here"')
    sys.exit(1)

OUT_DIR = os.path.join(".", "data", "images")
os.makedirs(OUT_DIR, exist_ok=True)

# category -> how many images to pull. 5 categories x 10 = 50.
CATEGORIES = {
    "red fox": 10,
    "gray wolf": 10,
    "dog": 10,
    "bear": 10,
    "deer": 10,
}


HEADERS = {
    "Authorization": API_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code} from Pexels: {body}")
        raise


def download(url: str, path: str) -> None:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp, open(path, "wb") as f:
        f.write(resp.read())


def main():
    total = 0
    for query, count in CATEGORIES.items():
        slug = query.replace(" ", "_")
        print(f"== Fetching {count} images for '{query}' ==")

        search_url = (
            "https://api.pexels.com/v1/search?"
            f"query={urllib.parse.quote(query)}&per_page={count}"
        )
        data = fetch_json(search_url)
        photos = data.get("photos", [])

        if not photos:
            print(f"  WARNING: no results for '{query}' -- check API key / quota.")
            continue

        for i, photo in enumerate(photos, start=1):
            url = photo["src"]["medium"]
            outfile = os.path.join(OUT_DIR, f"img_{slug}_{i}.jpg")
            print(f"  -> {outfile}")
            download(url, outfile)
            total += 1
            time.sleep(0.3)  # be polite to the free-tier rate limit

    print(f"\nDone. Total images downloaded this run: {total}")
    all_files = [f for f in os.listdir(OUT_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    print(f"Total images in {OUT_DIR}: {len(all_files)}")


if __name__ == "__main__":
    main()