"""Turn per-subreddit Reddit dump files into candidate comments and a thread-title map.

Reads <raw>/<sub>_comments.zst and <raw>/<sub>_submissions.zst (zstd NDJSON, one file pair per
subreddit in sources.SUBREDDITS), keeps course-related comments via reddit.candidate, and writes
data/reddit/candidates.jsonl plus data/reddit/threads.json ({comment_id: [thread_id, title]}, the
same shape as HN's). Ids already in candidates.jsonl are skipped, so a rerun only adds new rows.

    uv run python pipeline/fetch_reddit.py --raw data/reddit/raw [--since 2023-01-01] [--until 2026-01-01]
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import zstandard

from reddit import candidate
from sources import SUBREDDITS, paths


def read_dump(path: Path) -> Iterator[dict]:
    """Stream a zst NDJSON dump, skipping malformed lines."""
    dctx = zstandard.ZstdDecompressor(max_window_size=2**31)
    with path.open("rb") as f, dctx.stream_reader(f) as reader:
        tail = b""
        while chunk := reader.read(2**24):
            lines = (tail + chunk).split(b"\n")
            tail = lines.pop()
            for line in lines:
                if (row := _parse(line)) is not None:
                    yield row
        if (row := _parse(tail)) is not None:
            yield row


def _parse(line: bytes) -> dict | None:
    try:
        row = json.loads(line)
    except ValueError:  # includes bad UTF-8
        return None
    return row if isinstance(row, dict) else None


def _epoch(day: str | None) -> float | None:
    if not day:
        return None
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def existing_rows(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, filter(str.strip, f))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/reddit/raw"))
    ap.add_argument("--since", help="keep comments created on/after this date (YYYY-MM-DD)")
    ap.add_argument("--until", help="keep comments created before this date (YYYY-MM-DD)")
    args = ap.parse_args()
    since, until = _epoch(args.since), _epoch(args.until)

    p = paths("reddit")
    p.candidates.parent.mkdir(parents=True, exist_ok=True)
    rows = existing_rows(p.candidates)
    seen = set(rows)
    threads = json.loads(p.threads.read_text(encoding="utf-8")) if p.threads.exists() else {}

    with p.candidates.open("a", encoding="utf-8") as out:
        for sub in SUBREDDITS:
            comments, subs = args.raw / f"{sub}_comments.zst", args.raw / f"{sub}_submissions.zst"
            if not comments.exists():
                print(f"{sub}: no comments file, skipped", flush=True)
                continue
            total, kept = 0, 0
            # Every candidate of this subreddit (old or new) still lacking a thread title is backfilled.
            thread_of = {cid: r["thread"] for cid, r in rows.items()
                         if r.get("sub", "").lower() == sub.lower() and not (threads.get(cid) or ["", ""])[1]}
            for raw in read_dump(comments):
                total += 1
                t = raw.get("created_utc")
                try:
                    t = int(t)
                except (TypeError, ValueError):
                    continue
                if (since is not None and t < since) or (until is not None and t >= until):
                    continue
                c = candidate(raw)
                if c is None or c["id"] in seen:
                    continue
                seen.add(c["id"])
                out.write(json.dumps(c, ensure_ascii=False) + "\n")
                thread_of[c["id"]] = c["thread"]
                rows[c["id"]] = c
                kept += 1
            out.flush()
            titles = {}
            wanted = set(thread_of.values())
            if wanted and not subs.exists():
                print(f"WARNING {sub}: no submissions file, thread titles left empty until it is added", flush=True)
            if wanted and subs.exists():
                for post in read_dump(subs):
                    if f"t3_{post.get('id')}" in wanted:
                        titles[f"t3_{post['id']}"] = post.get("title") or ""
            for cid, tid in thread_of.items():
                threads[cid] = [tid, titles.get(tid, "")]
            p.threads.write_text(json.dumps(threads, ensure_ascii=False), encoding="utf-8")
            print(f"{sub}: kept {kept}/{total}", flush=True)


if __name__ == "__main__":
    main()
