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
