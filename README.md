# Hacker Courses

The online courses programmers keep recommending, ranked from 18 years of public Hacker News
comments (2006 – Sep 2024). A static, keyboard-navigable site: no accounts, no backend, no build step.
Domain: hackercourses.com (not deployed yet).

No YC or HN logos or names are used as branding; Hacker News is credited only as the data source,
and the footer states the site is not affiliated with either.

## Pipeline

```bash
uv run python pipeline/fetch.py          # stream nixiesearch/hackernews-comments (~6.3 GB zstd), keep course mentions -> data/candidates.jsonl
uv run python pipeline/classify.py       # rules: spam filter + "recommends a course" -> data/pool.json, data/courses.json
uv run python pipeline/review.py         # LLM: does each comment really recommend a course? -> data/llm_labels.jsonl
uv run python pipeline/review.py --recheck-spam
uv run python pipeline/classify.py       # apply the verdicts -> data/courses.json
uv run python pipeline/threads.py        # second dataset pass: thread title for every comment -> data/threads.json
uv run python pipeline/canonicalize.py   # LLM: merge name variants into one course -> data/catalog.json
uv run python pipeline/canonicalize.py --dedupe
uv run python pipeline/summarize.py      # LLM per course: summary, facets, best link, stance of each comment -> data/summaries.jsonl
uv run python pipeline/images.py         # preview image per course (og:image / YouTube thumbnail), checked -> data/images.json
uv run python pipeline/placeholders.py   # one original illustration per topic -> site/img/topics/*.svg
uv run python pipeline/build.py          # ranking, badges, related courses -> site/data.js
uv run pytest -q tests
```

Every LLM step reads `OPEN_ROUTER_API_KEY` from `.env` (git-ignored), uses a strict JSON schema, and is
resumable. Fetch and thread passes never write raw shards to disk.

**Images.** `images.py` uses the preview image each course page publishes for link sharing (or a
YouTube video thumbnail), only after downloading it once to confirm it is a real landscape image of
at least 300x150; pictures shared by 3+ courses (site-wide defaults) are dropped. The site hotlinks
them with no referrer and swaps to the topic illustration if one fails to load. These images belong to
the course providers; nothing is re-hosted. The 13 topic illustrations are original line art.

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

`site/` is self-contained (`index.html`, `style.css`, `app.js`, `data.js`). Open `site/index.html`
directly or serve it:

```bash
uv run python -m http.server 8765 --directory site
```

Views: Best, Trending, Hidden gems, Evergreen, Saved. Filters: topic, level, cost, format, era; five
sort orders. Each course has its own page (`#/course/<id>`) with summary, a by-year timeline, every
comment with its stance and thread, and related courses. Saved/seen courses and the theme are kept in
`localStorage` only.

Keys: arrows move, Home/End, Ctrl+Home/End, PgUp/PgDn, Enter opens, S saves, 1–5 views, `[` `]` topics,
`/` search, T theme, `?` help; on a course page ← → previous/next course, O opens the course site,
Esc goes back.
