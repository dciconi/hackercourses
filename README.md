# Hacker Courses

The online courses programmers keep recommending, ranked from public Hacker News comments since 2006
(refreshed up to the run date). A static, keyboard-navigable site: no accounts, no backend, no build step.
Domain: hackercourses.com (not deployed yet).

No YC or HN logos or names are used as branding; Hacker News is credited only as the data source,
and the footer states the site is not affiliated with either.

## Pipeline

```bash
uv run python pipeline/fetch.py          # stream nixiesearch/hackernews-comments (~6.3 GB zstd, to Oct 2024), keep course mentions -> data/candidates.jsonl
uv run python pipeline/fetch_recent.py   # newer comments: open-index/hacker-news Parquet (via DuckDB) + HN Search API for the last weeks
uv run python pipeline/classify.py       # rules: spam filter + "recommends a course" -> data/pool.json, data/courses.json
uv run python pipeline/review.py         # LLM: does each comment really recommend a course? -> data/llm_labels.jsonl
uv run python pipeline/review.py --recheck-spam
uv run python pipeline/classify.py       # apply the verdicts -> data/courses.json
uv run python pipeline/threads.py        # second dataset pass: thread title for every comment -> data/threads.json
uv run python pipeline/threads.py --missing  # thread titles for comments added by fetch_recent.py
uv run python pipeline/canonicalize.py   # LLM: merge name variants into one course -> data/catalog.json
uv run python pipeline/canonicalize.py --dedupe
uv run python pipeline/summarize.py      # LLM per course: summary, facets, best link, stance of each comment -> data/summaries.jsonl
uv run python pipeline/images.py         # preview image per course (og:image / YouTube thumbnail), checked -> data/images.json
uv run python pipeline/discover_images.py  # second pass: verified current course pages, then archived copies of dead links
uv run python pipeline/placeholders.py   # one original illustration per topic -> site/img/topics/*.svg
uv run python pipeline/build.py          # ranking, badges, related courses, all pages -> site/
uv run pytest -q tests
```

Every LLM step reads `OPEN_ROUTER_API_KEY` from `.env` (git-ignored), uses a strict JSON schema, and is
resumable. Fetch and thread passes never write raw shards to disk.

**Images.** `images.py` uses the preview image each course page publishes for link sharing (YouTube
videos and playlists via YouTube's public oEmbed endpoint), else the first large image on the page.
Each image is downloaded once to confirm it is real and at least 300px wide; plain page images must
also be clearly landscape and not come from people/staff paths, so headshots never slip in.
`discover_images.py` handles courses whose posted links are dead: Haiku suggests likely current course
pages, used only when the page title matches the course (75% of its key words, or the same course
code; tested in `tests/test_discover_images.py`), then falls back to the Internet Archive's copy of the
posted link. Pictures shared by 3+ courses (site-wide defaults) are dropped. The site hotlinks images
with no referrer and swaps to the topic illustration if one fails to load. These images belong to the
course providers; nothing is re-hosted. The 13 topic illustrations are original line art.

### Models and cost

| Step | Model | Why | Cost |
|---|---|---|---|
| review (5,928 comments) | `anthropic/claude-haiku-5.5`, low effort | high volume, simple yes/no judgement | $0.61 |
| spam recheck (149) | `anthropic/claude-sonnet-5.5` | Haiku over-flags paid third-party courses | $0.27 |
| canonicalize (~2.7k names) | Haiku 5.5 | mapping names onto a growing catalog | ~$0.20 |
| dedupe (1 call) | Sonnet 5.5, medium effort | one judgement-heavy pass over the whole catalog | ~$0.08 |
| summarize (~1.5k courses) | Haiku 5.5 | per-course blurbs and stances | see `data_summarize.log` |

### What each step decides

`classify.py` (rules, no key): drops dead/deleted items, coupon/affiliate/referral links, URL shorteners,
self-promotion, copy-paste duplicates and accounts posting the same course link 5+ times; keeps comments
where an endorsement sits next to a *specific* course (course-site link, known name, course code).

`review.py`: the model's verdict decides the final comment set and names the courses in each comment.

`canonicalize.py`: rules pre-merge identical titles, the model maps the rest onto a catalog, and a final
Sonnet pass merges leftovers. Rule-based vetoes overrule the model: different part numbers (I vs II),
a specialization vs a single course, different course codes, or a MOOC vs the campus course it grew out of
(Coursera *Machine Learning* is not Stanford *CS229*) never merge. Tested in `tests/test_canonicalize.py`.

## Ranking

Comment karma is not public, so `pipeline/rank.py` scores each course from who recommended it, how
strongly, in how many separate discussions and for how long:

1. **Stance** per comment (from the summarize pass): strongly recommends 1.0, recommends 0.7,
   mentions 0.25, criticizes 0.
2. **One vote per person**, at their strongest stance.
3. **Pile-on damping**: inside one thread votes decay 1, ½, ¼…, so ten replies in one thread count for
   less than two independent threads.
4. **Staying power**: +8% for each extra calendar year with a recommendation.

**Trending** uses the same votes with a two-year half-life back from the newest comment.
Badges: *Classic* (top-ranked, recommended across 8+ years), *Evergreen* (6+ distinct years),
*Rising* (most support in the last three years), *Hidden gem* (2–4 recommenders, nearly all emphatic).
Properties are tested in `tests/test_rank.py`.

## Site

`site/` is the whole deployable site, fully static and committed; `build.py` (via `pipeline/pages.py`)
generates it:

- `index.html` + `courses.js` (card data only, ~275 KB gzipped) + `app.js`: the grid
- `course/<slug>/index.html`: one pre-rendered page per course (summary, by-year timeline, every comment
  with its stance and thread, related courses, schema.org `Course` data, social preview tags) + `course.js`
- `about/` (dedication, ranking method, removal requests), `404.html`, `sitemap.xml`, `robots.txt`
- `_headers`: security headers (strict CSP: no inline scripts or styles) and image caching
- `common.js`: theme, keyboard help and storage shared by every page

Preview locally with the same headers and 404 handling Cloudflare Pages applies:

```bash
uv run python pipeline/serve.py 8765
```

Views: Best, Trending, Hidden gems, Evergreen, Saved. Filters: topic, level, cost, format, era; five
sort orders. Saved/seen courses and the theme are kept in `localStorage` only; the grid's current list
is kept in `sessionStorage` so course pages can step through it and Back returns to the same card.

## Hosting

Cloudflare Pages, connected to this repo: production branch `main`, framework preset *None*, build
command empty, build output directory `site`. Every push to `main` deploys. The domain
hackercourses.com is registered at Namecheap; its nameservers point to Cloudflare.

Keys: arrows move, Home/End, Ctrl+Home/End, PgUp/PgDn, Enter opens, S saves, 1–5 views, `[` `]` topics,
`/` search, T theme, `?` help; on a course page ← → previous/next course, O opens the course site,
Esc goes back.

## License

- **Code and original artwork**: [MIT](LICENSE).
- **Generated data** (catalog, rankings, summaries, facets, stance labels): CC BY 4.0.
- **Hacker News comments** quoted on the site remain their authors' and are not licensed by this
  project; removal requests via GitHub issues. Course images are hotlinked and belong to the providers.
- Source datasets and their licenses (Apache-2.0, ODC-By) are credited in [`NOTICE`](NOTICE).

Details in [`DATA-LICENSE.md`](DATA-LICENSE.md). The "Hacker Courses" name and logo are not licensed;
forks should use their own name.
