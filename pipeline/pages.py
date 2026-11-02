"""Static pages for hosting on Cloudflare Pages (no build step there; everything is committed).

Writes into site/: index.html (the grid), course/<slug>/index.html for every course,
topic/<slug>/index.html for every topic, about/, 404.html, sitemap.xml, robots.txt, llms.txt,
llms-full.txt and _headers. Called from build.py.
"""

import json
import re
import time
from html import escape

import rank
import sources
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
TOPIC_PAGES = {"hn": [], "reddit": []}  # source -> [(topic, slug, course count)], filled by write_all() for the footer
SOURCE_NAMES = {"hn": "Hacker News", "reddit": "Reddit"}
REDDIT_COMMUNITIES = len(sources.SUBREDDITS)  # write_all() sets the number actually present in the data
REDDIT_SUBS = list(sources.SUBREDDITS)  # likewise: the configured subreddits that have comments
SUBREDDIT_GROUPS = [
    ("Business & entrepreneurship", ["Entrepreneur", "startups", "smallbusiness", "SaaS", "indiehackers",
                                     "EntrepreneurRideAlong"]),
    ("Software development", ["programming", "ExperiencedDevs", "webdev", "learnprogramming", "Python", "selfhosted"]),
    ("AI & ML", ["MachineLearning", "LocalLLaMA", "artificial", "ChatGPT", "ClaudeAI", "learnmachinelearning"]),
    ("Productivity", ["productivity", "getdisciplined", "Notion", "ObsidianMD", "PKMS", "bujo"]),
    ("Marketing & growth", ["marketing", "PPC", "SEO", "bigseo", "socialmedia", "Emailmarketing"]),
]
# The only Reddit data in use: a per-subreddit dump of Reddit's own comments, 2005-06 to 2023-12.
REDDIT_DUMP = "https://academictorrents.com/details/56aa49f9653ba545f48df2e33679f014d2829c10"
REDDIT_TERMS = "https://www.redditinc.com/policies/user-agreement"
HN_CREDITS = (("nixiesearch/hackernews-comments", "https://huggingface.co/datasets/nixiesearch/hackernews-comments",
               "Apache-2.0"),
              ("open-index/hacker-news", "https://huggingface.co/datasets/open-index/hacker-news", "ODC-By"),
              ("HN Search API", "https://hn.algolia.com/api", None))


def home(source):
    return "/reddit/" if source == "reddit" else "/"


def topic_url(source, slug):
    return f"{home(source)}topic/{slug}/"


def tagline(source, comments=0):
    if source == "reddit":
        return (f"The online courses Redditors keep recommending, ranked from {comments:,} public comments "
                f"in {REDDIT_COMMUNITIES} communities.")
    return TAGLINE


def source_switch(source, links=None):
    """The Hacker News | Reddit control. links maps a source to its href (default: its home page)."""
    links = links or {}
    items = ""
    for s, name in SOURCE_NAMES.items():
        current = ' aria-current="page"' if s == source else ""
        items += f'<a href="{links.get(s, home(s))}" data-source="{s}"{current}>{name}</a>'
    return f'<nav class="source-switch" aria-label="Source">{items}</nav>'


def has_switch(meta, source):
    """The switch only exists once there are Reddit courses, so nothing ever links to a missing /reddit/."""
    return source == "reddit" or bool(meta.get("reddit"))


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


def header(query="", source="hn", tag=None):
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="/" aria-label="{NAME}, home">
    <svg class="mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7"/><path d="M9 10h14M9 16h10M9 22h6"/></svg>
    <span>
      <span class="name">{NAME}</span>
      <span class="sub" id="summary">{e(tag or TAGLINE)}</span>
    </span>
  </a>
  <form class="search" action="{home(source)}" method="get" role="search">
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


def reddit_present():
    return bool(TOPIC_PAGES["reddit"])


