"""Static pages for hosting on Cloudflare Pages (no build step there; everything is committed).

Writes into site/: index.html (the grid), course/<slug>/index.html for every course, about/,
404.html, sitemap.xml, robots.txt and _headers. Called from build.py.
"""

import json
import re
import time
from html import escape

from classify import ROOT

SITE = ROOT / "site"
BASE = "https://hackercourses.com"
NAME = "Hacker Courses"
TAGLINE = "The online courses programmers keep recommending, ranked from public forum comments since 2006."
SPAN = "2006 onward"  # replaced by configure() with the real end of the data, e.g. "2006 to November 2026"


def configure(data_end):
    global TAGLINE, SPAN
    years = year(data_end) - 2006
    SPAN = f"2006 to {time.strftime('%B %Y', time.gmtime(data_end))}"
    TAGLINE = f"The online courses programmers keep recommending, ranked from {years} years of public forum comments."
REPO = "https://github.com/dciconi/hackercourses"
STANCE = ["Criticizes", "Mentions", "Recommends", "Strongly recommends"]
BADGE = {"classic": ("Classic", "classic"), "evergreen": ("Evergreen", "evergreen"),
         "rising": ("Rising", "rising"), "hidden gem": ("Hidden gem", "gem")}
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
           "height='32' rx='7' fill='%23ff6600'/%3E%3Cpath d='M9 10h14M9 16h10M9 22h6' stroke='white' stroke-width='3' "
           "stroke-linecap='round'/%3E%3C/svg%3E")


def e(text):
    return escape(str(text or ""), quote=True)


def slugify(name, taken):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", "and")).strip("-")[:70].strip("-") or "course"
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    taken.add(slug)
    return slug


def topic_slug(topic):
    return re.sub(r"[^a-z0-9]+", "-", topic.lower().replace("&", "and")).strip("-")


def year(t):
    return time.gmtime(t).tm_year


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


# ---- shared templates -------------------------------------------------------------

