"""Find a preview image for each course -> data/images.json

For each course, try its best link (from summarize.py), then the course links in its comments:
- YouTube video links: the video thumbnail;
- any other page: the og:image / twitter:image the page publishes for link previews.
Every candidate image is downloaded once to check it is real: 300x150 or larger and landscape
(square logos look wrong on a 16:9 card). Images shared by 3+ courses are site-wide defaults, not
course art, and are dropped. Courses without an image get their topic placeholder on the site.

The site hotlinks these URLs; nothing is re-hosted.
"""

import io
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image

from classify import ROOT
from summarize import SUMMARIES, course_comments

OUT = ROOT / "data" / "images.json"
UA = "Mozilla/5.0 (compatible; HackerCoursesBot/0.1; +https://hackercourses.com)"
WORKERS = 12
META = re.compile(
    r'<meta\s+[^>]*?(?:property|name)\s*=\s*["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]*>', re.I)
CONTENT = re.compile(r'content\s*=\s*["\']([^"\']+)["\']', re.I)


def fetch(url, limit):
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=15) as r:
        return r.geturl(), r.headers.get("Content-Type", ""), r.read(limit)


def youtube_thumb(url):
    u = urlparse(url)
    vid = None
    if u.netloc.endswith("youtu.be"):
        vid = u.path.strip("/").split("/")[0]
    elif "youtube.com" in u.netloc:
        vid = parse_qs(u.query).get("v", [None])[0] or (u.path.split("/embed/")[1].split("/")[0] if "/embed/" in u.path else None)
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None


def page_image(url):
    final, ctype, body = fetch(url, 600_000)
    if "html" not in ctype:
        return None
    html = body.decode("utf-8", "replace")
    for tag in META.findall(html):
        m = CONTENT.search(tag)
        if m:
            return urljoin(final, unescape(m.group(1).strip()))
    return None


def check(img_url):
    """Return (width, height) if the URL is a real landscape image of usable size."""
    _, ctype, body = fetch(img_url, 5_000_000)
    if not ctype.startswith("image/") or "svg" in ctype:
        return None
    with Image.open(io.BytesIO(body)) as im:
        w, h = im.size
    if w < 300 or h < 150 or w / h < 1.2 or w / h > 2.6:
        return None
    return w, h


def find(course_id, urls):
    for url in urls:
        try:
            cand = youtube_thumb(url) or page_image(url)
            if not cand or not cand.startswith("http"):
                continue
            size = check(cand)
            if size:
                return course_id, {"src": cand, "page": url, "w": size[0], "h": size[1]}
        except Exception:  # dead links, timeouts, bad images: try the next candidate
            continue
    return course_id, None


def main():
    _, by_course = course_comments()
    summaries = {}
    if SUMMARIES.exists():
        for line in SUMMARIES.open(encoding="utf-8"):
            s = json.loads(line)
            summaries[s["id"]] = s
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    jobs = []
    for cid, items in by_course.items():
        if str(cid) in done:
            continue
        # A comment's links only count when it names this course alone; otherwise a link may
        # belong to another course mentioned alongside it.
        urls = [summaries.get(cid, {}).get("url")] + [u for it in items if len(it.get("courses", [])) == 1
                                                      for u in it["links"]]
        urls = [u for u in dict.fromkeys(urls) if u and u.startswith("http")][:4]
        if urls:
            jobs.append((cid, urls))
    if len(sys.argv) > 1:
        jobs = jobs[: int(sys.argv[1])]
    print(f"{len(jobs)} courses to look up ({len(done)} done)", flush=True)
    with ThreadPoolExecutor(WORKERS) as ex:
        futures = [ex.submit(find, cid, urls) for cid, urls in jobs]
        for n, fut in enumerate(as_completed(futures), 1):
            cid, found = fut.result()
            done[str(cid)] = found
            if n % 100 == 0:
                OUT.write_text(json.dumps(done, indent=0), encoding="utf-8")
                print(f"{n}/{len(jobs)}  found {sum(1 for v in done.values() if v)}", flush=True)

    # The same picture on several courses is a site-wide default, not course art.
    shared = Counter(v["src"] for v in done.values() if v)
    for k, v in done.items():
        if v and shared[v["src"]] >= 3:
            done[k] = None
    OUT.write_text(json.dumps(done, indent=0), encoding="utf-8")
    found = sum(1 for v in done.values() if v)
    print(f"done: {found} of {len(done)} courses have an image "
          f"({sum(1 for n in shared.values() if n >= 3)} shared defaults dropped)", flush=True)


if __name__ == "__main__":
    main()