def footer(source="hn"):
    credit = f"""Built from public Hacker News comments, {SPAN}, via the
  <a href="https://huggingface.co/datasets/nixiesearch/hackernews-comments">nixiesearch/hackernews-comments</a> (Apache-2.0) and
  <a href="https://huggingface.co/datasets/open-index/hacker-news">open-index/hacker-news</a> (ODC-By) datasets and the
  <a href="https://hn.algolia.com/api">HN Search API</a>."""
    unaffiliated = "Not affiliated with Y Combinator or Hacker News."
    if reddit_present() or source == "reddit":
        credit += f"""
  Reddit comments come from the <a href="{REDDIT_DUMP}">per-subreddit Reddit dump by Watchful1</a> on Academic
  Torrents (2005 to 2023, no license published; the comments belong to their authors under
  <a href="{REDDIT_TERMS}">Reddit's User Agreement</a>)."""
        unaffiliated = "Not affiliated with Y Combinator, Hacker News or Reddit."
    return f"""<footer class="foot">
  {credit}
  Each comment belongs to its author; course images belong to the course providers.
  Want a comment removed? <a href="{REPO}/issues/new?template=removal.yml">Open a removal request</a>.
  <a href="/about/">About</a> · <a href="{REPO}">Source</a>.
  {unaffiliated}
  {topic_nav(source)}
</footer>"""


def topic_nav(source="hn"):
    links = " · ".join(f'<a href="{topic_url(source, s)}">{e(t)}</a>' for t, s, _ in TOPIC_PAGES[source])
    return f'<nav class="foot-topics" aria-label="Topics">Courses by topic: {links}</nav>' if links else ""


def end(scripts, source="hn"):
    tags = "\n".join(f'<script src="{s}" defer></script>' for s in scripts)
    return f"{HELP}\n{footer(source)}\n{tags}\n</body>\n</html>\n"


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


def index_page(meta, courses, source="hn"):
    reddit = source == "reddit"
    top = ", ".join(c["name"] for c in courses[:3])
    if reddit:
        desc = (f"{meta['courses']:,} online courses Redditors keep recommending, ranked from {meta['comments']:,} "
                f"public Reddit comments in {REDDIT_COMMUNITIES} communities. Top picks: {top}.")
        title, h1 = f"{NAME}: the online courses Reddit recommends", "The online courses recommended most on Reddit"
        coll, listing = f"{NAME}: the courses Redditors keep recommending", "Courses Redditors recommend most on Reddit"
    else:
        desc = (f"{meta['courses']:,} online courses programmers keep recommending, ranked from {meta['comments']:,} "
                f"public Hacker News comments, {SPAN}. Top picks: {top}.")
        title, h1 = (f"{NAME}: the online courses programmers recommend on Hacker News",
                     "The online courses programmers recommend most on Hacker News")
        coll, listing = (f"{NAME}: the courses programmers keep recommending",
                         "Courses programmers recommend most on Hacker News")
    path = home(source)
    ld = {"@context": "https://schema.org", "@graph": [
        WEBSITE | {"description": desc},
        {"@type": "CollectionPage", "@id": f"{BASE}{path}", "url": f"{BASE}{path}", "name": coll,
         "isPartOf": {"@id": f"{BASE}/#website"}, "dateModified": iso(meta["data_end"]),
         "mainEntity": item_list(courses[:FIRST_SCREEN], listing)}]}
    cards = "".join(card_html(c, eager=i < 6) for i, c in enumerate(courses[:FIRST_SCREEN]))
    switch = source_switch(source) + "\n  " if has_switch(meta, source) else ""
    scripts = ["/reddit/courses.js" if reddit else "/courses.js", "/app.js"]
    return (head(title, desc, path, f"{BASE}/img/og/site.png", extra=json_ld(ld))
            + header(source=source, tag=tagline(source, meta["comments"]))
            + f"""
<div id="listView">
  {switch}<nav class="views" aria-label="Views"><div role="tablist" id="views"></div></nav>
  <div class="filters" id="filters" aria-label="Filters"></div>
  <main id="main">
    <h1 class="visually-hidden">{h1}</h1>
    <p class="status" id="status" aria-live="polite">{meta['courses']:,} courses · sorted by best ranked.</p>
    <div id="grid" class="grid" role="grid" aria-labelledby="status" aria-describedby="gridHint">{cards}</div>
    <p id="gridHint" class="visually-hidden">Arrow keys move between courses, Enter opens one, S saves it.</p>
    <button id="more" class="btn more" type="button" hidden>Show more</button>
  </main>
</div>
"""
            + end(scripts, source))


