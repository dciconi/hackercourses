"""Stream every shard of nixiesearch/hackernews-comments and keep course-related comments.

The raw dataset is ~6.3 GB of zstd JSONL. Shards are decompressed in memory and
discarded; only a broad candidate set is written to data/candidates.jsonl so the
classification rules in classify.py can be tuned without re-downloading.
"""

import io
import json
import re
import sys
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import zstandard

REPO = "nixiesearch/hackernews-comments"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main/items"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main/"

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "candidates.jsonl"
DONE = ROOT / "data" / "shards_done.txt"

# Deliberately wide: anything that might be a course mention.
PREFILTER = re.compile(
    r"course|mooc|coursera|edx\b|udacity|udemy|khan ?academy|\bocw\b|opencourseware|"
    r"nand2tetris|fast\.ai|pluralsight|egghead|frontend ?masters|lecture",
    re.I,
)


def list_shards():
    with urllib.request.urlopen(API) as r:
        return sorted(f["path"] for f in json.load(r) if f["path"].endswith(".jsonl.zst"))


def process(path):
    req = urllib.request.Request(RAW + path, headers={"User-Agent": "hacker-courses/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r:
        blob = r.read()
    reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob))
    kept, total = [], 0
    for line in io.TextIOWrapper(reader, encoding="utf-8"):
        total += 1
        try:
            it = json.loads(line)
        except json.JSONDecodeError:
            continue
        if it.get("type") != "comment" or it.get("deleted") or it.get("dead"):
            continue
        text = it.get("text") or ""
        if not PREFILTER.search(text):
            continue
        kept.append({k: it.get(k) for k in ("id", "by", "time", "text", "parent")})
    return path, total, kept


def main():
    OUT.parent.mkdir(exist_ok=True)
    done = set(DONE.read_text().split()) if DONE.exists() else set()
    shards = [s for s in list_shards() if s not in done]
    print(f"{len(shards)} shards to fetch ({len(done)} already done)", flush=True)
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    with ProcessPoolExecutor(workers) as pool, OUT.open("a", encoding="utf-8") as out, DONE.open("a") as log:
        futures = [pool.submit(process, s) for s in shards]
        for n, fut in enumerate(as_completed(futures), 1):
            try:
                path, total, kept = fut.result()
            except Exception as e:  # retry on the next run
                print(f"FAILED: {e}", flush=True)
                continue
            for row in kept:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            log.write(path + "\n")
            log.flush()
            print(f"[{n}/{len(shards)}] {path}: {total} items, {len(kept)} kept", flush=True)


if __name__ == "__main__":
    main()
