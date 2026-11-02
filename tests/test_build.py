import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import build  # noqa: E402
import pages  # noqa: E402
import rank  # noqa: E402
import reddit  # noqa: E402

Y2024 = 1_710_000_000
NOW = 1_790_000_000


def end(author, stance="recommends", thread="t3_a", t=Y2024, factor=None, item=None):
    e = {"author": author, "thread": thread, "time": t, "stance": stance,
         "item": item or {"id": f"t1_{author}", "time": t}}
    if factor is not None:
        e["factor"] = factor
    return e


def test_source_stats_reddit_needs_two_recommenders():
    one = [end("a"), end("b", "mentions")]
    assert build.source_stats(one, NOW, "reddit") is None
    two = one + [end("c", thread="t3_b")]
    stats = build.source_stats(two, NOW, "reddit")
    assert stats["recommenders"] == 2
    assert stats["threads"] == 2
    # HN keeps listing single-recommender courses.
    assert build.source_stats(one, NOW, "hn")["recommenders"] == 1


def test_source_stats_none_without_a_positive_stance():
    assert build.source_stats([end("a", "mentions"), end("b", "criticizes")], NOW, "hn") is None


def test_source_stats_counts_recommenders_by_stance_not_upvotes():
    # A downvoted "recommends" (factor 0.5 -> vote 0.35) is still a recommender.
    ends = [end("a", factor=0.5), end("b", "strongly_recommends", factor=0.5)]
    stats = build.source_stats(ends, NOW, "reddit")
    assert stats["recommenders"] == 2
    assert stats["strong_share"] == 0.5
    # The upvote factor still scales the score.
    assert stats["score"] == round(rank.score(ends), 3)
    assert stats["score"] < build.source_stats([end("a"), end("b", "strongly_recommends")], NOW, "reddit")["score"]


def test_source_stats_endorsements_strongest_then_newest():
    ends = [end("a", t=Y2024), end("b", "strongly_recommends", t=Y2024 - 10), end("c", t=Y2024 + 10)]
    stats = build.source_stats(ends, NOW, "hn")
    assert [(it["id"], code) for it, code in stats["endorsements"]] == [("t1_b", 3), ("t1_c", 2), ("t1_a", 2)]


def test_reddit_comment_is_excerpt():
    words = ("lorem ipsum dolor sit amet " * 30)[:500]
    it = {"id": "t1_xyz", "src": "reddit", "by": "u1", "time": Y2024, "text": words, "sub": "learnprogramming",
          "ups": 12, "age": 10**7, "thread": "t3_abc"}
    cm = build.comment_entry(it, {"t1_xyz": ["t3_abc", "Best course?"]})
    assert len(cm["text"]) <= 300 and cm["text"].endswith("…")
    assert cm["src"] == "reddit" and cm["sub"] == "learnprogramming" and cm["ups"] == 12
    assert cm["url"] == reddit.permalink(it)
    assert (cm["tid"], cm["thread"]) == ("t3_abc", "Best course?")


def test_hn_comment_entry_unchanged():
    it = {"id": 42, "src": "hn", "by": "pg", "time": Y2024, "text": "x" * 900}
    assert build.comment_entry(it, {"42": [40, "Ask HN"]}) == {
        "id": 42, "by": "pg", "t": Y2024, "text": "x" * 900, "thread": "Ask HN", "tid": 40}
    assert build.comment_entry(it, {})["tid"] == 42


def test_file_count_guard(tmp_path):
    for i in range(3):
        (tmp_path / f"f{i}.html").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "g.html").write_text("x")
    assert build.check_file_count(tmp_path, limit=4) == 4
    with pytest.raises(SystemExit):
        build.check_file_count(tmp_path, limit=3)
    assert build.MAX_FILES == 19_000


def test_pages_view_flattens_one_source():
    c = {"id": 1, "name": "CS50", "related": [2], "slug": "cs50",
         "sources": {"hn": {"rank": 3, "score": 9.0}, "reddit": {"rank": 1, "score": 4.0}}}
    v = pages.view(c, "reddit")
    assert v["rank"] == 1 and v["score"] == 4.0 and v["name"] == "CS50" and v["related"] == [2]
    assert "sources" not in v
    assert pages.view(c, "hn")["rank"] == 3


def it_hn(i, by, t=Y2024, topic="Programming"):
    return {"id": i, "src": "hn", "by": by, "time": t, "text": "hn text", "topic": topic}


def it_rd(i, by, t=Y2024, ups=5, topic="Programming"):
    return {"id": i, "src": "reddit", "by": by, "time": t, "text": "rd text", "sub": "learnprogramming",
            "ups": ups, "age": 10**8, "thread": "t3_q", "topic": topic}


def test_assemble_merges_sources_hn_first():
    cat = {"courses": {1: {"name": "CS50", "provider": "Harvard"}, 2: {"name": "Fast.ai", "provider": "fast.ai"},
                       3: {"name": "Solo", "provider": "X"}, 4: {"name": "SICP", "provider": "MIT"}}}
    by_course = {
        1: [it_hn(10, "a"), it_rd("t1_r1", "ra"), it_rd("t1_r2", "rb"), it_rd("t1_r3", "rc")],
        2: [it_rd("t1_r3", "rc"), it_rd("t1_r4", "rd", ups=2000), it_rd("t1_r2", "rb")],
        3: [it_rd("t1_r5", "re")],  # one Reddit recommender: not listed
        4: [it_hn(11, "b"), it_hn(12, "c", t=Y2024 + 5)],
    }
    summaries = {"hn": {1: {"id": 1, "summary": "HN blurb", "stances": {"10": "recommends"}},
                        4: {"id": 4, "summary": "SICP blurb", "stances": {"11": "strongly_recommends"}}},
                 "reddit": {1: {"id": 1, "summary": "Reddit blurb", "stances": {"t1_r1": "mentions"}},
                            2: {"id": 2, "summary": "Fast blurb", "stances": {}}}}
    threads = {"hn": {"10": [9, "Ask HN"]}, "reddit": {}}
    courses, comments, ends_at = build.assemble(cat, by_course, summaries, threads, {})
    # HN rank order first, then Reddit-only courses by Reddit rank.
    assert [c["id"] for c in courses] == [4, 1, 2]
    sicp, cs50, fast = courses
    assert cs50["summary"] == "HN blurb" and fast["summary"] == "Fast blurb"
    assert set(cs50["sources"]) == {"hn", "reddit"} and set(fast["sources"]) == {"reddit"}
    assert cs50["sources"]["reddit"]["recommenders"] == 2  # r1's Reddit-file stance "mentions" applies
    assert [sicp["sources"]["hn"]["rank"], cs50["sources"]["hn"]["rank"]] == [1, 2]
    assert {cs50["sources"]["reddit"]["rank"], fast["sources"]["reddit"]["rank"]} == {1, 2}
    assert fast["sources"]["reddit"]["badges"] == rank.badges(fast["sources"]["reddit"],
                                                              fast["sources"]["reddit"]["rank"] - 1, 2, Y2024, "reddit")
    # Co-mentioned in the same Reddit comments first, then the best of the topic.
    assert fast["related"] == [1, 4] and cs50["related"] == [2, 4] and sicp["related"] == [1, 2]
    reddit_cms = [cm for cm in comments if cm.get("src") == "reddit"]
    assert reddit_cms and all(cm["url"].startswith("https://www.reddit.com/") for cm in reddit_cms)
    assert "t1_r5" not in {cm["id"] for cm in comments}
    assert ends_at == {"hn": Y2024 + 5, "reddit": Y2024}