def topic_page(topic, slug, courses, meta, source="hn"):
    reddit = source == "reddit"
    n = len(courses)
    top = ", ".join(c["name"] for c in courses[:3])
    where = SOURCE_NAMES[source]
    title = f"Best {topic} courses, as recommended on {where}"
    if reddit:
        desc = (f"The {n} {topic} courses Redditors recommend, ranked from public Reddit comments. "
                f"Top picks: {top}.")
    else:
        desc = (f"The {n} {topic} courses programmers recommend on Hacker News, ranked from public comments, {SPAN}. "
                f"Top picks: {top}.")
    who = "Redditors" if reddit else "programmers"
    span_text = "" if reddit else f", {SPAN}"
    path = topic_url(source, slug)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{BASE}{path}", "url": f"{BASE}{path}", "name": title, "description": desc,
         "isPartOf": {"@id": f"{BASE}/#website"}, "about": topic,
         "dateModified": iso(max(c["last"] for c in courses)),
         "mainEntity": item_list(courses, f"{topic} courses ranked by {where} recommendations")},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": NAME, "item": f"{BASE}{home(source)}"},
            {"@type": "ListItem", "position": 2, "name": topic, "item": f"{BASE}{path}"}]}]}
    free = sum(c["cost"] == "free" for c in courses)
    recs = sum(c["recommenders"] for c in courses)
    others = "".join(f'<a class="chip" href="{topic_url(source, s)}">{e(t)} ({k})</a>'
                     for t, s, k in TOPIC_PAGES[source] if s != slug)
    switch = ""
    if has_switch(meta, source):
        other = "hn" if reddit else "reddit"
        has_other = slug in meta.get("topics", {}).get(other, ())
        switch = source_switch(source, {other: topic_url(other, slug) if has_other else home(other)}) + "\n"
    return (head(title, desc, path, f"{BASE}/img/og/{slug}.png", extra=json_ld(ld))
            + header(source=source, tag=tagline(source, meta["comments"]))
            + f"""
{switch}<main id="main" class="topic-page" tabindex="-1">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="{home(source)}">← All courses</a></nav>
  <h1>Best {e(topic)} courses</h1>
  <p class="intro">The {e(plural(n, f"{topic} course"))} {who} recommend to each other on {where}, ranked by
  how many people recommended each one, how strongly, in how many separate threads and over how many years
  ({plural(recs, "recommendation")}{span_text}). {free:,} of them are free. <a href="/about/">How ranking works</a>.</p>
  <div class="grid static">{"".join(card_html(c, eager=i < 6) for i, c in enumerate(courses))}</div>
  <h2 class="section-h other-topics">Other topics</h2>
  <div class="facts">{others}</div>
</main>
"""
            + end([], source))


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


def present(c):
    """The sources this course is recommended on, in display order."""
    return [src for src in SOURCE_NAMES if src in c["sources"]]


def timeline(c, comments, data_end):
    vs = {src: view(c, src) for src in present(c)}
    # HN-only courses keep the 2006-to-today axis; a Reddit-only course shows just its own years.
    start = min([2006] * ("hn" in vs) + [year(v["first"]) for v in vs.values()])
    stop = max([year(data_end)] * ("hn" in vs) + [year(v["last"]) for v in vs.values()])
    rows = ""
    for src, v in vs.items():
        counts = [0] * (stop - start + 1)
        for ci, s in v["endorsements"]:
            if s >= 2:
                counts[year(comments[ci]["t"]) - start] += 1
        peak = max(counts) or 1
        bars = "".join(
            f'<span class="h{round(n / peak * 10) if n else 0}{"" if n else " zero"}" title="{start + i}: {n}"></span>'
            for i, n in enumerate(counts))
        label = ", ".join(f"{start + i}: {n}" for i, n in enumerate(counts) if n)
        if len(vs) > 1:
            label = f"{SOURCE_NAMES[src]}. {label}"
            rows += f'<p class="bars-label">{SOURCE_NAMES[src]}</p>'
        rows += f'<div class="bars" role="img" aria-label="{e(label)}">{bars}</div>'
    return (f'<section class="timeline"><h2>Recommendations by year</h2>{rows}'
            f'<div class="years"><span>{start}</span><span>{stop}</span></div></section>')


READ_ALL = '<button class="link-btn read-more" type="button">Read all</button>'


