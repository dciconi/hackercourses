"""Static pages for hosting on Cloudflare Pages (no build step there; everything is committed).

Writes into site/: index.html (the grid), course/<slug>/index.html for every course,
topic/<slug>/index.html for every topic, about/, 404.html, sitemap.xml, robots.txt, llms.txt,
llms-full.txt and _headers. Called from build.py.
"""

import json
import re
import time
from html import escape

from classify import OTHER, ROOT, TOPICS

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
TOPIC_PAGES = []  # [(topic, slug, course count)], filled by write_all() for the footer


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

def clip(text, n):
    """Shorten to at most n characters at a word boundary, for meta descriptions."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[:n - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def json_ld(data):
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}</script>\n'


def iso(t):
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def head(title, description, path, image, kind="website", extra="", index=True):
    # The 404 page is served at every missing URL, so it gets no canonical and stays out of the index.
    where = (f'<link rel="canonical" href="{BASE}{path}">\n<meta property="og:url" content="{BASE}{path}">\n'
             if index else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="{"index, follow, max-image-preview:large, max-snippet:-1" if index else "noindex"}">
{where}<meta property="og:site_name" content="{NAME}">
<meta property="og:locale" content="en_US">
<meta property="og:type" content="{kind}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:image" content="{e(image)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="alternate" type="text/plain" href="/llms.txt" title="Site summary for language models">
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
  Want a comment removed? <a href="{REPO}/issues/new?template=removal.yml">Open a removal request</a>.
  <a href="/about/">About</a> · <a href="{REPO}">Source</a>.
  Not affiliated with Y Combinator or Hacker News.
  {topic_nav()}
</footer>"""


def topic_nav():
    links = " · ".join(f'<a href="/topic/{s}/">{e(t)}</a>' for t, s, _ in TOPIC_PAGES)
    return f'<nav class="foot-topics" aria-label="Topics">Courses by topic: {links}</nav>' if links else ""


def end(scripts):
    tags = "\n".join(f'<script src="{s}" defer></script>' for s in scripts)
    return f"{HELP}\n{footer()}\n{tags}\n</body>\n</html>\n"


# ---- pages ------------------------------------------------------------------------

def span(c):
    return f"{year(c['first'])}" if year(c["first"]) == year(c["last"]) else f"{year(c['first'])}–{year(c['last'])}"


def topic_art(topic):
    return f"/img/topics/{topic_slug(topic)}.svg"


def card_html(c, eager=False):
    """A grid card as static HTML, matching what app.js builds, so the grid is readable without scripts."""
    thumb_cls = "thumb" + ("" if c["img"] else " art") + (" tall" if c["img"] and c["imgTall"] else "")
    prov = " · ".join(x for x in (c["provider"], c["level"], c["cost"]) if x and x != "unknown")
    return (f'<div class="card"><div class="{thumb_cls}"><img src="{e(c["img"] or topic_art(c["topic"]))}" alt="" '
            f'loading="{"eager" if eager else "lazy"}" decoding="async" referrerpolicy="no-referrer" '
            f'data-fallback="{topic_art(c["topic"])}"></div>'
            f'<div class="card-top"><span class="rank">#{c["rank"]}</span>{badges_html(c)}</div>'
            f'<h3><a href="/course/{c["slug"]}/">{e(c["name"])}</a></h3>'
            f'<p class="provider">{e(prov)}</p><p class="why">{e(c["why"] or c["summary"])}</p>'
            f'<div class="meta"><span>{plural(c["recommenders"], "recommender")} · {plural(c["threads"], "thread")} · '
            f'{span(c)}</span><span>{e(c["topic"])}</span></div></div>')


def item_list(courses, name):
    return {"@type": "ItemList", "name": name, "numberOfItems": len(courses),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/course/{c['slug']}/",
                                 "name": c["name"]} for i, c in enumerate(courses)]}


