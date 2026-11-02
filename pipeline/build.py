"""Assemble the site data: canonical courses, their comments, ranking, badges and related courses.

Hacker News and Reddit are ranked separately: each course carries one stats block per source it
was recommended in (`sources: {"hn": ..., "reddit": ...}`), and each source gets its own grid
(site/courses.js, site/reddit/courses.js). Ranks and scores are never mixed across sources.

    uv run python pipeline/build.py
"""

import json
import time
from collections import Counter, defaultdict

import pages
import rank
import reddit
import removals
import sources
import summarize
from classify import OTHER, ROOT, TOPICS
from images import OUT as IMAGES

STANCE_CODE = {"strongly_recommends": 3, "recommends": 2, "mentions": 1, "criticizes": 0}
SITE = ROOT / "site"
COURSES_JS = SITE / "courses.js"
REDDIT_COURSES_JS = SITE / "reddit" / "courses.js"
OLD_DATA_JS = SITE / "data.js"  # pre-static-pages bundle with every comment
GRID_FIELDS = ("id", "slug", "name", "provider", "topic", "summary", "why", "level", "cost", "format", "tags",
               "score", "trend", "recommenders", "threads", "first", "last", "years_active", "rank", "badges",
               "img", "imgTall")
REDDIT_MIN_RECOMMENDERS = 2  # a Reddit course needs two people behind it to be listed and get a page
REDDIT_EXCERPT = 300  # Reddit comments are shown as excerpts, never in full
MAX_FILES = 19_000  # Cloudflare Pages free tier allows about 20,000 files per deploy


def source_stats(ends, now, source):
    """One source's ranking stats for a course, or None when it is not a recommended course there.

    ends: [{author, thread, time, stance, item, factor?}]. "endorsements" is [[item, stance code]],
    strongest stance first, then newest."""
    positive = [e for e in ends if rank.STANCE_WEIGHT[e["stance"]] >= 0.7]
    if not positive:
        return None  # only mentioned or criticized: not a recommended course
    votes = rank.author_votes(ends)
    # Recommenders are people whose stance recommends it; upvotes scale the score, not this count.
    recommenders = sum(1 for v in votes if v["sw"] >= 0.7)
    if source == "reddit" and recommenders < REDDIT_MIN_RECOMMENDERS:
        return None
    times = [e["time"] for e in positive]
    return {
        "score": round(rank.score(ends), 3), "trend": round(rank.trending(ends, now), 3),
        "recommenders": recommenders, "threads": len({e["thread"] for e in positive}),
        "first": min(times), "last": max(times),
        "years_active": len({time.gmtime(t).tm_year for t in times}),
        "strong_share": sum(v["sw"] == 1.0 for v in votes) / max(1, len(votes)),
        "recent_share": rank.recent_share(ends, now),
        "endorsements": sorted(([e["item"], STANCE_CODE[e["stance"]]] for e in ends),
                               key=lambda x: (-x[1], -x[0]["time"])),
    }


def comment_entry(it, threads):
    """What a course page shows for one comment. Reddit text is clipped to an excerpt."""
    tid, title = threads.get(str(it["id"])) or [it.get("thread") or it["id"], None]
    if it.get("src") != "reddit":
        return {"id": it["id"], "by": it["by"], "t": it["time"], "text": it["text"], "thread": title, "tid": tid}
    return {"id": it["id"], "by": it["by"], "t": it["time"], "text": pages.clip(it["text"], REDDIT_EXCERPT),
            "thread": title, "tid": tid, "src": "reddit", "sub": it["sub"], "ups": it["ups"],
            "url": reddit.permalink(it)}


def check_file_count(root, limit=MAX_FILES):
    n = sum(1 for p in root.rglob("*") if p.is_file())
    if n > limit:
        raise SystemExit(f"{root} holds {n:,} files, over the {limit:,} limit (Cloudflare Pages allows ~20,000)")
    return n


