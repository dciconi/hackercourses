"""Find the thread (root story) each pool comment was posted in.

One more streaming pass over the dataset: records every comment's parent in a compact
array plus every story title, then walks each pool comment up to its root.
Writes data/threads.json: {comment_id: [story_id, title]}.
"""

import io
import json
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import zstandard

from classify import POOL, ROOT
from fetch import RAW, list_shards

OUT = ROOT / "data" / "threads.json"
MAX_ID = 42_500_000  # last shard ends at 41,773,265; leave headroom


def scan(path):
    req = urllib.request.Request(RAW + path, headers={"User-Agent": "hacker-courses/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r:
        blob = r.read()
    reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob))
    ids, parents, titles = [], [], {}
    for line in io.TextIOWrapper(reader, encoding="utf-8"):
        try:
            it = json.loads(line)
        except json.JSONDecodeError:
            continue
        if it.get("type") == "comment" and it.get("parent"):
            ids.append(it["id"])
            parents.append(it["parent"])
        elif it.get("title"):
            titles[it["id"]] = it["title"]
    return np.array(ids, np.int32), np.array(parents, np.int32), titles


def main():
    parent = np.zeros(MAX_ID, np.int32)
    titles = {}
    shards = list_shards()
    with ProcessPoolExecutor(8) as pool:
        futures = [pool.submit(scan, s) for s in shards]
        for n, fut in enumerate(as_completed(futures), 1):
            ids, ps, ts = fut.result()
            parent[ids] = ps
            titles.update(ts)
            if n % 25 == 0:
                print(f"[{n}/{len(shards)}] {len(titles)} titles", flush=True)

    out = {}
    for it in json.loads(POOL.read_text(encoding="utf-8")):
        node, hops = it["id"], 0
        while parent[node] and hops < 500:
            node, hops = int(parent[node]), hops + 1
        out[it["id"]] = [node, titles.get(node)]
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    missing = sum(1 for v in out.values() if not v[1])
    print(f"wrote {len(out)} threads, {missing} without a title", flush=True)


if __name__ == "__main__":
    main()