WEBSITE = {"@type": "WebSite", "@id": f"{BASE}/#website", "url": f"{BASE}/", "name": NAME,
           "alternateName": "hackercourses.com", "inLanguage": "en"}
FIRST_SCREEN = 60  # app.js shows this many cards before "Show more"


def index_page(meta, courses):
    top = ", ".join(c["name"] for c in courses[:3])
    desc = (f"{meta['courses']:,} online courses programmers keep recommending, ranked from {meta['comments']:,} "
            f"public Hacker News comments, {SPAN}. Top picks: {top}.")
    ld = {"@context": "https://schema.org", "@graph": [
        WEBSITE | {"description": desc},
        {"@type": "CollectionPage", "@id": f"{BASE}/", "url": f"{BASE}/", "name": f"{NAME}: the courses programmers keep recommending",
         "isPartOf": {"@id": f"{BASE}/#website"}, "dateModified": iso(meta["data_end"]),
         "mainEntity": item_list(courses[:FIRST_SCREEN], "Courses programmers recommend most on Hacker News")}]}
    cards = "".join(card_html(c, eager=i < 6) for i, c in enumerate(courses[:FIRST_SCREEN]))
    return (head(f"{NAME}: the online courses programmers recommend on Hacker News", desc, "/",
                 f"{BASE}/img/og/site.png", extra=json_ld(ld))
            + header()
            + f"""
<div id="listView">
  <nav class="views" aria-label="Views"><div role="tablist" id="views"></div></nav>
  <div class="filters" id="filters" aria-label="Filters"></div>
  <main id="main">
    <h1 class="visually-hidden">The online courses programmers recommend most on Hacker News</h1>
    <p class="status" id="status" aria-live="polite">{meta['courses']:,} courses · sorted by best ranked.</p>
    <div id="grid" class="grid" role="grid" aria-labelledby="status" aria-describedby="gridHint">{cards}</div>
    <p id="gridHint" class="visually-hidden">Arrow keys move between courses, Enter opens one, S saves it.</p>
    <button id="more" class="btn more" type="button" hidden>Show more</button>
  </main>
</div>
"""
            + end(["/courses.js", "/app.js"]))


