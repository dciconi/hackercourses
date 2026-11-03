"""Course ranking.

Comment karma is not public, so the score rests on who recommended a course, how strongly,
in how many separate discussions, and for how long:

1. Stance weight per comment: strongly recommends 1.0, recommends 0.7, mentions 0.25,
   criticizes 0 (criticism is shown, it just earns no points).
2. One vote per person: an author who recommends a course five times counts once, at their
   strongest stance.
3. Pile-on damping: within one thread, votes are sorted and decay geometrically
   (1, 1/2, 1/4, ...), so ten replies in one "Ask HN" thread are worth at most two independent
   ones, while the same course surfacing in ten unrelated threads counts ten times.
4. Staying power: x(1 + 0.08 per extra calendar year with a recommendation), so a course people
   still recommend a decade later outranks a one-season fad with the same votes.

score = sum over threads of damped votes  x  staying-power multiplier

Reddit comments also carry an upvote factor on their vote, 1 + min(1, log10(ups) / 3): 1 upvote
counts as 1.0, 1,000 or more as 2.0, a score of 0 or below as 0.5, and a comment captured less than
30 days after posting is not scaled. The factor scales the vote, never the stance weight. HN
endorsements have no factor, so HN scores are unchanged.

"Trending" uses the same votes with a 2-year half-life back from the newest comment in the data.
"""

import math
import time
from collections import defaultdict

STANCE_WEIGHT = {"strongly_recommends": 1.0, "recommends": 0.7, "mentions": 0.25, "criticizes": 0.0}
THREAD_DECAY = 0.5
YEAR_BONUS = 0.08
HALF_LIFE_YEARS = 2.0
YEAR = 365.25 * 24 * 3600
UPVOTE_MIN_AGE = 30 * 24 * 3600
_HN_RULES = {"classic_span": 8, "evergreen_years": 6, "evergreen_span": 8, "rising_min": 3,
             "rising_share": 0.6, "gem_min": 2, "gem_max": 4, "gem_strong": 0.75}
# Reddit: stricter "rising" (full 2005-2023 history makes a 3-year window selective) and "hidden gem".
_REDDIT_RULES = {**_HN_RULES, "rising_min": 5, "rising_share": 0.7, "gem_strong": 0.8}
BADGE_RULES = {"hn": dict(_HN_RULES), "reddit": _REDDIT_RULES}


def upvote_factor(ups, age):
    """Vote multiplier from a comment's upvotes; age = seconds between posting and capture."""
    if ups is None or age is None or age < UPVOTE_MIN_AGE:
        return 1.0
    if ups <= 0:
        return 0.5
    return 1 + min(1.0, math.log10(ups) / 3)


def author_votes(endorsements):
    """endorsements: [{author, thread, time, stance, factor?}] -> one strongest vote per author.

    "w" is the vote (stance weight x optional upvote factor) of the author's strongest weighted
    comment, which also supplies thread and time; "sw" is the author's strongest stance weight
    across all their comments."""
    best = {}
    for e in endorsements:
        sw = STANCE_WEIGHT[e["stance"]]
        w = sw * e.get("factor", 1.0)
        cur = best.get(e["author"])
        if cur is None:
            best[e["author"]] = {**e, "sw": sw, "w": w}
            continue
        top_sw = max(sw, cur["sw"])
        if w > cur["w"]:
            best[e["author"]] = {**e, "sw": top_sw, "w": w}
        else:
            cur["sw"] = top_sw
    return list(best.values())


def damped(votes, weight=lambda v: v["w"]):
    by_thread = defaultdict(list)
    for v in votes:
        by_thread[v["thread"]].append(weight(v))
    total = 0.0
    for ws in by_thread.values():
        total += sum(w * THREAD_DECAY ** i for i, w in enumerate(sorted(ws, reverse=True)))
    return total


def score(endorsements):
    votes = author_votes(endorsements)
    years = {time.gmtime(e["time"]).tm_year for e in endorsements if STANCE_WEIGHT[e["stance"]] > 0}
    return damped(votes) * (1 + YEAR_BONUS * max(0, len(years) - 1))


def trending(endorsements, now):
    votes = author_votes(endorsements)
    return damped(votes, lambda v: v["w"] * 0.5 ** ((now - v["time"]) / (HALF_LIFE_YEARS * YEAR)))


def badges(course, rank, n_courses, now, source="hn"):
    """course: dict with recommenders, years_active, first, last, strong_share, recent_share."""
    r = BADGE_RULES[source]
    out = []
    span = time.gmtime(course["last"]).tm_year - time.gmtime(course["first"]).tm_year
    if rank < max(25, n_courses // 50) and span >= r["classic_span"]:
        out.append("classic")
    if course["years_active"] >= r["evergreen_years"] and span >= r["evergreen_span"]:
        out.append("evergreen")
    if course["recommenders"] >= r["rising_min"] and course["recent_share"] >= r["rising_share"]:
        out.append("rising")
    if r["gem_min"] <= course["recommenders"] <= r["gem_max"] and course["strong_share"] >= r["gem_strong"]:
        out.append("hidden gem")
    return out


def recent_share(endorsements, now, years=3):
    votes = author_votes(endorsements)
    total = sum(v["w"] for v in votes) or 1.0
    return sum(v["w"] for v in votes if now - v["time"] <= years * YEAR) / total
