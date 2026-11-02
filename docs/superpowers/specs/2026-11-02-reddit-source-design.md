# Reddit as a second source — design

Date: 2026-11-02 · Status: draft for approval

## Intent

Hacker Courses ranks online courses from Hacker News comments. HN mostly covers programming, so the
library stops at programming. Adding Reddit, and specifically communities about business, AI,
productivity and marketing, widens the library past programming while staying a **course** library.

The two sources are **never mixed into one ranking**. Each one has its own ranking, and a visible
HN | Reddit switch picks which one you're browsing. The reader always knows whose recommendations
they're looking at. Normalizing scores across sources is explicitly out of scope.

## Goals

- A complete Reddit ranking, built from the 30 subreddits below, with the same views, filters,
  search, badges and keyboard behaviour as the HN ranking.
- A switch between the two rankings that is obvious, remembered per browser, and crawlable.
- One page per course. A course recommended on both sites shows both, in clearly separate sections.
- The SEO work from `b976ef1` (crawlable grid, topic pages, JSON-LD, llms.txt, sitemap lastmod)
  extends to the Reddit side and doesn't regress for HN.

## Non-goals

- Books, YouTube channels, podcasts, apps, newsletters. Courses only, as today.
- Any combined or "overall" ranking across sources.
- Subreddits outside the list below (the list can grow later; the pipeline should make that a config
  change).

## Anti-goals (a failure even if it works)

- Reddit rankings visible only after JavaScript runs (invisible to search engines and LLM crawlers).
- Reddit volume swamping HN: the HN side must look and rank exactly as it does now. Reddit-only
  courses never appear in the HN ranking, and vice versa.
- Reproducing Reddit comments in bulk. Reddit content is under Reddit's terms, and Reddit
  litigates over scraping. Show short excerpts with a link back, not full comment text.
- The Reddit side filling up with guru/course-seller promotion (r/Entrepreneur, r/SaaS, marketing
  subs are full of people selling courses). Spam/self-promotion filtering must be at least as strict
  as for HN.

## Subreddits (user's list)

| Group | Subreddits |
|---|---|
| Business & entrepreneurship | Entrepreneur, startups, smallbusiness, SaaS, indiehackers, EntrepreneurRideAlong |
| Software development | programming, ExperiencedDevs, webdev, learnprogramming, Python, ~~selfhosted~~ |
| AI & ML | MachineLearning, LocalLLaMA, artificial, ChatGPT, ClaudeAI, learnmachinelearning |
| Productivity | productivity, getdisciplined, Notion, ~~ObsidianMD~~, PKMS, ~~bujo~~ |
| Marketing & growth | marketing, PPC, SEO, ~~bigseo~~, ~~socialmedia~~, ~~Emailmarketing~~ |

Struck-through subreddits (bujo, socialmedia, bigseo, ObsidianMD, selfhosted, Emailmarketing) were
dropped after the 2021–2023 pilot (owner decision, 2026-11-02); 24 remain configured. `classify.py --source reddit`
discards any row from a subreddit not in the configured list.

Kept as a list in one config file. Each Reddit comment keeps its subreddit, and course pages show it
("r/learnprogramming, 2023").

## What the reader sees

- **Header switch**: a two-option control, `Hacker News | Reddit`, next to the views. It is a pair
  of links, not a JS-only toggle:
  - HN ranking stays at `/` and `/topic/<slug>/` (unchanged URLs).
  - Reddit ranking lives at `/reddit/` and `/reddit/topic/<slug>/`.
  - The last choice is remembered in localStorage (`hc.source`). Landing on `/` with `reddit`
    remembered redirects client-side to `/reddit/`, except when arriving from an explicit switch
    click. First visit defaults to HN.
- **Grid**: identical behaviour on both sides (views Best / Trending / Hidden gems / Evergreen /
  Saved, filters, sorts, search, keyboard). Ranks, scores, recommender counts and badges are the
  chosen source's. Saved is shared across sources (it's a list of courses, not of rankings).
- **Taglines and headings** name the source: e.g. "The online courses Redditors keep recommending,
  ranked from N public comments in 30 communities" vs today's HN line.
