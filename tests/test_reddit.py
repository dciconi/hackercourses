import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import reddit  # noqa: E402
import sources  # noqa: E402

DAY = 86400


def raw(**kw):
    base = {"id": "abc", "author": "u1", "created_utc": 1_700_000_000, "retrieved_on": 1_700_000_000 + 40 * DAY,
            "body": "Highly recommend the Coursera course", "subreddit": "learnprogramming", "score": 12,
            "link_id": "t3_xyz"}
    return {**base, **kw}


def test_candidate_shapes_a_comment():
    r = raw()
    assert reddit.candidate(r) == {"id": "t1_abc", "by": "u1", "time": 1_700_000_000, "text": r["body"],
                                   "src": "reddit", "sub": "learnprogramming", "ups": 12, "age": 40 * DAY,
                                   "thread": "t3_xyz"}


def test_age_falls_back_to_retrieved_utc_then_none():
    r = raw(retrieved_utc=1_700_000_000 + 5 * DAY)
    del r["retrieved_on"]
    assert reddit.candidate(r)["age"] == 5 * DAY
    del r["retrieved_utc"]
    assert reddit.candidate(r)["age"] is None


def test_deleted_removed_and_foreign_subs_are_dropped():
    assert reddit.candidate(raw(body="[deleted]")) is None
    assert reddit.candidate(raw(body="[removed]")) is None
    assert reddit.candidate(raw(author="[deleted]")) is None
    assert reddit.candidate(raw(subreddit="pics")) is None
    assert reddit.candidate(raw(body="nothing relevant here")) is None


def test_subreddit_match_is_case_insensitive():
    assert reddit.candidate(raw(subreddit="LearnProgramming")) is not None


def test_to_text_markdown():
    text, links = reddit.to_text("Try [CS50](https://cs50.harvard.edu) &amp; see https://ocw.mit.edu/x\n\n&gt; quoted")
    assert text.startswith("Try CS50 & see") and "> quoted" in text
    assert links == ["https://cs50.harvard.edu", "https://ocw.mit.edu/x"]


def test_reddit_ids_never_collide_with_hn():
    assert str(reddit.candidate(raw(id="123"))["id"]) != "123"


def test_hn_paths_unchanged():
    assert sources.paths("hn").pool == ROOT / "data" / "pool.json"
    assert sources.paths("reddit").pool == ROOT / "data" / "reddit" / "pool.json"
    assert len(sources.SUBREDDITS) == 30


def test_permalink():
    c = reddit.candidate(raw())
    assert reddit.permalink(c) == "https://www.reddit.com/r/learnprogramming/comments/xyz/_/abc/"


def test_prefilter_catches_reddit_only_names_and_hosts():
    assert reddit.PREFILTER.search("I loved Building a Second Brain")
    assert reddit.PREFILTER.search("see https://maven.com/x")
    assert reddit.PREFILTER.search("a great lecture")
    assert reddit.REDDIT_SPAM.search("check out my profile")
