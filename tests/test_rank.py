import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import rank  # noqa: E402

Y2015 = 1_430_000_000  # mid-2015
YEAR = int(rank.YEAR)


def e(author, thread, stance="recommends", t=Y2015):
    return {"author": author, "thread": thread, "time": t, "stance": stance}


def test_one_vote_per_author_at_their_strongest():
    repeated = [e("a", 1, "mentions"), e("a", 2, "strongly_recommends"), e("a", 3)]
    assert rank.score(repeated) == rank.score([e("a", 2, "strongly_recommends")])


def test_pile_on_in_one_thread_is_damped():
    one_thread = [e(f"u{i}", 1) for i in range(10)]
    ten_threads = [e(f"u{i}", i) for i in range(10)]
    assert rank.score(ten_threads) > 4 * rank.score(one_thread) / 2
    # ten replies in the same thread are worth less than two independent threads' full weight
    assert rank.score(one_thread) < 2 * rank.STANCE_WEIGHT["recommends"]


def test_staying_power_beats_a_single_season():
    same_year = [e(f"u{i}", i) for i in range(6)]
    spread = [e(f"u{i}", i, t=Y2015 + i * YEAR) for i in range(6)]
    assert rank.score(spread) > rank.score(same_year)


def test_criticism_earns_nothing():
    assert rank.score([e("a", 1, "criticizes")]) == 0


def test_stronger_stance_scores_higher():
    assert rank.score([e("a", 1, "strongly_recommends")]) > rank.score([e("a", 1, "recommends")]) \
        > rank.score([e("a", 1, "mentions")])


def test_trending_prefers_recent_votes():
    now = Y2015 + 10 * YEAR
    old = [e("a", 1, t=Y2015)]
    new = [e("a", 1, t=now - YEAR // 2)]
    assert rank.trending(new, now) > 4 * rank.trending(old, now)


def test_upvote_factor():
    D = 86400
    assert rank.upvote_factor(None, None) == 1.0
    assert rank.upvote_factor(500, 5 * D) == 1.0          # too young to trust
    assert rank.upvote_factor(0, 60 * D) == 0.5
    assert rank.upvote_factor(1, 60 * D) == 1.0
    assert rank.upvote_factor(1000, 60 * D) == 2.0
    assert rank.upvote_factor(10**6, 60 * D) == 2.0       # capped


def test_factor_scales_vote_but_not_stance_weight():
    v = rank.author_votes([{**e("a", 1), "factor": 2.0}])[0]
    assert v["w"] == 1.4 and v["sw"] == 0.7


def test_factor_applies_to_trending_and_hn_unchanged():
    now = Y2015
    assert rank.trending([{**e("a", 1), "factor": 2.0}], now) == 2 * rank.trending([e("a", 1)], now)
    assert rank.score([{**e("a", 1), "factor": 0.5}]) == 0.5 * rank.score([e("a", 1)])


def test_badge_rules_per_source():
    c = {"recommenders": 3, "years_active": 6, "first": 1_300_000_000, "last": 1_700_000_000,
         "strong_share": 0.0, "recent_share": 0.6}
    assert set(rank.BADGE_RULES) == {"hn", "reddit"}
    assert rank.badges(c, 0, 100, 0) == rank.badges(c, 0, 100, 0, source="hn")