def comment_item(cm, s, src):
    thread = f'<span class="thread">in “{e(cm["thread"])}”</span>' if cm["thread"] else ""
    if src == "reddit":
        sub = f'<span>r/{e(cm["sub"])}</span>' if cm.get("sub") else ""
        # Votes captured too soon after posting say little, so they are not shown (nor counted).
        settled = cm.get("age") is not None and cm["age"] >= rank.UPVOTE_MIN_AGE
        ups = f'<span class="ups">▲ {cm["ups"]:,}</span>' if cm.get("ups") is not None and settled else ""
        return (f'<li class="comment"><header><span class="stance s{s}">{STANCE[s]}</span><strong>{e(cm["by"])}</strong>'
                f'{sub}<span>{year(cm["t"])}</span>{thread}{ups}</header>'
                f'<div>{comment_body(cm["text"])}</div>'
                f'<footer><a href="{e(cm["url"])}" target="_blank" rel="noopener">Open on Reddit ↗</a></footer></li>')
    long = len(cm["text"]) > 600
    return (
        f'<li class="comment"><header><span class="stance s{s}">{STANCE[s]}</span><strong>{e(cm["by"])}</strong>'
        f'<span>{year(cm["t"])}</span>{thread}</header>'
        f'<div class="{"clamped" if long else ""}">{comment_body(cm["text"])}</div>'
        f'<footer>{READ_ALL if long else ""}'
        f'<a href="https://news.ycombinator.com/item?id={cm["id"]}" target="_blank" rel="noopener">Open comment ↗</a></footer></li>')


