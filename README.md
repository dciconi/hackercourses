# Hacker Courses

**The online courses programmers keep recommending, ranked from public Hacker News comments since 2006.**

1,376 courses drawn from 3,371 recommendation comments, 2006 to October 2026, in a fast, static,
keyboard-navigable site. No accounts, no cookies, no backend. Live at
**[hackercourses.com](https://hackercourses.com)**.

Dedicated to [Andrej Karpathy](https://x.com/karpathy), whose idea prompted
[HackerTube](https://hackertube.org), the collection of videos programmers keep telling each other
to watch. Hacker Courses applies that idea to courses.

Not affiliated with Y Combinator or Hacker News; Hacker News is credited only as the data source.

## Features

- **Views:** Best, Trending, Hidden gems, Evergreen, Saved.
- **Filters:** topic (13), level, cost, format, era; five sort orders; instant search.
- **A page per course:** summary, why people recommend it, a by-year timeline, every comment with its
  stance and thread, related courses, and a link to the course.
- **Badges:** Classic, Evergreen, Rising, Hidden gem.
- **Fully keyboard-driven** (press `?` on the site):

  | Where | Keys |
  |---|---|
  | Grid | arrows, Home/End, Ctrl+Home/End, PgUp/PgDn move · Enter opens · S saves · 1–5 views · `[` `]` topics |
  | Course page | ← → previous/next course in your list · S saves · O opens the course site · Esc back |
  | Anywhere | `/` search · T light/dark theme · `?` help |

- **Private by design:** saved courses, seen markers and the theme live in your browser's storage only.

## How it works

```
HN comments ──► prefilter ──► rules ──► AI review ──► merge course names ──► per-course summaries
 (1.13M candidates)          (spam,       (does it        (one entry per          (stance of every
                              "recommends   really          course; rule            comment, facets,
                              a course?")   recommend?)     vetoes)                 best link)
                                                                    │
                     images (course pages, verified) ◄──────────────┤
                                                                    ▼
                                         ranking + static pages ──► site/
```

**Sources.** [nixiesearch/hackernews-comments](https://huggingface.co/datasets/nixiesearch/hackernews-comments)
(Apache-2.0) for 2006 to October 2024, streamed without saving the 6.3 GB dump;
[open-index/hacker-news](https://huggingface.co/datasets/open-index/hacker-news) (ODC-By) monthly
Parquet files, read column-wise with DuckDB, for October 2024 to August 2026; the
[HN Search API](https://hn.algolia.com/api) for the weeks after; and the official
[HN API](https://github.com/HackerNews/API) for thread titles.

**Filtering.** Keyword rules drop dead/deleted items, coupon, affiliate and referral links, URL
shorteners, self-promotion, copy-paste duplicates and accounts posting the same course link five or more
times, and keep comments where an endorsement sits next to a *specific* course. An AI review then decides
whether each comment really recommends a course and names it. Paid third-party courses that the first
model flags as self-promotion get a second opinion from a stronger model.

**One entry per course.** Thousands of spellings ("SICP lectures", "6.001", "Abelson & Sussman")
collapse into one course. Rules pre-merge identical titles, a model maps the rest onto a growing catalog,
and a final pass merges leftovers. Rule-based vetoes overrule the model: different part numbers (I vs II),
a specialization vs a single course, different course codes (checked across every spelling), or a MOOC vs
the campus course it grew out of (Coursera *Machine Learning* is not Stanford *CS229*) never merge.

**Images.** Each course page's own preview image (or a YouTube thumbnail via oEmbed), downloaded once to
check it is real; page images must be clearly landscape and never come from staff/people paths. For dead
links, a model suggests the current course page, used only if its title matches the course, then the
Internet Archive's copy. Images are hotlinked, never re-hosted; courses without one get an original
illustration for their topic.

## Ranking

Comment karma is not public, so [`pipeline/rank.py`](pipeline/rank.py) scores each course from who
recommended it, how strongly, in how many separate discussions and for how long:

1. **Stance** of each comment: strongly recommends 1.0, recommends 0.7, mentions 0.25, criticizes 0.
2. **One vote per person**, at their strongest stance.
3. **Pile-ons are damped:** within one thread, votes decay 1, ½, ¼…, so ten replies in one thread count
   for less than two independent threads.
4. **Staying power:** +8% for each extra calendar year with a recommendation.

**Trending** uses the same votes with a two-year half-life. **Badges:** Classic (top-ranked,
recommended across 8+ years), Evergreen (6+ distinct years), Rising (most support in the last three
years), Hidden gem (2–4 recommenders, nearly all emphatic).

## Run it yourself

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/). The AI steps use
[OpenRouter](https://openrouter.ai); put your key in a git-ignored `.env`:

```bash
uv sync
echo "OPEN_ROUTER_API_KEY=sk-or-..." > .env
```

**Full build** (a few hours, mostly downloads; about $2 of model calls):

```bash
uv run python pipeline/fetch.py              # 2006 to Oct 2024 -> data/candidates.jsonl
uv run python pipeline/fetch_recent.py       # Oct 2024 to today
uv run python pipeline/classify.py           # rules -> data/pool.json
uv run python pipeline/review.py             # AI review -> data/llm_labels.jsonl
uv run python pipeline/review.py --recheck-spam
uv run python pipeline/classify.py           # apply verdicts -> data/courses.json
uv run python pipeline/threads.py            # thread titles (second pass over the dump)
uv run python pipeline/threads.py --missing  # thread titles for newer comments
uv run python pipeline/canonicalize.py       # one entry per course -> data/catalog.json
uv run python pipeline/canonicalize.py --dedupe
uv run python pipeline/summarize.py          # summaries, facets, stances -> data/summaries.jsonl
uv run python pipeline/images.py             # course preview images -> data/images.json
uv run python pipeline/discover_images.py    # images for courses with dead links
uv run python pipeline/placeholders.py       # topic illustrations and social cards
uv run python pipeline/build.py              # ranking + every page -> site/
```

**Refresh with new comments** (minutes; about $0.30): run `fetch_recent.py`, then the same steps from
`classify.py` on, skipping `threads.py` without `--missing`. Every step is resumable and only processes
what is new: unseen comments, unmapped names, courses whose comments changed.

**Preview** with the same headers and 404 handling as Cloudflare Pages, and **test**:

```bash
uv run python pipeline/serve.py 8765
uv run pytest -q tests
```

### Models and cost

| Step | Model | Why | Cost (runs behind the current data) |
|---|---|---|---|
| review (6,253 comments) | `anthropic/claude-haiku-5.5`, low effort | high volume, simple judgement | $0.65 |
| spam recheck | `anthropic/claude-sonnet-5.5` | Haiku over-flags paid third-party courses | $0.32 |
| canonicalize | Haiku 5.5 | mapping names onto a growing catalog | $0.23 |
| dedupe | Sonnet 5.5, medium effort | one judgement-heavy pass over the whole catalog | $0.17 |
| summarize (1,534 + 194 courses) | Haiku 5.5 | per-course blurbs and stances | $0.43 |
| image discovery | Haiku 5.5 | suggesting current course pages | $0.04 |

## Repository layout

```
pipeline/   data pipeline, ranking (rank.py), page generator (pages.py), local server (serve.py)
site/       the deployable site, generated by build.py and committed
  index.html, courses.js, app.js     the grid (card data only, ~285 KB gzipped)
  course/<slug>/index.html, course.js one pre-rendered page per course
  about/, 404.html, sitemap.xml, robots.txt
  _headers                           security headers (strict CSP) and caching
  common.js, style.css, img/         shared script, styles, topic art, social cards
tests/      ranking properties, merge vetoes, image page matching
data/       working data (git-ignored; rebuilt by the pipeline)
```

## Hosting

Static hosting on [Cloudflare Pages](https://pages.cloudflare.com), connected to this repository:
production branch `main`, framework preset *None*, no build command, build output directory `site`.
Every push to `main` deploys to [hackercourses.com](https://hackercourses.com). The domain is
registered at Namecheap and uses Cloudflare's nameservers.

## Contributing and removal requests

Issues and pull requests are welcome. If you wrote a comment quoted on the site and want it removed,
[open a removal request](https://github.com/dciconi/hackercourses/issues/new?title=Removal%20request&labels=removal).

## License

- **Code and original artwork:** [MIT](LICENSE).
- **Generated data** (catalog, rankings, summaries, facets, stance labels):
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Hacker News comments** quoted on the site remain their authors' and are not licensed by this project.
  Course images are hotlinked and belong to the course providers.
- Source datasets and their licenses (Apache-2.0, ODC-By) are credited in [`NOTICE`](NOTICE).

Details in [`DATA-LICENSE.md`](DATA-LICENSE.md). The "Hacker Courses" name and logo are not licensed;
forks should use their own name.
