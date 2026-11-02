"""Assemble the site data: canonical courses, their comments, ranking, badges and related courses.

    uv run python pipeline/build.py
"""

import json
import time
from collections import Counter, defaultdict

import rank
from classify import OTHER, OUT_JS, ROOT, TOPICS
from images import OUT as IMAGES
from summarize import SUMMARIES, THREADS, course_comments

STANCE_CODE = {"strongly_recommends": 3, "recommends": 2, "mentions": 1, "criticizes": 0}


def main():
    cat, by_course = course_comments()
    threads = json.loads(THREADS.read_text(encoding="utf-8"))
    summaries = {}
    if SUMMARIES.exists():
        for line in SUMMARIES.open(encoding="utf-8"):
            s = json.loads(line)
            summaries[s["id"]] = s
    now = max(it["time"] for cs in by_course.values() for it in cs)
    images = json.loads(IMAGES.read_text(encoding="utf-8")) if IMAGES.exists() else {}

    comment_index, comments = {}, []

    def cidx(it):
        if it["id"] not in comment_index:
            tid, title = threads.get(str(it["id"])) or [it["id"], None]
            comment_index[it["id"]] = len(comments)
            comments.append({"id": it["id"], "by": it["by"], "t": it["time"], "text": it["text"],
                             "thread": title, "tid": tid})
        return comment_index[it["id"]]

    courses = []
    for cid, items in by_course.items():
        s = summaries.get(cid, {})
        stances = s.get("stances", {})
        # Comments past the summarizer's cap passed the recommendation filter, so default to "recommends".
        ends = [{"author": it["by"], "thread": (threads.get(str(it["id"])) or [it["id"]])[0], "time": it["time"],
                 "stance": stances.get(str(it["id"]), "recommends"), "item": it} for it in items]
        positive = [e for e in ends if rank.STANCE_WEIGHT[e["stance"]] >= 0.7]
        if not positive:
            continue  # only mentioned or criticized: not a recommended course
        votes = rank.author_votes(ends)
        recommenders = sum(1 for v in votes if v["w"] >= 0.7)
        c = cat["courses"][cid]
        times = [e["time"] for e in positive]
        course = {
            "id": cid, "name": c["name"], "provider": c["provider"], "url": s.get("url"),
            "topic": s.get("topic") or Counter(it["topic"] for it in items).most_common(1)[0][0],
            "summary": s.get("summary", ""), "why": s.get("why", ""),
            "level": s.get("level", "unknown"), "cost": s.get("cost", "unknown"),
            "format": s.get("format", "unknown"), "tags": s.get("tags", []),
            # Preview image from the course's own page; the site falls back to a topic illustration.
            "img": (images.get(str(cid)) or {}).get("src"), "imgPage": (images.get(str(cid)) or {}).get("page"),
            "score": round(rank.score(ends), 3), "trend": round(rank.trending(ends, now), 3),
            "recommenders": recommenders, "threads": len({e["thread"] for e in positive}),
            "mentions": len(ends), "first": min(times), "last": max(times),
            "years_active": len({time.gmtime(t).tm_year for t in times}),
            "strong_share": sum(v["w"] == 1.0 for v in votes) / max(1, len(votes)),
            "recent_share": rank.recent_share(ends, now),
            "endorsements": sorted(([cidx(e["item"]), STANCE_CODE[e["stance"]]] for e in ends),
                                   key=lambda x: (-x[1], -comments[x[0]]["t"])),
        }
        courses.append(course)

    courses.sort(key=lambda c: (-c["score"], -c["recommenders"], -c["last"]))
    for i, c in enumerate(courses):
        c["rank"] = i + 1
        c["badges"] = rank.badges(c, i, len(courses), now)

    # Related: courses recommended in the same comments first, then the best of the same topic.
    by_comment = defaultdict(set)
    for c in courses:
        for ci, _ in c["endorsements"]:
            by_comment[ci].add(c["id"])
    pos = {c["id"]: i for i, c in enumerate(courses)}
    best_by_topic = defaultdict(list)
    for c in courses:
        best_by_topic[c["topic"]].append(c["id"])
    for c in courses:
        co = Counter(o for ci, _ in c["endorsements"] for o in by_comment[ci] if o != c["id"])
        related = [o for o, _ in sorted(co.items(), key=lambda kv: (-kv[1], pos[kv[0]]))][:6]
        for o in best_by_topic[c["topic"]]:
            if len(related) >= 8:
                break
            if o != c["id"] and o not in related:
                related.append(o)
        c["related"] = related
        for k in ("strong_share", "recent_share"):
            c[k] = round(c[k], 2)

    order = [name for name, _ in TOPICS] + [OTHER]
    counts = Counter(c["topic"] for c in courses)
    payload = {
        "generated": int(time.time()), "dataEnd": now,
        "topics": [{"name": n, "count": counts[n]} for n in order if counts[n]],
        "courses": courses, "comments": comments,
    }
    OUT_JS.parent.mkdir(exist_ok=True)
    OUT_JS.write_text("window.HACKER_COURSES = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                      encoding="utf-8")
    print(f"{len(courses)} courses, {len(comments)} comments, {OUT_JS.stat().st_size / 1e6:.1f} MB")
    for c in courses[:15]:
        print(f"{c['rank']:>3} {c['score']:6.2f} {c['recommenders']:>3}r {c['threads']:>3}t "
              f"{time.gmtime(c['first']).tm_year}-{time.gmtime(c['last']).tm_year} {c['badges']} {c['name']} | {c['provider']}")


if __name__ == "__main__":
    main()
