# Hacker Courses

**The online courses programmers keep recommending, ranked from public Hacker News comments since 2006.**

1,376 courses drawn from 3,371 recommendation comments, 2006 to October 2026, in a fast, static,
keyboard-navigable site. No accounts, no cookies, no backend. Live at
**[hackercourses.com](https://hackercourses.com)**.

Dedicated to [Andrej Karpathy](https://x.com/karpathy), whose idea prompted
[HackerTube](https://hackertube.org), the collection of videos programmers keep telling each other
to watch. Hacker Courses applies that idea to courses.

Not affiliated with Y Combinator, Hacker News or Reddit; they are credited only as data sources.

## Features

- **Two sources:** a Hacker News list and, separately, a Reddit list (`/reddit/`), each ranked on its
  own and never mixed. Switch between them at the top of the grid.
- **Views:** Best, Trending, Hidden gems, Evergreen, Saved.
- **Filters:** topic, level, cost, format, era; several sort orders; instant search.
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
  Visits are counted with cookieless analytics; nothing else is loaded from outside the site.

## How it works

Public Hacker News comments are filtered for genuine course recommendations (spam and self-promotion
are dropped), reviewed by a language model, and merged so that different spellings of the same course
("SICP lectures", "6.001", "Abelson & Sussman") become one entry. Each course then gets a short summary
and a ranking, and everything is rendered into static pages in `site/`.

**Ranking** favours courses recommended by many different people, in many separate discussions, over
many years. Strong endorsements count for more than passing mentions, each person counts once, and a
pile-on in a single thread counts for less than independent threads.

**Reddit** comments from a set of subreddits go through the same steps, with one addition: a comment's
upvotes count (up to twice), and Reddit comments are shown only as short excerpts linking to the original.

**Sources:** [nixiesearch/hackernews-comments](https://huggingface.co/datasets/nixiesearch/hackernews-comments)
(Apache-2.0), [open-index/hacker-news](https://huggingface.co/datasets/open-index/hacker-news) (ODC-By),
the [HN Search API](https://hn.algolia.com/api) and the official [HN API](https://github.com/HackerNews/API).
Reddit: the per-subreddit dump by Watchful1 on
[Academic Torrents](https://academictorrents.com/details/56aa49f9653ba545f48df2e33679f014d2829c10)
(2005 to 2023; no license published, comments belong to their authors under
[Reddit's User Agreement](https://www.redditinc.com/policies/user-agreement)). See [`NOTICE`](NOTICE).

## Run it yourself

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/). The AI steps use
[OpenRouter](https://openrouter.ai); put your key in a git-ignored `.env` as `OPEN_ROUTER_API_KEY`.

```bash
uv sync
uv run pytest -q tests
uv run python pipeline/serve.py 8765   # preview the committed site
```

The Reddit list runs the same steps with `--source reddit`, in this order:

```bash
uv run python pipeline/fetch_reddit.py --raw <folder of dump files>
uv run python pipeline/classify.py --source reddit
uv run python pipeline/review.py --source reddit
uv run python pipeline/review.py --source reddit --recheck-spam
uv run python pipeline/classify.py --source reddit
uv run python pipeline/canonicalize.py --source reddit
uv run python pipeline/canonicalize.py --dedupe-reddit
uv run python pipeline/summarize.py --source reddit
uv run python pipeline/build.py
```

`build.py` renders both lists, and the Reddit pages exist only once Reddit data does.

The pipeline lives in `pipeline/`, one script per step, from `fetch.py` to `build.py`. Every step is
resumable and only processes what is new.

## Contributing and removal requests

Issues and pull requests are welcome. If you wrote a comment quoted on the site and want it removed,
[open a removal request](https://github.com/dciconi/hackercourses/issues/new?template=removal.yml).
Removed comments stay excluded from future data refreshes.

## License

- **Code and original artwork:** [MIT](LICENSE).
- **Generated data** (catalog, rankings, summaries, facets, stance labels):
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Hacker News and Reddit comments** quoted on the site remain their authors' and are not licensed by this
  project; Reddit comments appear only as excerpts.
  Course images are hotlinked and belong to the course providers.
- Source datasets and their licenses (Apache-2.0, ODC-By; none published for the Reddit dump) are credited in
  [`NOTICE`](NOTICE).

Details in [`DATA-LICENSE.md`](DATA-LICENSE.md). The "Hacker Courses" name and logo are not licensed;
forks should use their own name.