def course_page(c, comments, by_id, data_end, multi=False):
    """c: a merged course (shared fields plus sources). multi: the site has Reddit pages, so rank
    labels name their source ("#3 on Hacker News") instead of "overall"."""
    vs = {src: view(c, src) for src in present(c)}
    lead = next(iter(vs))
    first, last = min(x["first"] for x in vs.values()), max(x["last"] for x in vs.values())
    img = c["img"] or f"{BASE}/img/og/{topic_slug(c['topic'])}.png"
    years = span({"first": first, "last": last})
    url, tslug = f"{BASE}/course/{c['slug']}/", topic_slug(c["topic"])
    who = " and ".join(plural(vs[src]["recommenders"], word) for src, word in
                       (("hn", "Hacker News commenter"), ("reddit", "Redditor")) if src in vs)
    # Lead with the facts a searcher (or a model quoting the page) needs: who, how many, since when.
    desc = clip(f"{c['name']} ({c['provider']}): recommended by {who}, {years}. {c['why'] or c['summary']}", 300)
    with_provider = c["provider"] and c["provider"].lower() not in c["name"].lower()
    suffix = {("hn",): "Hacker News recommendations", ("reddit",): "Reddit recommendations"}.get(
        tuple(vs), "recommended on Hacker News and Reddit")
    title = f"{c['name']}{f' ({c['provider']})' if with_provider else ''} · {suffix}"
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
    modified = max(comments[ci]["t"] for x in vs.values() for ci, _ in x["endorsements"])
    ld = {"@context": "https://schema.org", "@graph": [
        course,
        {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc,
         "isPartOf": {"@id": f"{BASE}/#website"}, "about": {"@id": f"{url}#course"},
         "datePublished": iso(first), "dateModified": iso(modified)},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": NAME, "item": f"{BASE}{home(lead)}"},
            {"@type": "ListItem", "position": 2, "name": c["topic"], "item": f"{BASE}{topic_url(lead, tslug)}"},
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
    facts = f'<a class="chip" href="{topic_url(lead, tslug)}">{e(c["topic"])}</a>'
    facts += "".join(f'<span class="chip">{e(f)}</span>' for f in (c["level"], c["cost"], c["format"])
                     if f and f != "unknown")
    facts += "".join(f'<span class="chip plain">#{e(t)}</span>' for t in c["tags"])

    ranks = []
    for src, x in vs.items():
        where = "overall" if not multi and src == "hn" else f"on {SOURCE_NAMES[src]}"
        ranks.append(f'<span class="rank">#{x["rank"]} {where}</span>{badges_html(x)}')
    rank_line = '<span class="rank-sep" aria-hidden="true">·</span>'.join(ranks)
    statlines = "\n    ".join(
        f'<p class="statline">{SOURCE_NAMES[src] + ": " if len(vs) > 1 else ""}{plural(x["recommenders"], "recommender")} · '
        f'{plural(x["threads"], "thread")} · recommended in {plural(x["years_active"], "year")}, {span(x)} · '
        f'score {x["score"]:.1f}</p>' for src, x in vs.items())

    sections = []
    for src, x in vs.items():
        heading = "What commenters said" if tuple(vs) == ("hn",) else f"On {SOURCE_NAMES[src]}"
        items = "".join(comment_item(comments[ci], s, src) for ci, s in x["endorsements"])
        sections.append(f'<h2 class="section-h">{heading} ({len(x["endorsements"])})</h2>\n'
                        f'  <ol class="comments">{items}</ol>')

    related = "".join(
        f'<li><a href="/course/{r["slug"]}/"><strong>{e(r["name"])}</strong>'
        f'<span>{e(r["provider"])} · {plural(view(r, present(r)[0])["recommenders"], "recommender")}</span></a></li>'
        for r in (by_id[i] for i in c["related"] if i in by_id))

    prev_next = ""
    if c.get("prev"):
        prev_next += f'<a id="prevLink" href="/course/{c["prev"]["slug"]}/">← {e(c["prev"]["name"])}</a> '
    if c.get("next"):
        prev_next += f'<a id="nextLink" href="/course/{c["next"]["slug"]}/">{e(c["next"]["name"])} →</a>'

    return (head(title, desc, f"/course/{c['slug']}/", img, "article", extra)
            + header(source=lead)
            + f"""
<main id="main" class="course-page" tabindex="-1" data-id="{c['id']}" data-slug="{c['slug']}">
  <nav class="crumbs" aria-label="Course navigation"><a href="{home(lead)}" id="backLink">← All courses</a><span id="prevNext">{prev_next}</span></nav>
  <figure class="hero"><div class="{hero_cls}"><img src="{e(hero_src)}" alt="{e(c['name']) if c['img'] else ''}" referrerpolicy="no-referrer" data-fallback="/img/topics/{topic_slug(c['topic'])}.svg"></div>{caption}</figure>
  <header class="course-head">
    <div class="card-top">{rank_line}</div>
    <h1 id="cName">{e(c['name'])}</h1>
    <p class="provider">{e(c['provider'])}</p>
    {statlines}
  </header>
  <div class="actions">{go}<button class="btn" id="saveBtn" type="button" aria-pressed="false">☆ Save</button></div>
  <p class="lede">{e(c['summary'])}</p>
  <p class="why-long">{e(c['why'])}</p>
  <div class="facts">{facts}</div>
  {timeline(c, comments, data_end)}
  {"".join(sections)}
  {'<h2 class="section-h">Related courses</h2><ul class="related">' + related + '</ul>' if related else ''}
</main>
"""
            + end(["/course.js"], lead))


def reddit_about(meta):
    """The About section for the Reddit list; only the subreddits that are in the data."""
    present = set(meta.get("reddit_subs", ()))
    groups = "".join(
        f"<li><strong>{e(name)}.</strong> " + ", ".join(f"r/{e(sub)}" for sub in subs if sub in present) + "</li>"
        for name, subs in SUBREDDIT_GROUPS if present.intersection(subs))
    y0, y1 = meta.get("reddit_years", (2023, 2023))
    years = str(y0) if y0 == y1 else f"{y0} to {y1}"
    return f"""
  <h2 id="reddit">Reddit</h2>
  <p>The Reddit list is built the same way from {meta.get('reddit_comments', 0):,} public comments in
  {len(present)} subreddits, {years}, and ranked on its own. The two rankings are never mixed or normalized, so a
  rank on one says nothing about the other. A course needs at least two different recommenders to be listed
  from Reddit alone.</p>
  <ul class="subs">{groups}</ul>
  <p><strong>Upvotes.</strong> On Reddit a comment's votes also count. An upvoted comment counts up to twice
  (the more upvotes, the closer to twice), a comment with no net upvotes counts half, and comments captured
  less than 30 days after they were posted count without their votes, since they had no time to collect any.</p>
  <p><strong>Excerpts.</strong> Reddit comments are shown as short excerpts of at most 300 characters, each
  linking to the full comment on Reddit.</p>
  <p><strong>Data.</strong> The comments come from the
  <a href="{REDDIT_DUMP}" rel="noopener">per-subreddit Reddit dump by Watchful1</a> on Academic Torrents
  ("Subreddit comments/submissions 2005-06 to 2023-12", top 40k subreddits), so the Reddit list ends in
  December 2023. No license or terms were published with that dump. The comments belong to their authors
  and remain subject to <a href="{REDDIT_TERMS}" rel="noopener">Reddit's User Agreement</a>.
  {NAME} is not affiliated with Reddit.</p>
"""


def about_page(meta):
    reddit = meta.get("reddit")
    desc = (f"How {NAME} finds, ranks and credits the {meta['courses']:,} online courses programmers recommend "
            f"in {meta['comments']:,} public Hacker News comments, {SPAN}"
            + (" and in public Reddit comments." if reddit else "."))
    # The generated catalog is CC BY 4.0, so describe it as a dataset (Google Dataset Search, citations).
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "AboutPage", "@id": f"{BASE}/about/", "url": f"{BASE}/about/", "name": f"About {NAME}",
         "description": desc, "isPartOf": {"@id": f"{BASE}/#website"}},
        {"@type": "Dataset", "name": f"{NAME}: online courses recommended on Hacker News" + (" and Reddit" if reddit else ""),
         "description": (f"{meta.get('total', meta['courses']):,} online courses recommended in {meta['comments']:,} public Hacker News "
                         + (f"comments, {SPAN}, and {meta.get('reddit_comments', 0):,} public Reddit comments" if reddit
                            else f"comments, {SPAN}")
                         + ", with rankings, summaries, topics, levels, costs and formats."),
         "url": f"{BASE}/", "sameAs": REPO, "license": "https://creativecommons.org/licenses/by/4.0/",
         "isAccessibleForFree": True, "keywords": ["online courses", "Hacker News", "MOOC", "computer science",
                                                   "programming", "recommendations"],
         "temporalCoverage": f"2006-01-01/{iso(meta['data_end'])}", "dateModified": iso(meta["data_end"]),
         "creator": {"@type": "Organization", "name": NAME, "url": f"{BASE}/"},
         "distribution": [{"@type": "DataDownload", "encodingFormat": "text/plain",
                           "contentUrl": f"{BASE}/llms-full.txt"}]}]}
    if reddit:
        ld["@graph"][1]["isBasedOn"] = (
            [{"@type": "Dataset", "name": name, "url": link} for name, link, _ in HN_CREDITS]
            + [{"@type": "Dataset", "name": "Subreddit comments/submissions 2005-06 to 2023-12 (Watchful1)",
                "url": REDDIT_DUMP}])
    reddit_section = reddit_about(meta) if reddit else ""
    reddit_note = ' Reddit has its own list; see <a href="#reddit">Reddit</a> below.' if reddit else ""
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
  from {SPAN}: {meta['courses']:,} courses drawn from {meta['comments']:,} comments.{reddit_note}</p>

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
{reddit_section}
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


