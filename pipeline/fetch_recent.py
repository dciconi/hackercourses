"""Add comments newer than the nixiesearch dump (which ends at item 41,773,265, early Oct 2024).

1. open-index/hacker-news monthly Parquet files (ODC-By), from 2024-10 up to its last month.
   DuckDB reads only the columns needed and applies the same prefilter as fetch.py.
2. The Algolia HN search API for anything after the newest item in those files, searching
   the prefilter's terms (Algolia matches words, so results are re-checked with the regex).
Appends to data/candidates.jsonl in fetch.py's format; ids already present are skipped.
Algolia also returns each comment's thread, saved to data/threads_recent.json.

    uv run python pipeline/fetch_recent.py
"""

import json
import time
import urllib.parse
import urllib.request

import duckdb

from fetch import OUT, PREFILTER

DATASET = "https://huggingface.co/datasets/open-index/hacker-news"
OLD_MAX_ID = 41_773_265
THREADS_RECENT = OUT.parent / "threads_recent.json"
ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"
TERMS = ["course", "courses", "mooc", "coursera", "edx", "udacity", "udemy", "khan academy", "ocw",
         "opencourseware", "nand2tetris", "fast.ai", "pluralsight", "egghead", "frontend masters", "lecture",
         "lectures"]
UA = {"User-Agent": "HackerCoursesBot/0.1 (+https://hackercourses.com)"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def months():
    """Monthly files from 2024-10 on, oldest first."""
    out = []
    for y in range(2024, time.gmtime().tm_year + 1):
        tree = get_json(f"https://huggingface.co/api/datasets/open-index/hacker-news/tree/main/data/{y}")
        out += sorted(f["path"] for f in tree if f["path"].endswith(".parquet") and f["path"] >= "data/2024/2024-10")
    return out


def existing_ids():
    ids = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            for line in f:
                ids.add(json.loads(line)["id"])
    return ids


def from_parquet(seen, out):
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET enable_progress_bar = false;")
    # RE2 syntax: same alternatives as fetch.PREFILTER, case-insensitive.
    pattern = PREFILTER.pattern
    newest = 0
    for path in months():
        url = f"{DATASET}/resolve/main/{path}"
        rows = con.execute(
            f"""SELECT id, "by", epoch(time)::BIGINT, text, parent FROM read_parquet('{url}')
                WHERE type = 2 AND id > {OLD_MAX_ID} AND coalesce(dead, 0) = 0 AND coalesce(deleted, 0) = 0
                  AND text IS NOT NULL AND regexp_matches(text, ?, 'i')""", [pattern]).fetchall()
        added = 0
        for cid, by, t, text, parent in rows:
            newest = max(newest, t)
            if cid in seen:
                continue
            seen.add(cid)
            out.write(json.dumps({"id": cid, "by": by, "time": t, "text": text, "parent": parent}, ensure_ascii=False) + "\n")
            added += 1
        out.flush()
        print(f"{path}: {len(rows)} matches, {added} new", flush=True)
    return newest


def from_algolia(since, seen, out):
    threads = json.loads(THREADS_RECENT.read_text(encoding="utf-8")) if THREADS_RECENT.exists() else {}
    added = 0
    for term in TERMS:
        upper = int(time.time())
        while True:
            # Walk backwards in time; each request returns the newest 1000 hits below `upper`.
            params = urllib.parse.urlencode({"query": term, "tags": "comment", "hitsPerPage": 1000,
                                             "numericFilters": f"created_at_i>{since},created_at_i<{upper}"})
            hits = get_json(f"{ALGOLIA}?{params}")["hits"]
            for h in hits:
                cid, text = int(h["objectID"]), h.get("comment_text") or ""
                if cid in seen or not h.get("author") or not PREFILTER.search(text):
                    continue
                seen.add(cid)
                out.write(json.dumps({"id": cid, "by": h["author"], "time": h["created_at_i"], "text": text,
                                      "parent": h.get("parent_id")}, ensure_ascii=False) + "\n")
                if h.get("story_id"):
                    threads[str(cid)] = [h["story_id"], h.get("story_title")]
                added += 1
            if len(hits) < 1000:
                break
            upper = min(h["created_at_i"] for h in hits)
            time.sleep(0.5)
        out.flush()
        time.sleep(0.5)
    THREADS_RECENT.write_text(json.dumps(threads, ensure_ascii=False), encoding="utf-8")
    print(f"algolia since {time.strftime('%Y-%m-%d %H:%M', time.gmtime(since))} UTC: {added} new", flush=True)


def main():
    seen = existing_ids()
    print(f"{len(seen)} candidates already on disk", flush=True)
    with OUT.open("a", encoding="utf-8") as out:
        newest = from_parquet(seen, out)
        from_algolia(newest, seen, out)


if __name__ == "__main__":
    main()