def assemble(cat, by_course, summaries, threads, images):
    """-> (courses, comments, newest comment time per source).

    summaries/threads: {source: {...}}. Courses come in HN rank order, then Reddit-only courses in
    Reddit rank order."""
    srcs = [s for s in sources.SOURCES if any(it["src"] == s for items in by_course.values() for it in items)]
    ends_at = {s: max(it["time"] for items in by_course.values() for it in items if it["src"] == s) for s in srcs}

    comment_index, comments = {}, []

    def cidx(it):
        if it["id"] not in comment_index:
            comment_index[it["id"]] = len(comments)
            comments.append(comment_entry(it, threads.get(it["src"], {})))
        return comment_index[it["id"]]

    courses = []
    for cid, items in by_course.items():
        hn_s, rd_s = summaries.get("hn", {}).get(cid), summaries.get("reddit", {}).get(cid)
        s = hn_s or rd_s or {}  # shared fields: the HN summary when there is one
        stances = {**(hn_s or {}).get("stances", {}), **(rd_s or {}).get("stances", {})}
        stats = {}
        for src in srcs:
            th = threads.get(src, {})
            # Comments past the summarizer's cap passed the recommendation filter, so default to "recommends".
            ends = [{"author": it["by"], "thread": (th.get(str(it["id"])) or [it.get("thread") or it["id"]])[0],
                     "time": it["time"], "stance": stances.get(str(it["id"]), "recommends"), "item": it}
                    | ({"factor": rank.upvote_factor(it.get("ups"), it.get("age"))} if src == "reddit" else {})
                    for it in items if it["src"] == src]
            if ends and (st := source_stats(ends, ends_at[src], src)):
                st["endorsements"] = [[cidx(it), code] for it, code in st["endorsements"]]
                stats[src] = st
        if not stats:
            continue
        c = cat["courses"][cid]
        img = images.get(str(cid)) or {}
        courses.append({
            "id": cid, "name": c["name"], "provider": c["provider"], "url": s.get("url"),
            "topic": s.get("topic") or Counter(it["topic"] for it in items).most_common(1)[0][0],
            "summary": s.get("summary", ""), "why": s.get("why", ""),
            "level": s.get("level", "unknown"), "cost": s.get("cost", "unknown"),
            "format": s.get("format", "unknown"), "tags": s.get("tags", []),
            # Preview image from the course's own page; the site falls back to a topic illustration.
            "img": img.get("src"), "imgPage": img.get("page"),
            # Portrait/square images (MIT OCW) are cropped from the top on 16:9 cards.
            "imgTall": bool(img) and img["h"] > 0.8 * img["w"],
            "sources": stats,
        })

    for src in srcs:
        ranked = sorted((c for c in courses if src in c["sources"]),
                        key=lambda c: (-c["sources"][src]["score"], -c["sources"][src]["recommenders"],
                                       -c["sources"][src]["last"]))
        for i, c in enumerate(ranked):
            st = c["sources"][src]
            st["rank"] = i + 1
            st["badges"] = rank.badges(st, i, len(ranked), ends_at[src], src)
            for k in ("strong_share", "recent_share"):  # rounded only after badges read them
                st[k] = round(st[k], 2)
    unranked = len(courses) + 1
    courses.sort(key=lambda c: tuple(c["sources"][s]["rank"] if s in c["sources"] else unranked
                                     for s in sources.SOURCES))

    # Related: courses recommended in the same comments (either source) first, then the best of the same topic.
    def endorsed(c):
        return [ci for st in c["sources"].values() for ci, _ in st["endorsements"]]

    by_comment = defaultdict(set)
    for c in courses:
        for ci in endorsed(c):
            by_comment[ci].add(c["id"])
    pos = {c["id"]: i for i, c in enumerate(courses)}
    best_by_topic = defaultdict(list)
    for c in courses:
        best_by_topic[c["topic"]].append(c["id"])
    for c in courses:
        co = Counter(o for ci in endorsed(c) for o in by_comment[ci] if o != c["id"])
        related = [o for o, _ in sorted(co.items(), key=lambda kv: (-kv[1], pos[kv[0]]))][:6]
        for o in best_by_topic[c["topic"]]:
            if len(related) >= 8:
                break
            if o != c["id"] and o not in related:
                related.append(o)
        c["related"] = related

    taken = set()
    for c in courses:
        c["slug"] = pages.slugify(c["name"], taken)
    return courses, comments, ends_at


def grid_payload(courses, comments, source, data_end):
    """The grid only needs card fields; comments live in each course's own page."""
    views = sorted((pages.view(c, source) for c in courses if source in c["sources"]), key=lambda v: v["rank"])
    mine = [cm for cm in comments if cm.get("src", "hn") == source]
    order = [name for name, _ in TOPICS] + [OTHER]
    counts = Counter(v["topic"] for v in views)
    payload = {"generated": int(time.time()), "dataEnd": data_end, "comments": len(mine)}
    if source != "hn":  # the HN payload keeps its exact shape
        payload = {"source": source, **payload, "dataStart": min(cm["t"] for cm in mine)}
    payload |= {"topics": [{"name": n, "count": counts[n]} for n in order if counts[n]],
                "courses": [{k: v[k] for k in GRID_FIELDS} for v in views]}
    return payload


def write_js(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("window.HACKER_COURSES = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                    encoding="utf-8")


def main():
    cat, by_course = summarize.course_comments(None)
    # Honor removal requests before anything is ranked or published.
    ids, users = removals.load()
    by_course = {cid: kept for cid, items in by_course.items()
                 if (kept := [it for it in items if not removals.removed(it, ids, users)])}
    if ids or users:
        print(f"removals: {len(ids)} comment ids, {len(users)} users")
    threads = {}
    for src in sources.SOURCES:
        f = sources.paths(src).threads
        threads[src] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    summaries = {src: summarize.load(src) for src in sources.SOURCES}
    images = json.loads(IMAGES.read_text(encoding="utf-8")) if IMAGES.exists() else {}

    courses, comments, ends_at = assemble(cat, by_course, summaries, threads, images)

    write_js(COURSES_JS, grid_payload(courses, comments, "hn", ends_at["hn"]))
    if any("reddit" in c["sources"] for c in courses):
        write_js(REDDIT_COURSES_JS, grid_payload(courses, comments, "reddit", ends_at["reddit"]))
    elif REDDIT_COURSES_JS.exists():
        REDDIT_COURSES_JS.unlink()
    pages.write_all(courses, comments, ends_at["hn"])
    if OLD_DATA_JS.exists():
        OLD_DATA_JS.unlink()
    n_files = check_file_count(SITE)
    for src in sources.SOURCES:
        views = sorted((pages.view(c, src) for c in courses if src in c["sources"]), key=lambda v: v["rank"])
        if views:
            print(f"{src}: {len(views)} courses")
        for v in views[:15]:
            print(f"{v['rank']:>3} {v['score']:6.2f} {v['recommenders']:>3}r {v['threads']:>3}t "
                  f"{time.gmtime(v['first']).tm_year}-{time.gmtime(v['last']).tm_year} {v['badges']} "
                  f"{v['name']} | {v['provider']}")
    print(f"{len(courses)} courses, {len(comments)} comments, {n_files:,} site files; "
          f"grid data {COURSES_JS.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