def llms_sources():
    return ["## Sources", "",
            "- Hacker News comments: "
            + "; ".join(f"[{n}]({u})" + (f" ({lic})" if lic else "") for n, u, lic in HN_CREDITS) + ".",
            f"- Reddit comments: the [per-subreddit Reddit dump by Watchful1]({REDDIT_DUMP}) on Academic Torrents "
            "(\"Subreddit comments/submissions 2005-06 to 2023-12\"). No license or terms were published with it; "
            f"the comments belong to their authors under [Reddit's User Agreement]({REDDIT_TERMS}). "
            "Reddit comments are shown as excerpts of at most 300 characters, linked to the original.", ""]


def llms_txt(courses, meta, by_topic, reddit=None):
    """courses/by_topic: the Hacker News ranking. reddit: the Reddit ranking (views), when there is one."""
    reddit = reddit or []
    affiliation = ("Not affiliated with Y Combinator, Hacker News or Reddit." if reddit
                   else "Not affiliated with Y Combinator or Hacker News.")
    out = [f"# {NAME}", "",
           f"> The online courses programmers keep recommending, ranked from {meta['comments']:,} public Hacker News "
           f"comments, {SPAN}: {meta.get('total', meta['courses']):,} courses with a page each.", "",
           "Each course is scored from who recommended it, how strongly, in how many separate threads and for how "
           "many years (one vote per person; replies piling onto one thread are damped). Every course page quotes "
           "the comments behind its ranking and links each one to Hacker News. The catalog, rankings and summaries "
           f"are CC BY 4.0; please cite and link the course page. {affiliation}", ""]
    if reddit:
        out += [f"Reddit has its own ranking, built the same way from {meta.get('reddit_comments', 0):,} public Reddit "
                f"comments. The Hacker News and Reddit rankings are never mixed. {BASE}/reddit/ is the Reddit list.", ""]
    out += ["## Courses by topic", ""]
    for t, s, n in TOPIC_PAGES["hn"]:
        out.append(f"- [{t}]({BASE}/topic/{s}/): {n} courses. Top: "
                   + ", ".join(c["name"] for c in by_topic[t][:5]))
    out += ["", "## Top 30 overall" if not reddit else "## Top 30 on Hacker News", ""] + [course_line(c) for c in courses[:30]]
    if reddit:
        out += ["", "## Top 30 on Reddit", ""] + [course_line(c) for c in reddit[:30]]
    out += ["", "## Optional", "",
            f"- [Every course, one record each]({BASE}/llms-full.txt): rank, links, topic, level, cost, format, "
            "years and summaries for all courses",
            f"- [About and ranking method]({BASE}/about/)",
            f"- [Source code and pipeline]({REPO})", ""]
    if reddit:
        out += llms_sources()
    return "\n".join(out)