def head(title, description, path, image, kind="website", extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{BASE}{path}">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{kind}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{e(image)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="/style.css">
<script src="/common.js"></script>
{extra}</head>
<body>"""


def header(query=""):
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="/" aria-label="{NAME}, home">
    <svg class="mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7"/><path d="M9 10h14M9 16h10M9 22h6"/></svg>
    <span>
      <span class="name">{NAME}</span>
      <span class="sub" id="summary">{e(TAGLINE)}</span>
    </span>
  </a>
  <form class="search" action="/" method="get" role="search">
    <label for="q" class="visually-hidden">Search courses</label>
    <input id="q" name="q" type="search" value="{e(query)}" placeholder="Search courses, instructors, topics" autocomplete="off">
    <kbd aria-hidden="true">/</kbd>
  </form>
  <div class="tools">
    <button class="icon-btn" id="themeBtn" type="button" aria-label="Toggle light or dark theme" title="Theme (T)">◐</button>
    <a class="icon-btn" href="/about/" title="About and how ranking works" aria-label="About">i</a>
    <button class="icon-btn" id="helpBtn" type="button" aria-haspopup="dialog" aria-label="Keyboard shortcuts" title="Shortcuts (?)">?</button>
  </div>
</header>"""


HELP = """<dialog id="help" aria-labelledby="hTitle">
  <h2 id="hTitle">Keyboard</h2>
  <dl class="keys">
    <dt class="keys-h">In the course grid</dt>
    <dt><kbd>←</kbd><kbd>↑</kbd><kbd>→</kbd><kbd>↓</kbd></dt><dd>Move between courses</dd>
    <dt><kbd>Home</kbd> <kbd>End</kbd></dt><dd>Start / end of row (with <kbd>Ctrl</kbd>: first / last)</dd>
    <dt><kbd>PgUp</kbd> <kbd>PgDn</kbd></dt><dd>Jump several rows</dd>
    <dt><kbd>Enter</kbd></dt><dd>Open course</dd>
    <dt><kbd>S</kbd></dt><dd>Save / unsave course</dd>
    <dt><kbd>1</kbd>–<kbd>5</kbd></dt><dd>Best, Trending, Hidden gems, Evergreen, Saved</dd>
    <dt><kbd>[</kbd> <kbd>]</kbd></dt><dd>Previous / next topic</dd>
    <dt class="keys-h">On a course page</dt>
    <dt><kbd>←</kbd> <kbd>→</kbd></dt><dd>Previous / next course in your list</dd>
    <dt><kbd>S</kbd></dt><dd>Save / unsave</dd>
    <dt><kbd>O</kbd></dt><dd>Open the course website</dd>
    <dt><kbd>Esc</kbd></dt><dd>Back to the grid</dd>
    <dt class="keys-h">Everywhere</dt>
    <dt><kbd>/</kbd></dt><dd>Search</dd>
    <dt><kbd>T</kbd></dt><dd>Light / dark theme</dd>
    <dt><kbd>?</kbd></dt><dd>This help</dd>
  </dl>
  <button class="btn" id="hClose" type="button">Close</button>
</dialog>"""


def footer():
    return f"""<footer class="foot">
  Built from public Hacker News comments, {SPAN}, via the
  <a href="https://huggingface.co/datasets/nixiesearch/hackernews-comments">nixiesearch/hackernews-comments</a> (Apache-2.0) and
  <a href="https://huggingface.co/datasets/open-index/hacker-news">open-index/hacker-news</a> (ODC-By) datasets and the
  <a href="https://hn.algolia.com/api">HN Search API</a>.
  Each comment belongs to its author; course images belong to the course providers.
  Want a comment removed? <a href="{REPO}/issues/new?title=Removal%20request&amp;labels=removal">Open a removal request</a>.
  <a href="/about/">About</a> · <a href="{REPO}">Source</a>.
  Not affiliated with Y Combinator or Hacker News.
</footer>"""


def end(scripts):
    tags = "\n".join(f'<script src="{s}" defer></script>' for s in scripts)
    return f"{HELP}\n{footer()}\n{tags}\n</body>\n</html>\n"


# ---- pages ------------------------------------------------------------------------

def index_page(meta):
    return (head(f"{NAME}: the courses programmers keep recommending", TAGLINE, "/", f"{BASE}/img/og/site.png")
            + header()
            + """
<div id="listView">
  <nav class="views" aria-label="Views"><div role="tablist" id="views"></div></nav>
  <div class="filters" id="filters" aria-label="Filters"></div>
  <main id="main">
    <h1 class="visually-hidden">Courses programmers recommend</h1>
    <p class="status" id="status" aria-live="polite"></p>
    <div id="grid" class="grid" role="grid" aria-labelledby="status" aria-describedby="gridHint"></div>
    <p id="gridHint" class="visually-hidden">Arrow keys move between courses, Enter opens one, S saves it.</p>
    <button id="more" class="btn more" type="button" hidden>Show more</button>
  </main>
</div>
"""
            + end(["/courses.js", "/app.js"]))


def badges_html(c):
    shown = [b for b in c["badges"] if not ("classic" in c["badges"] and b == "evergreen")]
    return "".join(f'<span class="badge {BADGE[b][1]}">{BADGE[b][0]}</span>' for b in shown)


def comment_body(text):
    out = []
    for para in re.split(r"\n{2,}", text):
        if re.match(r"^\s*>", para):
            out.append(f"<blockquote>{e(re.sub(r'(?m)^\s*>\s?', '', para))}</blockquote>")
        else:
            out.append(f"<p>{e(para)}</p>")
    return "".join(out)


def timeline(c, comments, data_end):
    start, stop = 2006, year(data_end)
    counts = [0] * (stop - start + 1)
    for ci, s in c["endorsements"]:
        if s >= 2:
            counts[year(comments[ci]["t"]) - start] += 1
    peak = max(counts) or 1
    bars = "".join(
        f'<span class="h{round(n / peak * 10) if n else 0}{"" if n else " zero"}" title="{start + i}: {n}"></span>'
        for i, n in enumerate(counts))
    label = ", ".join(f"{start + i}: {n}" for i, n in enumerate(counts) if n)
    return (f'<section class="timeline"><h2>Recommendations by year</h2>'
            f'<div class="bars" role="img" aria-label="{e(label)}">{bars}</div>'
            f'<div class="years"><span>{start}</span><span>{stop}</span></div></section>')


def course_page(c, comments, by_id, data_end):
    img = c["img"] or f"{BASE}/img/og/{topic_slug(c['topic'])}.png"
    desc = c["why"] or c["summary"] or f"{c['name']} from {c['provider']}, recommended on Hacker News."
    span = f"{year(c['first'])}" if year(c["first"]) == year(c["last"]) else f"{year(c['first'])}–{year(c['last'])}"
    ld = {"@context": "https://schema.org", "@type": "Course", "name": c["name"], "description": c["summary"] or desc,
          "provider": {"@type": "Organization", "name": c["provider"]}, "url": f"{BASE}/course/{c['slug']}/"}
    if c["url"]:
        ld["sameAs"] = c["url"]
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>\n'

    hero_cls = "hero-img" + ("" if c["img"] else " art") + (" tall" if c["imgTall"] else "")
    hero_src = c["img"] or f"/img/topics/{topic_slug(c['topic'])}.svg"
    caption = ""
    if c["img"] and c["imgPage"]:
        host = re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*", r"\1", c["imgPage"]))
        caption = f'<figcaption>Image: <a href="{e(c["imgPage"])}" rel="noopener nofollow" target="_blank">{e(host)}</a></figcaption>'
    go = (f'<a class="btn primary" id="goBtn" href="{e(c["url"])}" target="_blank" rel="noopener nofollow">Go to course ↗</a>'
          if c["url"] else
          f'<a class="btn primary" id="goBtn" href="https://duckduckgo.com/?q={e(c["name"] + " " + c["provider"])}" '
          f'target="_blank" rel="noopener nofollow">Search for it ↗</a>')
    facts = "".join(f'<span class="chip">{e(f)}</span>' for f in (c["topic"], c["level"], c["cost"], c["format"])
                    if f and f != "unknown")
    facts += "".join(f'<span class="chip plain">#{e(t)}</span>' for t in c["tags"])

    items = []
    for ci, s in c["endorsements"]:
        cm = comments[ci]
        thread = f'<span class="thread">in “{e(cm["thread"])}”</span>' if cm["thread"] else ""
        long = len(cm["text"]) > 600
        items.append(
            f'<li class="comment"><header><span class="stance s{s}">{STANCE[s]}</span><strong>{e(cm["by"])}</strong>'
            f'<span>{year(cm["t"])}</span>{thread}</header>'
            f'<div class="{"clamped" if long else ""}">{comment_body(cm["text"])}</div>'
            f'<footer>{"<button class=\"link-btn read-more\" type=\"button\">Read all</button>" if long else ""}'
            f'<a href="https://news.ycombinator.com/item?id={cm["id"]}" target="_blank" rel="noopener">Open comment ↗</a></footer></li>')

    related = "".join(
        f'<li><a href="/course/{r["slug"]}/"><strong>{e(r["name"])}</strong>'
        f'<span>{e(r["provider"])} · {plural(r["recommenders"], "recommender")}</span></a></li>'
        for r in (by_id[i] for i in c["related"] if i in by_id))

    prev_next = ""
    if c.get("prev"):
        prev_next += f'<a id="prevLink" href="/course/{c["prev"]["slug"]}/">← {e(c["prev"]["name"])}</a> '
    if c.get("next"):
        prev_next += f'<a id="nextLink" href="/course/{c["next"]["slug"]}/">{e(c["next"]["name"])} →</a>'

    return (head(f"{c['name']} · {NAME}", desc, f"/course/{c['slug']}/", img, "article", extra)
            + header()
            + f"""
<main id="main" class="course-page" tabindex="-1" data-id="{c['id']}" data-slug="{c['slug']}">
  <nav class="crumbs" aria-label="Course navigation"><a href="/" id="backLink">← All courses</a><span id="prevNext">{prev_next}</span></nav>
  <figure class="hero"><div class="{hero_cls}"><img src="{e(hero_src)}" alt="" referrerpolicy="no-referrer" data-fallback="/img/topics/{topic_slug(c['topic'])}.svg"></div>{caption}</figure>
  <header class="course-head">
    <div class="card-top"><span class="rank">#{c['rank']} overall</span>{badges_html(c)}</div>
    <h1 id="cName">{e(c['name'])}</h1>
    <p class="provider">{e(c['provider'])}</p>
    <p class="statline">{plural(c['recommenders'], 'recommender')} · {plural(c['threads'], 'thread')} · recommended in {plural(c['years_active'], 'year')}, {span} · score {c['score']:.1f}</p>
  </header>
  <div class="actions">{go}<button class="btn" id="saveBtn" type="button" aria-pressed="false">☆ Save</button></div>
  <p class="lede">{e(c['summary'])}</p>
  <p class="why-long">{e(c['why'])}</p>
  <div class="facts">{facts}</div>
  {timeline(c, comments, data_end)}
  <h2 class="section-h">What commenters said ({len(c['endorsements'])})</h2>
  <ol class="comments">{''.join(items)}</ol>
  {'<h2 class="section-h">Related courses</h2><ul class="related">' + related + '</ul>' if related else ''}
</main>
"""
            + end(["/course.js"]))


def about_page(meta):
    return (head(f"About · {NAME}", "How Hacker Courses finds, ranks and credits the courses programmers recommend.",
                 "/about/", f"{BASE}/img/og/site.png")
            + header()
            + f"""
<main id="main" class="prose" tabindex="-1">
  <h1>About {NAME}</h1>
  <aside class="dedication">
    <h2>Dedication</h2>
    <p>Dedicated to <a href="https://x.com/karpathy" rel="noopener">Andrej Karpathy</a>, whose idea prompted
    <a href="https://hackertube.org" rel="noopener">HackerTube</a>, the collection of videos programmers keep
    telling each other to watch. {NAME} applies that idea to courses.</p>
  </aside>

  <p>{NAME} collects the online courses programmers recommend to each other in public Hacker News comments,
  from {SPAN}: {meta['courses']:,} courses drawn from {meta['comments']:,} comments.</p>

  <h2>How ranking works</h2>
  <p>Comment karma is not public, so each course is scored from who recommended it, how strongly, in how many
  separate discussions, and for how long.</p>
  <ol class="method">
    <li><strong>Stance.</strong> Every comment is labelled for the course it mentions: strongly recommends (1.0),
    recommends (0.7), mentions (0.25) or criticizes (0).</li>
    <li><strong>One vote per person.</strong> Someone who recommends a course five times counts once, at their
    strongest stance.</li>
    <li><strong>Pile-ons are damped.</strong> Within one thread, votes decay by half each (1, ½, ¼…). Ten replies in
    one thread are worth less than two independent threads; the same course surfacing in ten unrelated threads
    counts ten times.</li>
    <li><strong>Staying power.</strong> Each extra calendar year in which people recommended it adds 8%.</li>
  </ol>
  <p><strong>Trending</strong> uses the same votes, halving their weight every two years back from the newest comment
  in the data.</p>

  <h2>Badges</h2>
  <dl class="badge-defs">
    <dt><span class="badge classic">Classic</span></dt><dd>Top-ranked and recommended across at least eight years.</dd>
    <dt><span class="badge evergreen">Evergreen</span></dt><dd>Recommended in six or more different years.</dd>
    <dt><span class="badge rising">Rising</span></dt><dd>Most of its support came in the last three years of data.</dd>
    <dt><span class="badge gem">Hidden gem</span></dt><dd>Only two to four recommenders, but nearly all of them emphatic.</dd>
  </dl>

  <h2>How the list was made</h2>
  <p>Comments were found with keyword rules and reviewed by AI models (Claude Haiku 5.5 and Claude Sonnet 5.5),
  which also merged the many spellings of each course, labelled each comment's stance and wrote the summaries.
  Expect a few misses. Course images come from each course's own page; courses without one get an illustration
  for their topic. The full pipeline is <a href="{REPO}">open source</a>.</p>

  <h2>License</h2>
  <p>The code and original artwork are <a href="{REPO}/blob/main/LICENSE">MIT licensed</a>. The course catalog,
  rankings and summaries this project generated are
  <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Comments remain their authors' and
  course images their providers'; neither is licensed by this project. Details in
  <a href="{REPO}/blob/main/DATA-LICENSE.md">DATA-LICENSE.md</a>.</p>

  <h2>Privacy and removal</h2>
  <p>No accounts, no cookies, no tracking. Saved courses and your theme are kept in your own browser.
  Each comment belongs to its author and links back to the original. To have a comment removed,
  <a href="{REPO}/issues/new?title=Removal%20request&amp;labels=removal">open a removal request</a>.</p>
</main>
"""
            + end([]))


def not_found_page():
    return (head(f"Not found · {NAME}", TAGLINE, "/404", f"{BASE}/img/og/site.png")
            + header()
            + """
<main id="main" class="prose" tabindex="-1">
  <h1>Page not found</h1>
  <p>That page doesn't exist. <a href="/">Browse all courses</a> or search above.</p>
</main>
"""
            + end([]))


HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
  Content-Security-Policy: default-src 'self'; img-src 'self' https: data:; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'

/img/*
  Cache-Control: public, max-age=2592000
"""


def write_all(courses, comments, data_end):
    """courses must already carry slug, rank and the fields build.py computes."""
    configure(data_end)
    by_id = {c["id"]: c for c in courses}
    for i, c in enumerate(courses):
        c["prev"] = courses[i - 1] if i > 0 else None
        c["next"] = courses[i + 1] if i + 1 < len(courses) else None
    meta = {"courses": len(courses), "comments": len(comments)}

    for old in (SITE / "course").glob("*/index.html"):
        old.unlink()
    for c in courses:
        d = SITE / "course" / c["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(course_page(c, comments, by_id, data_end), encoding="utf-8")
    for c in courses:
        c.pop("prev", None), c.pop("next", None)

    (SITE / "index.html").write_text(index_page(meta), encoding="utf-8")
    (SITE / "about").mkdir(exist_ok=True)
    (SITE / "about" / "index.html").write_text(about_page(meta), encoding="utf-8")
    (SITE / "404.html").write_text(not_found_page(), encoding="utf-8")
    (SITE / "_headers").write_text(HEADERS, encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    today = time.strftime("%Y-%m-%d")
    urls = ["/", "/about/"] + [f"/course/{c['slug']}/" for c in courses]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
