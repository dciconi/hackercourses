"""Second image pass for courses images.py left without a picture.

Two sources, tried in order for each course (most-mentioned first):
1. Current course page. Haiku suggests likely official URLs; a suggestion is used only if the page
   loads and its title matches the course (shared significant words or the same course code), so a
   wrong or invented URL can't attach someone else's image.
2. Archived page. For the links commenters actually posted, the Internet Archive's closest snapshot
   and the preview image that page had then.
Images go through the same checks as images.py and land in data/images.json.

    uv run python pipeline/discover_images.py [limit]
"""

import json
import math
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from canonicalize import codes
from classify import ROOT
from images import OUT, fetch, first_good, page
from llm import HAIKU, api_key, structured
from summarize import SUMMARIES, course_comments

TRIED = ROOT / "data" / "images_discover.json"
BATCH = 25
WORKERS = 10
STOP = {"introduction", "intro", "course", "courses", "with", "from", "into", "your", "part", "series",
        "lectures", "lecture", "online", "free", "class", "university", "learning", "the", "and", "for"}

SYSTEM = """For each course, give up to 2 URLs most likely to be its current official landing page
(the course's own page on its provider: Coursera, edX, MIT OpenCourseWare, a university course site,
a YouTube playlist, etc.). Prefer stable canonical pages over search results or blog posts. If you are
not reasonably sure such a page exists, return an empty list. Never guess at random."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "urls"],
        "properties": {"id": {"type": "integer"}, "urls": {"type": "array", "items": {"type": "string"}, "maxItems": 2}},
    }}},
}
def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 4 and w not in STOP}


def title_matches(course, page_title):
    """Does the page look like this course? Same course code, or most of the name's key words."""
    name = re.sub(r"\(.*?\)", " ", course["name"])  # instructor asides rarely appear in titles
    if codes(course["name"]) & codes(page_title):
        return True
    want = words(name)
    return bool(want) and len(want & words(page_title)) >= math.ceil(0.75 * len(want))


def from_current(course, urls):
    for url in urls:
        try:
            final, title, cands = page(url)
        except Exception:
            continue
        if not title_matches(course, title):
            continue
        img, size = first_good(cands)
        if img:
            return {"src": img, "page": final, "w": size[0], "h": size[1], "via": "current"}
    return None


def from_archive(urls):
    for url in urls:
        try:
            _, _, body = fetch(f"https://archive.org/wayback/available?url={quote(url, safe='')}", 100_000)
            snap = json.loads(body).get("archived_snapshots", {}).get("closest", {})
            if not snap.get("available"):
                continue
            _, _, cands = page(snap["url"])
        except Exception:
            continue
        img, size = first_good(cands)
        if img:
            return {"src": img, "page": url, "w": size[0], "h": size[1], "via": "archive"}
    return None


def main():
    key = api_key()
    cat, by_course = course_comments()
    summaries = {}
    if SUMMARIES.exists():
        for line in SUMMARIES.open(encoding="utf-8"):
            s = json.loads(line)
            summaries[s["id"]] = s
    images = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    tried = json.loads(TRIED.read_text(encoding="utf-8")) if TRIED.exists() else {}
    todo = [cid for cid in sorted(by_course, key=lambda c: -len(by_course[c]))
            if not images.get(str(cid)) and str(cid) not in tried]
    if len(sys.argv) > 1:
        todo = todo[: int(sys.argv[1])]
    print(f"{len(todo)} courses without an image to try", flush=True)

    # 1. ask for likely current URLs, in batches
    suggested, cost = {}, 0.0
    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        listing = "\n".join(f"{cid} | {cat['courses'][cid]['name']} | {cat['courses'][cid]['provider']}" for cid in batch)
        out, c = structured(key, HAIKU, SYSTEM, f"<courses>\n{listing}\n</courses>", SCHEMA, max_tokens=4096)
        cost += c
        for item in out["items"]:
            if item["id"] in batch:
                suggested[item["id"]] = [u for u in item["urls"] if u.startswith("http")]
    print(f"URL suggestions: ${cost:.3f}", flush=True)

    def work(cid):
        course = cat["courses"][cid]
        found = from_current(course, suggested.get(cid, []))
        if not found:
            posted = [summaries.get(cid, {}).get("url")] + [u for it in by_course[cid]
                                                            if len(it.get("courses", [])) == 1 for u in it["links"]]
            found = from_archive([u for u in dict.fromkeys(posted) if u and u.startswith("http")][:3])
        return cid, found

    hits = 0
    with ThreadPoolExecutor(WORKERS) as ex:
        futures = [ex.submit(work, cid) for cid in todo]
        for n, fut in enumerate(as_completed(futures), 1):
            cid, found = fut.result()
            tried[str(cid)] = found["via"] if found else None
            if found:
                images[str(cid)] = found
                hits += 1
            if n % 50 == 0:
                OUT.write_text(json.dumps(images, indent=0), encoding="utf-8")
                TRIED.write_text(json.dumps(tried), encoding="utf-8")
                print(f"{n}/{len(todo)}  +{hits}", flush=True)

    # Re-apply the shared-default filter across both passes.
    shared = Counter(v["src"] for v in images.values() if v)
    dropped = 0
    for k, v in images.items():
        if v and shared[v["src"]] >= 3:
            images[k] = None
            dropped += 1
    OUT.write_text(json.dumps(images, indent=0), encoding="utf-8")
    TRIED.write_text(json.dumps(tried), encoding="utf-8")
    vias = Counter(v for v in tried.values() if v)
    print(f"done: +{hits} images ({dict(vias)}), {dropped} shared defaults dropped, "
          f"{sum(1 for v in images.values() if v)} courses now have one", flush=True)


if __name__ == "__main__":
    main()