def llms_full_txt(courses, meta):
    """courses: merged courses in listing order (Hacker News rank first, then Reddit-only courses)."""
    reddit = bool(meta.get("reddit"))
    both = f" and {meta.get('reddit_comments', 0):,} public Reddit comments" if reddit else ""
    out = [f"# {NAME}: every course", "",
           f"> {meta.get('total', meta['courses']):,} online courses recommended in {meta['comments']:,} public Hacker News comments"
           f"{both}, {SPAN}, in rank order. CC BY 4.0: cite {BASE}/ and link the course page."
           + (" Ranks are per source and never mixed." if reddit else ""), ""]
    for c in courses:
        vs = {src: view(c, src) for src in present(c)}
        facts = "; ".join(f"{k}: {v}" for k, v in (("Topic", c["topic"]), ("Level", c["level"]), ("Cost", c["cost"]),
                                                   ("Format", c["format"])) if v and v != "unknown")
        if reddit:
            out += [f"## {c['name']} ({c['provider']})", "",
                    "Rank: " + " · ".join(f"#{v['rank']} on {SOURCE_NAMES[src]}" for src, v in vs.items())]
            out.append(f"Page: {BASE}/course/{c['slug']}/")
        else:
            v = vs["hn"]
            out += [f"## #{v['rank']} {c['name']} ({c['provider']})", "", f"Page: {BASE}/course/{c['slug']}/"]
        if c["url"]:
            out.append(f"Course website: {c['url']}")
        out.append(facts)
        for src, v in vs.items():
            badges = ", ".join(BADGE[b][0] for b in v["badges"])
            where = f" on {SOURCE_NAMES[src]}" if reddit else ""
            out.append(f"Recommended{where} by {v['recommenders']:,} {'person' if v['recommenders'] == 1 else 'people'} "
                       f"in {plural(v['threads'], 'thread')}, {span(v)}." + (f" Badges: {badges}." if badges else ""))
        if c["tags"]:
            out.append("Tags: " + ", ".join(c["tags"]))
        out += [""] + [p for p in (c["summary"], c["why"] and f"Why people recommend it: {c['why']}") if p] + [""]
    if reddit:
        out += llms_sources()
    return "\n".join(out)


def view(c, source):
    """A course as one source sees it: the shared fields plus that source's stats (rank, score,
    trend, recommenders, threads, first, last, years_active, badges, endorsements, strong_share,
    recent_share) at the top level."""
    return {k: v for k, v in c.items() if k != "sources"} | c["sources"][source]


def remove_reddit_pages(root):
    """Drop the Reddit pages left from an earlier build that had Reddit data."""
    for old in (root / "topic").glob("*/index.html"):
        old.unlink()
    (root / "index.html").unlink(missing_ok=True)
    for d in sorted(root.rglob("*"), reverse=True) if root.exists() else ():
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass
    try:
        root.rmdir()
    except OSError:
        pass