- **Course page** (one URL, `/course/<slug>/`, unchanged):
  - The header shows the rank and stats for each source the course appears in, e.g.
    "#12 on Hacker News · #340 on Reddit". A course in one source shows only that one.
  - The summary/why/facets stay shared (one catalog entry per course).
  - The comment list splits into "On Hacker News (n)" and "On Reddit (n)". HN comments render as
    today. Reddit comments show the stance, author, subreddit, year, thread title, the upvote score,
    an excerpt of at most ~300 characters (cut at a sentence/word boundary), and "Open on Reddit ↗".
  - The timeline shows both sources (two bar rows, or stacked, builder's call).
  - Prev/next (← →) follows the list the reader came from, as now; within the chosen source.
  - Related courses: unchanged logic, computed on the union.
- **About page**: a Reddit section explaining the source, the subreddit list, and how the Reddit
  score differs (upvotes count, see Ranking).

## Ranking

Reuse `rank.py` unchanged for HN. For Reddit, the same pipeline (stance weight, one vote per
person at their strongest, pile-on damping per thread, +8% per extra year, trending half-life) with
**one addition: the comment's upvote score scales its vote**, since Reddit makes it public and it is
real community agreement.

- Vote weight = stance weight × upvote factor, where the factor is log-scaled and capped so one viral
  comment can't carry a course: e.g. `1 + min(1, log10(max(score, 1)) / 3)` (1× at 1 point, 2× at
  1000+). Comments at score ≤ 0 count with stance weight × 0.5. Exact constants are the builder's call;
  the test is that rankings look sane on the pilot data.
- "One vote per person" keeps the author's strongest *weighted* vote.
- Thread = the Reddit submission (`link_id`).
- Badge thresholds: the Reddit side has less history depth for most subs (many are post-2015), so
  Classic/Evergreen thresholds may need to be per-source. Builder's call, tuned on real data.
- Ranks are computed per source over that source's courses only. A course's `rank`, `score`,
  `trend`, `recommenders`, `threads`, `first`, `last`, `years_active`, `badges` exist per source.

## Data and pipeline

**Getting the data (builder verifies current availability before committing):**

1. Bulk history: the per-subreddit comment + submission dumps on Academic Torrents (Watchful1's
   "Reddit comments/submissions … top 40k subreddits", zst NDJSON). Download only the 30 subreddits'
   files. Fallback: `open-index/arctic` monthly Parquet on Hugging Face (1.3 TB, not partitioned by
   subreddit; slow but uses the DuckDB approach `fetch_recent.py` already has).
2. Months after the dump ends: the Arctic Shift API (`arctic-shift.photon-reddit.com`), one subreddit
   at a time, with backoff. In testing it rate-limits hard ("Timeout. Maybe slow down a bit") and
   returns 422 on body searches in big subs, so page by date instead of full-text search, and filter
   locally.
3. Thread titles come from the submissions files/API, not a second pass.

History: everything the dumps have for these subs (oldest r/programming goes back to 2006).
Downloads stay out of git, like `data/` today.

**Pipeline**: each existing step learns a `source` field (`hn` | `reddit`) instead of a parallel copy
of every script:

- `fetch_reddit.py` (new) → `data/reddit_candidates.jsonl`, same row shape as HN candidates plus
  `source`, `subreddit`, `score`, `link_id`, and Reddit's string id (`t1_…`). Prefilter with the same
  course-word / course-host rules so only plausible comments are kept.