def topic_page(topic, slug, courses, meta):
    n = len(courses)
    top = ", ".join(c["name"] for c in courses[:3])
    title = f"Best {topic} courses, as recommended on Hacker News"
    desc = (f"The {n} {topic} courses programmers recommend on Hacker News, ranked from public comments, {SPAN}. "
            f"Top picks: {top}.")
    path = f"/topic/{slug}/"
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{BASE}{path}", "url": f"{BASE}{path}", "name": title, "description": desc,
         "isPartOf": {"@id": f"{BASE}/#website"}, "about": topic,
         "dateModified": iso(max(c["last"] for c in courses)),
         "mainEntity": item_list(courses, f"{topic} courses ranked by Hacker News recommendations")},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": NAME, "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": topic, "item": f"{BASE}{path}"}]}]}
    free = sum(c["cost"] == "free" for c in courses)
    recs = sum(c["recommenders"] for c in courses)
    others = "".join(f'<a class="chip" href="/topic/{s}/">{e(t)} ({k})</a>' for t, s, k in TOPIC_PAGES if s != slug)
    return (head(title, desc, path, f"{BASE}/img/og/{slug}.png", extra=json_ld(ld))
            + header()
            + f"""
<main id="main" class="topic-page" tabindex="-1">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">← All courses</a></nav>
  <h1>Best {e(topic)} courses</h1>
  <p class="intro">The {e(plural(n, f"{topic} course"))} programmers recommend to each other on Hacker News, ranked by
  how many people recommended each one, how strongly, in how many separate threads and over how many years
  ({plural(recs, "recommendation")}, {SPAN}). {free:,} of them are free. <a href="/about/">How ranking works</a>.</p>
  <div class="grid static">{"".join(card_html(c, eager=i < 6) for i, c in enumerate(courses))}</div>
  <h2 class="section-h other-topics">Other topics</h2>
  <div class="facts">{others}</div>
</main>
"""
            + end([]))


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
    years = span(c)
    url, tslug = f"{BASE}/course/{c['slug']}/", topic_slug(c["topic"])
    # Lead with the facts a searcher (or a model quoting the page) needs: who, how many, since when.
    desc = clip(f"{c['name']} ({c['provider']}): recommended by {plural(c['recommenders'], 'Hacker News commenter')}, "
                f"{years}. {c['why'] or c['summary']}", 300)
    with_provider = c["provider"] and c["provider"].lower() not in c["name"].lower()
    title = f"{c['name']}{f' ({c['provider']})' if with_provider else ''} · Hacker News recommendations"
    course = {"@type": "Course", "@id": f"{url}#course", "name": c["name"],
              "description": c["summary"] or c["why"] or desc, "url": url, "image": img, "about": c["topic"],
              "provider": {"@type": "Organization", "name": c["provider"]}}
    if c["url"]:
        course["sameAs"] = c["url"]
    if c["level"] not in ("unknown", "mixed"):
        course["educationalLevel"] = c["level"]
    if c["cost"] in ("free", "paid"):
        course["isAccessibleForFree"] = c["cost"] == "free"
    if c["tags"]:
        course["keywords"] = ", ".join(c["tags"])
    modified = max(comments[ci]["t"] for ci, _ in c["endorsements"])
    ld = {"@context": "https://schema.org", "@graph": [
        course,
        {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc,
         "isPartOf": {"@id": f"{BASE}/#website"}, "about": {"@id": f"{url}#course"},
         "datePublished": iso(c["first"]), "dateModified": iso(modified)},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": NAME, "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": c["topic"], "item": f"{BASE}/topic/{tslug}/"},
            {"@type": "ListItem", "position": 3, "name": c["name"], "item": url}]}]}
    extra = json_ld(ld)

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
    facts = f'<a class="chip" href="/topic/{tslug}/">{e(c["topic"])}</a>'
    facts += "".join(f'<span class="chip">{e(f)}</span>' for f in (c["level"], c["cost"], c["format"])
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

    return (head(title, desc, f"/course/{c['slug']}/", img, "article", extra)
            + header()
            + f"""
<main id="main" class="course-page" tabindex="-1" data-id="{c['id']}" data-slug="{c['slug']}">
  <nav class="crumbs" aria-label="Course navigation"><a href="/" id="backLink">← All courses</a><span id="prevNext">{prev_next}</span></nav>
  <figure class="hero"><div class="{hero_cls}"><img src="{e(hero_src)}" alt="{e(c['name']) if c['img'] else ''}" referrerpolicy="no-referrer" data-fallback="/img/topics/{topic_slug(c['topic'])}.svg"></div>{caption}</figure>
  <header class="course-head">
    <div class="card-top"><span class="rank">#{c['rank']} overall</span>{badges_html(c)}</div>
    <h1 id="cName">{e(c['name'])}</h1>
    <p class="provider">{e(c['provider'])}</p>
    <p class="statline">{plural(c['recommenders'], 'recommender')} · {plural(c['threads'], 'thread')} · recommended in {plural(c['years_active'], 'year')}, {years} · score {c['score']:.1f}</p>
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
    desc = (f"How {NAME} finds, ranks and credits the {meta['courses']:,} online courses programmers recommend "
            f"in {meta['comments']:,} public Hacker News comments, {SPAN}.")
    # The generated catalog is CC BY 4.0, so describe it as a dataset (Google Dataset Search, citations).
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "AboutPage", "@id": f"{BASE}/about/", "url": f"{BASE}/about/", "name": f"About {NAME}",
         "description": desc, "isPartOf": {"@id": f"{BASE}/#website"}},
        {"@type": "Dataset", "name": f"{NAME}: online courses recommended on Hacker News",
         "description": (f"{meta['courses']:,} online courses recommended in {meta['comments']:,} public Hacker News "
                         f"comments, {SPAN}, with rankings, summaries, topics, levels, costs and formats."),
         "url": f"{BASE}/", "sameAs": REPO, "license": "https://creativecommons.org/licenses/by/4.0/",
         "isAccessibleForFree": True, "keywords": ["online courses", "Hacker News", "MOOC", "computer science",
                                                   "programming", "recommendations"],
         "temporalCoverage": f"2006-01-01/{iso(meta['data_end'])}", "dateModified": iso(meta["data_end"]),
         "creator": {"@type": "Organization", "name": NAME, "url": f"{BASE}/"},
         "distribution": [{"@type": "DataDownload", "encodingFormat": "text/plain",
                           "contentUrl": f"{BASE}/llms-full.txt"}]}]}
    return (head(f"About · {NAME}", desc, "/about/", f"{BASE}/img/og/site.png", extra=json_ld(ld))
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
  <p>No accounts and no cookies. Visits are counted with
  <a href="https://www.cloudflare.com/web-analytics/" rel="noopener">Cloudflare Web Analytics</a>, which
  doesn't use cookies or fingerprinting and doesn't follow you to other sites. Saved courses and your
  theme are kept in your own browser.
  Each comment belongs to its author and links back to the original. To have a comment removed,
  <a href="{REPO}/issues/new?template=removal.yml">open a removal request</a>.</p>
</main>
"""
            + end([]))


def not_found_page():
    return (head(f"Not found · {NAME}", TAGLINE, "/404", f"{BASE}/img/og/site.png", index=False)
            + header()
            + """
<main id="main" class="prose" tabindex="-1">
  <h1>Page not found</h1>
  <p>That page doesn't exist. <a href="/">Browse all courses</a> or search above.</p>
</main>
"""
            + end([]))


# Cloudflare injects its Web Analytics beacon into every page; the CSP allows that script and its
# reporting endpoint and nothing else from outside the site.
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
  Content-Security-Policy: default-src 'self'; img-src 'self' https: data:; script-src 'self' https://static.cloudflareinsights.com; style-src 'self'; connect-src 'self' https://cloudflareinsights.com; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'

/img/*
  Cache-Control: public, max-age=2592000

/llms*.txt
  Content-Type: text/plain; charset=utf-8
"""


# ---- plain-text summaries for language models (llmstxt.org) -------------------------

def course_line(c):
    return (f"- [{c['name']}]({BASE}/course/{c['slug']}/): {c['provider']}; "
            f"{plural(c['recommenders'], 'recommender')}, {span(c)}. {clip(c['summary'] or c['why'], 220)}")


def llms_txt(courses, meta, by_topic):
    out = [f"# {NAME}", "",
           f"> The online courses programmers keep recommending, ranked from {meta['comments']:,} public Hacker News "
           f"comments, {SPAN}: {meta['courses']:,} courses with a page each.", "",
           "Each course is scored from who recommended it, how strongly, in how many separate threads and for how "
           "many years (one vote per person; replies piling onto one thread are damped). Every course page quotes "
           "the comments behind its ranking and links each one to Hacker News. The catalog, rankings and summaries "
           "are CC BY 4.0; please cite and link the course page. Not affiliated with Y Combinator or Hacker News.", "",
           "## Courses by topic", ""]
    for t, s, n in TOPIC_PAGES:
        out.append(f"- [{t}]({BASE}/topic/{s}/): {n} courses. Top: "
                   + ", ".join(c["name"] for c in by_topic[t][:5]))
    out += ["", "## Top 30 overall", ""] + [course_line(c) for c in courses[:30]]
    out += ["", "## Optional", "",
            f"- [Every course, one record each]({BASE}/llms-full.txt): rank, links, topic, level, cost, format, "
            "years and summaries for all courses",
            f"- [About and ranking method]({BASE}/about/)",
            f"- [Source code and pipeline]({REPO})", ""]
    return "\n".join(out)


def llms_full_txt(courses, meta):
    out = [f"# {NAME}: every course", "",
           f"> {meta['courses']:,} online courses recommended in {meta['comments']:,} public Hacker News comments, "
           f"{SPAN}, in rank order. CC BY 4.0: cite {BASE}/ and link the course page.", ""]
    for c in courses:
        facts = "; ".join(f"{k}: {v}" for k, v in (("Topic", c["topic"]), ("Level", c["level"]), ("Cost", c["cost"]),
                                                   ("Format", c["format"])) if v and v != "unknown")
        badges = ", ".join(BADGE[b][0] for b in c["badges"])
        out += [f"## #{c['rank']} {c['name']} ({c['provider']})", "",
                f"Page: {BASE}/course/{c['slug']}/"]
        if c["url"]:
            out.append(f"Course website: {c['url']}")
        out += [facts,
                f"Recommended by {c['recommenders']:,} {'person' if c['recommenders'] == 1 else 'people'} in {plural(c['threads'], 'thread')}, "
                f"{span(c)}." + (f" Badges: {badges}." if badges else "")]
        if c["tags"]:
            out.append("Tags: " + ", ".join(c["tags"]))
        out += [""] + [p for p in (c["summary"], c["why"] and f"Why people recommend it: {c['why']}") if p] + [""]
    return "\n".join(out)


def write_all(courses, comments, data_end):
    """courses must already carry slug, rank and the fields build.py computes."""
    configure(data_end)
    by_id = {c["id"]: c for c in courses}
    for i, c in enumerate(courses):
        c["prev"] = courses[i - 1] if i > 0 else None
        c["next"] = courses[i + 1] if i + 1 < len(courses) else None
    meta = {"courses": len(courses), "comments": len(comments), "data_end": data_end}
    by_topic = {}
    for c in courses:
        by_topic.setdefault(c["topic"], []).append(c)
    TOPIC_PAGES[:] = [(t, topic_slug(t), len(by_topic[t])) for t in [name for name, _ in TOPICS] + [OTHER]
                      if t in by_topic]

    for old in (SITE / "course").glob("*/index.html"):
        old.unlink()
    for c in courses:
        d = SITE / "course" / c["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(course_page(c, comments, by_id, data_end), encoding="utf-8")
    for c in courses:
        c.pop("prev", None), c.pop("next", None)

    for old in (SITE / "topic").glob("*/index.html"):
        old.unlink()
    for t, s, _ in TOPIC_PAGES:
        d = SITE / "topic" / s
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(topic_page(t, s, by_topic[t], meta), encoding="utf-8")

    (SITE / "index.html").write_text(index_page(meta, courses), encoding="utf-8")
    (SITE / "about").mkdir(exist_ok=True)
    (SITE / "about" / "index.html").write_text(about_page(meta), encoding="utf-8")
    (SITE / "404.html").write_text(not_found_page(), encoding="utf-8")
    (SITE / "_headers").write_text(HEADERS, encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    (SITE / "llms.txt").write_text(llms_txt(courses, meta, by_topic), encoding="utf-8")
    (SITE / "llms-full.txt").write_text(llms_full_txt(courses, meta), encoding="utf-8")

    # lastmod is the newest comment behind each page, so crawlers can trust it and skip unchanged pages.
    def newest(cs):
        return iso(max(comments[ci]["t"] for c in cs for ci, _ in c["endorsements"]))
    urls = ([("/", iso(data_end)), ("/about/", iso(data_end))]
            + [(f"/topic/{s}/", newest(by_topic[t])) for t, s, _ in TOPIC_PAGES]
            + [(f"/course/{c['slug']}/", newest([c])) for c in courses])
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{m}</lastmod></url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