def write_all(courses, comments, data_end, reddit_end=None):
    """courses: build.py's merged courses (shared fields, slug, related, sources). data_end and
    reddit_end: the newest Hacker News and Reddit comment times.

    Every course gets a page (Hacker News ones, then Reddit-only ones). Each source's grid and topic
    pages are rendered from that source's views. The switch and the Reddit pages exist only when some
    course was recommended on Reddit."""
    global REDDIT_COMMUNITIES, REDDIT_SUBS
    merged = {src: sorted((c for c in courses if src in c["sources"]), key=lambda c: c["sources"][src]["rank"])
              for src in SOURCE_NAMES}
    ranked = {src: [view(c, src) for c in cs] for src, cs in merged.items()}
    has_reddit = bool(ranked["reddit"])
    listing = merged["hn"] + [c for c in merged["reddit"] if "hn" not in c["sources"]]
    reddit_comments = [cm for cm in comments if cm.get("src", "hn") == "reddit"]
    comments_in = {"hn": len(comments) - len(reddit_comments), "reddit": len(reddit_comments)}
    if has_reddit:
        seen = {cm["sub"] for cm in reddit_comments if cm.get("sub")}
        REDDIT_SUBS = [s for s in sources.SUBREDDITS if s in seen]
        REDDIT_COMMUNITIES = len(REDDIT_SUBS)
    configure(data_end)
    by_id = {c["id"]: c for c in listing}
    for src in SOURCE_NAMES:
        for i, c in enumerate(merged[src]):
            if present(c)[0] == src:  # baked prev/next follow the course's first source
                c["prev"] = merged[src][i - 1] if i > 0 else None
                c["next"] = merged[src][i + 1] if i + 1 < len(merged[src]) else None
    by_topic = {src: {} for src in SOURCE_NAMES}
    for src, cs in ranked.items():
        for c in cs:
            by_topic[src].setdefault(c["topic"], []).append(c)
        TOPIC_PAGES[src][:] = [(t, topic_slug(t), len(by_topic[src][t]))
                               for t in [name for name, _ in TOPICS] + [OTHER] if t in by_topic[src]]
    ends = {"hn": data_end, "reddit": reddit_end or data_end}
    metas = {src: {"courses": len(ranked[src]), "comments": comments_in[src], "data_end": ends[src],
                   "reddit": has_reddit,
                   "topics": {s: {slug for _, slug, _ in TOPIC_PAGES[s]} for s in SOURCE_NAMES}}
             for src in SOURCE_NAMES}
    meta = dict(metas["hn"])
    if has_reddit:
        years = [year(cm["t"]) for cm in reddit_comments]
        meta |= {"total": len(listing), "reddit_comments": comments_in["reddit"], "reddit_subs": REDDIT_SUBS,
                 "reddit_years": (min(years), max(years))}

    for old in (SITE / "course").glob("*/index.html"):
        old.unlink()
    for c in listing:
        d = SITE / "course" / c["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(course_page(c, comments, by_id, data_end, multi=has_reddit), encoding="utf-8")
    for c in listing:
        c.pop("prev", None), c.pop("next", None)

    for src in SOURCE_NAMES:
        root = SITE / "reddit" if src == "reddit" else SITE
        if src == "reddit" and not has_reddit:
            remove_reddit_pages(root)
            continue
        for old in (root / "topic").glob("*/index.html"):
            old.unlink()
        for t, s, _ in TOPIC_PAGES[src]:
            d = root / "topic" / s
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(topic_page(t, s, by_topic[src][t], metas[src], src), encoding="utf-8")
        root.mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text(index_page(metas[src], ranked[src], src), encoding="utf-8")

    (SITE / "about").mkdir(exist_ok=True)
    (SITE / "about" / "index.html").write_text(about_page(meta), encoding="utf-8")
    (SITE / "404.html").write_text(not_found_page(), encoding="utf-8")
    (SITE / "_headers").write_text(HEADERS, encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    (SITE / "llms.txt").write_text(llms_txt(ranked["hn"], meta, by_topic["hn"], ranked["reddit"]), encoding="utf-8")
    (SITE / "llms-full.txt").write_text(llms_full_txt(listing, meta), encoding="utf-8")

    # lastmod is the newest comment behind each page, so crawlers can trust it and skip unchanged pages.
    def newest(cs):
        return iso(max(comments[ci]["t"] for c in cs for x in c["sources"].values() for ci, _ in x["endorsements"]))

    def newest_in(vs):
        return iso(max(comments[ci]["t"] for v in vs for ci, _ in v["endorsements"]))
    urls = [("/", iso(data_end)), ("/about/", iso(data_end))]
    urls += [(f"/topic/{s}/", newest_in(by_topic["hn"][t])) for t, s, _ in TOPIC_PAGES["hn"]]
    if has_reddit:
        urls.append(("/reddit/", iso(ends["reddit"])))
        urls += [(topic_url("reddit", s), newest_in(by_topic["reddit"][t])) for t, s, _ in TOPIC_PAGES["reddit"]]
    urls += [(f"/course/{c['slug']}/", newest([c])) for c in listing]
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{m}</lastmod></url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