- `classify.py`: Reddit markdown → text (Reddit uses markdown, not HN's HTML; quoting is `>` in both),
  same rules and spam filter. Add Reddit-specific spam patterns (e.g. "check my profile", "DM me for
  the link", course-seller boilerplate).
- `review.py`: the prompt names the source ("Reddit comments in r/…") so the model judges in context.
- `canonicalize.py`: Reddit names map onto the **same catalog** as HN. Vetoes unchanged.
- `summarize.py`: one summary per course from both sources' comments (capped as now).
- `build.py`: rank per source; write `courses.js` (HN grid) and `reddit/courses.js` (Reddit grid),
  each with only that source's courses and per-source rank fields; course pages get both.
- `pages.py`: index/topic pages parameterized by source; course page sections per source; About,
  footer credits, `llms.txt`/`llms-full.txt` (one section per source), sitemap with the new URLs;
  JSON-LD ItemLists per source; course titles/descriptions name the sources the course appears in.
- `removals.py`: accept Reddit ids/usernames as well as HN (ids are strings, not ints).

**Topics**: the current 13 topics have no home for productivity or marketing courses. Add
"Productivity & Personal Development" and "Marketing & Growth" (with regexes), and make sure
"Business, Finance & Economics" doesn't swallow marketing. This also re-buckets a few HN courses;
that's acceptable.

## Documenting the sources

Every source the Reddit side uses is credited with a link and its terms, the way HN's are today, in
**all** of these places: README (Sources paragraph, pipeline diagram, run steps, cost table), About
page (new Reddit section), site footer, `llms.txt`/`llms-full.txt` headers, the About page's Dataset
JSON-LD (`isBasedOn`), and `DATA-LICENSE.md`.

Sources to credit (builder confirms the exact names, URLs and terms when wiring them up):

| Source | Used for | Terms to state |
|---|---|---|
| Reddit (reddit.com), the 30 subreddits listed | the comments themselves | content belongs to its authors under [Reddit's User Agreement](https://www.redditinc.com/policies/user-agreement); not affiliated with Reddit |
| [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift) | archive and API for recent months | the project's stated research terms |
| Academic Torrents per-subreddit dumps (Watchful1) | bulk history | as published with the torrent |
| [open-index/arctic](https://huggingface.co/datasets/open-index/arctic) | fallback bulk history, if used | as on its dataset card |

Also: list the subreddits on the About page, link each Reddit comment to its permalink, and say
plainly that Reddit comments are shown as excerpts. If a source is evaluated but not used, leave it
out of the credits.

## Rollout

1. **Pilot**: 2–3 years (2023–2025) of all 30 subs through the pipeline, no site changes. Look at the
   top 50 Reddit courses and the spam rate per subreddit before going further. Subreddits that
   produce almost no real course recommendations get dropped from the list (with the user's OK).
2. Full history + site changes.
3. A refresh path like `fetch_recent.py` for Reddit, run alongside the HN refresh.

## Constraints

- Static site on Cloudflare Pages, everything committed; no backend, no cookies; strict CSP stays.
- Grid payload per source should stay in the range of today's (~285 KB gzipped). If Reddit is much
  bigger, trim card fields, not the CSP or static model.
- Model costs: same models as now (Haiku for volume, Sonnet for rechecks/dedupe). Estimate cost on the
  pilot and report it before the full run.
- `uv` for everything Python.
- Not affiliated with Reddit; no Reddit branding beyond the name and the source credit.

## Decided by the user

- Courses only; add Reddit; separate rankings with a switch, no normalization.
- One course page per course, both sources shown separately.
- Same views/filters on both sides; HN is the default; the switch is remembered.
- Upvotes count in the Reddit ranking.
- Short excerpts + link for Reddit comments, not full text.
- The 30 subreddits above.
- **Archive as-is.** No Reddit API account and no live checks for comments deleted after archiving;
  comments already marked `[deleted]`/`[removed]` in the archive are dropped, and `removals.txt` handles
  requests, as for HN.
- **Paid creator/influencer courses and vendor certificates count** (e.g. Building a Second Brain, a
  Maven cohort, Google Ads or HubSpot certification) when the recommendation is genuine, not paid
  marketing. The review step rejects comments that look like paid promotion: the author selling or
  affiliated with the course, affiliate/referral links, sponsored or astroturf patterns (fresh
  accounts, the same course pushed across threads, copy-paste praise). When unsure on a paid course,
  the stronger-model recheck decides, as for HN today.

## My calls (flagged for review)

- Crawlable `/reddit/…` URLs instead of a JS-only toggle (because of the SEO work).
- Full available history, after a 2023–2025 pilot.
- Upvote factor formula and the halved weight for ≤0-score comments.
- Two new topics: Productivity & Personal Development, Marketing & Growth.
- Saved list shared across sources.
- Data via Academic Torrents per-subreddit dumps + Arctic Shift API for recent months.

## Settled after the builder check (my calls)

- **Course detection widened for Reddit only.** `COURSE_HOSTS` / `NAMED_COURSE` get Reddit-only
  additions (e.g. HubSpot Academy, Google Skillshop / Digital Garage, Maven, Teachable/Kajabi/Podia
  hosts, named programs like Building a Second Brain). HN rules stay exactly as they are.
- **HN stays frozen.** Stances are stored and capped per source (30 HN + 30 Reddit comments per
  course in the summarizer), so Reddit never pushes HN comments out. Courses that already have a
  summary keep their summary, topic, level, cost, format and URL; only new courses get summarized.
  Catalog dedupe may merge a new Reddit entry into an existing one, never two existing HN entries
  into each other. The only accepted HN change is the topic re-bucketing from the two new topics.
- **Young-comment scores.** The upvote factor applies only to comments captured at least 30 days
  after posting (archive `retrieved_on` minus `created_utc`); younger comments get factor 1. This
  keeps Trending and Rising from being biased against recent months.
- **Page count.** Cloudflare Pages free tier allows about 20,000 files per deployment. A Reddit-only
  course gets a page only with at least 2 recommenders; raise that threshold if the pilot projects
  more than ~15,000 files in total. Courses below it stay out of the Reddit ranking too.

## Left to the builder

Exact constants and badge thresholds, Reddit-specific spam patterns, timeline rendering, file layout
of new scripts, excerpt length within ~300 chars, torrent tooling.
