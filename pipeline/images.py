"""Find a preview image for each course -> data/images.json

For each course, try its best link (from summarize.py), then the course links in its comments:
- YouTube links: the video or playlist thumbnail (via YouTube's public oEmbed endpoint);
- any other page: the og:image / twitter:image it publishes for link previews, else the first
  large image on the page (skipping logos, icons, avatars, sprites).
Every candidate image is downloaded once to check it is real and at least 300px wide. Landscape
images need 300x150; portrait or square ones are allowed (MIT OCW uses them) and are cropped from
the top on the site. Images shared by 3+ courses are site-wide defaults, not course art, and are
dropped. Courses without an image get their topic placeholder on the site.

The site hotlinks these URLs; nothing is re-hosted.
"""

import io
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import quote, urljoin, urlparse
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
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OG_TITLE = re.compile(r'<meta\s+[^>]*?property\s*=\s*["\']og:title["\'][^>]*>', re.I)
IMG = re.compile(r'<img\s[^>]*?src\s*=\s*["\']([^"\']+)["\']', re.I)
NOT_ART = re.compile(r"logo|icon|sprite|avatar|badge|pixel|spacer|button|favicon|seal|\.svg|^data:", re.I)
# Plain <img>s on course sites are often staff photos; never use anything that looks like one.
PEOPLE = re.compile(r"people|staff|team|faculty|instructor|headshot|portrait|profile|person|bio|/ta/|students?", re.I)


def fetch(url, limit):
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=15) as r:
        return r.geturl(), r.headers.get("Content-Type", ""), r.read(limit)


def is_youtube(url):
    host = urlparse(url).netloc
    return host.endswith("youtube.com") or host.endswith("youtu.be")


def youtube(url):
    """(title, thumbnail) for a YouTube video or playlist via oEmbed, or (None, None)."""
    _, _, body = fetch(f"https://www.youtube.com/oembed?url={quote(url, safe='')}&format=json", 100_000)
    data = json.loads(body)
    return data.get("title"), data.get("thumbnail_url")


def page(url):
    """(final_url, title, [(image url, kind)]): declared preview images ("preview") first,
    then plain <img>s on the page ("img"), which must pass a stricter shape check."""
    if is_youtube(url):
        title, thumb = youtube(url)
        return url, title or "", [(thumb, "preview")] if thumb else []
    final, ctype, body = fetch(url, 600_000)
    if "html" not in ctype:
        return final, "", []
    html = body.decode("utf-8", "replace")
    title = " ".join(unescape(m) for m in TITLE.findall(html)[:1])
    for tag in OG_TITLE.findall(html):
        m = CONTENT.search(tag)
        if m:
            title += " " + unescape(m.group(1))
    cands = []
    for tag in META.findall(html):
        m = CONTENT.search(tag)
        if m:
            cands.append((urljoin(final, unescape(m.group(1).strip())), "preview"))
    cands += [(urljoin(final, unescape(src)), "img") for src in IMG.findall(html)
              if not NOT_ART.search(src) and not PEOPLE.search(src)][:6]
    seen, out = set(), []
    for u, kind in cands:
        if u.startswith("http") and u not in seen:
            seen.add(u)
            out.append((u, kind))
    return final, title, out


def check(img_url, kind="preview"):
    """Return (width, height) if the URL is a real image of usable size and shape.

    Declared preview images may be portrait (MIT OCW uses them). Plain page images must be
    clearly landscape, which also keeps out headshots.
    """
    _, ctype, body = fetch(img_url, 5_000_000)
    if not ctype.startswith("image/") or "svg" in ctype:
        return None
    with Image.open(io.BytesIO(body)) as im:
        w, h = im.size
    if kind == "img":
        ok = w >= 400 and 1.3 <= w / h <= 2.6
    else:
        ok = w >= 300 and h >= 150 and 0.6 <= w / h <= 2.6
    return (w, h) if ok else None


def first_good(cands):
    for img, kind in cands[:5]:
        try:
            size = check(img, kind)
        except Exception:
            continue
        if size:
            return img, size
    return None, None


def find(course_id, urls):
    for url in urls:
        try:
            final, _, cands = page(url)
        except Exception:  # dead links, timeouts, blocked: try the next candidate
            continue
        img, size = first_good(cands)
        if img:
            return course_id, {"src": img, "page": final, "w": size[0], "h": size[1]}
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
